from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from canopen_node_editor.gui.widgets.object_dictionary import ObjectDictionaryWidget
from canopen_node_editor.parsers import parse_xdd

SAMPLES = Path(__file__).resolve().parents[1] / "od_examples"


@pytest.mark.qt
def test_object_dictionary_widget_loads_xdd(qtbot):
    xdd_path = SAMPLES / "demo_device.xdd"
    device = parse_xdd(xdd_path)

    widget = ObjectDictionaryWidget()
    qtbot.addWidget(widget)
    widget.set_device(device)

    model = widget.model()
    indices = {model.item(row, 0).text() for row in range(model.rowCount())}

    assert "0x1000" in indices
    assert "0x1600" in indices
    assert widget.tree().model() is model


@pytest.mark.qt
def test_add_entry_button_disabled_without_device(qtbot):
    widget = ObjectDictionaryWidget()
    qtbot.addWidget(widget)

    assert widget.can_add_entries() is False

    xdd_path = SAMPLES / "demo_device.xdd"
    device = parse_xdd(xdd_path)
    widget.set_device(device)

    assert widget.can_add_entries() is True
