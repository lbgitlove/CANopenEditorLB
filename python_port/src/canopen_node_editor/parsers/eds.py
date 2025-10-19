"""Parser and serializer for CANopen EDS files."""
from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import re

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

_OBJECT_SECTION_RE = re.compile(r"^(?P<index>[0-9A-Fa-f]{4})(?:sub(?P<subindex>\d+))?$")


def parse_eds(path: str | Path) -> Device:
    """Parse an EDS file and return a :class:`Device`."""

    parser = _load_parser(path)
    device = Device(info=_parse_device_info(parser))

    indexed_sections: dict[int, dict[int, dict[str, str]]] = {}

    for section_name in parser.sections():
        match = _OBJECT_SECTION_RE.match(section_name)
        if not match:
            continue
        index = int(match.group("index"), 16)
        subindex = match.group("subindex")
        sections = indexed_sections.setdefault(index, {})
        if subindex is None:
            sections["main"] = dict(parser.items(section_name))
        else:
            sections[int(subindex)] = dict(parser.items(section_name))

    for index, subentries in sorted(indexed_sections.items()):
        main_section = subentries.get("main", {})
        object_entry = ObjectEntry(
            index=index,
            name=main_section.get("ParameterName", f"0x{index:04X}"),
            object_type=_parse_object_type(main_section.get("ObjectType", "VAR")),
            data_type=_parse_data_type(main_section.get("DataType")),
            access_type=_parse_access_type(main_section.get("AccessType")),
            default=_normalise_default(main_section.get("DefaultValue")),
            value=_normalise_default(main_section.get("Value")),
            minimum=_normalise_default(main_section.get("LowLimit")),
            maximum=_normalise_default(main_section.get("HighLimit")),
            pdo_mapping=_parse_pdo(main_section.get("PDOMapping")),
        )

        for subindex, details in sorted(
            (item for item in subentries.items() if not isinstance(item[0], str)),
            key=lambda item: item[0],
        ):
            sub = SubObject(
                key=ObjectKey(index=index, subindex=subindex),
                name=details.get("ParameterName", f"0x{index:04X} sub{subindex}"),
                data_type=_parse_data_type(details.get("DataType", main_section.get("DataType", "UNSIGNED8"))),
                access_type=_parse_access_type(details.get("AccessType", main_section.get("AccessType", "rw"))),
                default=_normalise_default(details.get("DefaultValue")),
                value=_normalise_default(details.get("Value")),
                minimum=_normalise_default(details.get("LowLimit")),
                maximum=_normalise_default(details.get("HighLimit")),
                pdo_mapping=_parse_pdo(details.get("PDOMapping")),
            )
            object_entry.sub_objects[subindex] = sub
        device.add_object(object_entry)

    return device


def serialize_device_to_eds(device: Device) -> str:
    parser = ConfigParser()
    parser.optionxform = str
    parser.add_section("DeviceInfo")
    parser.set("DeviceInfo", "VendorName", device.info.vendor_name or "")
    parser.set("DeviceInfo", "VendorNumber", device.info.vendor_number or "")
    parser.set("DeviceInfo", "ProductName", device.info.product_name or "")
    parser.set("DeviceInfo", "ProductNumber", device.info.product_number or "")
    parser.set("DeviceInfo", "RevisionNumber", device.info.revision_number or "")
    parser.set("DeviceInfo", "OrderCode", device.info.order_code or "")

    for entry in device.all_entries():
        section_name = f"{entry.index:04X}"
        parser.add_section(section_name)
        parser.set(section_name, "ParameterName", entry.name)
        parser.set(section_name, "ObjectType", entry.object_type.name)
        if entry.data_type:
            parser.set(section_name, "DataType", entry.data_type.name)
        if entry.access_type:
            parser.set(section_name, "AccessType", entry.access_type.value)
        if entry.default is not None:
            parser.set(section_name, "DefaultValue", entry.default)
        if entry.value is not None:
            parser.set(section_name, "Value", entry.value)
        if entry.minimum is not None:
            parser.set(section_name, "LowLimit", entry.minimum)
        if entry.maximum is not None:
            parser.set(section_name, "HighLimit", entry.maximum)
        if entry.pdo_mapping is not None:
            parser.set(section_name, "PDOMapping", entry.pdo_mapping.value)

        for subindex, sub in sorted(entry.sub_objects.items()):
            sub_section = f"{entry.index:04X}sub{subindex}"
            parser.add_section(sub_section)
            parser.set(sub_section, "ParameterName", sub.name)
            parser.set(sub_section, "DataType", sub.data_type.name)
            parser.set(sub_section, "AccessType", sub.access_type.value)
            if sub.default is not None:
                parser.set(sub_section, "DefaultValue", sub.default)
            if sub.value is not None:
                parser.set(sub_section, "Value", sub.value)
            if sub.minimum is not None:
                parser.set(sub_section, "LowLimit", sub.minimum)
            if sub.maximum is not None:
                parser.set(sub_section, "HighLimit", sub.maximum)
            if sub.pdo_mapping is not None:
                parser.set(sub_section, "PDOMapping", sub.pdo_mapping.value)

    output_lines = []
    for section in parser.sections():
        output_lines.append(f"[{section}]")
        for key, value in parser.items(section):
            output_lines.append(f"{key}={value}")
        output_lines.append("")
    return "\n".join(output_lines)


def _load_parser(path: str | Path) -> ConfigParser:
    parser = ConfigParser()
    parser.optionxform = str
    with open(path, "r", encoding="utf-8") as handle:
        parser.read_file(handle)
    return parser


def _parse_device_info(parser: ConfigParser) -> DeviceInfo:
    if not parser.has_section("DeviceInfo"):
        return DeviceInfo()
    section = parser["DeviceInfo"]
    return DeviceInfo(
        vendor_name=section.get("VendorName"),
        vendor_number=section.get("VendorNumber"),
        product_name=section.get("ProductName"),
        product_number=section.get("ProductNumber"),
        revision_number=section.get("RevisionNumber"),
        order_code=section.get("OrderCode"),
    )


def _parse_object_type(value: str | None) -> ObjectType:
    if value is None:
        return ObjectType.VAR
    return ObjectType.from_eds(value)


def _parse_data_type(value: str | None) -> DataType | None:
    if value in (None, "0"):
        return None
    try:
        return DataType.from_eds(value)
    except ValueError:
        return DataType(int(value, 0))


def _parse_access_type(value: str | None) -> AccessType | None:
    if value is None:
        return None
    return AccessType.from_eds(value)


def _parse_pdo(value: str | None) -> PDOMapping | None:
    if value is None:
        return None
    try:
        return PDOMapping.from_eds(value)
    except ValueError:
        return None


def _normalise_default(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()
