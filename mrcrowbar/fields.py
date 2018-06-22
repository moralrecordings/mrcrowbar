"""Definition classes for common fields in binary formats."""

import struct
import itertools 
import math
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar.refs import Ref, property_get, property_set
from mrcrowbar import utils

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
    
    def get_start_offset( self, value, parent=None ):
        """Return the start offset of where the Field's data is to be stored in the Block.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return 0

    def get_size( self, value, parent=None ):
        """Return the size of the field data (in bytes).

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return 0

    def get_end_offset( self, value, parent=None ):
        """Return the end offset of the Field's data. Useful for chainloading.

        value
            Input Python object to process.

        parent
            Parent block object where this Field is defined. Used for e.g.
            evaluating Refs.
        """
        return self.get_start_offset( value, parent ) + self.get_size( value, parent )

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


class BlockStream( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, transform=None, stop_check=None, length=None, stream_end=None, **kwargs ):
        super().__init__( **kwargs )
        self.block_klass = block_klass
        self.offset = offset
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.transform = transform
        self.stop_check = stop_check
        self.length = length
        if stream_end is not None:
            assert utils.is_bytes( stream_end )
        self.stream_end = stream_end

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )
        if length is not None:
            buffer = buffer[:offset+length]

        pointer = offset
        result = []
        while pointer < len( buffer ):
            # run the stop check (if exists): if it returns true, we've hit the end of the stream
            if self.stop_check and (self.stop_check( buffer, pointer )):
                break
            if self.stream_end is not None and buffer[pointer:pointer+len( self.stream_end )] == self.stream_end:
                break
            if self.transform:
                data = self.transform.import_data( buffer[pointer:], parent=parent )
                block = self.block_klass( source_data=data['payload'], parent=parent, **self.block_kwargs )
                result.append( block )
                pointer += data['end_offset']
            else:
                block = self.block_klass( source_data=buffer[pointer:], parent=parent, **self.block_kwargs )
                size = block.get_size()
                assert size > 0
                result.append( block )
                pointer += size
        return result

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        
        pointer = offset
        block_data = bytearray()
        for b in value:
            data = b.export_data()
            if self.transform:
                data = self.transform.export_data( data, parent=parent )['payload']
            block_data += data
        
        if self.stream_end is not None:
            block_data += self.stream_end

        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )
        buffer[offset:offset+len( block_data )] = block_data
        return         

    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None ):
        size = 0
        value = value if value else []
        for b in value:
            if self.transform:
                data = self.transform.export_data( b.export_data(), parent=parent )['payload']
                size += len( data )
            else:
                size += b.get_size()

        if self.stream_end is not None:
            size += len( self.stream_end )
        return size


class ChunkStream( Field ):
    def __init__( self, offset, chunk_map, length=None, default_chunk=None, chunk_id_size=None, length_field=None, alignment=1, **kwargs ):
        super().__init__( **kwargs )
        self.offset = offset
        self.chunk_map = chunk_map
        self.length = length
        self.alignment = alignment
        if length_field:
            assert issubclass( length_field, ValueField )
            self.length_field = length_field( 0x00 )
        else:
            self.length_field = None
        self.default_chunk = default_chunk
        
        self.chunk_id_size=chunk_id_size
        #for chunk_id, chunk in self.chunk_map:
        #    assert utils.is_bytes( chunk_id )
        #    if self.chunk_id_size:
        #        assert len( chunk_id ) == self.chunk_id_size

        
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
            if self.chunk_id_size:
                chunk_id = data[pointer:pointer+self.chunk_id_size]
            else:
                for test_id in chunk_map:
                    if data[pointer:].startswith( test_id ):
                        chunk_id = test_id
                        break
                if not chunk_id:
                    raise ParseError( 'Could not find matching chunk at offset {}'.format( pointer ) )
            if chunk_id in chunk_map:
                chunk_klass = chunk_map[chunk_id]
            elif self.default_chunk:
                chunk_klass = self.default_chunk
            else:
                raise ParseError( 'No chunk class match for ID {}'.format( chunk_id ) )

            pointer += len( chunk_id )
            if self.length_field:
                size = self.length_field.get_from_buffer( data[pointer:] )
                pointer += self.length_field.field_size
                chunk = chunk_klass( data[pointer:pointer+size] )
                result.append( (chunk_id, chunk) )
                pointer += size
            else:
                chunk = chunk_klass( data[pointer:] )
                result.append( (chunk_id, chunk) )
                pointer += chunk.get_size()
            if self.alignment:
                width = (pointer-start_offset) % self.alignment
                if width:
                    pointer += self.alignment - width

        return result
            
    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset



class BlockField( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, count=None, fill=None, block_type=None, **kwargs ):
        """Field for inserting another Block into the parent class.

        block_klass
            Block class to use, or a dict mapping between type and block class.

        offset
            Position of data, relative to the start of the parent block.

        block_kwargs
            Arguments to be passed to the constructor of the block class.

        count
            Interpret data as an array of this size. None implies a single value, non-negative
            numbers will return a Python list.

        fill
            Byte pattern to apply to denote an empty entry in a list.

        block_type
            Key to use with the block_klass mapping. (Usually a Ref for a property on the parent block)

        """
        super().__init__( **kwargs )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.block_type = block_type
        # TODO: support different args if using a switch
        self.offset = offset
        self.count = count
        if fill:
            assert utils.is_bytes( fill )
        self.fill = fill

    def _get_fill_pattern( self, length ):
        if self.fill:
            return (self.fill*math.ceil( length/len( self.fill ) ))[:length]
        return None

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        is_array = count is not None
        count = count if is_array else 1
        assert count >= 0  
        klass = self.get_klass( parent )
        stride = klass( parent=parent, **self.block_kwargs ).get_size()

        result = []
        fill_pattern = self._get_fill_pattern( stride ) if self.fill else None
        for i in range( count ):
            sub_buffer = buffer[offset + i*stride:]
            # if data matches the fill pattern, leave a None in the list
            if fill_pattern and sub_buffer[:stride] == fill_pattern:
                result.append( None )
            else:
                block = klass( source_data=sub_buffer, parent=parent, **self.block_kwargs )
                result.append( block )
               
        if not is_array:
            return result[0]
        return result
        
    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        klass = self.get_klass( parent )
        stride = klass( parent=parent, **self.block_kwargs ).get_size()
        is_array = count is not None

        if is_array:
            try:
                it = iter( value )
            except TypeError:
                raise FieldValidationError( 'Type {} not iterable'.format( type( value ) ) )
            assert len( value ) <= count
        else:
            value = [value]

        block_data = bytearray()
        for b in value:
            if b is None:
                if self.fill:
                    block_data += bytes(( self.fill[j % len(self.fill)] for j in range( stride ) ))
                else:
                    block_data += b'\x00'*stride
            else:
                block_data += b.export_data()
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )
        buffer[offset:offset+len( block_data )] = block_data
        return

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
        klass = self.get_klass( parent )
        is_array = count is not None

        if is_array:
            try:
                it = iter( value )
            except TypeError:
                raise FieldValidationError( 'Type {} not iterable'.format( type( value ) ) )
            assert len( value ) <= count
        else:
            value = [value]
        for b in value:
            if (b is not None) and (not isinstance( b, klass )):
                 raise FieldValidationError( 'Expecting block class {}, not {}'.format( self.block_klass, type( b ) ) )

    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None ):
        # TODO: current design assumes blocks are fixed size, maybe change this to introspection?
        count = property_get( self.count, parent )
        klass = self.get_klass( parent )
        stride = klass( parent=parent, **self.block_kwargs ).get_size()
        if count is not None:
            return stride*count
        return stride

    def get_klass( self, parent=None ):
        if isinstance( self.block_klass, dict ):
            block_type = property_get( self.block_type, parent )
            return self.block_klass[block_type]
        return self.block_klass


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
            data = self.transform.import_data( data, parent=parent )['payload']
    
        return data

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        data = value
        if self.transform:
            data = self.transform.export_data( data, parent=parent )['payload']

        if length is not None and length != len( value ):
            property_set( self.length, parent, len( value ) )

        new_size = offset+len( data )
        if self.stream_end is not None:
            new_size += len( self.stream_end )

        if len( buffer ) < new_size:
            buffer.extend( b'\x00'*(new_size-len( buffer )) )

        buffer[offset:offset+len( data )] = data
        if self.stream_end is not None:
            buffer[offset+len( data ):new_size] = self.stream_end
        return

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        if length is not None and (not isinstance( self.length, Ref )) and (len( value ) != length):
            raise FieldValidationError( 'Length defined as a constant, was expecting {} bytes but got {}!'.format( length, len( value ) ) )

        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
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

    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None ):
        length = property_get( self.length, parent )
        if length is None:
            if self.transform:
                data = self.transform.export_data( value, parent=parent )['payload']
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
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        return 

    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None ):
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
    
    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None ):
        length = property_get( self.length, parent )
        return length


class CStringNStream( Field ):
    def __init__( self, offset, length_field, **kwargs ):
        assert issubclass( length_field, ValueField )
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

    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None ):
        size = 0
        for x in value:
            size += self.length_field.field_size
            size += len( x )
        return size


class ValueField( Field ):
    def __init__( self, format, field_size, format_type, format_range, offset, default=0, count=None, bitmask=None, range=None, enum=None, **kwargs ):
        """Base class for numeric value Fields.

        format
            Data format, represented as a Python 'struct' module format string. (Usually defined by child class)

        field_size
            Size of field in bytes. (Usually defined by child class)

        format_type
            Python native type equivalent. Used for validation. (Usually defined by child class)

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
        self.offset = offset
        self.format = format
        self.format_type = format_type
        self.format_range = format_range
        if bitmask:
            assert utils.is_bytes( bitmask )
            assert len( bitmask ) == field_size
        self.count = count
        self.field_size = field_size
        self.bitmask = bitmask
        self.range = range
        self.enum = enum

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )
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

            # use Python's struct module to convert bytes to native
            value = struct.unpack( self.format, data )[0]
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
        is_array = count is not None
        count = count if is_array else 1
        assert count >= 0

        if not is_array:
            value = [value]
        if not count == len( value ):
            property_set( self.count, parent, len( value ) )
            count = len( value )

        if (len( buffer ) < offset+self.field_size*count):
            buffer.extend( b'\x00'*(offset+self.field_size*count-len( buffer )) )
        for j in range( count ):
            start = offset+self.field_size*j
            item = value[j]
            # cast via enum if required
            if self.enum:
                item = self.enum( item ).value
            data = struct.pack( self.format, item )
            
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

    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None ):
        count = property_get( self.count, parent )
        if count:
            return self.field_size*count
        return self.field_size


class Int8( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<b', 1, int, range( -1<<7, 1<<7 ), *args, **kwargs )


class UInt8( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>B', 1, int, range( 0, 1<<8 ), *args, **kwargs )


class Bits( ValueField ):
    def __init__( self, offset, bits, default=0, size=1, enum=None, *args, **kwargs ):
        SIZES = {
            1: ('>B', 1, int, range( 0, 1<<8 )),
            2: ('>H', 2, int, range( 0, 1<<16 )),
            4: ('>I', 4, int, range( 0, 1<<32 )),
            8: ('>Q', 8, int, range( 0, 1<<64 )),
        }
        assert size in SIZES
        assert type( bits ) == int
        assert (bits >= 0)
        assert (bits < 1<<(8*size))

        self.mask_bits = bin( bits ).split( 'b', 1 )[1]
        self.bits = [(1<<i) for i, x in enumerate( reversed( self.mask_bits ) ) if x == '1']
        self.check_range = range( 0, 1<<len( self.bits ) )
        self.enum_t = enum
        bitmask = struct.pack( SIZES[size][0], bits )
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
                raise FieldValidationError( 'Value {} not castable to {}'.format( value, self.enum ) )
            value = self.enum_t(value).value
        super().validate( value, parent )

    @property
    def repr( self ):
        details = 'offset={}, bits=0b{}'.format( hex( self.offset ), self.mask_bits )
        if self.default:
            details += ', default={}'.format( self.default )
        details


class UInt16_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<H', 2, int, range( 0, 1<<16 ), *args, **kwargs )


class UInt32_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<I', 4, int, range( 0, 1<<32 ), *args, **kwargs )


class UInt64_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<Q', 8, int, range( 0, 1<<64 ), *args, **kwargs )


class Int16_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<h', 2, int, range( -1<<15, 1<<15 ), *args, **kwargs )


class Int32_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<i', 4, int, range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<q', 8, int, range( -1<<63, 1<<63 ), *args, **kwargs )


class Float_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<f', 4, float, None, *args, **kwargs )


class Double_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '<d', 8, float, None, *args, **kwargs )


class UInt16_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>H', 2, int, range( 0, 1<<16 ), *args, **kwargs )


class UInt32_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>I', 4, int, range( 0, 1<<32 ), *args, **kwargs )


class UInt64_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>Q', 8, int, range( 0, 1<<64 ), *args, **kwargs )


class Int16_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>h', 2, int, range( -1<<15, 1<<15 ), *args, **kwargs )


class Int32_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>i', 4, int, range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>q', 8, int, range( -1<<63, 1<<63 ), *args, **kwargs )


class Float_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>f', 4, float, None, *args, **kwargs )


class Double_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        super().__init__( '>d', 8, float, None, *args, **kwargs )


