"""Models used by the object dictionary tree view."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel

from ...model import Device, ObjectEntry, SubObject


class ObjectDictionaryModel(QStandardItemModel):
    """Tree model presenting :class:`~canopen_node_editor.model.Device` objects."""

    COLUMN_HEADERS = ("Index", "Name", "Type", "Access", "Value", "Default")
    _FIELD_ROLE = Qt.UserRole + 1

    valueEdited = Signal(object, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHorizontalHeaderLabels([self.tr(text) for text in self.COLUMN_HEADERS])
        self._device: Device | None = None

    def set_device(self, device: Device | None) -> None:
        self._device = device
        self._refresh()

    def device(self) -> Device | None:
        return self._device

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        self.removeRows(0, self.rowCount())
        if not self._device:
            return

        for entry in self._device.all_entries():
            parent = self._create_entry_item(entry)
            self.appendRow(parent)
            if entry.sub_objects:
                for subindex, sub in sorted(entry.sub_objects.items()):
                    child_items = self._create_sub_item(entry, subindex, sub)
                    parent[0].appendRow(child_items)

    def _create_entry_item(self, entry: ObjectEntry) -> list[QStandardItem]:
        index_text = f"0x{entry.index:04X}"
        type_name = entry.object_type.name if entry.object_type else self.tr("Unknown")
        access = entry.access_type.name if entry.access_type else ""

        index_item = QStandardItem(index_text)
        index_item.setData((entry, None), Qt.UserRole)
        name_item = QStandardItem(entry.name or self.tr("Unnamed Object"))
        type_item = QStandardItem(type_name)
        access_item = QStandardItem(access)
        value_item = QStandardItem(entry.value or "")
        default_item = QStandardItem(entry.default or "")

        for item in (index_item, type_item, access_item):
            item.setEditable(False)

        for item, field in (
            (name_item, "name"),
            (value_item, "value"),
            (default_item, "default"),
        ):
            item.setEditable(True)
            item.setData((entry, None, field), self._FIELD_ROLE)

        if entry.value is None and entry.default is None:
            # Highlight entries that still require configuration.
            name_item.setData(self._pending_brush(), Qt.ForegroundRole)

        return [index_item, name_item, type_item, access_item, value_item, default_item]

    def _create_sub_item(
        self, entry: ObjectEntry, subindex: int, sub: SubObject
    ) -> list[QStandardItem]:
        index_text = f"{subindex}"
        name_item = QStandardItem(sub.name or self.tr("SubIndex"))
        type_item = QStandardItem(sub.data_type.name)
        access_item = QStandardItem(sub.access_type.name)
        value_item = QStandardItem(sub.value or "")
        default_item = QStandardItem(sub.default or "")

        index_item = QStandardItem(index_text)
        index_item.setData((entry, sub), Qt.UserRole)

        for item in (index_item, type_item, access_item):
            item.setEditable(False)

        for item, field in (
            (name_item, "name"),
            (value_item, "value"),
            (default_item, "default"),
        ):
            item.setEditable(True)
            item.setData((entry, sub, field), self._FIELD_ROLE)

        if sub.pdo_mapping:
            name_item.setData(self._pdo_brush(), Qt.ForegroundRole)

        return [index_item, name_item, type_item, access_item, value_item, default_item]

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):  # type: ignore[override]
        if role == Qt.EditRole and index.isValid():
            item = self.itemFromIndex(index)
            if item is not None:
                payload = item.data(self._FIELD_ROLE)
                if isinstance(payload, tuple) and len(payload) == 3:
                    entry, sub, field = payload
                    if value is None:
                        text = ""
                    elif isinstance(value, str):
                        text = value
                    else:
                        text = str(value)
                    text = text.strip()
                    setattr_target = sub or entry
                    setattr(setattr_target, field, text or None)
                    self.valueEdited.emit(entry, sub)
        return super().setData(index, value, role)

    def _pending_brush(self):
        from PySide6.QtGui import QBrush, QColor

        return QBrush(QColor(200, 120, 0))

    def _pdo_brush(self):
        from PySide6.QtGui import QBrush, QColor

        return QBrush(QColor(33, 150, 243))


def iter_selected_payloads(
    indexes: Iterable[QModelIndex], model: QStandardItemModel
) -> Iterable[tuple[ObjectEntry, SubObject | None]]:
    for index in indexes:
        if not index.isValid() or index.column() != 0:
            continue
        item = model.itemFromIndex(index)
        if item is None:
            continue
        data = item.data(Qt.UserRole)
        if isinstance(data, tuple):
            yield data
