import os
import subprocess
from pathlib import Path

import pytest
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


@pytest.mark.parametrize(
    "available_cpus,expected_shards", [(1, 1), (2, 2), (4, 4), (8, 8), (16, 8)]
)
def test_integration_limits_exit_hang_shards_to_runner_cpus(
    tmp_path, available_cpus, expected_shards
):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/integration-tests.yml").read_text())
    step = next(
        step for step in workflow["jobs"]["integration-test"]["steps"]
        if step.get("name") == "Run integration tests"
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    nproc = fake_bin / "nproc"
    nproc.write_text(f"#!/bin/sh\nprintf '%s\\n' {available_cpus}\n")
    nproc.chmod(0o755)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    runner = scripts / "run_test.sh"
    runner.write_text(
        '#!/bin/sh\nprintf "%s\\n" "${EXIT_HANG_SMP-unset}" > "$SMP_RESULT"\n'
    )
    runner.chmod(0o755)
    result_path = tmp_path / "shards"
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "SMP_RESULT": str(result_path),
            "DRIVER_REF": "3.29.13-scylla",
            "DRIVER_TYPE": "scylla",
            "PYTHON_DRIVER_DIR": str(tmp_path / "driver"),
            "PROTOCOLS": "3,4",
            "SCYLLA_VERSION": "release:2025.1.16",
            "TESTS": "",
        }
    )
    env.pop("EXIT_HANG_SMP", None)

    subprocess.run(
        ["bash", "-c", step["run"]], cwd=tmp_path, env=env,
        check=True, timeout=10
    )

    assert result_path.read_text().strip() == str(expected_shards)
