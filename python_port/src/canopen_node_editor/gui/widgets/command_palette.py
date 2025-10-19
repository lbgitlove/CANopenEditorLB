"""A simple command palette inspired by modern IDEs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout


@dataclass
class Command:
    text: str
    callback: Callable[[], None]
    shortcut: str | None = None


class CommandPalette(QDialog):
    """Modal dialog providing quick command search."""

    def __init__(self, commands: Iterable[Command], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Command Palette"))
        self.setModal(True)
        self.resize(400, 320)

        self._commands: List[Command] = list(commands)

        self._filter = QLineEdit(self)
        self._filter.setPlaceholderText(self.tr("Search commands"))
        self._filter.textChanged.connect(self._rebuild)

        self._list = QListWidget(self)
        self._list.itemActivated.connect(self._accept_current)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel, parent=self)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._filter)
        layout.addWidget(self._list)
        layout.addWidget(buttons)

        self._rebuild()

    def reset(self) -> None:
        self._filter.clear()
        self._rebuild()

    def _rebuild(self) -> None:
        query = self._filter.text().strip().lower()
        self._list.clear()
        for command in self._commands:
            if query and query not in command.text.lower():
                continue
            label = command.text
            if command.shortcut:
                label = f"{label} ({command.shortcut})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, command)
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _accept_current(self, item: QListWidgetItem) -> None:
        command = item.data(Qt.UserRole)
        if not command:
            return
        self.accept()
        command.callback()

    def set_commands(self, commands: Iterable[Command]) -> None:
        self._commands = list(commands)
        self._rebuild()
