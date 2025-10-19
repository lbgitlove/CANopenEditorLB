from pathlib import Path

import pytest

from canopen_node_editor.model import ObjectType
from canopen_node_editor.parsers import XDDParseWarning, parse_xdd, serialize_device_to_xdd

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


def test_parse_xdd_missing_metadata_warns(tmp_path):
    xdd_content = """
    <DeviceProfile xmlns="http://www.canopen.org/xml/CANopenDeviceProfile">
        <ProfileBody>
            <DeviceManager>
                <ObjectList>
                    <Object index="0x2000">
                        <Name>Faulty Object</Name>
                        <SubObjectList>
                            <SubObject>
                                <Name>Missing Index</Name>
                            </SubObject>
                        </SubObjectList>
                    </Object>
                </ObjectList>
            </DeviceManager>
        </ProfileBody>
    </DeviceProfile>
    """
    xdd_path = tmp_path / "faulty.xdd"
    xdd_path.write_text(xdd_content, encoding="utf-8")

    with pytest.warns(XDDParseWarning):
        device = parse_xdd(xdd_path)

    assert 0x2000 in device.objects
    assert device.objects[0x2000].object_type == ObjectType.VAR
    assert device.objects[0x2000].sub_objects == {}
