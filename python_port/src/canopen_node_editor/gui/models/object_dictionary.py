"""Models used by the object dictionary tree view."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

from ...model import Device, ObjectEntry, SubObject


class ObjectDictionaryModel(QStandardItemModel):
    """Tree model presenting :class:`~canopen_node_editor.model.Device` objects."""

    COLUMN_HEADERS = ("Index", "Name", "Type", "Access")

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

        for item in (index_item, name_item, type_item, access_item):
            item.setEditable(False)

        if entry.value is None and entry.default is None:
            # Highlight entries that still require configuration.
            name_item.setData(self._pending_brush(), Qt.ForegroundRole)

        return [index_item, name_item, type_item, access_item]

    def _create_sub_item(
        self, entry: ObjectEntry, subindex: int, sub: SubObject
    ) -> list[QStandardItem]:
        index_text = f"{subindex}"
        name_item = QStandardItem(sub.name or self.tr("SubIndex"))
        type_item = QStandardItem(sub.data_type.name)
        access_item = QStandardItem(sub.access_type.name)

        index_item = QStandardItem(index_text)
        index_item.setData((entry, sub), Qt.UserRole)

        for item in (index_item, name_item, type_item, access_item):
            item.setEditable(False)

        if sub.pdo_mapping:
            name_item.setData(self._pdo_brush(), Qt.ForegroundRole)

        return [index_item, name_item, type_item, access_item]

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
