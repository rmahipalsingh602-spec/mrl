from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ast_nodes import SourceLocation
from environment import Environment

MRL_LOGO = r"""
 __  __ ____  _      
|  \/  |  _ \| |     
| |\/| | |_) | |     
| |  | |  _ <| |___  
|_|  |_|_| \_\_____| 
Neon Tri-Core :: Multi Runtime Language
""".strip("\n")


@dataclass(slots=True)
class CallFrame:
    name: str
    location: SourceLocation
    file_path: str | None = None

    def describe(self) -> str:
        if self.file_path is not None:
            return f"{self.name} @ {self.file_path}:{self.location.line}:{self.location.column}"
        return f"{self.name} @ line {self.location.line}, column {self.location.column}"


@dataclass(slots=True)
class UserFunction:
    name: str
    parameters: list[str]
    body: list[Any]
    closure: Environment
    location: SourceLocation
    file_path: str | None = None
    source_lines: tuple[str, ...] | None = None

    @property
    def arity(self) -> int:
        return len(self.parameters)


class RuntimeContext:
    def __init__(
        self,
        *,
        target: str = "native",
        output_stream: Any = None,
        project_root: Path | str | None = None,
        jit_enabled: bool = True,
    ) -> None:
        self.target = target
        self.output_stream = output_stream if output_stream is not None else sys.stdout
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.jit_enabled = jit_enabled
        self.global_env = Environment(scope_name=f"global:{target}")
        self.call_stack: list[CallFrame] = []
        self.optimization_events: list[str] = []

    def write(self, value: str) -> None:
        print(value, file=self.output_stream)

    def push_call(self, name: str, location: SourceLocation, file_path: str | None = None) -> None:
        self.call_stack.append(CallFrame(name=name, location=location, file_path=file_path))

    def pop_call(self) -> None:
        if self.call_stack:
            self.call_stack.pop()

    def format_call_stack(self) -> str:
        if not self.call_stack:
            return ""

        lines = ["Call stack:"]
        for frame in reversed(self.call_stack):
            lines.append(f"  {frame.describe()}")
        return "\n".join(lines)

    def record_optimization(self, message: str) -> None:
        self.optimization_events.append(message)


def render_logo() -> str:
    return MRL_LOGO