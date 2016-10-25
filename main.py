import logsubprocess
import logging
logging.basicConfig( level = logging.INFO )
import run
import os
import argparse

def main( pythonDriverGit, scyllaInstallDirectory ):
    versions = '3.0.0', '3.2.0', '3.4.0', '3.5.0'
    results = []
    for version in versions:
        results.append( run.Run( pythonDriverGit, scyllaInstallDirectory, version ) )

    print( '=== PYTHON DRIVER MATRIX RESULTS ===' )
    failed = False
    for result in results:
        print( result )
        if result.summary[ 'failure' ] > 0:
            failed = True

    if failed:
        quit( 1 )
    else:
        quit( 0 )

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument( 'pythonDriverGit', help = 'folder with git repository of python-driver' )
    parser.add_argument( 'scyllaInstallDirectory', help = 'folder with scylla installation, e.g. a checked out git scylla has been built' )
    arguments = parser.parse_args()
    main( arguments.pythonDriverGit, arguments.scyllaInstallDirectory )
