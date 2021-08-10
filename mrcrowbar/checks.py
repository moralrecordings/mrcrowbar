from __future__ import annotations

import logging
logger = logging.getLogger( __name__ )

from mrcrowbar.refs import Ref, property_get, property_set
from mrcrowbar import common, utils

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mrcrowbar.fields import Field

class CheckException( Exception ):
    pass

class Check( object ):
    def __init__( self, raise_exception: bool=False ):
        """Base class for Checks.

        raise_exception
            Whether to raise an exception if the check fails.
        """
        self._position_hint = next( common.next_position_hint )
        self.raise_exception = raise_exception

    def check_buffer( self, buffer: common.BytesReadType, parent=None ):
        """Check if the import buffer passes the check.

        Throws CheckException if raise_exception = True and the buffer doesn't match.
        """
        pass

    def update_deps( self, parent=None ):
        """Update all dependent variables derived from this Check."""
        pass

    def __repr__( self ):
        desc = f'0x{id( self ):016x}'
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return f'<{self.__class__.__name__}: {desc}>'

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
    def __init__( self, field: Field, target, *args, **kwargs ):
        """Check for ensuring a Field matches a particular constant.

        On import, the value is tested. On export, the value is copied
        from the target.

        field
            Field instance to wrap.

        target
            Target to copy from on export.
        """
        super().__init__( *args, **kwargs )
        self.field = field
        self.target = target

    def get_fields( self ):
        return self.field

    def check_buffer( self, buffer, parent=None ):
        test = self.field.get_from_buffer( buffer, parent )
        value = property_get( self.target, parent )
        if test != value:
            mismatch = f'{self}:{value}, found {test}!'
            if self.raise_exception:
                raise CheckException( mismatch )
            logger.warning( mismatch )

    def update_deps( self, parent=None ):
        if parent:
            name = parent.get_field_name_by_obj( self.field )
            value = property_get( self.target, parent )
            property_set( Ref( name ), parent, value )
        return

    def get_start_offset( self, parent=None ):
        value = property_get( self.target, parent )
        return self.field.get_start_offset( value, parent )

    def get_size( self, parent=None ):
        value = property_get( self.target, parent )
        return self.field.get_size( value, parent )

    @property
    def repr( self ):
        return f'{self.field} == {self.value}'


class Pointer( Check ):
    def __init__( self, field, target, *args, **kwargs ):
        """Check for loading an offset-type pointer into a Field.

        On import, the value is returned as-is. On export, the value is
        copied from the target; in most cases you'd use an EndOffset for
        another Field in the Block class. This allows for expansion and
        contraction of data.

        field
            Field instance to wrap.

        target
            Target to copy from on export.
        """
        super().__init__( *args, **kwargs )
        self.field = field
        self.target = target

    def get_fields( self ):
        return self.field

    def update_deps( self, parent=None ):
        if parent:
            name = parent.get_field_name_by_obj( self.field )
            value = property_get( self.target, parent )
            property_set( Ref( name ), parent, value )
        return

    def get_start_offset( self, parent=None ):
        value = property_get( self.target, parent )
        return self.field.get_start_offset( value, parent )

    def get_size( self, parent=None ):
        value = property_get( self.target, parent )
        return self.field.get_size( value, parent )

    @property
    def repr( self ):
        return f'{self.field} -> {self.value}'


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
        return f'{self.target} = {self.source}'
