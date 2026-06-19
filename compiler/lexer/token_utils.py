from enum import Enum, auto


class TokenTypes(Enum):
    """Token types recognised by the lexer."""

    ID = auto()
    NUMBER = auto()
    STRING = auto()
    OP = auto()
    PUNCTUATION = auto()
    WHITESPACEE = auto()


keywords = {
    "func", "assign", "if", "else", "return", "call",
    "gt", "lt", "ge", "le", "eq", "ne", "true", "false",
}


def is_keyword(word: str, keywords: set) -> bool | None:
    if word in keywords:
        return True


class Token(tuple):
    """
    A (type, value) tuple carrying source position.

    Inherits from tuple so Token("ID", "x", 1, 5) == ("ID", "x") is True.
    Position is available via .line and .col attributes.
    """

    def __new__(cls, type: str, value: str, line: int = 0, col: int = 0):
        return super().__new__(cls, (type, value))

    def __init__(self, type: str, value: str, line: int = 0, col: int = 0) -> None:
        self.line = line
        self.col = col

    @property
    def type(self) -> str:
        return self[0]

    @property
    def value(self) -> str:
        return self[1]

    @classmethod
    def from_dfa(
        cls, token_type: str, token_value: str, line: int, col: int
    ) -> "Token | None":
        """
        Build a Token from raw DFA output, or return None for whitespace.

        Keywords, operators, and punctuation are self-typed (type == value).
        All other token types use their DFA token type name.
        """
        if token_type == TokenTypes.WHITESPACEE.name:
            return None
        if (
            (token_type == TokenTypes.ID.name and is_keyword(token_value, keywords))
            or token_type == TokenTypes.OP.name
            or token_type == TokenTypes.PUNCTUATION.name
        ):
            return cls(token_value, token_value, line, col)
        return cls(token_type, token_value, line, col)
