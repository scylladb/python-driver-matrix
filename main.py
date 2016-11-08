import logging
logging.basicConfig(level=logging.INFO)
import argparse

import run


def main(pythonDriverGit, scyllaInstallDirectory, tests):
    versions = '3.0.0', '3.2.0', '3.4.0', '3.5.0'
    results = []
    for version in versions:
        results.append(run.Run(pythonDriverGit, scyllaInstallDirectory, version, tests))

    print('=== PYTHON DRIVER MATRIX RESULTS ===')
    failed = False
    for result in results:
        print(result)
        if result.summary['failure'] > 0:
            failed = True

    if failed:
        quit(1)
    else:
        quit(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pythonDriverGit', help='folder with git repository of python-driver')
    parser.add_argument('scyllaInstallDirectory', help='folder with scylla installation, e.g. a checked out git scylla has been built')
    parser.add_argument('--tests', default='tests.integration.standard', help='tests to pass to nosetests tool, default=tests.integration.standard')
    arguments = parser.parse_args()
    main(arguments.pythonDriverGit, arguments.scyllaInstallDirectory, arguments.tests)
