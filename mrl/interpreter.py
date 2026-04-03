from __future__ import annotations

from typing import Any, Sequence

from ai_engine import process_ai_command
from ast_nodes import (
    AICommandNode,
    BinaryOpNode,
    CountedLoopNode,
    FunctionCallNode,
    FunctionDefNode,
    IdentifierNode,
    IfNode,
    ImportNode,
    InstallNode,
    LiteralNode,
    LoopNode,
    PrintNode,
    ProgramNode,
    SourceLocation,
    UIWindowNode,
    UnaryOpNode,
    VariableAssignNode,
)
from environment import Environment
from errors import MRLRuntimeError
from gui_runtime import GUIRuntime
from module_loader import ModuleLoader
from package_manager import PackageManager, PackageManagerError
from runtime import RuntimeContext, UserFunction


class Interpreter:
    def __init__(
        self,
        runtime: RuntimeContext | None = None,
        module_loader: ModuleLoader | None = None,
        package_manager: PackageManager | None = None,
        gui_runtime: GUIRuntime | None = None,
        *,
        source_lines: Sequence[str] | None = None,
        file_path: str | None = None,
    ) -> None:
        self.runtime = runtime if runtime is not None else RuntimeContext()
        self.module_loader = module_loader if module_loader is not None else ModuleLoader()
        self.package_manager = package_manager if package_manager is not None else PackageManager()
        self.gui_runtime = gui_runtime if gui_runtime is not None else GUIRuntime()
        self.environment = self.runtime.global_env
        self.source_lines = tuple(source_lines) if source_lines is not None else None
        self.file_path = file_path

    def interpret(
        self,
        program: ProgramNode,
        *,
        environment: Environment | None = None,
        source_lines: Sequence[str] | None = None,
        file_path: str | None = None,
    ) -> None:
        previous_environment = self.environment
        previous_source_lines = self.source_lines
        previous_file_path = self.file_path

        try:
            if environment is not None:
                self.environment = environment
            if source_lines is not None:
                self.source_lines = tuple(source_lines)
            if file_path is not None:
                self.file_path = file_path
            program.accept(self)
        finally:
            self.environment = previous_environment
            self.source_lines = previous_source_lines
            self.file_path = previous_file_path

    def visit_ProgramNode(self, node: ProgramNode) -> None:
        for statement in node.statements:
            statement.accept(self)

    def visit_PrintNode(self, node: PrintNode) -> None:
        value = node.expression.accept(self)
        self.runtime.write(self.stringify(value))

    def visit_VariableAssignNode(self, node: VariableAssignNode) -> None:
        value = node.expression.accept(self)
        self.environment.assign(node.name, value)

    def visit_IfNode(self, node: IfNode) -> None:
        if self.is_truthy(node.condition.accept(self)):
            block_env = Environment(self.environment, scope_name="if")
            self.execute_block(node.body, block_env)
            return

        if node.else_body is not None:
            block_env = Environment(self.environment, scope_name="else")
            self.execute_block(node.else_body, block_env)

    def visit_LoopNode(self, node: LoopNode) -> None:
        while self.is_truthy(node.condition.accept(self)):
            block_env = Environment(self.environment, scope_name="loop")
            self.execute_block(node.body, block_env)

    def visit_CountedLoopNode(self, node: CountedLoopNode) -> None:
        start = node.start_expression.accept(self)
        end = node.end_expression.accept(self)
        step = node.step_expression.accept(self)

        self.require_integers("counted loop", start, end, node.location)
        if not self.is_integer(step):
            raise self.runtime_error("Counted loop step must be an integer.", node.location)
        if step == 0:
            raise self.runtime_error("Counted loop step cannot be 0.", node.location)

        current = start
        while self.is_counted_loop_value_in_range(current, end, step):
            block_env = Environment(self.environment, scope_name="counted-loop")
            block_env.define(node.variable_name, current)
            self.execute_block(node.body, block_env)
            current += step

    def visit_FunctionDefNode(self, node: FunctionDefNode) -> None:
        function = UserFunction(
            name=node.name,
            parameters=list(node.parameters),
            body=list(node.body),
            closure=self.environment,
            location=node.location,
            file_path=self.file_path,
            source_lines=self.source_lines,
        )
        self.environment.define(node.name, function)

    def visit_FunctionCallNode(self, node: FunctionCallNode) -> None:
        value = self.environment.get(
            node.name,
            location=node.location,
            source_lines=self.source_lines,
            file_path=self.file_path,
        )

        if not isinstance(value, UserFunction):
            raise self.runtime_error(f"'{node.name}' is not a callable function.", node.location)

        if len(node.arguments) != value.arity:
            raise self.runtime_error(
                f"Function '{node.name}' expected {value.arity} argument(s), got {len(node.arguments)}.",
                node.location,
            )

        call_env = Environment(value.closure, scope_name=f"function:{value.name}")
        evaluated_arguments = [argument.accept(self) for argument in node.arguments]
        for parameter, argument_value in zip(value.parameters, evaluated_arguments, strict=True):
            call_env.define(parameter, argument_value)

        self.runtime.push_call(value.name, node.location, self.file_path)
        try:
            self.execute_block(
                value.body,
                call_env,
                source_lines=value.source_lines,
                file_path=value.file_path,
            )
        finally:
            self.runtime.pop_call()

    def visit_ImportNode(self, node: ImportNode) -> None:
        self.module_loader.load_module(
            node.module_name,
            interpreter=self,
            target_environment=self.environment,
            location=node.location,
            source_lines=self.source_lines,
            current_file_path=self.file_path,
        )

    def visit_InstallNode(self, node: InstallNode) -> None:
        try:
            record = self.package_manager.install_package(node.package_name)
        except PackageManagerError as exc:
            raise self.runtime_error(str(exc), node.location) from exc

        self.runtime.write(f"[package] Installed '{record.name}' at {record.entrypoint}")

    def visit_AICommandNode(self, node: AICommandNode) -> None:
        self.runtime.write(process_ai_command(node.prompt))

    def visit_UIWindowNode(self, node: UIWindowNode) -> None:
        definition = self.gui_runtime.definition_from_model(
            {
                "title": node.title,
                "elements": [
                    {"kind": "button", "text": element.label} if hasattr(element, "label") else {"kind": "text", "text": element.value}
                    for element in node.elements
                ],
            }
        )
        preview = self.gui_runtime.render_definition(definition, run_mainloop=self.runtime.target == "app")
        if self.runtime.target != "app" or self.gui_runtime.headless:
            self.runtime.write(preview)

    def visit_LiteralNode(self, node: LiteralNode) -> Any:
        return node.value

    def visit_IdentifierNode(self, node: IdentifierNode) -> Any:
        return self.environment.get(
            node.name,
            location=node.location,
            source_lines=self.source_lines,
            file_path=self.file_path,
        )

    def visit_UnaryOpNode(self, node: UnaryOpNode) -> Any:
        operand = node.operand.accept(self)

        if node.operator == "-":
            if self.is_integer(operand):
                return -operand
            raise self.runtime_error("Unary '-' requires an integer operand.", node.location)

        if node.operator == "nahi":
            return not self.is_truthy(operand)

        raise self.runtime_error(f"Unsupported unary operator '{node.operator}'.", node.location)

    def visit_BinaryOpNode(self, node: BinaryOpNode) -> Any:
        left = node.left.accept(self)
        right = node.right.accept(self)
        operator = node.operator

        if operator == "+":
            if isinstance(left, str) or isinstance(right, str):
                return f"{self.stringify(left)}{self.stringify(right)}"
            if self.is_integer(left) and self.is_integer(right):
                return left + right
            raise self.runtime_error("Operator '+' supports integers or string concatenation.", node.location)

        if operator == "-":
            self.require_integers(operator, left, right, node.location)
            return left - right

        if operator == "*":
            self.require_integers(operator, left, right, node.location)
            return left * right

        if operator == "/":
            self.require_integers(operator, left, right, node.location)
            if right == 0:
                raise self.runtime_error("Division by zero is not allowed.", node.location)
            return left // right

        if operator == "aur":
            return self.is_truthy(left) and self.is_truthy(right)

        if operator == "ya":
            return self.is_truthy(left) or self.is_truthy(right)

        if operator == "==":
            return left == right

        if operator == "!=":
            return left != right

        if operator in (">", ">=", "<", "<="):
            if (self.is_integer(left) and self.is_integer(right)) or (
                isinstance(left, str) and isinstance(right, str)
            ):
                if operator == ">":
                    return left > right
                if operator == ">=":
                    return left >= right
                if operator == "<":
                    return left < right
                return left <= right
            raise self.runtime_error(
                f"Operator '{operator}' requires two integers or two strings.",
                node.location,
            )

        raise self.runtime_error(f"Unsupported operator '{operator}'.", node.location)

    def execute_block(
        self,
        statements: Sequence[Any],
        environment: Environment,
        *,
        source_lines: Sequence[str] | None = None,
        file_path: str | None = None,
    ) -> None:
        previous_environment = self.environment
        previous_source_lines = self.source_lines
        previous_file_path = self.file_path

        try:
            self.environment = environment
            if source_lines is not None:
                self.source_lines = tuple(source_lines)
            if file_path is not None:
                self.file_path = file_path
            for statement in statements:
                statement.accept(self)
        finally:
            self.environment = previous_environment
            self.source_lines = previous_source_lines
            self.file_path = previous_file_path

    def require_integers(self, operator: str, left: Any, right: Any, location: SourceLocation) -> None:
        if self.is_integer(left) and self.is_integer(right):
            return
        raise self.runtime_error(f"Operator '{operator}' requires integer operands.", location)

    def is_integer(self, value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def is_truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if self.is_integer(value):
            return value != 0
        if isinstance(value, str):
            return value != ""
        return bool(value)

    def stringify(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, UserFunction):
            return f"<function {value.name}>"
        return str(value)

    def is_counted_loop_value_in_range(self, value: int, end: int, step: int) -> bool:
        if step > 0:
            return value <= end
        return value >= end

    def runtime_error(self, message: str, location: SourceLocation | None = None) -> MRLRuntimeError:
        stack_trace = self.runtime.format_call_stack()
        if stack_trace:
            message = f"{message}\n{stack_trace}"

        return MRLRuntimeError(
            message,
            line=location.line if location is not None else None,
            column=location.column if location is not None else None,
            source_lines=self.source_lines,
            file_path=self.file_path,
        )
