from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_mrl_entry_module():
    target = Path(__file__).resolve().parent.parent / "mrl" / "main.py"
    spec = importlib.util.spec_from_file_location("_mrl_entry_module", target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load MRL entry module from {target}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    module = _load_mrl_entry_module()
    return module.main(list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
