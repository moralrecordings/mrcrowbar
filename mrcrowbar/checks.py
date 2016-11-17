from mrcrowbar.fields import Field
from mrcrowbar import utils

class Check( object ):
    def __init__( self ):
        pass

    def check_buffer( self, buffer, parent=None ):
        pass

    def update_buffer( self, buffer, parent=None ):
        pass

    def __repr__( self ):
        desc = '0x{:016x}'.format( id( self ) )
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return '<{}: {}>'.format( self.__class__.__name__, desc )

    repr = None


class Const( Check ):
    def __init__( self, field, value ):
        assert isinstance( field, Field )
        self.field = field
        self.value = value

    def check_buffer( self, buffer, parent=None ):
        test = self.field.get_from_buffer( buffer, parent )
        if test != self.value:
            print( 'Warning: was expecting constant value {}, found {}!'.format( self.value, test ) )
        
    def update_buffer( self, buffer, parent=None ):
        self.field.update_buffer_with_value( self.value, buffer, parent )
