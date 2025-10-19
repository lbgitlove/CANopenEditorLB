"""Editor surfaces for PDO mappings."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...model import Device, ObjectEntry, PDOMapping, SubObject


@dataclass
class _PDODescriptor:
    """Pairing of communication and mapping entries for a PDO."""

    number: int
    communication: ObjectEntry | None = None
    mapping: ObjectEntry | None = None


@dataclass
class _PDOSection:
    """Widget bundle and metadata for a PDO direction."""

    title: str
    container: QWidget
    selector: QListWidget
    communication: QTableWidget
    mapping: QTableWidget
    communication_start: int
    communication_end: int
    mapping_start: int
    mapping_end: int
    descriptors: list[_PDODescriptor] = field(default_factory=list)


class PDOEditorWidget(QWidget):
    """Display RPDO/TPDO assignments in a tabular form."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._device: Device | None = None
        self._field_role = Qt.UserRole + 1

        tpdo_section = self._build_section(
            title=self.tr("TPDO"),
            communication_range=(0x1800, 0x19FF),
            mapping_range=(0x1A00, 0x1BFF),
        )
        rpdo_section = self._build_section(
            title=self.tr("RPDO"),
            communication_range=(0x1400, 0x15FF),
            mapping_range=(0x1600, 0x17FF),
        )

        self._sections: dict[PDOMapping, _PDOSection] = {
            PDOMapping.TPDO: tpdo_section,
            PDOMapping.RPDO: rpdo_section,
        }

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(tpdo_section.container)
        splitter.addWidget(rpdo_section.container)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        for section in self._sections.values():
            for table in (section.communication, section.mapping):
                self._configure_table(table)
            section.selector.currentRowChanged.connect(
                partial(self._on_selector_changed, section)
            )

    # ------------------------------------------------------------------
    def set_device(self, device: Device | None) -> None:
        self._device = device
        for mapping_type, section in self._sections.items():
            previous = self._selected_descriptor(section)
            section.descriptors = self._collect_descriptors(section, device)
            self._populate_selector(section)
            target_number = previous.number if previous is not None else None
            self._restore_selection(section, target_number)
            self._populate_section_tables(mapping_type)

    # ------------------------------------------------------------------
    def tpdo_selector(self) -> QListWidget:
        return self._sections[PDOMapping.TPDO].selector

    def rpdo_selector(self) -> QListWidget:
        return self._sections[PDOMapping.RPDO].selector

    def tpdo_mapping_view(self) -> QTableWidget:
        return self._sections[PDOMapping.TPDO].mapping

    def tpdo_communication_view(self) -> QTableWidget:
        return self._sections[PDOMapping.TPDO].communication

    def rpdo_mapping_view(self) -> QTableWidget:
        return self._sections[PDOMapping.RPDO].mapping

    def rpdo_communication_view(self) -> QTableWidget:
        return self._sections[PDOMapping.RPDO].communication

    # ------------------------------------------------------------------
    def _on_selector_changed(self, section: _PDOSection, _row: int) -> None:
        mapping_type = self._mapping_type_for_section(section)
        if mapping_type is None:
            return
        self._populate_section_tables(mapping_type)

    def _mapping_type_for_section(
        self, target: _PDOSection
    ) -> PDOMapping | None:
        for mapping_type, section in self._sections.items():
            if section is target:
                return mapping_type
        return None

    # ------------------------------------------------------------------
    def _build_section(
        self,
        *,
        title: str,
        communication_range: tuple[int, int],
        mapping_range: tuple[int, int],
    ) -> _PDOSection:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal, container)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        selector_group = QGroupBox(
            self.tr("{title} Channels").format(title=title), splitter
        )
        selector_layout = QVBoxLayout(selector_group)
        selector_layout.setContentsMargins(0, 0, 0, 0)
        selector = QListWidget(selector_group)
        selector.setSelectionMode(QListWidget.SingleSelection)
        selector_layout.addWidget(selector)
        splitter.addWidget(selector_group)

        detail_container = QWidget(splitter)
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)

        comm_group = QGroupBox(
            self.tr("{title} Communication Parameters").format(title=title),
            detail_container,
        )
        comm_layout = QVBoxLayout(comm_group)
        comm_table = self._create_table()
        comm_layout.addWidget(comm_table)
        detail_layout.addWidget(comm_group)

        mapping_group = QGroupBox(
            self.tr("{title} Mapping Parameters").format(title=title),
            detail_container,
        )
        mapping_layout = QVBoxLayout(mapping_group)
        mapping_table = self._create_table()
        mapping_layout.addWidget(mapping_table)
        detail_layout.addWidget(mapping_group)

        detail_layout.addStretch(1)

        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        return _PDOSection(
            title=title,
            container=container,
            selector=selector,
            communication=comm_table,
            mapping=mapping_table,
            communication_start=communication_range[0],
            communication_end=communication_range[1],
            mapping_start=mapping_range[0],
            mapping_end=mapping_range[1],
        )

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
        table.setSelectionBehavior(QTableWidget.SelectRows)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        return table

    def _configure_table(self, table: QTableWidget) -> None:
        triggers = (
            QTableWidget.DoubleClicked
            | QTableWidget.EditKeyPressed
            | QTableWidget.SelectedClicked
        )
        table.setEditTriggers(triggers)
        table.itemChanged.connect(partial(self._on_table_item_changed, table))

    # ------------------------------------------------------------------
    def _collect_descriptors(
        self, section: _PDOSection, device: Device | None
    ) -> list[_PDODescriptor]:
        if device is None:
            return []
        descriptors: dict[int, _PDODescriptor] = {}
        for entry in device.all_entries():
            index = entry.index
            if section.communication_start <= index <= section.communication_end:
                number = index - section.communication_start
                descriptor = descriptors.setdefault(number, _PDODescriptor(number))
                descriptor.communication = entry
            elif section.mapping_start <= index <= section.mapping_end:
                number = index - section.mapping_start
                descriptor = descriptors.setdefault(number, _PDODescriptor(number))
                descriptor.mapping = entry
        return [descriptors[key] for key in sorted(descriptors)]

    def _populate_selector(self, section: _PDOSection) -> None:
        section.selector.blockSignals(True)
        section.selector.clear()
        for descriptor in section.descriptors:
            label = self._format_descriptor(section, descriptor)
            item = QListWidgetItem(label)
            item.setData(self._field_role, descriptor)
            section.selector.addItem(item)
        section.selector.blockSignals(False)

    def _format_descriptor(self, section: _PDOSection, descriptor: _PDODescriptor) -> str:
        number = descriptor.number + 1
        parts = [self.tr("{title} {number}").format(title=section.title, number=number)]
        if descriptor.communication is not None:
            parts.append(f"0x{descriptor.communication.index:04X}")
        if descriptor.mapping is not None:
            parts.append(f"0x{descriptor.mapping.index:04X}")
        return " – ".join(parts)

    def _restore_selection(self, section: _PDOSection, number: int | None) -> None:
        if section.selector.count() == 0:
            self._clear_table(section.communication)
            self._clear_table(section.mapping)
            return
        if number is None:
            section.selector.setCurrentRow(0)
            return
        for row in range(section.selector.count()):
            item = section.selector.item(row)
            descriptor = item.data(self._field_role)
            if isinstance(descriptor, _PDODescriptor) and descriptor.number == number:
                section.selector.setCurrentRow(row)
                return
        section.selector.setCurrentRow(0)

    def _selected_descriptor(self, section: _PDOSection) -> _PDODescriptor | None:
        item = section.selector.currentItem()
        if item is None:
            return None
        descriptor = item.data(self._field_role)
        if isinstance(descriptor, _PDODescriptor):
            return descriptor
        return None

    def _populate_section_tables(self, mapping_type: PDOMapping) -> None:
        section = self._sections[mapping_type]
        descriptor = self._selected_descriptor(section)
        self._populate_entry_table(
            section.communication,
            descriptor,
            kind="communication",
            mapping_type=mapping_type,
        )
        self._populate_entry_table(
            section.mapping,
            descriptor,
            kind="mapping",
            mapping_type=mapping_type,
        )

    def _populate_entry_table(
        self,
        table: QTableWidget,
        descriptor: _PDODescriptor | None,
        *,
        kind: str,
        mapping_type: PDOMapping,
    ) -> None:
        table.blockSignals(True)
        table.setRowCount(0)
        if descriptor is None:
            table.blockSignals(False)
            return

        entry = descriptor.communication if kind == "communication" else descriptor.mapping
        rows: list[tuple[ObjectEntry, SubObject | None]] = []
        if entry is not None:
            if entry.sub_objects:
                for subindex, sub in sorted(entry.sub_objects.items()):
                    rows.append((entry, sub))
            else:
                rows.append((entry, None))
        if kind == "mapping":
            rows.extend(self._collect_mappable_entries(mapping_type))
        self._fill_rows(table, rows)
        table.blockSignals(False)

    def _clear_table(self, table: QTableWidget) -> None:
        table.blockSignals(True)
        table.setRowCount(0)
        table.blockSignals(False)

    # ------------------------------------------------------------------
    def _fill_rows(
        self, table: QTableWidget, entries: list[tuple[ObjectEntry, SubObject | None]]
    ) -> None:
        table.blockSignals(True)
        table.setRowCount(len(entries))
        for row, (entry, sub) in enumerate(entries):
            index_item = QTableWidgetItem(f"0x{entry.index:04X}")
            subindex_text = f"{sub.key.subindex:02X}" if sub else "-"
            subindex_item = QTableWidgetItem(subindex_text)
            name_item = QTableWidgetItem(sub.name if sub else entry.name)
            value_item = QTableWidgetItem(self._value_text(entry, sub))
            default_item = QTableWidgetItem(self._default_text(entry, sub))

            columns = [
                (index_item, None),
                (subindex_item, None),
                (name_item, "name"),
                (value_item, "value"),
                (default_item, "default"),
            ]

            for column, (item, field) in enumerate(columns):
                if field is None:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    item.setData(self._field_role, (entry, sub, field))
                table.setItem(row, column, item)
        table.blockSignals(False)

    def _collect_mappable_entries(
        self, mapping_type: PDOMapping
    ) -> list[tuple[ObjectEntry, SubObject | None]]:
        if self._device is None:
            return []
        entries: list[tuple[ObjectEntry, SubObject | None]] = []
        for entry in self._device.all_entries():
            if entry.pdo_mapping == mapping_type:
                entries.append((entry, None))
            for subindex, sub in sorted(entry.sub_objects.items()):
                if sub.pdo_mapping == mapping_type:
                    entries.append((entry, sub))
        return entries


    def _fill_rows(
        self, table: QTableWidget, entries: list[tuple[ObjectEntry, SubObject | None]]
    ) -> None:
        table.blockSignals(True)
        table.setRowCount(len(entries))
        for row, (entry, sub) in enumerate(entries):
            index_item = QTableWidgetItem(f"0x{entry.index:04X}")
            subindex_text = f"{sub.key.subindex:02X}" if sub else "-"
            subindex_item = QTableWidgetItem(subindex_text)
            name_item = QTableWidgetItem(sub.name if sub else entry.name)
            value_item = QTableWidgetItem(self._value_text(entry, sub))
            default_item = QTableWidgetItem(self._default_text(entry, sub))

            columns = [
                (index_item, None),
                (subindex_item, None),
                (name_item, "name"),
                (value_item, "value"),
                (default_item, "default"),
            ]

            for column, (item, field) in enumerate(columns):
                if field is None:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    item.setData(self._field_role, (entry, sub, field))
                table.setItem(row, column, item)
        table.blockSignals(False)

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

    def _on_table_item_changed(self, table: QTableWidget, item: QTableWidgetItem) -> None:
        payload = item.data(self._field_role)
        if not isinstance(payload, tuple) or len(payload) != 3:
            return
        entry, sub, field = payload
        text = item.text().strip()
        target = sub or entry
        setattr(target, field, text or None)
