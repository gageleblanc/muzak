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

class T_EOF(MQLParserToken):
    pass

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

class MQLCollectionType:
    pass

class C_List(MQLCollectionType):
    pass

class C_Target(MQLCollectionType):
    pass

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
    None: T_Null,
    T_EOF: T_EOF,
}

WORDS = {
    "where": W_Condition,
    "limit": W_Condition,
    "select": W_Command,
    "show": W_Command
}

def word_type(word):
    if word in WORDS:
        return WORDS[word]
    else:
        return W_Generic

def token_type(token):
    if token in TOKENS:
        return TOKENS[token]
    else:
        raise TypeError(token)