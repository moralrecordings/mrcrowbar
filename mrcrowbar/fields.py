import struct
import itertools 
from array import array as arr

_next_position_hint = itertools.count()


class FieldValidationError( Exception ):
    pass


class Field:
    def __init__( self, default=None, **kwargs ):
        self._position_hint = next( _next_position_hint )
        self.default = default

    def get_from_buffer( self, buffer ):
        return None

    def update_array_with_value( self, value, array ):
        assert type( array ) == arr
        assert array.typecode == 'B'
        self.validate( value )
        return

    def validate( self, value ):
        pass 


class BlockStream( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, stride=0, count=0, stop_check=None, fill=None, transform=None, **kwargs ):
        super( BlockStream, self ).__init__( **kwargs )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.offset = offset
        self.stride = stride
        self.count = count
        self.stop_check = stop_check
        self.fill = fill
        self.transform = transform

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        result = []
        if self.transform:
            result = [self.block_klass( x, **self.block_kwargs ) for x in self.transform.import_data( buffer[self.offset:] )]
        else:
            for i in range( self.count ):
                sub_buffer = buffer[self.offset + i*self.stride:]
                # truncate input buffer to block size, if present
                if self.block_klass._block_size:
                    sub_buffer = sub_buffer[:self.block_klass._block_size]
                # if data matches the fill pattern, leave a None in the list
                if self.fill and (sub_buffer == bytes(( self.fill[j % len(self.fill)] for j in range(len(sub_buffer)) ))):
                    result.append( None )
                else:
                    # run the stop check (if exists): if it returns true, we've hit the end of the stream
                    if self.stop_check and (self.stop_check( buffer, self.offset+i*self.stride )):
                        break

                    result.append( self.block_klass( sub_buffer ) )
                    
                    
        return result
        
    def validate( self, value ):
        try:
            it = iter( value )
        except TypeError:
            raise FieldValidationError( 'Type {} not iterable'.format( type( value ) ) )
        if self.count:
            assert len( value ) <= self.count
        for b in value:
            if b:
                assert type( b ) == self.block_klass 


class BlockField( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, fill=None, transform=None, **kwargs ):
        super( BlockField, self ).__init__( **kwargs )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.offset = offset
        self.fill = fill
        self.transform = transform

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        result = None
        if self.transform:
            result = self.block_klass( self.transform.import_data( buffer[self.offset:] ), **self.block_kwargs )
        else:
            result = self.block_klass( buffer[self.offset:], **self.block_kwargs )

        return result
        #return (self.fill*int( 1+self.block_klass._block_size/len(self.fill) ))[:self.block_klass._block_size]


class Bytes( Field ):
    def __init__( self, offset, length=None, fill=b'\x00', default=None, **kwargs ):
        if length is not None:
            if default is not None:
                assert type( default ) == bytes
                assert len( default ) == length
            else:
                default = b'\x00'*length
        else:
            if default is not None:
                assert type( default ) == bytes
            else:
                default = b''
        super( Bytes, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        if self.length is not None:
            return buffer[self.offset:self.offset+self.length]
        else:
            return buffer[self.offset:]

    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (self.length is not None) and (len( value ) != self.length):
            raise FieldValidationError( 'Expecting length of {}, not {}'.format( self.length, len( value ) ) )
        return


class CString( Field ):
    def __init__( self, offset, default=b'', **kwargs ):
        assert type( default ) == bytes
        super( CString, self ).__init__( default=default, **kwargs )
        self.offset = offset

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        return buffer.split( b'\x00', 1, **kwargs )[0]

    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        return 

class CStringN( Field ):
    def __init__( self, offset, length, default=b'', **kwargs ):
        assert type( default ) == bytes
        super( CStringN, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        return buffer[self.offset:self.offset+self.length].split( b'\x00', 1, **kwargs )[0]

    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (len( value ) > self.length):
            raise FieldValidationError( 'Expecting length <= {}, not {}'.format( self.length, len( value ) ) )
        return
    

class ValueField( Field ):
    def __init__( self, offset, format, size, format_type, format_range, default=0, bitmask=None, range=None, **kwargs ):
        super( ValueField, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.format = format
        self.format_type = format_type
        self.format_range = format_range
        if bitmask:
            assert type( bitmask ) == bytes
            assert len( bitmask ) == size
        self.size = size
        self.bitmask = bitmask
        self.range = range

    def _get_bytes( self, buffer ):
        data = buffer[self.offset:self.offset+self.size]
        assert len( data ) == self.size
        if self.bitmask:
            return (int.from_bytes( data, byteorder='big' ) & 
                    int.from_bytes( self.bitmask, byteorder='big' )
                    ).to_bytes( self.size, byteorder='big' )
        else:
            return data

    def _set_bytes( self, data, array ):
        # force check for no data loss in the value from bitmask
        if self.bitmask:
            assert (int.from_bytes( data, byteorder='big' ) & 
                    int.from_bytes( self.bitmask, byteorder='big' ) ==
                    int.from_bytes( data, byteorder='big' ))
        
            for i in range( self.size ):
                # set bitmasked areas of target to 0
                array[i+self.offset] &= (~ self.bitmask[i])
                # OR target with replacement bitmasked portion
                array[i+self.offset] |= (data[i] & self.bitmask[i])
        else:
            for i in range( self.size ):
                array[i+self.offset] = data[i]
        return

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        value = struct.unpack( self.format, self._get_bytes( buffer ) )[0]
        if self.range and (value not in self.range):
            print( 'WARNING: value {} outside of range {}'.format( value, self.range ) )
        return value

    def update_array_with_value( self, value, array ):
        super( ValueField, self ).update_array_with_value( value, array )
        if (len( array ) < self.offset+self.size):
            array.extend( b'\x00'*(self.offset+self.size-len( array )) )
        data = struct.pack( self.format, value ) 
        self._set_bytes( data, array )
        return

    def validate( self, value ):
        if (type( value ) != self.format_type):
            raise FieldValidationError( 'Expecting type {}, not {}'.format( self.format_type, type( value ) ) )
        if self.format_range and (value not in self.format_range):
            raise FieldValidationError( 'Value {} not in format range ({})'.format( value, self.format_range ) )
        if self.range and (value not in self.range):
            raise FieldValidationError( 'Value {} not in range ({})'.format( value, self.range ) )
        return


class Int8( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<b', 1, int, range(-1<<7, 1<<7), **kwargs )


class UInt8( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>B', 1, int, range( 0, 1<<8 ), **kwargs )


class Bits( UInt8 ):
    def __init__( self, offset, bits, default=0, **kwargs ):
        UInt8.__init__( self, offset, default=default, **kwargs )
        assert type( bits ) == int
        mask_bits = bin( bits ).split('b', 1)[1]
        self.bits = [(1<<i) for i, x in enumerate( reversed( mask_bits ) ) if x == '1']
        self.format_range = range( 0, 1<<len(self.bits) )

    def get_from_buffer( self, buffer ):
        result = UInt8.get_from_buffer( self, buffer )
        value = 0
        for i, x in enumerate( self.bits ):
            value += (1 << i) if (result & x) else 0
        return value


class UInt16_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<H', 2, int, range( 0, 1<<16 ), **kwargs )


class UInt32_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<I', 4, int, range( 0, 1<<32 ), **kwargs )


class UInt64_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<Q', 8, int, range( 0, 1<<64 ), **kwargs )


class Int16_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<h', 2, int, range( -1<<15, 1<<15 ), **kwargs )


class Int32_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<i', 4, int, range( -1<<31, 1<<31 ), **kwargs )


class Int64_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<q', 8, int, range( -1<<63, 1<<63 ), **kwargs )


class Float_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<f', 4, float, None, **kwargs )


class Double_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<d', 8, float, None, **kwargs )


class UInt16_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>H', 2, int, range( 0, 1<<16 ), **kwargs )


class UInt32_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>I', 4, int, range( 0, 1<<32 ), **kwargs )


class UInt64_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>Q', 8, int, range( 0, 1<<64 ), **kwargs )


class Int16_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>h', 2, int, range( -1<<15, 1<<15 ), **kwargs )


class Int32_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>i', 4, int, range( -1<<31, 1<<31 ), **kwargs )


class Int64_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>q', 8, int, range( -1<<63, 1<<63 ), **kwargs )


class Float_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>f', 4, float, None,  **kwargs )


class Double_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>d', 8, float, None,  **kwargs )


