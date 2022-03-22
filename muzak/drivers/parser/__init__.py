from muzak.drivers.errors import MQLSyntaxError
from muzak.drivers.parser.tokens import T_EOF, TOKENS, C_List, C_Target, MQLParserToken, T_And, T_Char, T_CloseCurl, T_Equal, T_Int, T_OpenCurl, T_Whitespace, T_CloseBrac, T_CloseParen, T_Comma, T_Null, T_OpenBrac, T_OpenParen, W_Command, W_Condition, W_Generic, W_Int, token_type, word_type


class QueryLexer:
    def __init__(self, query_str: str):
        self.query_str = query_str
        self.strlen = len(query_str)

    def peek(self):
        if len(self.query_str) > 0:
            return self.query_str[0]
        else:
            return T_EOF

    def peek_type(self):
        if len(self.query_str) > 0:
            return token_type(self.query_str[0])
        else:
            return T_EOF

    def next(self):
        n = self.query_str[0]
        self.query_str = self.query_str[1:]
        return n

    def peek_word(self):
        next_word = self.query_str.split(" ", 1)[0]
        return str(next_word).strip()

    def parse_word(self):
        word_chars = []
        while TOKENS[self.peek()] == T_Char:
            # print(self.peek())
            c = self.next()
            word_chars.append(c)
        if self.peek() == " ":
            self.next()
        return "".join(word_chars)

    def parse_int(self):
        i_chars = []
        while self.peek_type() == T_Int:
            c = self.next()
            if not c.isnumeric():
                raise MQLSyntaxError("Expected type 'int' got type '%s' near: %s" % (repr(type(c)), self.query_str))
            i_chars.append(c)
        return int("".join(i_chars))

    def parse_kv_pair(self):
        if self.peek_type() == T_Whitespace:
            self.next()
        key_tokens = []
        while self.peek_type() != T_Equal:
            if self.peek_type() not in (T_Int, T_Char, T_Whitespace):
                raise MQLSyntaxError("Syntax error while parsing list: Expected one of %s, but got '%s' near: %s" % (", ".join(["'%s'" % x.__name__ for x in (T_Int, T_Char, T_Whitespace)]), self.peek(), self.query_str))
            key_tokens.append(self.next())
        if self.peek_type() == T_Equal:
            self.next()
        key = "".join(key_tokens)

        value_tokens = []
        while self.peek_type() not in (T_Comma, T_CloseCurl):
            if self.peek_type() not in (T_Int, T_Char, T_Whitespace):
                raise MQLSyntaxError("Syntax error while parsing list: Expected one of %s, but got '%s' near: %s" % (", ".join(["'%s'" % x.__name__ for x in (T_Int, T_Char, T_Whitespace)]), self.peek(), self.query_str))
            value_tokens.append(self.next())
        value = "".join(value_tokens)
        if self.peek_type() == T_Comma:
            self.next()
        return key, value

    def parse_list_item(self):
        if self.peek_type() == T_Whitespace:
            self.next()
        word_chars = []
        while self.peek_type() not in (T_CloseBrac, T_CloseParen, T_Comma, T_Null):
            word_chars.append(self.next())
        if self.peek_type() == T_Comma:
            self.next()
        return "".join(word_chars)

    def parse_list(self, list_type: MQLParserToken):
        close_paren = T_CloseParen
        if list_type == T_OpenBrac:
            close_paren == T_CloseBrac
        subjects = []
        if self.peek_type() != list_type:
            raise MQLSyntaxError("Syntax Error while parsing list: expected: '%s' but got '%s' near: %s" % (list_type.__name__, self.peek(), self.query_str))
        else:
            self.next()
        while self.peek_type() != close_paren:
            if self.peek_type() not in (T_Char, T_Whitespace):
                raise MQLSyntaxError("Syntax error while parsing list: Expected one of %s, but got '%s' near: %s" % (", ".join(["'%s'" % x.__name__ for x in (T_Char, T_Whitespace)]), self.peek(), self.query_str))
            subjects.append(self.parse_list_item())
        if "=" in subjects[0]:
            subjects = self.parse_kvs(subjects)
        while self.peek_type() in (T_Whitespace, close_paren):
            self.next()
        return subjects

    def parse_definition(self):
        _any = True
        definition = {}
        if self.peek_type() == T_And:
            _any = False
            self.next()
        if self.peek_type() != T_OpenCurl:
            raise MQLSyntaxError("Expected 'T_OpenCurl', but got '%s' near: %s" % (self.peek(), self.query_str))
        if self.peek_type() == T_OpenCurl:
            self.next()
        while self.peek_type() != T_CloseCurl:
            if self.peek_type() not in (T_Char, T_Whitespace):
                raise MQLSyntaxError("Syntax error while parsing list: Expected one of %s, but got '%s' near: %s" % (", ".join(["'%s'" % x.__name__ for x in (T_Char, T_Whitespace)]), self.peek(), self.query_str))
            key, value = self.parse_kv_pair()
            if value == "\\Null":
                value = None
            if _any:
                if key in definition:
                    definition[key].append(value)
                else:
                    definition[key] = [value]
            else:
                definition[key] = value
        if self.peek_type() == T_CloseCurl:
            self.next()
        return definition, _any

    def run(self):
        ast = []
        while self.peek_type() != T_EOF:
            if self.peek_type() == T_Whitespace:
                self.next()
            elif self.peek_type() == T_Char:
                w = self.parse_word()
                ast.append({"type": word_type(w), "data": w})
            elif self.peek_type() == T_Int:
                i = self.parse_int()
                ast.append({"type": W_Int, "data": i})
            elif self.peek_type() in (T_OpenBrac, T_OpenParen):
                c = self.parse_list(token_type(self.peek()))
                ast.append({"type": C_List, "data": c})
            elif self.peek_type() in (T_And, T_OpenCurl):
                d = self.parse_definition()
                ast.append({"type": C_Target, "data": d})
            else:
                raise MQLSyntaxError("Unexpected token: '%s' near: %s" % (self.peek(), self.query_str))
        return ast


class QueryParser:
    def __init__(self, query_str: str):
        self.query_str = query_str
        lexer = QueryLexer(query_str)
        self.ast = lexer.run()

    def peek(self):
        if len(self.query_str) > 0:
            return self.ast[0]
        else:
            return None

    def next(self):
        n = self.ast.pop(0)
        return n

    def expect(self, expect_type):
        i = self.next()
        if i["type"] == expect_type:
            return i["data"]
        else:
            raise MQLSyntaxError("Expected type: '%s' but got '%s'" % (expect_type.__name__, i["type"].__name__))

    def parse_query(self):
        command = self.expect(W_Command)
        if command == "show":
            subjects = [self.expect(W_Generic)]
            return command, subjects, {}, 0, False
        subjects = self.expect(C_List)
        target = {}
        _any = True
        limit = 0
        if len(self.ast) > 2:
            condition = self.expect(W_Condition)
            if condition.lower() == "where":
                target, _any = self.expect(C_Target)
                condition = self.expect(W_Condition)
            if condition.lower() == "limit":
                limit = self.expect(W_Int)
        return command, subjects, target, limit, _any