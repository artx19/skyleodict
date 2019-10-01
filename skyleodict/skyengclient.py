import requests
import re
from jsonschema import validate
from .errors import SkyengError


class SkyengClient:
    """HTTP client for fetch data from skyeng"""
    __auth_headers: dict
    __session: requests.Session
    __user_id: int

    def __init__(self):
        self.__session = requests.session()

    def get_meanings(self, words_ids):
        response = self.__session.get(
            'https://dictionary.skyeng.ru/api/for-mobile/v1/meanings',
            params=dict(
                ids=','.join(map(str, words_ids))
            ),
            headers=self.__auth_headers
        )
        self.__check_response(response)

        json = response.json()

        validate(json, {
            "id": {"type": "string"},
            "text": {"type": "string"},
            "translation": {
                "type": "object",
                "properties": {"text": {"type": "string"}}
            }
        })

        meanings = []
        for meaning in json:
            meanings.append({
                "text": str.strip(meaning['text']),
                "translation": str.strip(meaning['translation']['text'])
            })

        return meanings

    def get_words(self, word_set_id) -> list:
        words = self.__fetch_pages(
            'https://api.words.skyeng.ru/api/for-training/v1/wordsets/{}/words.json'.format(word_set_id),
            {
                "id": {"type": "integer"},
                "meaningId": {"type": "integer"},
            }
        )

        return words

    def get_word_sets(self) -> list:
        word_sets = self.__fetch_pages(
            'https://api.words.skyeng.ru/api/for-vimbox/v1/wordsets.json',
            {
                "type": "object",
                "properties": {
                    "meta": {
                        "type": "object",
                        "properties": {
                            "total": {"type": "integer"},
                            "lastPage": {"type": "integer"},
                            "pageSize": {"type": "integer"}
                        }
                    },
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "title": {"type": "string"}
                            }
                        }
                    }
                }
            }
        )

        return word_sets

    def auth(self, username: str, password: str):
        """Auth in skyeng"""
        csrf_token = self.__get_csrf_token()
        login_response = self.__session.post(
            'https://id.skyeng.ru/ru/frame/login-submit',
            data=dict(
                username=username,
                password=password,
                csrfToken=csrf_token
            )
        )
        self.__check_response(login_response)
        login_response_json = login_response.json()

        validate(login_response_json, {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"}
            }
        })

        if not login_response_json['success']:
            raise SkyengError('Auth failed')

        auth_response = self.__session.post('https://rooms.vimbox.skyeng.ru/users/api/v1/auth/auth')
        self.__check_response(auth_response)
        auth_response_json = auth_response.json()

        validate(auth_response_json, {
            "type": "object",
            "properties": {
                "token": {"type": "string"}
            }
        })

        self.__auth_headers = dict(Authorization='Bearer ' + auth_response.json()['token'])

        user_info_response = self.__session.get(
            'https://api.words.skyeng.ru/api/v1/userInfo.json',
            headers=self.__auth_headers,
        )
        self.__check_response(user_info_response)

        user_info_response_json = user_info_response.json()
        validate(user_info_response_json, {
            "type": "object",
            "properties": {
                "profile": {
                    "type": "object",
                    "properties": {
                        "userId": {"type": "integer"}
                    }
                }
            }
        })
        self.__user_id = user_info_response_json['profile']['userId']

    def __fetch_pages(self, url: str, schema: dict) -> list:
        page = 1
        last_page = None
        items = []
        while True:
            response = self.__session.get(
                url,
                params={'studentId': self.__user_id, 'pageSize': 100, 'page': page},
                headers=self.__auth_headers
            )
            self.__check_response(response)
            json = response.json()

            validate(json, schema)

            meta = json['meta']
            items += json['data']

            if last_page is None:
                last_page = meta['lastPage']
            if last_page <= page:
                break
            page += 1

        return items

    def __get_csrf_token(self) -> str:
        """Get csrf token from skyeng"""
        login_page_response = self.__session.get('https://id.skyeng.ru/ru/frame/login')
        self.__check_response(login_page_response)

        login_page_content = login_page_response.content.decode('utf8')
        csrf_token_search = re.search(
            r"<input type=\"hidden\" name=\"csrfToken\" value=\"(.+)\">",
            login_page_content
        )

        if csrf_token_search is None:
            raise SkyengError('Csrf token not found')

        return csrf_token_search.group(1)

    @staticmethod
    def __check_response(response: requests.models.Response):
        if response.status_code != 200:
            msg = f"Invalid status code {response.status_code} for url {response.url}"
            raise SkyengError(msg)
