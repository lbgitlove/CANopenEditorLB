"""Parser and serializer for CiA XDD/XDC XML files."""
from __future__ import annotations

import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator

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


@dataclass
class _ParameterInfo:
    """Aggregated parameter metadata referenced by CANopen objects."""

    unique_id: str
    name: str | None = None
    data_type: DataType | None = None
    access_type: AccessType | None = None
    default: str | None = None
    actual: str | None = None
    minimum: str | None = None
    maximum: str | None = None


# ---------------------------------------------------------------------------
# Generic helpers

def _local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _get_attr(node: ET.Element, name: str) -> str | None:
    lowered = name.lower()
    for key, value in node.attrib.items():
        if key.lower() == lowered:
            return value
    return None


def _first_child(node: ET.Element, *names: str) -> ET.Element | None:
    targets = {name.lower() for name in names}
    for child in node:
        if _local_name(child.tag).lower() in targets:
            return child
    return None


def _first_text(node: ET.Element, *names: str) -> str | None:
    child = _first_child(node, *names)
    if child is None:
        return None
    if child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _iter_children(node: ET.Element, name: str) -> Iterator[ET.Element]:
    target = name.lower()
    for child in node:
        if _local_name(child.tag).lower() == target:
            yield child


def _parse_int(value: str, *, base: int = 16) -> int:
    try:
        return int(value, base)
    except ValueError:
        return int(value, 0)


# ---------------------------------------------------------------------------
# Data type and parameter collection mirroring libEDSsharp

def _collect_data_type_definitions(root: ET.Element) -> Dict[str, DataType]:
    definitions: Dict[str, DataType] = {}
    unresolved: Dict[str, ET.Element] = {}

    for container in root.findall(".//{*}dataTypeList"):
        for element in container:
            unique_id = _get_attr(element, "uniqueID")
            if not unique_id:
                continue
            dtype = _extract_data_type(element, definitions)
            if dtype is not None:
                definitions[unique_id] = dtype
            else:
                unresolved[unique_id] = element

    # Resolve definitions that depend on previously parsed ones.
    changed = True
    while unresolved and changed:
        changed = False
        for unique_id in list(unresolved):
            dtype = _extract_data_type(unresolved[unique_id], definitions)
            if dtype is not None:
                definitions[unique_id] = dtype
                unresolved.pop(unique_id)
                changed = True

    return definitions


def _extract_data_type(node: ET.Element, definitions: Dict[str, DataType]) -> DataType | None:
    for child in node:
        local = _local_name(child.tag).lower()
        if local in {"subrange", "range", "description", "label", "property"}:
            continue
        if local == "datatypeidref":
            ref = _get_attr(child, "uniqueIDRef")
            if ref and ref in definitions:
                return definitions[ref]
            continue
        try:
            return DataType.from_eds(_local_name(child.tag))
        except ValueError:
            continue
    datatype = _get_attr(node, "baseDataType")
    if datatype:
        try:
            return DataType.from_eds(datatype)
        except ValueError:
            return None
    return None


def _collect_parameters(
    root: ET.Element, data_types: Dict[str, DataType]
) -> Dict[str, _ParameterInfo]:
    parameters: Dict[str, _ParameterInfo] = {}

    for param in root.findall(".//{*}parameterList/{*}parameter"):
        unique_id = _get_attr(param, "uniqueID")
        if not unique_id:
            continue
        parameters[unique_id] = _parse_parameter(param, data_types)

    return parameters


def _parse_parameter(node: ET.Element, data_types: Dict[str, DataType]) -> _ParameterInfo:
    label = None
    for candidate in _iter_children(node, "label"):
        text = candidate.text.strip() if candidate.text else ""
        if text:
            label = text
            break
    if label is None:
        label = _get_attr(node, "name")

    data_type = _parse_parameter_data_type(node, data_types)

    access_attr = _get_attr(node, "access") or _get_attr(node, "accessType")
    access_type = _parse_access_type(access_attr)

    default_value = None
    default_node = _first_child(node, "defaultValue")
    if default_node is not None:
        default_value = _get_attr(default_node, "value") or default_node.text
        if default_value:
            default_value = default_value.strip()

    actual_value = None
    actual_node = _first_child(node, "actualValue")
    if actual_node is not None:
        actual_value = _get_attr(actual_node, "value") or actual_node.text
        if actual_value:
            actual_value = actual_value.strip()

    minimum, maximum = _parse_parameter_limits(node)

    return _ParameterInfo(
        unique_id=_get_attr(node, "uniqueID") or "",
        name=label,
        data_type=data_type,
        access_type=access_type,
        default=default_value,
        actual=actual_value,
        minimum=minimum,
        maximum=maximum,
    )


def _parse_parameter_data_type(
    node: ET.Element, data_types: Dict[str, DataType]
) -> DataType | None:
    for child in node:
        local = _local_name(child.tag).lower()
        if local in {
            "label",
            "description",
            "property",
            "defaultvalue",
            "actualvalue",
            "allowedvalues",
        }:
            continue
        if local == "datatypeidref":
            ref = _get_attr(child, "uniqueIDRef")
            if ref and ref in data_types:
                return data_types[ref]
            continue
        try:
            return DataType.from_eds(_local_name(child.tag))
        except ValueError:
            continue
    ref = _get_attr(node, "dataTypeIDRef")
    if ref and ref in data_types:
        return data_types[ref]
    return None


def _parse_parameter_limits(node: ET.Element) -> tuple[str | None, str | None]:
    allowed = _first_child(node, "allowedValues")
    if allowed is None:
        return (None, None)
    for child in allowed:
        if _local_name(child.tag).lower() == "range":
            minimum = _get_attr(child, "minValue")
            maximum = _get_attr(child, "maxValue")
            return (minimum, maximum)
    return (None, None)


# ---------------------------------------------------------------------------
# Public parser API

def parse_xdd(path: str | Path) -> Device:
    tree = ET.parse(str(path))
    root = tree.getroot()

    device = Device(info=_parse_device_info(root))

    canopen_nodes = list(_iter_canopen_object_nodes(root))
    if canopen_nodes:
        data_types = _collect_data_type_definitions(root)
        parameters = _collect_parameters(root, data_types)
        for node in canopen_nodes:
            try:
                entry = _parse_canopen_object(node, parameters)
            except _XDDParseError as exc:
                warnings.warn(str(exc), XDDParseWarning, stacklevel=2)
                continue
            device.add_object(entry)
        return device

    for node in _iter_simple_object_nodes(root):
        try:
            entry = _parse_simple_object(node)
        except _XDDParseError as exc:
            warnings.warn(str(exc), XDDParseWarning, stacklevel=2)
            continue
        device.add_object(entry)

    return device


def _parse_device_info(root: ET.Element) -> DeviceInfo:
    identity = root.find(".//{*}DeviceIdentity")
    if identity is None:
        return DeviceInfo()
    return DeviceInfo(
        vendor_name=_first_text(identity, "VendorName", "vendorName"),
        vendor_number=_first_text(identity, "VendorID", "vendorID"),
        product_name=_first_text(identity, "ProductName", "productName"),
        product_number=_first_text(identity, "ProductNumber", "productID", "productNumber"),
        revision_number=_first_text(identity, "RevisionNumber", "revisionNumber"),
        order_code=_first_text(identity, "OrderNumber", "orderNumber"),
    )


def _iter_canopen_object_nodes(root: ET.Element) -> Iterable[ET.Element]:
    return root.findall(".//{*}CANopenObject")


def _parse_canopen_object(
    node: ET.Element, parameters: Dict[str, _ParameterInfo]
) -> ObjectEntry:
    index_attr = _get_attr(node, "index")
    if not index_attr:
        raise _XDDParseError("Encountered CANopenObject without index; skipping entry")
    try:
        index = _parse_int(index_attr, base=16)
    except ValueError as exc:
        raise _XDDParseError(f"Invalid object index '{index_attr}'") from exc

    object_type = _parse_object_type(_get_attr(node, "objectType"), index)
    unique_ref = _get_attr(node, "uniqueIDRef")
    parameter = parameters.get(unique_ref) if unique_ref else None

    name_attr = _get_attr(node, "name")
    name = name_attr or (parameter.name if parameter and parameter.name else None)
    if not name:
        name = f"0x{index:04X}"

    pdo_mapping = _parse_pdo_mapping(_get_attr(node, "PDOmapping"))

    entry = ObjectEntry(
        index=index,
        name=name,
        object_type=object_type,
        data_type=_select_data_type(parameter),
        access_type=parameter.access_type if parameter else None,
        default=_select_value(parameter, node, "defaultValue"),
        value=_select_value(parameter, node, "actualValue"),
        minimum=_select_value(parameter, node, "lowLimit"),
        maximum=_select_value(parameter, node, "highLimit"),
        pdo_mapping=pdo_mapping,
    )

    for sub_node in _iter_children(node, "CANopenSubObject"):
        sub = _parse_canopen_subobject(index, sub_node, parameters)
        if sub:
            entry.sub_objects[sub.key.subindex] = sub

    if entry.data_type is None and entry.sub_objects:
        # Approximate array/record type from first sub-entry
        first_sub = next(iter(entry.sub_objects.values()))
        entry.data_type = first_sub.data_type

    return entry


def _select_data_type(parameter: _ParameterInfo | None) -> DataType | None:
    return parameter.data_type if parameter else None


def _select_value(
    parameter: _ParameterInfo | None, node: ET.Element, attribute: str
) -> str | None:
    if parameter:
        if attribute == "defaultValue" and parameter.default:
            return parameter.default
        if attribute == "actualValue" and parameter.actual:
            return parameter.actual
        if attribute == "lowLimit" and parameter.minimum:
            return parameter.minimum
        if attribute == "highLimit" and parameter.maximum:
            return parameter.maximum
    attr_value = _get_attr(node, attribute)
    if attr_value:
        return attr_value.strip()
    return None


def _parse_canopen_subobject(
    index: int, node: ET.Element, parameters: Dict[str, _ParameterInfo]
) -> SubObject | None:
    subindex_attr = _get_attr(node, "subIndex")
    if not subindex_attr:
        warnings.warn(
            f"Object 0x{index:04X} has sub-object without subIndex; skipping sub-object",
            XDDParseWarning,
            stacklevel=3,
        )
        return None
    try:
        subindex = _parse_int(subindex_attr, base=16)
    except ValueError:
        warnings.warn(
            f"Object 0x{index:04X} has invalid subIndex '{subindex_attr}'; skipping sub-object",
            XDDParseWarning,
            stacklevel=3,
        )
        return None

    unique_ref = _get_attr(node, "uniqueIDRef")
    parameter = parameters.get(unique_ref) if unique_ref else None

    name_attr = _get_attr(node, "name")
    if not name_attr and parameter and parameter.name:
        name_attr = parameter.name
    if not name_attr:
        name_attr = f"0x{index:04X} sub{subindex}"

    pdo_mapping = _parse_pdo_mapping(_get_attr(node, "PDOmapping"))

    data_type = parameter.data_type if parameter and parameter.data_type else DataType.UNSIGNED8
    access_type = parameter.access_type if parameter and parameter.access_type else AccessType.RW

    return SubObject(
        key=ObjectKey(index=index, subindex=subindex),
        name=name_attr,
        data_type=data_type,
        access_type=access_type,
        default=_select_value(parameter, node, "defaultValue"),
        value=_select_value(parameter, node, "actualValue"),
        minimum=_select_value(parameter, node, "lowLimit"),
        maximum=_select_value(parameter, node, "highLimit"),
        pdo_mapping=pdo_mapping,
    )


def _parse_object_type(value: str | None, index: int) -> ObjectType:
    if value is None:
        warnings.warn(
            f"Object 0x{index:04X} missing objectType attribute; defaulting to VAR",
            XDDParseWarning,
            stacklevel=3,
        )
        return ObjectType.VAR
    try:
        return ObjectType(_parse_int(value, base=0))
    except (ValueError, KeyError):
        try:
            return ObjectType.from_eds(value)
        except ValueError:
            warnings.warn(
                f"Object 0x{index:04X} has unsupported objectType '{value}'; defaulting to VAR",
                XDDParseWarning,
                stacklevel=3,
            )
            return ObjectType.VAR


def _parse_pdo_mapping(value: str | None) -> PDOMapping | None:
    if value is None:
        return None
    try:
        return PDOMapping.from_eds(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Legacy simple structure handling

def _xpath(*tags: str) -> str:
    return ".//" + "/".join(f"{{*}}{tag}" for tag in tags)


def _find(node: ET.Element, *tags: str) -> ET.Element | None:
    return node.find(_xpath(*tags))


def _findall(node: ET.Element, *tags: str) -> list[ET.Element]:
    return node.findall(_xpath(*tags))


def _iter_simple_object_nodes(root: ET.Element) -> list[ET.Element]:
    nodes: list[ET.Element] = []
    seen: set[int] = set()

    for candidate in _findall(root, "Object"):
        index_attr = _get_attr(candidate, "index")
        if not index_attr:
            nodes.append(candidate)
            continue
        try:
            index = _parse_int(index_attr, base=16)
        except ValueError:
            nodes.append(candidate)
            continue
        if index in seen:
            continue
        seen.add(index)
        nodes.append(candidate)

    return nodes


def _parse_simple_object(node: ET.Element) -> ObjectEntry:
    index_attr = _get_attr(node, "index")
    if not index_attr:
        raise _XDDParseError("Encountered object without index; skipping entry")
    try:
        index = _parse_int(index_attr, base=0)
    except ValueError as exc:
        raise _XDDParseError(f"Invalid object index '{index_attr}'") from exc

    object_type_value = _get_attr(node, "objectType")
    object_type = _parse_object_type(object_type_value, index)

    entry = ObjectEntry(
        index=index,
        name=_first_text(node, "Name") or f"0x{index:04X}",
        object_type=object_type,
        data_type=_parse_data_type(_first_text(node, "DataType")),
        access_type=_parse_access_type(_first_text(node, "AccessType")),
        default=_first_text(node, "DefaultValue"),
        value=_first_text(node, "ActualValue"),
        minimum=_first_text(node, "LowLimit"),
        maximum=_first_text(node, "HighLimit"),
        pdo_mapping=_parse_pdo_mapping(_first_text(node, "PDOMapping")),
    )

    for sub in _findall(node, "SubObjectList", "SubObject"):
        subindex_attr = _get_attr(sub, "subIndex")
        if subindex_attr is None:
            warnings.warn(
                f"Object 0x{index:04X} has sub-object without subIndex; skipping sub-object",
                XDDParseWarning,
                stacklevel=3,
            )
            continue
        try:
            subindex = _parse_int(subindex_attr, base=0)
        except ValueError:
            warnings.warn(
                f"Object 0x{index:04X} has invalid subIndex '{subindex_attr}'; skipping sub-object",
                XDDParseWarning,
                stacklevel=3,
            )
            continue
        entry.sub_objects[subindex] = SubObject(
            key=ObjectKey(index=index, subindex=subindex),
            name=_first_text(sub, "Name") or f"0x{index:04X} sub{subindex}",
            data_type=_parse_data_type(_first_text(sub, "DataType")) or DataType.UNSIGNED8,
            access_type=_parse_access_type(_first_text(sub, "AccessType")) or AccessType.RW,
            default=_first_text(sub, "DefaultValue"),
            value=_first_text(sub, "ActualValue"),
            minimum=_first_text(sub, "LowLimit"),
            maximum=_first_text(sub, "HighLimit"),
            pdo_mapping=_parse_pdo_mapping(_first_text(sub, "PDOMapping")),
        )
    return entry


def _parse_data_type(value: str | None) -> DataType | None:
    if value is None:
        return None
    try:
        return DataType.from_eds(value)
    except ValueError:
        try:
            return DataType(_parse_int(value, base=0))
        except (ValueError, KeyError):
            return None


def _parse_access_type(value: str | None) -> AccessType | None:
    if value is None:
        return None
    try:
        return AccessType.from_eds(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Serializer remains unchanged for regression tests

def serialize_device_to_xdd(device: Device) -> str:
    root = ET.Element("DeviceProfile", xmlns="http://www.canopen.org/xml/CANopenDeviceProfile")
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
