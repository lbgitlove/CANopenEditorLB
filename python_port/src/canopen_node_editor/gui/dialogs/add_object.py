"""Dialog for creating new object dictionary entries."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)

from ...model import AccessType, DataType, ObjectEntry, ObjectType


@dataclass(slots=True)
class ObjectEntryRequest:
    """Container for data captured by :class:`AddObjectDialog`."""

    index: int
    name: str
    object_type: ObjectType
    data_type: DataType
    access_type: AccessType


class AddObjectDialog(QDialog):
    """Prompt the user for basic object dictionary entry details."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Add Object Dictionary Entry"))

        self._index_edit = QLineEdit(self)
        self._index_edit.setPlaceholderText("0x2000")

        self._name_edit = QLineEdit(self)

        self._object_type = QComboBox(self)
        for value in ObjectType:
            self._object_type.addItem(value.name.title(), value)
        default_object = ObjectType.VAR
        self._object_type.setCurrentIndex(self._object_type.findData(default_object))

        self._data_type = QComboBox(self)
        for value in DataType:
            self._data_type.addItem(value.name, value)
        default_data = DataType.UNSIGNED32
        self._data_type.setCurrentIndex(self._data_type.findData(default_data))

        self._access_type = QComboBox(self)
        for value in AccessType:
            self._access_type.addItem(value.name, value)
        default_access = AccessType.RW
        self._access_type.setCurrentIndex(self._access_type.findData(default_access))

        form = QFormLayout(self)
        form.addRow(self.tr("Index"), self._index_edit)
        form.addRow(self.tr("Name"), self._name_edit)
        form.addRow(self.tr("Object Type"), self._object_type)
        form.addRow(self.tr("Data Type"), self._data_type)
        form.addRow(self.tr("Access"), self._access_type)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)

        self._result: ObjectEntryRequest | None = None

    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        try:
            index = self._parse_index(self._index_edit.text())
        except ValueError:
            QMessageBox.warning(
                self,
                self.tr("Invalid index"),
                self.tr("Please provide a valid hexadecimal or decimal index."),
            )
            self._index_edit.setFocus()
            return

        name = self._name_edit.text().strip() or self.tr("Unnamed Object")
        object_type = self._object_type.currentData()
        data_type = self._data_type.currentData()
        access_type = self._access_type.currentData()

        self._result = ObjectEntryRequest(
            index=index,
            name=name,
            object_type=object_type,
            data_type=data_type,
            access_type=access_type,
        )
        self.accept()

    def request(self) -> ObjectEntryRequest | None:
        """Return the captured object definition if the dialog was accepted."""

        return self._result

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_index(text: str) -> int:
        stripped = text.strip()
        if not stripped:
            raise ValueError("index is required")
        if stripped.lower().startswith("0x"):
            return int(stripped, 16)
        return int(stripped)

    @staticmethod
    def create_entry(data: ObjectEntryRequest) -> ObjectEntry:
        """Transform captured data into an :class:`ObjectEntry`."""

        return ObjectEntry(
            index=data.index,
            name=data.name,
            object_type=data.object_type,
            data_type=data.data_type,
            access_type=data.access_type,
            default=None,
            value=None,
        )
