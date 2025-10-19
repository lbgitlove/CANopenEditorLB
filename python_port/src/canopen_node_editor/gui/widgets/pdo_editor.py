"""Editor surfaces for PDO mappings."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ...model import Device, ObjectEntry, SubObject


class PDOEditorWidget(QWidget):
    """Display RPDO/TPDO assignments in a tabular form."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tpdo = QTableWidget(0, 3, self)
        self._rpdo = QTableWidget(0, 3, self)

        for table, label in ((self._tpdo, self.tr("TPDO")), (self._rpdo, self.tr("RPDO"))):
            table.setHorizontalHeaderLabels([label, self.tr("Index"), self.tr("Name")])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self._tpdo)
        splitter.addWidget(self._rpdo)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def set_device(self, device: Device | None) -> None:
        self._populate_table(self._tpdo, device, include="TRANSMIT")
        self._populate_table(self._rpdo, device, include="RECEIVE")

    def _populate_table(self, table: QTableWidget, device: Device | None, include: str) -> None:
        table.clearContents()
        if device is None:
            table.setRowCount(0)
            return

        entries: list[tuple[str, ObjectEntry, SubObject | None]] = []
        for entry in device.all_entries():
            if entry.pdo_mapping and include in entry.pdo_mapping.name:
                entries.append((entry.pdo_mapping.name, entry, None))
            for sub in entry.sub_objects.values():
                if sub.pdo_mapping and include in sub.pdo_mapping.name:
                    entries.append((sub.pdo_mapping.name, entry, sub))

        table.setRowCount(len(entries))
        for row, (mapping, entry, sub) in enumerate(entries):
            mapping_item = QTableWidgetItem(mapping)
            index_item = QTableWidgetItem(f"0x{entry.index:04X}")
            name = sub.name if sub else entry.name
            name_item = QTableWidgetItem(name)
            table.setItem(row, 0, mapping_item)
            table.setItem(row, 1, index_item)
            table.setItem(row, 2, name_item)
