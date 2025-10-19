"""Widget embedding rendered validation reports."""

from __future__ import annotations

from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from ...model import Device
from ...validation import ValidationIssue
from ...services.reporting import render_validation_report


class ReportViewerWidget(QWidget):
    """Display HTML validation reports inside the application."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._browser = QTextBrowser(self)
        self._browser.setOpenExternalLinks(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._browser)

        self._device: Device | None = None
        self._issues: list[ValidationIssue] = []

    def set_report(self, device: Device | None, issues: list[ValidationIssue] | None = None) -> None:
        self._device = device
        self._issues = list(issues or [])
        if device is None:
            self._browser.setHtml("<p>" + self.tr("No device loaded.") + "</p>")
            return
        html = render_validation_report(device, self._issues)
        self._browser.setHtml(html)

    def document(self) -> QTextBrowser:
        return self._browser

    def issues(self) -> list[ValidationIssue]:
        return list(self._issues)
