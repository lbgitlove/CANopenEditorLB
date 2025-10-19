"""Persistence utilities for user preferences and MRU tracking."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List

from platformdirs import PlatformDirs


@dataclass
class UserPreferences:
    """Serializable settings for the application."""

    theme: str = "system"
    recent_files: List[str] = field(default_factory=list)
    window_state: dict[str, object] = field(default_factory=dict)


class SettingsManager:
    """Store and retrieve :class:`UserPreferences` from disk."""

    def __init__(
        self,
        storage_dir: Path | None = None,
        app_name: str = "CANopenNodeEditor",
        app_author: str = "OpenAI",
    ) -> None:
        if storage_dir is None:
            dirs = PlatformDirs(app_name, app_author)
            storage_dir = Path(dirs.user_config_dir)
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._settings_path = self._storage_dir / "settings.json"
        self._preferences = UserPreferences()

    @property
    def storage_path(self) -> Path:
        return self._settings_path

    def load(self) -> UserPreferences:
        if not self._settings_path.exists():
            self._preferences = UserPreferences()
            return self._preferences

        try:
            data = json.loads(self._settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._preferences = UserPreferences()
            return self._preferences

        prefs = UserPreferences(**{**asdict(UserPreferences()), **data})
        self._preferences = prefs
        return prefs

    def save(self) -> None:
        payload = asdict(self._preferences)
        self._settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def update_preferences(self, **changes: object) -> UserPreferences:
        for key, value in changes.items():
            if hasattr(self._preferences, key):
                setattr(self._preferences, key, value)
        return self._preferences

    def add_recent_file(self, path: Path, max_entries: int = 10) -> UserPreferences:
        normalized = str(Path(path).resolve())
        recent = [item for item in self._preferences.recent_files if item != normalized]
        recent.insert(0, normalized)
        self._preferences.recent_files = recent[:max_entries]
        return self._preferences

    def remove_recent_files(self, paths: Iterable[Path]) -> UserPreferences:
        removal = {str(Path(path).resolve()) for path in paths}
        self._preferences.recent_files = [
            item for item in self._preferences.recent_files if item not in removal
        ]
        return self._preferences
