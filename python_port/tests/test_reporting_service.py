from pathlib import Path

from canopen_node_editor.parsers import parse_eds
from canopen_node_editor.services import render_validation_report
from canopen_node_editor.validation import validate_device

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_render_validation_report_contains_summary():
    device = parse_eds(SAMPLES / "demo_device.eds")
    issues = validate_device(device)
    html = render_validation_report(device, issues)

    assert "Validation Report" in html
    assert "Total issues" in html
    # Mandatory object 0x1001 exists, so ensure table rows render
    assert "No validation issues detected" in html
