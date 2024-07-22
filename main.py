import sys
import argparse
import logging
import os
import subprocess
from typing import List
import traceback

from run import Run
from email_sender import create_report, get_driver_origin_remote, send_mail

logging.basicConfig(level=logging.INFO)


def main(arguments: argparse.Namespace):
    status = 0
    results = dict()

    for driver_version in arguments.versions:
        for protocol in arguments.protocols:
            logging.info('=== PYTHON DRIVER VERSION %s, PROTOCOL v%s ===', driver_version, protocol)
            runner = Run(python_driver_git=arguments.python_driver_git,
                             python_driver_type=arguments.driver_type,
                             scylla_install_dir=arguments.scylla_install_dir,
                             tag=driver_version,
                             protocol=protocol,
                             tests=arguments.tests,
                             scylla_version=arguments.scylla_version,
                             collect_only=arguments.collect_only)
            try:
                result = runner.run()
                logging.info("=== (%s:%s) PYTHON DRIVER MATRIX RESULTS FOR PROTOCOL v%s ===",
                             arguments.driver_type, driver_version, protocol)
                logging.info(", ".join(f"{key}: {value}" for key, value in result.summary.items()))
                if result.is_failed:
                    if not result.summary["tests"]:
                        logging.error("The run is failed because of one or more steps in the setup are failed")
                    else:
                        logging.error("Please check the report because there were failed tests")
                    status = 1
                results[(driver_version, protocol)] = result.summary
            except Exception:
                logging.exception(f"{driver_version} failed")
                status = 1
                exc_type, exc_value, exc_traceback = sys.exc_info()
                failure_reason = traceback.format_exception(exc_type, exc_value, exc_traceback)
                results[(driver_version, protocol)] = dict(exception=failure_reason)
                runner.create_metadata_for_failure(reason="\n".join(failure_reason))

    if arguments.recipients:
        email_report = create_report(results=results)
        email_report['driver_remote'] = get_driver_origin_remote(arguments.python_driver_git)
        email_report['status'] = "SUCCESS" if status == 0 else "FAILED"
        send_mail(arguments.recipients, email_report)

    quit(status)


def extract_n_latest_repo_tags(repo_directory: str, latest_tags_size: int = 2, is_scylla_driver: bool = False
                               ) -> List[str]:
    filter_version = f"| grep {'' if is_scylla_driver else '-v '}scylla"
    commands = [
        f"cd {repo_directory}",
        "git checkout .",
        "git fetch -p --all",
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


def get_arguments() -> argparse.Namespace:
    default_protocols = ['3', '4']
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('python_driver_git', help='folder with git repository of python-driver')
    parser.add_argument('scylla_install_dir',
                        help='folder with scylla installation, e.g. a checked out git scylla has been built',
                        nargs='?', default='')
    parser.add_argument('--driver-type', help='Type of python-driver ("scylla", "cassandra" or "datastax")',
                        dest='driver_type')
    parser.add_argument('--versions', default="2", type=str,
                        help="python-driver versions to test\n"
                             "The value can be number or str with comma (example: '3.24.0,3.25.0').\n"
                             "default=2 - take the two latest driver's tags.")
    parser.add_argument('--tests', default='tests.integration.standard',
                        help='tests to pass to pytest tool, default=tests.integration.standard')
    parser.add_argument('--protocols', default=default_protocols,
                        help='cqlsh native protocol, default={}'.format(','.join(default_protocols)))
    parser.add_argument('--scylla-version', help="relocatable scylla version to use",
                        default=os.environ.get('SCYLLA_VERSION', None)),
    parser.add_argument('--collect-only', action="store_true", help="Show the all test names without run them",
                        default=False)
    parser.add_argument('--recipients', help="whom to send mail at the end of the run",  nargs='+', default=None)
    arguments = parser.parse_args()

    driver_versions = str(arguments.versions).replace(" ", "")
    if driver_versions.isdigit():
        arguments.versions = extract_n_latest_repo_tags(
            repo_directory=arguments.python_driver_git,
            latest_tags_size=int(driver_versions),
            is_scylla_driver=arguments.driver_type == "scylla"
        )
    else:
        arguments.versions = driver_versions.split(",")
    if not isinstance(arguments.protocols, list):
        arguments.protocols = arguments.protocols.split(",")
    return arguments


if __name__ == '__main__':
    main(get_arguments())
