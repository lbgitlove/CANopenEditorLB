from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from canopen_node_editor.gui.widgets.device_page import DeviceEditorPage
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
def test_device_page_tree_hides_subindices(qtbot):
    device = parse_xdd(SAMPLES / "od.xdd")
    page = DeviceEditorPage(device)
    qtbot.addWidget(page)

    model = page.object_dictionary.model()
    assert model.rowCount() > 0
    for row in range(model.rowCount()):
        index_item = model.item(row, 0)
        assert index_item.rowCount() == 0
        for column in (1, 4, 5):
            assert not model.item(row, column).isEditable()


@pytest.mark.qt
def test_entry_editor_updates_device_value(qtbot):
    device = parse_xdd(SAMPLES / "demo_device.xdd")
    page = DeviceEditorPage(device)
    qtbot.addWidget(page)

    entry = device.get_object(0x1000)
    assert entry is not None
    page.object_dictionary.select_entry(entry)
    qtbot.waitUntil(lambda: page.object_editor.current_entry() is entry)

    editor = page.object_editor
    editor._entry_value.clear()
    qtbot.keyClicks(editor._entry_value, "0x87654321")

    assert entry.value == "0x87654321"


@pytest.mark.qt
def test_subindex_pdo_mapping_updates_pdo_editor(qtbot):
    device = Device()
    entry = ObjectEntry(
        index=0x2000,
        name="Custom Record",
        object_type=ObjectType.RECORD,
        data_type=None,
        access_type=None,
    )
    entry.sub_objects = {
        0: SubObject(
            key=ObjectKey(index=0x2000, subindex=0),
            name="Number of entries",
            data_type=DataType.UNSIGNED8,
            access_type=AccessType.RO,
            value="1",
            default="1",
        ),
        1: SubObject(
            key=ObjectKey(index=0x2000, subindex=1),
            name="Mapped value",
            data_type=DataType.UNSIGNED32,
            access_type=AccessType.RW,
        ),
    }
    device.add_object(entry)

    mapping_entry = ObjectEntry(
        index=0x1A00,
        name="TPDO1 Mapping",
        object_type=ObjectType.RECORD,
        data_type=None,
        access_type=None,
    )
    mapping_entry.sub_objects = {
        0: SubObject(
            key=ObjectKey(index=0x1A00, subindex=0),
            name="Number of entries",
            data_type=DataType.UNSIGNED8,
            access_type=AccessType.RO,
            value="1",
            default="1",
        ),
        1: SubObject(
            key=ObjectKey(index=0x1A00, subindex=1),
            name="Mapped object",
            data_type=DataType.UNSIGNED32,
            access_type=AccessType.RW,
            value="0x20000008",
            default="0x20000008",
        ),
    }
    device.add_object(mapping_entry)

    page = DeviceEditorPage(device)
    qtbot.addWidget(page)
    page.object_dictionary.select_entry(entry)
    qtbot.waitUntil(lambda: page.object_editor.current_entry() is entry)

    sub_list = page.object_editor._sub_list
    sub_list.setCurrentRow(1)
    qtbot.waitUntil(lambda: page.object_editor.current_subobject() is entry.sub_objects[1])
    mapping_combo = page.object_editor._sub_pdo
    index = mapping_combo.findData(PDOMapping.TPDO)
    assert index >= 0
    mapping_combo.setCurrentIndex(index)

    table = page.pdo_editor.tpdo_mapping_view()

    def has_mappable_entry() -> bool:
        return any(
            table.item(row, 0).text() == "0x2000"
            for row in range(table.rowCount())
        )

    qtbot.waitUntil(has_mappable_entry)
