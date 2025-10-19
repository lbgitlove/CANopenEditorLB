"""Validation engine for CANopen devices."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .model import Device, ObjectEntry, ObjectType


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    index: int | None = None
    subindex: int | None = None


MANDATORY_OBJECTS = {0x1000: "Device Type", 0x1001: "Error Register"}


def validate_device(device: Device) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    issues.extend(_check_mandatory_objects(device))
    for entry in device.all_entries():
        issues.extend(_validate_entry(entry))
    return issues


def _check_mandatory_objects(device: Device) -> Iterable[ValidationIssue]:
    for index, name in MANDATORY_OBJECTS.items():
        if device.get_object(index) is None:
            yield ValidationIssue(
                code="MISSING_OBJECT",
                message=f"Mandatory object 0x{index:04X} ({name}) is missing.",
                index=index,
            )


def _validate_entry(entry: ObjectEntry) -> Iterable[ValidationIssue]:
    if entry.object_type == ObjectType.VAR and entry.data_type is None:
        yield ValidationIssue(
            code="MISSING_DATATYPE",
            message=f"Object 0x{entry.index:04X} lacks a data type.",
            index=entry.index,
        )

    if entry.minimum is not None and entry.maximum is not None:
        try:
            low = float(entry.minimum)
            high = float(entry.maximum)
            if low > high:
                yield ValidationIssue(
                    code="INVALID_RANGE",
                    message=f"Object 0x{entry.index:04X} has LowLimit greater than HighLimit.",
                    index=entry.index,
                )
        except ValueError:
            yield ValidationIssue(
                code="INVALID_RANGE_FORMAT",
                message=f"Object 0x{entry.index:04X} has non-numeric range limits.",
                index=entry.index,
            )

    for subindex, sub in entry.sub_objects.items():
        if sub.default is not None and sub.minimum is not None and sub.maximum is not None:
            try:
                value = float(sub.default)
                low = float(sub.minimum)
                high = float(sub.maximum)
            except ValueError:
                continue
            if not (low <= value <= high):
                yield ValidationIssue(
                    code="DEFAULT_OUT_OF_RANGE",
                    message=(
                        f"Default value {sub.default} for 0x{entry.index:04X}sub{subindex} "
                        f"lies outside the limits {sub.minimum}..{sub.maximum}."
                    ),
                    index=entry.index,
                    subindex=subindex,
                    severity="warning",
                )

        if entry.object_type != ObjectType.RECORD and subindex == 0:
            yield ValidationIssue(
                code="UNEXPECTED_SUBINDEX0",
                message=f"Object 0x{entry.index:04X} uses subindex 0 but is not a record.",
                index=entry.index,
                subindex=subindex,
                severity="warning",
            )
