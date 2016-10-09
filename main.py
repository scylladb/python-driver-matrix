import logsubprocess
import logging
logging.basicConfig( level = logging.INFO )
import run
import os
import argparse

def main( pythonDriverGit ):
    run.Run( pythonDriverGit, '3.5.0' )

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument( 'pythonDriverGit', help = 'folder with git repository of python-driver' )
    arguments = parser.parse_args()
    main( arguments.pythonDriverGit )
