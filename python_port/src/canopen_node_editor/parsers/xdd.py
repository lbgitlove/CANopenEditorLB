"""Parser and serializer for CiA XDD/XDC XML files."""
from __future__ import annotations

import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

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


class XDDParseWarning(UserWarning):
    """Warning type emitted when non-fatal XDD issues are encountered."""


class _XDDParseError(RuntimeError):
    """Internal helper used to convert parsing issues into warnings."""

NAMESPACE = "http://www.canopen.org/xml/CANopenDeviceProfile"


def _xpath(*tags: str) -> str:
    return ".//" + "/".join(f"{{*}}{tag}" for tag in tags)


def _find(node: ET.Element, *tags: str) -> ET.Element | None:
    return node.find(_xpath(*tags))


def _findall(node: ET.Element, *tags: str) -> list[ET.Element]:
    return node.findall(_xpath(*tags))


def parse_xdd(path: str | Path) -> Device:
    tree = ET.parse(str(path))
    root = tree.getroot()

    device = Device(info=_parse_device_info(root))
    for obj in _iter_object_nodes(root):
        try:
            entry = _parse_object(obj)
        except _XDDParseError as exc:
            warnings.warn(str(exc), XDDParseWarning, stacklevel=2)
            continue
        if entry is not None:
            device.add_object(entry)
    return device


def _parse_device_info(root: ET.Element) -> DeviceInfo:
    identity = _find(root, "DeviceIdentity")
    if identity is None:
        return DeviceInfo()
    return DeviceInfo(
        vendor_name=_get_text(identity, "VendorName"),
        vendor_number=_get_text(identity, "VendorID"),
        product_name=_get_text(identity, "ProductName"),
        product_number=_get_text(identity, "ProductNumber"),
        revision_number=_get_text(identity, "RevisionNumber"),
        order_code=_get_text(identity, "OrderNumber"),
    )


def _get_text(node: ET.Element, tag: str) -> str | None:
    child = _find(node, tag)
    if child is None or child.text is None:
        return None
    return child.text


def _iter_object_nodes(root: ET.Element) -> list[ET.Element]:
    """Return ordered object nodes irrespective of the surrounding structure."""

    nodes: list[ET.Element] = []
    seen: set[int] = set()

    for candidate in _findall(root, "Object"):
        index_attr = candidate.attrib.get("index")
        if not index_attr:
            # Let the parser raise a warning later when it attempts to parse
            nodes.append(candidate)
            continue
        try:
            index = int(index_attr, 16)
        except ValueError:
            nodes.append(candidate)
            continue
        if index in seen:
            continue
        seen.add(index)
        nodes.append(candidate)

    return nodes


def _parse_object(node: ET.Element) -> ObjectEntry:
    index_attr = node.attrib.get("index")
    if not index_attr:
        raise _XDDParseError("Encountered object without index; skipping entry")
    try:
        index = int(index_attr, 16)
    except ValueError as exc:
        raise _XDDParseError(f"Invalid object index '{index_attr}'") from exc

    object_type_value = node.attrib.get("objectType")
    if object_type_value is None:
        warnings.warn(
            f"Object 0x{index:04X} missing objectType attribute; defaulting to VAR",
            XDDParseWarning,
            stacklevel=3,
        )
        object_type = ObjectType.VAR
    else:
        try:
            object_type = ObjectType(int(object_type_value))
        except (ValueError, KeyError):
            warnings.warn(
                f"Object 0x{index:04X} has unsupported objectType '{object_type_value}'; defaulting to VAR",
                XDDParseWarning,
                stacklevel=3,
            )
            object_type = ObjectType.VAR

    entry = ObjectEntry(
        index=index,
        name=_get_text(node, "Name") or f"0x{index:04X}",
        object_type=object_type,
        data_type=_parse_data_type(_get_text(node, "DataType")),
        access_type=_parse_access_type(_get_text(node, "AccessType")),
        default=_get_text(node, "DefaultValue"),
        value=_get_text(node, "ActualValue"),
        minimum=_get_text(node, "LowLimit"),
        maximum=_get_text(node, "HighLimit"),
        pdo_mapping=_parse_pdo(_get_text(node, "PDOMapping")),
    )

    for sub in _findall(node, "SubObjectList", "SubObject"):
        subindex_attr = sub.attrib.get("subIndex")
        if subindex_attr is None:
            warnings.warn(
                f"Object 0x{index:04X} has sub-object without subIndex; skipping sub-object",
                XDDParseWarning,
                stacklevel=3,
            )
            continue
        try:
            subindex = int(subindex_attr, 0)
        except ValueError:
            warnings.warn(
                f"Object 0x{index:04X} has invalid subIndex '{subindex_attr}'; skipping sub-object",
                XDDParseWarning,
                stacklevel=3,
            )
            continue
        entry.sub_objects[subindex] = SubObject(
            key=ObjectKey(index=index, subindex=subindex),
            name=_get_text(sub, "Name") or f"0x{index:04X} sub{subindex}",
            data_type=_parse_data_type(_get_text(sub, "DataType")) or DataType.UNSIGNED8,
            access_type=_parse_access_type(_get_text(sub, "AccessType")) or AccessType.RW,
            default=_get_text(sub, "DefaultValue"),
            value=_get_text(sub, "ActualValue"),
            minimum=_get_text(sub, "LowLimit"),
            maximum=_get_text(sub, "HighLimit"),
            pdo_mapping=_parse_pdo(_get_text(sub, "PDOMapping")),
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
