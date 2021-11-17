import logging
import os
import re
import shutil
import subprocess
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Set

import yaml
import processjunit
import tempfile
from packaging.version import Version, InvalidVersion


class Run:

    def __init__(self, python_driver_git, python_driver_type, scylla_install_dir, tag, protocol, tests,
                 scylla_version=None):
        self.tag = tag.split("-", maxsplit=1)[0]
        self._full_tag_name = tag
        self._python_driver_git = Path(python_driver_git)
        self._python_driver_type = python_driver_type
        self._scylla_version = scylla_version
        self._scylla_install_dir = scylla_install_dir
        self._tests = tests
        self._protocol = int(protocol)
        self._venv_path = self._python_driver_git / 'venv' / self._python_driver_type / self.tag
        self._version_folder = None
        self._xunit_file = self._get_xunit_file(self._setup_out_dir())
        self._run()

    @cached_property
    def summary(self):
        return self._junit.summary

    def __repr__(self):
        details = dict(version=self.tag, protocol=self._protocol, type=str(self._python_driver_type))
        details.update(self._junit.summary)
        return '({type}){version}: v{protocol}: testcases: {testcase},' \
               ' failures: {failure}, errors: {error}, skipped: {skipped},' \
               ' ignored_in_analysis: {ignored_in_analysis}'.format(**details)

    @cached_property
    def version_folder(self) -> str:
        if self._version_folder is None:
            self._version_folder = self.__version_folder(self._python_driver_type, self.tag)
        logging.info("Taking patch and ignore files from directory '{}'".format(self._version_folder))
        return self._version_folder

    @staticmethod
    def __version_folder(python_driver_type, target_tag):
        version_pattern = re.compile(r"(\d+.)+\d+$")
        target_version_folder = os.path.join(os.path.dirname(__file__), 'versions', python_driver_type)
        try:
            target_version = Version(target_tag)
        except InvalidVersion:
            target_dir = os.path.join(target_version_folder, target_tag)
            if os.path.exists(target_dir):
                return target_dir
            return os.path.join(target_version_folder, 'master')

        tags_defined = sorted(
            (Version(tag) for tag in os.listdir(target_version_folder) if version_pattern.match(tag)),
            reverse=True
        )
        for tag in tags_defined:
            if tag <= target_version:
                return os.path.join(target_version_folder, str(tag))
        return None

    def _setup_out_dir(self):
        here = os.path.dirname(__file__)
        xunit_dir = os.path.join(here, 'xunit', self.tag)
        if not os.path.exists(xunit_dir):
            os.makedirs(xunit_dir)
        return xunit_dir

    def _get_xunit_file(self, xunit_dir):
        file_path = os.path.join(xunit_dir, f'nosetests.{self._python_driver_type}.v{self._protocol}.{self.tag}.xml')
        if os.path.exists(file_path):
            os.unlink(file_path)
        return file_path

    @cached_property
    def ignore_file(self):
        return os.path.join(self.version_folder, 'ignore.yaml')

    def _ignore_tests(self) -> Set[str]:
        if not os.path.exists(self.ignore_file):
            logging.info('Cannot find ignore file for version {}'.format(self.tag))
            return set()

        with open(self.ignore_file) as file:
            content = yaml.safe_load(file)
        ignore_tests = set(content.get("general", []) or [])
        ignore_tests.update(content.get(self._protocol, []) or [])
        if not ignore_tests:
            logging.info("The 'ignore.yaml' for version tag '%s' doesn't contains any test to ignore for protocol"
                         " '%d'" % (self.tag, self._protocol))
        return ignore_tests

    @cached_property
    def environment(self):
        result = {}
        result.update(os.environ)
        result['PROTOCOL_VERSION'] = str(self._protocol)
        if self._scylla_version:
            result['SCYLLA_VERSION'] = self._scylla_version
        else:
            result['INSTALL_DIRECTORY'] = self._scylla_install_dir
        return result

    def _apply_patch_files(self) -> bool:
        for file_name in os.listdir(self.version_folder):
            if file_name == "patch" or file_name.endswith(".patch"):
                file_path = os.path.join(self.version_folder, file_name)
                try:
                    logging.info("Applying patch for the file '%s'" % file_path)
                    self._run_command_in_shell(f"patch -p1 -i {file_path}")
                except Exception as exc:
                    logging.error("Failed to apply patch '{}' to version '{}', with: '{}'".format(
                        file_path, self.tag, str(exc)))
                    return False
        return True

    def _run_command_in_shell(self, cmd: str):
        logging.debug("Execute the cmd '%s'" % cmd)
        status_code = subprocess.call(cmd, shell=True, executable="/bin/bash", env=self.environment,
                                      cwd=self._python_driver_git)
        assert status_code == 0

    @lru_cache(maxsize=None)
    def _create_venv(self):
        imported_packages = ("pytest",
                             "https://github.com/scylladb/scylla-ccm/archive/master.zip",
                             "pytest-subtests")
        if self._venv_path.exists() and self._venv_path.is_dir():
            logging.info("Removing old python venv in directory '%s'", self._venv_path)
            shutil.rmtree(self._venv_path)

        logging.info("Creating a new python venv in directory '%s'", self._venv_path)
        self._venv_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_command_in_shell(cmd=f"python3 -m venv {self._venv_path}")
        logging.info("Upgrading 'pip' and 'setuptools' packages to the latest version")
        self._run_command_in_shell(cmd=f"{self._activate_venv_cmd()} && pip install --upgrade pip setuptools")
        logging.info("Installing the following packages:\n%s" % "\n".join(imported_packages))
        self._run_command_in_shell(cmd=f"{self._activate_venv_cmd()} && pip install {' '.join(imported_packages)}")

    @lru_cache(maxsize=None)
    def _activate_venv_cmd(self):
        return f"source {self._venv_path}/bin/activate"

    @lru_cache(maxsize=None)
    def _install_python_requirements(self):
        try:
            self._create_venv()
            for requirement_file in ['requirements.txt', 'test-requirements.txt']:
                if os.path.exists(requirement_file):
                    self._run_command_in_shell(f"{self._activate_venv_cmd()} && pip install --force-reinstall "
                                               f"-r {requirement_file}")
            return True
        except Exception as exc:
            logging.error("Failed to install python requirements for version {}, with: {}".format(self.tag, str(exc)))
            return False

    def _checkout_branch(self):
        try:
            self._run_command_in_shell('git checkout .')
            logging.info("git checkout to '%s' tag branch" % self._full_tag_name)
            self._run_command_in_shell(f'git checkout {self._full_tag_name}')
            return True
        except Exception as exc:
            logging.error("Failed to branch for version {}, with: {}".format(self.tag, str(exc)))
            return False

    def _run(self):
        logging.info("Changing the current working directory to the '%s' path" % self._python_driver_git)
        os.chdir(self._python_driver_git)
        if not (self._checkout_branch() and self._apply_patch_files() and self._install_python_requirements()):
            self._publish_fake_result()
            return

        deselect_tests_str = ""
        if test_excludes := self._ignore_tests():
            logging.info("The following tests will skips:\n%s", "\n".join(test_excludes))
            deselect_tests_str = "--deselect" + "--deselect".join(test_excludes)

        pytest_cmd = f"pytest -v --junitxml={self._xunit_file} -s {self._tests} {deselect_tests_str}"
        subprocess.call(f"{self._activate_venv_cmd()} && {pytest_cmd}", shell=True, executable="/bin/bash",
                        env=self.environment, cwd=self._python_driver_git)
        self._junit = self._process_output()

    def _process_output(self):
        junit = processjunit.ProcessJUnit(self._xunit_file, self._ignore_tests())
        content = open(self._xunit_file).read()
        open(self._xunit_file, 'w').write(content.replace('classname="', 'classname="version_{}_v{}_'.format(
            self.tag, self._protocol)))
        return junit

    def _publish_fake_result(self):
        logging.error("The run failed and the report is empty because the tests have not started to run")
        self._junit = FakeJunitResults(0, 0, 0, 0)


class FakeJunitResults:
    def __init__(self, testcase, failure, error, skipped):
        self.summary = {
            'testcase': testcase,
            'failure': failure,
            'error': error,
            'skipped': skipped,
            'ignored_in_analysis': 0
        }
