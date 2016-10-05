import subprocess
import shutil
import os

class Run:
    def __init__( self, directory, tag ):
        self._tag = tag
        os.chdir( directory )
        subprocess.check_call( 'git checkout {}'.format( tag ), shell = True )
        self._setupOutputDirectory()
        testCommand = 'nosetests --xunit-file {} -s tests/integration/standard/test_cluster.py'.format( self._xunitFile( 'nosetests.log' ) )
        subprocess.call( testCommand.split(), env = self._environment() )

    def _setupOutputDirectory( self ):
        self._xunitDirectory = os.path.join( 'xunit', self._tag )
        try:
            shutil.rmtree( self._xunitDirectory )
        except:
            pass
        os.makedirs( self._xunitDirectory )

    def _xunitFile( self, name ):
        return os.path.join( self._xunitDirectory, name )

    def _environment( self ):
        result = {}
        result.update( os.environ )
        result[ 'PROTOCOL_VERSION' ] = '3'
        return result
