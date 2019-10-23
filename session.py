from fuzzywuzzy import fuzz


class Session:

    def __init__(self, userd_id, first_name=None, last_name=None, language_code=None):
        self.language_code = language_code
        self.last_name = last_name
        self.first_name = first_name
        self.user_id = userd_id
        self.status = str()
        self.languages = dict()  # language: True/False - True is active now
        self.words_to_learn = list()  # (word, definition, mode, hid)]
        # ((word, definition, mode, hid), [similar words])
        self.read_error_storage = list()
        self.current_word = 0
        self.hid_cash = str()
        self.words_to_add = None
        self.definitions = list()
        self.list_hid_word = None  # ""(hid, word)

    def active_lang(self):
        for l, active in self.languages.items():
            if active:
                return l

    def delete_current_error(self):
        if len(self.read_error_storage) > 0:
            del self.read_error_storage[0]
        else:
            print(self.user_id, "deleting from empty self.read_error_storage")

    def move_error_down(self):
        self.read_error_storage.append(self.read_error_storage[0])
        self.delete_current_error()

    def get_most_similar_words(self, word, limit):
        tmp = dict()
        words = list(w[0] for w in self.words_to_learn)
        for w in words:
            if w.lower() == word.lower():
                continue
            r = fuzz.ratio(w, word)
            tmp[r] = w
        rr = list(tmp.keys())
        rr.sort(reverse=True)
        rr = rr[:limit]
        result = list()
        for r in rr:
            variant = tmp[r]
            if word[0].isupper():
                variant = variant.capitalize()
            else:
                variant = str(variant).lower()
            result.append(variant)
        return result

    def add_error(self):
        error = self.words_to_learn[self.current_word]
        variants = self.get_most_similar_words(error[0], 3)
        if (error, variants) not in self.read_error_storage:
            self.read_error_storage.append((error, variants))

    def get_error_answer(self):
        word = self.read_error_storage[0][0]
        return word[0]

    def has_more_errors(self):
         return len(self.read_error_storage) > 0

    def get_next_error(self):
        return self.read_error_storage[0][0], self.read_error_storage[0][1]

    def has_more_words_to_learn(self):
        return self.current_word < len(self.words_to_learn)

    def get_current_definition(self):
        return self.get_current_word()[1]

    def get_current_hid(self):
        hid = self.get_current_word()
        if hid is None:
            return None
        return hid[3]

    def get_current_mode(self):
        return self.get_current_word()[2]

    def get_current_word(self):
        if len(self.words_to_learn) > 0:
            if self.current_word >= len(self.words_to_learn):
                return None
            return self.words_to_learn[self.current_word]
        else:
            return None

    def delete_current_word(self):
        self.current_word += 1

    def level_up_current_word(self, new_hid):
        word = self.words_to_learn[self.current_word]
        mode = int(word[2]) + 1
        new_word = (word[0], word[1], mode, new_hid)
        self.words_to_learn.append(new_word)

    # Writing
    def add_writing_error(self, misspelt_word):
        for i in range(len(self.read_error_storage)):
            w = self.read_error_storage[i]
            if w[0] == self.get_current_word():
                l = list(w[1])
                l.append(misspelt_word)
                self.read_error_storage[i] = (w[0], l)
                return

        self.read_error_storage.append(
            (self.get_current_word(), [misspelt_word]))

    def set_active_language(self, lang):
        lang0 = self.active_lang()
        if lang0 is not None:
            self.languages[lang0] = False
        self.languages[lang] = True

    def get_user_id(self):
        return self.user_id
