from pathlib import Path

from canopen_node_editor.services import ProfileRepository

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_discovery_from_directory(tmp_path):
    repo_dir = tmp_path / "profiles"
    repo_dir.mkdir()
    for sample in SAMPLES.glob("demo_device.*"):
        if sample.suffix.lower() in {".eds", ".xdd"}:
            target = repo_dir / sample.name
            target.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")

    repository = ProfileRepository([repo_dir])
    profiles = repository.discover()
    assert {meta.path.name for meta in profiles} == {"demo_device.eds", "demo_device.xdd"}
    product_names = {meta.name for meta in profiles}
    assert "Demo Device" in product_names
