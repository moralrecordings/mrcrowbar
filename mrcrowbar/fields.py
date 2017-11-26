"""Definition classes for common fields in binary formats."""

import struct
import itertools 
import math

from mrcrowbar.refs import *
from mrcrowbar import utils

_next_position_hint = itertools.count()


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
        self.validate( value )
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
    def __init__( self, block_klass, offset, block_kwargs=None, transform=None, stop_check=None, **kwargs ):
        super().__init__( **kwargs )
        self.block_klass = block_klass
        self.offset = offset
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.transform = transform
        self.stop_check = stop_check

    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )

        pointer = offset
        result = []
        while pointer < len( buffer ):
            # run the stop check (if exists): if it returns true, we've hit the end of the stream
            if self.stop_check and (self.stop_check( buffer, pointer )):
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
        
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )
        buffer[offset:offset+len( block_data )] = block_data
        return         

    def get_start_offset( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        return offset


class BlockField( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, count=None, fill=None, **kwargs ):
        super().__init__( **kwargs )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.stride = self.block_klass( **self.block_kwargs ).get_size()
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

        result = []
        fill_pattern = self._get_fill_pattern( self.stride ) if self.fill else None
        for i in range( count ):
            sub_buffer = buffer[offset + i*self.stride:]
            # if data matches the fill pattern, leave a None in the list
            if fill_pattern and sub_buffer[:self.stride] == fill_pattern:
                result.append( None )
            else:
                block = self.block_klass( source_data=sub_buffer, parent=parent, **self.block_kwargs )
                result.append( block )
               
        if not is_array:
            return result[0]
        return result
        
    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )

        block_data = bytearray()
        for b in value:
            if b is None:
                if self.fill:
                    block_data += bytes(( self.fill[j % len(self.fill)] for j in range(self.stride) ))
                else:
                    block_data += b'\x00'*self.stride
            else:
                block_data += b.export_data()
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )
        buffer[offset:offset+len( block_data )] = block_data
        return

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )

        try:
            it = iter( value )
        except TypeError:
            raise FieldValidationError( 'Type {} not iterable'.format( type( value ) ) )
        if count:
            assert len( value ) <= count
        for b in value:
            if (b is not None) and (not isinstance( b, self.block_klass )):
                 raise FieldValidationError( 'Expecting block class {}, not {}'.format( self.block_klass, type( b ) ) )


class Bytes( Field ):
    def __init__( self, offset, length=None, default=None, transform=None, **kwargs ):
        if default is not None:
            assert utils.is_bytes( default )
        else:
            default = b''
        super().__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length
        self.transform = transform

    def get_from_buffer( self, buffer, parent=None, **kwargs ):
        assert utils.is_bytes( buffer )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        data = buffer[offset:]
        if length is not None:
            data = buffer[offset:offset+length]

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

        if len( buffer ) < offset+len( data ):
            buffer.extend( b'\x00'*(offset+len( data )-len( buffer )) )    
        buffer[offset:offset+len( data )] = data
        return

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (length is not None) and (len( value ) != length):
            raise FieldValidationError( 'Expecting length of {}, not {}'.format( length, len( value ) ) )
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
            return 0
            # breaks with transforms :(
            #return len( value )
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
        return len( length )


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
                print( 'Warning: value {} outside of range {}'.format( value, self.range ) )

            # friendly warning if the imported data fails the enum check
            if self.enum:
                if (value not in [x.value for x in self.enum]):
                    print( 'Warning: value {} not castable to {}'.format( value, self.enum ) )
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
        assert count == len( value )

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
        if self.enum:
            if (value not in [x.value for x in self.enum]):
                raise FieldValidationError( 'Value {} not castable to {}'.format( value, self.enum ) )
            value = self.enum(value).value
        if (type( value ) != self.format_type):
            raise FieldValidationError( 'Expecting type {}, not {}'.format( self.format_type, type( value ) ) )
        if self.format_range and (value not in self.format_range):
            raise FieldValidationError( 'Value {} not in format range ({})'.format( value, self.format_range ) )
        if self.range and (value not in self.range):
            raise FieldValidationError( 'Value {} not in range ({})'.format( value, self.range ) )
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
        return self.field_size


class Int8( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<b', 1, int, range( -1<<7, 1<<7 ), *args, **kwargs )


class UInt8( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>B', 1, int, range( 0, 1<<8 ), *args, **kwargs )


class Bits( UInt8 ):
    def __init__( self, offset, bits, default=0, *args, **kwargs ):
        super().__init__( offset, default=default, *args, **kwargs )
        assert type( bits ) == int
        self.mask_bits = bin( bits ).split( 'b', 1 )[1]
        self.bits = [(1<<i) for i, x in enumerate( reversed( self.mask_bits ) ) if x == '1']
        self.format_range = range( 0, 1<<len( self.bits ) )

    def get_from_buffer( self, buffer, parent=None ):
        result = super().get_from_buffer( buffer, parent )
        value = 0
        for i, x in enumerate( self.bits ):
            value += (1 << i) if (result & x) else 0
        return value

    def update_buffer_with_value( self, value, buffer, parent=None ):
        offset = property_get( self.offset, parent )

        for i, x in enumerate( self.bits ):
            buffer[offset] &= 0xff ^ x
            if (value & (1 << i)):
                buffer[offset] |= x
        return
    
    @property
    def repr( self ):
        details = 'offset={}, bits=0b{}'.format( hex( self.offset ), self.mask_bits )
        if self.default:
            details += ', default={}'.format( self.default )
        details


class UInt16_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<H', 2, int, range( 0, 1<<16 ), *args, **kwargs )


class UInt32_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<I', 4, int, range( 0, 1<<32 ), *args, **kwargs )


class UInt64_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<Q', 8, int, range( 0, 1<<64 ), *args, **kwargs )


class Int16_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<h', 2, int, range( -1<<15, 1<<15 ), *args, **kwargs )


class Int32_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<i', 4, int, range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<q', 8, int, range( -1<<63, 1<<63 ), *args, **kwargs )


class Float_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<f', 4, float, None, *args, **kwargs )


class Double_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<d', 8, float, None, *args, **kwargs )


class UInt16_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>H', 2, int, range( 0, 1<<16 ), *args, **kwargs )


class UInt32_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>I', 4, int, range( 0, 1<<32 ), *args, **kwargs )


class UInt64_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>Q', 8, int, range( 0, 1<<64 ), *args, **kwargs )


class Int16_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>h', 2, int, range( -1<<15, 1<<15 ), *args, **kwargs )


class Int32_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>i', 4, int, range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>q', 8, int, range( -1<<63, 1<<63 ), *args, **kwargs )


class Float_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>f', 4, float, None, *args, **kwargs )


class Double_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>d', 8, float, None, *args, **kwargs )


