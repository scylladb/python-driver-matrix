import logsubprocess
import logging
logging.basicConfig( level = logging.INFO )
import run
import os

def main():
    pythonDriverGit = os.path.join( os.getenv( 'HOME' ), 'python-driver' )
    run.Run( pythonDriverGit, '3.6.0' )

if __name__ == '__main__':
    main()
