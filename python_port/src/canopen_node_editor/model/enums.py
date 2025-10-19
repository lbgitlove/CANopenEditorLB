"""Domain enumerations for CANopen object dictionary metadata."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class ObjectType(Enum):
    """CANopen object dictionary entry type identifiers."""

    VAR = 7
    ARRAY = 8
    RECORD = 9

    @classmethod
    def from_eds(cls, value: str) -> "ObjectType":
        normalized = value.strip().upper()
        try:
            return cls[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported ObjectType '{value}'") from exc


class PDOMapping(Enum):
    """PDO mapping flag."""

    OPTIONAL = "0"
    DEFAULT = "1"

    @classmethod
    def from_eds(cls, value: str) -> "PDOMapping":
        normalized = value.strip()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unsupported PDOMapping '{value}'")


class AccessType(Enum):
    RO = "ro"
    WO = "wo"
    RW = "rw"
    CONST = "const"

    @classmethod
    def from_eds(cls, value: str) -> "AccessType":
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported AccessType '{value}'") from exc


class DataType(Enum):
    """Subset of CiA 301 data types required for Phase 1."""

    BOOLEAN = 0x01
    INTEGER8 = 0x02
    INTEGER16 = 0x03
    INTEGER32 = 0x04
    UNSIGNED8 = 0x05
    UNSIGNED16 = 0x06
    UNSIGNED32 = 0x07
    REAL32 = 0x08
    VISIBLE_STRING = 0x09
    OCTET_STRING = 0x0A
    UNICODE_STRING = 0x0B
    TIME_OF_DAY = 0x0C
    TIME_DIFFERENCE = 0x0D
    DOMAIN = 0x0F
    INTEGER24 = 0x10
    REAL64 = 0x11
    INTEGER40 = 0x12
    INTEGER48 = 0x13
    INTEGER56 = 0x14
    INTEGER64 = 0x15
    UNSIGNED24 = 0x16
    UNSIGNED40 = 0x18
    UNSIGNED48 = 0x19
    UNSIGNED56 = 0x1A
    UNSIGNED64 = 0x1B

    @classmethod
    def from_eds(cls, value: str) -> "DataType":
        normalized = value.strip().upper()
        try:
            return _EDS_NAME_MAP[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported DataType '{value}'") from exc


@dataclass(frozen=True)
class ObjectKey:
    index: int
    subindex: int

    def as_tuple(self) -> tuple[int, int]:
        return (self.index, self.subindex)


_EDS_NAME_MAP: Dict[str, DataType] = {name: member for name, member in DataType.__members__.items()}
