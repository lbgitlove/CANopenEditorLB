from __future__ import annotations

from canopen_node_editor import __version__
from canopen_node_editor.app import main


def test_main_prints_version(capsys):
    exit_code = main(["--version"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == __version__


def test_main_check_mode_reports_environment(capsys):
    exit_code = main(["--check"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("CANopenNode Editor environment OK")
