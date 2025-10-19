"""Runtime coordination of multiple CANopen devices."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from ..exporters import export_canopennode_sources
from ..model import Device, create_empty_device, create_minimal_profile_device
from ..parsers import parse_eds, parse_xdd

@dataclass
class DeviceSession:
    identifier: str
    device: Device
    source_path: Path | None = None
    dirty: bool = False
    exports: Dict[str, Path] = field(default_factory=dict)


class NetworkManager:
    """Manage loaded devices and orchestrate export flows."""

    def __init__(self) -> None:
        self._sessions: Dict[str, DeviceSession] = {}

    def sessions(self) -> List[DeviceSession]:
        return list(self._sessions.values())

    def open_device(self, path: Path) -> DeviceSession:
        device = self._parse_device(path)
        identifier = self._unique_identifier(path.stem)
        session = DeviceSession(identifier=identifier, device=device, source_path=Path(path))
        self._sessions[identifier] = session
        return session

    def register_device(self, identifier: str, device: Device) -> DeviceSession:
        identifier = self._unique_identifier(identifier)
        session = DeviceSession(identifier=identifier, device=device, source_path=None)
        self._sessions[identifier] = session
        return session

    def create_device(self, include_minimal_profile: bool = False) -> DeviceSession:
        """Create a new in-memory device, optionally pre-populated with profile data."""

        device = (
            create_minimal_profile_device() if include_minimal_profile else create_empty_device()
        )
        base_identifier = "Minimal Device" if include_minimal_profile else "New Device"
        return self.register_device(base_identifier, device)

    def mark_dirty(self, identifier: str, dirty: bool = True) -> None:
        session = self._require_session(identifier)
        session.dirty = dirty

    def close_device(self, identifier: str) -> None:
        self._sessions.pop(identifier, None)

    def export_device(
        self,
        identifier: str,
        output_dir: Path,
        header_name: str = "CO_OD.h",
        source_name: str = "CO_OD.c",
    ) -> Dict[str, Path]:
        session = self._require_session(identifier)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        rendered = export_canopennode_sources(
            session.device, header_name=header_name, source_name=source_name
        )

        exports: Dict[str, Path] = {}
        for filename, content in rendered.items():
            destination = output_dir / filename
            destination.write_text(content, encoding="utf-8")
            exports[filename] = destination

        session.exports = exports
        session.dirty = False
        return exports

    def _require_session(self, identifier: str) -> DeviceSession:
        try:
            return self._sessions[identifier]
        except KeyError as exc:
            raise KeyError(f"Unknown session '{identifier}'") from exc

    def _parse_device(self, path: Path) -> Device:
        suffix = Path(path).suffix.lower()
        if suffix == ".eds":
            return parse_eds(path)
        if suffix in {".xdd", ".xdc"}:
            return parse_xdd(path)
        raise ValueError(f"Unsupported device description: {path}")

    def _unique_identifier(self, stem: str) -> str:
        candidate = stem
        counter = 1
        while candidate in self._sessions:
            candidate = f"{stem}_{counter}"
            counter += 1
        return candidate
