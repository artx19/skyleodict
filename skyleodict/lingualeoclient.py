import requests
import urllib.parse
from jsonschema import validate
from .errors import LingualeoError


class LingualeoClient:
    """HTTP client for fetch&put data from/to skyeng"""
    __session: requests.Session

    def __init__(self):
        self.__session = requests.session()

    def auth(self, username: str, password: str):
        """Auth lingualeo API"""
        response = self.__session.get(
            "http://api.lingualeo.com/api/login?email={}&password={}".format(username, password)
        )
        self.__check_response(response)

        json = response.json()

        validate(json, {
            "user": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"}
                }
            }
        })

    def word_add(self, word: str, translation: str):
        response = self.__session.get(
            "http://api.lingualeo.com/addword?word={}&tword={}".format(word, translation)
        )
        self.__check_response(response)

        json = response.json()
        validate(json, {"error_msg": {"type": "string"}})

        if json['error_msg'] != '':
            raise LingualeoError(json['error_msg'])

    def word_exists(self, word) -> bool:
        """Get word's translate from lingualeo"""
        parsed_word = urllib.parse.quote(word)
        url = "http://api.lingualeo.com/gettranslates?word={}".format(parsed_word)
        response = self.__session.get(url)
        self.__check_response(response)
        json = response.json()

        validate(json, {
            "id": {"type": "integer"},
            "is_user": {"type": "integer"},
            "status": {"type": "string"},
            "translate": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "is_user": {"type": "integer"},
                    }
                }
            }
        })

        if json['status'] != 'ok':
            message = "Invalid status for url {}".format(url)
            raise LingualeoError(message)

        if json['is_user'] != 0:
            return True

        for translate in json['translate']:
            if translate['is_user'] is not None:
                return True

        return False

    @staticmethod
    def __check_response(response: requests.models.Response):
        if response.status_code != 200:
            msg = f"Invalid status code {response.status_code} for url {response.url}"
            raise LingualeoError(msg)
