"""Object dictionary dock widget."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtWidgets import QTreeView, QWidget, QVBoxLayout

from ...model import Device
from ..models.object_dictionary import ObjectDictionaryModel, iter_selected_payloads


class ObjectDictionaryWidget(QWidget):
    """Widget presenting the CANopen object dictionary."""

    selectionChanged = Signal(object, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model = ObjectDictionaryModel(self)
        self._tree = QTreeView(self)
        self._tree.setModel(self._model)
        self._tree.setUniformRowHeights(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setRootIsDecorated(True)
        self._tree.expandAll()
        self._tree.selectionModel().selectionChanged.connect(self._on_selection_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tree)

    # ------------------------------------------------------------------
    def set_device(self, device: Device | None) -> None:
        self._model.set_device(device)
        self._tree.expandToDepth(0)
        if device:
            self._tree.resizeColumnToContents(0)

    def model(self) -> ObjectDictionaryModel:
        return self._model

    def tree(self) -> QTreeView:
        return self._tree

    # ------------------------------------------------------------------
    def _on_selection_changed(self, selected, _deselected) -> None:
        indexes = selected.indexes()
        for entry, sub in iter_selected_payloads(indexes, self._model):
            self.selectionChanged.emit(entry, sub)

    def select_first_row(self) -> None:
        if self._model.rowCount() == 0:
            return
        index = self._model.index(0, 0)
        if isinstance(index, QModelIndex) and index.isValid():
            self._tree.setCurrentIndex(index)
