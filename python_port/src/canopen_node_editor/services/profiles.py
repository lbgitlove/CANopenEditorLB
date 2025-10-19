"""Profile discovery and metadata extraction utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from ..model import Device
from ..parsers import parse_eds, parse_xdd

SUPPORTED_EXTENSIONS = {".eds", ".xdd", ".xdc"}


@dataclass(frozen=True)
class ProfileMetadata:
    name: str
    path: Path
    vendor: str | None = None
    version: str | None = None


class ProfileRepository:
    """Scan file system locations for CANopen profiles."""

    def __init__(self, search_paths: Iterable[Path] | None = None) -> None:
        self._search_paths: List[Path] = [Path(path) for path in search_paths or []]

    @property
    def search_paths(self) -> List[Path]:
        return list(self._search_paths)

    def add_search_path(self, path: Path) -> None:
        normalized = Path(path)
        if normalized not in self._search_paths:
            self._search_paths.append(normalized)

    def discover(self) -> List[ProfileMetadata]:
        profiles: List[ProfileMetadata] = []
        for base in self._search_paths:
            if not base.exists():
                continue
            if base.is_file():
                profiles.extend(self._load_profile(base))
                continue
            for candidate in base.rglob("*"):
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                    profiles.extend(self._load_profile(candidate))
        unique: dict[Path, ProfileMetadata] = {profile.path: profile for profile in profiles}
        return sorted(unique.values(), key=lambda meta: meta.name.lower())

    def _load_profile(self, path: Path) -> List[ProfileMetadata]:
        try:
            device = self._parse_device(path)
        except Exception:
            return []

        info = device.info
        name = info.product_name or path.stem
        version = info.revision_number
        vendor = info.vendor_name
        metadata = ProfileMetadata(name=name, version=version, vendor=vendor, path=path)
        return [metadata]

    def _parse_device(self, path: Path) -> Device:
        suffix = path.suffix.lower()
        if suffix == ".eds":
            return parse_eds(path)
        if suffix in {".xdd", ".xdc"}:
            return parse_xdd(path)
        raise ValueError(f"Unsupported profile extension: {suffix}")
