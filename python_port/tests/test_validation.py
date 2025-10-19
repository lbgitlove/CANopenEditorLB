from canopen_node_editor.model import Device, ObjectEntry, ObjectType
from canopen_node_editor.validation import ValidationIssue, validate_device


def test_validation_reports_missing_objects():
    device = Device()
    issues = validate_device(device)
    codes = {issue.code for issue in issues}
    assert "MISSING_OBJECT" in codes
    severities = {issue.severity for issue in issues if issue.code == "MISSING_OBJECT"}
    assert severities == {"warning"}


def test_validation_detects_bad_range():
    entry = ObjectEntry(
        index=0x2000,
        name="Invalid Range",
        object_type=ObjectType.VAR,
        data_type=None,
        access_type=None,
        minimum="10",
        maximum="5",
    )
    device = Device()
    device.add_object(entry)

    issues = validate_device(device)
    assert any(issue.code == "INVALID_RANGE" for issue in issues)
    assert any(issue.code == "MISSING_DATATYPE" for issue in issues)
