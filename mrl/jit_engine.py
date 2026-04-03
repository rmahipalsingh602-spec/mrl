from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from compiler import BytecodeProgram, LoopDescriptor
from config import DEFAULT_JIT_HOT_LOOP_THRESHOLD

if TYPE_CHECKING:
    from vm import ExecutionFrame, VirtualMachine


@dataclass(slots=True)
class OptimizedLoop:
    descriptor: LoopDescriptor
    runner: Callable[["VirtualMachine", "ExecutionFrame"], None]
    trigger_count: int


class JITEngine:
    def __init__(self, *, hot_loop_threshold: int = DEFAULT_JIT_HOT_LOOP_THRESHOLD, enabled: bool = True) -> None:
        self.hot_loop_threshold = hot_loop_threshold
        self.enabled = enabled
        self.loop_hits: dict[tuple[str, int], int] = {}
        self.optimized_loops: dict[tuple[str, int], OptimizedLoop] = {}

    def record_back_edge(self, program: BytecodeProgram, descriptor: LoopDescriptor) -> bool:
        if not self.enabled:
            return False

        key = self.make_key(program, descriptor)
        hit_count = self.loop_hits.get(key, 0) + 1
        self.loop_hits[key] = hit_count

        if hit_count < self.hot_loop_threshold or key in self.optimized_loops:
            return False

        self.optimized_loops[key] = self.compile_loop(program, descriptor, hit_count)
        return True

    def maybe_run_optimized_loop(self, vm: "VirtualMachine", frame: "ExecutionFrame") -> bool:
        if not self.enabled:
            return False

        descriptor = frame.program.loop_by_start.get(frame.ip)
        if descriptor is None:
            return False

        optimized = self.optimized_loops.get(self.make_key(frame.program, descriptor))
        if optimized is None:
            return False

        optimized.runner(vm, frame)
        frame.ip = descriptor.exit_target
        return True

    def compile_loop(
        self,
        program: BytecodeProgram,
        descriptor: LoopDescriptor,
        hit_count: int,
    ) -> OptimizedLoop:
        def runner(vm: "VirtualMachine", frame: "ExecutionFrame") -> None:
            vm.execute_optimized_loop(frame, descriptor)

        return OptimizedLoop(descriptor=descriptor, runner=runner, trigger_count=hit_count)

    def make_key(self, program: BytecodeProgram, descriptor: LoopDescriptor) -> tuple[str, int]:
        program_key = program.file_path or program.name
        return program_key, descriptor.loop_id