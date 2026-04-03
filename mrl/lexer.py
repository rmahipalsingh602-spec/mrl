from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from errors import LexerError


class TokenType(Enum):
    MRL = auto()
    BOLO = auto()
    RAKHO = auto()
    AGAR = auto()
    WARNA = auto()
    JAB = auto()
    TAK = auto()
    GINO = auto()
    SE = auto()
    KADAM = auto()
    KHATAM = auto()
    FUNCTION = auto()
    CALL = auto()
    IMPORT = auto()
    INSTALL = auto()
    AI = auto()
    UI = auto()
    SACH = auto()
    JHOOTH = auto()
    AUR = auto()
    YA = auto()
    NAHI = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    BANG_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    lexeme: str
    literal: Any
    line: int
    column: int


KEYWORDS = {
    "mrl": TokenType.MRL,
    "bolo": TokenType.BOLO,
    "rakho": TokenType.RAKHO,
    "agar": TokenType.AGAR,
    "warna": TokenType.WARNA,
    "jab": TokenType.JAB,
    "tak": TokenType.TAK,
    "gino": TokenType.GINO,
    "se": TokenType.SE,
    "kadam": TokenType.KADAM,
    "khatam": TokenType.KHATAM,
    "function": TokenType.FUNCTION,
    "call": TokenType.CALL,
    "import": TokenType.IMPORT,
    "install": TokenType.INSTALL,
    "ai": TokenType.AI,
    "ui": TokenType.UI,
    "sach": TokenType.SACH,
    "jhooth": TokenType.JHOOTH,
    "aur": TokenType.AUR,
    "ya": TokenType.YA,
    "nahi": TokenType.NAHI,
}


class Lexer:
    def __init__(self, source: str, *, file_path: str | None = None) -> None:
        self.source = source
        self.source_lines = source.splitlines()
        self.file_path = file_path
        self.tokens: list[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        while not self.is_at_end():
            self.start = self.current
            start_line = self.line
            start_column = self.column
            self.scan_token(start_line, start_column)

        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens

    def scan_token(self, start_line: int, start_column: int) -> None:
        char = self.advance()

        if char in (" ", "\r", "\t", "\ufeff"):
            return
        if char == "\n":
            self.add_token(TokenType.NEWLINE, start_line, start_column)
            return
        if char == "#":
            self.skip_comment()
            return
        if char == "(":
            self.add_token(TokenType.LPAREN, start_line, start_column)
            return
        if char == ")":
            self.add_token(TokenType.RPAREN, start_line, start_column)
            return
        if char == ",":
            self.add_token(TokenType.COMMA, start_line, start_column)
            return
        if char == "+":
            self.add_token(TokenType.PLUS, start_line, start_column)
            return
        if char == "-":
            self.add_token(TokenType.MINUS, start_line, start_column)
            return
        if char == "*":
            self.add_token(TokenType.STAR, start_line, start_column)
            return
        if char == "/":
            self.add_token(TokenType.SLASH, start_line, start_column)
            return
        if char == "=":
            token_type = TokenType.EQUAL_EQUAL if self.match("=") else TokenType.EQUAL
            self.add_token(token_type, start_line, start_column)
            return
        if char == "!":
            if self.match("="):
                self.add_token(TokenType.BANG_EQUAL, start_line, start_column)
                return
            self.raise_error("Unexpected '!'. Use '!=' for comparison.", start_line, start_column)
        if char == ">":
            token_type = TokenType.GREATER_EQUAL if self.match("=") else TokenType.GREATER
            self.add_token(token_type, start_line, start_column)
            return
        if char == "<":
            token_type = TokenType.LESS_EQUAL if self.match("=") else TokenType.LESS
            self.add_token(token_type, start_line, start_column)
            return
        if char in ('"', "'"):
            self.read_string(char, start_line, start_column)
            return
        if char.isdigit():
            self.read_number(start_line, start_column)
            return
        if self.is_identifier_start(char):
            self.read_identifier(start_line, start_column)
            return

        self.raise_error(f"Unexpected character '{char}'.", start_line, start_column)

    def read_string(self, quote_char: str, start_line: int, start_column: int) -> None:
        characters: list[str] = []

        while not self.is_at_end():
            char = self.advance()

            if char == quote_char:
                lexeme = self.source[self.start : self.current]
                self.tokens.append(Token(TokenType.STRING, lexeme, "".join(characters), start_line, start_column))
                return

            if char == "\\":
                if self.is_at_end():
                    self.raise_error("Unterminated string literal.", start_line, start_column)
                escaped = self.advance()
                escape_map = {
                    "n": "\n",
                    "t": "\t",
                    '"': '"',
                    "'": "'",
                    "\\": "\\",
                }
                if escaped not in escape_map:
                    self.raise_error(
                        f"Unsupported escape sequence '\\{escaped}'.",
                        self.line,
                        max(self.column - 1, 1),
                    )
                characters.append(escape_map[escaped])
                continue

            if char == "\n":
                self.raise_error("Unterminated string literal.", start_line, start_column)

            characters.append(char)

        self.raise_error("Unterminated string literal.", start_line, start_column)

    def read_number(self, start_line: int, start_column: int) -> None:
        while self.peek().isdigit():
            self.advance()

        lexeme = self.source[self.start : self.current]
        self.tokens.append(Token(TokenType.NUMBER, lexeme, int(lexeme), start_line, start_column))

    def read_identifier(self, start_line: int, start_column: int) -> None:
        while self.is_identifier_part(self.peek()):
            self.advance()

        lexeme = self.source[self.start : self.current]
        token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        literal = lexeme if token_type is TokenType.IDENTIFIER else None
        self.tokens.append(Token(token_type, lexeme, literal, start_line, start_column))

    def skip_comment(self) -> None:
        while not self.is_at_end() and self.peek() != "\n":
            self.advance()

    def add_token(self, token_type: TokenType, line: int, column: int, literal: Any = None) -> None:
        lexeme = self.source[self.start : self.current]
        self.tokens.append(Token(token_type, lexeme, literal, line, column))

    def is_identifier_start(self, char: str) -> bool:
        return char.isalpha() or char == "_"

    def is_identifier_part(self, char: str) -> bool:
        return char.isalnum() or char == "_"

    def advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def match(self, expected: str) -> bool:
        if self.is_at_end() or self.source[self.current] != expected:
            return False
        self.advance()
        return True

    def peek(self) -> str:
        if self.is_at_end():
            return "\0"
        return self.source[self.current]

    def is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def raise_error(self, message: str, line: int, column: int) -> None:
        raise LexerError(
            message,
            line=line,
            column=column,
            source_lines=self.source_lines,
            file_path=self.file_path,
        )
