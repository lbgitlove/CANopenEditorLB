from pathlib import Path

from canopen_node_editor.exporters import export_header, export_source
from canopen_node_editor.parsers import parse_eds

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def _normalize_timestamp(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith(" * Generated:"):
            lines.append(" * Generated: 2023-01-01 00:00:00Z")
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def test_header_export_matches_fixture():
    device = parse_eds(SAMPLES / "demo_device.eds")
    rendered = export_header(device, header_name="CO_OD.h")
    normalized = _normalize_timestamp(rendered)
    expected = (SAMPLES / "demo_device.h").read_text(encoding="utf-8")
    assert normalized == expected


def test_source_export_matches_fixture():
    device = parse_eds(SAMPLES / "demo_device.eds")
    rendered = export_source(device, header_name="CO_OD.h", source_name="CO_OD.c")
    normalized = _normalize_timestamp(rendered)
    expected = (SAMPLES / "demo_device.c").read_text(encoding="utf-8")
    assert normalized == expected
