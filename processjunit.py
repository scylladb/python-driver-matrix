import logging
import os
import xml.etree.ElementTree

import yaml


class ProcessJUnit:

    def __init__(self, xunitFile, ignoreFile):
        tree = xml.etree.ElementTree.parse(xunitFile)
        self._ignore = self._ignoreSet(ignoreFile)
        logging.info('ignoring {}'.format(self._ignore))
        self._summary = {'testcase': 0, 'failure': 0, 'skipped': 0, 'ignored_in_analysis': 0}
        for element in tree.getiterator():
            if self._shouldIgnore(element):
                self._summary['ignored_in_analysis'] += 1
                continue
            if element.tag in self._summary:
                self._summary[element.tag] += 1

    def _ignoreSet(self, file):
        logging.info('looking for ignore.yaml file {}'.format(file))
        if not os.path.exists(file):
            return set()
        with open(file) as f:
            content = yaml.load(f)
            return set(content['tests'])

    def _shouldIgnore(self, element):
        fullName = '{}.{}'.format(element.get('classname'), element.get('name'))
        return fullName in self._ignore

    @property
    def summary(self):
        return self._summary
