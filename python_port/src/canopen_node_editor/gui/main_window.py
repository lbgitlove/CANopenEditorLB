"""Main window composition for the CANopenNode Editor GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List

from PySide6.QtCore import QByteArray, QLocale
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QTabWidget,
)

from ..services.network import DeviceSession, NetworkManager
from ..services.profiles import ProfileRepository
from ..services.settings import SettingsManager
from .dialogs import AddObjectDialog
from .widgets.command_palette import Command, CommandPalette
from .widgets.device_page import DeviceEditorPage


class EditorMainWindow(QMainWindow):
    """Main window providing menus, docks, and the device workspace."""

    def __init__(
        self,
        network: NetworkManager,
        settings: SettingsManager,
        profile_repository: ProfileRepository | None = None,
        toggle_theme: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._network = network
        self._settings = settings
        self._profile_repository = profile_repository or ProfileRepository([])
        self._toggle_theme = toggle_theme
        self._palette: CommandPalette | None = None

        self.setWindowTitle(self.tr("CANopenNode Editor"))
        self.resize(1280, 720)

        self._tabs = QTabWidget(self)
        self._tabs.setTabsClosable(True)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self._tabs)

        self._pages: Dict[DeviceEditorPage, DeviceSession] = {}

        self._status = QStatusBar(self)
        self.setStatusBar(self._status)

        self._create_actions()
        self._create_menus()
        self._register_signals()
        self._restore_window_state()
        self._refresh_recent_files()

    # ------------------------------------------------------------------
    def _create_actions(self) -> None:
        self._action_new = QAction(self.tr("&New Device…"), self)
        self._action_new.setShortcut(QKeySequence.StandardKey.New)
        self._action_new.triggered.connect(self._new_device)

        self._action_open = QAction(self.tr("&Open Device…"), self)
        self._action_open.setShortcut(QKeySequence.StandardKey.Open)
        self._action_open.triggered.connect(self._open_device_dialog)

        self._action_recent: list[QAction] = []

        self._action_export = QAction(self.tr("Export CANopenNode Sources…"), self)
        self._action_export.setShortcut("Ctrl+E")
        self._action_export.triggered.connect(self._export_current_session)

        self._action_close = QAction(self.tr("Close Device"), self)
        self._action_close.setShortcut(QKeySequence.StandardKey.Close)
        self._action_close.triggered.connect(self._close_current_tab)

        self._action_exit = QAction(self.tr("Exit"), self)
        self._action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self._action_exit.triggered.connect(self.close)

        self._action_palette = QAction(self.tr("Command Palette"), self)
        self._action_palette.setShortcut("Ctrl+K")
        self._action_palette.triggered.connect(self._show_command_palette)

        self._action_toggle_theme = QAction(self.tr("Toggle Dark Mode"), self)
        self._action_toggle_theme.triggered.connect(self._toggle_theme_action)

        self._action_about = QAction(self.tr("About"), self)
        self._action_about.triggered.connect(self._show_about_dialog)

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu(self.tr("&File"))
        file_menu.addAction(self._action_new)
        file_menu.addAction(self._action_open)
        self._recent_menu = file_menu.addMenu(self.tr("Open &Recent"))
        file_menu.addSeparator()
        file_menu.addAction(self._action_export)
        file_menu.addSeparator()
        file_menu.addAction(self._action_close)
        file_menu.addSeparator()
        file_menu.addAction(self._action_exit)

        view_menu = menu_bar.addMenu(self.tr("&View"))
        view_menu.addAction(self._action_toggle_theme)

        tools_menu = menu_bar.addMenu(self.tr("&Tools"))
        tools_menu.addAction(self._action_palette)

        profiles_menu = menu_bar.addMenu(self.tr("&Profiles"))
        profiles_menu.aboutToShow.connect(lambda m=profiles_menu: self._populate_profiles_menu(m))

        help_menu = menu_bar.addMenu(self.tr("&Help"))
        help_menu.addAction(self._action_about)

    def _register_signals(self) -> None:
        self._tabs.currentChanged.connect(lambda _: self._update_context_widgets())

    # ------------------------------------------------------------------
    def _restore_window_state(self) -> None:
        prefs = self._settings.load()
        state = prefs.window_state
        geometry = state.get("geometry")
        dock_state = state.get("dock_state")
        if geometry:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geometry.encode("ascii")))
            except Exception:
                pass
        if dock_state:
            try:
                self.restoreState(QByteArray.fromBase64(dock_state.encode("ascii")))
            except Exception:
                pass

    def _save_window_state(self) -> None:
        geometry = bytes(self.saveGeometry().toBase64()).decode("ascii")
        dock_state = bytes(self.saveState().toBase64()).decode("ascii")
        locale = QLocale.system().name()
        self._settings.update_preferences(window_state={
            "geometry": geometry,
            "dock_state": dock_state,
            "locale": locale,
        })
        self._settings.save()

    # ------------------------------------------------------------------
    def _open_device_dialog(self) -> None:
        directory = self._settings.storage_path.parent
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open Device"),
            str(directory),
            self.tr("Device Descriptions (*.eds *.xdd *.xdc)"),
        )
        if not path:
            return
        try:
            session = self._network.open_device(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Failed to open device"), str(exc))
            return
        self._settings.add_recent_file(Path(path))
        self._settings.save()
        self._refresh_recent_files()
        self._add_session(session)
        self._status.showMessage(self.tr("Loaded {name}").format(name=session.identifier), 5000)

    def _add_session(self, session: DeviceSession) -> None:
        page = DeviceEditorPage(session.device, self)
        page.addEntryRequested.connect(self._add_object_entry)
        index = self._tabs.addTab(page, session.identifier)
        self._pages[page] = session
        self._tabs.setCurrentIndex(index)
        self._update_context_widgets()
        self._offer_mandatory_object_fix(page, session)

    def add_session(self, session: DeviceSession) -> None:
        """Public helper used by tests to inject sessions."""
        self._add_session(session)

    def _close_current_tab(self) -> None:
        index = self._tabs.currentIndex()
        if index >= 0:
            self._close_tab(index)

    def _close_tab(self, index: int) -> None:
        widget = self._tabs.widget(index)
        page = widget if isinstance(widget, DeviceEditorPage) else None
        session = self._pages.pop(page, None) if page else None
        if session is not None:
            self._network.close_device(session.identifier)
        self._tabs.removeTab(index)
        self._update_context_widgets()

    def _export_current_session(self) -> None:
        index = self._tabs.currentIndex()
        if index < 0:
            return
        widget = self._tabs.currentWidget()
        page = widget if isinstance(widget, DeviceEditorPage) else None
        session = self._pages.get(page) if page else None
        if session is None:
            return
        session_id = session.identifier
        output_dir = QFileDialog.getExistingDirectory(self, self.tr("Select Output Directory"))
        if not output_dir:
            return
        try:
            exports = self._network.export_device(session_id, Path(output_dir))
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Export failed"), str(exc))
            return
        names = ", ".join(sorted(exports))
        self._status.showMessage(self.tr("Exported: {files}").format(files=names), 5000)

    def _on_tab_changed(self, index: int) -> None:
        self._update_context_widgets()

    def _update_context_widgets(self) -> None:
        page = self._current_page()
        if page is None:
            self._status.clearMessage()
            return
        self._status.showMessage(self.tr("Issues: {count}").format(count=len(page.issues)), 3000)

    def _refresh_recent_files(self) -> None:
        for action in self._action_recent:
            self._recent_menu.removeAction(action)
        self._action_recent.clear()

        prefs = self._settings.load()
        for path in prefs.recent_files:
            action = QAction(Path(path).name, self)
            action.setData(path)
            action.triggered.connect(lambda checked=False, p=path: self._open_recent_file(p))
            self._recent_menu.addAction(action)
            self._action_recent.append(action)

        if not self._action_recent:
            placeholder = QAction(self.tr("No recent files"), self)
            placeholder.setEnabled(False)
            self._recent_menu.addAction(placeholder)
            self._action_recent.append(placeholder)

    def _open_recent_file(self, path: str) -> None:
        try:
            session = self._network.open_device(Path(path))
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Unable to open"), str(exc))
            return
        self._add_session(session)

    def _populate_profiles_menu(self, menu: QMenu) -> None:
        menu.clear()
        profiles = self._profile_repository.discover()
        if not profiles:
            placeholder = QAction(self.tr("No profiles found"), self)
            placeholder.setEnabled(False)
            menu.addAction(placeholder)
            return
        for profile in profiles:
            action = QAction(profile.name, self)
            action.setData(str(profile.path))
            action.triggered.connect(lambda checked=False, p=profile.path: self._open_profile(p))
            menu.addAction(action)

    def _open_profile(self, path: Path) -> None:
        try:
            session = self._network.open_device(path)
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Unable to open profile"), str(exc))
            return
        self._add_session(session)

    def _show_command_palette(self) -> None:
        commands = self._default_commands()
        if self._palette is None:
            self._palette = CommandPalette(commands, self)
        else:
            self._palette.set_commands(commands)
        self._palette.reset()
        self._palette.open()

    def _default_commands(self) -> List[Command]:
        commands = [
            Command(self.tr("New Device"), self._new_device, shortcut="Ctrl+N"),
            Command(self.tr("Open Device"), self._open_device_dialog, shortcut="Ctrl+O"),
            Command(self.tr("Export CANopenNode Sources"), self._export_current_session, shortcut="Ctrl+E"),
            Command(self.tr("Add Object Entry"), self._add_object_entry, shortcut="Ctrl+Shift+N"),
            Command(self.tr("Toggle Dark Mode"), self._toggle_theme_action, shortcut="Ctrl+Shift+L"),
            Command(self.tr("Show Validation Report"), self._show_validation_report_tab),
        ]
        return commands

    def _offer_mandatory_object_fix(self, page: DeviceEditorPage, session: DeviceSession) -> None:
        missing = [issue for issue in page.issues if issue.code == "MISSING_OBJECT"]
        if not missing:
            return

        bullet_list = "\n".join(f"• {issue.message}" for issue in missing)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(self.tr("Missing mandatory objects"))
        box.setText(self.tr("Some mandatory CANopen objects are missing."))
        box.setInformativeText(
            self.tr(
                "{details}\n\nWould you like to add the standard CiA 301 entries automatically?"
            ).format(details=bullet_list)
        )
        fix_button = box.addButton(self.tr("Add Automatically"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(self.tr("Ignore"), QMessageBox.ButtonRole.RejectRole)

        box.exec()
        if box.clickedButton() is not fix_button:
            return

        updated = self._network.apply_minimal_profile(session.identifier)
        if not updated:
            self._status.showMessage(
                self.tr("No changes applied; device already contains the minimal profile."), 5000
            )
            return

        page.set_device(session.device)
        self._update_context_widgets()
        indexes = ", ".join(f"0x{index:04X}" for index in updated)
        self._status.showMessage(
            self.tr("Added missing mandatory objects: {indexes}").format(indexes=indexes), 7000
        )

    def _current_page(self) -> DeviceEditorPage | None:
        widget = self._tabs.currentWidget()
        return widget if isinstance(widget, DeviceEditorPage) else None

    def _current_session(self) -> DeviceSession | None:
        page = self._current_page()
        if page is None:
            return None
        return self._pages.get(page)

    def _add_object_entry(self) -> None:
        session = self._current_session()
        if session is None:
            return

        dialog = AddObjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        request = dialog.request()
        if request is None:
            return

        entry = AddObjectDialog.create_entry(request)
        try:
            self._network.insert_object(session.identifier, entry)
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Unable to add object"), str(exc))
            return

        page = self._tabs.currentWidget()
        if isinstance(page, DeviceEditorPage):
            page.set_device(session.device)
        self._update_context_widgets()
        self._status.showMessage(
            self.tr("Added object 0x{index:04X}").format(index=entry.index),
            5000,
        )

    def _new_device(self) -> None:
        buttons = (
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel
        )
        choice = QMessageBox.question(
            self,
            self.tr("Create New Device"),
            self.tr(
                "Load minimal standard profile entries?\n\n"
                "Choose 'Yes' to start with required CiA 301 identity objects,"
                " 'No' for a completely empty dictionary, or 'Cancel' to abort."
            ),
            buttons,
            QMessageBox.StandardButton.Yes,
        )

        if choice == QMessageBox.StandardButton.Cancel:
            return

        session = self._network.create_device(include_minimal_profile=choice == QMessageBox.StandardButton.Yes)
        self._add_session(session)
        self._status.showMessage(
            self.tr("Created {name}").format(name=session.identifier),
            5000,
        )

    def _show_validation_report_tab(self) -> None:
        page = self._current_page()
        if page is None:
            return
        page.show_validation_report()

    def _toggle_theme_action(self) -> None:
        if self._toggle_theme is not None:
            self._toggle_theme()

    def _show_about_dialog(self) -> None:
        QMessageBox.information(
            self,
            self.tr("About CANopenNode Editor"),
            self.tr(
                "<p><strong>CANopenNode Editor</strong><br/>"
                "Modern Python port of the legacy editor with CANopenNode export support."),
        )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_window_state()
        super().closeEvent(event)
