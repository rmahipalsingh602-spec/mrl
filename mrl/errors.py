from __future__ import annotations

from typing import Sequence


def get_source_line(source_lines: Sequence[str] | None, line: int | None) -> str | None:
    if source_lines is None or line is None:
        return None
    if 1 <= line <= len(source_lines):
        return source_lines[line - 1]
    return None


class MRLError(Exception):
    label = "MRL Error"

    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        column: int | None = None,
        source_lines: Sequence[str] | None = None,
        file_path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
        self.source_lines = source_lines
        self.file_path = file_path

    def __str__(self) -> str:
        location = ""
        if self.file_path and self.line is not None and self.column is not None:
            location = f" at {self.file_path}:{self.line}:{self.column}"
        elif self.file_path and self.line is not None:
            location = f" at {self.file_path}:{self.line}"
        elif self.line is not None and self.column is not None:
            location = f" at line {self.line}, column {self.column}"
        elif self.line is not None:
            location = f" at line {self.line}"
        elif self.file_path:
            location = f" in {self.file_path}"

        lines = [f"{self.label}{location}: {self.message}"]
        source_line = get_source_line(self.source_lines, self.line)
        if source_line is not None:
            lines.append(f"    {source_line}")
            if self.column is not None:
                caret_padding = max(self.column - 1, 0)
                lines.append(f"    {' ' * caret_padding}^")
        return "\n".join(lines)


class LexerError(MRLError):
    label = "Lexer Error"


class ParserError(MRLError):
    label = "Parser Error"


class MRLRuntimeError(MRLError):
    label = "Runtime Error"


class ModuleLoadError(MRLError):
    label = "Import Error"


class MRLFileError(MRLError):
    label = "File Error"
