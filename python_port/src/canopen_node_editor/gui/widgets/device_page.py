"""Container widget representing a single device tab."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from ...model import Device
from ...validation import ValidationIssue, validate_device


class DeviceEditorPage(QWidget):
    """Simple summary widget holding a :class:`Device` reference."""

    def __init__(self, device: Device, parent=None) -> None:
        super().__init__(parent)
        self.device = device
        self.issues: list[ValidationIssue] = []

        self._title = QLabel("", self)
        self._title.setObjectName("devicePageTitle")

        self._summary = QTextEdit(self)
        self._summary.setReadOnly(True)
        self._summary.setObjectName("deviceSummary")

        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._summary)

        self.refresh()

    # ------------------------------------------------------------------
    def set_device(self, device: Device) -> None:
        """Replace the underlying device reference and refresh content."""

        self.device = device
        self.refresh()

    def refresh(self) -> None:
        """Re-run validation and update the rendered summary."""

        self.issues = validate_device(self.device)
        self._title.setText(self._format_title())
        self._summary.setHtml(self._build_summary())

    def _format_title(self) -> str:
        info = self.device.info
        name = info.product_name or self.tr("Unnamed Device")
        vendor = info.vendor_name or self.tr("Unknown Vendor")
        return self.tr("{name} – {vendor}").format(name=name, vendor=vendor)

    def _build_summary(self) -> str:
        info = self.device.info
        lines = ["<ul>"]
        lines.append(f"<li><strong>{self.tr('Vendor')}:</strong> {info.vendor_name or '-'}")
        lines.append(f"<li><strong>{self.tr('Product')}:</strong> {info.product_name or '-'}")
        lines.append(f"<li><strong>{self.tr('Revision')}:</strong> {info.revision_number or '-'}")
        lines.append("</ul>")
        lines.append("<h3>" + self.tr("Validation Issues") + "</h3>")
        if not self.issues:
            lines.append("<p>" + self.tr("No validation issues detected.") + "</p>")
        else:
            lines.append("<ul>")
            for issue in self.issues:
                lines.append(
                    "<li><strong>{severity}</strong>: {message}</li>".format(
                        severity=issue.severity.title(), message=issue.message
                    )
                )
            lines.append("</ul>")
        return "\n".join(lines)
