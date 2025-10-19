"""Application bootstrap helpers for the Qt GUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import QApplication, QStyle

try:
    from qt_material import apply_stylesheet
except Exception:  # pragma: no cover - optional dependency at runtime only
    apply_stylesheet = None  # type: ignore[assignment]

from ..services.settings import SettingsManager, UserPreferences


@dataclass
class ThemeDefinition:
    """Metadata describing an available application theme."""

    key: str
    label: str
    material_theme: str | None


class EditorApplication(QApplication):
    """QApplication subclass that wires configuration and localisation."""

    THEMES: tuple[ThemeDefinition, ...] = (
        ThemeDefinition("system", "System", None),
        ThemeDefinition("light", "Light", "light_blue.xml"),
        ThemeDefinition("dark", "Dark", "dark_teal.xml"),
    )

    def __init__(
        self,
        argv: Sequence[str] | None,
        settings: SettingsManager,
        available_locales: Iterable[QLocale] | None = None,
    ) -> None:
        super().__init__(list(argv or []))
        self.setOrganizationName("CANopenNode")
        self.setOrganizationDomain("canopennode.org")
        self.setApplicationName("CANopenNode Editor")
        self.setApplicationDisplayName(self.applicationName())

        self._settings = settings
        self._translator = QTranslator(self)
        self._translator_installed = False
        self._locales = list(available_locales or [QLocale.system()])

        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        if not icon.isNull():
            self.setWindowIcon(icon)

        preferences = self._settings.load()
        self._apply_theme(preferences)
        self._install_translator(preferences)

    # ------------------------------------------------------------------
    # Theme management
    def _apply_theme(self, preferences: UserPreferences) -> None:
        theme = preferences.theme
        chosen = next((definition for definition in self.THEMES if definition.key == theme), None)
        if chosen is None:
            chosen = self.THEMES[0]
            preferences.theme = chosen.key

        if apply_stylesheet is None or chosen.material_theme is None:
            self.setStyleSheet("")
            return

        try:
            apply_stylesheet(self, theme=chosen.material_theme)
        except Exception:
            # Fall back to the default Qt style if theming fails.
            self.setStyleSheet("")

    def set_theme(self, theme_key: str) -> None:
        preferences = self._settings.update_preferences(theme=theme_key)
        self._apply_theme(preferences)
        self._settings.save()

    # ------------------------------------------------------------------
    # Localisation support
    def _install_translator(self, preferences: UserPreferences) -> None:
        locale = self._resolve_locale(preferences)
        if not locale:
            return

        if self._translator_installed:
            self.removeTranslator(self._translator)
            self._translator_installed = False

        translation_path = self._translation_path(locale)
        if translation_path:
            if self._translator.load(translation_path):
                self._translator_installed = self.installTranslator(self._translator)

    def _resolve_locale(self, preferences: UserPreferences) -> QLocale | None:
        if preferences.window_state.get("locale"):
            return QLocale(preferences.window_state["locale"])
        return self._locales[0] if self._locales else None

    def _translation_path(self, locale: QLocale) -> str | None:
        # Translation packs are optional. The method returns the first matching
        # resource if it exists.
        locale_names = [locale.name(), locale.name().split("_")[0]]
        base_paths = []
        settings_path = self._settings.storage_path.parent / "translations"
        base_paths.append(settings_path)

        for base in base_paths:
            for name in locale_names:
                candidate = base / f"canopen_node_editor_{name}.qm"
                if candidate.exists():
                    return str(candidate)
        return None

    # ------------------------------------------------------------------
    # Convenience helpers
    def toggle_theme(self) -> None:
        current = self._settings.load().theme
        if current == "dark":
            self.set_theme("light")
        else:
            self.set_theme("dark")

    def reload_preferences(self) -> None:
        self._apply_theme(self._settings.load())
