from __future__ import annotations

from canopen_node_editor.app import resolve_paths


def test_resolve_paths_uses_project_root(tmp_path):
    custom_root = tmp_path / "project"
    custom_root.mkdir()

    paths = resolve_paths(custom_root)

    assert paths.root_dir == custom_root
    assert paths.config_dir == custom_root / "config"
    assert paths.data_dir == custom_root / "data"
