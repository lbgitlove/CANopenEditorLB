"""Object dictionary dock widget."""

from __future__ import annotations

from functools import partial
from typing import Optional

from PySide6.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableView,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ...model import Device, ObjectEntry, SubObject
from ..models.object_dictionary import ObjectDictionaryModel


class IndexRangeProxyModel(QSortFilterProxyModel):
    """Filter model exposing only entries within a specific index range."""

    def __init__(self, minimum: int, maximum: int, parent=None) -> None:
        super().__init__(parent)
        self._minimum = minimum
        self._maximum = maximum
        self.setDynamicSortFilter(True)

    # ------------------------------------------------------------------
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # type: ignore[override]
        if source_parent.isValid():
            return False
        source = self.sourceModel()
        if source is None:
            return False
        index = source.index(source_row, 0, source_parent)
        if not index.isValid():
            return False
        data = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple):
            return False
        entry, sub = data
        if sub is not None:
            return False
        if not isinstance(entry, ObjectEntry):
            return False
        return self._minimum <= entry.index <= self._maximum

    def filterAcceptsColumn(self, source_column: int, _source_parent: QModelIndex) -> bool:  # type: ignore[override]
        # Only expose the index and name columns for list views.
        return source_column in (0, 1)


class SubObjectTableModel(QAbstractTableModel):
    """Table model presenting sub-objects for the selected entry."""

    HEADERS = ("Sub", "Name", "Data Type", "SDO", "PDO", "Default Value")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entry: ObjectEntry | None = None
        self._rows: list[tuple[int, SubObject]] = []

    # ------------------------------------------------------------------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # type: ignore[override]
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return None
        if index.row() >= len(self._rows):
            return None

        subindex, sub = self._rows[index.row()]
        column = index.column()

        if column == 0:
            return str(subindex)
        if column == 1:
            return sub.name or "—"
        if column == 2:
            return sub.data_type.name
        if column == 3:
            return sub.access_type.name
        if column == 4:
            return sub.pdo_mapping.name if sub.pdo_mapping else "—"
        if column == 5:
            return sub.default or "—"
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):  # type: ignore[override]
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            try:
                return self.HEADERS[section]
            except IndexError:
                return None
        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:  # type: ignore[override]
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ------------------------------------------------------------------
    def set_entry(self, entry: ObjectEntry | None) -> None:
        self.beginResetModel()
        self._entry = entry
        if entry is None:
            self._rows = []
        else:
            self._rows = sorted(entry.sub_objects.items())
        self.endResetModel()

    def subobject_at(self, row: int) -> SubObject | None:
        if 0 <= row < len(self._rows):
            return self._rows[row][1]
        return None


class ObjectDictionaryWidget(QWidget):
    """Widget presenting the CANopen object dictionary."""

    selectionChanged = Signal(object, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model = ObjectDictionaryModel(self)
        self._active_entry: ObjectEntry | None = None

        self._ranges: list[tuple[QTreeView, IndexRangeProxyModel]] = []
        self._sub_model = SubObjectTableModel(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        left_splitter = QSplitter(Qt.Orientation.Vertical, splitter)
        left_splitter.setChildrenCollapsible(False)

        for title, lower, upper in (
            (self.tr("Communication Parameters"), 0x1000, 0x1FFF),
            (self.tr("Manufacturer Parameters"), 0x2000, 0x5FFF),
            (self.tr("Device Profile Parameters"), 0x6000, 0x9FFF),
        ):
            proxy = IndexRangeProxyModel(lower, upper, self)
            proxy.setSourceModel(self._model)

            view = QTreeView(self)
            view.setModel(proxy)
            view.setUniformRowHeights(True)
            view.setAlternatingRowColors(True)
            view.setRootIsDecorated(False)
            view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            view.setAllColumnsShowFocus(True)
            view.hideColumn(2)
            view.hideColumn(3)
            header = view.header()
            header.setStretchLastSection(True)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)

            group = QGroupBox(title, self)
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(4, 8, 4, 4)
            group_layout.addWidget(view)
            left_splitter.addWidget(group)

            view.selectionModel().selectionChanged.connect(
                partial(self._on_entry_selection_changed, view)
            )
            self._ranges.append((view, proxy))

        right_splitter = QSplitter(Qt.Orientation.Vertical, splitter)
        right_splitter.setChildrenCollapsible(False)

        # Sub-object table -------------------------------------------------
        sub_group = QGroupBox(self.tr("Sub-Objects"), self)
        sub_layout = QVBoxLayout(sub_group)
        sub_layout.setContentsMargins(4, 8, 4, 4)

        self._sub_table = QTableView(self)
        self._sub_table.setModel(self._sub_model)
        self._sub_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._sub_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._sub_table.setAlternatingRowColors(True)
        self._sub_table.setSortingEnabled(False)
        self._sub_table.horizontalHeader().setStretchLastSection(True)
        self._sub_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._sub_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._sub_table.verticalHeader().setVisible(False)
        sub_layout.addWidget(self._sub_table)
        right_splitter.addWidget(sub_group)

        # Detail panel -----------------------------------------------------
        detail_group = QGroupBox(self.tr("Selection Details"), self)
        detail_layout = QFormLayout(detail_group)
        detail_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._detail_labels: dict[str, QLabel] = {}
        for key, label in (
            ("index", self.tr("Index")),
            ("subindex", self.tr("SubIndex")),
            ("name", self.tr("Name")),
            ("type", self.tr("Data Type")),
            ("access", self.tr("Access")),
            ("default", self.tr("Default")),
            ("value", self.tr("Value")),
        ):
            value_label = QLabel("—", self)
            value_label.setObjectName(f"objectDetail_{key}")
            detail_layout.addRow(label + ":", value_label)
            self._detail_labels[key] = value_label

        right_splitter.addWidget(detail_group)

        splitter.setStretchFactor(splitter.indexOf(left_splitter), 0)
        splitter.setStretchFactor(splitter.indexOf(right_splitter), 1)

        self._sub_table.selectionModel().selectionChanged.connect(self._on_sub_selection_changed)
        self._update_details(None, None)

    # ------------------------------------------------------------------
    def set_device(self, device: Device | None) -> None:
        self._model.set_device(device)
        self._active_entry = None
        self._sub_model.set_entry(None)
        for view, _proxy in self._ranges:
            view.selectionModel().clearSelection()
        self._update_details(None, None)
        if device:
            for view, proxy in self._ranges:
                if proxy.rowCount() > 0:
                    view.expandAll()
                    view.resizeColumnToContents(0)
                    view.header().setStretchLastSection(True)

    def model(self) -> ObjectDictionaryModel:
        return self._model

    def tree(self) -> QTreeView:
        """Compatibility shim returning the communication view."""

        return self._ranges[0][0] if self._ranges else QTreeView(self)

    # ------------------------------------------------------------------
    def select_first_row(self) -> None:
        for view, proxy in self._ranges:
            if proxy.rowCount() == 0:
                continue
            index = proxy.index(0, 0)
            if not index.isValid():
                continue
            selection_model = view.selectionModel()
            selection_model.select(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            view.setCurrentIndex(index)
            view.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtTop)
            return

    # ------------------------------------------------------------------
    def _on_entry_selection_changed(
        self, view: QTreeView, selected: QItemSelection, _deselected: QItemSelection
    ) -> None:
        if selected.isEmpty():
            return
        index = next((idx for idx in selected.indexes() if idx.column() == 0), None)
        if index is None:
            return
        entry = self._entry_from_index(view, index)
        if entry is None:
            return

        # Clear selections in sibling lists to keep a single active entry.
        for other_view, _ in self._ranges:
            if other_view is not view:
                other_view.selectionModel().blockSignals(True)
                other_view.selectionModel().clearSelection()
                other_view.selectionModel().blockSignals(False)

        self._select_entry(entry)

    def _on_sub_selection_changed(
        self, selected: QItemSelection, _deselected: QItemSelection
    ) -> None:
        entry = self._active_entry
        if entry is None:
            return
        if selected.isEmpty():
            self.selectionChanged.emit(entry, None)
            self._update_details(entry, None)
            return

        index = next((idx for idx in selected.indexes() if idx.column() == 0), None)
        if index is None:
            self.selectionChanged.emit(entry, None)
            self._update_details(entry, None)
            return
        sub = self._sub_model.subobject_at(index.row())
        if sub is not None:
            self.selectionChanged.emit(entry, sub)
            self._update_details(entry, sub)

    # ------------------------------------------------------------------
    def _entry_from_index(self, view: QTreeView, index: QModelIndex) -> Optional[ObjectEntry]:
        model = view.model()
        if isinstance(model, QSortFilterProxyModel):
            source_index = model.mapToSource(index)
        else:
            source_index = index
        if not source_index.isValid():
            return None
        data = source_index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple):
            return None
        entry, sub = data
        if sub is not None or not isinstance(entry, ObjectEntry):
            return None
        return entry

    def _select_entry(self, entry: ObjectEntry) -> None:
        self._active_entry = entry
        self._sub_model.set_entry(entry)
        self._sub_table.selectionModel().clearSelection()
        self.selectionChanged.emit(entry, None)
        self._update_details(entry, None)

    def _update_details(self, entry: ObjectEntry | None, sub: SubObject | None) -> None:
        def set_value(key: str, value: str) -> None:
            label = self._detail_labels.get(key)
            if label is not None:
                label.setText(value if value else "—")

        if entry is None:
            for key in self._detail_labels:
                self._detail_labels[key].setText("—")
            return

        set_value("index", f"0x{entry.index:04X}")
        set_value("name", entry.name or "")
        set_value("type", entry.data_type.name if entry.data_type else "")
        set_value("access", entry.access_type.name if entry.access_type else "")
        set_value("default", entry.default or "")
        set_value("value", entry.value or "")

        if sub is None:
            set_value("subindex", "—")
        else:
            subindex = getattr(getattr(sub, "key", None), "subindex", None)
            set_value("subindex", str(subindex) if subindex is not None else "?")
            set_value("name", sub.name or "")
            set_value("type", sub.data_type.name)
            set_value("access", sub.access_type.name)
            set_value("default", sub.default or "")
            set_value("value", sub.value or "")
