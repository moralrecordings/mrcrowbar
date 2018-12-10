"""Definition classes for common fields in binary formats."""

import collections
import itertools 
import math
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar.refs import Ref, property_get, property_set
from mrcrowbar import utils, encoding

_next_position_hint = itertools.count()


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
        self._position_hint = next( _next_position_hint )
        self.default = default

    def __repr__( self ):
        desc = '0x{:016x}'.format( id( self ) )
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return '<{}: {}>'.format( self.__class__.__name__, desc )

    repr = None


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
        assert utils.is_bytes( buffer )
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


class StreamField( Field ):
    def __init__( self, offset=mrc.Chain(), count=None, length=None, stream=False,
                    alignment=1, stream_end=None, stop_check=None, **kwargs ):
        super().__init__( **kwargs )
        self.offset = offset
        self.count = count
        self.length = length
        self.stream = stream
        self.alignment = alignment
        if stream_end is not None:
            assert utils.is_bytes( stream_end )
        self.stream_end = stream_end
        self.stop_check = stop_check

    def get_element_from_buffer( self, offset, buffer, parent=None ):
        pass

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
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

            item, end_offset = self.get_element_from_buffer( pointer, buffer, parent )
            result.append( item )
            pointer = end_offset

            # if an alignment is set, do some aligning
            if alignment is not None:
                width = (pointer-start_offset) % alignment
                if width:
                    pointer += alignment - width

        if not is_array:
            return result[0]
        return result

    def update_buffer_with_element( self, offset, element, buffer, parent ):
        pass

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
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
        for item in value:
            start_offset = pointer
            end_offset = self.update_buffer_with_element( self, pointer, item, buffer, parent )
            pointer = end_offset

            if alignment is not None:
                width = (pointer-start_offset) % alignment
                if width:
                    pointer += alignment - width


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
        offset = property_get( self.offset, parent )
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

        for item in value:
            self.validate_element( element, parent=None )

    def get_element_size_calc( self, element, parent=None ):
        pass

    def get_start_offset( self, value, parent=None, index=None ):
        offset = property_get( self.offset, parent )
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
            for item in value[:index]:
                start_offset = pointer
                pointer += self.get_element_size_calc( element, parent )
                # if an alignment is set, do some aligning
                if alignment is not None:
                    width = (pointer-start_offset) % alignment
                    if width:
                        pointer += alignment - width

        return pointer

    def get_size( self, value, parent=None, index=None ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
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
        for item in value:
            pointer += get_element_size_calc( item, parent )
            # if an alignment is set, do some aligning
            if alignment is not None:
                width = (pointer-start_offset) % alignment
                if width:
                    pointer += alignment - width
        return pointer - start



Chunk = collections.namedtuple( 'Chunk', ['id', 'obj'] )


class ChunkField( Field ):
    """Field for inserting a tokenised Block stream into the parent class.
    
    chunk_map
        A dict mapping between the chunk 

    offset
        Position of data, relative to the start of the parent block.

    length
        Maximum size of the buffer to read in.

    default_klass
        Fallback Block class to use if there's no match with the chunk_map mapping.

    chunk_id_size
        Size in bytes of the Chunk ID.

    chunk_id_field
        Field class used to parse Chunk ID. Defaults to Bytes.

    chunk_length_field
        Field class used to parse the Chunk data length. For use when a Chunk consists of an ID followed by the size of the data.
       
    alignment
        Number of bytes to align the start of each Chunk to.
    """
    def __init__( self, chunk_map, offset, length=None, default_klass=None, chunk_id_size=None, chunk_id_field=None, chunk_length_field=None, alignment=1, **kwargs ):
        super().__init__( **kwargs )
        self.offset = offset
        self.chunk_map = chunk_map
        self.length = length
        self.alignment = alignment
        if chunk_length_field:
            assert issubclass( chunk_length_field, NumberField )
            self.chunk_length_field = chunk_length_field( 0x00 )
        else:
            self.chunk_length_field = None
        if chunk_id_field:
            assert issubclass( chunk_id_field, NumberField )
            self.chunk_id_field = chunk_id_field( 0x00 )
        else:
            self.chunk_id_field = None
        self.default_klass = default_klass
        
        self.chunk_id_size = chunk_id_size
        
    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        chunk_map = property_get( self.chunk_map, parent )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )
        data = buffer[offset:]
        if length:
            data = data[:length]
            
        result = []
        pointer = 0
        while pointer < len( data ):
            start_offset = pointer
            chunk_id = None
            if self.chunk_id_field:
                chunk_id = self.chunk_id_field.get_from_buffer( data[pointer:], parent=parent )
                pointer += self.chunk_id_field.field_size
            elif self.chunk_id_size:
                chunk_id = data[pointer:pointer+self.chunk_id_size]
                pointer += len( chunk_id )
            else:
                for test_id in chunk_map:
                    if data[pointer:].startswith( test_id ):
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
                size = self.chunk_length_field.get_from_buffer( data[pointer:], parent=parent )
                pointer += self.chunk_length_field.field_size
                chunk = chunk_klass( data[pointer:pointer+size], parent=parent )
                result.append( Chunk( id=chunk_id, obj=chunk ) )
                pointer += size
            else:
                chunk = chunk_klass( data[pointer:], parent=parent )
                result.append( Chunk( id=chunk_id, obj=chunk ) )
                pointer += chunk.get_size()
            if self.alignment:
                width = (pointer-start_offset) % self.alignment
                if width:
                    pointer += self.alignment - width

        return result
    
    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        chunk_map = property_get( self.chunk_map, parent )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )
        

    def get_start_offset( self, value, parent=None, index=None ):
        offset = property_get( self.offset, parent )
        if index is not None:
            offset += self._size_calc( value[:index] )
        return offset

    def get_size( self, value, parent=None, index=None ):
        value = value if value else []
        if index is not None:
            value = [value[index]]
        size = self._size_calc( value, parent )

        return size

    def _size_calc( self, value, parent=None ):
        size = 0
        for key, b in value:
            start_size = size
            if self.chunk_id_field:
                size += self.chunk_id_field.field_size
            else:
                size += len( key )
            if self.chunk_length_field:
                size += self.chunk_length_field.field_size
            size += b.get_size()
            if self.alignment:
                width = (size-start_size) % self.alignment
                if width:
                    size += self.alignment - width

        return size


class BlockField( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, count=None, fill=None,
                    block_type=None, default_klass=None, length=None, stream=False,
                    alignment=1, transform=None, stream_end=None, stop_check=None,
                    **kwargs ):
        """Field for inserting another Block into the parent class.

        block_klass
            Block class to use, or a dict mapping between type and block class.

        offset
            Position of data, relative to the start of the parent block.

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
        super().__init__( **kwargs )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.block_type = block_type
        # TODO: support different args if using a switch
        self.offset = offset
        self.count = count
        self.fill = fill
        self.default_klass = default_klass
        self.length = length
        self.stream = stream
        self.alignment = alignment
        self.transform = transform
        if stream_end is not None:
            assert utils.is_bytes( stream_end )
        self.stream_end = stream_end
        self.stop_check = stop_check

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        fill = property_get( self.fill, parent )
        stream = property_get( self.stream, parent )

        is_array = stream or (count is not None)
        count = count if is_array else 1
        if count is not None:
            assert count >= 0
        length = property_get( self.length, parent )
        if length is not None:
            buffer = buffer[:offset+length]

        klass = self.get_klass( parent )
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
            # add an empty list entry if we find the fill pattern
            if fill and buffer[pointer:pointer+len( fill )] == fill:
                result.append( None )
                pointer += len( fill )
            # if we have an inline transform, apply it
            elif self.transform:
                data = self.transform.import_data( buffer[pointer:], parent=parent )
                block = klass( source_data=data.payload, parent=parent, **self.block_kwargs )
                result.append( block )
                pointer += data.end_offset
            # add block to results
            else:
                block = klass( source_data=buffer[pointer:], parent=parent, **self.block_kwargs )
                size = block.get_size()
                if size == 0:
                    if stream:
                        raise ParseError( 'Can\'t stream 0 byte Blocks ({}) from a BlockField'.format( klass ) )
                    elif count > 1 and len( result ) == 0:
                        logger.warning( '{}: copying 0 byte Blocks ({}) from a BlockField, this is probably not what you want'.format( self, klass ) )

                result.append( block )
                pointer += size

            # if an alignment is set, do some aligning
            if self.alignment:
                width = (pointer-start_offset) % self.alignment
                if width:
                    pointer += self.alignment - width

        if not is_array:
            return result[0]
        return result
        
    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        fill = property_get( self.fill, parent )

        klass = self.get_klass( parent )
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

        block_data = bytearray()
        for b in value:
            # if an alignment is set, do some aligning
            if self.alignment:
                width = len( block_data ) % self.alignment
                if width:
                    block_data += b'\x00'*(self.alignment - width)

            if b is None:
                if fill:
                    block_data += fill
                else:
                    raise ParseError( 'A fill pattern needs to be specified to use None as a list entry' )
            else:
                data = b.export_data()
                if self.transform:
                    data = self.transform.export_data( data, parent=parent ).payload
                block_data += data

        if self.stream_end is not None:
            block_data += self.stream_end

        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )
        buffer[offset:offset+len( block_data )] = block_data
        return

    def update_deps( self, value, parent=None ):
        count = property_get( self.count, parent )
        if count is not None and count != len( value ):
            property_set( self.count, parent, len( value ) )

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        klass = self.get_klass( parent )
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
        for b in value:
            if (b is not None) and (not isinstance( b, klass )):
                 raise FieldValidationError( 'Expecting block class {}, not {}'.format( klass, type( b ) ) )

    def get_start_offset( self, value, parent=None, index=None ):
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)

        if index is not None:
            if not is_array:
                raise IndexError( 'Can\'t use index for a non-array BlockField' )
            elif index not in range( 0, count ):
                raise IndexError( 'Index {} is not within range( 0, {} )'.format( index, count ) )
            offset += self._size_calc( value[:index] )

        return offset

    def get_size( self, value, parent=None, index=None ):
        count = property_get( self.count, parent )
        stream = property_get( self.stream, parent )
        is_array = stream or (count is not None)

        if index is not None:
            if not is_array:
                raise IndexError( 'Can\'t use index for a non-array BlockField' )
            elif index not in range( 0, count ):
                raise IndexError( 'Index {} is not within range( 0, {} )'.format( index, count ) )
            value = [value[index]]
        else:
            value = value if is_array else [value]

        size = self._size_calc( value, parent )
        if index is None and self.stream_end is not None:
            size += len( self.stream_end )
        return size

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

    def _size_calc( self, value, parent=None ):
        fill = property_get( self.fill, parent )

        size = 0
        for b in value:
            if self.transform:
                data = self.transform.export_data( b.export_data(), parent=parent ).payload
                size += len( data )
            elif b is None:
                if fill:
                    size += len( fill )
                else:
                    raise ParseError( 'A fill pattern needs to be specified to use None as a list entry' )
            else:
                size += b.get_size()
        return size


class Bytes( Field ):
    def __init__( self, offset, length=None, default=None, transform=None, stream_end=None, **kwargs ):
        """Field class for raw byte data.

        offset
            Position of data, relative to the start of the parent block.

        length
            Maximum size of the data in bytes.

        default
            Default byte data. Used for creating an empty block.

        transform
            A Transform to process the data before import/export.

        stream_end
            Byte string to indicate the end of the data.
        """
        if default is not None:
            assert utils.is_bytes( default )
        else:
            default = b''
        super().__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length
        self.transform = transform
        if stream_end is not None:
            assert utils.is_bytes( stream_end )
        self.stream_end = stream_end

    def get_from_buffer( self, buffer, parent=None, **kwargs ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        data = buffer[offset:]
        if self.stream_end is not None:
            end = data.find( self.stream_end )
            if end != -1:
                data = data[:end]
        if length is not None:
            data = data[:length]

        if self.transform:
            data = self.transform.import_data( data, parent=parent ).payload
    
        return data

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        data = value
        if self.transform:
            data = self.transform.export_data( data, parent=parent ).payload

        new_size = offset+len( data )
        if self.stream_end is not None:
            new_size += len( self.stream_end )

        if len( buffer ) < new_size:
            buffer.extend( b'\x00'*(new_size-len( buffer )) )

        buffer[offset:offset+len( data )] = data
        if self.stream_end is not None:
            buffer[offset+len( data ):new_size] = self.stream_end
        return

    def update_deps( self, value, parent=None ):
        length = property_get( self.length, parent )
        if length is not None and length != len( value ):
            property_set( self.length, parent, len( value ) )

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        if length is not None and (not isinstance( self.length, Ref )) and (len( value ) != length):
            raise FieldValidationError( 'Length defined as a constant, was expecting {} bytes but got {}!'.format( length, len( value ) ) )

        if not utils.is_bytes( value ):
            raise FieldValidationError( 'Expecting bytes, not {}'.format( type( value ) ) )
        return

    @property
    def repr( self ):
        details = 'offset={}'.format( hex( self.offset ) )
        if self.length:
            details += ', length={}'.format( self.length )
        if self.default:
            details += ', default={}'.format( self.default )
        if self.transform:
            details += ', transform={}'.format( self.transform )
        return details

    def get_start_offset( self, value, parent=None, index=None ):
        assert index is None
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None, index=None ):
        assert index is None
        length = property_get( self.length, parent )
        if length is None:
            if self.transform:
                data = self.transform.export_data( value, parent=parent ).payload
                return len( data )
            return len( value )
        return length
    

class CString( Field ):
    def __init__( self, offset, default=b'', **kwargs ):
        assert utils.is_bytes( default )
        super().__init__( default=default, **kwargs )
        self.offset = offset

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )

        return buffer[offset:].split( b'\x00', 1 )[0]

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )

        block_data = value + b'\x00'
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )    
        buffer[offset:offset+len( block_data )] = block_data
        return

    def validate( self, value, parent=None ):
        if not utils.is_bytes( value ):
            raise FieldValidationError( 'Expecting bytes, not {}'.format( type( value ) ) )
        return 

    def get_start_offset( self, value, parent=None, index=None ):
        assert index is None
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None, index=None ):
        assert index is None
        return len( value )


class CStringN( Field ):
    def __init__( self, offset, length, default=b'', **kwargs ):
        assert utils.is_bytes( default )
        super().__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        return buffer[offset:offset+length].split( b'\x00', 1 )[0]

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
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
        offset = property_get( self.offset, parent )
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
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
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
        offset = property_get( self.offset, parent )
        length = self.length_field.field_size

        pointer = offset
        for s in value:
            assert utils.is_bytes( s )
            string_data = s+b'\x00'
            self.length_field.offset = pointer
            self.length_field.update_buffer_with_value( len( string_data ), buffer )
            pointer += length
            buffer[pointer:pointer+len( string_data )] = string_data
            pointer += len( string_data )

    def get_start_offset( self, value, parent=None, index=None ):
        assert index is None
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None, index=None ):
        assert index is None
        size = 0
        for x in value:
            size += self.length_field.field_size
            size += len( x )
        return size


class NumberField( Field ):
    def __init__( self, format_type, field_size, signedness, endian, format_range, offset, default=0, count=None, bitmask=None, range=None, enum=None, **kwargs ):
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
            Position of data, relative to the start of the parent block.

        default
            Default value of field. Used for creating an empty block.

        count
            Interpret data as an array of this size. None implies a single value, non-negative
            numbers will return a Python list.

        bitmask
            Apply AND mask (bytes) to data before reading/writing. Used for demultiplexing
            data to multiple fields, e.g. one byte with 8 flag fields.

        range
            Restrict allowed values to a list of choices. Used for validation

        enum
            Restrict allowed values to those provided by a Python enum type. Used for validation.
        """
        super().__init__( default=default, **kwargs )
        self.format_type = format_type
        self.field_size = field_size
        self.signedness = signedness
        self.endian = endian
        self.format_range = format_range
        self.offset = offset
        if bitmask:
            assert utils.is_bytes( bitmask )
            assert len( bitmask ) == field_size
        self.count = count
        self.bitmask = bitmask
        self.range = range
        self.enum = enum

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        endian = property_get( self.endian, parent )
        is_array = count is not None
        count = count if is_array else 1
        assert count >= 0

        result = []
        for i in range( count ):
            start = offset+self.field_size*i
            data = buffer[start:start+self.field_size]
            assert len( data ) == self.field_size
            if self.bitmask:
                # if a bitmask is defined, AND with it first
                data = (int.from_bytes( data, byteorder='big' ) & 
                        int.from_bytes( self.bitmask, byteorder='big' )
                        ).to_bytes( self.field_size, byteorder='big' )

            # convert bytes to Python type
            value = encoding.unpack( (self.format_type, self.field_size, self.signedness, endian), data )
            # friendly warnings if the imported data fails the range check
            if self.range and (value not in self.range):
                logger.warning( '{}: value {} outside of range {}'.format( self, value, self.range ) )

            # friendly warning if the imported data fails the enum check
            if self.enum:
                if (value not in [x.value for x in self.enum]):
                    logger.warning( '{}: value {} not castable to {}'.format( self, value, self.enum ) )
                else:
                    # cast to enum because why not
                    value = self.enum( value )

            result.append( value )

        if not is_array:
            return result[0]
        return result

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        endian = property_get( self.endian, parent )
        is_array = count is not None
        count = count if is_array else 1
        assert count >= 0

        if not is_array:
            value = [value]

        if (len( buffer ) < offset+self.field_size*count):
            buffer.extend( b'\x00'*(offset+self.field_size*count-len( buffer )) )
        for j in range( count ):
            start = offset+self.field_size*j
            item = value[j]
            # cast via enum if required
            if self.enum:
                item = self.enum( item ).value
            data = encoding.pack( (self.format_type, self.field_size, self.signedness, endian), item )
            
            # force check for no data loss in the value from bitmask
            if self.bitmask:
                assert (int.from_bytes( data, byteorder='big' ) & 
                        int.from_bytes( self.bitmask, byteorder='big' ) ==
                        int.from_bytes( data, byteorder='big' ))
            
                for i in range( self.field_size ):
                    # set bitmasked areas of target to 0
                    buffer[start+i] &= (self.bitmask[i] ^ 0xff)
                    # OR target with replacement bitmasked portion
                    buffer[start+i] |= (data[i] & self.bitmask[i])
            else:
                for i in range( self.field_size ):
                    buffer[start+i] = data[i]
        return

    def update_deps( self, value, parent=None ):
        count = property_get( self.count, parent )
        if count is not None and count != len( value ):
            property_set( self.count, parent, len( value ) )

    def validate( self, value, parent=None ):
        count = property_get( self.count, parent )
        is_array = count is not None
        count = count if is_array else 1
        if not is_array:
            value = [value]

        for i in range( len( value ) ):
            if self.enum:
                if (value[i] not in [x.value for x in self.enum]):
                    raise FieldValidationError( 'Value {} not castable to {}'.format( value, self.enum ) )
                value[i] = self.enum( value[i] ).value
            if (type( value[i] ) != self.format_type):
                raise FieldValidationError( 'Expecting type {}, not {}'.format( self.format_type, type( value[i] ) ) )
            if self.format_range and (value[i] not in self.format_range):
                raise FieldValidationError( 'Value {} not in format range ({})'.format( value[i], self.format_range ) )
            if self.range and (value[i] not in self.range):
                raise FieldValidationError( 'Value {} not in range ({})'.format( value[i], self.range ) )
        return

    @property
    def repr( self ):
        details = 'offset={}'.format( hex( self.offset ) )
        if self.default:
            details += ', default={}'.format( self.default )
        if self.range:
            details += ', range={}'.format( self.range )
        if self.bitmask:
            details += ', bitmask={}'.format( self.bitmask )
        return details

    def get_start_offset( self, value, parent=None, index=None ):
        assert index is None
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None, index=None ):
        assert index is None
        count = property_get( self.count, parent )
        if count:
            return self.field_size*count
        return self.field_size


class Int8( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 1, 'signed', None, range( -1<<7, 1<<7 ), *args, **kwargs )


class UInt8( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 1, 'unsigned', None, range( 0, 1<<8 ), *args, **kwargs )


class Bits( NumberField ):
    def __init__( self, offset, bits, default=0, size=1, enum=None, endian=None, *args, **kwargs ):
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
        self.enum_t = enum
        bitmask = encoding.pack( SIZES[size][:4], bits )
        super().__init__( *SIZES[size], offset, default=default, bitmask=bitmask, *args, **kwargs )

    def get_from_buffer( self, buffer, parent=None ):
        result = super().get_from_buffer( buffer, parent )
        value = 0
        for i, x in enumerate( self.bits ):
            value += (1 << i) if (result & x) else 0
        if self.enum_t:
            if (value not in [x.value for x in self.enum_t]):
                logger.warning( '{}: value {} not castable to {}'.format( self, value, self.enum_t ) )
            else:
                # cast to enum because why not
                value = self.enum_t( value )
        return value

    def update_buffer_with_value( self, value, buffer, parent=None ):
        assert value in self.check_range
        if self.enum_t:
            value = self.enum_t( value ).value
        packed = 0
        for i, x in enumerate( self.bits ):
            if (value & (1 << i)):
                packed |= x

        super().update_buffer_with_value( packed, buffer, parent )
        return

    def validate( self, value, parent=None ):
        if self.enum_t:
            if (value not in [x.value for x in self.enum_t]):
                raise FieldValidationError( 'Value {} not castable to {}'.format( value, self.enum_t ) )
            value = self.enum_t( value ).value
        super().validate( value, parent )

    @property
    def repr( self ):
        details = 'offset={}, bits=0b{}'.format( hex( self.offset ), self.mask_bits )
        if self.default:
            details += ', default={}'.format( self.default )
        details


class Int16_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'signed', 'little', range( -1<<15, 1<<15 ), *args, **kwargs )


class Int32_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'signed', 'little', range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'signed', 'little', range( -1<<63, 1<<63 ), *args, **kwargs )


class UInt16_LE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'unsigned', 'little', range( 0, 1<<16 ), *args, **kwargs )


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


class Int32_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'signed', 'big', range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'signed', 'big', range( -1<<63, 1<<63 ), *args, **kwargs )


class UInt16_BE( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'unsigned', 'big', range( 0, 1<<16 ), *args, **kwargs )


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


class Int32_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 4, 'signed', Ref( '_endian' ), range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 8, 'signed', Ref( '_endian' ), range( -1<<63, 1<<63 ), *args, **kwargs )


class UInt16_P( NumberField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( int, 2, 'unsigned', Ref( '_endian' ), range( 0, 1<<16 ), *args, **kwargs )


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

