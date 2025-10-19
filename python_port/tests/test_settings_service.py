from canopen_node_editor.services import SettingsManager


def test_settings_round_trip(tmp_path):
    storage = tmp_path / "config"
    manager = SettingsManager(storage_dir=storage)
    prefs = manager.load()
    assert prefs.theme == "system"

    manager.update_preferences(theme="dark")
    manager.add_recent_file(tmp_path / "demo.eds")
    manager.save()

    # Reload to verify persistence
    reloaded = SettingsManager(storage_dir=storage).load()
    assert reloaded.theme == "dark"
    assert reloaded.recent_files[0].endswith("demo.eds")

    manager.remove_recent_files([tmp_path / "demo.eds"])
    manager.save()
    empty = SettingsManager(storage_dir=storage).load()
    assert empty.recent_files == []
