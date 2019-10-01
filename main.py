import skyleodict
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

skyeng_client = skyleodict.SkyengClient()
skyeng_client.auth(config['skyeng']['username'], config['skyeng']['password'])

lingualeo_client = skyleodict.LingualeoClient()
lingualeo_client.auth(config['lingualeo']['username'], config['lingualeo']['password'])

word_sets = skyeng_client.get_word_sets()
meanings_ids = []

for word_set in word_sets:
    words = skyeng_client.get_words(word_set['id'])
    word_set_meanings_ids = [(word.get('meaningId')) for word in words]
    word_set_meanings_count = len(word_set_meanings_ids)
    meanings_ids += word_set_meanings_ids

    print(f"Fetched {word_set_meanings_count} words from \"{word_set['title']}\" word set")

new_words = 0
existing_words = 0

print("Adding words to lingualeo...", end='')
for chunk in skyleodict.chunks(meanings_ids, 50):
    meanings = skyeng_client.get_meanings(chunk)

    for meaning in meanings:
        word = meaning['text']
        translation = meaning['translation']
        word_exists = lingualeo_client.word_exists(word)

        if not word_exists:
            new_words += 1
            lingualeo_client.word_add(word, translation)
        else:
            existing_words += 1

        print(".", end='')

print("finish!")
print("Added {} words, skipped {} words".format(new_words, existing_words))
