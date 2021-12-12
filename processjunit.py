import logging
import os
import xml.etree.ElementTree
import yaml


class ProcessJUnit:

    def __init__(self, xunitFile, ignoreSet):
        tree = xml.etree.ElementTree.parse(xunitFile)
        self._ignore = ignoreSet
        logging.info('ignoring {}'.format(self._ignore))
        self._summary = {'testcase': 0, 'failure': 0, 'error': 0, 'skipped': 0, 'ignored_in_analysis': 0}
        for element in tree.iter():
            if self._shouldIgnore(element):
                self._summary['ignored_in_analysis'] += 1
                continue
            if element.tag in self._summary:
                self._summary[element.tag] += 1

    def _shouldIgnore(self, element):
        if element.get('classname') in self._ignore:
            return True
        fullName = '{}.{}'.format(element.get('classname'), element.get('name'))
        return fullName in self._ignore

    @property
    def summary(self):
        return self._summary
