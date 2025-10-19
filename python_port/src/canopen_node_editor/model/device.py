"""Core data model abstractions for the CANopenNode Editor port."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .enums import AccessType, DataType, ObjectKey, ObjectType, PDOMapping


@dataclass
class SubObject:
    """Represents a sub-indexed object dictionary entry."""

    key: ObjectKey
    name: str
    data_type: DataType
    access_type: AccessType
    default: Optional[str] = None
    value: Optional[str] = None
    minimum: Optional[str] = None
    maximum: Optional[str] = None
    pdo_mapping: Optional[PDOMapping] = None


@dataclass
class ObjectEntry:
    """Represents a primary object dictionary entry."""

    index: int
    name: str
    object_type: ObjectType
    data_type: Optional[DataType]
    access_type: Optional[AccessType]
    default: Optional[str] = None
    value: Optional[str] = None
    minimum: Optional[str] = None
    maximum: Optional[str] = None
    pdo_mapping: Optional[PDOMapping] = None
    sub_objects: Dict[int, SubObject] = field(default_factory=dict)

    def is_complex(self) -> bool:
        return bool(self.sub_objects)

    def iter_all(self) -> Iterable[SubObject | "ObjectEntry"]:
        if self.sub_objects:
            yield from self.sub_objects.values()
        else:
            yield self


@dataclass
class DeviceInfo:
    vendor_name: Optional[str] = None
    vendor_number: Optional[str] = None
    product_name: Optional[str] = None
    product_number: Optional[str] = None
    revision_number: Optional[str] = None
    order_code: Optional[str] = None


@dataclass
class Device:
    """Unified representation of a CANopen device description."""

    info: DeviceInfo = field(default_factory=DeviceInfo)
    objects: Dict[int, ObjectEntry] = field(default_factory=dict)

    def add_object(self, entry: ObjectEntry) -> None:
        self.objects[entry.index] = entry

    def get_object(self, index: int) -> Optional[ObjectEntry]:
        return self.objects.get(index)

    def all_entries(self) -> List[ObjectEntry]:
        return sorted(self.objects.values(), key=lambda entry: entry.index)

    def to_dict(self) -> Dict[str, object]:
        """Return a serializable representation for debugging and tests."""

        return {
            "info": self.info.__dict__,
            "objects": {
                f"0x{index:04X}": {
                    "name": entry.name,
                    "object_type": entry.object_type.name,
                    "data_type": entry.data_type.name if entry.data_type else None,
                    "access_type": entry.access_type.name if entry.access_type else None,
                    "default": entry.default,
                    "value": entry.value,
                    "minimum": entry.minimum,
                    "maximum": entry.maximum,
                    "pdo_mapping": entry.pdo_mapping.name if entry.pdo_mapping else None,
                    "sub_objects": {
                        f"{subindex}": {
                            "name": sub.name,
                            "data_type": sub.data_type.name,
                            "access_type": sub.access_type.name,
                            "default": sub.default,
                            "value": sub.value,
                            "minimum": sub.minimum,
                            "maximum": sub.maximum,
                            "pdo_mapping": sub.pdo_mapping.name if sub.pdo_mapping else None,
                        }
                        for subindex, sub in sorted(entry.sub_objects.items())
                    },
                }
                for index, entry in sorted(self.objects.items())
            },
        }


def merge_devices(primary: Device, *others: Device) -> Device:
    """Merge multiple device representations prioritising `primary`."""

    merged = Device(info=primary.info, objects=dict(primary.objects))
    for device in others:
        for index, entry in device.objects.items():
            if index not in merged.objects:
                merged.objects[index] = entry
            else:
                merged_entry = merged.objects[index]
                if not merged_entry.name:
                    merged_entry.name = entry.name
                if not merged_entry.data_type:
                    merged_entry.data_type = entry.data_type
                merged_entry.sub_objects.update({
                    key: value
                    for key, value in entry.sub_objects.items()
                    if key not in merged_entry.sub_objects
                })
    return merged
