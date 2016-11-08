import logging
import os
import shutil
import subprocess

import yaml

import processjunit


class Run:

    def __init__(self, pythonDriverDirectory, scyllaInstallDirectory, tag, tests):
        self._tag = tag
        self._scyllaInstallDirectory = scyllaInstallDirectory
        os.chdir(pythonDriverDirectory)
        subprocess.check_call('git checkout .'.format(tag), shell=True)
        subprocess.check_call('git checkout {}'.format(tag), shell=True)
        self._setupOutputDirectory()
        self._applyPatch()
        exclude_str = ' '
        for ignore_element in self._ignoreSet():
            ignore_element = ignore_element.split('.')[-1]
            exclude_str += '--exclude %s ' % ignore_element
        testCommand = 'nosetests --with-xunit --xunit-file {} -s {} {}'.format(self._xunitFile(), tests, exclude_str)
        logging.info(testCommand)
        subprocess.call(testCommand.split(), env=self._environment())
        self._junit = processjunit.ProcessJUnit(self._xunitFile(), self._ignoreFile())
        content = open(self._xunitFile()).read()
        open(self._xunitFile(), 'w').write(content.replace('classname="', 'classname="version_{}_'.format(tag)))

    @property
    def summary(self):
        return self._junit.summary

    def __repr__(self):
        details = dict(version=self._tag)
        details.update(self._junit.summary)
        return '{version}: pass: {testcase}, failure: {failure}, skipped: {skipped}, ignored_in_analysis: {ignored_in_analysis}'.format(** details)

    def _setupOutputDirectory(self):
        self._xunitDirectory = os.path.join('xunit', self._tag)
        try:
            shutil.rmtree(self._xunitDirectory)
        except:
            pass
        os.makedirs(self._xunitDirectory)

    def _xunitFile(self):
        return os.path.join(self._xunitDirectory, 'nosetests.{}.xml'.format(self._tag))

    def _ignoreFile(self):
        here = os.path.dirname(__file__)
        ignoreFile = os.path.join(here, 'versions', self._tag, 'ignore.yaml')
        return ignoreFile

    def _ignoreSet(self):
        with open(self._ignoreFile()) as f:
            content = yaml.load(f)
            return set(content['tests'])

    def _environment(self):
        result = {}
        result.update(os.environ)
        result['PROTOCOL_VERSION'] = '3'
        result['INSTALL_DIRECTORY'] = self._scyllaInstallDirectory
        return result

    def _applyPatch(self):
        here = os.path.dirname(__file__)
        patchFile = os.path.join(here, 'versions', self._tag, 'patch')
        command = "patch -p1 -i {}".format(patchFile)
        subprocess.check_call(command, shell=True)
