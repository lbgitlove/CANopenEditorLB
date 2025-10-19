from pathlib import Path

from canopen_node_editor.model import ObjectType
from canopen_node_editor.services import NetworkManager

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def _normalize(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith(" * Generated:"):
            lines.append(" * Generated: 2023-01-01 00:00:00Z")
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def test_open_and_export(tmp_path):
    manager = NetworkManager()
    session = manager.open_device(SAMPLES / "demo_device.eds")
    assert session.identifier.startswith("demo_device")

    manager.mark_dirty(session.identifier)
    exports = manager.export_device(session.identifier, tmp_path, header_name="CO_OD.h")
    assert set(exports.keys()) == {"CO_OD.h", "CO_OD.c"}

    header_text = (tmp_path / "CO_OD.h").read_text(encoding="utf-8")
    source_text = (tmp_path / "CO_OD.c").read_text(encoding="utf-8")
    expected_header = (SAMPLES / "demo_device.h").read_text(encoding="utf-8")
    expected_source = (SAMPLES / "demo_device.c").read_text(encoding="utf-8")

    assert _normalize(header_text) == expected_header
    assert _normalize(source_text) == expected_source

    # Exporting clears dirty flag
    assert manager._sessions[session.identifier].dirty is False


def test_create_device_with_minimal_profile():
    manager = NetworkManager()
    session = manager.create_device(include_minimal_profile=True)

    assert session.source_path is None
    assert 0x1000 in session.device.objects
    assert session.device.objects[0x1018].object_type == ObjectType.RECORD
