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
    _cache_bytes = False
    _bytes = None

    def __init__( self, source_data=None, parent=None, preload_attrs=None, endian=None, cache_bytes=False, path_hint=None ):
        """Base class for Blocks.

        source_data
            Source data to construct Block with. Can be a byte string, dictionary 
            of attribute: value pairs, or another Block object.

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

        cache_bytes
            Cache the bytes equivalent of the Block. Useful for debugging the
            loading procedure. Defaults to False.

        path_hint
            Cache a string containing the path of the current Block, relative
            to the root.
        """
        self._field_data = {}
        self._ref_cache = {}
        if parent is not None:
            assert isinstance( parent, Block )
        self._parent = parent
        self._endian = endian if endian else (parent._endian if parent else self._endian)
        self._path_hint = path_hint
        if self._path_hint is None:
            self._path_hint = '<{}>'.format( self.__class__.__name__ )

        if cache_bytes:
            self._cache_bytes = True
            if source_data and common.is_bytes( source_data ):
                self._bytes = bytes( source_data )

        if preload_attrs:
            for attr, value in preload_attrs.items():
                setattr( self, attr, value )

        # start the initial load of data
        if isinstance( source_data, Block ):
            self.clone_data( source_data )
        elif isinstance( source_data, dict ):
            # preload defaults, then overwrite with dictionary values
            self.import_data( None )
            self.update_data( source_data )
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

    def update_data( self, source ):
        """Update data from a dictionary.

        source
            Dictionary of attribute: value pairs.
        """
        assert isinstance( source, dict )
        for attr, value in source.items():
            assert hasattr( self, attr )
            setattr( self, attr, value )

    def import_data( self, raw_buffer ):
        """Import data from a byte array.

        raw_buffer
            Byte array to import from.
        """
        klass = self.__class__
        if raw_buffer is not None:
            assert common.is_bytes( raw_buffer )
#            raw_buffer = memoryview( raw_buffer )

        self._field_data = {}

        logger.debug( '{}: loading fields'.format( self ) )

        for name in klass._fields:
            if raw_buffer is not None:
                if logger.isEnabledFor( logging.DEBUG ):
                    logger.debug( '{} [{}]: input buffer'.format( name, klass._fields[name] ) )
                self._field_data[name] = klass._fields[name].get_from_buffer(
                    raw_buffer, parent=self
                )
                if logger.isEnabledFor( logging.DEBUG ):
                    logger.debug( 'Result for {} [{}]: {}'.format( name, klass._fields[name], self._field_data[name] ) )
            else:
                self._field_data[name] = klass._fields[name].default
        
        if raw_buffer is not None:
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
                        logger.debug( 'Content: exact match with overflow!' )
                    else:
                        logger.debug( 'Content: different!' )
                        for x in utils.hexdump_diff_iter( raw_buffer[:len( test )], test ):
                            logger.debug( x )
                elif test != raw_buffer[:len( test )]:
                    logger.info( '{} export produced changed output from import'.format( self ) )

#        if raw_buffer:
#            raw_buffer.release()
        return

    load = import_data

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

    dump = export_data

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

    def get_field_obj( self, field_name ):
        """Return a Field object associated with this Block class.

        field_name
            Name of the Field.
        """
        klass = self.__class__
        return klass._fields[field_name]

    def get_field_names( self ):
        """Get the list of Fields associated with this Block class."""
        klass = self.__class__
        return klass._fields.keys()

    def get_field_path( self, field ):
        """Return the path of this Block and a child Field in the current object tree.

        Used for error messages.

        field
            Field object on the object to reference.
        """
        klass = self.__class__
        for field_name, field_obj in klass._fields.items():
            if field_obj == field:
                return '{}.{}'.format( self.get_path(), field_name )
        return '{}.?'.format( self.get_path() )

    def get_path( self ):
        """Return the path of this Block in the current object tree.

        Used for error messages."""
        klass = self.__class__
        if not self._parent:
            self._path_hint = '<{}>'.format( klass.__name__ )
        else:
            pklass = self._parent.__class__
            for field_name, field_obj in pklass._fields.items():
                if field_name in self._parent._field_data:
                    if self._parent._field_data[field_name] == self:
                        self._path_hint = '{}.{}'.format( self._parent.get_path(), field_name )
                    elif type( self._parent._field_data[field_name] ) == list:
                        for i, subobject in enumerate( self._parent._field_data[field_name] ):
                            if subobject == self:
                                self._path_hint = '{}.{}[{}]'.format( self._parent.get_path(), field_name, i )
                            elif hasattr( subobject, 'obj' ) and subobject.obj == self:
                                self._path_hint = '{}.{}[{}].obj'.format( self._parent.get_path(), field_name, i )
        return self._path_hint

    def get_field_start_offset( self, field_name, index=None ):
        """Return the start offset of where a Field's data is to be stored in the Block.

        field_name
            Name of the Field to inspect.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        klass = self.__class__
        return klass._fields[field_name].get_start_offset( self._field_data[field_name], parent=self, index=index )

    def get_field_size( self, field_name, index=None ):
        """Return the size of a Field's data (in bytes).

        field_name
            Name of the Field to inspect.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        klass = self.__class__
        return klass._fields[field_name].get_size( self._field_data[field_name], parent=self, index=index )

    def get_field_end_offset( self, field_name, index=None ):
        """Return the end offset of a Field's data. Useful for chainloading.

        field_name
            Name of the Field to inspect.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        klass = self.__class__
        return klass._fields[field_name].get_end_offset( self._field_data[field_name], parent=self, index=index )

    def scrub_field( self, field_name ):
        """Return a Field's data coerced to the correct type (if necessary).

        field_name
            Name of the Field to inspect.

        Throws FieldValidationError if value can't be coerced.
        """

        klass = self.__class__
        self._field_data[field_name] = klass._fields[field_name].scrub( self._field_data[field_name], parent=self )
        return self._field_data[field_name]

    def update_deps_on_field( self, field_name ):
        """Update all dependent variables derived from the value of a Field.

        field_name
            Name of the Field to inspect.
        """
        klass = self.__class__
        return klass._fields[field_name].update_deps( self._field_data[field_name], parent=self )

    def validate_field( self, field_name ):
        """Validate that a correctly-typed Python object meets the constraints for a Field.

        field_name
            Name of the Field to inspect.

        Throws FieldValidationError if a constraint fails.

        """
        klass = self.__class__
        return klass._fields[field_name].validate( self._field_data[field_name], parent=self )

    def hexdump( self, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, address_base=None, show_offsets=True, show_glyphs=True ):
        """Print the exported data in tabular hexadecimal/ASCII format.

        start
            Start offset to read from (default: start)

        end
            End offset to stop reading at (default: end)

        length
            Length to read in (optional replacement for end)

        major_len
            Number of hexadecimal groups per line

        minor_len
            Number of bytes per hexadecimal group

        colour
            Add ANSI colour formatting to output (default: true)

        address_base
            Base address to use for labels (default: start)

        show_offsets
            Display offsets at the start of each line (default: true)

        show_glyphs
            Display glyph map at the end of each line (default: true)

        Raises ValueError if both end and length are defined.
        """
        utils.hexdump(
            self.export_data(), start=start, end=end,
            length=length, major_len=major_len, minor_len=minor_len,
            colour=colour, address_base=address_base,
            show_offsets=show_offsets, show_glyphs=show_glyphs
        )

    def histdump( self, start=None, end=None, length=None, samples=0x10000, width=64, address_base=None ):
        """Print the histogram of the exported data.

        start
            Start offset to read from (default: start)

        end
            End offset to stop reading at (default: end)

        length
            Length to read in (optional replacement for end)

        samples
            Number of samples per histogram slice (default: 0x10000)

        width
            Width of rendered histogram (default: 64)

        address_base
            Base address to use for labelling (default: start)
        """
        utils.histdump(
            self.export_data(), start=start, end=end, length=length,
            samples=samples, width=width, address_base=address_base
        )

    def search( self, pattern, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False ):
        """Find the Fields that match a byte pattern.

        pattern
            Pattern to match, as a Python string

        encoding
            Convert strings in the pattern to a specific Python encoding (default: utf8)

        fixed_string
            Interpret the pattern as a fixed string (disable regular expressions)

        hex_format
            Interpret the pattern as raw hexidecimal (default: false)

        ignore_case
            Perform a case-insensitive search
        """
        return [x for x in utils.search_iter(
            pattern, source, prefix='<{}>'.format( self.__class__.__name__ ),
            depth=None, encoding=encoding, fixed_string=fixed_string,
            hex_format=hex_format, ignore_cast=ignore_case
        )]


class Unknown( Block ):
    """Placeholder block for data of an unknown format."""

    #: Raw data.
    data =  Bytes( 0x0000 )
