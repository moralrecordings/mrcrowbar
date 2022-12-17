"""Definition classes for common fields in binary formats."""
from __future__ import annotations

import logging
from typing_extensions import TypedDict
from mrcrowbar.transforms import Transform

logger = logging.getLogger( __name__ )

from enum import IntEnum
from typing import (
    Any,
    Callable,
    NamedTuple,
    Sequence,
    Tuple,
    List,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from mrcrowbar.blocks import Block

from mrcrowbar.refs import Ref, Chain, property_get, property_set
from mrcrowbar import common, encoding

OffsetType = Union[int, Ref[int]]


class FieldDefinitionError( Exception ):
    pass


class ParseError( Exception ):
    pass


class FieldValidationError( Exception ):
    pass


class EmptyFieldError( Exception ):
    pass


StopCheckType = Callable[[common.BytesReadType, int], bool]


class Field( object ):
    def __init__( self, *, default: Any = None ):
        """Base class for Fields.

        default
            Default value to emit in the case of e.g. creating an empty Block.
        """
        self._position_hint = next( common.next_position_hint )
        self.default = default

    def __repr__( self ):
        desc = f"0x{id( self ):016x}"
        if hasattr( self, "repr" ) and isinstance( self.repr, str ):
            desc = self.repr
        return f"<{self.__class__.__name__}: {desc}>"

    @property
    def repr( self ):
        """Plaintext summary of the Field."""
        return None

    @property
    def serialised( self ) -> common.SerialiseType:
        """Tuple containing the contents of the Field."""
        return common.serialise( self, tuple() )

    def __hash__( self ) -> int:
        serial = self.serialised
        if serial is None:
            return super().__hash__()
        return hash( self.serialised )

    def __eq__( self, other: Any ) -> bool:
        serial = self.serialised
        if serial is None:
            return super().__eq__( other )
        return self.serialised == other.serialised

    # Overrides to disable the type checker!
    # Unfortunately the expected input/output types
    # for Fields are a little bit too dynamic to lock down
    # with generics. Even if there was some way of dynamically
    # changing the output type with overload signatures
    # (like TypeScript lets you do), I feel there'd need to be
    # a class split between single and array types, as too many
    # attributes can be changed at runtime with Refs.
    def __get__( self, instance: Block, owner: Any ) -> Any:
        ...

    def __set__( self, instance: Block, value: Any ) -> None:
        ...

    def get_from_buffer(
        self, buffer: common.BytesReadType, parent: Optional[Block] = None
    ) -> Any:
        """Create a Python object from a byte string, using the field definition.

        buffer
            Input byte string to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return None

    def update_buffer_with_value(
        self, value: Any, buffer: common.BytesWriteType, parent: Optional[Block] = None
    ):
        """Write a Python object into a byte array, using the field definition.

        value
            Input Python object to process.

        buffer
            Output byte array to encode value into.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        self.validate( value, parent )

    def get_start_offset(
        self, value: Any, parent: Optional[Block] = None, index: Optional[int] = None
    ) -> int:
        """Return the start offset of where the Field's data is to be stored in the Block.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        return 0

    def get_size(
        self, value: Any, parent: Optional[Block] = None, index: Optional[int] = None
    ) -> int:
        """Return the size of the Field's data (in bytes).

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        return 0

    def get_end_offset(
        self, value: Any, parent: Optional[Block] = None, index: Optional[int] = None
    ) -> int:
        """Return the end offset of the Field's data. Useful for chainloading.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        return self.get_start_offset( value, parent, index ) + self.get_size(
            value, parent, index
        )

    def scrub( self, value: Any, parent: Optional[Block] = None ) -> Any:
        """Return the value coerced to the correct type of the Field (if necessary).

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.

        Throws FieldValidationError if value can't be coerced.
        """
        return value

    def update_deps( self, value: Any, parent: Optional[Block] = None ):
        """Update all dependent variables derived from the value of the Field.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return

    def validate( self, value: Any, parent: Optional[Block] = None ):
        """Validate that a correctly-typed Python object meets the constraints for the Field.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.

        Throws FieldValidationError if a constraint fails.
        """
        pass

    def serialise( self, value: Any, parent: Optional[Block] = None ):
        """Return a value as basic Python types.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return None

    def get_path(
        self, parent: Optional[Block] = None, index: Optional[int] = None
    ) -> str:
        """Return the location in the Block tree.

        parent
            Parent block object where this Field is defined.

        index
            Index into the value of the Field.
        """
        suffix = f"[{index}]" if index is not None else ""
        if not parent:
            return f"<{self.__class__.__name__}>{suffix}"
        return parent.get_field_path( self ) + suffix

    def get_strict( self, parent: Optional[Block] = None ):
        """Return whether the parent Block is loading in strict mode.

        parent
            Parent block object where this Field is defined.
        """
        if not parent:
            return False
        return parent._strict

    def get_cache_refs( self, parent: Optional[Block] = None ):
        """Return whether the parent Block is pre-caching all the Refs.

        parent
            Parent block object where this Field is defined.
        """
        if parent is None:
            return False
        return parent._cache_refs


class StreamField( Field ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: Any = None,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ):
        """Base class for accessing one or more streamable elements.

        offset
            Position of data, relative to the start of the parent block. Defaults to
            the end offset of the previous field.

        default
            Default value to emit in the case of e.g. creating an empty Block.

        count
            Load multiple elements. None implies a single value, non-negative
            numbers will return a Python list.

        length
            Maximum size of the buffer to read in.

        end_offset
            Maximum end offset of the buffer to read in.

        stream
            Read elements continuously until a stop condition is met. Defaults to False.

        alignment
            Number of bytes to align the start of each element to.

        stream_end
            Byte pattern to denote the end of the stream.

        stop_check
            A function that takes a data buffer and an offset; should return True if
            the end of the data stream has been reached and False otherwise.

        exists
            True if this Field should be parsed and generate values, False if it should be skipped.
            Can be set programmatically as a Ref. Defaults to True.
        """
        if count is not None and default is None:
            default = []
        super().__init__( default=default )
        self.offset = offset
        self.count = count
        if length is not None and end_offset is not None:
            raise FieldDefinitionError( f"Can't define both length and end_offset!" )
        self.length = length
        self.end_offset = end_offset
        self.stream = stream
        self.alignment = alignment
        if stream_end is not None:
            if not common.is_bytes( stream_end ):
                raise FieldDefinitionError(
                    f"stream_end must be of type bytes, not {stream_end.__class__}!"
                )
        self.stream_end = stream_end
        self.stop_check = stop_check
        self.exists = exists

    def get_element_from_buffer(
        self,
        offset: int,
        buffer: common.BytesReadType,
        parent: Optional[Block] = None,
        index: Optional[int] = None,
    ) -> Any:
        return None  # pass

    def get_from_buffer(
        self, buffer: common.BytesReadType, parent: Optional["Block"] = None
    ) -> Union[Any, List[Any]]:
        if not common.is_bytes( buffer ):
            raise ParseError(
                f"{self.get_path( parent )}: buffer needs to be of type bytes, not {buffer.__class__}!"
            )
        offset = property_get( self.offset, parent, caller=self )
        if offset is None:
            raise ParseError(
                f"{self.get_path( parent )}: offset parameter must be defined!"
            )
        count = property_get( self.count, parent )
        length = property_get( self.length, parent )
        end_offset = property_get( self.end_offset, parent )
        stream = property_get( self.stream, parent )
        alignment = property_get( self.alignment, parent )
        exists = property_get( self.exists, parent )

        # If we're using end_offset, convert it to a length
        if end_offset is not None:
            length = end_offset - offset

        if not exists:
            return None

        is_array = stream or (count is not None)
        count = count if is_array else 1
        if count is not None:
            if count < 0:
                raise ParseError(
                    f"{self.get_path( parent )}: count can't be less than zero"
                )
        if length is not None:
            buffer = buffer[: offset + length]

        pointer = offset
        result: List[Any] = []
        while pointer < len( buffer ):
            start_offset = pointer
            # stop if we've hit the maximum number of items
            if not stream and (len( result ) == count):
                break
            # run the stop check (if exists): if it returns true, we've hit the end of the stream
            if self.stop_check and (self.stop_check( buffer, pointer )):
                break
            # stop if we find the end of stream marker
            if (
                self.stream_end is not None
                and buffer[pointer : pointer + len( self.stream_end )]
                == self.stream_end
            ):
                break

            element, end_offset = self.get_element_from_buffer(
                pointer, buffer, parent, index=len( result ) if is_array else None
            )
            result.append( element )
            pointer = end_offset

            # if an alignment is set, do some aligning
            if alignment is not None:
                width = (pointer - start_offset) % alignment
                if width:
                    pointer += alignment - width

        if not is_array:
            if not result:
                # in the case of an empty result for a non-array, attempt to fetch one record.
                # this will only work if the resulting element is of size 0.
                try:
                    result, _ = self.get_element_from_buffer(
                        pointer, buffer, parent, index=0
                    )
                except Exception:
                    raise EmptyFieldError(
                        f"{self.get_path( parent )}: No data could be extracted"
                    )
            else:
                return result[0]
        return result

    def update_buffer_with_element(
        self,
        offset: int,
        element: Any,
        buffer: common.BytesWriteType,
        parent: Optional[Block] = None,
        index: Optional[int] = None,
    ) -> int:
        return 0

    def update_buffer_with_value(
        self,
        value: Union[Any, Sequence[Any]],
        buffer: common.BytesWriteType,
        parent: Optional[Block] = None,
    ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent, caller=self )
        if offset is None:
            raise ParseError(
                f"{self.get_path( parent )}: offset parameter must be defined!"
            )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        alignment = property_get( self.alignment, parent )
        exists = property_get( self.exists, parent )

        if not exists:
            return

        is_array = stream or (count is not None)

        if is_array:
            try:
                _ = iter( value )
            except TypeError:
                raise FieldValidationError(
                    f"{self.get_path( parent )}: Type {type( value )} not iterable"
                )
            if count is not None:
                if not len( value ) <= count:
                    raise FieldValidationError(
                        f"{self.get_path( parent )}: list length not less than or equal to { count }"
                    )
        else:
            value = [value]

        pointer: int = offset
        for index, element in enumerate( value ):
            start_offset = pointer
            end_offset = self.update_buffer_with_element(
                pointer, element, buffer, parent, index=index if is_array else None
            )
            pointer = end_offset

            if alignment is not None:
                width = (pointer - start_offset) % alignment
                if width:
                    pointer += alignment - width

        new_size = pointer
        if self.stream_end is not None:
            new_size += len( self.stream_end )

        if len( buffer ) < new_size:
            buffer.extend( b"\x00" * (new_size - len( buffer )) )

        if self.stream_end is not None:
            buffer[new_size - len( self.stream_end ) : new_size] = self.stream_end

    def update_deps(
        self, value: Union[Any, Sequence[Any]], parent: Optional[Block] = None
    ):
        offset = property_get( self.offset, parent, caller=self )
        count = property_get( self.count, parent )
        length = property_get( self.length, parent )
        end_offset = property_get( self.end_offset, parent )
        exists = property_get( self.exists, parent )

        if exists and value is None:
            if not isinstance( self.exists, Ref ):
                # non-programmatic exists gets a free pass
                pass
            elif isinstance( exists, int ):
                property_set( self.exists, parent, 1 )
            elif isinstance( exists, bool ):
                property_set( self.exists, parent, True )
        elif not exists and value is not None:
            if not isinstance( self.exists, Ref ):
                raise FieldValidationError(
                    "f{self.get_path( parent )}: Attribute exists is a constant, can't set!"
                )
            elif isinstance( exists, int ):
                property_set( self.exists, parent, 0 )
            elif isinstance( exists, bool ):
                property_set( self.exists, parent, False )

        if count is not None and count != len( value ):
            property_set( self.count, parent, len( value ) )
        target_length = self.get_size( value, parent )

        if end_offset is not None and (end_offset - offset) != target_length:
            property_set( self.end_offset, parent, offset + target_length )

        if length is not None and length != target_length:
            property_set( self.length, parent, target_length )

    def validate_element(
        self, element: Any, parent: Optional[Block] = None, index: Optional[int] = None
    ):
        pass

    def validate(
        self, value: Union[Any, Sequence[Any]], parent: Optional[Block] = None
    ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        exists = property_get( self.exists, parent )

        if exists is not None and not isinstance( exists, (int, bool) ):
            raise FieldValidationError(
                f"{self.get_path( parent )}: Exists only supports int or bool. To control with other types, use a Ref pointing to a property."
            )

        # for the case where exists=True without a ref, allow None
        # to fall through to validate_element.
        # however if exists=False without a ref, that's a problem.
        if exists == False:
            if value is not None:
                if not isinstance( self.exists, Ref ):
                    raise FieldValidationError(
                        f"{self.get_path( parent )}: Exists defined as a constant, was expecting None but got {value}!"
                    )
            else:
                return

        is_array = stream or (count is not None)
        if is_array:
            try:
                _ = iter( value )
            except TypeError:
                raise FieldValidationError(
                    f"{self.get_path( parent )}: Type {type( value )} not iterable"
                )
            if (
                count is not None
                and (not isinstance( self.count, Ref ))
                and (len( value ) != count)
            ):
                raise FieldValidationError(
                    f"{self.get_path( parent )}: Count defined as a constant, was expecting {count} list entries but got {len( value )}!"
                )
        else:
            value = [value]

        for index, element in enumerate( value ):
            self.validate_element(
                element, parent=parent, index=index if is_array else None
            )

    def get_element_size(
        self, element: Any, parent: Optional[Block] = None, index: Optional[int] = None
    ) -> int:
        return 0  # pass

    def get_start_offset(
        self,
        value: Union[Any, Sequence[Any]],
        parent: Optional[Block] = None,
        index: Optional[int] = None,
    ) -> int:
        offset = property_get( self.offset, parent, caller=self )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        alignment = property_get( self.alignment, parent )
        exists = property_get( self.exists, parent )
        is_array = stream or (count is not None)

        pointer = offset
        if exists and index is not None:
            if not is_array:
                raise IndexError(
                    f"{self.get_path( parent )}: Can't use index for a non-array"
                )
            elif index not in range( len( value ) ):
                raise IndexError(
                    f"{self.get_path( parent )}: Index {index} is not within range( 0, {len( value )} )"
                )
            for el_index, element in enumerate( value[:index] ):
                start_offset = pointer
                pointer += self.get_element_size(
                    element, parent, index=el_index if is_array else None
                )
                # if an alignment is set, do some aligning
                if alignment is not None:
                    width = (pointer - start_offset) % alignment
                    if width:
                        pointer += alignment - width

        return pointer

    def get_size(
        self,
        value: Union[Any, Sequence[Any]],
        parent: Optional[Block] = None,
        index: Optional[int] = None,
    ) -> int:
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        alignment = property_get( self.alignment, parent )
        exists = property_get( self.exists, parent )
        is_array = stream or (count is not None)

        pointer = 0

        if not exists:
            return pointer

        if index is not None:
            if not is_array:
                raise IndexError(
                    f"{self.get_path( parent )}: Can't use index for a non-array"
                )
            elif index not in range( 0, len( value ) ):
                raise IndexError(
                    f"{self.get_path( parent )}: Index {index} is not within range( 0, {len( value )} )"
                )
            value = [value[index]]
        else:
            value = value if is_array else [value]

        for el_index, element in enumerate( value ):
            start_offset = pointer
            pointer += self.get_element_size(
                element, parent, index=el_index if is_array else None
            )
            # if an alignment is set, do some aligning
            if alignment is not None:
                width = (pointer - start_offset) % alignment
                if width:
                    pointer += alignment - width

        if self.stream_end is not None:
            pointer += len( self.stream_end )

        return pointer


class ChunkBase( NamedTuple ):
    id: Union[int, bytes]
    obj: Block


class Chunk( ChunkBase ):
    @property
    def serialised( self ) -> common.SerialiseType:
        """Tuple containing the contents of the Chunk."""
        klass = self.__class__
        return (
            (klass.__module__, klass.__name__),
            (
                ("id", self.id),
                ("obj", self.obj.serialised if self.obj is not None else None),
            ),
        )


class ChunkField( StreamField ):
    def __init__(
        self,
        chunk_map: Dict[Union[bytes, int], Type[Block]],
        offset: OffsetType = Chain(),
        *,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = True,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        default_klass: Optional[Type[Block]] = None,
        id_size: Optional[int] = None,
        id_field: Optional[Type[Field]] = None,
        id_enum: Optional[IntEnum] = None,
        length_field: Optional[Type[NumberField]] = None,
        fill: Optional[bytes] = None,
        length_inclusive: bool = False,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
        length_before_id: bool = False,
    ):
        """Field for inserting a tokenised Block stream into the parent class.

        chunk_map
            A dict mapping between the chunk ID and the Block class to interpret the payload as.

        offset
            Position of data, relative to the start of the parent block. Defaults to
            the end offset of the previous field.

        count
            Load multiple chunks. None implies a single value, non-negative
            numbers will return a Python list.

        length
            Maximum size of the buffer to read in.

        end_offset
            Maximum end offset of the buffer to read in.

        stream
            Read elements continuously until a stop condition is met. Defaults to True.

        alignment
            Number of bytes to align the start of each Chunk to.

        stream_end
            Byte pattern to denote the end of the stream.

        stop_check
            A function that takes a data buffer and an offset; should return True if
            the end of the data stream has been reached and False otherwise.

        default_klass
            Fallback Block class to use if there's no match with the chunk_map mapping.

        id_size
            Size in bytes of the Chunk ID.

        id_field
            Field class used to parse Chunk ID. Defaults to Bytes.

        id_enum
            Restrict allowed values for Chunk ID to those provided by a Python enum type. Used for validation.

        length_field
            Field class used to parse the Chunk data length. For use when a Chunk consists of an ID followed by the size of the data.

        fill
            Exact byte sequence that denotes an empty Chunk object.

        length_inclusive
            True if the length field indicates the total length of the chunk, inclusive of the ID field and the length field.
            Defaults to False (i.e. length of the data only).

        exists
            True if this Field should be parsed and generate values, False if it should be skipped.
            Can be set programmatically as a Ref. Defaults to True.

        length_before_id
            True if the length field appears in the chunk before the ID field.
            Defaults to False.
        """

        super().__init__(
            offset=offset,
            default=None,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            exists=exists,
        )
        self.chunk_map = chunk_map
        if length_field:
            if not issubclass( length_field, NumberField ):
                raise FieldDefinitionError(
                    f"length_field must be a subclass of NumberField, not {length_field}!"
                )
            self.length_field = length_field( 0x00 )
        else:
            self.length_field = None
        self.length_inclusive = length_inclusive
        if id_field:
            if not issubclass( id_field, (NumberField) ):
                raise FieldDefinitionError(
                    f"id_field must be a subclass of NumberField, not {id_field}!"
                )
            if id_enum:
                self.id_field = id_field( 0x00, enum=id_enum )
            else:
                self.id_field = id_field( 0x00 )
        else:
            self.id_field = None
        self.default_klass = default_klass

        self.id_size = id_size
        self.fill = fill
        self.length_before_id = length_before_id

    def get_element_from_buffer( self, offset, buffer, parent=None, index=None ):
        chunk_map = property_get( self.chunk_map, parent )
        fill = property_get( self.fill, parent )

        def get_chunk_id( pointer: int ):
            if self.id_field:
                chunk_id = self.id_field.get_from_buffer(
                    buffer[pointer:], parent=parent
                )
                pointer += self.id_field.field_size
            elif self.id_size:
                chunk_id = buffer[pointer : pointer + self.id_size]
                pointer += len( chunk_id )
            else:
                for test_id in chunk_map:
                    if buffer[pointer:].startswith( test_id ):
                        chunk_id = test_id
                        break
                if not chunk_id:
                    raise ParseError(
                        f"{self.get_path( parent, index )}: Could not find matching chunk at offset {pointer}"
                    )
                pointer += len( chunk_id )
            return chunk_id, pointer

        def get_chunk_length( pointer: int ):
            chunk_length = None
            if self.length_field:
                chunk_length = self.length_field.get_from_buffer(
                    buffer[pointer:], parent=parent
                )
                pointer += self.length_field.field_size
            return chunk_length, pointer

        def constructor( source_data ):
            try:
                block = chunk_klass(
                    source_data=source_data,
                    parent=parent,
                    cache_bytes=parent._cache_bytes,
                    path_hint=self.get_path( parent, index ),
                    strict=self.get_strict( parent ),
                    cache_refs=self.get_cache_refs( parent ),
                )
            except Exception as e:
                if self.get_strict( parent ):
                    raise e
                else:
                    logger.warning(
                        f"{self.get_path( parent, index )}: failed to create Block ({chunk_klass}) for Chunk {chunk_id}, falling back to Unknown"
                    )
                    logger.warning( f'{self.get_path( parent, index )}: "{str( e )}"' )
                    from mrcrowbar.unknown import Unknown

                    block = Unknown(
                        source_data=source_data,
                        parent=parent,
                        cache_bytes=parent._cache_bytes,
                        path_hint=self.get_path( parent, index ),
                        strict=self.get_strict( parent ),
                        cache_refs=self.get_cache_refs( parent ),
                    )
            return block

        pointer = offset
        chunk_id = None
        chunk_length = None

        if self.length_before_id:
            chunk_length, pointer = get_chunk_length( pointer )
            chunk_id, pointer = get_chunk_id( pointer )
        else:
            chunk_id, pointer = get_chunk_id( pointer )
            chunk_length, pointer = get_chunk_length( pointer )

        if chunk_id in chunk_map:
            chunk_klass = chunk_map[chunk_id]
        elif self.default_klass:
            chunk_klass = self.default_klass
        else:
            raise ParseError(
                f"{self.get_path( parent, index )}: No chunk class match for ID {chunk_id}"
            )

        if chunk_length is not None:
            if self.length_inclusive:
                chunk_length -= pointer - offset
            chunk_buffer = buffer[pointer : pointer + chunk_length]
            pointer += chunk_length
            if chunk_buffer == fill:
                result = Chunk( id=chunk_id, obj=None )
                return result, pointer
            chunk = constructor( chunk_buffer )
        else:
            chunk = constructor( buffer[pointer:] )
            pointer += chunk.get_size()
        result = Chunk( id=chunk_id, obj=chunk )

        return result, pointer

    def update_buffer_with_element(
        self, offset, element, buffer, parent=None, index=None
    ) -> int:
        chunk_map = property_get( self.chunk_map, parent )
        fill = property_get( self.fill, parent )
        alignment = property_get( self.alignment, parent )

        def add_chunk_id( data ):
            if self.id_field:
                id_buf = bytearray( b"\x00" * self.id_field.field_size )
                self.id_field.update_buffer_with_value(
                    element.id, id_buf, parent=parent
                )
                data.extend( id_buf )
            else:
                data.extend( element.id )

        def add_chunk_length( data, payload ):
            if self.length_field:
                length_buf = bytearray( b"\x00" * self.length_field.field_size )
                size = len( payload )
                if self.length_inclusive:
                    size += len( length_buf )
                    size += (
                        self.id_field.field_size if self.id_field else len( element.id )
                    )
                width = size % alignment
                if width:
                    size += alignment - width
                self.length_field.update_buffer_with_value(
                    size, length_buf, parent=parent
                )
                data.extend( length_buf )

        if element.obj is None:
            if fill is not None:
                payload = fill
            else:
                raise ValueError(
                    f"{self.get_path( parent, index )}: Object part of Chunk can't be None unless there's a fill pattern set"
                )
        else:
            payload = element.obj.export_data()

        data = bytearray()
        if self.length_before_id:
            add_chunk_length( data, payload )
            add_chunk_id( data )
        else:
            add_chunk_id( data )
            add_chunk_length( data, payload )
        data += payload

        if len( buffer ) < offset + len( data ):
            buffer.extend( b"\x00" * (offset + len( data ) - len( buffer )) )
        buffer[offset : offset + len( data )] = data
        return offset + len( data )

    def validate_element( self, element, parent=None, index=None ):
        from mrcrowbar.unknown import Unknown

        chunk_map = property_get( self.chunk_map, parent )
        fill = property_get( self.fill, parent )

        if not isinstance( element, Chunk ):
            raise FieldValidationError(
                f"{self.get_path( parent, index )}: Element {element} is not of type Chunk!"
            )
        chunk_klass: Optional[Type[Block]] = None
        if element.id in chunk_map:
            chunk_klass = chunk_map[element.id]
        elif self.default_klass:
            chunk_klass = self.default_klass

        if element.obj is None:
            if fill is None:
                raise FieldValidationError(
                    f"{self.get_path( parent, index )}: Can't pass a Chunk with an empty object to a ChunkField when the fill pattern isn't defined!"
                )
        else:
            if not isinstance( element.obj, chunk_klass ):
                if isinstance( element.obj, Unknown ):
                    if self.get_strict( parent ):
                        raise FieldValidationError(
                            f"{self.get_path( parent, index )}: ChunkMap expected Block type {chunk_klass}, received Unknown; can't accept Unknown blocks when loaded in strict mode!"
                        )
                else:
                    raise FieldValidationError(
                        f"{self.get_path( parent, index )}: ChunkMap expected Block type {chunk_klass}, received {element.obj.__class__}!"
                    )

        if self.id_size:
            if len( element.id ) != self.id_size:
                raise FieldValidationError(
                    f"{self.get_path( parent, index )}: Chunk id is of size {len( element.id )}, expected {self.id_size}!"
                )

    def get_element_size( self, element, parent=None, index=None ):
        fill = property_get( self.fill, parent )

        size = 0
        if self.id_field:
            size += self.id_field.field_size
        else:
            size += len( element.id )
        if self.length_field:
            size += self.length_field.field_size
        if element.obj is None:
            size += len( fill )
        else:
            size += element.obj.get_size()
        return size

    def serialise( self, value, parent=None ):
        self.validate( value, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)
        if is_array:
            return (
                ("builtins", "list"),
                tuple( (a, b.serialised if b is not None else None) for a, b in value ),
            )
        return (value[0], value[1].serialised if value is not None else None)


class BlockField( StreamField ):
    def __init__(
        self,
        block_klass: Union[Type[Block], Dict[Any, Type[Block]]],
        offset: OffsetType = Chain(),
        *,
        block_kwargs: Optional[Dict[str, Any]] = None,
        count: Optional[Union[int, Ref[int]]] = None,
        fill: Optional[bytes] = None,
        block_type: Optional[Ref[Any]] = None,
        default_klass: Optional[Type[Block]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        transform: Optional[Transform] = None,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ):
        """Field for inserting another Block into the parent class.

        block_klass
            Block class to use, or a dict mapping between type and block class.

        offset
            Position of data, relative to the start of the parent block. Defaults to
            the end offset of the previous field.

        block_kwargs
            Arguments to be passed to the constructor of the block class.

        count
            Load multiple Blocks. None implies a single value, non-negative
            numbers will return a Python list.

        fill
            Exact byte sequence that denotes an empty entry in a list.

        block_type
            Key to use with the block_klass mapping. (Usually a Ref for a property on the parent block)

        default_klass
            Fallback Block class to use if there's no match with the block_klass mapping.

        length
            Maximum size of the buffer to read in.

        end_offset
            Maximum end offset of the buffer to read in.

        stream
            Read Blocks continuously until a stop condition is met.

        alignment
            Number of bytes to align the start of each Block to.

        transform
            Transform class to use for preprocessing the data before importing or
            exporting each Block.

        stream_end
            Byte pattern to denote the end of the stream.

        stop_check
            A function that takes a data buffer and an offset; should return True if
            the end of the data stream has been reached and False otherwise.

        exists
            True if this Field should be parsed and generate values, False if it should be skipped.
            Can be set programmatically as a Ref. Defaults to True.

        """
        super().__init__(
            offset=offset,
            default=None,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            exists=exists,
        )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.block_type = block_type
        # TODO: support different args if using a switch
        self.fill = fill
        self.default_klass = default_klass
        self.transform = transform

    def get_element_from_buffer( self, offset, buffer, parent=None, index=None ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        fill = property_get( self.fill, parent )
        klass = self.get_klass( parent )

        def constructor( source_data ):
            try:
                block = klass(
                    source_data=source_data,
                    parent=parent,
                    cache_bytes=parent._cache_bytes,
                    path_hint=self.get_path( parent, index ),
                    strict=self.get_strict( parent ),
                    cache_refs=self.get_cache_refs( parent ),
                    **self.block_kwargs,
                )
            except Exception as e:
                if self.get_strict( parent ):
                    raise e
                else:
                    logger.warning(
                        f"{self.get_path( parent, index )}: failed to create Block ({klass}), falling back to Unknown"
                    )
                    logger.warning( f'{self.get_path( parent, index )}: "{str( e )}"' )
                    from mrcrowbar.unknown import Unknown

                    block = Unknown(
                        source_data=source_data,
                        parent=parent,
                        cache_bytes=parent._cache_bytes,
                        path_hint=self.get_path( parent, index ),
                        strict=self.get_strict( parent ),
                        cache_refs=self.get_cache_refs( parent ),
                        **self.block_kwargs,
                    )
            return block

        # add an empty list entry if we find the fill pattern
        if fill and buffer[offset : offset + len( fill )] == fill:
            return None, offset + len( fill )
        # if we have an inline transform, apply it
        elif self.transform:
            data = self.transform.import_data( buffer[offset:], parent=parent )
            block = constructor( data.payload )
            return block, offset + data.end_offset
        # otherwise, create a block
        block = constructor( buffer[offset:] )
        size = block.get_size()
        if size == 0:
            if stream:
                raise ParseError(
                    f"{self.get_path( parent, index )}: Can't stream 0 byte Blocks ({klass}) from a BlockField"
                )
            elif count and len( result ) == 0:
                logger.warning(
                    f"{self.get_path( parent, index )}: copying 0 byte Blocks ({klass}) from a BlockField, this is probably not what you want"
                )

        return block, offset + size

    def update_buffer_with_element(
        self, offset, element, buffer, parent=None, index=None
    ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        fill = property_get( self.fill, parent )

        klass = self.get_klass( parent )

        if element is None:
            if fill:
                data = fill
            else:
                raise ParseError(
                    f"{self.get_path( parent, index )}: A fill pattern needs to be specified to use None as a list entry"
                )
        else:
            data = element.export_data()
            if self.transform:
                data = self.transform.export_data( data, parent=parent ).payload
        if len( buffer ) < offset + len( data ):
            buffer.extend( b"\x00" * (offset + len( data ) - len( buffer )) )
        buffer[offset : offset + len( data )] = data
        return offset + len( data )

    def update_deps( self, value, parent=None ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        exists = property_get( self.exists, parent )

        is_array = stream or (count is not None)

        if exists == True and count is not None and count != len( value ):
            property_set( self.count, parent, len( value ) )

        if not is_array or exists == False:
            value = [value]

        for element in value:
            if element is not None:
                element.update_deps()

    def validate_element(
        self, element: Any, parent: Optional[Block] = None, index: Optional[int] = None
    ):
        from mrcrowbar.unknown import Unknown

        klass = self.get_klass( parent )
        if element is not None:
            test = isinstance( element, klass )
            if not self.get_strict( parent ):
                test = test or isinstance( element, Unknown )
            if not test:
                raise FieldValidationError(
                    f"{self.get_path( parent, index )}: Expecting block class {klass}, not {type( element )}"
                )

    def get_element_size(
        self, element: Any, parent: Optional[Block] = None, index: Optional[int] = None
    ):
        fill = property_get( self.fill, parent )
        if self.transform:
            data = self.transform.export_data(
                element.export_data(), parent=parent
            ).payload
            return len( data )
        elif element is None:
            if fill:
                return len( fill )
            else:
                raise ParseError(
                    f"{self.get_path( parent, index )}: A fill pattern needs to be specified to use None as a list entry"
                )
        else:
            return element.get_size()

    def get_klass( self, parent=None ):
        block_klass = property_get( self.block_klass, parent )
        if isinstance( block_klass, dict ):
            block_type = property_get( self.block_type, parent )
            if block_type in block_klass:
                return block_klass[block_type]
            elif self.default_klass:
                return self.default_klass
            else:
                raise ParseError(
                    f"{self.get_path( parent )}: No block klass match for type {block_type}"
                )
        return block_klass

    def serialise( self, value, parent=None ):
        self.validate( value, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        exists = property_get( self.exists, parent )
        if exists == False:
            return None
        is_array = stream or (count is not None)
        if is_array:
            return (
                ("builtins", "list"),
                tuple( x.serialised if x is not None else None for x in value ),
            )
        return value.serialised if value is not None else None


class StringField( StreamField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: Any = None,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        transform: Optional[Transform] = None,
        encoding: Optional[str] = None,
        length_field: Optional[Type[NumberField]] = None,
        fill: Optional[bytes] = None,
        element_length: Optional[int] = None,
        element_end: Optional[bytes] = None,
        zero_pad: bool = False,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ):
        """Field class for string data.

        offset
            Position of data, relative to the start of the parent block. Defaults to
            the end offset of the previous field.

        default
            Default value to emit in the case of e.g. creating an empty block.

        count
            Load multiple strings. None implies a single value, non-negative
            numbers will return a Python list.

        length
            Maximum size of the buffer to read in.

        end_offset
            Maximum end offset of the buffer to read in.

        stream
            Read strings continuously until a stop condition is met. Defaults to False.

        alignment
            Number of bytes to align the start of the next element to.

        stream_end
            Byte string to indicate the end of the data.

        stop_check
            A function that takes a data buffer and an offset; should return True if
            the end of the data stream has been reached and False otherwise.

        transform
            Transform class to use for preprocessing the data before importing or
            exporting each string.

        encoding
            Python string encoding to use for output, as accepted by bytes.decode().

        length_field
            Field class used to parse the string length. For use when a string is preceded by
            the size.

        fill
            Exact byte sequence that denotes an empty entry in a list.

        element_length
            Length of each string element to load.

        element_end
            Byte string to indicate the end of a single string element.

        zero_pad
            Pad each element with zeros to match the length. Only for use with fixed
            length elements. The data size must be up to or equal to the length.
            Defaults to False.

        exists
            True if this Field should be parsed and generate values, False if it should be skipped.
            Can be set programmatically as a Ref. Defaults to True.

        """
        super().__init__(
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            exists=exists,
        )

        if count is not None:
            if stream:
                raise FieldDefinitionError( "Can't define both count and stream!" )
            if not (
                (element_length is not None)
                or (length_field is not None)
                or (element_end is not None)
            ):
                raise FieldDefinitionError(
                    "Given that count is defined, at least one of element_length, length_field and element_end must be defined!"
                )

        elif stream:
            if not (
                (element_length is not None)
                or (length_field is not None)
                or (element_end is not None)
            ):
                raise FieldDefinitionError(
                    "Given that stream is defined, at least one of element_length, length_field and element_end must be defined!"
                )

        else:  # single element
            pass

        if zero_pad:
            if element_length is None:
                raise FieldDefinitionError(
                    "Given that zero_pad is defined, element_length must be defined!"
                )

        if length_field:
            if element_length is not None:
                raise FieldDefinitionError(
                    "Can't define both length_field and element_length!"
                )
            if not issubclass( length_field, NumberField ):
                raise FieldDefinitionError(
                    f"length_field must be a subclass of NumberField, not {length_field}!"
                )
            self.length_field = length_field( 0x00 )
        else:
            self.length_field = None

        self.transform = transform
        self.zero_pad = zero_pad
        self.encoding = encoding
        self.fill = fill
        self.element_length = element_length
        if element_end:
            if not common.is_bytes( element_end ):
                raise FieldDefinitionError(
                    f"element_end must be of type bytes, not {element_end.__class__}!"
                )
        self.element_end = element_end

    def _scrub_bytes( self, value, parent=None ):
        fill = property_get( self.fill, parent )
        encoding = property_get( self.encoding, parent )
        data = value

        if data is None:
            if fill:
                return fill
            else:
                raise ParseError(
                    f"{self.get_path( parent )}: A fill pattern needs to be specified to use None as a list entry"
                )

        if encoding:
            data = data.encode( encoding )
        if self.transform:
            data = self.transform.export_data( data, parent=parent ).payload
        if self.element_end is not None:
            data += self.element_end
        return data

    def get_from_buffer( self, buffer, parent=None ):
        encoding = property_get( self.encoding, parent )

        try:
            result = super().get_from_buffer( buffer, parent=parent )
        except EmptyFieldError:
            result = b""
            if encoding:
                result = result.decode( encoding )
        return result

    def get_element_from_buffer( self, offset, buffer, parent=None, index=None ):
        fill = property_get( self.fill, parent )
        encoding = property_get( self.encoding, parent )
        element_length = property_get( self.element_length, parent )
        element_end = property_get( self.element_end, parent )
        zero_pad = property_get( self.zero_pad, parent )

        pointer = offset
        # add an empty list entry if we find the fill pattern
        if fill and buffer[pointer : pointer + len( fill )] == fill:
            return None, pointer + len( fill )

        if self.length_field:
            # if there's a prefixed length field, that determines the end offset
            size = self.length_field.get_from_buffer( buffer[pointer:], parent=parent )
            pointer += self.length_field.field_size
            data = buffer[pointer : pointer + size]
        elif element_length:
            # if the element length is fixed, that determines the end offset
            data = buffer[pointer : pointer + element_length]
        else:
            # no element size hints, use more guesswork
            data = buffer[pointer:]

        # if we have an inline transform, apply it
        if self.transform:
            data_ts = self.transform.import_data( data, parent=parent )
            pointer += data_ts.end_offset
            data = data_ts.payload
        else:
            if element_end:
                index = data.find( element_end )
                if index >= 0:
                    data = data[:index]
                    pointer += 1

            pointer += len( data )

        if zero_pad:
            zero_index = data.find( b"\x00" )
            if zero_index >= 0:
                data = data[:zero_index]

        if encoding:
            data = data.decode( encoding )

        return data, pointer

    def update_buffer_with_element(
        self, offset, element, buffer, parent=None, index=None
    ):
        fill = property_get( self.fill, parent )
        encoding = property_get( self.encoding, parent )
        element_length = property_get( self.element_length, parent )
        element_end = property_get( self.element_end, parent )
        zero_pad = property_get( self.zero_pad, parent )

        data = bytearray()

        if element is None:
            if fill:
                data.extend( fill )
            else:
                raise ParseError(
                    f"{self.get_path( parent, index )}: A fill pattern needs to be specified to use None as a list entry"
                )
        else:
            if encoding:
                element = element.encode( encoding )

            if self.transform:
                element = self.transform.export_data( element, parent=parent ).payload
            else:
                if element_end:
                    element += element_end

            if self.length_field:
                length_buf = bytearray( b"\x00" * self.length_field.field_size )
                self.length_field.update_buffer_with_value(
                    len( element ), length_buf, parent=parent
                )
                data.extend( length_buf )

            data.extend( element )

            if element_length is not None:
                if element_length != len( element ):
                    if zero_pad and len( element ) < element_length:
                        data.extend( b"\x00" * (element_length - len( data )) )

        # add element to buffer
        if len( buffer ) < offset + len( data ):
            buffer.extend( b"\x00" * (offset + len( data ) - len( buffer )) )
        buffer[offset : offset + len( data )] = data
        return offset + len( data )

    def validate_element( self, element, parent=None, index=None ):
        fill = property_get( self.fill, parent )
        zero_pad = property_get( self.zero_pad, parent )
        encoding = property_get( self.encoding, parent )
        element_length = property_get( self.element_length, parent )

        if element is None:
            if fill is None:
                raise FieldValidationError( "" )

        if encoding:
            # try to encode string, throw UnicodeEncodeError if fails
            element = element.encode( encoding )
        elif not common.is_bytes( element ):
            raise FieldValidationError(
                f"{self.get_path( parent, index )}: Expecting bytes, not {type( value )}"
            )

        if element_length is not None:
            if not zero_pad and element_length < len( element ):
                raise FieldValidationError(
                    f"{self.get_path( parent, index )}: Elements must have a size of {element_length} but found {len( element )}!"
                )

    @property
    def repr( self ):
        offset_str = hex( self.offset ) if type( self.offset ) == int else self.offset
        details = f"offset={offset_str}"
        if self.length:
            details += f", length={self.length}"
        if self.count:
            details += f", count={self.count}"
        if self.stream:
            details += f", stream={self.stream}"
        if self.default:
            details += f", default={self.default}"
        if self.transform:
            details += f", transform={self.transform}"
        return details

    def get_start_offset( self, value, parent=None, index=None ):
        offset = property_get( self.offset, parent, caller=self )
        return offset

    def get_element_size( self, element, parent=None, index=None ):
        fill = property_get( self.fill, parent )

        size = 0
        if self.length_field:
            size += self.length_field.field_size
        size += len( self._scrub_bytes( element, parent=parent ) )
        return size

    def serialise( self, value, parent=None ):
        self.validate( value, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)
        if is_array:
            return (("builtins", "list"), tuple( (v for v in value) ))
        return value


class Bytes( StringField ):
    def __init__( self, offset=Chain(), **kwargs ):
        super().__init__( offset=offset, **kwargs )


class CString( StringField ):
    def __init__( self, offset=Chain(), **kwargs ):
        super().__init__( offset=offset, element_end=b"\x00", **kwargs )


class CStringN( StringField ):
    def __init__( self, offset=Chain(), **kwargs ):
        super().__init__( offset=offset, element_end=b"\x00", zero_pad=True, **kwargs )


class PString( StringField ):
    def __init__( self, offset=Chain(), **kwargs ):
        super().__init__( offset=offset, length_field=UInt8, **kwargs )


class NumberField( StreamField ):
    def __init__(
        self,
        format_type: Union[encoding.NumberType, Ref[encoding.NumberType]],
        field_size: Union[int, Ref[int]],
        signedness: Union[encoding.SignedEncoding, Ref[encoding.SignedEncoding]],
        endian: Union[
            None, encoding.EndianEncoding, Ref[Union[None, encoding.EndianEncoding]]
        ],
        format_range: Optional[Sequence[int]],
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ):
        """Base class for numeric value Fields.

        format_type
            Python native type equivalent. Used for validation. (Usually defined by child class)

        field_size
            Size of field in bytes. (Usually defined by child class)

        signedness
            Signedness of the field. Should be 'signed' or 'unsigned'. (Usually defined by child class)

        endian
            Endianness of the field. Should be 'little', 'big' or None. (Usually defined by child class)

        format_range
            Numeric bounds of format. Used for validation. (Usually defined by child class)

        offset
            Position of data, relative to the start of the parent block. Defaults to
            the end offset of the previous field.

        default
            Default value to emit in the case of e.g. creating an empty Block.

        count
            Load multiple numbers. None implies a single value, non-negative
            numbers will return a Python list.

        length
            Maximum size of the buffer to read in.

        length
            Maximum end offset of the buffer to read in.

        stream
            Read elements continuously until a stop condition is met.

        alignment
            Number of bytes to align the start of each element to.

        stream_end
            Byte pattern to denote the end of the stream.

        stop_check
            A function that takes a data buffer and an offset; should return True if
            the end of the data stream has been reached and False otherwise.

        bitmask
            Apply AND mask (bytes) to data before reading/writing. Used for demultiplexing
            data to multiple fields, e.g. one byte with 8 flag fields.

        range
            Restrict allowed values to a list of choices. Used for validation

        enum
            Restrict allowed values to those provided by a Python enum type. Used for validation.

        exists
            True if this Field should be parsed and generate values, False if it should be skipped.
            Can be set programmatically as a Ref. Defaults to True.
        """
        super().__init__(
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            exists=exists,
        )
        self.format_type = format_type
        self.field_size = field_size
        self.signedness = signedness
        self.endian = endian
        self.format_range = format_range
        if bitmask is not None:
            if not common.is_bytes( bitmask ):
                raise FieldDefinitionError( "bitmask must be a byte string!" )
            if not len( bitmask ) == field_size:
                raise FieldDefinitionError(
                    f"To match field_size, bitmask must be {field_size} bytes long!"
                )
        self.bitmask = bitmask
        self.range = range
        self.enum = enum

    def get_element_from_buffer(
        self,
        offset: int,
        buffer: common.BytesReadType,
        parent: Optional[Block] = None,
        index: Optional[int] = None,
    ) -> encoding.NumberType:
        format_type = property_get( self.format_type, parent )
        assert format_type is not None
        field_size = property_get( self.field_size, parent )
        assert field_size is not None
        signedness = property_get( self.signedness, parent )
        assert signedness is not None
        endian = property_get( self.endian, parent )

        data = buffer[offset : offset + field_size]
        if not len( data ) == field_size:
            raise ParseError(
                f"{self.get_path( parent, index )}: was expecting {field_size} bytes, only found {len(data)}!"
            )
        if self.bitmask:
            # if a bitmask is defined, AND with it first
            data = (
                int.from_bytes( data, byteorder="big" )
                & int.from_bytes( self.bitmask, byteorder="big" )
            ).to_bytes(field_size, byteorder="big")

        # convert bytes to Python type
        element = encoding.unpack( (format_type, field_size, signedness, endian), data )
        # friendly warnings if the imported data fails the range check
        if self.range and (element not in self.range):
            logger.warning(
                f"{self.get_path( parent, index )}: value {element} outside of range {self.range}"
            )

        # friendly warning if the imported data fails the enum check
        if self.enum:
            if element not in [x.value for x in self.enum]:
                logger.warning(
                    f"{self.get_path( parent, index )}: value {element} not castable to {self.enum}"
                )
            else:
                # cast to enum because why not
                element = self.enum( element )

        return element, offset + self.field_size

    def update_buffer_with_element(
        self, offset, element, buffer, parent=None, index=None
    ):
        field_size = property_get( self.field_size, parent )
        assert field_size is not None
        format_type = property_get( self.format_type, parent )
        assert format_type is not None
        field_size = property_get( self.field_size, parent )
        assert field_size is not None
        signedness = property_get( self.signedness, parent )
        assert signedness is not None
        endian = property_get( self.endian, parent )

        data = encoding.pack( (format_type, field_size, signedness, endian), element )
        # force check for no data loss in the value from bitmask
        if self.bitmask:
            orig = int.from_bytes( data, byteorder="big" )
            masked = orig & int.from_bytes( self.bitmask, byteorder="big" )
            if masked != orig:
                raise FieldValidationError(
                    f"{self.get_path( parent, index )}: attempted to mask {data}, expected {orig} but got {masked}!"
                )

            for i in range( field_size ):
                # set bitmasked areas of target to 0
                buffer[offset + i] &= self.bitmask[i] ^ 0xff
                # OR target with replacement bitmasked portion
                buffer[offset + i] |= data[i] & self.bitmask[i]
        else:
            for i in range( field_size ):
                buffer[offset + i] = data[i]
        return offset + field_size

    def update_deps( self, value, parent=None ):
        count = property_get( self.count, parent )
        if count is not None and count != len( value ):
            property_set( self.count, parent, len( value ) )

    def validate_element( self, element, parent=None, index=None ):
        if self.enum:
            if element not in [x.value for x in self.enum]:
                raise FieldValidationError(
                    f"{self.get_path( parent, index )}: Value {element} not castable to {self.enum}"
                )
            element = self.enum( element ).value
        if type( element ) != self.format_type:
            raise FieldValidationError(
                f"{self.get_path( parent, index )}: Expecting type {self.format_type}, not {type( element )}"
            )

        if self.format_range is not None and (element not in self.format_range):
            raise FieldValidationError(
                f"{self.get_path( parent, index )}: Value {element} not in format range ({self.format_range})"
            )
        if self.range is not None and (element not in self.range):
            raise FieldValidationError(
                f"{self.get_path( parent, index )}: Value {element} not in range ({self.range})"
            )
        return

    def get_element_size( self, element, parent=None, index=None ):
        field_size = property_get( self.field_size, parent )
        return field_size

    @property
    def repr( self ):
        offset_str = hex( self.offset ) if type( self.offset ) == int else self.offset
        details = f"offset={offset_str}"
        if self.default:
            details += f", default={self.default}"
        if self.range:
            details += f", range={self.range}"
        if self.bitmask:
            details += f", bitmask={self.bitmask}"
        return details

    @property
    def serialised( self ) -> common.SerialiseType:
        return common.serialise(
            self,
            (
                "offset",
                "default",
                "count",
                "length",
                "stream",
                "alignment",
                "stream_end",
                "stop_check",
                "format_type",
                "field_size",
                "signedness",
                "endian",
                "format_range",
                "bitmask",
                "range",
                "enum",
            ),
        )

    def serialise( self, value: Any, parent: Optional[Block] = None ):
        self.validate( value, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)
        if is_array:
            return (("builtins", "list"), tuple( value ))
        return value


# TODO: Maybe revisit the constructor boilerplate once PEP-0692 arrives
rang = range


class Bits( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        bits: int = 0,
        *,
        size: int = 1,
        endian: Optional[encoding.EndianEncoding] = None,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ):
        SIZES: Dict[
            int,
            Tuple[
                encoding.NumberType,
                int,
                encoding.SignedEncoding,
                Optional[encoding.EndianEncoding],
                Sequence[int],
            ],
        ] = {
            1: (
                int,
                1,
                "unsigned",
                None if endian is None else endian,
                rang( 0, 1 << 8 ),
            ),
            2: (
                int,
                2,
                "unsigned",
                "big" if endian is None else endian,
                rang( 0, 1 << 16 ),
            ),
            4: (
                int,
                4,
                "unsigned",
                "big" if endian is None else endian,
                rang( 0, 1 << 32 ),
            ),
            8: (
                int,
                8,
                "unsigned",
                "big" if endian is None else endian,
                rang( 0, 1 << 64 ),
            ),
        }
        if not size in SIZES:
            raise FieldDefinitionError(
                f"Invalid value for argument size {size} (choices: {list(SIZES.keys())})"
            )
        max_bit_range = rang( 0, 1 << (8 * size) )
        if bits not in max_bit_range:
            raise FieldDefinitionError(
                f"Argument bits must be within {max_bit_range}"
            )

        self.mask_bits = bin( bits ).split( "b", 1 )[1]
        self.bits = [
            (1 << i) for i, x in enumerate( reversed( self.mask_bits ) ) if x == "1"
        ]
        self.check_range = rang( 0, 1 << len( self.bits ) )

        # because we reinterpret the value of the element, we need a seperate enum evaluation
        # compared to the base class
        self.enum_t = enum
        bitmask = encoding.pack( SIZES[size][:4], bits )

        super().__init__(
            *SIZES[size],
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            exists=exists,
        )

    def get_element_from_buffer(
        self,
        offset: int,
        buffer: common.BytesReadType,
        parent: Optional["Block"] = None,
        index: Optional[int] = None,
    ) -> int:
        result, end_offset = super().get_element_from_buffer(
            offset, buffer, parent, index=index
        )
        element = 0
        for i, x in enumerate( self.bits ):
            element += (1 << i) if (result & x) else 0
        if self.enum_t:
            if element not in [x.value for x in self.enum_t]:
                logger.warning(
                    f"{self.get_path( parent, index )}: Value {element} not castable to {self.enum_t}"
                )
            else:
                # cast to enum because why not
                element = self.enum_t( element )
        return element, end_offset

    def update_buffer_with_element(
        self, offset, element, buffer, parent=None, index=None
    ):
        if self.enum_t:
            element = self.enum_t( element ).value
        packed = 0
        for i, x in enumerate( self.bits ):
            if element & (1 << i):
                packed |= x

        return super().update_buffer_with_element(
            offset, packed, buffer, parent, index=index
        )

    def validate_element( self, value, parent=None, index=None ):
        if value not in self.check_range:
            raise FieldValidationError(
                f"{self.get_path( parent, index )}: Value {value} must be within {self.check_range}"
            )
        if self.enum_t:
            if value not in [x.value for x in self.enum_t]:
                raise FieldValidationError(
                    f"{self.get_path( parent, index )}: Value {value} not castable to {self.enum_t}"
                )
            value = self.enum_t( value ).value
        super().validate_element( value, parent, index=index )

    @property
    def repr( self ):
        offset_str = hex( self.offset ) if type( self.offset ) == int else self.offset
        details = f"offset={offset_str}, bits=0b{self.mask_bits}"
        if self.default:
            details += f", default={self.default}"
        return details

    @property
    def serialised( self ):
        return common.serialise(
            self,
            (
                "offset",
                "default",
                "count",
                "length",
                "stream",
                "alignment",
                "stream_end",
                "stop_check",
                "format_type",
                "field_size",
                "signedness",
                "endian",
                "format_range",
                "bitmask",
                "range",
                "enum",
                "bits",
                "enum_t",
            ),
        )


class Bits8( Bits ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        bits: int = 0,
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            offset=offset,
            bits=bits,
            size=1,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Bits16( Bits ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        bits: int = 0,
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            offset=offset,
            bits=bits,
            size=2,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Bits32( Bits ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        bits: int = 0,
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            offset=offset,
            bits=bits,
            size=4,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Bits64( Bits ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        bits: int = 0,
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            offset=offset,
            bits=bits,
            size=8,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int8( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            1,
            "signed",
            None,
            rang( -1 << 7, 1 << 7 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int16_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            2,
            "signed",
            "little",
            rang( -1 << 15, 1 << 15 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int24_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            3,
            "signed",
            "little",
            rang( -1 << 23, 1 << 23 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int32_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            4,
            "signed",
            "little",
            rang( -1 << 31, 1 << 31 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int64_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            8,
            "signed",
            "little",
            rang( -1 << 63, 1 << 63 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt8( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            1,
            "unsigned",
            None,
            rang( 0, 1 << 8 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt16_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            2,
            "unsigned",
            "little",
            rang( 0, 1 << 16 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt24_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            3,
            "unsigned",
            "little",
            rang( 0, 1 << 24 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt32_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            4,
            "unsigned",
            "little",
            rang( 0, 1 << 32 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt64_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            8,
            "unsigned",
            "little",
            rang( 0, 1 << 64 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Float32_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            float,
            4,
            "signed",
            "little",
            None,
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Float64_LE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            float,
            8,
            "signed",
            "little",
            None,
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int16_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            2,
            "signed",
            "big",
            rang( -1 << 15, 1 << 15 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int24_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            3,
            "signed",
            "big",
            rang( -1 << 23, 1 << 23 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int32_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            4,
            "signed",
            "big",
            rang( -1 << 31, 1 << 31 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int64_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            8,
            "signed",
            "big",
            rang( -1 << 63, 1 << 63 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt16_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            2,
            "unsigned",
            "big",
            rang( 0, 1 << 16 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt24_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            3,
            "unsigned",
            "big",
            rang( 0, 1 << 24 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt32_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            4,
            "unsigned",
            "big",
            rang( 0, 1 << 32 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt64_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            8,
            "unsigned",
            "big",
            rang( 0, 1 << 64 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Float32_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            float,
            4,
            "signed",
            "big",
            None,
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Float64_BE( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            float,
            8,
            "signed",
            "big",
            None,
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int16_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            2,
            "signed",
            Ref( "_endian" ),
            rang( -1 << 15, 1 << 15 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int24_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            3,
            "signed",
            Ref( "_endian" ),
            rang( -1 << 23, 1 << 23 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int32_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            4,
            "signed",
            Ref( "_endian" ),
            rang( -1 << 31, 1 << 31 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Int64_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            8,
            "signed",
            Ref( "_endian" ),
            rang( -1 << 63, 1 << 63 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt16_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            2,
            "unsigned",
            Ref( "_endian" ),
            rang( 0, 1 << 16 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt24_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            3,
            "unsigned",
            Ref( "_endian" ),
            rang( 0, 1 << 24 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt32_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            4,
            "unsigned",
            Ref( "_endian" ),
            rang( 0, 1 << 32 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class UInt64_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            int,
            8,
            "unsigned",
            Ref( "_endian" ),
            rang( 0, 1 << 64 ),
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Float32_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            float,
            4,
            "signed",
            Ref( "_endian" ),
            None,
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )


class Float64_P( NumberField ):
    def __init__(
        self,
        offset: OffsetType = Chain(),
        *,
        default: int = 0,
        count: Optional[Union[int, Ref[int]]] = None,
        length: Optional[Union[int, Ref[int]]] = None,
        end_offset: Optional[Union[int, Ref[int]]] = None,
        stream: Union[bool, Ref[bool]] = False,
        alignment: Union[int, Ref[int]] = 1,
        stream_end: Optional[bytes] = None,
        stop_check: Optional[StopCheckType] = None,
        bitmask: Optional[bytes] = None,
        range: Optional[Sequence[int]] = None,
        enum: Optional[IntEnum] = None,
        exists: Union[bool, int, Ref[Union[bool, int]]] = True,
    ) -> None:
        super().__init__(
            float,
            8,
            "signed",
            Ref( "_endian" ),
            None,
            offset=offset,
            default=default,
            count=count,
            length=length,
            end_offset=end_offset,
            stream=stream,
            alignment=alignment,
            stream_end=stream_end,
            stop_check=stop_check,
            bitmask=bitmask,
            range=range,
            enum=enum,
            exists=exists,
        )
