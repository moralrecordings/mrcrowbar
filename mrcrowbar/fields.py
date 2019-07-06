"""Definition classes for common fields in binary formats."""

import collections
import math
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar.refs import Ref, Chain, property_get, property_set
from mrcrowbar import common, encoding


class ParseError( Exception ):
    pass

class FieldValidationError( Exception ):
    pass


class Field( object ):
    def __init__( self, default=None, **kwargs ):
        """Base class for Fields.

        default
            Default value to emit in the case of e.g. creating an empty Block.
        """
        self._position_hint = next( common.next_position_hint )
        self.default = default

    def __repr__( self ):
        desc = '0x{:016x}'.format( id( self ) )
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return '<{}: {}>'.format( self.__class__.__name__, desc )

    @property
    def repr( self ):
        """Plaintext summary of the Field."""
        return None

    @property
    def serialised( self ):
        """Tuple containing the contents of the Field."""
        return None

    def __hash__( self ):
        serial = self.serialised
        if serial is None:
            return super().__hash__()
        return hash( self.serialised )

    def __eq__( self, other ):
        serial = self.serialised
        if serial is None:
            return super().__eq__( other )
        return self.serialised == other.serialised

    def get_from_buffer( self, buffer, parent=None ):
        """Create a Python object from a byte string, using the field definition.

        buffer
            Input byte string to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return None

    def update_buffer_with_value( self, value, buffer, parent=None ):
        """Write a Python object into a byte array, using the field definition.

        value
            Input Python object to process.

        buffer
            Output byte array to encode value into.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        assert common.is_bytes( buffer )
        self.validate( value, parent )
        return
    
    def get_start_offset( self, value, parent=None, index=None ):
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
        assert index is None
        return 0

    def get_size( self, value, parent=None, index=None ):
        """Return the size of the field data (in bytes).

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.

        index
            Index of the Python object to measure from. Used if the Field
            takes a list of objects.
        """
        assert index is None
        return 0

    def get_end_offset( self, value, parent=None, index=None ):
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
        return self.get_start_offset( value, parent, index ) + self.get_size( value, parent, index )

    def scrub( self, value, parent=None ):
        """Return the value coerced to the correct type of the field (if necessary).

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.

        Throws FieldValidationError if value can't be coerced.
        """
        return value

    def update_deps( self, value, parent=None ):
        """Update all dependent variables with data derived from the value of the field.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return

    def validate( self, value, parent=None ):
        """Validate that a correctly-typed Python object meets the constraints for the field.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.

        Throws FieldValidationError if a constraint fails.
        """
        pass 

    def serialise( self, value, parent=None ):
        """Return a value as basic Python types.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return None


class StreamField( Field ):
    def __init__( self, offset=Chain(), default=None, count=None, length=None, stream=False,
                    alignment=1, stream_end=None, stop_check=None, **kwargs ):
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

        stream
            Read elements continuously until a stop condition is met. Defaults to False.

        alignment
            Number of bytes to align the start of each element to.

        stream_end
            Byte pattern to denote the end of the stream.

        stop_check
            A function that takes a data buffer and an offset; should return True if
            the end of the data stream has been reached and False otherwise.
        """
        if count is not None and default is None:
            default = []
        super().__init__( default=default, **kwargs )
        self.offset = offset
        self.count = count
        self.length = length
        self.stream = stream
        self.alignment = alignment
        if stream_end is not None:
            assert common.is_bytes( stream_end )
        self.stream_end = stream_end
        self.stop_check = stop_check

    def get_element_from_buffer( self, offset, buffer, parent=None ):
        pass

    def get_from_buffer( self, buffer, parent=None ):
        assert common.is_bytes( buffer )
        offset = property_get( self.offset, parent, caller=self )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        alignment = property_get( self.alignment, parent )

        is_array = stream or (count is not None)
        count = count if is_array else 1
        if count is not None:
            assert count >= 0
        length = property_get( self.length, parent )
        if length is not None:
            buffer = buffer[:offset+length]

        pointer = offset
        result = []
        while pointer < len( buffer ):
            start_offset = pointer
            # stop if we've hit the maximum number of items
            if not stream and (len( result ) == count):
                break
            # run the stop check (if exists): if it returns true, we've hit the end of the stream
            if self.stop_check and (self.stop_check( buffer, pointer )):
                break
            # stop if we find the end of stream marker
            if self.stream_end is not None and buffer[pointer:pointer+len( self.stream_end )] == self.stream_end:
                break

            element, end_offset = self.get_element_from_buffer( pointer, buffer, parent )
            result.append( element )
            pointer = end_offset

            # if an alignment is set, do some aligning
            if alignment is not None:
                width = (pointer-start_offset) % alignment
                if width:
                    pointer += alignment - width

        if not is_array:
            return result[0]
        return result

    def update_buffer_with_element( self, offset, element, buffer, parent=None ):
        pass

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent, caller=self )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        alignment = property_get( self.alignment, parent )

        is_array = stream or (count is not None)
        
        if is_array:
            try:
                it = iter( value )
            except TypeError:
                raise FieldValidationError( 'Type {} not iterable'.format( type( value ) ) )
            if not stream:
                assert len( value ) <= count
        else:
            value = [value]

        pointer = offset
        for element in value:
            start_offset = pointer
            end_offset = self.update_buffer_with_element( pointer, element, buffer, parent )
            pointer = end_offset

            if alignment is not None:
                width = (pointer-start_offset) % alignment
                if width:
                    pointer += alignment - width

        new_size = pointer
        if self.stream_end is not None:
            new_size += len( self.stream_end )

        if len( buffer ) < new_size:
            buffer.extend( b'\x00'*(new_size-len( buffer )) )

        if self.stream_end is not None:
            buffer[new_size-len( self.stream_end ):new_size] = self.stream_end

    def update_deps( self, value, parent=None ):
        count = property_get( self.count, parent )
        length = property_get( self.length, parent )
        if count is not None and count != len( value ):
            property_set( self.count, parent, len( value ) )
        if length is not None:
            property_set( self.length, parent, self.get_size( value, parent ) )

    def validate_element( self, element, parent=None ):
        pass

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent, caller=self )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)

        if is_array:
            try:
                it = iter( value )
            except TypeError:
                raise FieldValidationError( 'Type {} not iterable'.format( type( value ) ) )
            if count is not None and (not isinstance( self.count, Ref )) and (len( value ) != count):
                raise FieldValidationError( 'Count defined as a constant, was expecting {} list entries but got {}!'.format( length, len( value ) ) )
        else:
            value = [value]

        for element in value:
            self.validate_element( element, parent=parent )

    def get_element_size( self, element, parent=None ):
        pass

    def get_start_offset( self, value, parent=None, index=None ):
        offset = property_get( self.offset, parent, caller=self )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        alignment = property_get( self.alignment, parent )
        is_array = stream or (count is not None)

        pointer = offset
        if index is not None:
            if not is_array:
                raise IndexError( 'Can\'t use index for a non-array' )
            elif index not in range( len( value ) ):
                raise IndexError( 'Index {} is not within range( 0, {} )'.format( index, len( value ) ) )
            for element in value[:index]:
                start_offset = pointer
                pointer += self.get_element_size( element, parent )
                # if an alignment is set, do some aligning
                if alignment is not None:
                    width = (pointer-start_offset) % alignment
                    if width:
                        pointer += alignment - width

        return pointer

    def get_size( self, value, parent=None, index=None ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        alignment = property_get( self.alignment, parent )
        is_array = stream or (count is not None)

        if index is not None:
            if not is_array:
                raise IndexError( 'Can\'t use index for a non-array BlockField' )
            elif index not in range( 0, count ):
                raise IndexError( 'Index {} is not within range( 0, {} )'.format( index, count ) )
            value = [value[index]]
        else:
            value = value if is_array else [value]

        pointer = self.get_start_offset( value, parent, index )
        start = pointer
        for element in value:
            start_offset = pointer
            pointer += self.get_element_size( element, parent )
            # if an alignment is set, do some aligning
            if alignment is not None:
                width = (pointer-start_offset) % alignment
                if width:
                    pointer += alignment - width

        if self.stream_end is not None:
            pointer += len( self.stream_end )

        return pointer - start



ChunkBase = collections.namedtuple( 'Chunk', ['id', 'obj'] )
class Chunk( ChunkBase ):
    @property
    def serialised( self ):
        """Tuple containing the contents of the Chunk."""
        klass = self.__class__
        return ((klass.__module__, klass.__name__), (('id', self.id), ('obj', self.obj.serialised if self.obj is not None else None)))


class ChunkField( StreamField ):
    def __init__( self, chunk_map, offset=Chain(), count=None, length=None, stream=True,
                    alignment=1, stream_end=None, stop_check=None, default_klass=None,
                    chunk_id_size=None, chunk_id_field=None, chunk_length_field=None,
                    fill=None, **kwargs ):
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

        chunk_id_size
            Size in bytes of the Chunk ID.

        chunk_id_field
            Field class used to parse Chunk ID. Defaults to Bytes.

        chunk_length_field
            Field class used to parse the Chunk data length. For use when a Chunk consists of an ID followed by the size of the data.

        fill
            Exact byte sequence that denotes an empty Chunk object.
        """

        super().__init__( offset=offset, default=None, count=count, length=length,
                          stream=stream, alignment=alignment, stream_end=stream_end,
                          stop_check=stop_check, **kwargs )
        self.chunk_map = chunk_map
        if chunk_length_field:
            assert issubclass( chunk_length_field, NumberField )
            self.chunk_length_field = chunk_length_field( 0x00 )
        else:
            self.chunk_length_field = None
        if chunk_id_field:
            assert issubclass( chunk_id_field, (NumberField) )
            self.chunk_id_field = chunk_id_field( 0x00 )
        else:
            self.chunk_id_field = None
        self.default_klass = default_klass

        self.chunk_id_size = chunk_id_size
        self.fill = fill

    def get_element_from_buffer( self, offset, buffer, parent=None ):
        chunk_map = property_get( self.chunk_map, parent )
        fill = property_get( self.fill, parent )

        pointer = offset
        chunk_id = None
        if self.chunk_id_field:
            chunk_id = self.chunk_id_field.get_from_buffer( buffer[pointer:], parent=parent )
            pointer += self.chunk_id_field.field_size
        elif self.chunk_id_size:
            chunk_id = buffer[pointer:pointer+self.chunk_id_size]
            pointer += len( chunk_id )
        else:
            for test_id in chunk_map:
                if buffer[pointer:].startswith( test_id ):
                    chunk_id = test_id
                    break
            if not chunk_id:
                raise ParseError( 'Could not find matching chunk at offset {}'.format( pointer ) )
            pointer += len( chunk_id )

        if chunk_id in chunk_map:
            chunk_klass = chunk_map[chunk_id]
        elif self.default_klass:
            chunk_klass = self.default_klass
        else:
            raise ParseError( 'No chunk class match for ID {}'.format( chunk_id ) )

        if self.chunk_length_field:
            size = self.chunk_length_field.get_from_buffer( buffer[pointer:], parent=parent )
            pointer += self.chunk_length_field.field_size
            chunk_buffer = buffer[pointer:pointer+size]
            pointer += size
            if chunk_buffer == fill:
                result = Chunk( id=chunk_id, obj=None )
                return result, pointer
            chunk = chunk_klass( chunk_buffer, parent=parent )
        else:
            chunk = chunk_klass( buffer[pointer:], parent=parent )
            pointer += chunk.get_size()
        result = Chunk( id=chunk_id, obj=chunk )

        return result, pointer

    def update_buffer_with_element( self, offset, element, buffer, parent=None ):
        chunk_map = property_get( self.chunk_map, parent )
        fill = property_get( self.fill, parent )

        data = bytearray()
        if self.chunk_id_field:
            data.extend( b'\x00'*self.chunk_id_field.field_size )
            self.chunk_id_field.update_buffer_with_value( element.id, data, parent=parent )
        else:
            data += element.id

        if element.obj is None:
            if fill is not None:
                payload = fill
            else:
                raise ValueError( 'Object part of Chunk can\'t be None unless there\'s a fill set' )
        else:
            payload = element.obj.export_data()

        if self.chunk_length_field:
            length_buf = bytearray( b'\x00'*self.chunk_length_field.field_size )
            self.chunk_length_field.update_buffer_with_value( len( payload ), length_buf, parent=parent )
            data.extend( length_buf )

        data += payload

        if len( buffer ) < offset+len( data ):
            buffer.extend( b'\x00'*(offset+len( data )-len( buffer )) )
        buffer[offset:offset+len( data )] = data
        return offset+len( data )

    def validate_element( self, element, parent=None ):
        chunk_map = property_get( self.chunk_map, parent )
        fill = property_get( self.fill, parent )

        assert isinstance( element, Chunk )
        if element.id in chunk_map:
            chunk_klass = chunk_map[element.id]
        elif self.default_klass:
            chunk_klass = self.default_klass

        if element.obj is None:
            assert fill is not None
        else:
            assert isinstance( element.obj, chunk_klass )

        if self.chunk_id_size:
            assert len( element.id ) == self.chunk_id_size

    def get_element_size( self, element, parent=None ):
        fill = property_get( self.fill, parent )

        size = 0
        if self.chunk_id_field:
            size += self.chunk_id_field.field_size
        else:
            size += len( element.id )
        if self.chunk_length_field:
            size += self.chunk_length_field.field_size
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
            return (('builtins', 'list'), tuple( (a, b.serialised if b is not None else None) for a, b in value ))
        return (value[0], value[1].serialised if value is not None else None)


class BlockField( StreamField ):
    def __init__( self, block_klass, offset=Chain(), block_kwargs=None, count=None, fill=None,
                    block_type=None, default_klass=None, length=None, stream=False,
                    alignment=1, transform=None, stream_end=None, stop_check=None,
                    **kwargs ):
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

        stream
            Read Blocks continuously until a stop condition is met.

        alignment
            Number of bytes to align the start of each Block to.

        transform
            Transform class to use for preprocessing the data before creating each Block.

        stream_end
            Byte pattern to denote the end of the stream.

        stop_check
            A function that takes a data buffer and an offset; should return True if
            the end of the data stream has been reached and False otherwise.

        """
        super().__init__( offset=offset, default=None, count=count, length=length,
                          stream=stream, alignment=alignment, stream_end=stream_end,
                          stop_check=stop_check, **kwargs )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.block_type = block_type
        # TODO: support different args if using a switch
        self.fill = fill
        self.default_klass = default_klass
        self.transform = transform

    def get_element_from_buffer( self, offset, buffer, parent=None ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        fill = property_get( self.fill, parent )
        klass = self.get_klass( parent )

        # add an empty list entry if we find the fill pattern
        if fill and buffer[offset:offset+len( fill )] == fill:
            return None, offset+len( fill )
        # if we have an inline transform, apply it
        elif self.transform:
            data = self.transform.import_data( buffer[offset:], parent=parent )
            block = klass( source_data=data.payload, parent=parent, **self.block_kwargs )
            return block, offset+data.end_offset
        # otherwise, create a block
        block = klass( source_data=buffer[offset:], parent=parent, **self.block_kwargs )
        size = block.get_size()
        if size == 0:
            if stream:
                raise ParseError( 'Can\'t stream 0 byte Blocks ({}) from a BlockField'.format( klass ) )
            elif count and len( result ) == 0:
                logger.warning( '{}: copying 0 byte Blocks ({}) from a BlockField, this is probably not what you want'.format( self, klass ) )

        return block, offset+size
        
    def update_buffer_with_element( self, offset, element, buffer, parent=None ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        fill = property_get( self.fill, parent )

        klass = self.get_klass( parent )

        if element is None:
            if fill:
                data = fill
            else:
                raise ParseError( 'A fill pattern needs to be specified to use None as a list entry' )
        else:
            data = element.export_data()
            if self.transform:
                data = self.transform.export_data( data, parent=parent ).payload
        if len( buffer ) < offset+len( data ):
            buffer.extend( b'\x00'*(offset+len( data )-len( buffer )) )
        buffer[offset:offset+len( data )] = data
        return offset+len( data )

    def update_deps( self, value, parent=None ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )

        is_array = stream or (count is not None)

        if count is not None and count != len( value ):
            property_set( self.count, parent, len( value ) )

        if not is_array:
            value = [value]

        for element in value:
            if element is not None:
                element.update_deps()

    def validate_element( self, element, parent=None ):
        klass = self.get_klass( parent )
        if (element is not None) and (not isinstance( element, klass )):
             raise FieldValidationError( 'Expecting block class {}, not {}'.format( klass, type( element ) ) )

    def get_element_size( self, element, parent=None ):
        fill = property_get( self.fill, parent )
        if self.transform:
            data = self.transform.export_data( element.export_data(), parent=parent ).payload
            return len( data )
        elif element is None:
            if fill:
                return len( fill )
            else:
                raise ParseError( 'A fill pattern needs to be specified to use None as a list entry' )
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
                raise ParseError( 'No block klass match for type {}'.format( block_type ) )
        return block_klass

    def serialise( self, value, parent=None ):
        self.validate( value, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)
        if is_array:
            return (('builtins', 'list'), tuple( x.serialised if x is not None else None for x in value ))
        return value.serialised if value is not None else None


class Bytes( Field ):
    def __init__( self, offset=Chain(), length=None, default=None, transform=None, stream_end=None, alignment=1, zero_pad=False, encoding=None, **kwargs ):
        """Field class for raw byte data.

        offset
            Position of data, relative to the start of the parent block. Defaults to
            the end offset of the previous field.

        length
            Maximum size of the data in bytes.

        default
            Default byte data. Used for creating an empty block.

        transform
            A Transform to process the data before import/export.

        stream_end
            Byte string to indicate the end of the data.

        alignment
            Number of bytes to align the start of the next element to.

        zero_pad
            Pad the data with zeros to match the length. If enabled, the data size must be up to or equal to the length.

        encoding
            Python string encoding to use for output, as accepted by bytes.decode().
        """
        if default is not None:
            assert common.is_bytes( default )
        else:
            default = b''
        super().__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length
        self.transform = transform
        if stream_end is not None:
            assert common.is_bytes( stream_end )
        self.stream_end = stream_end
        self.alignment = alignment
        if zero_pad:
            assert self.length is not None
        self.zero_pad = zero_pad
        self.encoding = encoding

    def _scrub_bytes( self, value, parent=None ):
        encoding = property_get( self.encoding, parent )
        data = value

        if encoding:
            data = data.encode( encoding )
        if self.transform:
            data = self.transform.export_data( data, parent=parent ).payload
        if self.stream_end is not None:
            data += self.stream_end
        return data

    def get_from_buffer( self, buffer, parent=None, **kwargs ):
        assert common.is_bytes( buffer )
        offset = property_get( self.offset, parent, caller=self )
        length = property_get( self.length, parent )
        encoding = property_get( self.encoding, parent )

        data = buffer[offset:]
        if self.stream_end is not None:
            end = data.find( self.stream_end )
            if end != -1:
                data = data[:end]
        if length is not None:
            data = data[:length]

        if self.transform:
            data = self.transform.import_data( data, parent=parent ).payload
    
        if encoding:
            data = data.decode( encoding )

        return data

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent, caller=self )
        length = property_get( self.length, parent )
        alignment = property_get( self.alignment, parent )
        encoding = property_get( self.encoding, parent )

        data = self._scrub_bytes( value, parent=None )

        new_size = offset+len( data )
        if alignment is not None:
            width = new_size % alignment
            if width:
                new_size += alignment-width

        if len( buffer ) < new_size:
            buffer.extend( b'\x00'*(new_size-len( buffer )) )

        buffer[offset:offset+len( data )] = data
        return

    def update_deps( self, value, parent=None ):
        length = property_get( self.length, parent )
        zero_pad = property_get( self.zero_pad, parent )
        encoding = property_get( self.encoding, parent )

        value = self._scrub_bytes( value, parent=None )
        test_length = len( value )

        if length is not None and not zero_pad and length != test_length:
            property_set( self.length, parent, test_length )

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent, caller=self )
        length = property_get( self.length, parent )
        zero_pad = property_get( self.zero_pad, parent )
        encoding = property_get( self.encoding, parent )

        if encoding:
            # try to encode string, throw UnicodeEncodeError if fails
            value = value.encode( encoding )
        elif not common.is_bytes( value ):
            raise FieldValidationError( 'Expecting bytes, not {}'.format( type( value ) ) )

        calc_length = len( value )

        if length is not None:
            if (not isinstance( self.length, Ref )) and (calc_length != length):
                raise FieldValidationError( 'Length defined as a constant, was expecting {} bytes but got {}!'.format( length, calc_length ) )
            elif zero_pad and calc_length > length:
                raise FieldValidationError( 'Content of {} bytes is greater than expected length of {} bytes!'.format( calc_length, length ) )

        return

    @property
    def repr( self ):
        details = 'offset={}'.format( hex( self.offset ) if type( self.offset ) == int else self.offset )
        if self.length:
            details += ', length={}'.format( self.length )
        if self.default:
            details += ', default={}'.format( self.default )
        if self.transform:
            details += ', transform={}'.format( self.transform )
        return details

    def get_start_offset( self, value, parent=None, index=None ):
        assert index is None
        offset = property_get( self.offset, parent, caller=self )
        return offset

    def get_size( self, value, parent=None, index=None ):
        assert index is None
        length = property_get( self.length, parent )
        encoding = property_get( self.encoding, parent )
        if length is None:
            return len( self._scrub_bytes( value, parent ) )
        return length

    def serialise( self, value, parent=None ):
        self.validate( value, parent )
        return value


class StringField( StreamField ):
    def __init__( self, offset=Chain(), default=None, count=None, length=None,
                    stream=False, alignment=1, stream_end=None, stop_check=None,
                    zero_pad=False, encoding=False, length_field=None, fill=None,
                    element_length=None, element_end=None,
                    **kwargs ):
        super().__init__( ofset=offset, default=default, count=count, length=length,
                          stream=stream, alignment=alignment, stream_end=stream_end,
                          stop_check=stop_check, **kwargs )

        if count is not None:
            assert not stream
            assert (element_length is not None) or (length_field is not None) or (element_end is not None)

        elif stream:
            assert (element_length is not None) or (length_field is not None) or (element_end is not None)

        else: # single element
            pass

        if zero_pad:
            assert element_length is not None

        if length_field:
            assert element_length is None
            assert issubclass( length_field, NumberField )
            self.length_field = length_field( 0x00 )
        else:
            self.length_field = None

        self.zero_pad = zero_pad
        self.encoding = encoding
        self.fill = fill
        self.element_length = element_length

    def _scrub_bytes( self, value, parent=None ):
        encoding = property_get( self.encoding, parent )
        data = value

        if encoding:
            data = data.encode( encoding )
        return data

    def get_element_from_buffer( self, offset, buffer, parent=None ):
        fill = property_get( self.fill, parent )
        encoding = property_get( self.encoding, parent )
        element_length = property_get( self.element_length, parent )
        zero_pad = property_get( self.zero_pad, parent )

        pointer = offset
        if self.length_field:
            size = self.length_field.get_from_buffer( buffer[pointer:], parent=parent )
            pointer += self.length_field.field_size
            data = buffer[pointer:pointer+size]
            pointer += size
        elif element_length:
            data = buffer[pointer:pointer+element_length]
            pointer += element_length
        else:
            # no element size hints, assume it's the whole thing
            data = buffer[pointer:]
            pointer += len( data )

        if data == fill:
            return None, pointer

        if zero_pad:
            index = data.find( b'\x00' )
            if index >= 0:
                data = data[:index]

        if encoding:
            data = data.decode( encoding )

        return data, pointer

    def update_buffer_with_element( self, offset, element, buffer, parent=None ):
        fill = property_get( self.fill, parent )
        encoding = property_get( self.encoding, parent )
        element_length = property_get( self.element_length, parent )
        zero_pad = property_get( self.zero_pad, parent )

        data = bytearray()

        if encoding:
            element = element.encode( encoding )

        if self.length_field:
            data.extend( b'\x00'*self.length_field.field_size )
            self.length_field.update_buffer_with_value( len( element ) )
        elif element_length is not None:
            if element_length != len( element ):
                if zero_pad and len( element ) < element_length:
                    element += b'\x00'*(element_length-len( element ))

        data.extend( element )

        if len( buffer ) < offset+len( data ):
            buffer.extend( b'\x00'*(offset+len( data )-len( buffer )) )
        buffer[offset:offset+len( data )] = data
        return offset+len( data )

    def validate_element( self, element, parent=None ):
        fill = property_get( self.fill, parent )
        zero_pad = property_get( self.zero_pad, parent )
        encoding = property_get( self.encoding, parent )
        element_length = property_get( self.element_length, parent )

        if element is None:
            assert fill is not None

        if encoding:
            # try to encode string, throw UnicodeEncodeError if fails
            element = element.encode( encoding )
        elif not common.is_bytes( element ):
            raise FieldValidationError( 'Expecting bytes, not {}'.format( type( value ) ) )

        if element_length is not None:
            if not zero_pad and element_length < len( element ):
                raise FieldValidationError( 'Elements must have a size of {} but found {}!'.format( element_length, len( element ) ) )


    def get_element_size( self, element, parent=None ):
        fill = property_get( self.fill, parent )

        size = 0
        if self.length_field:
            size += self.length_field.field_size
        size += len( self._scrub_bytes( element ) )
        return size

    def serialise( self, value, parent=None ):
        self.validate( value, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)
        if is_array:
            return (('builtins', 'list'), tuple( (v for v in value) ))
        return value



class CString( Bytes ):
    def __init__( self, offset=Chain(), **kwargs ):
        super().__init__( offset=offset, stream_end=b'\x00', **kwargs )


class CStringN( Field ):
    def __init__( self, offset, length, default=b'', **kwargs ):
        assert common.is_bytes( default )
        super().__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length

    def get_from_buffer( self, buffer, parent=None ):
        assert common.is_bytes( buffer )
        offset = property_get( self.offset, parent, caller=self )
        length = property_get( self.length, parent )

        return buffer[offset:offset+length].split( b'\x00', 1 )[0]

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent, caller=self )
        length = property_get( self.length, parent )

        block_data = value + b'\x00'*(length - len( value ))
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )    
        buffer[offset:offset+len( block_data )] = block_data
        return

    def validate( self, value, parent=None ):
        length = property_get( self.length, parent )

        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (len( value ) > length):
            raise FieldValidationError( 'Expecting length <= {}, not {}'.format( length, len( value ) ) )
        return
    
    def get_start_offset( self, value, parent=None, index=None ):
        assert index is None
        offset = property_get( self.offset, parent, caller=self )
        return offset

    def get_size( self, value, parent=None, index=None ):
        assert index is None
        length = property_get( self.length, parent )
        return length


class CStringNStream( Field ):
    def __init__( self, offset, length_field, **kwargs ):
        assert issubclass( length_field, NumberField )
        super().__init__( **kwargs )
        self.offset = offset
        self.length_field = length_field( 0x00 )

    def get_from_buffer( self, buffer, parent=None ):
        assert common.is_bytes( buffer )
        offset = property_get( self.offset, parent, caller=self )
        strings = []

        pointer = offset
        while pointer < len( buffer ):
            count = self.length_field.get_from_buffer( buffer[pointer:] )
            pointer += self.length_field.field_size
            strings.append( buffer[pointer:pointer+count].split( b'\x00', 1 )[0] )
            pointer += count
        return strings

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent, caller=self )
        length = self.length_field.field_size

        pointer = offset
        for s in value:
            assert common.is_bytes( s )
            string_data = s+b'\x00'
            self.length_field.offset = pointer
            self.length_field.update_buffer_with_value( len( string_data ), buffer )
            pointer += length
            buffer[pointer:pointer+len( string_data )] = string_data
            pointer += len( string_data )

    def get_start_offset( self, value, parent=None, index=None ):
        assert index is None
        offset = property_get( self.offset, parent, caller=self )
        return offset

    def get_size( self, value, parent=None, index=None ):
        assert index is None
        size = 0
        for x in value:
            size += self.length_field.field_size
            size += len( x )
        return size


class NumberField( StreamField ):
    def __init__( self, format_type, field_size, signedness, endian, format_range, offset=Chain(), default=0, count=None, length=None, stream=False, alignment=1, stream_end=None, stop_check=None, bitmask=None, range=None, enum=None, **kwargs ):
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
        """
        super().__init__( offset=offset, default=default, count=count, length=length,
                          stream=stream, alignment=alignment, stream_end=stream_end,
                          stop_check=stop_check, **kwargs )
        self.format_type = format_type
        self.field_size = field_size
        self.signedness = signedness
        self.endian = endian
        self.format_range = format_range
        if bitmask:
            assert common.is_bytes( bitmask )
            assert len( bitmask ) == field_size
        self.bitmask = bitmask
        self.range = range
        self.enum = enum

    def get_element_from_buffer( self, offset, buffer, parent=None ):
        format_type = property_get( self.format_type, parent )
        field_size = property_get( self.field_size, parent )
        signedness = property_get( self.signedness, parent )
        endian = property_get( self.endian, parent )

        data = buffer[offset:offset+self.field_size]
        assert len( data ) == self.field_size
        if self.bitmask:
            # if a bitmask is defined, AND with it first
            data = (int.from_bytes( data, byteorder='big' ) &
                    int.from_bytes( self.bitmask, byteorder='big' )
                    ).to_bytes( self.field_size, byteorder='big' )

        # convert bytes to Python type
        element = encoding.unpack( (format_type, field_size, signedness, endian), data )
        # friendly warnings if the imported data fails the range check
        if self.range and (element not in self.range):
            logger.warning( '{}: value {} outside of range {}'.format( self, element, self.range ) )

        # friendly warning if the imported data fails the enum check
        if self.enum:
            if (element not in [x.value for x in self.enum]):
                logger.warning( '{}: value {} not castable to {}'.format( self, element, self.enum ) )
            else:
                # cast to enum because why not
                element = self.enum( element )

        return element, offset+self.field_size

    def update_buffer_with_element( self, offset, element, buffer, parent=None ):
        field_size = property_get( self.field_size, parent )
        format_type = property_get( self.format_type, parent )
        field_size = property_get( self.field_size, parent )
        signedness = property_get( self.signedness, parent )
        endian = property_get( self.endian, parent )

        data = encoding.pack( (format_type, field_size, signedness, endian), element )
        # force check for no data loss in the value from bitmask
        if self.bitmask:
            assert (int.from_bytes( data, byteorder='big' ) &
                    int.from_bytes( self.bitmask, byteorder='big' ) ==
                    int.from_bytes( data, byteorder='big' ))

            for i in range( field_size ):
                # set bitmasked areas of target to 0
                buffer[offset+i] &= (self.bitmask[i] ^ 0xff)
                # OR target with replacement bitmasked portion
                buffer[offset+i] |= (data[i] & self.bitmask[i])
        else:
            for i in range( field_size ):
                buffer[offset+i] = data[i]
        return offset+field_size

    def update_deps( self, value, parent=None ):
        count = property_get( self.count, parent )
        if count is not None and count != len( value ):
            property_set( self.count, parent, len( value ) )

    def validate_element( self, element, parent=None ):
        if self.enum:
            if (element not in [x.value for x in self.enum]):
                raise FieldValidationError( 'Value {} not castable to {}'.format( element, self.enum ) )
            element = self.enum( element ).value
        if (type( element ) != self.format_type):
            raise FieldValidationError( 'Expecting type {}, not {}'.format( self.format_type, type( element ) ) )

        if self.format_range is not None and (element not in self.format_range):
            raise FieldValidationError( 'Value {} not in format range ({})'.format( element, self.format_range ) )
        if self.range is not None and (element not in self.range):
            raise FieldValidationError( 'Value {} not in range ({})'.format( element, self.range ) )
        return

    def get_element_size( self, element, parent=None ):
        field_size = property_get( self.field_size, parent )
        return field_size

    @property
    def repr( self ):
        details = 'offset={}'.format( hex( self.offset ) if type( self.offset ) == int else self.offset )
        if self.default:
            details += ', default={}'.format( self.default )
        if self.range:
            details += ', range={}'.format( self.range )
        if self.bitmask:
            details += ', bitmask={}'.format( self.bitmask )
        return details

    @property
    def serialised( self ):
        return common.serialise( self, ('offset', 'default', 'count', 'length', 'stream', 'alignment', 'stream_end', 'stop_check', 'format_type', 'field_size', 'signedness', 'endian', 'format_range', 'bitmask', 'range', 'enum') )

    def serialise( self, value, parent=None ):
        self.validate( value, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)
        if is_array:
            return (('builtins', 'list'), tuple( value ))
        return value


class Int8( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 1, 'signed', None, range( -1<<7, 1<<7 ), *args, **kwargs )


class UInt8( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 1, 'unsigned', None, range( 0, 1<<8 ), *args, **kwargs )


class Bits( NumberField ):
    def __init__( self, offset=Chain(), bits=0, default=0, size=1, enum=None, endian=None, *args, **kwargs ):
        SIZES = {
            1: (int, 1, 'unsigned', None if endian is None else endian, range( 0, 1<<8 )),
            2: (int, 2, 'unsigned', 'big' if endian is None else endian, range( 0, 1<<16 )),
            4: (int, 4, 'signed', 'big' if endian is None else endian, range( 0, 1<<32 )),
            8: (int, 8, 'signed', 'big' if endian is None else endian, range( 0, 1<<64 )),
        }
        assert size in SIZES
        assert type( bits ) == int
        assert (bits >= 0)
        assert (bits < 1<<(8*size))

        self.mask_bits = bin( bits ).split( 'b', 1 )[1]
        self.bits = [(1<<i) for i, x in enumerate( reversed( self.mask_bits ) ) if x == '1']
        self.check_range = range( 0, 1<<len( self.bits ) )

        # because we reinterpret the value of the element, we need a seperate enum evaluation
        # compared to the base class
        self.enum_t = enum
        bitmask = encoding.pack( SIZES[size][:4], bits )

        # Python 3.4 compat
        inner_args = list( SIZES[size] ) + [offset] + list( args )
        super().__init__( *inner_args, default=default, bitmask=bitmask, **kwargs )

    def get_element_from_buffer( self, offset, buffer, parent=None ):
        result, end_offset = super().get_element_from_buffer( offset, buffer, parent )
        element = 0
        for i, x in enumerate( self.bits ):
            element += (1 << i) if (result & x) else 0
        if self.enum_t:
            if (element not in [x.value for x in self.enum_t]):
                logger.warning( '{}: value {} not castable to {}'.format( self, element, self.enum_t ) )
            else:
                # cast to enum because why not
                element = self.enum_t( element )
        return element, end_offset

    def update_buffer_with_element( self, offset, element, buffer, parent=None ):
        assert element in self.check_range
        if self.enum_t:
            element = self.enum_t( element ).value
        packed = 0
        for i, x in enumerate( self.bits ):
            if (element & (1 << i)):
                packed |= x

        return super().update_buffer_with_element( offset, packed, buffer, parent )

    def validate_element( self, value, parent=None ):
        if self.enum_t:
            if (value not in [x.value for x in self.enum_t]):
                raise FieldValidationError( 'Value {} not castable to {}'.format( value, self.enum_t ) )
            value = self.enum_t( value ).value
        super().validate_element( value, parent )

    @property
    def repr( self ):
        details = 'offset={}, bits=0b{}'.format( hex( self.offset ) if type( self.offset ) == int else self.offset, self.mask_bits )
        if self.default:
            details += ', default={}'.format( self.default )
        return details

    @property
    def serialised( self ):
        return common.serialise( self, ('offset', 'default', 'bits', 'size', 'enum', 'endian') )


class Bits8( Bits ):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, size=1, **kwargs )


class Bits16( Bits ):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, size=2, **kwargs )


class Bits32( Bits ):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, size=4, **kwargs )


class Bits64( Bits ):
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, size=8, **kwargs )


class Int16_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'signed', 'little', range( -1<<15, 1<<15 ), *args, **kwargs )


class Int24_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 3, 'signed', 'little', range( -1<<23, 1<<23 ), *args, **kwargs )


class Int32_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'signed', 'little', range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'signed', 'little', range( -1<<63, 1<<63 ), *args, **kwargs )


class UInt16_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'unsigned', 'little', range( 0, 1<<16 ), *args, **kwargs )


class UInt24_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 3, 'unsigned', 'little', range( 0, 1<<24 ), *args, **kwargs )


class UInt32_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'unsigned', 'little', range( 0, 1<<32 ), *args, **kwargs )


class UInt64_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'unsigned', 'little', range( 0, 1<<64 ), *args, **kwargs )


class Float32_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( float, 4, 'signed', 'little', None, *args, **kwargs )


class Float64_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( float, 8, 'signed', 'little', None, *args, **kwargs )


class Int16_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'signed', 'big', range( -1<<15, 1<<15 ), *args, **kwargs )


class Int24_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 3, 'signed', 'big', range( -1<<23, 1<<23 ), *args, **kwargs )


class Int32_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'signed', 'big', range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'signed', 'big', range( -1<<63, 1<<63 ), *args, **kwargs )


class UInt16_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'unsigned', 'big', range( 0, 1<<16 ), *args, **kwargs )


class UInt24_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 3, 'unsigned', 'big', range( 0, 1<<24 ), *args, **kwargs )


class UInt32_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'unsigned', 'big', range( 0, 1<<32 ), *args, **kwargs )


class UInt64_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'unsigned', 'big', range( 0, 1<<64 ), *args, **kwargs )


class Float32_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( float, 4, 'signed', 'big', None, *args, **kwargs )


class Float64_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( float, 8, 'signed', 'big', None, *args, **kwargs )


class Int16_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'signed', Ref( '_endian' ), range( -1<<15, 1<<15 ), *args, **kwargs )


class Int24_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 3, 'signed', Ref( '_endian' ), range( -1<<23, 1<<23 ), *args, **kwargs )


class Int32_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'signed', Ref( '_endian' ), range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'signed', Ref( '_endian' ), range( -1<<63, 1<<63 ), *args, **kwargs )


class UInt16_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'unsigned', Ref( '_endian' ), range( 0, 1<<16 ), *args, **kwargs )


class UInt24_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 3, 'unsigned', Ref( '_endian' ), range( 0, 1<<24 ), *args, **kwargs )


class UInt32_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'unsigned', Ref( '_endian' ), range( 0, 1<<32 ), *args, **kwargs )


class UInt64_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'unsigned', Ref( '_endian' ), range( 0, 1<<64 ), *args, **kwargs )


class Float32_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( float, 4, 'signed', Ref( '_endian' ), None, *args, **kwargs )


class Float64_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( float, 8, 'signed', Ref( '_endian' ), None, *args, **kwargs )

