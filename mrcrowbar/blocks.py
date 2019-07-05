"""Definition classes for data blocks."""

from collections import OrderedDict
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar.fields import Field, Bytes
from mrcrowbar.refs import Ref
from mrcrowbar.checks import Check

from mrcrowbar import common, utils

class FieldDescriptor( object ):
    def __init__( self, name ):
        """Attribute wrapper class for Fields.

        name
            Name of the Field.
        """
        self.name = name

    def __get__( self, instance, cls ):
        try:
            if instance is None:
                return cls._fields[self.name]
            return instance._field_data[self.name]
        except KeyError:
            raise AttributeError( self.name )

    def __set__( self, instance, value ):
        if instance is None:
            return
        instance._field_data[self.name] = value
        return

    def __delete__( self, instance ):
        if self.name not in instance._fields:
            raise AttributeError( "{} has no attribute {}".format(
                type( instance ).__name__, self.name ) )
        del instance._fields[self.name]


class RefDescriptor( object ):
    def __init__( self, name ):
        """Attribute wrapper class for Refs.

        name
            Name of the Ref.
        """
        self.name = name

    def __get__( self, instance, cls ):
        try:
            if instance is None:
                return cls._refs[self.name]
            # FIXME: don't cache until we evaluate if the performance suffers
            if True: #self.name not in instance._ref_cache:
                instance._ref_cache[self.name] = instance._refs[self.name].get( instance )
            return instance._ref_cache[self.name]
        except KeyError:
            raise AttributeError( self.name )

    def __set__( self, instance, value ):
        if instance is None:
            return
        instance._refs[self.name].set( instance, value )
        return

    def __delete__( self, instance ):
        raise AttributeError( "can't delete Ref" )


class BlockMeta( type ):
    def __new__( mcs, name, bases, attrs ):
        """Metaclass for Block which detects and wraps attributes from the class definition."""

        # Structures used to accumulate meta info
        fields = OrderedDict()
        refs = OrderedDict()
        checks = OrderedDict()

        # add base class attributes to structs
        for base in bases:
            if hasattr( base, '_fields' ):
                fields.update( base._fields )
            if hasattr( base, '_refs' ):
                refs.update( base._refs )
            if hasattr( base, '_checks' ):
                checks.update( base._checks )

        # Parse this class's attributes into meta structures
        previous = None
        # Python 3.6+ uses an ordered dict for class attributes; prior to that we cheat
        attrs_compat = OrderedDict( sorted( attrs.items(), key=lambda i: getattr(i[1], '_position_hint', 0) ) )
        for key, value in attrs_compat.items():
            if isinstance( value, Field ):
                fields[key] = value
                value._previous_attr = previous
                previous = key
            if isinstance( value, Ref ):
                refs[key] = value
            if isinstance( value, Check ):
                checks[key] = value
                check_fields = value.get_fields()
                if isinstance( check_fields, dict ):
                    for field_id, field in value.get_fields().items():
                        sub_key = '{}__{}'.format(key, field_id)
                        fields[sub_key] = field
                        field._previous_attr = previous
                        previous = sub_key
                elif isinstance( check_fields, Field ):
                    fields[key] = check_fields
                    check_fields._previous_attr = previous
                    previous = key


        # Convert list of types into fields for new klass
        for key, field in fields.items():
            attrs[key] = FieldDescriptor( key )
        for key, ref in refs.items():
            attrs[key] = RefDescriptor( key )

        # Ready meta data to be klass attributes
        attrs['_fields'] = fields
        attrs['_refs'] = refs
        attrs['_checks'] = checks

        klass = type.__new__( mcs, name, bases, attrs )

        for field_name, field in fields.items():
            field._name = field_name

        return klass

    @property
    def fields( cls ):
        return cls._fields

    @property
    def refs( cls ):
        return cls._refs
    
    @property
    def checks( cls ):
        return cls._checks


class Block( object, metaclass=BlockMeta ):
    _parent = None
    _endian = None

    def __init__( self, source_data=None, parent=None, preload_attrs=None, endian=None ):
        """Base class for Blocks.

        source_data
            Source data to construct Block with. Can be a byte string or 
            another Block object.

        parent
            Parent Block object where this Block is defined. Used for e.g. 
            evaluating Refs.

        preload_attrs
            Attributes on the Block to set before importing the data. Used
            for linking in dependencies before loading.

        endian
            Platform endianness to use when interpreting the Block data. 
            Useful for Blocks which have the same data layout but different
            endianness for stored numbers. Has no effect on fields with an
            predefined endianness.
        """
        self._field_data = {}
        self._ref_cache = {}
        if parent is not None:
            assert isinstance( parent, Block )
        self._parent = parent
        self._endian = endian if endian else (parent._endian if parent else self._endian)

        if preload_attrs:
            for attr, value in preload_attrs.items():
                setattr( self, attr, value )

        # start the initial load of data
        if isinstance( source_data, Block ):
            self.clone_data( source_data )
        else:
            self.import_data( source_data )

        # cache all refs
        for key, ref in self._refs.items():
            ref.cache( self )

    def __repr__( self ):
        desc = '0x{:016x}'.format( id( self ) )
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return '<{}: {}>'.format( self.__class__.__name__, desc )

    @property
    def repr( self ):
        """Plaintext summary of the Block."""
        return None

    @property
    def serialised( self ):
        """Tuple containing the contents of the Block."""
        klass = self.__class__
        return ((klass.__module__, klass.__name__), tuple( (name, field.serialise( self._field_data[name], parent=self ) ) for name, field in klass._fields.items()))

    def clone_data( self, source ):
        """Clone data from another Block.

        source
            Block instance to copy from.
        """
        klass = self.__class__
        assert isinstance( source, klass )

        for name in klass._fields:
            self._field_data[name] = getattr( source, name )

    def import_data( self, raw_buffer ):
        """Import data from a byte array.

        raw_buffer
            Byte array to import from.
        """
        klass = self.__class__
        if raw_buffer:
            assert common.is_bytes( raw_buffer )
#            raw_buffer = memoryview( raw_buffer )

        self._field_data = {}

        for name in klass._fields:
            if raw_buffer:
                self._field_data[name] = klass._fields[name].get_from_buffer(
                    raw_buffer, parent=self
                )
            else:
                self._field_data[name] = klass._fields[name].default
        
        if raw_buffer:
            for name, check in klass._checks.items():
                check.check_buffer( raw_buffer, parent=self )

            # if we have debug logging on, check the roundtrip works
            if logger.isEnabledFor( logging.INFO ):
                test = self.export_data()
                if logger.getEffectiveLevel() <= logging.DEBUG:
                    logger.debug( 'Stats for {}:'.format( self ) )
                    logger.debug( 'Import buffer size: {}'.format( len( raw_buffer ) ) )
                    logger.debug( 'Export size: {}'.format( len( test ) ) )
                    if test == raw_buffer:
                        logger.debug( 'Content: exact match!' )
                    elif test == raw_buffer[:len( test )]:
                        logger.debug( 'Content: partial match!' )
                    else:
                        logger.debug( 'Content: different!' )
                        for x in utils.hexdump_diff_iter( raw_buffer[:len( test )], test ):
                            logger.debug( x )
                elif test != raw_buffer[:len( test )]:
                    logger.info( '{} export produced changed output from import'.format( self ) )

#        if raw_buffer:
#            raw_buffer.release()
        return


    def export_data( self ):
        """Export data to a byte array."""
        klass = self.__class__

        output = bytearray( b'\x00'*self.get_size() )

        # prevalidate all data before export.
        # this is important to ensure that any dependent fields
        # are updated beforehand, e.g. a count referenced
        # in a BlockField
        queue = []
        for name in klass._fields:
            self.scrub_field( name )
            self.validate_field( name )

        self.update_deps()

        for name in klass._fields:
            klass._fields[name].update_buffer_with_value(
                self._field_data[name], output, parent=self
            )

        for name, check in klass._checks.items():
            check.update_buffer( output, parent=self )
        return output

    def update_deps( self ):
        """Update dependencies on all the fields on this Block instance."""
        klass = self.__class__

        for name in klass._fields:
            self.update_deps_on_field( name )
        return

    def validate( self ):
        """Validate all the fields on this Block instance."""
        klass = self.__class__

        for name in klass._fields:
            self.validate_field( name )
        return

    def get_size( self ):
        """Get the projected size (in bytes) of the exported data from this Block instance."""
        klass = self.__class__
        size = 0
        for name in klass._fields:
            size = max( size, klass._fields[name].get_end_offset( self._field_data[name], parent=self ) )
        for check in klass._checks.values():
            size = max( size, check.get_end_offset( parent=self ) )
        return size

    def get_field_start_offset( self, field_name, index=None ):
        klass = self.__class__
        return klass._fields[field_name].get_start_offset( self._field_data[field_name], parent=self, index=index )

    def get_field_size( self, field_name, index=None ):
        klass = self.__class__
        return klass._fields[field_name].get_size( self._field_data[field_name], parent=self, index=index )

    def get_field_end_offset( self, field_name, index=None ):
        klass = self.__class__
        return klass._fields[field_name].get_end_offset( self._field_data[field_name], parent=self, index=index )

    def update_deps_on_field( self, field_name ):
        klass = self.__class__
        return klass._fields[field_name].update_deps( self._field_data[field_name], parent=self )

    def scrub_field( self, field_name ):
        klass = self.__class__
        self._field_data[field_name] = klass._fields[field_name].scrub( self._field_data[field_name], parent=self )
        return self._field_data[field_name]

    def validate_field( self, field_name ):
        klass = self.__class__
        return klass._fields[field_name].validate( self._field_data[field_name], parent=self )


class Unknown( Block ):
    """Placeholder block for data of an unknown format."""

    #: Raw data.
    data =  Bytes( 0x0000 )
