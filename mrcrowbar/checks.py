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

    def get_start_offset( self, parent=None ):
        """Return the start offset of where the Check inspects the Block."""
        return 0

    def get_size( self, parent=None ):
        """Return the size of the checked data (in bytes)."""
        return 0

    def get_end_offset( self, parent=None ):
        """Return the end offset of where the Check inspects the Block."""
        return self.get_start_offset( parent ) + self.get_size( parent )

    repr = None


class Const( Check ):
    def __init__( self, field, value ):
        assert isinstance( field, Field )
        self.field = field
        self.value = value

    def check_buffer( self, buffer, parent=None ):
        test = self.field.get_from_buffer( buffer, parent )
        if test != self.value:
            print( 'Warning: {}:{}, found {}!'.format( parent, self, self.value, test ) )
        
    def update_buffer( self, buffer, parent=None ):
        self.field.update_buffer_with_value( self.value, buffer, parent )

    def get_start_offset( self, parent=None ):
        return self.field.get_start_offset( self.value, parent )

    def get_size( self, parent=None ):
        return self.field.get_size( self.value, parent )

    @property
    def repr( self ):
        return '{} == {}'.format( self.field, self.value )
