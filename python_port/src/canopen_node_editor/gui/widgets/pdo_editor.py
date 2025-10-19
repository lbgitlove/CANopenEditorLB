"""Editor surfaces for PDO mappings."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...model import Device, ObjectEntry, SubObject


class PDOEditorWidget(QWidget):
    """Display RPDO/TPDO assignments in a tabular form."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        (
            tpdo_section,
            self._tpdo_comm,
            self._tpdo_mapping,
        ) = self._build_section(self.tr("TPDO"))
        (
            rpdo_section,
            self._rpdo_comm,
            self._rpdo_mapping,
        ) = self._build_section(self.tr("RPDO"))

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(tpdo_section)
        splitter.addWidget(rpdo_section)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def set_device(self, device: Device | None) -> None:
        self._populate_mapping_table(self._tpdo_mapping, device, include="TRANSMIT")
        self._populate_mapping_table(self._rpdo_mapping, device, include="RECEIVE")
        self._populate_communication_table(
            self._tpdo_comm, device, self._is_tpdo_communication
        )
        self._populate_communication_table(
            self._rpdo_comm, device, self._is_rpdo_communication
        )

    def tpdo_mapping_view(self) -> QTableWidget:
        return self._tpdo_mapping

    def tpdo_communication_view(self) -> QTableWidget:
        return self._tpdo_comm

    def rpdo_mapping_view(self) -> QTableWidget:
        return self._rpdo_mapping

    def rpdo_communication_view(self) -> QTableWidget:
        return self._rpdo_comm

    def _build_section(self, title: str) -> tuple[QWidget, QTableWidget, QTableWidget]:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        comm_group = QGroupBox(self.tr("{title} Communication Parameters").format(title=title))
        comm_layout = QVBoxLayout(comm_group)
        comm_table = self._create_table()
        comm_layout.addWidget(comm_table)
        layout.addWidget(comm_group)

        mapping_group = QGroupBox(self.tr("{title} Mapping Parameters").format(title=title))
        mapping_layout = QVBoxLayout(mapping_group)
        mapping_table = self._create_table()
        mapping_layout.addWidget(mapping_table)
        layout.addWidget(mapping_group)

        layout.addStretch(1)
        return container, comm_table, mapping_table

    def _create_table(self) -> QTableWidget:
        table = QTableWidget(0, 5, self)
        table.setHorizontalHeaderLabels(
            [
                self.tr("Index"),
                self.tr("SubIndex"),
                self.tr("Name"),
                self.tr("Value"),
                self.tr("Default"),
            ]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        return table

    def _populate_mapping_table(
        self, table: QTableWidget, device: Device | None, include: str
    ) -> None:
        table.setRowCount(0)
        if device is None:
            return

        entries: list[tuple[ObjectEntry, SubObject | None]] = []
        for entry in device.all_entries():
            if entry.pdo_mapping and include in entry.pdo_mapping.name:
                entries.append((entry, None))
            for sub in entry.sub_objects.values():
                if sub.pdo_mapping and include in sub.pdo_mapping.name:
                    entries.append((entry, sub))

        self._fill_rows(table, entries)

    def _populate_communication_table(
        self,
        table: QTableWidget,
        device: Device | None,
        predicate,
    ) -> None:
        table.setRowCount(0)
        if device is None:
            return

        entries: list[tuple[ObjectEntry, SubObject | None]] = []
        for entry in device.all_entries():
            if not predicate(entry.index):
                continue
            if entry.sub_objects:
                for subindex, sub in sorted(entry.sub_objects.items()):
                    entries.append((entry, sub))
            else:
                entries.append((entry, None))

        self._fill_rows(table, entries)

    def _fill_rows(
        self, table: QTableWidget, entries: list[tuple[ObjectEntry, SubObject | None]]
    ) -> None:
        table.setRowCount(len(entries))
        for row, (entry, sub) in enumerate(entries):
            index_item = QTableWidgetItem(f"0x{entry.index:04X}")
            subindex_text = f"{sub.key.subindex:02X}" if sub else "-"
            subindex_item = QTableWidgetItem(subindex_text)
            name_item = QTableWidgetItem(sub.name if sub else entry.name)
            value_item = QTableWidgetItem(self._value_text(entry, sub))
            default_item = QTableWidgetItem(self._default_text(entry, sub))

            for column, item in enumerate(
                [index_item, subindex_item, name_item, value_item, default_item]
            ):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, column, item)

    def _value_text(self, entry: ObjectEntry, sub: SubObject | None) -> str:
        if sub and sub.value:
            return sub.value
        if not sub and entry.value:
            return entry.value
        if sub and sub.default:
            return sub.default
        if entry.default:
            return entry.default
        return ""

    def _default_text(self, entry: ObjectEntry, sub: SubObject | None) -> str:
        if sub and sub.default:
            return sub.default
        if not sub and entry.default:
            return entry.default
        return ""

    @staticmethod
    def _is_rpdo_mapping(index: int) -> bool:
        return 0x1600 <= index <= 0x17FF

    @staticmethod
    def _is_tpdo_mapping(index: int) -> bool:
        return 0x1A00 <= index <= 0x1BFF

    @staticmethod
    def _is_rpdo_communication(index: int) -> bool:
        return 0x1400 <= index <= 0x15FF

    @staticmethod
    def _is_tpdo_communication(index: int) -> bool:
        return 0x1800 <= index <= 0x19FF
