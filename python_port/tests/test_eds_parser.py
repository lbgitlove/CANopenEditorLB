from pathlib import Path

from canopen_node_editor.parsers import parse_eds, serialize_device_to_eds
from canopen_node_editor.validation import validate_device

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_parse_eds_round_trip(tmp_path):
    eds_path = SAMPLES / "demo_device.eds"
    device = parse_eds(eds_path)

    # Core metadata
    assert device.info.vendor_name == "OpenAI Automation"
    assert 0x1000 in device.objects
    assert device.objects[0x1600].sub_objects[1].name == "Mapped object 1"

    # Round-trip serialisation
    rendered = serialize_device_to_eds(device)
    out_path = tmp_path / "roundtrip.eds"
    out_path.write_text(rendered, encoding="utf-8")

    reparsed = parse_eds(out_path)
    assert reparsed.to_dict() == device.to_dict()

    # Validation of mandatory objects
    issues = validate_device(device)
    assert not any(issue.code == "MISSING_OBJECT" for issue in issues)
