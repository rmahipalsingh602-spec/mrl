from __future__ import annotations

import argparse
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from ai_engine import process_ai_command
from compiler import BytecodeCompiler, disassemble
from config import EcosystemConfig
from errors import MRLFileError, MRLError
from gui_runtime import GUIRuntime
from jit_engine import JITEngine
from lexer import Lexer
from module_loader import ModuleLoader
from package_manager import PackageManager, PackageManagerError
from parser import Parser
from runtime import RuntimeContext, render_logo
from version import DISPLAY_VERSION
from vm import VirtualMachine
from web_runtime import WebRuntimeError, run_web_runtime

VERSION = DISPLAY_VERSION
SUPPORTED_RUNTIMES = {"native", "web", "app", "game"}


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mrl",
        description="Run, compile, and serve Multi Runtime Language programs.",
        epilog=(
            "Examples:\n"
            "  mrl test.mrl\n"
            "  mrl showcase_update.mrl\n"
            "  mrl run test.mrl\n"
            "  mrl run web\n"
            "  mrl run app ui.mrl\n"
            "  mrl compile test.mrl\n"
            "  mrl install utils\n"
            "  mrl ai \"generate navbar\"\n"
            "  mrl logo"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="Source file or subcommand such as 'run', 'compile', 'install', 'list', 'ai', or 'logo'",
    )
    parser.add_argument("rest", nargs="*", help="Additional arguments for the selected command")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser


def build_execution_stack(
    *,
    file_path: str | None = None,
    runtime_target: str = "native",
) -> tuple[RuntimeContext, VirtualMachine]:
    project_root = Path(file_path).resolve().parent if file_path is not None else Path.cwd().resolve()
    ecosystem_config = EcosystemConfig.for_project(project_root)
    package_manager = PackageManager(ecosystem_config)
    runtime = RuntimeContext(target=runtime_target, project_root=project_root)
    module_loader = ModuleLoader(search_root=project_root, package_manager=package_manager)
    gui_runtime = GUIRuntime(headless=None if runtime_target == "app" else True)
    jit_engine = JITEngine(enabled=True)
    vm = VirtualMachine(
        runtime=runtime,
        module_loader=module_loader,
        package_manager=package_manager,
        gui_runtime=gui_runtime,
        jit_engine=jit_engine,
    )
    return runtime, vm


def parse_source(source: str, *, file_path: str | None = None):
    source_lines = source.splitlines()
    lexer = Lexer(source, file_path=file_path)
    tokens = lexer.tokenize()
    parser = Parser(tokens, source_lines=source_lines, file_path=file_path)
    return parser.parse(), tuple(source_lines)


def compile_source(source: str, *, file_path: str | None = None):
    program, source_lines = parse_source(source, file_path=file_path)
    compiler = BytecodeCompiler(file_path=file_path, source_lines=source_lines)
    return compiler.compile(program)


def run_source(
    source: str,
    *,
    file_path: str | None = None,
    runtime_target: str = "native",
) -> RuntimeContext:
    if runtime_target not in {"native", "app", "game"}:
        raise ValueError(f"Unsupported bytecode runtime target: {runtime_target}")

    bytecode = compile_source(source, file_path=file_path)
    runtime, vm = build_execution_stack(file_path=file_path, runtime_target=runtime_target)

    if runtime_target == "game":
        print("[runtime] game runtime selected.")
    elif runtime_target == "app":
        print("[runtime] app runtime selected.")
    else:
        print("[runtime] native vm selected.")

    vm.execute(bytecode)
    return runtime


def run_file(path: str, *, runtime_target: str = "native") -> int:
    source_path = Path(path)
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(MRLFileError(str(exc), file_path=str(source_path)), file=sys.stderr)
        return 1

    try:
        run_source(source, file_path=str(source_path), runtime_target=runtime_target)
    except MRLError as exc:
        print(exc, file=sys.stderr)
        return 1

    return 0


def resolve_run_arguments(arguments: list[str]) -> tuple[str, str | None]:
    if not arguments:
        return "native", None

    if len(arguments) == 1:
        if arguments[0] in SUPPORTED_RUNTIMES:
            return arguments[0], None
        return "native", arguments[0]

    if len(arguments) == 2 and arguments[0] in SUPPORTED_RUNTIMES:
        return arguments[0], arguments[1]

    raise ValueError("Use 'run <file.mrl>' or 'run <native|web|app|game> [entry]'.")


def build_package_manager(*, project_root: Path | None = None) -> PackageManager:
    return PackageManager(EcosystemConfig.for_project(project_root or Path.cwd()))


def handle_run_command(arguments: list[str], parser: argparse.ArgumentParser) -> int:
    try:
        runtime_target, entry = resolve_run_arguments(arguments)
    except ValueError as exc:
        parser.error(str(exc))

    if runtime_target == "web":
        try:
            run_web_runtime(entry)
        except WebRuntimeError as exc:
            print(f"Web Runtime Error: {exc}", file=sys.stderr)
            return 1
        return 0

    if entry is None:
        parser.error("Use 'run <file.mrl>' or 'run <app|game> <file.mrl>'.")

    return run_file(entry, runtime_target=runtime_target)


def handle_compile_command(arguments: list[str], parser: argparse.ArgumentParser) -> int:
    if len(arguments) != 1:
        parser.error("Use 'compile <file.mrl>'.")

    source_path = Path(arguments[0])
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(MRLFileError(str(exc), file_path=str(source_path)), file=sys.stderr)
        return 1

    try:
        bytecode = compile_source(source, file_path=str(source_path))
    except MRLError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(disassemble(bytecode))
    return 0


def handle_install_command(arguments: list[str], parser: argparse.ArgumentParser) -> int:
    if len(arguments) != 1:
        parser.error("Use 'install <package_name>'.")

    package_manager = build_package_manager()
    try:
        record = package_manager.install_package(arguments[0])
    except PackageManagerError as exc:
        print(f"Package Error: {exc}", file=sys.stderr)
        return 1

    print(f"[package] Installed '{record.name}' at {record.entrypoint}")
    return 0


def handle_list_command(arguments: list[str], parser: argparse.ArgumentParser) -> int:
    if arguments:
        parser.error("Use 'list' without extra arguments.")

    package_manager = build_package_manager()
    try:
        packages = package_manager.list_packages()
    except PackageManagerError as exc:
        print(f"Package Error: {exc}", file=sys.stderr)
        return 1

    if not packages:
        print("No packages installed.")
        return 0

    for package_name in packages:
        print(package_name)
    return 0


def handle_ai_command(arguments: list[str], parser: argparse.ArgumentParser) -> int:
    if not arguments:
        parser.error("Use 'ai \"prompt\"'.")

    prompt = " ".join(arguments).strip()
    print(process_ai_command(prompt))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if not args.command:
        print(render_logo())
        print()
        parser.print_help()
        return 1

    if args.command == "run":
        return handle_run_command(args.rest, parser)

    if args.command in {"compile", "bytecode"}:
        return handle_compile_command(args.rest, parser)

    if args.command == "install":
        return handle_install_command(args.rest, parser)

    if args.command == "list":
        return handle_list_command(args.rest, parser)

    if args.command == "ai":
        return handle_ai_command(args.rest, parser)

    if args.command == "logo":
        print(render_logo())
        return 0

    if args.command == "repl":
        print("REPL support is not wired into this runtime yet. Use 'mrl test.mrl' for now.")
        return 0

    if args.rest:
        parser.error("Unexpected extra arguments. Use 'mrl <file.mrl>' or 'mrl run <file.mrl>'.")

    return run_file(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

