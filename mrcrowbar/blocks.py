"""Definition classes for data blocks."""
from __future__ import annotations

import logging
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Sequence

from mrcrowbar.encoding import EndianEncoding

logger = logging.getLogger( __name__ )

if TYPE_CHECKING:
    from mrcrowbar.fields import Field
    from mrcrowbar.refs import Ref
    from mrcrowbar.checks import Check

from mrcrowbar import common, utils


class FieldDescriptor:
    def __init__( self, name: str ):
        """Attribute wrapper class for Fields.

        name
            Name of the Field.
        """
        self.name = name

    def __get__( self, instance: Block, cls: type[Block] ) -> Any:
        try:
            if instance is None:
                return cls._fields[self.name]
            return instance._field_data[self.name]
        except KeyError:
            raise AttributeError( self.name )

    def __set__( self, instance: Block, value: Any ):
        if instance is None:
            return
        instance._field_data[self.name] = value
        instance.set_dirty()
        return

    def __delete__( self, instance ):
        if self.name not in instance._fields:
            raise AttributeError(
                f"{type( instance ).__name__} has no attribute {self.name}"
            )
        del instance._fields[self.name]
        instance.set_dirty()


class RefDescriptor:
    def __init__( self, name: str ):
        """Attribute wrapper class for Refs.

        name
            Name of the Ref.
        """
        self.name = name

    def __get__( self, instance: Block, cls ):
        try:
            if instance is None:
                return cls._refs[self.name]
            # FIXME: don't cache until we evaluate if the performance suffers
            if True:  # self.name not in instance._ref_cache:
                instance._ref_cache[self.name] = instance._refs[self.name].get(
                    instance
                )
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
        from mrcrowbar.checks import Check
        from mrcrowbar.fields import Field
        from mrcrowbar.refs import Coda, Ref

        # Structures used to accumulate meta info
        fields: OrderedDict[str, Field] = OrderedDict()
        refs: OrderedDict[str, Ref[Any]] = OrderedDict()
        checks: OrderedDict[str, Check] = OrderedDict()

        # add base class attributes to structs
        for base in bases:
            if hasattr( base, "_fields" ):
                fields.update( base._fields )
            if hasattr( base, "_refs" ):
                refs.update( base._refs )
            if hasattr( base, "_checks" ):
                checks.update( base._checks )

        # Parse this class's attributes into meta structures
        previous = None
        # Python 3.6+ uses an ordered dict for class attributes; prior to that we cheat
        attrs_compat = OrderedDict(
            sorted( attrs.items(), key=lambda i: getattr( i[1], "_position_hint", 0 ) )
        )
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
                        sub_key = f"{key}__{field_id}"
                        fields[sub_key] = field
                        field._previous_attr = previous
                        previous = sub_key
                elif isinstance( check_fields, Field ):
                    fields[key] = check_fields
                    check_fields._previous_attr = previous
                    previous = key

        # sieve out coda fields
        coda_field_names: list[str] = []
        coda_enabled: bool = False
        coda_chain_size: int = 0
        coda_size: int = 0
        for key, value in fields.items():
            if hasattr( value, "offset" ):
                if isinstance( value.offset, Coda ):
                    if not value.is_fixed_size():
                        raise AttributeError(
                            f"Coda can only be used with Fields that are of a fixed size; {key} is not fixed"
                        )
                    coda_field_names.append( key )
                    coda_enabled = True
                    coda_size = max( coda_size, coda_chain_size )
                    coda_chain_size += value.get_fixed_size() or 0
                elif coda_enabled and isinstance( value.offset, refs.Chain ):
                    if not value.is_fixed_size():
                        raise AttributeError(
                            f"Coda can only be used with Fields that are of a fixed size; {key} is not fixed"
                        )
                    coda_field_names.append( key )
                    coda_chain_size += value.get_fixed_size() or 0
                else:
                    coda_enabled = False

        coda_size = max( coda_size, coda_chain_size )

        # Convert list of types into fields for new klass
        for key, field in fields.items():
            attrs[key] = FieldDescriptor( key )
        for key, ref in refs.items():
            attrs[key] = RefDescriptor( key )

        # Ready meta data to be klass attributes
        attrs["_fields"] = fields
        attrs["_refs"] = refs
        attrs["_checks"] = checks
        attrs["_coda_field_names"] = coda_field_names
        attrs["_coda_size"] = coda_size

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


class Block( metaclass=BlockMeta ):
    _parent: Block | None = None
    _endian: EndianEncoding | None = None
    _cache_bytes = False
    _bytes = None
    _repr_values: list[str] | None = None

    _fields: OrderedDict[str, Field]
    _refs: OrderedDict[str, Ref[Any]]
    _checks: OrderedDict[str, Check]
    _coda_size: int
    _coda_field_names: list[str]
    _cache_refs: bool
    _size: int
    _field_data: dict[str, Any]
    _field_size: dict[str, int]
    _field_start_offset: dict[str, int]
    _ref_cache: dict[str, Any]
    _strict: bool
    _dirty: bool
    _initial_load: bool

    def __init__(
        self,
        source_data: common.BytesReadType | None = None,
        *,
        parent: Block | None = None,
        preload_attrs: dict[str, Any] | None = None,
        endian: EndianEncoding = None,
        cache_bytes: bool = False,
        path_hint: str | None = None,
        strict: bool = False,
        cache_refs: bool = True,
    ):
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

        strict
            Throw an exception if parsing a BlockField fails, instead of
            logging a warning and returning an Unknown. Defaults to False.

        cache_refs
            Pre-cache all the Refs. Defaults to True.
        """
        self._field_data = {}
        self._field_size = {}
        self._field_start_offset = {}
        self._size = 0
        self._ref_cache = {}
        self._dirty = False
        self._initial_load = True
        if parent is not None:
            assert isinstance( parent, Block )
        self._parent = parent
        self._endian = (
            endian if endian else (parent._endian if parent else self._endian)
        )
        self._path_hint = path_hint
        if self._path_hint is None:
            self._path_hint = f"<{self.__class__.__name__}>"
        self._strict = strict
        self._cache_refs = cache_refs

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

        self._initial_load = False
        self._dirty = True
        self.recalculate_fields()

        # cache all refs
        if self._cache_refs:
            for key, ref in self._refs.items():
                ref.cache( self, key )

    def __repr__( self ) -> str:
        desc = f"0x{id( self ):016x}"
        if isinstance( self.repr, str ):
            desc = self.repr
        return f"<{self.__class__.__name__}: {desc}>"

    @property
    def repr( self ) -> str | None:
        """Plaintext summary of the Block."""
        value_map: dict[str, Any] = {}
        if self._repr_values and isinstance( self._repr_values, list ):
            value_map = {
                x: getattr( self, x ) for x in self._repr_values if hasattr( self, x )
            }
        else:
            value_map = {k: v for k, v in self._field_data.items()}
        values: list[str] = []
        for name, value in value_map.items():
            output = ""
            if isinstance( value, str ):
                output = f"str[{len(value)}]"
            elif common.is_bytes( value ):
                output = f"bytes[{len(value)}]"
            elif isinstance( value, Sequence ):
                output = f"list[{len(value)}]"
            else:
                output = str( value )
            values.append( f"{name}={output}" )
        return ", ".join( values )

    @property
    def serialised( self ):
        """Tuple containing the contents of the Block."""
        klass = self.__class__
        return (
            (klass.__module__, klass.__name__),
            tuple(
                (name, field.serialise( self._field_data[name], parent=self ))
                for name, field in klass._fields.items()
            ),
        )

    def clone_data( self, source: Block ) -> None:
        """Clone data from another Block.

        source
            Block instance to copy from.
        """
        klass = self.__class__
        assert isinstance( source, klass )

        for name in klass._fields:
            self._field_data[name] = getattr( source, name )

    def update_data( self, source: dict[str, Any] ) -> None:
        """Update data from a dictionary.

        source
            Dictionary of attribute: value pairs.
        """
        assert isinstance( source, dict )
        for attr, value in source.items():
            assert hasattr( self, attr )
            setattr( self, attr, value )

    def _import_from_field( self, buffer, field_name ):
        klass = self.__class__
        if logger.isEnabledFor( logging.DEBUG ):
            logger.debug( f"{field_name} [{klass._fields[field_name]}]: input buffer" )
        self._field_data[field_name] = klass._fields[field_name].get_from_buffer(
            buffer, parent=self
        )
        if logger.isEnabledFor( logging.DEBUG ):
            if isinstance( self._field_data[field_name], str ):
                logger.debug(
                    f"Result for {field_name} [{klass._fields[field_name]}]: str[{len(self._field_data[field_name])}]"
                )

            elif common.is_bytes( self._field_data[field_name] ):
                logger.debug(
                    f"Result for {field_name} [{klass._fields[field_name]}]: bytes[{len(self._field_data[field_name])}]"
                )
            elif isinstance( self._field_data[field_name], Sequence ):
                logger.debug(
                    f"Result for {field_name} [{klass._fields[field_name]}]: list[{len(self._field_data[field_name])}]"
                )
            else:
                logger.debug(
                    f"Result for {field_name} [{klass._fields[field_name]}]: {self._field_data[field_name]}"
                )

    def import_data( self, raw_buffer: common.BytesReadType | None ) -> None:
        """Import data from a byte array.

        raw_buffer
            Byte array to import from.
        """
        klass = self.__class__
        raw_buffer_partial: common.BytesReadType | None = raw_buffer
        if raw_buffer is not None:
            assert common.is_bytes( raw_buffer )
            if self._coda_size:
                raw_buffer_partial = raw_buffer[: -self._coda_size]

        self._field_data = {}

        if logger.isEnabledFor( logging.DEBUG ):
            logger.debug(
                f"{self.get_path()}<{self.__class__.__name__}>: loading fields"
            )
            if raw_buffer is not None:
                for x in utils.hexdump_iter( raw_buffer, end=0x200 ):
                    logger.debug( x )

        for name in klass._fields:
            if name not in klass._coda_field_names:
                if raw_buffer_partial is not None:
                    self._import_from_field( raw_buffer_partial, name )
                else:
                    self._field_data[name] = klass._fields[name].default

        for name in klass._coda_field_names:
            if raw_buffer is not None:
                self._import_from_field( raw_buffer, name )
            else:
                self._field_data[name] = klass._fields[name].default

        if raw_buffer is not None:
            for name, check in klass._checks.items():
                check.check_buffer( raw_buffer, parent=self )

            # if we have debug logging on, check the roundtrip works
            if logger.isEnabledFor( logging.INFO ):
                test = self.export_data()
                if logger.getEffectiveLevel() <= logging.DEBUG:
                    logger.debug( f"Stats for {self}:" )
                    logger.debug( f"Import buffer size: {len( raw_buffer )}" )
                    logger.debug( f"Export size: {len( test )}" )
                    if test == raw_buffer:
                        logger.debug( "Content: exact match!" )
                    elif test == raw_buffer[: len( test )]:
                        logger.debug( "Content: exact match with overflow!" )
                    else:
                        logger.debug( "Content: different!" )
                        for x in utils.diffdump_iter( raw_buffer[: len( test )], test ):
                            logger.debug( x )
                elif test != raw_buffer[: len( test )]:
                    logger.info(
                        f"{self.__class__.__name__} export produced changed output from import"
                    )

        #        if raw_buffer:
        #            raw_buffer.release()
        return

    load = import_data

    def export_data( self ):
        """Export data to a byte array."""
        klass = self.__class__

        # prevalidate all data before export.
        # this is important to ensure that any dependent fields
        # are updated beforehand, e.g. a count referenced
        # in a BlockField
        for name in klass._fields:
            self.scrub_field( name )
            self.validate_field( name )

        self.update_deps()

        output = bytearray( b"\x00" * self.get_size() )

        for name in klass._fields:
            klass._fields[name].update_buffer_with_value(
                self._field_data[name], output, parent=self
            )

        return output

    dump = export_data

    def update_deps( self ):
        """Update dependencies on all the fields on this Block instance."""
        klass = self.__class__

        for name in klass._checks:
            self.update_deps_on_check( name )

        for name in klass._fields:
            self.update_deps_on_field( name )
        return

    def validate( self ):
        """Validate all the fields on this Block instance."""
        klass = self.__class__

        for name in klass._fields:
            self.validate_field( name )
        return

    def set_dirty( self ):
        self._dirty = True
        if self._parent:
            self._parent.set_dirty()

    def recalculate_fields( self ):
        self._initial_load = True
        klass = self.__class__
        for field_name in klass._fields:
            self._field_size[field_name] = klass._fields[field_name].get_size(
                self._field_data[field_name], parent=self
            )
            self._field_start_offset[field_name] = klass._fields[
                field_name
            ].get_start_offset(self._field_data[field_name], parent=self)

        # precalculate size of whole block
        self._size = 0
        for field_name in klass._fields:
            self._size = max(
                self._size,
                self._field_start_offset[field_name] + self._field_size[field_name],
            )
        for check in klass._checks.values():
            self._size = max( self._size, check.get_end_offset( parent=self ) )
        self._dirty = False
        self._initial_load = False
        return

    def get_size( self ) -> int:
        """Get the projected size (in bytes) of the exported data from this Block instance."""
        if self._initial_load:
            klass = self.__class__
            size = 0
            for name in klass._fields:
                size = max(
                    size,
                    klass._fields[name].get_end_offset(
                        self._field_data[name], parent=self
                    ),
                )
            for check in klass._checks.values():
                size = max( size, check.get_end_offset( parent=self ) )
            return size

        if self._dirty:
            self.recalculate_fields()
        return self._size

    @property
    def _coda_offset( self ) -> int:
        # same as get_size, but assume there's no coda
        klass = self.__class__
        size = 0
        for name in klass._fields:
            if name in klass._coda_field_names:
                continue
            size = max(
                size,
                klass._fields[name].get_end_offset(
                    self._field_data[name], parent=self
                ),
            )
        for check in klass._checks.values():
            size = max( size, check.get_end_offset( parent=self ) )
        return size

    def get_field_obj( self, field_name: str ) -> Field:
        """Return a Field object associated with this Block class.

        field_name
            Name of the Field.
        """
        klass = self.__class__
        return klass._fields[field_name]

    def get_field_name_by_obj( self, field: Field ) -> str:
        """Return a name associated with a Field object in this Block class.

        field
            Field object on the object to reference.
        """
        klass = self.__class__
        return next( name for name, value in klass._fields.items() if value == field )

    def get_field_names( self ) -> list[str]:
        """Get the list of Fields associated with this Block class."""
        klass = self.__class__
        return list( klass._fields.keys() )

    def get_field_path( self, field: Field ) -> str:
        """Return the path of this Block and a child Field in the current object tree.

        Used for error messages.

        field
            Field object on the object to reference.
        """
        klass = self.__class__
        for field_name, field_obj in klass._fields.items():
            if field_obj == field:
                return f"{self.get_path()}.{field_name}"
        return f"{self.get_path()}.?"

    def get_path( self ) -> str:
        """Return the path of this Block in the current object tree.

        Used for error messages."""
        klass = self.__class__
        if self._parent is None:
            self._path_hint = f"<{klass.__name__}>"
        else:
            pklass = self._parent.__class__
            for field_name in pklass._fields.keys():
                if field_name in self._parent._field_data:
                    if self._parent._field_data[field_name] == self:
                        self._path_hint = f"{self._parent.get_path()}.{field_name}"
                    elif type( self._parent._field_data[field_name] ) == list:
                        for i, subobject in enumerate(
                            self._parent._field_data[field_name]
                        ):
                            if subobject == self:
                                self._path_hint = (
                                    f"{self._parent.get_path()}.{field_name}[{i}]"
                                )
                            elif hasattr( subobject, "obj" ) and subobject.obj == self:
                                self._path_hint = (
                                    f"{self._parent.get_path()}.{field_name}[{i}].obj"
                                )
        return self._path_hint if self._path_hint else ""

    def get_field_start_offset(
        self, field_name: str, index: int | None = None
    ) -> int:
        """Return the start offset of where a Field's data is to be stored in the Block.

        field_name
            Name of the Field to inspect.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        klass = self.__class__
        if self._initial_load or index is not None:
            return klass._fields[field_name].get_start_offset(
                self._field_data[field_name], parent=self, index=index
            )
        if self._dirty:
            self.recalculate_fields()
        return self._field_start_offset[field_name]

    def get_field_size( self, field_name: str, index: int | None = None ) -> int:
        """Return the size of a Field's data (in bytes).

        field_name
            Name of the Field to inspect.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        klass = self.__class__
        if self._initial_load or index is not None:
            return klass._fields[field_name].get_size(
                self._field_data[field_name], parent=self, index=index
            )
        if self._dirty:
            self.recalculate_fields()
        return self._field_size[field_name]

    def get_field_end_offset( self, field_name: str, index: int | None = None ) -> int:
        """Return the end offset of a Field's data. Useful for chainloading.

        field_name
            Name of the Field to inspect.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        klass = self.__class__
        if self._initial_load or index is not None:
            return klass._fields[field_name].get_end_offset(
                self._field_data[field_name], parent=self, index=index
            )
        if self._dirty:
            self.recalculate_fields()
        return self._field_start_offset[field_name] + self._field_size[field_name]

    def scrub_field( self, field_name: str ) -> Any:
        """Return a Field's data coerced to the correct type (if necessary).

        field_name
            Name of the Field to inspect.

        Throws FieldValidationError if value can't be coerced.
        """

        klass = self.__class__
        self._field_data[field_name] = klass._fields[field_name].scrub(
            self._field_data[field_name], parent=self
        )
        return self._field_data[field_name]

    def update_deps_on_field( self, field_name: str ):
        """Update all dependent variables derived from the value of a Field.

        field_name
            Name of the Field to inspect.
        """
        klass = self.__class__
        return klass._fields[field_name].update_deps(
            self._field_data[field_name], parent=self
        )

    def validate_field( self, field_name: str ):
        """Validate that a correctly-typed Python object meets the constraints for a Field.

        field_name
            Name of the Field to inspect.

        Throws FieldValidationError if a constraint fails.

        """
        klass = self.__class__
        return klass._fields[field_name].validate(
            self._field_data[field_name], parent=self
        )

    def update_deps_on_check( self, check_name: str ):
        """Update all dependent variables derived from a Check.

        check_name
            Name of the Check to inspect.
        """

        klass = self.__class__
        return klass._checks[check_name].update_deps( parent=self )

    def hexdump(
        self,
        *,
        start: int | None = None,
        end: int | None = None,
        length: int | None = None,
        major_len: int = 8,
        minor_len: int = 4,
        colour: bool = True,
        address_base: int | None = None,
        show_offsets: bool = True,
        show_glyphs: bool = True,
    ):
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
            self.export_data(),
            start=start,
            end=end,
            length=length,
            major_len=major_len,
            minor_len=minor_len,
            colour=colour,
            address_base=address_base,
            show_offsets=show_offsets,
            show_glyphs=show_glyphs,
        )

    def histdump(
        self,
        *,
        start: int | None = None,
        end: int | None = None,
        length: int | None = None,
        samples: int = 0x10000,
        width: int = 64,
        address_base: int | None = None,
    ):
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
            self.export_data(),
            start=start,
            end=end,
            length=length,
            samples=samples,
            width=width,
            address_base=address_base,
        )

    def search(
        self,
        pattern: str,
        *,
        encoding: str = "utf8",
        fixed_string: bool = False,
        hex_format: bool = False,
        ignore_case: bool = False,
    ):
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
        return [
            x
            for x in utils.search_iter(
                pattern,
                source,
                prefix=f"<{self.__class__.__name__}>",
                depth=None,
                encoding=encoding,
                fixed_string=fixed_string,
                hex_format=hex_format,
                ignore_cast=ignore_case,
            )
        ]

    def diffdump( self, target, prefix="source", depth=None ):
        """Find differences between this Block and another.

        target
            The second Block.

        prefix
            The name of the base element to display.

        depth
            Maximum number of levels to traverse.
        """
        return utils.objdiffdump( self, target, prefix, depth )
