"""Container widget representing a single device tab."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...model import Device, ObjectEntry, SubObject
from ...validation import ValidationIssue, validate_device
from .object_dictionary import ObjectDictionaryWidget
from .object_entry_editor import ObjectEntryEditorWidget
from .pdo_editor import PDOEditorWidget
from .report_viewer import ReportViewerWidget


class DeviceEditorPage(QWidget):
    """Tabbed workspace hosting the editors for a device session."""

    addEntryRequested = Signal()

    def __init__(self, device: Device, parent=None) -> None:
        super().__init__(parent)
        self.device = device
        self.issues: list[ValidationIssue] = []

        layout = QVBoxLayout(self)

        self._tabs = QTabWidget(self)
        layout.addWidget(self._tabs)

        self._object_page = QWidget(self)
        object_layout = QHBoxLayout(self._object_page)
        object_layout.setContentsMargins(0, 0, 0, 0)

        self.object_dictionary = ObjectDictionaryWidget(
            include_subindices=False,
            editable=False,
            show_add_button=True,
        )
        object_layout.addWidget(self.object_dictionary, stretch=1)

        self.object_editor = ObjectEntryEditorWidget(self._object_page)
        object_layout.addWidget(self.object_editor, stretch=2)

        self._tabs.addTab(self._object_page, self.tr("Object Dictionary"))

        self.pdo_editor = PDOEditorWidget(self)
        self._tabs.addTab(self.pdo_editor, self.tr("PDO Editor"))

        self._overview_page = QWidget(self)
        overview_layout = QVBoxLayout(self._overview_page)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel("", self._overview_page)
        self._title.setObjectName("devicePageTitle")
        self._summary = QTextEdit(self._overview_page)
        self._summary.setReadOnly(True)
        self._summary.setObjectName("deviceSummary")
        overview_layout.addWidget(self._title)
        overview_layout.addWidget(self._summary)
        self._tabs.addTab(self._overview_page, self.tr("Overview"))

        self.report_view = ReportViewerWidget(self)
        self._tabs.addTab(self.report_view, self.tr("Validation Report"))

        self.object_dictionary.selectionChanged.connect(self._on_selection_changed)
        self.object_dictionary.addEntryRequested.connect(self.addEntryRequested.emit)
        self.object_editor.entryChanged.connect(self._on_entry_changed)
        self.object_editor.subEntryChanged.connect(self._on_sub_entry_changed)

        self.refresh()

    # ------------------------------------------------------------------
    def set_device(self, device: Device) -> None:
        self.device = device
        self.refresh()

    def refresh(self) -> None:
        self.issues = validate_device(self.device)
        current_entry = self.object_editor.current_entry()
        self.object_dictionary.set_device(self.device)
        if current_entry is not None:
            self.object_dictionary.select_entry(current_entry)
        selection_model = self.object_dictionary.tree().selectionModel()
        if selection_model is None or not selection_model.hasSelection():
            if self.object_dictionary.model().rowCount() > 0:
                self.object_dictionary.select_first_row()
            else:
                self.object_editor.set_entry(None)
        self.pdo_editor.set_device(self.device)
        self.report_view.set_report(self.device, self.issues)
        self._summary.setHtml(self._build_summary())
        self._title.setText(self._format_title())

    # ------------------------------------------------------------------
    def _on_selection_changed(
        self, entry: ObjectEntry | None, _sub: SubObject | None
    ) -> None:
        self.object_editor.set_entry(entry)

    def _on_entry_changed(self, entry: ObjectEntry) -> None:
        self.object_dictionary.refresh(entry)
        self.pdo_editor.set_device(self.device)

    def _on_sub_entry_changed(self, _entry: ObjectEntry, _sub: SubObject) -> None:
        self.pdo_editor.set_device(self.device)

    def show_validation_report(self) -> None:
        index = self._tabs.indexOf(self.report_view)
        if index >= 0:
            self._tabs.setCurrentIndex(index)

    # ------------------------------------------------------------------
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
                        severity=issue.severity.title(),
                        message=issue.message,
                    )
                )
            lines.append("</ul>")
        return "\n".join(lines)
