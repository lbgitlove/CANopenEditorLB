"""Property inspector displaying details of the selected object."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ...model import ObjectEntry, SubObject


class PropertyInspectorWidget(QWidget):
    """Simple property grid highlighting metadata for the selection."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._header = QLabel(self.tr("No selection"))
        self._header.setObjectName("propertyInspectorHeader")
        self._header.setWordWrap(True)

        self._body = QLabel("")
        self._body.setWordWrap(True)
        flags = self._body.textInteractionFlags() | Qt.TextInteractionFlag.LinksAccessibleByMouse
        self._body.setTextInteractionFlags(flags)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._body)

        layout = QVBoxLayout(self)
        layout.addWidget(self._header)
        layout.addWidget(scroll)

        self._current_entry: ObjectEntry | None = None
        self._current_sub: SubObject | None = None

    def display(self, entry: ObjectEntry | None, sub: SubObject | None = None) -> None:
        self._current_entry = entry
        self._current_sub = sub
        if entry is None:
            self._header.setText(self.tr("No selection"))
            self._body.setText("")
            return

        if sub is None:
            title = f"0x{entry.index:04X} – {entry.name}"
            details = [
                self.tr("Object Type: {type}").format(type=entry.object_type.name if entry.object_type else "-"),
                self.tr("Data Type: {type}").format(type=entry.data_type.name if entry.data_type else "-"),
                self.tr("Access: {access}").format(access=entry.access_type.name if entry.access_type else "-"),
            ]
            if entry.default:
                details.append(self.tr("Default: {value}").format(value=entry.default))
            if entry.value:
                details.append(self.tr("Value: {value}").format(value=entry.value))
        else:
            subindex = getattr(getattr(sub, "key", None), "subindex", None)
            title = self.tr("SubIndex {sub} – {name}").format(sub=subindex if subindex is not None else "?", name=sub.name)
            details = [
                self.tr("Data Type: {type}").format(type=sub.data_type.name),
                self.tr("Access: {access}").format(access=sub.access_type.name),
            ]
            if sub.default:
                details.append(self.tr("Default: {value}").format(value=sub.default))
            if sub.minimum and sub.maximum:
                details.append(
                    self.tr("Range: {min} … {max}").format(min=sub.minimum, max=sub.maximum)
                )
            if sub.pdo_mapping:
                details.append(self.tr("PDO Mapping: {mapping}").format(mapping=sub.pdo_mapping.name))

        self._header.setText(title)
        self._body.setText("\n".join(details))

    def current_entry(self) -> ObjectEntry | None:
        return self._current_entry

    def current_subobject(self) -> SubObject | None:
        return self._current_sub
