"""High-level application bootstrap helpers."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from platformdirs import PlatformDirs

from . import __version__
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

    explicit_root = base_dir is not None
    if explicit_root:
        root = Path(base_dir)
    else:
        module_path = Path(__file__).resolve()
        root = None
        for candidate in module_path.parents:
            config_candidate = candidate / "config"
            data_candidate = candidate / "data"
            if config_candidate.exists() and data_candidate.exists():
                root = candidate
                break
        if root is None:
            root = module_path.parent

    config_dir = root / "config"
    data_dir = root / "data"

    if not explicit_root and (not config_dir.exists() or not data_dir.exists()):
        dirs = PlatformDirs("CANopenNodeEditor", "OpenAI")
        config_dir = Path(dirs.user_config_dir)
        data_dir = Path(dirs.user_data_dir)

    return ApplicationPaths(root_dir=root, config_dir=config_dir, data_dir=data_dir)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the CANopenNode Editor GUI")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the environment and exit without starting the GUI",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the application version and exit",
    )
    return parser


def _normalise_argv(argv: Sequence[str] | None) -> list[str]:
    if argv is None:
        return list(sys.argv)
    arguments = list(argv)
    if not arguments or arguments[0].startswith("-"):
        return ["canopen-node-editor", *arguments]
    return arguments


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for launching the Qt application."""

    normalised_argv = _normalise_argv(argv)
    parser = _build_parser()
    args = parser.parse_args(normalised_argv[1:])

    if args.version:
        print(__version__)
        return 0

    paths = resolve_paths()
    if args.check:
        # Resolving the paths and loading settings is sufficient to ensure the
        # application can start once Qt dependencies are available.
        settings = SettingsManager()
        settings.load()
        print(
            "CANopenNode Editor environment OK:\n"
            f"  config: {paths.config_dir}\n"
            f"  data: {paths.data_dir}"
        )
        return 0

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

    try:
        from .gui import EditorApplication, EditorMainWindow
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            raise RuntimeError(
                "PySide6 is required to launch the GUI. Install the project dependencies "
                "using 'pip install -r requirements.txt'."
            ) from exc
        raise

    app = EditorApplication(normalised_argv, settings)
    window = EditorMainWindow(
        network,
        settings,
        profile_repository=profile_repository,
        toggle_theme=app.toggle_theme,
    )
    window.show()
    return app.exec()
