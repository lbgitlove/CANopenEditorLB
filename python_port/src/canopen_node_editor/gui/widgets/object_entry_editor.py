"""Editor widget for mutating object dictionary entries."""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...model import ObjectEntry, SubObject
from ...model.enums import AccessType, DataType, ObjectType, PDOMapping


class ObjectEntryEditorWidget(QWidget):
    """Provides editable fields for an object entry and its sub-indices."""

    entryChanged = Signal(ObjectEntry)
    subEntryChanged = Signal(ObjectEntry, SubObject)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entry: ObjectEntry | None = None
        self._current_sub: SubObject | None = None
        self._updating_entry = False
        self._updating_sub = False

        self._entry_group = QGroupBox(self.tr("Object Entry"), self)
        entry_form = QFormLayout(self._entry_group)

        self._entry_name = QLineEdit(self._entry_group)
        self._entry_object_type = QComboBox(self._entry_group)
        self._entry_data_type = QComboBox(self._entry_group)
        self._entry_access = QComboBox(self._entry_group)
        self._entry_default = QLineEdit(self._entry_group)
        self._entry_value = QLineEdit(self._entry_group)
        self._entry_minimum = QLineEdit(self._entry_group)
        self._entry_maximum = QLineEdit(self._entry_group)
        self._entry_pdo = QComboBox(self._entry_group)

        entry_form.addRow(self.tr("Name"), self._entry_name)
        entry_form.addRow(self.tr("Object Type"), self._entry_object_type)
        entry_form.addRow(self.tr("Data Type"), self._entry_data_type)
        entry_form.addRow(self.tr("Access"), self._entry_access)
        entry_form.addRow(self.tr("Default"), self._entry_default)
        entry_form.addRow(self.tr("Value"), self._entry_value)
        entry_form.addRow(self.tr("Minimum"), self._entry_minimum)
        entry_form.addRow(self.tr("Maximum"), self._entry_maximum)
        entry_form.addRow(self.tr("PDO Mapping"), self._entry_pdo)

        self._sub_table = QTableWidget(self)
        self._sub_table.setColumnCount(7)
        self._sub_table.setHorizontalHeaderLabels(
            [
                self.tr("Sub"),
                self.tr("Name"),
                self.tr("Data Type"),
                self.tr("SDO"),
                self.tr("PDO"),
                self.tr("SRDO"),
                self.tr("Default Value"),
            ]
        )
        self._sub_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._sub_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._sub_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._sub_table.setAlternatingRowColors(True)
        self._sub_table.verticalHeader().setVisible(False)
        header = self._sub_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for column in range(2, self._sub_table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

        self._sub_group = QGroupBox(self.tr("Sub-Index Details"), self)
        self._sub_form_container = QWidget(self._sub_group)
        self._sub_form = QFormLayout(self._sub_form_container)
        self._sub_index_label = QLabel("-", self._sub_form_container)
        self._sub_name = QLineEdit(self._sub_form_container)
        self._sub_data_type = QComboBox(self._sub_form_container)
        self._sub_access = QComboBox(self._sub_form_container)
        self._sub_default = QLineEdit(self._sub_form_container)
        self._sub_value = QLineEdit(self._sub_form_container)
        self._sub_minimum = QLineEdit(self._sub_form_container)
        self._sub_maximum = QLineEdit(self._sub_form_container)
        self._sub_pdo = QComboBox(self._sub_form_container)

        self._sub_form.addRow(self.tr("SubIndex"), self._sub_index_label)
        self._sub_form.addRow(self.tr("Name"), self._sub_name)
        self._sub_form.addRow(self.tr("Data Type"), self._sub_data_type)
        self._sub_form.addRow(self.tr("Access"), self._sub_access)
        self._sub_form.addRow(self.tr("Default"), self._sub_default)
        self._sub_form.addRow(self.tr("Value"), self._sub_value)
        self._sub_form.addRow(self.tr("Minimum"), self._sub_minimum)
        self._sub_form.addRow(self.tr("Maximum"), self._sub_maximum)
        self._sub_form.addRow(self.tr("PDO Mapping"), self._sub_pdo)

        sub_group_layout = QVBoxLayout(self._sub_group)
        sub_group_layout.setContentsMargins(8, 8, 8, 8)
        sub_group_layout.addWidget(self._sub_form_container)

        sub_splitter = QSplitter(Qt.Orientation.Vertical, self)
        sub_splitter.setChildrenCollapsible(False)
        sub_splitter.addWidget(self._sub_table)
        sub_splitter.addWidget(self._sub_group)
        sub_splitter.setStretchFactor(0, 2)
        sub_splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout(self)
        layout.addWidget(self._entry_group)
        layout.addWidget(sub_splitter, stretch=1)

        self._populate_enum_combo(self._entry_object_type, ObjectType, allow_none=True)
        self._populate_enum_combo(self._entry_data_type, DataType, allow_none=True)
        self._populate_enum_combo(self._entry_access, AccessType, allow_none=True)
        self._populate_enum_combo(self._entry_pdo, PDOMapping, allow_none=True)

        self._populate_enum_combo(self._sub_data_type, DataType, allow_none=False)
        self._populate_enum_combo(self._sub_access, AccessType, allow_none=False)
        self._populate_enum_combo(self._sub_pdo, PDOMapping, allow_none=True)

        self._bind_entry_signals()
        self._bind_sub_signals()
        self._set_entry_enabled(False)
        self._set_sub_enabled(False)

    # ------------------------------------------------------------------
    def set_entry(self, entry: ObjectEntry | None) -> None:
        self._entry = entry
        self._updating_entry = True

        if entry is None:
            self._clear_entry_fields()
            self._set_entry_enabled(False)
            self._sub_table.setRowCount(0)
            self._load_sub_object(None)
            self._sub_table.setEnabled(False)
            self._updating_entry = False
            return

        self._set_entry_enabled(True)
        self._sub_table.setEnabled(True)
        self._entry_name.setText(entry.name or "")
        self._set_combo_value(self._entry_object_type, entry.object_type)
        self._set_combo_value(self._entry_data_type, entry.data_type)
        self._set_combo_value(self._entry_access, entry.access_type)
        self._entry_default.setText(entry.default or "")
        self._entry_value.setText(entry.value or "")
        self._entry_minimum.setText(entry.minimum or "")
        self._entry_maximum.setText(entry.maximum or "")
        self._set_combo_value(self._entry_pdo, entry.pdo_mapping)

        self._sub_table.blockSignals(True)
        self._sub_table.setRowCount(0)
        for row, (subindex, sub) in enumerate(sorted(entry.sub_objects.items())):
            self._sub_table.insertRow(row)
            index_item = QTableWidgetItem(f"{subindex:02X}")
            index_item.setData(Qt.UserRole, sub)
            name_item = QTableWidgetItem(sub.name or self.tr("SubIndex"))
            type_item = QTableWidgetItem(sub.data_type.name)
            sdo_item = QTableWidgetItem(sub.access_type.name)
            pdo_text = sub.pdo_mapping.name if sub.pdo_mapping else ""
            pdo_item = QTableWidgetItem(pdo_text)
            srdo_item = QTableWidgetItem("")
            default_item = QTableWidgetItem(sub.default or "")

            for column, item in enumerate(
                (index_item, name_item, type_item, sdo_item, pdo_item, srdo_item, default_item)
            ):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._sub_table.setItem(row, column, item)
        self._sub_table.blockSignals(False)

        if self._sub_table.rowCount() > 0:
            self._sub_table.selectRow(0)
            self._load_sub_object(self._sub_object_for_row(0))
        else:
            self._load_sub_object(None)

        self._updating_entry = False

    # ------------------------------------------------------------------
    def _bind_entry_signals(self) -> None:
        self._entry_name.textEdited.connect(self._on_entry_name_changed)
        self._entry_object_type.currentIndexChanged.connect(
            partial(self._on_entry_combo_changed, self._entry_object_type, "object_type")
        )
        self._entry_data_type.currentIndexChanged.connect(
            partial(self._on_entry_combo_changed, self._entry_data_type, "data_type")
        )
        self._entry_access.currentIndexChanged.connect(
            partial(self._on_entry_combo_changed, self._entry_access, "access_type")
        )
        self._entry_default.textEdited.connect(
            partial(self._on_entry_text_changed, "default", self._entry_default)
        )
        self._entry_value.textEdited.connect(
            partial(self._on_entry_text_changed, "value", self._entry_value)
        )
        self._entry_minimum.textEdited.connect(
            partial(self._on_entry_text_changed, "minimum", self._entry_minimum)
        )
        self._entry_maximum.textEdited.connect(
            partial(self._on_entry_text_changed, "maximum", self._entry_maximum)
        )
        self._entry_pdo.currentIndexChanged.connect(
            partial(self._on_entry_combo_changed, self._entry_pdo, "pdo_mapping")
        )

    def _bind_sub_signals(self) -> None:
        selection_model = self._sub_table.selectionModel()
        if selection_model is not None:
            selection_model.selectionChanged.connect(self._on_sub_selection_changed)
        self._sub_table.itemSelectionChanged.connect(self._on_sub_selection_changed)
        self._sub_name.textEdited.connect(self._on_sub_name_changed)
        self._sub_data_type.currentIndexChanged.connect(
            partial(self._on_sub_combo_changed, self._sub_data_type, "data_type")
        )
        self._sub_access.currentIndexChanged.connect(
            partial(self._on_sub_combo_changed, self._sub_access, "access_type")
        )
        self._sub_default.textEdited.connect(
            partial(self._on_sub_text_changed, "default", self._sub_default)
        )
        self._sub_value.textEdited.connect(
            partial(self._on_sub_text_changed, "value", self._sub_value)
        )
        self._sub_minimum.textEdited.connect(
            partial(self._on_sub_text_changed, "minimum", self._sub_minimum)
        )
        self._sub_maximum.textEdited.connect(
            partial(self._on_sub_text_changed, "maximum", self._sub_maximum)
        )
        self._sub_pdo.currentIndexChanged.connect(
            partial(self._on_sub_combo_changed, self._sub_pdo, "pdo_mapping")
        )

    # ------------------------------------------------------------------
    def _on_entry_name_changed(self, text: str) -> None:
        if self._entry is None or self._updating_entry:
            return
        self._entry.name = text.strip() or None
        self.entryChanged.emit(self._entry)

    def _on_entry_text_changed(self, field: str, widget: QLineEdit) -> None:
        if self._entry is None or self._updating_entry:
            return
        value = widget.text().strip() or None
        setattr(self._entry, field, value)
        self.entryChanged.emit(self._entry)

    def _on_entry_combo_changed(self, combo: QComboBox, field: str) -> None:
        if self._entry is None or self._updating_entry:
            return
        value = combo.currentData(Qt.UserRole)
        setattr(self._entry, field, value)
        self.entryChanged.emit(self._entry)

    # ------------------------------------------------------------------
    def _on_sub_selection_changed(self, selected=None, _deselected=None) -> None:
        if selected is not None:
            indexes = selected.indexes()
        else:
            selection_model = self._sub_table.selectionModel()
            if selection_model is None:
                indexes = []
            else:
                indexes = selection_model.selectedIndexes()
        if not indexes:
            self._load_sub_object(None)
            return
        row = indexes[0].row()
        self._load_sub_object(self._sub_object_for_row(row))

    def _load_sub_object(self, sub: SubObject | None) -> None:
        self._current_sub = sub
        self._updating_sub = True
        if sub is None:
            self._sub_index_label.setText("-")
            self._sub_name.clear()
            self._set_combo_value(self._sub_data_type, None)
            self._set_combo_value(self._sub_access, None)
            self._sub_default.clear()
            self._sub_value.clear()
            self._sub_minimum.clear()
            self._sub_maximum.clear()
            self._set_combo_value(self._sub_pdo, None)
            self._set_sub_enabled(False)
            self._updating_sub = False
            return

        self._set_sub_enabled(True)
        self._sub_index_label.setText(f"{sub.key.subindex:02X}")
        self._sub_name.setText(sub.name or "")
        self._set_combo_value(self._sub_data_type, sub.data_type)
        self._set_combo_value(self._sub_access, sub.access_type)
        self._sub_default.setText(sub.default or "")
        self._sub_value.setText(sub.value or "")
        self._sub_minimum.setText(sub.minimum or "")
        self._sub_maximum.setText(sub.maximum or "")
        self._set_combo_value(self._sub_pdo, sub.pdo_mapping)
        self._updating_sub = False

    def _on_sub_name_changed(self, text: str) -> None:
        if self._entry is None or self._current_sub is None or self._updating_sub:
            return
        self._current_sub.name = text.strip() or None
        self.subEntryChanged.emit(self._entry, self._current_sub)
        self._refresh_sub_row(self._current_sub)

    def _on_sub_text_changed(self, field: str, widget: QLineEdit) -> None:
        if self._entry is None or self._current_sub is None or self._updating_sub:
            return
        value = widget.text().strip() or None
        setattr(self._current_sub, field, value)
        self.subEntryChanged.emit(self._entry, self._current_sub)
        self._refresh_sub_row(self._current_sub)

    def _on_sub_combo_changed(self, combo: QComboBox, field: str) -> None:
        if self._entry is None or self._current_sub is None or self._updating_sub:
            return
        value = combo.currentData(Qt.UserRole)
        setattr(self._current_sub, field, value)
        self.subEntryChanged.emit(self._entry, self._current_sub)
        self._refresh_sub_row(self._current_sub)

    # ------------------------------------------------------------------
    def _populate_enum_combo(self, combo: QComboBox, enum_cls, *, allow_none: bool) -> None:
        combo.clear()
        if allow_none:
            combo.addItem(self.tr("Not set"), None)
        for member in enum_cls:
            combo.addItem(self._format_enum(member), member)

    def _set_combo_value(self, combo: QComboBox, value) -> None:
        index = combo.findData(value, Qt.UserRole)
        if index < 0 and value is None:
            index = combo.findData(None, Qt.UserRole)
        if index >= 0:
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)
        else:
            combo.blockSignals(True)
            combo.setCurrentIndex(0 if combo.count() else -1)
            combo.blockSignals(False)

    def _refresh_sub_row(self, sub: SubObject) -> None:
        for row in range(self._sub_table.rowCount()):
            item = self._sub_table.item(row, 0)
            if item is None:
                continue
            stored = item.data(Qt.UserRole)
            if stored is sub:
                name_item = self._sub_table.item(row, 1)
                if name_item is not None:
                    name_item.setText(sub.name or self.tr("SubIndex"))
                type_item = self._sub_table.item(row, 2)
                if type_item is not None:
                    type_item.setText(sub.data_type.name)
                access_item = self._sub_table.item(row, 3)
                if access_item is not None:
                    access_item.setText(sub.access_type.name)
                pdo_item = self._sub_table.item(row, 4)
                if pdo_item is not None:
                    pdo_item.setText(sub.pdo_mapping.name if sub.pdo_mapping else "")
                default_item = self._sub_table.item(row, 6)
                if default_item is not None:
                    default_item.setText(sub.default or "")
                break

    def _format_enum(self, member) -> str:
        name = member.name.replace("_", " ").title()
        return name

    def _set_entry_enabled(self, enabled: bool) -> None:
        for widget in (
            self._entry_name,
            self._entry_object_type,
            self._entry_data_type,
            self._entry_access,
            self._entry_default,
            self._entry_value,
            self._entry_minimum,
            self._entry_maximum,
            self._entry_pdo,
        ):
            widget.setEnabled(enabled)

    def _set_sub_enabled(self, enabled: bool) -> None:
        self._sub_form_container.setEnabled(enabled)

    def _clear_entry_fields(self) -> None:
        self._entry_name.clear()
        self._set_combo_value(self._entry_object_type, None)
        self._set_combo_value(self._entry_data_type, None)
        self._set_combo_value(self._entry_access, None)
        self._entry_default.clear()
        self._entry_value.clear()
        self._entry_minimum.clear()
        self._entry_maximum.clear()
        self._set_combo_value(self._entry_pdo, None)

    def current_entry(self) -> ObjectEntry | None:
        return self._entry

    def current_subobject(self) -> SubObject | None:
        return self._current_sub

    def _sub_object_for_row(self, row: int) -> SubObject | None:
        if row < 0 or row >= self._sub_table.rowCount():
            return None
        item = self._sub_table.item(row, 0)
        if item is None:
            return None
        data = item.data(Qt.UserRole)
        return data if isinstance(data, SubObject) else None
