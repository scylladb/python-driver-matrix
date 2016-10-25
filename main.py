import logsubprocess
import logging
logging.basicConfig( level = logging.INFO )
import run
import os
import argparse

def main( pythonDriverGit, scyllaInstallDirectory ):
    run.Run( pythonDriverGit, scyllaInstallDirectory, '3.5.0' )

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument( 'pythonDriverGit', help = 'folder with git repository of python-driver' )
    parser.add_argument( 'scyllaInstallDirectory', help = 'folder with scylla installation, e.g. a checked out git scylla has been built' )
    arguments = parser.parse_args()
    main( arguments.pythonDriverGit, arguments.scyllaInstallDirectory )
