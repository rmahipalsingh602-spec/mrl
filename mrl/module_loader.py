from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from ast_nodes import ProgramNode, SourceLocation
from config import EcosystemConfig
from environment import Environment
from errors import ModuleLoadError
from lexer import Lexer
from package_manager import PackageManager, PackageManagerError
from parser import Parser

if TYPE_CHECKING:
    from interpreter import Interpreter
    from vm import VirtualMachine


@dataclass(slots=True)
class ParsedModule:
    name: str
    path: Path
    program: ProgramNode
    source_lines: tuple[str, ...]


@dataclass(slots=True)
class ModuleRecord:
    name: str
    path: Path
    environment: Environment


class ModuleLoader:
    def __init__(
        self,
        *,
        search_root: Path | None = None,
        package_manager: PackageManager | None = None,
    ) -> None:
        self.search_root = (search_root or Path.cwd()).resolve()
        config = EcosystemConfig.for_project(self.search_root)
        self.package_manager = package_manager if package_manager is not None else PackageManager(config)
        self.cache: dict[Path, ModuleRecord] = {}
        self.parsed_cache: dict[Path, ParsedModule] = {}
        self.loading: set[Path] = set()

    def load_module(
        self,
        module_name: str,
        *,
        interpreter: "Interpreter",
        target_environment: Environment,
        location: SourceLocation | None = None,
        source_lines: Sequence[str] | None = None,
        current_file_path: str | None = None,
    ) -> ModuleRecord:
        parsed = self.parse_module(
            module_name,
            location=location,
            source_lines=source_lines,
            current_file_path=current_file_path,
        )

        if parsed.path in self.cache:
            record = self.cache[parsed.path]
            self.expose_exports(record, target_environment)
            return record

        if parsed.path in self.loading:
            raise self.circular_import_error(module_name, location, source_lines, current_file_path)

        self.loading.add(parsed.path)
        try:
            module_env = Environment(interpreter.runtime.global_env, scope_name=f"module:{module_name}")
            interpreter.interpret(
                parsed.program,
                environment=module_env,
                source_lines=parsed.source_lines,
                file_path=str(parsed.path),
            )
            record = ModuleRecord(name=module_name, path=parsed.path, environment=module_env)
            self.cache[parsed.path] = record
        finally:
            self.loading.discard(parsed.path)

        self.expose_exports(record, target_environment)
        return record

    def load_module_vm(
        self,
        module_name: str,
        *,
        vm: "VirtualMachine",
        target_environment: Environment,
        location: SourceLocation | None = None,
        source_lines: Sequence[str] | None = None,
        current_file_path: str | None = None,
    ) -> ModuleRecord:
        parsed = self.parse_module(
            module_name,
            location=location,
            source_lines=source_lines,
            current_file_path=current_file_path,
        )

        if parsed.path in self.cache:
            record = self.cache[parsed.path]
            self.expose_exports(record, target_environment)
            return record

        if parsed.path in self.loading:
            raise self.circular_import_error(module_name, location, source_lines, current_file_path)

        self.loading.add(parsed.path)
        try:
            from compiler import BytecodeCompiler

            compiler = BytecodeCompiler(
                file_path=str(parsed.path),
                source_lines=parsed.source_lines,
                program_name=module_name,
            )
            bytecode = compiler.compile(parsed.program)
            module_env = Environment(vm.runtime.global_env, scope_name=f"module:{module_name}")
            vm.execute(bytecode, environment=module_env)
            record = ModuleRecord(name=module_name, path=parsed.path, environment=module_env)
            self.cache[parsed.path] = record
        finally:
            self.loading.discard(parsed.path)

        self.expose_exports(record, target_environment)
        return record

    def parse_module(
        self,
        module_name: str,
        *,
        location: SourceLocation | None = None,
        source_lines: Sequence[str] | None = None,
        current_file_path: str | None = None,
    ) -> ParsedModule:
        path = self.resolve_module_path(
            module_name,
            location=location,
            source_lines=source_lines,
            current_file_path=current_file_path,
        )

        if path in self.parsed_cache:
            return self.parsed_cache[path]

        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ModuleLoadError(
                str(exc),
                line=location.line if location is not None else None,
                column=location.column if location is not None else None,
                source_lines=source_lines,
                file_path=current_file_path,
            ) from exc

        module_source_lines = tuple(source.splitlines())
        lexer = Lexer(source, file_path=str(path))
        tokens = lexer.tokenize()
        parser = Parser(tokens, source_lines=list(module_source_lines), file_path=str(path))
        program = parser.parse()

        parsed = ParsedModule(
            name=module_name,
            path=path,
            program=program,
            source_lines=module_source_lines,
        )
        self.parsed_cache[path] = parsed
        return parsed

    def expose_exports(self, record: ModuleRecord, target_environment: Environment) -> None:
        for name, value in record.environment.bindings().items():
            if name.startswith("_"):
                continue
            target_environment.define(name, value)

    def resolve_module_path(
        self,
        module_name: str,
        *,
        location: SourceLocation | None = None,
        source_lines: Sequence[str] | None = None,
        current_file_path: str | None = None,
    ) -> Path:
        module_filename = module_name if module_name.endswith(".mrl") else f"{module_name}.mrl"

        candidates: list[Path] = []
        if current_file_path is not None:
            candidates.append(Path(current_file_path).resolve().parent / module_filename)
        candidates.append(self.search_root / module_filename)

        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.exists():
                return resolved

        try:
            package_entrypoint = self.package_manager.resolve_entrypoint(module_name)
        except PackageManagerError as exc:
            raise ModuleLoadError(
                str(exc),
                line=location.line if location is not None else None,
                column=location.column if location is not None else None,
                source_lines=source_lines,
                file_path=current_file_path,
            ) from exc

        if package_entrypoint is not None:
            return package_entrypoint.resolve()

        raise ModuleLoadError(
            f"Module '{module_name}' could not be found.",
            line=location.line if location is not None else None,
            column=location.column if location is not None else None,
            source_lines=source_lines,
            file_path=current_file_path,
        )

    def circular_import_error(
        self,
        module_name: str,
        location: SourceLocation | None,
        source_lines: Sequence[str] | None,
        current_file_path: str | None,
    ) -> ModuleLoadError:
        return ModuleLoadError(
            f"Circular import detected for module '{module_name}'.",
            line=location.line if location is not None else None,
            column=location.column if location is not None else None,
            source_lines=source_lines,
            file_path=current_file_path,
        )