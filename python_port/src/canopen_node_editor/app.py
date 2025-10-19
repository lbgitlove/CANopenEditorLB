"""High-level application bootstrap helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .gui import EditorApplication, EditorMainWindow
from .services.network import NetworkManager
from .services.profiles import ProfileRepository
from .services.settings import SettingsManager


@dataclass(slots=True)
class ApplicationPaths:
    """Container for well-known application paths.

    These are resolved relative to the project root and allow the rest of the
    application to discover resources regardless of the active virtual
    environment or working directory.
    """

    root_dir: Path
    config_dir: Path
    data_dir: Path


def resolve_paths(base_dir: Path | None = None) -> ApplicationPaths:
    """Return the standard path layout for the application.

    Parameters
    ----------
    base_dir:
        Optional project root. When ``None`` the function climbs two
        directories up from this file. This keeps the bootstrap environment
        consistent whether the package is installed in editable or regular
        mode.
    """

    root = base_dir if base_dir is not None else Path(__file__).resolve().parents[2]
    config_dir = root / "config"
    data_dir = root / "data"

    return ApplicationPaths(root_dir=root, config_dir=config_dir, data_dir=data_dir)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for launching the Qt application."""

    paths = resolve_paths()
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    paths.data_dir.mkdir(parents=True, exist_ok=True)

    storage_dir = paths.config_dir / "user"
    storage_dir.mkdir(parents=True, exist_ok=True)

    settings = SettingsManager(storage_dir=storage_dir)
    network = NetworkManager()

    search_paths = []
    for candidate in (paths.data_dir / "profiles", paths.data_dir / "samples"):
        if candidate.exists():
            search_paths.append(candidate)
    profile_repository = ProfileRepository(search_paths)

    app = EditorApplication(argv or [], settings)
    window = EditorMainWindow(
        network,
        settings,
        profile_repository=profile_repository,
        toggle_theme=app.toggle_theme,
    )
    window.show()
    return app.exec()
