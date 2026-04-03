from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_engine import process_ai_command
from ast_nodes import SourceLocation
from compiler import BytecodeProgram, CallSpec, FunctionPrototype, LoopDescriptor, Opcode
from compiler import CountedLoopNextSpec, CountedLoopSetupSpec
from environment import Environment
from errors import MRLRuntimeError
from gui_runtime import GUIRuntime
from jit_engine import JITEngine
from module_loader import ModuleLoader
from package_manager import PackageManager, PackageManagerError
from runtime import RuntimeContext


@dataclass(slots=True)
class CompiledFunction:
    name: str
    parameters: list[str]
    program: BytecodeProgram
    closure: Environment
    location: SourceLocation | None = None

    @property
    def arity(self) -> int:
        return len(self.parameters)


@dataclass(slots=True)
class ExecutionFrame:
    program: BytecodeProgram
    environment: Environment
    stack: list[Any] = field(default_factory=list)
    counted_loops: dict[int, "CountedLoopState"] = field(default_factory=dict)
    ip: int = 0


@dataclass(slots=True)
class CountedLoopState:
    current: int
    end: int
    step: int


class VirtualMachine:
    def __init__(
        self,
        *,
        runtime: RuntimeContext | None = None,
        module_loader: ModuleLoader | None = None,
        package_manager: PackageManager | None = None,
        gui_runtime: GUIRuntime | None = None,
        jit_engine: JITEngine | None = None,
    ) -> None:
        self.runtime = runtime if runtime is not None else RuntimeContext()
        self.package_manager = package_manager if package_manager is not None else PackageManager()
        self.module_loader = module_loader if module_loader is not None else ModuleLoader(package_manager=self.package_manager)
        self.gui_runtime = gui_runtime if gui_runtime is not None else GUIRuntime()
        self.jit_engine = jit_engine if jit_engine is not None else JITEngine(enabled=self.runtime.jit_enabled)

    def execute(self, program: BytecodeProgram, *, environment: Environment | None = None) -> Any:
        frame = ExecutionFrame(
            program=program,
            environment=environment if environment is not None else self.runtime.global_env,
        )
        return self.run_frame(frame)

    def run_frame(self, frame: ExecutionFrame) -> Any:
        while frame.ip < len(frame.program.instructions):
            if self.jit_engine.maybe_run_optimized_loop(self, frame):
                continue

            action, payload = self.step(frame, frame.ip)
            if action == "return":
                return payload
            frame.ip = payload
        return None

    def execute_optimized_loop(self, frame: ExecutionFrame, descriptor: LoopDescriptor) -> None:
        while True:
            condition_value = self.evaluate_region_value(frame, descriptor.condition_start, descriptor.condition_end)
            if not self.is_truthy(condition_value):
                return
            self.execute_region(frame, descriptor.body_start, descriptor.body_end)

    def execute_region(self, frame: ExecutionFrame, start: int, end: int) -> None:
        stack_size = len(frame.stack)
        ip = start
        while ip < end:
            action, payload = self.step(frame, ip, allow_jit=False)
            if action == "return":
                raise self.runtime_error("Unexpected return inside an optimized loop region.", None, frame.program)
            if payload < start or payload > end:
                raise self.runtime_error("Optimized loop execution escaped its region.", None, frame.program)
            ip = payload
        if len(frame.stack) != stack_size:
            raise self.runtime_error("Optimized loop body left unbalanced stack state.", None, frame.program)

    def evaluate_region_value(self, frame: ExecutionFrame, start: int, end: int) -> Any:
        stack_size = len(frame.stack)
        ip = start
        while ip < end:
            action, payload = self.step(frame, ip, allow_jit=False)
            if action == "return":
                raise self.runtime_error("Unexpected return inside an optimized condition.", None, frame.program)
            if payload < start or payload > end:
                raise self.runtime_error("Optimized condition escaped its region.", None, frame.program)
            ip = payload

        if len(frame.stack) != stack_size + 1:
            raise self.runtime_error("Optimized condition produced invalid stack state.", None, frame.program)
        return frame.stack.pop()

    def step(self, frame: ExecutionFrame, ip: int, *, allow_jit: bool = True) -> tuple[str, Any]:
        instruction = frame.program.instructions[ip]
        location = instruction.location
        next_ip = ip + 1

        if instruction.opcode is Opcode.LOAD_CONST:
            frame.stack.append(instruction.operand)
            return "continue", next_ip

        if instruction.opcode is Opcode.LOAD_VAR:
            value = frame.environment.get(
                instruction.operand,
                location=location,
                source_lines=frame.program.source_lines,
                file_path=frame.program.file_path,
            )
            frame.stack.append(value)
            return "continue", next_ip

        if instruction.opcode is Opcode.STORE_VAR:
            value = self.pop_stack(frame, "STORE_VAR", location, frame.program)
            frame.environment.assign(instruction.operand, value)
            return "continue", next_ip

        if instruction.opcode is Opcode.ADD:
            right, left = self.pop_binary_operands(frame, instruction.opcode.value, location, frame.program)
            if isinstance(left, str) or isinstance(right, str):
                frame.stack.append(f"{self.stringify(left)}{self.stringify(right)}")
            elif self.is_integer(left) and self.is_integer(right):
                frame.stack.append(left + right)
            else:
                raise self.runtime_error("Operator '+' supports integers or string concatenation.", location, frame.program)
            return "continue", next_ip

        if instruction.opcode is Opcode.SUB:
            right, left = self.pop_binary_operands(frame, instruction.opcode.value, location, frame.program)
            self.require_integers("-", left, right, location, frame.program)
            frame.stack.append(left - right)
            return "continue", next_ip

        if instruction.opcode is Opcode.MUL:
            right, left = self.pop_binary_operands(frame, instruction.opcode.value, location, frame.program)
            self.require_integers("*", left, right, location, frame.program)
            frame.stack.append(left * right)
            return "continue", next_ip

        if instruction.opcode is Opcode.DIV:
            right, left = self.pop_binary_operands(frame, instruction.opcode.value, location, frame.program)
            self.require_integers("/", left, right, location, frame.program)
            if right == 0:
                raise self.runtime_error("Division by zero is not allowed.", location, frame.program)
            frame.stack.append(left // right)
            return "continue", next_ip

        if instruction.opcode is Opcode.NOT:
            value = self.pop_stack(frame, "NOT", location, frame.program)
            frame.stack.append(not self.is_truthy(value))
            return "continue", next_ip

        if instruction.opcode is Opcode.AND:
            right, left = self.pop_binary_operands(frame, instruction.opcode.value, location, frame.program)
            frame.stack.append(self.is_truthy(left) and self.is_truthy(right))
            return "continue", next_ip

        if instruction.opcode is Opcode.OR:
            right, left = self.pop_binary_operands(frame, instruction.opcode.value, location, frame.program)
            frame.stack.append(self.is_truthy(left) or self.is_truthy(right))
            return "continue", next_ip

        if instruction.opcode in {
            Opcode.COMPARE_EQ,
            Opcode.COMPARE_NE,
            Opcode.COMPARE_GT,
            Opcode.COMPARE_GTE,
            Opcode.COMPARE_LT,
            Opcode.COMPARE_LTE,
        }:
            right, left = self.pop_binary_operands(frame, instruction.opcode.value, location, frame.program)
            frame.stack.append(self.compare_values(instruction.opcode, left, right, location, frame.program))
            return "continue", next_ip

        if instruction.opcode is Opcode.PRINT:
            value = self.pop_stack(frame, "PRINT", location, frame.program)
            self.runtime.write(self.stringify(value))
            return "continue", next_ip

        if instruction.opcode is Opcode.JUMP_IF_FALSE:
            value = self.pop_stack(frame, "JUMP_IF_FALSE", location, frame.program)
            if not self.is_truthy(value):
                return "continue", instruction.operand
            return "continue", next_ip

        if instruction.opcode is Opcode.JUMP:
            descriptor = frame.program.loop_by_back_jump.get(ip)
            if allow_jit and descriptor is not None and instruction.operand == descriptor.condition_start:
                if self.jit_engine.record_back_edge(frame.program, descriptor):
                    self.runtime.record_optimization(
                        f"JIT optimized loop {descriptor.loop_id} in {frame.program.name}"
                    )
            return "continue", instruction.operand

        if instruction.opcode is Opcode.DEFINE_FUNCTION:
            prototype = instruction.operand
            if not isinstance(prototype, FunctionPrototype):
                raise self.runtime_error("Invalid function prototype encountered in bytecode.", location, frame.program)
            compiled = CompiledFunction(
                name=prototype.name,
                parameters=list(prototype.parameters),
                program=prototype.program,
                closure=frame.environment,
                location=prototype.location,
            )
            frame.environment.define(prototype.name, compiled)
            return "continue", next_ip

        if instruction.opcode is Opcode.CALL_FUNCTION:
            call_spec = instruction.operand
            if not isinstance(call_spec, CallSpec):
                raise self.runtime_error("Invalid function call metadata in bytecode.", location, frame.program)
            arguments = [self.pop_stack(frame, "CALL_FUNCTION", location, frame.program) for _ in range(call_spec.arg_count)]
            arguments.reverse()
            value = frame.environment.get(
                call_spec.name,
                location=location,
                source_lines=frame.program.source_lines,
                file_path=frame.program.file_path,
            )
            result = self.call_function(value, call_spec.name, arguments, location, frame.program)
            frame.stack.append(result)
            return "continue", next_ip

        if instruction.opcode is Opcode.IMPORT_MODULE:
            self.module_loader.load_module_vm(
                instruction.operand,
                vm=self,
                target_environment=frame.environment,
                location=location,
                source_lines=frame.program.source_lines,
                current_file_path=frame.program.file_path,
            )
            return "continue", next_ip

        if instruction.opcode is Opcode.INSTALL_PACKAGE:
            try:
                record = self.package_manager.install_package(str(instruction.operand))
            except PackageManagerError as exc:
                raise self.runtime_error(str(exc), location, frame.program) from exc
            self.runtime.write(f"[package] Installed '{record.name}' at {record.entrypoint}")
            return "continue", next_ip

        if instruction.opcode is Opcode.AI_COMMAND:
            self.runtime.write(process_ai_command(str(instruction.operand)))
            return "continue", next_ip

        if instruction.opcode is Opcode.BUILD_UI:
            definition = self.gui_runtime.definition_from_model(dict(instruction.operand))
            preview = self.gui_runtime.render_definition(
                definition,
                run_mainloop=self.runtime.target == "app",
            )
            if self.runtime.target != "app" or self.gui_runtime.headless:
                self.runtime.write(preview)
            return "continue", next_ip

        if instruction.opcode is Opcode.SETUP_COUNTED_LOOP:
            spec = instruction.operand
            if not isinstance(spec, CountedLoopSetupSpec):
                raise self.runtime_error("Invalid counted loop setup metadata.", location, frame.program)

            step = self.pop_stack(frame, "SETUP_COUNTED_LOOP", location, frame.program)
            end = self.pop_stack(frame, "SETUP_COUNTED_LOOP", location, frame.program)
            start = self.pop_stack(frame, "SETUP_COUNTED_LOOP", location, frame.program)

            self.require_integers("counted loop", start, end, location, frame.program)
            if not self.is_integer(step):
                raise self.runtime_error("Counted loop step must be an integer.", location, frame.program)
            if step == 0:
                raise self.runtime_error("Counted loop step cannot be 0.", location, frame.program)

            if not self.is_counted_loop_value_in_range(start, end, step):
                frame.counted_loops.pop(spec.loop_id, None)
                return "continue", spec.exit_target if spec.exit_target is not None else next_ip

            frame.counted_loops[spec.loop_id] = CountedLoopState(current=start, end=end, step=step)
            frame.environment.assign(spec.variable_name, start)
            return "continue", next_ip

        if instruction.opcode is Opcode.COUNTED_LOOP_NEXT:
            spec = instruction.operand
            if not isinstance(spec, CountedLoopNextSpec):
                raise self.runtime_error("Invalid counted loop step metadata.", location, frame.program)

            state = frame.counted_loops.get(spec.loop_id)
            if state is None:
                raise self.runtime_error("Counted loop state was lost during execution.", location, frame.program)

            next_value = state.current + state.step
            if self.is_counted_loop_value_in_range(next_value, state.end, state.step):
                state.current = next_value
                frame.environment.assign(spec.variable_name, next_value)
                return "continue", spec.body_start

            frame.counted_loops.pop(spec.loop_id, None)
            return "continue", next_ip

        if instruction.opcode is Opcode.POP:
            if frame.stack:
                frame.stack.pop()
            return "continue", next_ip

        if instruction.opcode is Opcode.RETURN:
            value = frame.stack.pop() if frame.stack else None
            return "return", value

        raise self.runtime_error(f"Unsupported opcode '{instruction.opcode.value}'.", location, frame.program)

    def call_function(
        self,
        value: Any,
        name: str,
        arguments: list[Any],
        location: SourceLocation | None,
        program: BytecodeProgram,
    ) -> Any:
        if isinstance(value, CompiledFunction):
            if len(arguments) != value.arity:
                raise self.runtime_error(
                    f"Function '{name}' expected {value.arity} argument(s), got {len(arguments)}.",
                    location,
                    program,
                )

            call_env = Environment(value.closure, scope_name=f"function:{value.name}")
            for parameter, argument in zip(value.parameters, arguments, strict=True):
                call_env.define(parameter, argument)

            call_location = location if location is not None else value.location
            if call_location is not None:
                self.runtime.push_call(value.name, call_location, value.program.file_path)
            try:
                return self.run_frame(ExecutionFrame(program=value.program, environment=call_env))
            finally:
                if call_location is not None:
                    self.runtime.pop_call()

        if callable(value):
            return value(*arguments)

        raise self.runtime_error(f"'{name}' is not a callable function.", location, program)

    def pop_stack(
        self,
        frame: ExecutionFrame,
        opcode_name: str,
        location: SourceLocation | None,
        program: BytecodeProgram,
    ) -> Any:
        if not frame.stack:
            raise self.runtime_error(f"Opcode '{opcode_name}' attempted to read from an empty stack.", location, program)
        return frame.stack.pop()

    def pop_binary_operands(
        self,
        frame: ExecutionFrame,
        opcode_name: str,
        location: SourceLocation | None,
        program: BytecodeProgram,
    ) -> tuple[Any, Any]:
        right = self.pop_stack(frame, opcode_name, location, program)
        left = self.pop_stack(frame, opcode_name, location, program)
        return right, left

    def compare_values(
        self,
        opcode: Opcode,
        left: Any,
        right: Any,
        location: SourceLocation | None,
        program: BytecodeProgram,
    ) -> bool:
        if opcode is Opcode.COMPARE_EQ:
            return left == right
        if opcode is Opcode.COMPARE_NE:
            return left != right

        if (self.is_integer(left) and self.is_integer(right)) or (isinstance(left, str) and isinstance(right, str)):
            if opcode is Opcode.COMPARE_GT:
                return left > right
            if opcode is Opcode.COMPARE_GTE:
                return left >= right
            if opcode is Opcode.COMPARE_LT:
                return left < right
            if opcode is Opcode.COMPARE_LTE:
                return left <= right

        raise self.runtime_error(
            f"Operator '{opcode.value}' requires two integers or two strings.",
            location,
            program,
        )

    def require_integers(
        self,
        operator: str,
        left: Any,
        right: Any,
        location: SourceLocation | None,
        program: BytecodeProgram,
    ) -> None:
        if self.is_integer(left) and self.is_integer(right):
            return
        raise self.runtime_error(f"Operator '{operator}' requires integer operands.", location, program)

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
        if isinstance(value, CompiledFunction):
            return f"<function {value.name}>"
        return str(value)

    def is_counted_loop_value_in_range(self, value: int, end: int, step: int) -> bool:
        if step > 0:
            return value <= end
        return value >= end

    def runtime_error(
        self,
        message: str,
        location: SourceLocation | None,
        program: BytecodeProgram,
    ) -> MRLRuntimeError:
        stack_trace = self.runtime.format_call_stack()
        if stack_trace:
            message = f"{message}\n{stack_trace}"
        return MRLRuntimeError(
            message,
            line=location.line if location is not None else None,
            column=location.column if location is not None else None,
            source_lines=program.source_lines,
            file_path=program.file_path,
        )
