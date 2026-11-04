from pathlib import Path


def test_gitignore_covers_local_secret_files():
    text = Path(".gitignore").read_text(encoding="utf-8")
    assert "config.json" in text
    assert "inventory.json" in text


def test_workflow_installs_and_runs_tests_only():
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "push:" in text
    assert "pull_request:" in text
    assert "pip install -r requirements.txt" in text
    assert "pytest" in text
    assert "deploy" not in lowered
    assert "upload-artifact" not in lowered
    assert "secrets." not in lowered
