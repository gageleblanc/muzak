# Token types below
# Tokens are individual characters. These classes
# are mostly used to associate characters with types
# so that we can further understand the input, or raise
# errors for unexpected syntax.
class MQLParserToken:
    pass

class T_Char(MQLParserToken):
    pass

class T_Int(MQLParserToken):
    pass

class T_Whitespace(MQLParserToken):
    pass

class T_Comma(MQLParserToken):
    pass

class T_Equal(MQLParserToken):
    pass

class T_And(MQLParserToken):
    pass

class T_Wildcard(MQLParserToken):
    pass

class T_OpenParen(MQLParserToken):
    pass

class T_CloseParen(MQLParserToken):
    pass

class T_OpenBrac(MQLParserToken):
    pass

class T_CloseBrac(MQLParserToken):
    pass

class T_OpenCurl(MQLParserToken):
    pass

class T_CloseCurl(MQLParserToken):
    pass

class T_Null(MQLParserToken):
    pass

class T_QueryTerminator(MQLParserToken):
    pass

class T_EOF(MQLParserToken):
    pass


# Words
# Words are groups of tokens that make up a type of word
# Words that are defined are matched with a type below,
# but Words that are not defined are matched with
# W_Generic type.
class MQLParserWord:
    pass

class W_Generic(MQLParserWord):
    pass

class W_Int(MQLParserWord):
    pass

class W_Condition(MQLParserWord):
    pass

class W_Command(MQLParserWord):
    pass


# Collections
# Collections are lists or key/value pairs
class MQLCollectionType:
    pass

# List is like a standard list in most languages. code ex.: (list, item, foo, bar)
class C_List(MQLCollectionType):
    pass

# Targets are a special type of key/value pairing. Each target
# can be either eager or strict. By default targets are eager
# this is a mechanic used when querying data. A target would
# be defined like this:
# 
# Eager:
# Query Syntax: {key1=value1,key1=value2,key2=value3}
# Python Syntax:
# 
# {
#   "key1": ["value1", "value2"],
#   "key2": ["value3"]
# }
#
# Strict:
# Query Syntax: &{key=value,key2=value2}
# Python Syntax:
# {
#   "key": "value",
#   "key2": "value2"
# }
#
class C_Target(MQLCollectionType):
    pass


# This is a map of tokens known to the parser/lexer
TOKENS = {
    'a': T_Char,
    'b': T_Char,
    'c': T_Char,
    'd': T_Char,
    'e': T_Char,
    'f': T_Char,
    'g': T_Char,
    'h': T_Char,
    'i': T_Char,
    'j': T_Char,
    'k': T_Char,
    'l': T_Char,
    'm': T_Char,
    'n': T_Char,
    'o': T_Char,
    'p': T_Char,
    'q': T_Char,
    'r': T_Char,
    's': T_Char,
    't': T_Char,
    'u': T_Char,
    'v': T_Char,
    'w': T_Char,
    'x': T_Char,
    'y': T_Char,
    'z': T_Char,
    'A': T_Char,
    'B': T_Char,
    'C': T_Char,
    'D': T_Char,
    'E': T_Char,
    'F': T_Char,
    'G': T_Char,
    'H': T_Char,
    'I': T_Char,
    'J': T_Char,
    'K': T_Char,
    'L': T_Char,
    'M': T_Char,
    'N': T_Char,
    'O': T_Char,
    'P': T_Char,
    'Q': T_Char,
    'R': T_Char,
    'S': T_Char,
    'T': T_Char,
    'U': T_Char,
    'V': T_Char,
    'W': T_Char,
    'X': T_Char,
    'Y': T_Char,
    'Z': T_Char,
    '-': T_Char,
    '_': T_Char,
    '/': T_Char,
    '.': T_Char,
    '\\': T_Char,
    '1': T_Int,
    '2': T_Int, 
    '3': T_Int,
    '4': T_Int, 
    '5': T_Int,
    '6': T_Int,
    '7': T_Int,
    '8': T_Int,
    '9': T_Int,
    '0': T_Int,
    '*': T_Wildcard,
    ' ': T_Whitespace,
    ',': T_Comma,
    "(": T_OpenParen,
    ")": T_CloseParen,
    "[": T_OpenBrac,
    "]": T_CloseBrac,
    "{": T_OpenCurl,
    "}": T_CloseCurl,
    "=": T_Equal,
    "&": T_And,
    ';': T_QueryTerminator,
    '~': T_Char,
    None: T_Null,
    T_EOF: T_EOF,
}

# This is a map of words known to the parser/lexer
WORDS = {
    "where": W_Condition,
    "limit": W_Condition,
    "select": W_Command,
    "update": W_Command,
    "show": W_Command
}

# This returns the type of a given word, or generic if it is not defined.
def word_type(word):
    if word.lower() in WORDS:
        return WORDS[word.lower()]
    else:
        return W_Generic

# This returns the type of a given token, but raises an error if this token is not known to the parser/lexer
def token_type(token):
    if token in TOKENS:
        return TOKENS[token]
    else:
        raise TypeError(token)