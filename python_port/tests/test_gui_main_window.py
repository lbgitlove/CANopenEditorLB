from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

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
