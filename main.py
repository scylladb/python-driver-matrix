import os
import logging
import argparse
import subprocess
from typing import List

import run

logging.basicConfig(level=logging.INFO)


def main(python_driver_git, scylla_install_dir, driver_type, tests, versions, protocols, scylla_version):
    results = []
    for version in versions:
        for protocol in protocols:
            logging.info('=== PYTHON DRIVER VERSION {}, PROTOCOL v{} ==='.format(version, protocol))
            results.append(run.Run(python_driver_git, driver_type, scylla_install_dir, version, protocol, tests,
                                   scylla_version=scylla_version))

    logging.info('=== PYTHON DRIVER MATRIX RESULTS ===')
    status = 0
    for result in results:
        logging.info(result)
        if not result.summary['testcase'] or result.summary['failure'] > 0 or result.summary['error']:
            logging.info("The 'python-driver-matrix' run failed because there are failures and/or errors")
            status = 1
    quit(status)


def extract_n_latest_repo_tags(repo_directory: str, latest_tags_size: int = 2, is_python_driver: bool = False
                               ) -> List[str]:
    filter_version = f"| grep {'' if is_python_driver else '-v '}scylla"
    commands = [
        f"cd {repo_directory}",
        f"git tag --sort=-creatordate {filter_version}",
    ]
    major_tags = set()
    tags = []
    for repo_tag in subprocess.check_output("\n".join(commands), shell=True).decode().splitlines():
        if "." in repo_tag and not ("-" in repo_tag and not repo_tag.endswith("-scylla")):
            major_tag = tuple(repo_tag.split(".", maxsplit=2)[:2])
            if major_tag not in major_tags:
                major_tags.add(major_tag)
                tags.append(repo_tag)
            if len(tags) == latest_tags_size:
                break
    else:
        raise ValueError(f"The last {latest_tags_size} tags in {repo_directory} couldn't be extracted")
    return tags


def get_arguments():
    default_protocols = ['3', '4']
    parser = argparse.ArgumentParser()
    parser.add_argument('python_driver_git', help='folder with git repository of python-driver')
    parser.add_argument('scylla_install_dir',
                        help='folder with scylla installation, e.g. a checked out git scylla has been built',
                        nargs='?', default='')
    parser.add_argument('--driver-type', help='Type of python-driver ("scylla", "cassandra" or "datastax")',
                        dest='driver_type')
    parser.add_argument('--versions', default='2',
                        help="python-driver versions to test, default=2 - take the two latest driver's tags")
    parser.add_argument('--tests', default='tests.integration.standard',
                        help='tests to pass to nosetests tool, default=tests.integration.standard')
    parser.add_argument('--protocols', default=default_protocols,
                        help='cqlsh native protocol, default={}'.format(','.join(protocols)))
    parser.add_argument('--scylla-version', help="relocatable scylla version to use",
                        default=os.environ.get('SCYLLA_VERSION', None))
    return parser.parse_args()


if __name__ == '__main__':
    arguments = get_arguments()
    if "dynamic" in arguments.versions:
        versions = extract_n_latest_repo_tags(
            repo_directory=arguments.python_driver_git,
            latest_tags_size=1,
            is_python_driver=arguments.driver_type == "scylla"
        )
    else:
        versions = arguments.versions.split(",") if isinstance(arguments.versions, str) else arguments.versions

    protocols = arguments.protocols.split(',') if isinstance(arguments.protocols, str) else arguments.protocols
    logging.info('The following python driver versions will test: '.format(', '.join(versions)))
    main(arguments.python_driver_git, arguments.scylla_install_dir, arguments.driver_type, arguments.tests, versions,
         protocols, arguments.scylla_version)
