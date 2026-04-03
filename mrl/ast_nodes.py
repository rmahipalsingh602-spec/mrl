from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceLocation:
    line: int
    column: int


@dataclass(slots=True)
class Node:
    location: SourceLocation

    def accept(self, visitor: Any) -> Any:
        method_name = f"visit_{self.__class__.__name__}"
        method = getattr(visitor, method_name, None)
        if method is None:
            raise AttributeError(f"{visitor.__class__.__name__} does not implement {method_name}()")
        return method(self)


@dataclass(slots=True)
class ProgramNode(Node):
    statements: list["StatementNode"]


@dataclass(slots=True)
class PrintNode(Node):
    expression: "ExpressionNode"


@dataclass(slots=True)
class VariableAssignNode(Node):
    name: str
    expression: "ExpressionNode"


@dataclass(slots=True)
class IfNode(Node):
    condition: "ExpressionNode"
    body: list["StatementNode"]
    else_body: list["StatementNode"] | None = None


@dataclass(slots=True)
class LoopNode(Node):
    condition: "ExpressionNode"
    body: list["StatementNode"]


@dataclass(slots=True)
class CountedLoopNode(Node):
    variable_name: str
    start_expression: "ExpressionNode"
    end_expression: "ExpressionNode"
    step_expression: "ExpressionNode"
    body: list["StatementNode"]


@dataclass(slots=True)
class FunctionDefNode(Node):
    name: str
    parameters: list[str]
    body: list["StatementNode"]


@dataclass(slots=True)
class FunctionCallNode(Node):
    name: str
    arguments: list["ExpressionNode"]


@dataclass(slots=True)
class ImportNode(Node):
    module_name: str


@dataclass(slots=True)
class InstallNode(Node):
    package_name: str


@dataclass(slots=True)
class AICommandNode(Node):
    prompt: str


@dataclass(slots=True)
class UIButtonNode(Node):
    label: str


@dataclass(slots=True)
class UITextNode(Node):
    value: str


@dataclass(slots=True)
class UIWindowNode(Node):
    title: str
    elements: list["UIElementNode"]


@dataclass(slots=True)
class LiteralNode(Node):
    value: Any


@dataclass(slots=True)
class IdentifierNode(Node):
    name: str


@dataclass(slots=True)
class UnaryOpNode(Node):
    operator: str
    operand: "ExpressionNode"


@dataclass(slots=True)
class BinaryOpNode(Node):
    left: "ExpressionNode"
    operator: str
    right: "ExpressionNode"


UIElementNode = UIButtonNode | UITextNode
ExpressionNode = LiteralNode | IdentifierNode | UnaryOpNode | BinaryOpNode
StatementNode = (
    PrintNode
    | VariableAssignNode
    | IfNode
    | LoopNode
    | CountedLoopNode
    | FunctionDefNode
    | FunctionCallNode
    | ImportNode
    | InstallNode
    | AICommandNode
    | UIWindowNode
)
