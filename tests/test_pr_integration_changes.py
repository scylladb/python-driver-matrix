from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pr_integration_change_helper_is_not_carried_as_dead_code():
    assert not (REPO_ROOT / "scripts/pr_integration_changes.py").exists()


def test_ccm_cache_restore_and_save_use_the_same_path():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/integration-tests.yml").read_text())
    steps = workflow["jobs"]["integration-test"]["steps"]
    restore = next(step for step in steps if step.get("id") == "ccm-cache")
    save = next(step for step in steps if step.get("name") == "Save CCM download cache")

    assert restore["with"]["path"] == "~/.ccm/scylla-repository"
    assert save["with"]["path"] == restore["with"]["path"]


def test_python_package_cache_restore_and_save_use_the_same_paths():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/integration-tests.yml").read_text())
    steps = workflow["jobs"]["integration-test"]["steps"]
    restore = next(step for step in steps if step.get("id") == "python-package-cache")
    save = next(step for step in steps if step.get("name") == "Save Python package cache")

    assert restore["with"]["path"].split() == ["~/.pip-cache", "~/.uv-cache"]
    assert save["with"]["path"] == restore["with"]["path"]
    assert save["with"]["key"] == restore["with"]["key"]


def test_pr_detector_does_not_run_helper_from_pr_checkout():
    workflow_path = REPO_ROOT / ".github/workflows/pr-integration-tests.yml"
    workflow = yaml.safe_load(workflow_path.read_text())
    changes_steps = workflow["jobs"]["changes"]["steps"]

    assert "from scripts.pr_integration_changes import detect_changes" not in workflow_path.read_text()
    assert not any("actions/checkout" in step.get("uses", "") for step in changes_steps)
