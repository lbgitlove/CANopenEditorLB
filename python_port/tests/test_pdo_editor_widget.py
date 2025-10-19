from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from canopen_node_editor.gui.widgets.pdo_editor import PDOEditorWidget
from canopen_node_editor.model import (
    AccessType,
    DataType,
    Device,
    ObjectEntry,
    ObjectKey,
    ObjectType,
    PDOMapping,
    SubObject,
)
from canopen_node_editor.parsers import parse_xdd

SAMPLES = Path(__file__).resolve().parents[1] / "od_examples"


@pytest.mark.qt
def test_pdo_editor_lists_mapped_objects(qtbot):
    device = parse_xdd(SAMPLES / "od.xdd")

    widget = PDOEditorWidget()
    qtbot.addWidget(widget)
    widget.set_device(device)

    table = widget.tpdo_mapping_view()
    rows = {table.item(row, 0).text() for row in range(table.rowCount())}

    assert "0x1001" in rows


@pytest.mark.qt
def test_pdo_editor_displays_communication_parameters(qtbot):
    device = Device()
    entry = ObjectEntry(
        index=0x1800,
        name="TPDO1 Communication",
        object_type=ObjectType.RECORD,
        data_type=None,
        access_type=None,
    )
    entry.sub_objects = {
        0: SubObject(
            key=ObjectKey(index=0x1800, subindex=0),
            name="Number of entries",
            data_type=DataType.UNSIGNED8,
            access_type=AccessType.RO,
            default="2",
            value="2",
        ),
        1: SubObject(
            key=ObjectKey(index=0x1800, subindex=1),
            name="COB-ID",
            data_type=DataType.UNSIGNED32,
            access_type=AccessType.RW,
            default="0x180",
            value="0x280",
        ),
    }
    device.add_object(entry)

    widget = PDOEditorWidget()
    qtbot.addWidget(widget)
    widget.set_device(device)

    comm_table = widget.tpdo_communication_view()

    assert comm_table.rowCount() == 2
    assert comm_table.item(0, 0).text() == "0x1800"
    assert comm_table.item(0, 3).text() == "2"


@pytest.mark.qt
def test_editing_tpdo_mapping_updates_device(qtbot):
    device = Device()
    entry = ObjectEntry(
        index=0x1A00,
        name="TPDO1 Mapping",
        object_type=ObjectType.RECORD,
        data_type=None,
        access_type=None,
        pdo_mapping=PDOMapping.TPDO,
    )
    entry.sub_objects = {
        0: SubObject(
            key=ObjectKey(index=0x1A00, subindex=0),
            name="Number of entries",
            data_type=DataType.UNSIGNED8,
            access_type=AccessType.RO,
            default="1",
            value="1",
        ),
        1: SubObject(
            key=ObjectKey(index=0x1A00, subindex=1),
            name="Mapped object",
            data_type=DataType.UNSIGNED32,
            access_type=AccessType.RW,
            default="0x20000008",
            value="0x20000008",
            pdo_mapping=PDOMapping.TPDO,
        ),
    }
    device.add_object(entry)

    widget = PDOEditorWidget()
    qtbot.addWidget(widget)
    widget.set_device(device)

    table = widget.tpdo_mapping_view()
    target_row = next(
        row
        for row in range(table.rowCount())
        if table.item(row, 1).text() == "01"
    )

    item = table.item(target_row, 3)
    item.setText("0x20000010")

    assert entry.sub_objects[1].value == "0x20000010"


@pytest.mark.qt
def test_editing_rpdo_communication_updates_device(qtbot):
    device = Device()
    entry = ObjectEntry(
        index=0x1400,
        name="RPDO1 Communication",
        object_type=ObjectType.RECORD,
        data_type=None,
        access_type=None,
    )
    entry.sub_objects = {
        0: SubObject(
            key=ObjectKey(index=0x1400, subindex=0),
            name="Number of entries",
            data_type=DataType.UNSIGNED8,
            access_type=AccessType.RO,
            default="2",
            value="2",
        ),
        1: SubObject(
            key=ObjectKey(index=0x1400, subindex=1),
            name="COB-ID",
            data_type=DataType.UNSIGNED32,
            access_type=AccessType.RW,
            default="0x200",
            value="0x200",
        ),
        2: SubObject(
            key=ObjectKey(index=0x1400, subindex=2),
            name="Transmission type",
            data_type=DataType.UNSIGNED8,
            access_type=AccessType.RW,
            default="255",
            value="255",
        ),
    }
    device.add_object(entry)

    widget = PDOEditorWidget()
    qtbot.addWidget(widget)
    widget.set_device(device)

    table = widget.rpdo_communication_view()
    target_row = next(
        row
        for row in range(table.rowCount())
        if table.item(row, 1).text() == "02"
    )

    item = table.item(target_row, 4)
    item.setText("128")

    assert entry.sub_objects[2].default == "128"
