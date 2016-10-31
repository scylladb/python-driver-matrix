import subprocess
import processjunit
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
        testCommand = 'nosetests --with-xunit --xunit-file {} -s tests/integration/standard/test_cluster.py'.format( self._xunitFile() )
        subprocess.call( testCommand.split(), env = self._environment() )
        self._junit = processjunit.ProcessJUnit( self._xunitFile(), self._ignoreFile() )
        content = open( self._xunitFile() ).read()
        open( self._xunitFile(), 'w' ).write( content.replace( 'nosetests', 'version_{}'.format(tag) ) )

    @property
    def summary( self ):
        return self._junit.summary

    def __repr__( self ):
        details = dict( version = self._tag )
        details.update( self._junit.summary )
        return '{version}: pass: {testcase}, failure: {failure}, skipped: {skipped}, ignored_in_analysis: {ignored_in_analysis}'.format( ** details )

    def _setupOutputDirectory( self ):
        self._xunitDirectory = os.path.join( 'xunit', self._tag )
        try:
            shutil.rmtree( self._xunitDirectory )
        except:
            pass
        os.makedirs( self._xunitDirectory )

    def _xunitFile( self ):
        return os.path.join( self._xunitDirectory, 'nosetests.{}.xml'.format( self._tag ) )

    def _ignoreFile( self ):
        here = os.path.dirname( __file__ )
        ignoreFile = os.path.join( here, 'versions', self._tag, 'ignore.yaml' )
        return ignoreFile

    def _environment( self ):
        result = {}
        result.update( os.environ )
        result[ 'PROTOCOL_VERSION' ] = '3'
        result[ 'INSTALL_DIRECTORY' ] = self._scyllaInstallDirectory
        return result

    def _applyPatch( self ):
        here = os.path.dirname( __file__ )
        patchFile = os.path.join( here, 'versions', self._tag, 'patch' )
        command = "patch -p1 -i {}".format( patchFile )
        subprocess.check_call( command, shell = True )
