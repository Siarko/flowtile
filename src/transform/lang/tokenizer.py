from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    NUMBER_INT = auto()
    NUMBER_FLOAT = auto()
    STRING = auto()
    BOOL = auto()

    IDENTIFIER = auto()
    KEYWORD_IF = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    COMMA = auto()

    OPERATOR_LAST_CONDITION = auto()

    OPERATOR_EQUAL = auto()
    OPERATOR_NOT_EQUAL = auto()
    OPERATOR_GREATER_THAN = auto()
    OPERATOR_GREATER_EQUAL_THAN = auto()
    OPERATOR_LESS_THAN = auto()
    OPERATOR_LESS_EQUAL_THAN = auto()
    OPERATOR_NOT = auto()
    OPERATOR_LOGIC_AND = auto()
    OPERATOR_LOGIC_OR = auto()

    OPERATOR_NEGATIVE = auto()
    OPERATOR_ADD = auto()
    OPERATOR_SUBTRACT = auto()
    OPERATOR_MULTIPLY = auto()
    OPERATOR_DIVIDE = auto()
    OPERATOR_POWER = auto()
    OPERATOR_MODULO = auto()

    OPERATOR_CONCAT = auto()

    END = auto()

@dataclass(frozen=True)
class Token:
    type: TokenType
    value: Any
    declaration_position: tuple[int, int]

class TokenizeError(Exception):
    def __init__(self, message: str, position: int):
        super().__init__(message)
        self.message = message
        self.position = position
        self.line: int | None = None

KEYWORDS = {"if": TokenType.KEYWORD_IF}
BOOL_LITERALS = {"true": True, "false": False}
UNARY_CONTEXT = {
    TokenType.LEFT_PAREN, TokenType.LEFT_BRACKET, TokenType.COMMA,
    TokenType.OPERATOR_ADD, TokenType.OPERATOR_SUBTRACT, TokenType.OPERATOR_NEGATIVE,
    TokenType.OPERATOR_MULTIPLY, TokenType.OPERATOR_DIVIDE, TokenType.OPERATOR_MODULO, TokenType.OPERATOR_POWER,
    TokenType.OPERATOR_EQUAL, TokenType.OPERATOR_NOT_EQUAL, TokenType.OPERATOR_GREATER_THAN,
    TokenType.OPERATOR_GREATER_EQUAL_THAN, TokenType.OPERATOR_LESS_THAN, TokenType.OPERATOR_LESS_EQUAL_THAN,
    TokenType.KEYWORD_IF, TokenType.OPERATOR_NOT
}

THREE_CHAR_TOKENS = {
    "...": TokenType.OPERATOR_LAST_CONDITION
}

TWO_CHAR_TOKENS = {
    "==": TokenType.OPERATOR_EQUAL,
    "~=": TokenType.OPERATOR_NOT_EQUAL,
    ">=": TokenType.OPERATOR_GREATER_EQUAL_THAN,
    "<=": TokenType.OPERATOR_LESS_EQUAL_THAN,
    "&&": TokenType.OPERATOR_LOGIC_AND,
    "||": TokenType.OPERATOR_LOGIC_OR,
    "..": TokenType.OPERATOR_CONCAT
}
SINGLE_CHAR_TOKENS = {
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "[": TokenType.LEFT_BRACKET,
    "]": TokenType.RIGHT_BRACKET,
    ",": TokenType.COMMA,
    ">": TokenType.OPERATOR_GREATER_THAN,
    "<": TokenType.OPERATOR_LESS_THAN,
    "+": TokenType.OPERATOR_ADD,
    "-": TokenType.OPERATOR_SUBTRACT,
    "*": TokenType.OPERATOR_MULTIPLY,
    "/": TokenType.OPERATOR_DIVIDE,
    "%": TokenType.OPERATOR_MODULO,
    "^": TokenType.OPERATOR_POWER,
    "~": TokenType.OPERATOR_NOT,
}

ESCAPE_SEQUENCES = {"n": "\n", "\\": "\\", '"': '"'}
def _tokenize_literal(line: str, position: int, _) -> tuple[int, Token | None]:
    if line[position] != "\"":
        return position, None
    length = len(line)
    start = position
    position += 1
    buffer = []
    while position < length and line[position] != "\"":
        if line[position] == "\\" and position + 1 < length:
            escaped_char = line[position + 1]
            if escaped_char not in ESCAPE_SEQUENCES:
                raise TokenizeError(f"Unknown escape sequence '\\{escaped_char}'", position)
            buffer.append(ESCAPE_SEQUENCES[escaped_char])
            position += 2
        else:
            buffer.append(line[position])
            position += 1
    if position >= length:
        raise TokenizeError("String literal is not closed", start)
    position += 1
    return position, Token(TokenType.STRING, "".join(buffer), (start, position))

def _tokenize_number(line: str, position: int, _) -> tuple[int, Token | None]:
    if not line[position].isdigit():
        return position, None
    length = len(line)
    start = position
    while position < length and line[position].isdigit():
        position += 1
    is_decimal_point = (
        position < length and line[position] == "."
        and not (position + 1 < length and line[position + 1] == ".")
    )
    if is_decimal_point:
        position += 1
        if position >= length or not line[position].isdigit():
            raise TokenizeError(f"Number expected after '.' in float definition", position)
        while position < length and line[position].isdigit():
            position += 1
        token = Token(TokenType.NUMBER_FLOAT, float(line[start:position]), (start, position))
    else:
        token = Token(TokenType.NUMBER_INT, int(line[start:position]), (start, position))
    if position < length and (line[position].isalpha() or line[position] == "_"):
        raise TokenizeError("Invalid number literal: letter immediately follows digits", position)
    return position, token

def _tokenize_keywords(line: str, position: int, _) -> tuple[int, Token | None]:
    if not line[position].isalpha() and not line[position] == "_":
        return position, None
    length = len(line)
    start = position
    while position < length and (line[position].isalnum() or line[position] == "_"):
        position += 1
    word = line[start:position]
    if word in KEYWORDS:
        token = Token(KEYWORDS[word], None, (start, position))
    elif word in BOOL_LITERALS:
        token = Token(TokenType.BOOL, BOOL_LITERALS[word], (start, position))
    else:
        token = Token(TokenType.IDENTIFIER, word, (start, position))
    return position, token

def _tokenize_symbols(line: str, position: int, previous_token: Token | None) -> tuple[int, Token | None]:
    length = len(line)
    if position + 3 <= length:
        three_chars = line[position:position + 3]
        operator = THREE_CHAR_TOKENS.get(three_chars, None)
        if operator is not None:
            return position + 3, Token(operator, None, (position, position + 3))
    if position + 2 <= length:
        two_chars = line[position:position + 2]
        operator = TWO_CHAR_TOKENS.get(two_chars, None)
        if operator is not None:
            return position+2, Token(operator, None, (position, position+2))
    operator = SINGLE_CHAR_TOKENS.get(line[position], None)
    if operator is None:
        raise TokenizeError(f"Unexpected token \"{line[position]}\"", position)
    if operator == TokenType.OPERATOR_SUBTRACT and (previous_token is None or previous_token.type in UNARY_CONTEXT):
        token = Token(TokenType.OPERATOR_NEGATIVE, None, (position, position+1))
    else:
        token = Token(operator, None, (position, position+1))
    position += 1
    return position, token


_tokenizers = [
    _tokenize_literal,
    _tokenize_number,
    _tokenize_keywords,
    _tokenize_symbols
]

def _call_tokenizers(line: str, position: int, previous_token: Token | None = None) -> tuple[int, Token]:
    for tokenizer in _tokenizers:
        new_position, token = tokenizer(line, position, previous_token)
        if token is not None:
            return new_position, token

    # Just in case tokenizers change, currently _tokenize_symbols do the same
    raise TokenizeError("Unexpected token", position)


def tokenize(line: str) -> list[Token]:
    tokens = []
    position = 0
    previous_token: Token | None = None
    length = len(line)
    while position < length:
        char = line[position]
        if char.isspace():
            position += 1
            continue

        position, token = _call_tokenizers(line, position, previous_token)
        tokens.append(token)
        previous_token = token
    tokens.append(Token(TokenType.END, None, (length, length)))
    return tokens