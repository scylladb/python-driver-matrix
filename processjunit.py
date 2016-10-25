import xml.etree.ElementTree

class ProcessJUnit:
    def __init__( self, filename ):
        tree = xml.etree.ElementTree.parse( filename )
        self._summary = { 'testcase': 0, 'failure': 0, 'skipped': 0 }
        for element in tree.getiterator():
            if element.tag in self._summary:
                self._summary[ element.tag ] += 1

    @property
    def summary( self ):
        return self._summary
