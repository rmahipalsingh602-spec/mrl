from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIRECTORY_NAME = "packages"
PACKAGE_ENTRYPOINT = "main.mrl"
PACKAGE_REGISTRY_FILE = "registry.json"
PACKAGE_REGISTRY_VERSION = 1

DEFAULT_WEB_ROOT = "pages"
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 5080
DEFAULT_JIT_HOT_LOOP_THRESHOLD = 8


@dataclass(frozen=True, slots=True)
class EcosystemConfig:
    project_root: Path
    packages_dir: Path
    registry_path: Path
    package_entrypoint: str = PACKAGE_ENTRYPOINT

    @classmethod
    def for_project(cls, project_root: Path | str | None = None) -> "EcosystemConfig":
        root = Path(project_root or Path.cwd()).resolve()
        packages_dir = root / PACKAGE_DIRECTORY_NAME
        registry_path = packages_dir / PACKAGE_REGISTRY_FILE
        return cls(
            project_root=root,
            packages_dir=packages_dir,
            registry_path=registry_path,
        )

    def package_dir(self, package_name: str) -> Path:
        return self.packages_dir / package_name

    def package_entrypoint_path(self, package_name: str) -> Path:
        return self.package_dir(package_name) / self.package_entrypoint