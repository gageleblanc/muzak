from muzak.drivers.errors import MQLSyntaxError
from muzak.drivers.parser.tokens import T_EOF, TOKENS, C_List, C_Target, MQLParserToken, T_And, T_Char, T_CloseCurl, T_Equal, T_Int, T_OpenCurl, T_QueryTerminator, T_Whitespace, T_CloseBrac, T_CloseParen, T_Comma, T_Null, T_OpenBrac, T_OpenParen, W_Command, W_Condition, W_Generic, W_Int, token_type, word_type


class QueryLexer:
    def __init__(self, query_str: str):
        self._raw = query_str
        self.pos = 0
        self.query_str = query_str
        self.strlen = len(query_str)

    def peek(self):
        # Peek at the next character in the input or return EOF if it doesn't exist
        if len(self.query_str) > 0:
            return self.query_str[0]
        else:
            return T_EOF

    def peek_type(self):
        # Peek at the type of the next character in the input, or return EOF if it doesn't exist
        if len(self.query_str) > 0:
            return token_type(self.query_str[0])
        else:
            return T_EOF

    def next(self):
        # Remove and return the next character from the input
        n = self.query_str[0]
        self.pos += 1
        self.query_str = self.query_str[1:]
        return n

    def parse_word(self):
        word_chars = []
        # Continue only while the next character is of the T_Char type 
        while self.peek_type() == T_Char:
            # Get the next character in the input and append it to the list of characters in this word
            c = self.next()
            word_chars.append(c)
        if self.peek() == " ":
            self.next()
        # Join all word characters together to form word
        return "".join(word_chars)

    def parse_int(self):
        i_chars = []
        # Continue only while the next character is of the T_Int type
        while self.peek_type() == T_Int:
            # Get the next character in the input and validate that it is also numeric
            # as far as python is concerned before appending to the list of characters 
            # in this int, raise an error otherwise
            c = self.next()
            if not c.isnumeric():
                raise MQLSyntaxError("Expected type 'int' got type '%s' near: %s" % (repr(type(c)), self.query_str))
            i_chars.append(c)
        # Join int characters and cast to int python type before returning
        return int("".join(i_chars))

    def parse_kv_pair(self):
        # Remove leading whitespace if any
        if self.peek_type() == T_Whitespace:
            self.next()
        key_tokens = []
        # Continue until we hit an equal token
        while self.peek_type() != T_Equal:
            # If the next character is not one of T_Int, T_Char, or T_Whitespace throw a SyntaxError since it is not valid for a key
            if self.peek_type() not in (T_Int, T_Char, T_Whitespace):
                raise MQLSyntaxError("Syntax error while parsing list: Expected one of %s, but got '%s' near: %s" % (", ".join(["'%s'" % x.__name__ for x in (T_Int, T_Char, T_Whitespace)]), self.peek(), self.query_str))
            # Append the next character to the key_tokens list since we have made it past any possible exceptions
            key_tokens.append(self.next())
        # This should technically always be true, but better safe than sorry
        if self.peek_type() == T_Equal:
            # Remove leading equal since we don't care about it
            self.next()
        # Join our resulting tokens into the key
        key = "".join(key_tokens)

        value_tokens = []
        # Continue until we hit a closing curly brace or comma, indicating another item
        while self.peek_type() not in (T_Comma, T_CloseCurl):
            # If the next character is not one of T_Int, T_Char, or T_Whitespace throw a SyntaxError since it is not valid for a key
            if self.peek_type() not in (T_Int, T_Char, T_Whitespace):
                raise MQLSyntaxError("Syntax error while parsing list: Expected one of %s, but got '%s' near: %s" % (", ".join(["'%s'" % x.__name__ for x in (T_Int, T_Char, T_Whitespace)]), self.peek(), self.query_str))
            # Append the next character to the value_tokens list since we have made it past any possible exceptions
            value_tokens.append(self.next())
        # Join our resulting tokens into the value
        value = "".join(value_tokens)
        # Remove leading comma if it exists
        if self.peek_type() == T_Comma:
            self.next()
        # Return our key, value pair
        return key, value

    def parse_list_item(self):
        # Remove leading whitespace if any
        if self.peek_type() == T_Whitespace:
            self.next()
        word_chars = []
        while self.peek_type() not in (T_CloseBrac, T_CloseParen, T_Comma, T_Null):
            word_chars.append(self.next())
        if self.peek_type() == T_Comma:
            self.next()
        return "".join(word_chars)

    def parse_list(self, list_type: MQLParserToken):
        # Lists can be defined with either parenthesis or square brackets,
        # so to account for this we match the beginning list token with
        # the proper end token. The default expected type is parenthesis
        close_paren = T_CloseParen
        if list_type == T_OpenBrac:
            close_paren = T_CloseBrac
        items = []
        # Again, this should always be true, but better to be safe than sorry
        if self.peek_type() != list_type:
            raise MQLSyntaxError("Syntax Error while parsing list: expected: '%s' but got '%s' near: %s" % (list_type.__name__, self.peek(), self.query_str))
        else:
            self.next()
        # Continue until we hit a closing token
        while self.peek_type() != close_paren:
            if self.peek_type() not in (T_Char, T_Whitespace):
                raise MQLSyntaxError("Syntax error while parsing list: Expected one of %s, but got '%s' near: %s" % (", ".join(["'%s'" % x.__name__ for x in (T_Char, T_Whitespace)]), self.peek(), self.query_str))
            items.append(self.parse_list_item())
        # Remove extra whitespace and closing tokens.
        while self.peek_type() in (T_Whitespace, close_paren):
            self.next()
        return items

    def parse_target(self):
        eager = True
        definition = {}
        # If the target begins with the & symbol, this target is strict instead of eager
        if self.peek_type() == T_And:
            eager = False
            # Remove token after setting eager to false
            self.next()
        # Ensure the target starts with an opening curly brace
        if self.peek_type() != T_OpenCurl:
            raise MQLSyntaxError("Expected 'T_OpenCurl', but got '%s' near: %s" % (self.peek(), self.query_str))
        if self.peek_type() == T_OpenCurl:
            self.next()
        # Continue until closing curly brace
        while self.peek_type() != T_CloseCurl:
            # If the next character is not one of T_Char or T_Whitespace throw a SyntaxError since it is not valid for a key
            if self.peek_type() not in (T_Char, T_Whitespace):
                raise MQLSyntaxError("Syntax error while parsing list: Expected one of %s, but got '%s' near: %s" % (", ".join(["'%s'" % x.__name__ for x in (T_Char, T_Whitespace)]), self.peek(), self.query_str))
            # Get Key, value pair from query string
            key, value = self.parse_kv_pair()
            # Recognize a value of "\Null" as python's NoneType
            if value == "\\Null":
                value = None
            # Add key, value pair target definition
            if eager:
                # If Eager we use lists since the key could be any of the given values
                if key in definition:
                    definition[key].append(value)
                else:
                    definition[key] = [value]
            else:
                # When strict we use a string value since 
                # the key needs to be equal to the value strictly
                definition[key] = value
        # Remove any closing curly braces
        if self.peek_type() == T_CloseCurl:
            self.next()
        # Return our target definition and the eager value 
        return definition, eager

    def run(self):
        ast = []
        while self.peek_type() != T_EOF:
            # Ignore whitespace
            if self.peek_type() == T_Whitespace:
                self.next()
            # Parse a word if we detect a regular character
            elif self.peek_type() == T_Char:
                position = self.pos
                w = self.parse_word()
                ast.append({"type": word_type(w), "data": w, "position": position})
            # Parse a number if we detect an int character
            elif self.peek_type() == T_Int:
                position = self.pos
                i = self.parse_int()
                ast.append({"type": W_Int, "data": i, "position": position})
            # Parse a list if we detect an opening token for lists
            elif self.peek_type() in (T_OpenBrac, T_OpenParen):
                position = self.pos
                c = self.parse_list(self.peek_type())
                ast.append({"type": C_List, "data": c, "position": position})
            # Parse a target if we detect an & token or the curly brace token
            elif self.peek_type() in (T_And, T_OpenCurl):
                position = self.pos
                d = self.parse_target()
                ast.append({"type": C_Target, "data": d, "position": position})
            # If we see a query terminator, remove it from the input and add to AST, indicating to the parser that this query is over. 
            elif self.peek_type() == T_QueryTerminator:
                self.next()
                ast.append({"type": T_QueryTerminator, "data": None})
            # Raise an error for an unexpected token
            else:
                raise MQLSyntaxError("Unexpected token: '%s' near: %s" % (self.peek(), self.query_str))
        return ast


# This parser essentially pulls the data from the AST that we need to interperet in order to run the query. see muzak.drivers.MuzakQL 
class QueryParser:
    def __init__(self, query_str: str):
        self.query_str = "%s " % query_str
        lexer = QueryLexer(query_str)
        self.ast = lexer.run()

    def peek(self):
        # Peek at the next value without removing and returning it from the AST
        if len(self.query_str) > 0:
            return self.ast[0]
        else:
            return {"type": T_EOF}
    
    def peek_type(self):
        # Peek at the next value without removing and returning it from the AST
        if len(self.query_str) > 0:
            return self.ast[0]["type"]
        else:
            return {"type": T_EOF}

    def next(self):
        # Remove and return the next value from the AST, or return an EOF token if the AST is empty
        if len(self.ast) > 0:
            n = self.ast.pop(0)
            return n
        else:
            return {"type": T_EOF}

    def expect(self, expect_type):
        # Expect that the next value in the AST is a certain type, or raise an error if it is not.
        i = self.next()
        position = i.get("position", 0)
        if i["type"] == expect_type:
            return i["data"]
        else:
            raise MQLSyntaxError("Expected type: '%s' but got '%s' near: %s" % (expect_type.__name__, i["type"].__name__, self.query_str[position:]))

    def parse_query(self):
        # Start by expecting at least a command from the query
        command = self.expect(W_Command)
        # If the command is "show" we can expect one more word and return
        if command == "show":
            labels = [self.expect(W_Generic)]
            return command, labels, {}, 0, False
        # If we arrive here, we should expect a list of labels to query
        labels = self.expect(C_List)
        if len(labels) == 0:
            labels = None
        # Set default values in case there are no restriction conditions on this query
        target = {}
        eager = True
        limit = 0
        # If we have more information in our AST, continue on by expecting a condition
        if len(self.ast) > 0 and self.peek_type() != T_QueryTerminator:
            condition = self.expect(W_Condition)
            # If the condition is a "where" condition, we will expect a target 
            # which will contain the target data, and the eager value of this target
            if condition.lower() == "where":
                target, eager = self.expect(C_Target)
                # we will also expect another condition word after our target if the AST is not empty
                if len(self.ast) > 0 and self.peek_type() != T_QueryTerminator:
                    condition = self.expect(W_Condition)
            # If our condition is a "limit" condition, we will expect an integer word.
            if condition.lower() == "limit":
                limit = self.expect(W_Int)
        # Return all of these values to whatever program will interpret them, in this case just another python function.
        return command, labels, target, limit, eager

    def parse_all(self):
        queries = []
        # While there are still items in the AST, continue
        while len(self.ast) > 0:
            # If the next item is the query terminator we can remove it
            if self.peek_type() == T_QueryTerminator:
                self.next()
            else:
                # Parse the next query, append to final list, and continue
                q = self.parse_query()
                queries.append(q)
        return queries