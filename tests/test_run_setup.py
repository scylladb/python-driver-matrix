import argparse
import json
import shlex
from pathlib import Path
from unittest.mock import Mock

import pytest

from run import Run


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.delenv("CCM_DIR", raising=False)
    result = Run(tmp_path, "apache", "", "3.29.3", 4,
                 "tests.integration.standard", "2026.1.15", False)
    result.__dict__["xunit_dir"] = tmp_path
    return result


@pytest.mark.parametrize("driver_type", ["apache", "scylla"])
def test_bootstrap_uses_configured_ccm_checkout(runner, tmp_path, monkeypatch, driver_type):
    ccm_dir = tmp_path / "CCM checkout; echo unwanted"
    ccm_dir.mkdir()
    monkeypatch.setenv("CCM_DIR", str(ccm_dir))
    runner._python_driver_type = driver_type
    runner._run_command_in_shell = Mock()

    runner._create_venv()

    install = shlex.split(runner._run_command_in_shell.call_args.kwargs["cmd"])
    assert install[install.index("install") + 1:] == [
        "pytest==7.4.4", str(ccm_dir), "pytest-subtests",
    ]
    assert ("uv" in install) == (driver_type == "scylla")


@pytest.mark.parametrize("ccm_dir", [None, ""])
def test_bootstrap_keeps_archive_fallback_without_ccm_dir(runner, monkeypatch, ccm_dir):
    if ccm_dir is not None:
        monkeypatch.setenv("CCM_DIR", ccm_dir)
    runner._run_command_in_shell = Mock()

    runner._create_venv()

    install = shlex.split(runner._run_command_in_shell.call_args.kwargs["cmd"])
    assert "https://github.com/scylladb/scylla-ccm/archive/master.zip" in install


def test_missing_configured_ccm_checkout_fails_before_install(runner, tmp_path, monkeypatch):
    monkeypatch.setenv("CCM_DIR", str(tmp_path / "missing-ccm"))
    runner._run_command_in_shell = Mock()

    with pytest.raises(FileNotFoundError, match="CCM_DIR"):
        runner._create_venv()

    runner._run_command_in_shell.assert_not_called()


def test_install_failure_is_reported_with_original_cause(runner, monkeypatch):
    import main

    monkeypatch.setattr(main, "Run", Mock(return_value=runner))
    monkeypatch.setattr("run.os.chdir", Mock())
    monkeypatch.setattr(runner, "_checkout_branch", Mock(return_value=True))
    monkeypatch.setattr(runner, "_apply_patch_files", Mock(return_value=True))
    monkeypatch.setattr(runner, "_run_command_in_shell", Mock(side_effect=[
        None, AssertionError("HTTP error 504 while getting scylla-ccm/archive/master.zip"),
    ]))
    execute_tests = Mock()
    monkeypatch.setattr("run.subprocess.call", execute_tests)
    arguments = argparse.Namespace(
        versions=["3.29.3"], protocols=[4], python_driver_git=str(runner._python_driver_git),
        driver_type="apache", scylla_install_dir="", tests="tests.integration.standard",
        scylla_version="2026.1.15", collect_only=False, recipients=None,
    )

    with pytest.raises(SystemExit) as exit_info:
        main.main(arguments)

    assert exit_info.value.code == 1
    execute_tests.assert_not_called()
    metadata = json.loads((runner.xunit_dir / runner.metadata_file_name).read_text())
    assert "HTTP error 504" in metadata["failure_reason"]
    assert "FileNotFoundError" not in metadata["failure_reason"]
    assert not runner.xunit_file.exists()


@pytest.mark.parametrize("driver_type", ["apache", "scylla"])
def test_relative_ccm_checkout_survives_matrix_directory_changes(runner, tmp_path, monkeypatch, driver_type):
    import main

    invocation_dir = tmp_path / "invocation"
    ccm_dir = invocation_dir / "CCM checkout; echo unwanted"
    ccm_dir.mkdir(parents=True)
    monkeypatch.chdir(invocation_dir)
    monkeypatch.setenv("CCM_DIR", ccm_dir.name)
    monkeypatch.setattr(Run, "xunit_dir", tmp_path / "reports")
    monkeypatch.setattr(Run, "_checkout_branch", Mock(return_value=True))
    monkeypatch.setattr(Run, "_apply_patch_files", Mock(return_value=True))
    monkeypatch.setattr("run.shutil.which", Mock(return_value="uv"))
    monkeypatch.setattr("run.ProcessJUnit", Mock(return_value=Mock(summary={"tests": 1}, is_failed=False)))
    install_commands = Mock()
    monkeypatch.setattr(Run, "_run_command_in_shell", install_commands)
    execute_tests = Mock()
    monkeypatch.setattr("run.subprocess.call", execute_tests)
    arguments = argparse.Namespace(
        versions=["3.29.3", "3.29.2"], protocols=[3, 4], python_driver_git=str(runner._python_driver_git),
        driver_type=driver_type, scylla_install_dir="", tests="tests.integration.standard",
        scylla_version="2026.1.15", collect_only=False, recipients=None,
    )

    with pytest.raises(SystemExit) as exit_info:
        main.main(arguments)

    assert exit_info.value.code == 0
    assert Path.cwd() == runner._python_driver_git
    assert execute_tests.call_count == 4
    bootstrap_installs = [
        shlex.split(call.kwargs["cmd"])
        for call in install_commands.call_args_list
        if "pytest==7.4.4" in call.kwargs.get("cmd", "")
    ]
    assert len(bootstrap_installs) == 4
    for install in bootstrap_installs:
        assert install[install.index("install") + 1:] == [
            "pytest==7.4.4", str(ccm_dir), "pytest-subtests",
        ]
