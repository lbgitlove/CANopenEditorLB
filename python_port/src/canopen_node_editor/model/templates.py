"""Factory helpers for creating pre-populated CANopen devices."""
from __future__ import annotations

from .device import Device, ObjectEntry, SubObject
from .enums import AccessType, DataType, ObjectKey, ObjectType


def create_empty_device() -> Device:
    """Return an empty device with no predefined object dictionary entries."""

    return Device()


def create_minimal_profile_device() -> Device:
    """Return a device populated with the mandatory CiA 301 identity entries."""

    device = Device()

    device.add_object(
        ObjectEntry(
            index=0x1000,
            name="Device Type",
            object_type=ObjectType.VAR,
            data_type=DataType.UNSIGNED32,
            access_type=AccessType.RO,
            default="0x00000000",
        )
    )

    device.add_object(
        ObjectEntry(
            index=0x1001,
            name="Error Register",
            object_type=ObjectType.VAR,
            data_type=DataType.UNSIGNED8,
            access_type=AccessType.RO,
            default="0x00",
        )
    )

    identity = ObjectEntry(
        index=0x1018,
        name="Identity Object",
        object_type=ObjectType.RECORD,
        data_type=None,
        access_type=None,
    )
    identity.sub_objects[0] = SubObject(
        key=ObjectKey(index=0x1018, subindex=0),
        name="Number of Entries",
        data_type=DataType.UNSIGNED8,
        access_type=AccessType.RO,
        default="4",
    )
    identity.sub_objects[1] = SubObject(
        key=ObjectKey(index=0x1018, subindex=1),
        name="Vendor ID",
        data_type=DataType.UNSIGNED32,
        access_type=AccessType.RO,
        default="0x00000000",
    )
    identity.sub_objects[2] = SubObject(
        key=ObjectKey(index=0x1018, subindex=2),
        name="Product Code",
        data_type=DataType.UNSIGNED32,
        access_type=AccessType.RO,
        default="0x00000000",
    )
    identity.sub_objects[3] = SubObject(
        key=ObjectKey(index=0x1018, subindex=3),
        name="Revision Number",
        data_type=DataType.UNSIGNED32,
        access_type=AccessType.RO,
        default="0x00000000",
    )
    identity.sub_objects[4] = SubObject(
        key=ObjectKey(index=0x1018, subindex=4),
        name="Serial Number",
        data_type=DataType.UNSIGNED32,
        access_type=AccessType.RO,
        default="0x00000000",
    )

    device.add_object(identity)

    return device
