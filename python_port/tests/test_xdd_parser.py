from pathlib import Path

from canopen_node_editor.model import ObjectType
from canopen_node_editor.parsers import parse_xdd, serialize_device_to_xdd

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_parse_xdd_and_serialise(tmp_path):
    xdd_path = SAMPLES / "demo_device.xdd"
    device = parse_xdd(xdd_path)

    assert device.info.product_name == "Demo Device"
    assert device.objects[0x1600].object_type == ObjectType.RECORD

    rendered = serialize_device_to_xdd(device)
    out_path = tmp_path / "roundtrip.xdd"
    out_path.write_text(rendered, encoding="utf-8")
    reparsed = parse_xdd(out_path)

    assert reparsed.to_dict() == device.to_dict()
