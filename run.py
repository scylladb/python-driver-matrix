import logging
import os
import re
import shutil
import subprocess
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Dict, List

import yaml
from packaging.version import Version, InvalidVersion

from processjunit import ProcessJUnit


class Run:
    def __init__(self, python_driver_git, python_driver_type, scylla_install_dir, tag, protocol, tests, scylla_version,
                 collect_only):
        self.driver_version = tag.split("-", maxsplit=1)[0]
        self._full_driver_version = tag
        self._python_driver_git = Path(python_driver_git)
        self._python_driver_type = python_driver_type
        self._scylla_version = scylla_version
        self._scylla_install_dir = scylla_install_dir
        self._tests = tests.replace(".", "/").replace("/py", ".py")
        self._protocol = int(protocol)
        self._venv_path = self._python_driver_git / "venv" / self._python_driver_type / self.driver_version
        self._collect_only = collect_only

    @cached_property
    def version_folder(self) -> Path:
        version_pattern = re.compile(r"(\d+.)+\d+$")
        target_version_folder = Path(os.path.dirname(__file__)) / "versions" / self._python_driver_type
        try:
            target_version = Version(self.driver_version)
        except InvalidVersion:
            target_dir = target_version_folder / self.driver_version
            if target_dir.is_dir():
                return target_dir
            return target_version_folder / "master"

        tags_defined = sorted(
            (
                Version(folder_path.name)
                for folder_path in target_version_folder.iterdir() if version_pattern.match(folder_path.name)
            ),
            reverse=True
        )
        for tag in tags_defined:
            if tag <= target_version:
                return target_version_folder / str(tag)
        else:
            raise ValueError("Not found directory for python-driver version '%s'", self.driver_version)

    @cached_property
    def xunit_file(self) -> Path:
        xunit_dir = Path(os.path.dirname(__file__)) / "xunit" / self.driver_version
        if not xunit_dir.exists():
            xunit_dir.mkdir(parents=True)

        file_path = xunit_dir / f'pytest.{self._python_driver_type}.v{self._protocol}.{self.driver_version}.xml'
        if file_path.exists():
            file_path.unlink()
        return file_path

    @cached_property
    def ignore_tests(self) -> Dict[str, List[str]]:
        ignore_file = self.version_folder / "ignore.yaml"
        if not ignore_file.exists():
            logging.info("Cannot find ignore file for version '%s'", self.driver_version)
            return {}

        with ignore_file.open(mode="r", encoding="utf-8") as file:
            content = yaml.safe_load(file)
        ignore_tests = content.get("tests" if self._protocol == 3 else f"v{self._protocol}_tests", []) or {}
        if not ignore_tests.get("ignore", None):
            logging.info("The file '%s' for version tag '%s' doesn't contains any test to ignore for protocol"
                         " '%d'", ignore_file, self.driver_version, self._protocol)
        return ignore_tests

    @cached_property
    def environment(self) -> Dict:
        result = {}
        result.update(os.environ)
        result["PROTOCOL_VERSION"] = str(self._protocol)
        if self._scylla_version:
            result["SCYLLA_VERSION"] = self._scylla_version
        else:
            result["INSTALL_DIRECTORY"] = self._scylla_install_dir
        return result

    def _run_command_in_shell(self, cmd: str):
        logging.debug("Execute the cmd '%s'", cmd)
        with subprocess.Popen(cmd, shell=True, executable="/bin/bash", env=self.environment,
                              cwd=self._python_driver_git, stderr=subprocess.PIPE) as proc:
            stderr = proc.communicate()
            status_code = proc.returncode
        assert status_code == 0, stderr

    def _apply_patch_files(self) -> bool:
        for file_path in self.version_folder.iterdir():
            if file_path.name.startswith("patch"):
                try:
                    logging.info("Show patch's statistics for file '%s'", file_path)
                    self._run_command_in_shell(f"git apply --stat {file_path}")
                    logging.info("Detect patch's errors for file '%s'", file_path)
                    self._run_command_in_shell(f"git apply --check {file_path}")
                    logging.info("Applying patch file '%s'", file_path)
                    self._run_command_in_shell(f"patch -p1 -i {file_path}")
                except Exception as exc:
                    logging.error("Failed to apply patch '%s' to version '%s', with: '%s'",
                                  file_path, self.driver_version, str(exc))
                    return False
        return True

    @lru_cache(maxsize=None)
    def _create_venv(self):
        basic_packages = ("pytest",
                          "https://github.com/scylladb/scylla-ccm/archive/master.zip",
                          "pytest-subtests")
        if self._venv_path.exists() and self._venv_path.is_dir():
            logging.info("Removing old python venv in directory '%s'", self._venv_path)
            shutil.rmtree(self._venv_path)

        logging.info("Creating a new python venv in directory '%s'", self._venv_path)
        self._venv_path.mkdir(parents=True)
        self._run_command_in_shell(cmd=f"python3 -m venv {self._venv_path}")
        logging.info("Upgrading 'pip' and 'setuptools' packages to the latest version")
        self._run_command_in_shell(cmd=f"{self._activate_venv_cmd()} && pip install --upgrade pip setuptools")
        logging.info("Installing the following packages:\n%s", "\n".join(basic_packages))
        self._run_command_in_shell(cmd=f"{self._activate_venv_cmd()} && pip install {' '.join(basic_packages)}")

    @lru_cache(maxsize=None)
    def _activate_venv_cmd(self):
        return f"source {self._venv_path}/bin/activate"

    @lru_cache(maxsize=None)
    def _install_python_requirements(self):
        if os.environ.get("DEV_MODE", False) and self._venv_path.exists() and self._venv_path.is_dir():
            return True
        try:
            self._create_venv()
            for requirement_file in ["requirements.txt", "test-requirements.txt"]:
                if os.path.exists(requirement_file):
                    self._run_command_in_shell(f"{self._activate_venv_cmd()} && "
                                               f"pip install --force-reinstall -r {requirement_file}")
            return True
        except Exception as exc:
            logging.error("Failed to install python requirements for version %s, with: %s",
                          self.driver_version, str(exc))
            return False

    def _checkout_branch(self):
        try:
            self._run_command_in_shell("git checkout .")
            logging.info("git checkout to '%s' tag branch", self._full_driver_version)
            self._run_command_in_shell(f"git checkout {self._full_driver_version}")
            return True
        except Exception as exc:
            logging.error("Failed to branch for version '%s', with: '%s'", self.driver_version, str(exc))
            return False

    def run(self) -> ProcessJUnit:
        junit = ProcessJUnit(self.xunit_file, self.ignore_tests)
        logging.info("Changing the current working directory to the '%s' path", self._python_driver_git)
        os.chdir(self._python_driver_git)
        if self._checkout_branch() and self._apply_patch_files() and self._install_python_requirements():
            pytest_cmd = f"pytest -v -rxXs --junitxml={self.xunit_file} -o junit_family=xunit2 -s {self._tests}"
            if self._collect_only:
                pytest_cmd += " --collect-only"
            subprocess.call(f"{self._activate_venv_cmd()} && {pytest_cmd} -qq", shell=True, executable="/bin/bash",
                            env=self.environment, cwd=self._python_driver_git)
            junit.save_after_analysis(driver_version=self.driver_version, protocol=self._protocol,
                                      python_driver_type=self._python_driver_type)
        return junit
