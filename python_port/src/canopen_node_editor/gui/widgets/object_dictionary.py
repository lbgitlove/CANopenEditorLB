"""Object dictionary browser aligned with the Avalonia UI layout."""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import QModelIndex, Qt, QSortFilterProxyModel, Signal
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ...model import Device, ObjectEntry
from ..models.object_dictionary import ObjectDictionaryModel


class ObjectDictionaryWidget(QWidget):
    """Widget presenting the CANopen object dictionary grouped by index ranges."""

    selectionChanged = Signal(object, object)
    addEntryRequested = Signal()

    _SECTION_LAYOUT = (
        ("Communication Specific Parameters", 0x1000, 0x1FFF),
        ("Manufacturer Specific Parameters", 0x2000, 0x5FFF),
        ("Device Profile Specific Parameters", 0x6000, 0x9FFF),
    )

    def __init__(
        self,
        parent=None,
        *,
        include_subindices: bool = False,
        editable: bool = False,
        show_add_button: bool = True,
    ) -> None:
        super().__init__(parent)
        self._model = ObjectDictionaryModel(
            self,
            include_subindices=include_subindices,
            editable=editable,
        )
        self._device: Device | None = None
        self._add_button = QPushButton(self.tr("Add Object"), self)
        self._add_button.clicked.connect(self.addEntryRequested.emit)
        self._add_button.setVisible(show_add_button)

        self._sections: list[_ObjectDictionarySection] = []
        for title, start, end in self._SECTION_LAYOUT:
            section = _ObjectDictionarySection(title, start, end, self._model, self)
            section.entryActivated.connect(partial(self._on_entry_activated, section))
            self._sections.append(section)

        splitter = QSplitter(Qt.Vertical, self)
        splitter.setChildrenCollapsible(False)
        for section in self._sections:
            splitter.addWidget(section)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._add_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(splitter, stretch=1)

    # ------------------------------------------------------------------
    def set_device(self, device: Device | None) -> None:
        self._device = device
        self._model.set_device(device)
        self._add_button.setEnabled(device is not None)
        for section in self._sections:
            section.reset_view()
        if device is None:
            self.selectionChanged.emit(None, None)

    def model(self) -> ObjectDictionaryModel:
        return self._model

    def can_add_entries(self) -> bool:
        return self._add_button.isEnabled()

    def current_entry(self) -> ObjectEntry | None:
        for section in self._sections:
            entry = section.current_entry()
            if entry is not None:
                return entry
        return None

    def has_entries(self) -> bool:
        return self._model.rowCount() > 0

    def refresh(self, entry: ObjectEntry | None = None) -> None:
        index_value = entry.index if entry is not None else self._selected_entry_index()
        self._model.refresh()
        for section in self._sections:
            section.reset_view()
        if index_value is not None:
            self._select_entry_by_index(index_value)

    def select_first_entry(self) -> bool:
        for section in self._sections:
            if section.select_first_entry():
                return True
        return False

    def select_entry(self, entry: ObjectEntry) -> None:
        self._select_entry_by_index(entry.index)

    # ------------------------------------------------------------------
    def _selected_entry_index(self) -> int | None:
        current = self.current_entry()
        return current.index if current else None

    def _select_entry_by_index(self, index_value: int) -> None:
        for section in self._sections:
            if section.select_entry(index_value):
                self._on_entry_activated(section, section.current_entry())
                break

    def _on_entry_activated(
        self, section: _ObjectDictionarySection, entry: ObjectEntry | None
    ) -> None:
        if entry is None:
            return
        for other in self._sections:
            if other is section:
                continue
            other.clear_selection()
        self.selectionChanged.emit(entry, None)


class _ObjectDictionarySection(QFrame):
    """Container displaying a filtered view of object entries."""

    entryActivated = Signal(ObjectEntry)

    def __init__(
        self,
        title: str,
        start_index: int,
        end_index: int,
        model: ObjectDictionaryModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._start = start_index
        self._end = end_index
        self._model = model
        self._current_entry: ObjectEntry | None = None
        self._suppress_selection = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        self._proxy = _ObjectRangeProxyModel(start_index, end_index, self)
        self._proxy.setSourceModel(model)

        self._view = QTreeView(self)
        self._view.setModel(self._proxy)
        self._view.setRootIsDecorated(False)
        self._view.setAlternatingRowColors(True)
        self._view.setUniformRowHeights(True)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._view.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for column in range(2, model.columnCount()):
            self._view.setColumnHidden(column, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        heading = QLabel(self.tr(title), self)
        heading.setObjectName("odSectionHeading")
        layout.addWidget(heading)
        layout.addWidget(self._view, stretch=1)

        self._proxy_model_changed()
        model.modelReset.connect(self._proxy_model_changed)
        model.dataChanged.connect(self._proxy_model_changed)
        model.rowsInserted.connect(self._proxy_model_changed)
        model.rowsRemoved.connect(self._proxy_model_changed)

    # ------------------------------------------------------------------
    def reset_view(self) -> None:
        self._current_entry = None
        self.clear_selection()
        self._view.viewport().update()
        self._proxy.invalidate()

    def current_entry(self) -> ObjectEntry | None:
        return self._current_entry

    def select_first_entry(self) -> bool:
        if self._proxy.rowCount() == 0:
            return False
        self._select_row(0)
        return True
        return False

    def select_entry(self, index_value: int) -> bool:
        for row in range(self._proxy.rowCount()):
            entry = self._entry_at_row(row)
            if entry is None:
                continue
            if entry.index == index_value:
                self._select_row(row)
                return True
        return False

    def clear_selection(self) -> None:
        model = self._view.selectionModel()
        if model is None:
            return
        self._suppress_selection = True
        model.clearSelection()
        model.clearCurrentIndex()
        self._suppress_selection = False
        self._current_entry = None

    # ------------------------------------------------------------------
    def _select_row(self, row: int) -> None:
        index = self._proxy.index(row, 0)
        if not isinstance(index, QModelIndex) or not index.isValid():
            return
        entry = self._entry_from_index(index)
        if entry is None:
            return
        self._suppress_selection = True
        selection_model = self._view.selectionModel()
        if selection_model is None:
            self._suppress_selection = False
            return
        selection_model.setCurrentIndex(
            index,
            QAbstractItemView.SelectionFlag.ClearAndSelect
            | QAbstractItemView.SelectionFlag.Rows,
        )
        self._view.scrollTo(index, QTreeView.ScrollHint.PositionAtCenter)
        self._suppress_selection = False
        self._current_entry = entry

    def _entry_at_row(self, row: int) -> ObjectEntry | None:
        index = self._proxy.index(row, 0)
        return self._entry_from_index(index)

    def _entry_from_index(self, index: QModelIndex) -> ObjectEntry | None:
        if not isinstance(index, QModelIndex) or not index.isValid():
            return None
        source_index = self._proxy.mapToSource(index)
        item = self._model.itemFromIndex(source_index)
        if not isinstance(item, QStandardItem):
            return None
        data = item.data(Qt.UserRole)
        if not isinstance(data, tuple):
            return None
        entry, sub = data
        if isinstance(entry, ObjectEntry) and sub is None:
            return entry
        return None

    def _on_selection_changed(self, selected, _deselected) -> None:
        if self._suppress_selection:
            return
        indexes = selected.indexes()
        for index in indexes:
            entry = self._entry_from_index(index)
            if entry is None:
                continue
            self._current_entry = entry
            self.entryActivated.emit(entry)
            break

    def _proxy_model_changed(self) -> None:
        self._proxy.invalidateFilter()
        selection_model = self._view.selectionModel()
        if selection_model is None:
            return
        try:
            selection_model.selectionChanged.disconnect(self._on_selection_changed)
        except (TypeError, RuntimeError):
            pass
        selection_model.selectionChanged.connect(self._on_selection_changed)


class _ObjectRangeProxyModel(QSortFilterProxyModel):
    """Filters the shared dictionary model to a specific index range."""

    def __init__(self, start: int, end: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._start = start
        self._end = end

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # type: ignore[override]
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, 0, source_parent)
        if not index.isValid():
            return False
        item = model.itemFromIndex(index)
        if not isinstance(item, QStandardItem):
            return False
        data = item.data(Qt.UserRole)
        if not isinstance(data, tuple):
            return False
        entry, sub = data
        if not isinstance(entry, ObjectEntry) or sub is not None:
            return False
        return self._start <= entry.index <= self._end


