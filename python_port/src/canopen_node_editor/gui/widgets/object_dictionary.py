"""Object dictionary dock widget."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QPushButton,
    QTreeView,
    QWidget,
    QVBoxLayout,
)

from ...model import Device, ObjectEntry
from ..models.object_dictionary import ObjectDictionaryModel, iter_selected_payloads


class ObjectDictionaryWidget(QWidget):
    """Widget presenting the CANopen object dictionary."""

    selectionChanged = Signal(object, object)
    addEntryRequested = Signal()

    def __init__(
        self,
        parent=None,
        *,
        include_subindices: bool = True,
        editable: bool = True,
        show_add_button: bool = True,
    ) -> None:
        super().__init__(parent)
        self._model = ObjectDictionaryModel(
            self,
            include_subindices=include_subindices,
            editable=editable,
        )
        self._include_subindices = include_subindices
        self._add_button = QPushButton(self.tr("Add Object"), self)
        self._add_button.clicked.connect(self.addEntryRequested.emit)
        self._add_button.setVisible(show_add_button)

        self._tree = QTreeView(self)
        self._tree.setModel(self._model)
        self._tree.setUniformRowHeights(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setRootIsDecorated(include_subindices)
        if not editable:
            self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.expandAll()
        self._tree.selectionModel().selectionChanged.connect(self._on_selection_changed)
        if editable:
            self._model.valueEdited.connect(self._on_value_edited)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._add_button)
        layout.addWidget(self._tree)

    # ------------------------------------------------------------------
    def set_device(self, device: Device | None) -> None:
        self._model.set_device(device)
        self._add_button.setEnabled(device is not None)
        self._tree.expandToDepth(0)
        if device:
            self._tree.resizeColumnToContents(0)

    def model(self) -> ObjectDictionaryModel:
        return self._model

    def tree(self) -> QTreeView:
        return self._tree

    def can_add_entries(self) -> bool:
        return self._add_button.isEnabled()

    def refresh(self, entry: ObjectEntry | None = None) -> None:
        current_index = entry.index if entry else self._selected_entry_index()
        self._model.refresh()
        self._tree.expandToDepth(0)
        if current_index is not None:
            self._select_entry_by_index(current_index)

    # ------------------------------------------------------------------
    def _on_selection_changed(self, selected, _deselected) -> None:
        indexes = selected.indexes()
        for entry, sub in iter_selected_payloads(indexes, self._model):
            self.selectionChanged.emit(entry, sub)

    def _on_value_edited(self, entry, sub) -> None:
        selection_model = self._tree.selectionModel()
        if selection_model is None:
            return
        selected = list(
            iter_selected_payloads(selection_model.selectedIndexes(), self._model)
        )
        for current_entry, current_sub in selected:
            if current_entry is entry and current_sub is sub:
                self.selectionChanged.emit(entry, sub)
                break

    def select_first_row(self) -> None:
        if self._model.rowCount() == 0:
            return
        index = self._model.index(0, 0)
        if isinstance(index, QModelIndex) and index.isValid():
            self._tree.setCurrentIndex(index)

    def select_entry(self, entry: ObjectEntry) -> None:
        self._select_entry_by_index(entry.index)

    def _selected_entry_index(self) -> int | None:
        selection_model = self._tree.selectionModel()
        if selection_model is None:
            return None
        for entry, _ in iter_selected_payloads(
            selection_model.selectedIndexes(), self._model
        ):
            return entry.index
        return None

    def _select_entry_by_index(self, index_value: int) -> None:
        for row in range(self._model.rowCount()):
            item = self._model.item(row, 0)
            if item is None:
                continue
            data = item.data(Qt.UserRole)
            if not isinstance(data, tuple):
                continue
            entry, _ = data
            if isinstance(entry, ObjectEntry) and entry.index == index_value:
                index = self._model.index(row, 0)
                if index.isValid():
                    self._tree.setCurrentIndex(index)
                break
