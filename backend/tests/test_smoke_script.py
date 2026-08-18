from pathlib import Path


def test_smoke_script_exists():
    root = Path(__file__).resolve().parents[2]
    assert (root / "scripts" / "smoke_test.py").exists()

