import os
import subprocess
from pathlib import Path

import pytest

from processjunit import ProcessJUnit

TEST_FILE_PATH = Path(os.getcwd()) / "test_temp.py"
TEST_FILE_NAME = TEST_FILE_PATH.stem
XML_FILE_PATH = Path(os.getcwd()) / "temp_report.xml"
TESTS_DATA = """
import unittest


class TestSetupFailed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raise RuntimeError

    # In XML file this test is mark as "error"
    def test_error_in_setup(self):
        pass


class TestWithMark(unittest.TestCase):
    # In XML file this test is mark as "failure" with "Unexpected success" message (xpassed)
    @unittest.expectedFailure
    def test_pass_but_marked_as_expected_failure(self):
        pass

    @unittest.expectedFailure
    def test_pass_but_marked_as_ignore_in_yaml_file(self):
        pass

    # In XML file this test is mark as "failure" with type="pytest.xfail" 
    @unittest.expectedFailure
    def test_fail_but_marked_as_expected_failure(self):
        raise KeyError

    
    def test_fail(self):
        raise KeyError

    def test_fail_as_ignore_in_yaml_file(self):
        raise KeyError

    @unittest.expectedFailure
    def test_fail_but_marked_as_ignore_in_yaml_file(self):
        raise KeyError

    # In XML file this test is mark as "skip" with 
    @unittest.skip
    def test_skip(self):
        pass

    def test_pass(self):
        pass

    def test_flaky_pass(self):
        pass

    def test_flaky_failed(self):
        raise KeyError
"""
IGNORE_SET = {
    "ignore": {
        f"{TEST_FILE_NAME}.TestWithMark.test_pass_but_marked_as_ignore_in_yaml_file",
        f"{TEST_FILE_NAME}.TestWithMark.test_fail_but_marked_as_ignore_in_yaml_file",
        f"{TEST_FILE_NAME}.TestWithMark.test_fail_as_ignore_in_yaml_file",
    },
    "flaky": {
        f"{TEST_FILE_NAME}.TestWithMark.test_flaky_pass",
        f"{TEST_FILE_NAME}.TestWithMark.test_flaky_failed",
    }
}


class TestReportMechanism:
    @pytest.fixture(scope="class")
    def report(self):
        with TEST_FILE_PATH.open(mode="w", encoding="utf-8") as file:
            file.write(TESTS_DATA)
        subprocess.call(f"pytest -v -rxXs --junitxml={XML_FILE_PATH} -o junit_family=xunit2 -s {TEST_FILE_PATH}",
                        shell=True, executable="/bin/bash", env=os.environ)
        report = ProcessJUnit(xunit_file=XML_FILE_PATH, ignore_set=IGNORE_SET)
        yield report
        XML_FILE_PATH.unlink()
        TEST_FILE_PATH.unlink()

    def test_errors(self, report):
        assert report.summary_full_details["errors"] == {f"{TEST_FILE_NAME}.TestSetupFailed.test_error_in_setup"}

    def test_failures(self, report):
        assert report.summary_full_details["errors"] == {f"{TEST_FILE_NAME}.TestSetupFailed.test_error_in_setup"}

    def test_ignored_in_analysis(self, report):
        expected_tests_names = {
            f"{TEST_FILE_NAME}.TestWithMark.test_fail_as_ignore_in_yaml_file",
            f"{TEST_FILE_NAME}.TestWithMark.test_fail_but_marked_as_ignore_in_yaml_file",
            f"{TEST_FILE_NAME}.TestWithMark.test_pass_but_marked_as_ignore_in_yaml_file"}
        assert report.summary_full_details["ignored_in_analysis"] == expected_tests_names

    def test_xfailed(self, report):
        assert report.summary_full_details["xfailed"] == {
            f"{TEST_FILE_NAME}.TestWithMark.test_fail_but_marked_as_expected_failure"}

    def test_passed(self, report):
        assert report.summary_full_details["passed"] == {f"{TEST_FILE_NAME}.TestWithMark.test_pass"}

    def test_xpassed(self, report):
        pass_flaky_test_name = f"{TEST_FILE_NAME}.TestWithMark.test_flaky_pass"
        assert pass_flaky_test_name in IGNORE_SET["flaky"]
        assert report.summary_full_details["xpassed"] == {
            pass_flaky_test_name,
            f"{TEST_FILE_NAME}.TestWithMark.test_pass_but_marked_as_expected_failure"}

    def test_skipped(self, report):
        assert report.summary_full_details["skipped"] == {f"{TEST_FILE_NAME}.TestWithMark.test_skip"}

    def test_flaky(self, report):
        pass_flaky_test_name = f"{TEST_FILE_NAME}.TestWithMark.test_flaky_failed"
        assert pass_flaky_test_name in IGNORE_SET["flaky"]
        assert report.summary_full_details["flaky"] == {pass_flaky_test_name}

    def test_save_new_report_after_analysis(self, report):
        report.save_after_analysis(driver_version="3.25.0", protocol=3, python_driver_type="scylla")

    def test_is_report_failed(self, report):
        assert report.is_failed
