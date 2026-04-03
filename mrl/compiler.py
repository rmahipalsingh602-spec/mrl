from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

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
    UIButtonNode,
    UITextNode,
    UIWindowNode,
    UnaryOpNode,
    VariableAssignNode,
)


class Opcode(str, Enum):
    LOAD_CONST = "LOAD_CONST"
    LOAD_VAR = "LOAD_VAR"
    STORE_VAR = "STORE_VAR"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    PRINT = "PRINT"
    JUMP = "JUMP"
    JUMP_IF_FALSE = "JUMP_IF_FALSE"
    CALL_FUNCTION = "CALL_FUNCTION"
    RETURN = "RETURN"
    COMPARE_EQ = "COMPARE_EQ"
    COMPARE_NE = "COMPARE_NE"
    COMPARE_GT = "COMPARE_GT"
    COMPARE_GTE = "COMPARE_GTE"
    COMPARE_LT = "COMPARE_LT"
    COMPARE_LTE = "COMPARE_LTE"
    DEFINE_FUNCTION = "DEFINE_FUNCTION"
    IMPORT_MODULE = "IMPORT_MODULE"
    INSTALL_PACKAGE = "INSTALL_PACKAGE"
    AI_COMMAND = "AI_COMMAND"
    BUILD_UI = "BUILD_UI"
    SETUP_COUNTED_LOOP = "SETUP_COUNTED_LOOP"
    COUNTED_LOOP_NEXT = "COUNTED_LOOP_NEXT"
    POP = "POP"


@dataclass(frozen=True, slots=True)
class Instruction:
    opcode: Opcode
    operand: Any = None
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class CallSpec:
    name: str
    arg_count: int


@dataclass(frozen=True, slots=True)
class FunctionPrototype:
    name: str
    parameters: list[str]
    program: "BytecodeProgram"
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class LoopDescriptor:
    loop_id: int
    condition_start: int
    condition_end: int
    body_start: int
    body_end: int
    back_jump_ip: int
    exit_target: int
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class CountedLoopSetupSpec:
    loop_id: int
    variable_name: str
    exit_target: int | None = None


@dataclass(frozen=True, slots=True)
class CountedLoopNextSpec:
    loop_id: int
    variable_name: str
    body_start: int


@dataclass(slots=True)
class BytecodeProgram:
    name: str
    instructions: list[Instruction]
    file_path: str | None = None
    source_lines: tuple[str, ...] | None = None
    loop_descriptors: list[LoopDescriptor] = field(default_factory=list)
    loop_by_start: dict[int, LoopDescriptor] = field(init=False, default_factory=dict)
    loop_by_back_jump: dict[int, LoopDescriptor] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        if self.source_lines is not None and not isinstance(self.source_lines, tuple):
            self.source_lines = tuple(self.source_lines)
        self.rebuild_metadata()

    def rebuild_metadata(self) -> None:
        self.loop_by_start = {descriptor.condition_start: descriptor for descriptor in self.loop_descriptors}
        self.loop_by_back_jump = {descriptor.back_jump_ip: descriptor for descriptor in self.loop_descriptors}


class BytecodeCompiler:
    def __init__(
        self,
        *,
        file_path: str | None = None,
        source_lines: tuple[str, ...] | list[str] | None = None,
        program_name: str = "<module>",
    ) -> None:
        self.file_path = file_path
        self.source_lines = tuple(source_lines) if source_lines is not None else None
        self.program_name = program_name
        self.instructions: list[Instruction] = []
        self.loop_descriptors: list[LoopDescriptor] = []
        self._next_loop_id = 1

    def compile(self, program: ProgramNode) -> BytecodeProgram:
        for statement in program.statements:
            self.compile_statement(statement)
        self.emit(Opcode.LOAD_CONST, None, program.location)
        self.emit(Opcode.RETURN, None, program.location)
        return BytecodeProgram(
            name=self.program_name,
            instructions=list(self.instructions),
            file_path=self.file_path,
            source_lines=self.source_lines,
            loop_descriptors=list(self.loop_descriptors),
        )

    def compile_statement(self, node: Any) -> None:
        if isinstance(node, PrintNode):
            self.compile_expression(node.expression)
            self.emit(Opcode.PRINT, location=node.location)
            return

        if isinstance(node, VariableAssignNode):
            self.compile_expression(node.expression)
            self.emit(Opcode.STORE_VAR, node.name, node.location)
            return

        if isinstance(node, IfNode):
            self.compile_expression(node.condition)
            jump_false = self.emit(Opcode.JUMP_IF_FALSE, None, node.location)
            for statement in node.body:
                self.compile_statement(statement)

            if node.else_body:
                jump_end = self.emit(Opcode.JUMP, None, node.location)
                self.patch(jump_false, len(self.instructions))
                for statement in node.else_body:
                    self.compile_statement(statement)
                self.patch(jump_end, len(self.instructions))
            else:
                self.patch(jump_false, len(self.instructions))
            return

        if isinstance(node, LoopNode):
            loop_id = self.allocate_loop_id()
            condition_start = len(self.instructions)
            self.compile_expression(node.condition)
            condition_end = len(self.instructions)
            jump_false = self.emit(Opcode.JUMP_IF_FALSE, None, node.location)
            body_start = len(self.instructions)
            for statement in node.body:
                self.compile_statement(statement)
            body_end = len(self.instructions)
            back_jump_ip = self.emit(Opcode.JUMP, condition_start, node.location)
            exit_target = len(self.instructions)
            self.patch(jump_false, exit_target)
            self.loop_descriptors.append(
                LoopDescriptor(
                    loop_id=loop_id,
                    condition_start=condition_start,
                    condition_end=condition_end,
                    body_start=body_start,
                    body_end=body_end,
                    back_jump_ip=back_jump_ip,
                    exit_target=exit_target,
                    location=node.location,
                )
            )
            return

        if isinstance(node, CountedLoopNode):
            loop_id = self.allocate_loop_id()
            self.compile_expression(node.start_expression)
            self.compile_expression(node.end_expression)
            self.compile_expression(node.step_expression)
            setup_index = self.emit(
                Opcode.SETUP_COUNTED_LOOP,
                CountedLoopSetupSpec(loop_id=loop_id, variable_name=node.variable_name, exit_target=None),
                node.location,
            )
            body_start = len(self.instructions)
            for statement in node.body:
                self.compile_statement(statement)
            next_index = self.emit(
                Opcode.COUNTED_LOOP_NEXT,
                CountedLoopNextSpec(loop_id=loop_id, variable_name=node.variable_name, body_start=body_start),
                node.location,
            )
            exit_target = len(self.instructions)
            self.patch(
                setup_index,
                CountedLoopSetupSpec(loop_id=loop_id, variable_name=node.variable_name, exit_target=exit_target),
            )
            self.loop_descriptors.append(
                LoopDescriptor(
                    loop_id=loop_id,
                    condition_start=setup_index,
                    condition_end=body_start,
                    body_start=body_start,
                    body_end=next_index,
                    back_jump_ip=next_index,
                    exit_target=exit_target,
                    location=node.location,
                )
            )
            return

        if isinstance(node, FunctionDefNode):
            child = BytecodeCompiler(
                file_path=self.file_path,
                source_lines=self.source_lines,
                program_name=node.name,
            )
            for statement in node.body:
                child.compile_statement(statement)
            child.emit(Opcode.LOAD_CONST, None, node.location)
            child.emit(Opcode.RETURN, None, node.location)
            prototype = FunctionPrototype(
                name=node.name,
                parameters=list(node.parameters),
                program=BytecodeProgram(
                    name=node.name,
                    instructions=list(child.instructions),
                    file_path=self.file_path,
                    source_lines=self.source_lines,
                    loop_descriptors=list(child.loop_descriptors),
                ),
                location=node.location,
            )
            self.emit(Opcode.DEFINE_FUNCTION, prototype, node.location)
            return

        if isinstance(node, FunctionCallNode):
            for argument in node.arguments:
                self.compile_expression(argument)
            self.emit(
                Opcode.CALL_FUNCTION,
                CallSpec(name=node.name, arg_count=len(node.arguments)),
                node.location,
            )
            self.emit(Opcode.POP, location=node.location)
            return

        if isinstance(node, ImportNode):
            self.emit(Opcode.IMPORT_MODULE, node.module_name, node.location)
            return

        if isinstance(node, InstallNode):
            self.emit(Opcode.INSTALL_PACKAGE, node.package_name, node.location)
            return

        if isinstance(node, AICommandNode):
            self.emit(Opcode.AI_COMMAND, node.prompt, node.location)
            return

        if isinstance(node, UIWindowNode):
            self.emit(Opcode.BUILD_UI, self.build_ui_definition(node), node.location)
            return

        raise TypeError(f"Unsupported statement node: {node.__class__.__name__}")

    def compile_expression(self, node: Any) -> None:
        if isinstance(node, LiteralNode):
            self.emit(Opcode.LOAD_CONST, node.value, node.location)
            return

        if isinstance(node, IdentifierNode):
            self.emit(Opcode.LOAD_VAR, node.name, node.location)
            return

        if isinstance(node, UnaryOpNode):
            if node.operator == "nahi":
                self.compile_expression(node.operand)
                self.emit(Opcode.NOT, location=node.location)
                return

            if node.operator != "-":
                raise ValueError(f"Unsupported unary operator {node.operator!r}")
            self.emit(Opcode.LOAD_CONST, 0, node.location)
            self.compile_expression(node.operand)
            self.emit(Opcode.SUB, location=node.location)
            return

        if isinstance(node, BinaryOpNode):
            self.compile_expression(node.left)
            self.compile_expression(node.right)
            opcode = {
                "+": Opcode.ADD,
                "-": Opcode.SUB,
                "*": Opcode.MUL,
                "/": Opcode.DIV,
                "aur": Opcode.AND,
                "ya": Opcode.OR,
                "==": Opcode.COMPARE_EQ,
                "!=": Opcode.COMPARE_NE,
                ">": Opcode.COMPARE_GT,
                ">=": Opcode.COMPARE_GTE,
                "<": Opcode.COMPARE_LT,
                "<=": Opcode.COMPARE_LTE,
            }.get(node.operator)
            if opcode is None:
                raise ValueError(f"Unsupported binary operator {node.operator!r}")
            self.emit(opcode, location=node.location)
            return

        raise TypeError(f"Unsupported expression node: {node.__class__.__name__}")

    def emit(self, opcode: Opcode, operand: Any = None, location: SourceLocation | None = None) -> int:
        instruction = Instruction(opcode=opcode, operand=operand, location=location)
        self.instructions.append(instruction)
        return len(self.instructions) - 1

    def patch(self, index: int, operand: Any) -> None:
        instruction = self.instructions[index]
        self.instructions[index] = Instruction(
            opcode=instruction.opcode,
            operand=operand,
            location=instruction.location,
        )

    def allocate_loop_id(self) -> int:
        loop_id = self._next_loop_id
        self._next_loop_id += 1
        return loop_id

    def build_ui_definition(self, node: UIWindowNode) -> dict[str, Any]:
        elements: list[dict[str, str]] = []
        for element in node.elements:
            if isinstance(element, UIButtonNode):
                elements.append({"kind": "button", "text": element.label})
            elif isinstance(element, UITextNode):
                elements.append({"kind": "text", "text": element.value})
            else:
                raise TypeError(f"Unsupported ui element: {element.__class__.__name__}")
        return {"title": node.title, "elements": elements}


def disassemble(program: BytecodeProgram, *, indent: int = 0) -> str:
    prefix = " " * indent
    lines = [f"{prefix}Bytecode<{program.name}>:"]
    for index, instruction in enumerate(program.instructions):
        operand = format_operand(instruction.operand)
        suffix = f" {operand}" if operand else ""
        lines.append(f"{prefix}{index:04d} {instruction.opcode.value}{suffix}")

    for instruction in program.instructions:
        if instruction.opcode is Opcode.DEFINE_FUNCTION and isinstance(instruction.operand, FunctionPrototype):
            lines.append("")
            lines.append(f"{prefix}function {instruction.operand.name}({', '.join(instruction.operand.parameters)}):")
            lines.append(disassemble(instruction.operand.program, indent=indent + 2))

    return "\n".join(lines)


def format_operand(operand: Any) -> str:
    if operand is None:
        return ""
    if isinstance(operand, CallSpec):
        return f"{operand.name}/{operand.arg_count}"
    if isinstance(operand, FunctionPrototype):
        return f"{operand.name}/{len(operand.parameters)}"
    if isinstance(operand, CountedLoopSetupSpec):
        return f"loop#{operand.loop_id} {operand.variable_name} exit={operand.exit_target}"
    if isinstance(operand, CountedLoopNextSpec):
        return f"loop#{operand.loop_id} {operand.variable_name} -> {operand.body_start}"
    if isinstance(operand, dict):
        if "title" in operand and "elements" in operand:
            return f"window<{operand['title']}>"
        return str(operand)
    return repr(operand)
