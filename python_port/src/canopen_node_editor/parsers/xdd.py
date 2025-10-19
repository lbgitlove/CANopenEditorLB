"""Parser and serializer for CiA XDD/XDC XML files."""
from __future__ import annotations

from pathlib import Path
from typing import Dict
import xml.etree.ElementTree as ET

from ..model import (
    AccessType,
    DataType,
    Device,
    DeviceInfo,
    ObjectEntry,
    ObjectKey,
    ObjectType,
    PDOMapping,
    SubObject,
)

NAMESPACE = "http://www.canopen.org/xml/CANopenDeviceProfile"
NS = {"ns": NAMESPACE}


def parse_xdd(path: str | Path) -> Device:
    tree = ET.parse(str(path))
    root = tree.getroot()

    device = Device(info=_parse_device_info(root))
    for obj in root.findall(".//ns:ProfileBody/ns:DeviceManager/ns:ObjectList/ns:Object", NS):
        entry = _parse_object(obj)
        device.add_object(entry)
    return device


def _parse_device_info(root: ET.Element) -> DeviceInfo:
    identity = root.find(".//ns:ProfileBody/ns:DeviceIdentity", NS)
    if identity is None:
        return DeviceInfo()
    return DeviceInfo(
        vendor_name=_get_text(identity, "ns:VendorName"),
        vendor_number=_get_text(identity, "ns:VendorID"),
        product_name=_get_text(identity, "ns:ProductName"),
        product_number=_get_text(identity, "ns:ProductNumber"),
        revision_number=_get_text(identity, "ns:RevisionNumber"),
        order_code=_get_text(identity, "ns:OrderNumber"),
    )


def _get_text(node: ET.Element, query: str) -> str | None:
    child = node.find(query, NS)
    if child is None or child.text is None:
        return None
    return child.text


def _parse_object(node: ET.Element) -> ObjectEntry:
    index = int(node.attrib["index"], 16)
    entry = ObjectEntry(
        index=index,
        name=_get_text(node, "ns:Name") or f"0x{index:04X}",
        object_type=ObjectType(int(node.attrib["objectType"])),
        data_type=_parse_data_type(_get_text(node, "ns:DataType")),
        access_type=_parse_access_type(_get_text(node, "ns:AccessType")),
        default=_get_text(node, "ns:DefaultValue"),
        value=_get_text(node, "ns:ActualValue"),
        minimum=_get_text(node, "ns:LowLimit"),
        maximum=_get_text(node, "ns:HighLimit"),
        pdo_mapping=_parse_pdo(_get_text(node, "ns:PDOMapping")),
    )

    for sub in node.findall("ns:SubObjectList/ns:SubObject", NS):
        subindex = int(sub.attrib["subIndex"], 0)
        entry.sub_objects[subindex] = SubObject(
            key=ObjectKey(index=index, subindex=subindex),
            name=_get_text(sub, "ns:Name") or f"0x{index:04X} sub{subindex}",
            data_type=_parse_data_type(_get_text(sub, "ns:DataType")) or DataType.UNSIGNED8,
            access_type=_parse_access_type(_get_text(sub, "ns:AccessType")) or AccessType.RW,
            default=_get_text(sub, "ns:DefaultValue"),
            value=_get_text(sub, "ns:ActualValue"),
            minimum=_get_text(sub, "ns:LowLimit"),
            maximum=_get_text(sub, "ns:HighLimit"),
            pdo_mapping=_parse_pdo(_get_text(sub, "ns:PDOMapping")),
        )
    return entry


def _parse_data_type(value: str | None) -> DataType | None:
    if value is None:
        return None
    try:
        return DataType.from_eds(value)
    except ValueError:
        return DataType(int(value, 0))


def _parse_access_type(value: str | None) -> AccessType | None:
    if value is None:
        return None
    try:
        return AccessType.from_eds(value)
    except ValueError:
        return None


def _parse_pdo(value: str | None) -> PDOMapping | None:
    if value is None:
        return None
    try:
        return PDOMapping.from_eds(value)
    except ValueError:
        return None


def serialize_device_to_xdd(device: Device) -> str:
    root = ET.Element("DeviceProfile", xmlns=NAMESPACE)
    profile_body = ET.SubElement(root, "ProfileBody")
    identity = ET.SubElement(profile_body, "DeviceIdentity")
    _write_text(identity, "VendorName", device.info.vendor_name)
    _write_text(identity, "VendorID", device.info.vendor_number)
    _write_text(identity, "ProductName", device.info.product_name)
    _write_text(identity, "ProductNumber", device.info.product_number)
    _write_text(identity, "RevisionNumber", device.info.revision_number)
    _write_text(identity, "OrderNumber", device.info.order_code)

    manager = ET.SubElement(profile_body, "DeviceManager")
    object_list = ET.SubElement(manager, "ObjectList")

    for entry in device.all_entries():
        obj = ET.SubElement(
            object_list,
            "Object",
            index=f"0x{entry.index:04X}",
            objectType=str(entry.object_type.value),
        )
        _write_text(obj, "Name", entry.name)
        if entry.data_type:
            _write_text(obj, "DataType", entry.data_type.name)
        if entry.access_type:
            _write_text(obj, "AccessType", entry.access_type.value)
        _write_optional(obj, "DefaultValue", entry.default)
        _write_optional(obj, "ActualValue", entry.value)
        _write_optional(obj, "LowLimit", entry.minimum)
        _write_optional(obj, "HighLimit", entry.maximum)
        if entry.pdo_mapping:
            _write_text(obj, "PDOMapping", entry.pdo_mapping.value)

        if entry.sub_objects:
            sub_list = ET.SubElement(obj, "SubObjectList")
            for subindex, sub in sorted(entry.sub_objects.items()):
                sub_node = ET.SubElement(sub_list, "SubObject", subIndex=str(subindex))
                _write_text(sub_node, "Name", sub.name)
                _write_text(sub_node, "DataType", sub.data_type.name)
                _write_text(sub_node, "AccessType", sub.access_type.value)
                _write_optional(sub_node, "DefaultValue", sub.default)
                _write_optional(sub_node, "ActualValue", sub.value)
                _write_optional(sub_node, "LowLimit", sub.minimum)
                _write_optional(sub_node, "HighLimit", sub.maximum)
                if sub.pdo_mapping:
                    _write_text(sub_node, "PDOMapping", sub.pdo_mapping.value)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _write_text(parent: ET.Element, tag: str, text: str | None) -> None:
    if text is None:
        return
    child = ET.SubElement(parent, tag)
    child.text = text


def _write_optional(parent: ET.Element, tag: str, value: str | None) -> None:
    if value is not None:
        _write_text(parent, tag, value)
