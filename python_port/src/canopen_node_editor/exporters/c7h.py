"""CANopenNode source generation helpers."""
from __future__ import annotations

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from ..model import Device, ObjectEntry, ObjectType, SubObject
from ..model.enums import DataType

HEADER_COMMENT = """/*
 * CANopenNode object dictionary header
 * Generated: {timestamp}
 */
"""

SOURCE_COMMENT = """/*
 * CANopenNode object dictionary source
 * Generated: {timestamp}
 */
"""

HEADER_INCLUDE = "#include <stdint.h>\n\n"

DEFAULT_HEADER_NAME = "CO_OD.h"
DEFAULT_SOURCE_NAME = "CO_OD.c"

_C_TYPE_MAP: dict[DataType, str] = {
    DataType.BOOLEAN: "uint8_t",
    DataType.INTEGER8: "int8_t",
    DataType.INTEGER16: "int16_t",
    DataType.INTEGER32: "int32_t",
    DataType.UNSIGNED8: "uint8_t",
    DataType.UNSIGNED16: "uint16_t",
    DataType.UNSIGNED32: "uint32_t",
    DataType.REAL32: "float",
    DataType.REAL64: "double",
    DataType.UNSIGNED64: "uint64_t",
    DataType.INTEGER64: "int64_t",
}


def export_header(device: Device, header_name: str = DEFAULT_HEADER_NAME) -> str:
    """Render the CANopenNode dictionary header for ``device``."""

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    guard = _make_include_guard(header_name)

    buffer = StringIO()
    buffer.write(HEADER_COMMENT.format(timestamp=timestamp))
    buffer.write(f"#ifndef {guard}\n")
    buffer.write(f"#define {guard}\n\n")
    buffer.write(HEADER_INCLUDE)

    for entry in device.all_entries():
        buffer.write(_format_declaration(entry))

    buffer.write("\n")
    buffer.write(f"#endif /* {guard} */\n")
    return buffer.getvalue()


def export_source(
    device: Device,
    header_name: str = DEFAULT_HEADER_NAME,
    source_name: str = DEFAULT_SOURCE_NAME,
) -> str:
    """Render the CANopenNode dictionary source for ``device``."""

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    header_path = Path(header_name).name

    buffer = StringIO()
    buffer.write(SOURCE_COMMENT.format(timestamp=timestamp))
    buffer.write(f'#include "{header_path}"\n\n')

    for entry in device.all_entries():
        buffer.write(_format_definition(entry))

    return buffer.getvalue()


def export_canopennode_sources(
    device: Device,
    header_name: str = DEFAULT_HEADER_NAME,
    source_name: str = DEFAULT_SOURCE_NAME,
) -> dict[str, str]:
    """Return mapping of filenames to rendered CANopenNode artefacts."""

    return {
        header_name: export_header(device, header_name=header_name),
        source_name: export_source(device, header_name=header_name, source_name=source_name),
    }


def export_c7h(device: Device) -> str:
    """Backward compatible shim for legacy tests.

    The legacy tooling produced a monolithic `.c7h` header. The Python port now
    emits dedicated `.c` and `.h` files. This helper preserves compatibility by
    delegating to :func:`export_header`.
    """

    return export_header(device)


def _format_declaration(entry: ObjectEntry) -> str:
    label = f"OD_{entry.index:04X}"
    if entry.object_type == ObjectType.VAR:
        c_type = _resolve_c_type(entry)
        return f"extern {c_type} {label};\n"

    struct_name = f"{label}_t"
    lines = ["\n", "typedef struct {\n"]
    for subindex, sub in sorted(entry.sub_objects.items()):
        c_type = _resolve_c_type(sub)
        field_name = _safe_name(sub.name)
        lines.append(f"    {c_type} {field_name}; /* sub{subindex} */\n")
    lines.append(f"}} {struct_name};\n")
    lines.append(f"extern {struct_name} {label};\n")
    return "".join(lines)


def _format_definition(entry: ObjectEntry) -> str:
    label = f"OD_{entry.index:04X}"
    if entry.object_type == ObjectType.VAR:
        c_type = _resolve_c_type(entry)
        value = entry.value or entry.default or "0"
        return f"{c_type} {label} = {value};\n"

    struct_name = f"{label}_t"
    lines = ["\n", f"{struct_name} {label} = {{\n"]
    for subindex, sub in sorted(entry.sub_objects.items()):
        field_name = _safe_name(sub.name)
        value = sub.value or sub.default or "0"
        lines.append(f"    .{field_name} = {value},\n")
    lines.append("};\n")
    return "".join(lines)


def _resolve_c_type(entry: ObjectEntry | SubObject) -> str:
    data_type = entry.data_type
    if data_type is None:
        return "uint32_t"
    return _C_TYPE_MAP.get(data_type, "uint32_t")


def _safe_name(name: str) -> str:
    filtered = [ch if ch.isalnum() else '_' for ch in name]
    candidate = ''.join(filtered)
    if candidate and candidate[0].isdigit():
        candidate = f'_{candidate}'
    return candidate or 'unnamed'


def _make_include_guard(filename: str) -> str:
    stem = Path(filename).name.upper()
    safe = [ch if ch.isalnum() else '_' for ch in stem]
    return "".join(safe)
