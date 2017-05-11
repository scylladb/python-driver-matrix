import logging
import os
import shutil
import subprocess
import yaml
import processjunit


class Run:

    def __init__(self, python_driver_git, scylla_install_dir, tag, tests):
        self._tag = tag
        self._python_driver_git = python_driver_git
        self._scylla_install_dir = scylla_install_dir
        self._tests = tests
        self._xunit_file = self._get_xunit_file(self._setup_out_dir())
        self._run()
        self._junit = self._process_output()

    @property
    def summary(self):
        return self._junit.summary

    def __repr__(self):
        details = dict(version=self._tag)
        details.update(self._junit.summary)
        return '{version}: testcases: {testcase}, failures: {failure}, errors: {error}, skipped: {skipped},' \
               ' ignored_in_analysis: {ignored_in_analysis}'.format(**details)

    def _setup_out_dir(self):
        here = os.path.dirname(__file__)
        xunit_dir = os.path.join(here, 'xunit', self._tag)
        if os.path.exists(xunit_dir):
            shutil.rmtree(xunit_dir)
        os.makedirs(xunit_dir)
        return xunit_dir

    def _get_xunit_file(self, xunit_dir):
        return os.path.join(xunit_dir, 'nosetests.{}.xml'.format(self._tag))

    def _ignoreFile(self):
        here = os.path.dirname(__file__)
        return os.path.join(here, 'versions', self._tag, 'ignore.yaml')

    def _ignoreSet(self):
        with open(self._ignoreFile()) as f:
            content = yaml.load(f)
            return set(content['tests'])

    def _environment(self):
        result = {}
        result.update(os.environ)
        result['PROTOCOL_VERSION'] = '3'
        result['INSTALL_DIRECTORY'] = self._scylla_install_dir
        return result

    def _apply_patch(self):
        here = os.path.dirname(__file__)
        patch_file = os.path.join(here, 'versions', self._tag, 'patch')
        if not os.path.exists(patch_file):
            raise Exception('Cannot find patch for version {}'.format(self._tag))
        command = "patch -p1 -i {}".format(patch_file)
        subprocess.check_call(command, shell=True)

    def _run(self):
        os.chdir(self._python_driver_git)
        subprocess.check_call('git checkout .'.format(self._tag), shell=True)
        subprocess.check_call('git checkout {}'.format(self._tag), shell=True)
        self._apply_patch()
        exclude_str = ' '
        for ignore_element in self._ignoreSet():
            ignore_element = ignore_element.split('.')[-1]
            exclude_str += '--exclude %s ' % ignore_element
        cmd = 'nosetests --with-xunit --xunit-file {} -s {} {}'.format(self._xunit_file, self._tests, exclude_str)
        logging.info(cmd)
        subprocess.call(cmd.split(), env=self._environment())

    def _process_output(self):
        junit = processjunit.ProcessJUnit(self._xunit_file, self._ignoreFile())
        content = open(self._xunit_file).read()
        open(self._xunit_file, 'w').write(content.replace('classname="', 'classname="version_{}_'.format(self._tag)))
        return junit
