from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QMessageBox

from canopen_node_editor.gui.main_window import EditorMainWindow
from canopen_node_editor.gui.widgets.device_page import DeviceEditorPage
from canopen_node_editor.model import Device
from canopen_node_editor.parsers import parse_eds
from canopen_node_editor.services.network import NetworkManager
from canopen_node_editor.services.profiles import ProfileRepository
from canopen_node_editor.services.settings import SettingsManager


@pytest.fixture()
def settings_manager(tmp_path) -> SettingsManager:
    storage = tmp_path / "settings"
    storage.mkdir(parents=True, exist_ok=True)
    manager = SettingsManager(storage_dir=storage)
    manager.load()
    return manager


@pytest.fixture()
def sample_device() -> Device:
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "samples" / "demo_device.eds"
    return parse_eds(path)


@pytest.mark.usefixtures("qapp")
def test_main_window_populates_views(qtbot, settings_manager, sample_device):
    network = NetworkManager()
    session = network.register_device("demo", sample_device)

    window = EditorMainWindow(network, settings_manager, profile_repository=ProfileRepository([]))
    qtbot.addWidget(window)
    window.show()

    window.add_session(session)
    qtbot.waitUntil(lambda: window._object_view.model().rowCount() > 0, timeout=2000)

    assert window._object_view.model().rowCount() > 0
    assert window._property_view.current_entry() is not None
    page = window._tabs.currentWidget()
    assert isinstance(page, DeviceEditorPage)
    assert window._report_view.issues() == page.issues


@pytest.mark.usefixtures("qapp")
def test_command_palette_executes_toggle(settings_manager, sample_device):
    network = NetworkManager()
    network.register_device("demo", sample_device)

    toggled = {"called": False}

    def _toggle() -> None:
        toggled["called"] = True

    window = EditorMainWindow(
        network,
        settings_manager,
        profile_repository=ProfileRepository([]),
        toggle_theme=_toggle,
    )

    commands = window._default_commands()
    toggle = next(command for command in commands if "Toggle" in command.text)
    toggle.callback()
    assert toggled["called"] is True
    window.close()


@pytest.mark.usefixtures("qapp")
def test_new_device_action_asks_for_profile(monkeypatch, qtbot, settings_manager):
    network = NetworkManager()

    created = {"args": None}

    def fake_create(include_minimal_profile: bool = False):
        created["args"] = include_minimal_profile
        device = Device()
        return network.register_device("created", device)

    monkeypatch.setattr(network, "create_device", fake_create)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)
    monkeypatch.setattr(EditorMainWindow, "_offer_mandatory_object_fix", lambda *args, **kwargs: None)

    window = EditorMainWindow(network, settings_manager, profile_repository=ProfileRepository([]))
    qtbot.addWidget(window)

    window._new_device()

    assert created["args"] is False


@pytest.mark.usefixtures("qapp")
def test_incomplete_xdd_populates_tree(monkeypatch, qtbot, settings_manager):
    root = Path(__file__).resolve().parents[1]
    xdd_path = root / "data" / "samples" / "incomplete_device.xdd"

    network = NetworkManager()
    session = network.open_device(xdd_path)

    # Avoid blocking on the warning prompt during automated tests
    monkeypatch.setattr(EditorMainWindow, "_offer_mandatory_object_fix", lambda *args, **kwargs: None)

    window = EditorMainWindow(network, settings_manager, profile_repository=ProfileRepository([]))
    qtbot.addWidget(window)
    window.show()

    window.add_session(session)

    qtbot.waitUntil(lambda: window._object_view.model().rowCount() > 0, timeout=2000)

    rows = [window._object_view.model().item(row, 0).text() for row in range(window._object_view.model().rowCount())]
    assert "0x2000" in rows
