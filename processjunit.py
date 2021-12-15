from functools import cached_property, lru_cache
from pathlib import Path
from typing import Dict, Union, Iterable
from xml.dom import minidom
from xml.etree import ElementTree


class ProcessJUnit:

    def __init__(self, xunit_file: Union[Path, str], ignore_set: Dict[str, Iterable[str]]):
        self._xunit_file = xunit_file
        self._ignore_set = {key: set(value) if value else set() for key, value in ignore_set.items()}
        self._summary = {"tests": 0, "errors": 0, "failures": 0, "skipped": 0, "xpassed": 0, "xfailed": 0,
                         "passed": 0, "ignored_in_analysis": 0, "flaky": 0}
        self._summary_full_details = {}

    @lru_cache(maxsize=None)
    def _analysis(self) -> None:
        """
        Analyze report results and modify the result according to the "ignore" tests names in the YAML file.
        Also, create a new XML file with the correct run results after the analysis and change the "casetest" so that
         the Jenkins can display all tests result (A job can run multiple python-driver runs).
        """
        tree = ElementTree.parse(self._xunit_file).find("testsuite[@name='pytest']")
        for element in tree.iter("testcase"):
            test_full_name = f"{element.attrib['classname']}.{element.attrib['name']}"
            is_ignore_test = test_full_name in self._ignore_set["ignore"]
            is_flaky_test = test_full_name in self._ignore_set["flaky"]
            if len(element):
                element_test_details = list(element.iter())[1]
                category_type = element_test_details.tag
                if category_type == "failure" and element_test_details.attrib["message"] == "Unexpected success":
                    # The test is passed, but it's marked as "xpassed" because the test contains the
                    # "@unittest.expectedFailure" mark and needs to remove it
                    category_type = "xpassed"
                    if is_ignore_test:
                        # The test passed, and it appears in the YAML file as a test that needs to skip - so need to
                        # remove it from the YAML file
                        category_type = "ignored_in_analysis"
                elif category_type == "skipped" and element_test_details.attrib["type"] == "pytest.xfail":
                    # The test is failed, but it's marked as "xfailed" because the test contains the
                    # "@unittest.expectedFailure" mark and needs to remove it and write the test name inside the YAML
                    # file
                    category_type = "xfailed"
                    if is_flaky_test:
                        category_type = "flaky"
                    elif is_ignore_test:
                        # The test is failed, and it appears in the YAML file as a test that needs to skip - so need to
                        # remove it from the YAML file
                        category_type = "ignored_in_analysis"
                elif is_ignore_test:
                    category_type = "ignored_in_analysis"
                elif is_flaky_test:
                    category_type = "flaky"
                elif category_type == "error" or category_type == "failure":
                    category_type += "s"
            else:
                category_type = "passed"
                if is_ignore_test and is_flaky_test:
                    # The test passed, and it appears in the YAML file as a test that needs to skip - so need to
                    # remove it from the YAML file
                    category_type = "xpassed"

            self._summary_full_details.setdefault(category_type, set()).add(test_full_name)
            self._summary[category_type] += 1
            self._summary["tests"] += 1

    @cached_property
    def summary(self) -> Dict[str, int]:
        self._analysis()
        return self._summary

    @cached_property
    def summary_full_details(self) -> Dict[str, int]:
        self._analysis()
        return self._summary_full_details

    @lru_cache(maxsize=None)
    def save_after_analysis(self, driver_version: str, protocol: int, python_driver_type: str) -> None:
        """
        Create a new XML file with the correct run results after filtering the names of the tests marked as "skip" in
        the YAML file.
        Also, change "casetest" so that the Jenkins can display all tests result (A job can run multiple python-driver
        runs).
        :param driver_version: The python-driver tag (Example: 3.25.0-scylla or 3.25.0)
        :param protocol: The cqlsh native protocol number
        :param python_driver_type: The driver type - can be "scylla" or "datastax"
        """
        tree = ElementTree.parse(self._xunit_file).find("testsuite[@name='pytest']")
        new_tree = ElementTree.Element("testsuites")
        _ = [tree.attrib.__setitem__(key, str(value)) for key, value in self.summary.items()]
        pytest_child = ElementTree.SubElement(new_tree, "testsuite", attrib=tree.attrib)
        new_test_prefix = f"{python_driver_type}_version_{driver_version}_v{protocol}_"

        for element in tree.iter("testcase"):
            test_full_name = f"{element.attrib['classname']}.{element.attrib['name']}"
            element.attrib["classname"] = f"{new_test_prefix}{element.attrib['classname']}"
            testcase_element = ElementTree.SubElement(pytest_child, "testcase", attrib=element.attrib)
            if test_full_name not in self.summary_full_details.get("passed", {}) and \
                    test_full_name not in self.summary_full_details.get("xpassed", {}):
                element_test_details = list(element.iter())[1]
                if test_full_name in self.summary_full_details.get("xpassed", {}):
                    message = "This test marked as 'xpassed' because it contains '@unittest.expectedFailure' mark -" \
                              " Please remove this mark from the test"
                    tag_name = "failure"
                elif test_full_name in self.summary_full_details.get("xfailed", {}):
                    message = "This test marked as 'xfailed' because it contains '@unittest.expectedFailure' mark -" \
                              " Please remove this mark from the test"
                    tag_name = "failure"
                elif test_full_name in self.summary_full_details.get("ignored_in_analysis", {}):
                    message = "This test marked as 'skipped' because it appears in the YAML file"
                    tag_name = "skipped"
                    element_test_details.attrib["type"] = "pytest.fail"
                elif test_full_name in self.summary_full_details.get("flaky", {}):
                    message = "This test marked as 'skipped' because it appears in the YAML file as 'flaky' test"
                    tag_name = "skipped"
                    element_test_details.attrib["type"] = "pytest.fail"
                else:
                    tag_name = element_test_details.tag
                    message = element_test_details.attrib["message"]

                element_test_details.attrib["message"] = message
                new_element_test_details = ElementTree.SubElement(
                    testcase_element, tag_name, attrib=element_test_details.attrib)
                new_element_test_details.text = element_test_details.text

        with self._xunit_file.open(mode="w", encoding="utf-8") as file:
            file.write(minidom.parseString(
                ElementTree.tostring(element=new_tree, encoding="utf-8")).toprettyxml(
                indent="  "))

    @cached_property
    def is_failed(self) -> bool:
        return not (self.summary["tests"] and self.summary["tests"] ==
                    self.summary["passed"] + self.summary["skipped"] + self.summary["ignored_in_analysis"] +
                    self.summary["flaky"])
