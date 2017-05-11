import logging
import argparse
import run

logging.basicConfig(level=logging.INFO)


def main(python_driver_git, scylla_install_dir, tests, versions):
    results = []
    for version in versions:
        results.append(run.Run(python_driver_git, scylla_install_dir, version, tests))

    print('=== PYTHON DRIVER MATRIX RESULTS ===')
    status = 0
    for result in results:
        print(result)
        if result.summary['failure'] > 0:
            status = 1
    quit(status)

if __name__ == '__main__':
    versions = ['3.0.0', '3.2.0', '3.4.0', '3.5.0', '3.8.0']
    parser = argparse.ArgumentParser()
    parser.add_argument('python_driver_git', help='folder with git repository of python-driver')
    parser.add_argument('scylla_install_dir',
                        help='folder with scylla installation, e.g. a checked out git scylla has been built')
    parser.add_argument('--versions', default=versions,
                        help='python-driver versions to test, default={}'.format(','.join(versions)))
    parser.add_argument('--tests', default='tests.integration.standard',
                        help='tests to pass to nosetests tool, default=tests.integration.standard')
    arguments = parser.parse_args()
    if not isinstance(arguments.versions, list):
        versions = arguments.versions.split(',')
    main(arguments.python_driver_git, arguments.scylla_install_dir, arguments.tests, versions)
