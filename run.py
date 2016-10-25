import subprocess
import shutil
import os

class Run:
    def __init__( self, pythonDriverDirectory, scyllaInstallDirectory, tag ):
        self._tag = tag
        self._scyllaInstallDirectory = scyllaInstallDirectory
        os.chdir( pythonDriverDirectory )
        subprocess.check_call( 'git checkout .'.format( tag ), shell = True )
        subprocess.check_call( 'git checkout {}'.format( tag ), shell = True )
        self._setupOutputDirectory()
        self._applyPatch()
        testCommand = 'nosetests --with-xunit --xunit-file {} -s tests/integration/standard/test_cluster.py'.format( self._xunitFile( 'nosetests.xml' ) )
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
        result[ 'INSTALL_DIRECTORY' ] = self._scyllaInstallDirectory
        return result

    def _applyPatch( self ):
        here = os.path.dirname( __file__ )
        patchFile = os.path.join( here, 'patches', self._tag )
        command = "patch -p1 -i {}".format( patchFile )
        subprocess.check_call( command, shell = True )
