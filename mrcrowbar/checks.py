import logging
logger = logging.getLogger( __name__ )

from mrcrowbar.fields import Field
from mrcrowbar.refs import Ref, property_get, property_set
from mrcrowbar import common, utils


class CheckException( Exception ):
    pass

class Check( object ):
    def __init__( self, raise_exception=False ):
        self._position_hint = next( common.next_position_hint )
        self.raise_exception = raise_exception

    def check_buffer( self, buffer, parent=None ):
        pass

    def update_buffer( self, buffer, parent=None ):
        pass

    def __repr__( self ):
        desc = '0x{:016x}'.format( id( self ) )
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return '<{}: {}>'.format( self.__class__.__name__, desc )

    def get_fields( self ):
        """Return None, a single field, or a dictionary of Fields embedded within the Check."""
        return None

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
    def __init__( self, field, value, *args, **kwargs ):
        assert isinstance( field, Field )
        super().__init__( *args, **kwargs )
        self.field = field
        self.value = value

    def get_fields( self ):
        return self.field

    def check_buffer( self, buffer, parent=None ):
        test = self.field.get_from_buffer( buffer, parent )
        if test != self.value:
            mismatch = '{}:{}, found {}!'.format( self, self.value, test )
            if self.raise_exception:
                raise CheckException( mismatch )
            logger.warning( mismatch )
        
    def update_buffer( self, buffer, parent=None ):
        self.field.update_buffer_with_value( self.value, buffer, parent )

    def get_start_offset( self, parent=None ):
        return self.field.get_start_offset( self.value, parent )

    def get_size( self, parent=None ):
        return self.field.get_size( self.value, parent )

    @property
    def repr( self ):
        return '{} == {}'.format( self.field, self.value )


class Updater( Check ):
    def __init__( self, source, target, *args, **kwargs ):
        assert isinstance( source, Ref )
        assert isinstance( target, Ref )
        super().__init__( *args, **kwargs )
        self.source = source
        self.target = target

    def update_buffer( self, buffer, parent=None ):
        value = property_get( self.source, parent )
        self.property_set( self.target, parent, value )

    @property
    def repr( self ):
        return '{} = {}'.format( self.target, self.source )
