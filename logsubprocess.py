import subprocess
import logging

def wrap( attributeName ):
    original = getattr( subprocess, attributeName )
    def _wrappedInLogging( * args, ** kwargs ):
        if type( args[ 0 ] ) is list:
            commandString = ' '.join( args[ 0 ] )
        else:
            commandString = args[ 0 ]
        logging.info( '{}: {}'.format( attributeName, commandString ) )
        return original( * args, ** kwargs )

    setattr( subprocess, attributeName, _wrappedInLogging )

wrap( 'Popen' )
