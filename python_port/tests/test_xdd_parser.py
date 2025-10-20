from pathlib import Path

import pytest

from canopen_node_editor.model import AccessType, DataType, ObjectType, PDOMapping
from canopen_node_editor.parsers import XDDParseWarning, parse_xdd, serialize_device_to_xdd

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"
EXAMPLES = Path(__file__).resolve().parents[1] / "od_examples"


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


def test_parse_xdd_without_namespace(tmp_path):
    xdd_content = """
    <DeviceProfile>
        <ProfileBody>
            <DeviceIdentity>
                <VendorName>Acme</VendorName>
            </DeviceIdentity>
            <DeviceManager>
                <ObjectList>
                    <Object index="0x2000" objectType="7">
                        <Name>Vendor Specific</Name>
                    </Object>
                </ObjectList>
            </DeviceManager>
        </ProfileBody>
    </DeviceProfile>
    """
    xdd_path = tmp_path / "no_namespace.xdd"
    xdd_path.write_text(xdd_content, encoding="utf-8")

    device = parse_xdd(xdd_path)

    assert device.info.vendor_name == "Acme"
    assert 0x2000 in device.objects
    assert device.objects[0x2000].name == "Vendor Specific"


def test_parse_xdd_with_application_layers_structure():
    xdd_path = SAMPLES / "incomplete_device.xdd"
    device = parse_xdd(xdd_path)

    assert device.info.product_name == "Incomplete Device"
    assert 0x2000 in device.objects
    assert 0x2100 in device.objects
    assert device.objects[0x2100].sub_objects[1].name == "Configuration Value"


def test_parse_xdd_with_mixed_case_attributes():
    xdd_path = SAMPLES / "mixed_case_device.xdd"
    device = parse_xdd(xdd_path)

    indices = {entry.index for entry in device.all_entries()}
    assert indices.issuperset({0x2000, 0x2200})


def test_parse_reference_od_from_csharp_editor():
    xdd_path = EXAMPLES / "od.xdd"
    device = parse_xdd(xdd_path)

    assert device.info.product_name == "minimal_test"
    assert device.objects[0x1001].default == "0x00"
    assert device.objects[0x1005].pdo_mapping == PDOMapping.NONE

    error_array = device.objects[0x1003]
    assert error_array.object_type == ObjectType.ARRAY
    assert len(error_array.sub_objects) == 17
    first_sub = error_array.sub_objects[0]
    assert first_sub.name == "Number of errors"
    assert first_sub.data_type == DataType.UNSIGNED8
    assert first_sub.access_type == AccessType.RW
