from muzak.drivers.errors import MQLSyntaxError

class QueryParser:
    def __init__(self, query_str: str):
        self.query_str = " ".join(query_str.split())
        self.strlen = len(query_str)

    def peek(self):
        if len(self.query_str) > 0:
            return self.query_str[0]
        else:
            return None

    def next(self):
        n = self.query_str[0]
        self.query_str = self.query_str[1:]
        return n

    def next_word(self):
        next_word = self.query_str.split(" ", 1)[0]
        return str(next_word).strip()

    def parse_word(self):
        word_chars = []
        while self.peek() not in (" ", None):
            # print(self.peek())
            c = self.next()
            if c.isalpha():
                word_chars.append(c)
        if self.peek() == " ":
            self.next()
        return "".join(word_chars)

    def parse_int(self):
        i_chars = []
        while self.peek() not in (" ", None):
            c = self.next()
            if not c.isnumeric():
                raise MQLSyntaxError("Expected type 'int' got type '%s' near: %s" % (repr(type(c)), self.query_str))
            i_chars.append(c)
        return int("".join(i_chars))

    def parse_kvs(self, subjects, _any: bool = False):
        definition = {}
        for subject in subjects:
            if "=" not in subject:
                raise MQLSyntaxError("Invalid Key=>Value mapping in query subject [%s]" % subject)
            key, value = subject.split("=", 1)
            if value == "\\Null":
                value = None
            if _any:
                if key in definition:
                    definition[key].append(value)
                else:
                    definition[key] = [value]
            else:
                definition[key] = value
        return definition

    def parse_subject_part(self):
        if self.peek() == " ":
            self.next()
        word_chars = []
        while self.peek() not in (" ", ")", None, ",", "]"):
            word_chars.append(self.next())
        if self.peek() == ",":
            self.next()
        return "".join(word_chars)

    def parse_subject(self):
        subjects = []
        if self.peek() != "(":
            raise MQLSyntaxError("Invalid subject: expected: '(' but got '%s' near: %s" % (self.peek(), self.query_str))
        else:
            self.next()
        while self.peek() not in (")", None):
            subjects.append(self.parse_subject_part())
        if "=" in subjects[0]:
            subjects = self.parse_kvs(subjects)
        while self.peek() in (" ", ")"):
            self.next()
        return subjects

    def parse_definition(self):
        _any = False
        subjects = []
        if self.peek() not in ("(", "["):
            raise MQLSyntaxError("Expected '(' or '[', but got '%s' near: %s" % (self.peek(), self.query_str))
        c = self.next()
        while self.peek() not in ("]", ")", None):
            subjects.append(self.parse_subject_part())
        if c == "[":
            _any = True
            definition = self.parse_kvs(subjects, True)
        else:
            definition = self.parse_kvs(subjects)
        while self.peek() in (" ", ")", "]"):
            self.next()
        return definition, _any

    def parse_query(self):
        command = self.parse_word()
        subjects = self.parse_subject()
        condition = self.parse_word()
        _any = False
        target = {}
        limit = 0
        if condition.lower() == "where":
            target, _any = self.parse_definition()
            condition = self.parse_word()
        if condition.lower() == "limit":
            limit = self.parse_int()
        # else:
        #     self.parse_word()
        #     limit = self.parse_int()
        return command, subjects, target, limit, _any