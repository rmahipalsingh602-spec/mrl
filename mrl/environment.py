from __future__ import annotations

from typing import Any, Sequence

from ast_nodes import SourceLocation
from errors import MRLRuntimeError


class Environment:
    def __init__(self, parent: "Environment | None" = None, *, scope_name: str = "scope") -> None:
        self.parent = parent
        self.scope_name = scope_name
        self.values: dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def resolve(self, name: str) -> "Environment | None":
        if name in self.values:
            return self
        if self.parent is not None:
            return self.parent.resolve(name)
        return None

    def assign(self, name: str, value: Any) -> None:
        scope = self.resolve(name)
        if scope is None:
            self.values[name] = value
            return
        scope.values[name] = value

    def get(
        self,
        name: str,
        *,
        location: SourceLocation | None = None,
        source_lines: Sequence[str] | None = None,
        file_path: str | None = None,
    ) -> Any:
        scope = self.resolve(name)
        if scope is not None:
            return scope.values[name]

        line = location.line if location is not None else None
        column = location.column if location is not None else None
        raise MRLRuntimeError(
            f"Undefined variable or function '{name}'.",
            line=line,
            column=column,
            source_lines=source_lines,
            file_path=file_path,
        )

    def bindings(self) -> dict[str, Any]:
        return dict(self.values)

    def snapshot(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        if self.parent is not None:
            merged.update(self.parent.snapshot())
        merged.update(self.values)
        return merged
