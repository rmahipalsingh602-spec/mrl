from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import EcosystemConfig, PACKAGE_REGISTRY_VERSION

PACKAGE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PackageManagerError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class PackageRecord:
    name: str
    directory: Path
    entrypoint: Path


class PackageManager:
    def __init__(self, config: EcosystemConfig | None = None) -> None:
        self.config = config if config is not None else EcosystemConfig.for_project()

    def install_package(self, name: str) -> PackageRecord:
        package_name = self.normalize_package_name(name)
        self.ensure_layout()

        package_dir = self.config.package_dir(package_name)
        entrypoint = self.config.package_entrypoint_path(package_name)
        package_dir.mkdir(parents=True, exist_ok=True)

        if not entrypoint.exists():
            entrypoint.write_text(self.build_package_template(package_name), encoding="utf-8")

        registry = self.load_registry()
        registry["packages"][package_name] = self.serialize_package_record(package_name, package_dir, entrypoint)
        self.write_registry(registry)

        return PackageRecord(name=package_name, directory=package_dir, entrypoint=entrypoint)

    def list_packages(self) -> list[str]:
        names = set(self.load_registry().get("packages", {}).keys())

        if self.config.packages_dir.exists():
            for child in self.config.packages_dir.iterdir():
                if not child.is_dir():
                    continue
                entrypoint = child / self.config.package_entrypoint
                if entrypoint.exists() and PACKAGE_NAME_PATTERN.fullmatch(child.name):
                    names.add(child.name)

        return sorted(name for name in names if self.is_installed(name))

    def is_installed(self, name: str) -> bool:
        return self.resolve_entrypoint(name) is not None

    def resolve_entrypoint(self, name: str) -> Path | None:
        try:
            package_name = self.normalize_package_name(name)
        except PackageManagerError:
            return None

        candidates: list[Path] = []
        package_data = self.load_registry().get("packages", {}).get(package_name)
        if isinstance(package_data, dict):
            entry = package_data.get("entry")
            if isinstance(entry, str) and entry.strip():
                candidates.append((self.config.project_root / entry).resolve())

        candidates.append(self.config.package_entrypoint_path(package_name).resolve())

        seen: set[Path] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.exists():
                return candidate
        return None

    def ensure_layout(self) -> None:
        self.config.packages_dir.mkdir(parents=True, exist_ok=True)
        if not self.config.registry_path.exists():
            self.write_registry(self.empty_registry())

    def load_registry(self) -> dict[str, Any]:
        if not self.config.registry_path.exists():
            return self.empty_registry()

        try:
            data = json.loads(self.config.registry_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise PackageManagerError(f"Unable to read the package registry: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise PackageManagerError(f"Package registry is not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise PackageManagerError("Package registry must contain a JSON object.")

        packages = data.get("packages", {})
        if not isinstance(packages, dict):
            raise PackageManagerError("Package registry must contain a 'packages' object.")

        return {
            "version": data.get("version", PACKAGE_REGISTRY_VERSION),
            "packages": packages,
        }

    def write_registry(self, registry: dict[str, Any]) -> None:
        self.config.packages_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.config.registry_path.write_text(
                json.dumps(registry, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise PackageManagerError(f"Unable to write the package registry: {exc}") from exc

    def serialize_package_record(self, name: str, directory: Path, entrypoint: Path) -> dict[str, str]:
        return {
            "path": self.relative_to_project(directory),
            "entry": self.relative_to_project(entrypoint),
        }

    def relative_to_project(self, path: Path) -> str:
        return path.resolve().relative_to(self.config.project_root).as_posix()

    def normalize_package_name(self, name: str) -> str:
        package_name = name.strip()
        if package_name.endswith(".mrl"):
            package_name = Path(package_name).stem
        if not package_name:
            raise PackageManagerError("Package name cannot be empty.")
        if not PACKAGE_NAME_PATTERN.fullmatch(package_name):
            raise PackageManagerError(
                "Package names must start with a letter or '_' and contain only letters, numbers, and '_'."
            )
        return package_name

    def empty_registry(self) -> dict[str, Any]:
        return {
            "version": PACKAGE_REGISTRY_VERSION,
            "packages": {},
        }

    def build_package_template(self, package_name: str) -> str:
        return (
            "# Auto-generated by the MRL package manager.\n"
            f"mrl function {package_name}_info()\n"
            f"    mrl bolo \"Package {package_name} is installed.\"\n"
            "khatam\n"
        )