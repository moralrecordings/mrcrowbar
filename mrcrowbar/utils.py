import struct

from_byte_type =    lambda format, size, buffer: struct.unpack( format, buffer[:size] )[0]
to_byte_type =      lambda format, value: struct.pack( format, value )

from_int8 =         lambda buffer: from_byte_type( '<b', 1, buffer )
from_uint8 =        lambda buffer: from_byte_type( '>B', 1, buffer )
from_uint16_le =    lambda buffer: from_byte_type( '<H', 2, buffer )
from_uint32_le =    lambda buffer: from_byte_type( '<I', 4, buffer )
from_uint64_le =    lambda buffer: from_byte_type( '<Q', 8, buffer )
from_int16_le =     lambda buffer: from_byte_type( '<h', 2, buffer )
from_int32_le =     lambda buffer: from_byte_type( '<i', 4, buffer )
from_int64_le =     lambda buffer: from_byte_type( '<q', 8, buffer )
from_float_le =     lambda buffer: from_byte_type( '<f', 4, buffer )
from_double_le =    lambda buffer: from_byte_type( '<d', 8, buffer )
from_uint16_be =    lambda buffer: from_byte_type( '>H', 2, buffer )
from_uint32_be =    lambda buffer: from_byte_type( '>I', 4, buffer )
from_uint64_be =    lambda buffer: from_byte_type( '>Q', 8, buffer )
from_int16_be =     lambda buffer: from_byte_type( '>h', 2, buffer )
from_int32_be =     lambda buffer: from_byte_type( '>i', 4, buffer )
from_int64_be =     lambda buffer: from_byte_type( '>q', 8, buffer )
from_float_be =     lambda buffer: from_byte_type( '>f', 4, buffer )
from_double_be =    lambda buffer: from_byte_type( '>d', 8, buffer )

to_int8 =           lambda value: to_byte_type( '<b', value )
to_uint8 =          lambda value: to_byte_type( '>B', value )
to_uint16_le =      lambda value: to_byte_type( '<H', value )
to_uint32_le =      lambda value: to_byte_type( '<I', value )
to_uint64_le =      lambda value: to_byte_type( '<Q', value )
to_int16_le =       lambda value: to_byte_type( '<h', value )
to_int32_le =       lambda value: to_byte_type( '<i', value )
to_int64_le =       lambda value: to_byte_type( '<q', value )
to_float_le =       lambda value: to_byte_type( '<f', value )
to_double_le =      lambda value: to_byte_type( '<d', value )
to_uint16_be =      lambda value: to_byte_type( '>H', value )
to_uint32_be =      lambda value: to_byte_type( '>I', value )
to_uint64_be =      lambda value: to_byte_type( '>Q', value )
to_int16_be =       lambda value: to_byte_type( '>h', value )
to_int32_be =       lambda value: to_byte_type( '>i', value )
to_int64_be =       lambda value: to_byte_type( '>q', value )
to_float_be =       lambda value: to_byte_type( '>f', value )
to_double_be =      lambda value: to_byte_type( '>d', value )



class BitReader( object ):
    def __init__( self, buffer, start_offset, bytes_reverse=False, bits_reverse=False ):
        assert type( buffer ) == bytes
        self.buffer = buffer
        self.bits_reverse = bits_reverse
        self.bytes_reverse = bytes_reverse
        self.set_offset( start_offset )


    def set_offset( self, offset ):
        assert offset in range( len( self.buffer ) )
        self.pos = offset
        self.bits_remaining = 8
        self.current_bits = self.buffer[self.pos]


    def get_bits( self, n ):
        result = 0
        for i in range( n ):
            if self.bits_remaining <= 0:
                new_pos = self.pos + (-1 if self.bytes_reverse else 1)
                if new_pos not in range( len( self.buffer ) ):
                    raise IndexError( 'Hit the end of the buffer, no more bytes' )

                self.pos = new_pos
                self.current_bits = self.buffer[self.pos]
                self.bits_remaining = 8
            if self.bits_reverse:
                bit = (1 if (self.current_bits & 0x80) else 0)
                self.current_bits <<= 1
                self.current_bits &= 0xff
            else:
                bit = (self.current_bits & 1)
                self.current_bits >>= 1
            
            self.bits_remaining -= 1

            result <<= 1
            result |= bit
        return result


class BitWriter( object ):
    def __init__( self, bytes_reverse=False, bits_reverse=False ):
        self.output = bytearray()
        self.bits_reverse = bits_reverse
        self.bytes_reverse = bytes_reverse
        self.bits_remaining = 8
        self.current_bits = 0


    def put_bits( self, value, n ):
        for i in range( n ):

            # bits are retrieved from the source LSB first
            bit = (value & 1)
            value >>= 1

            # however, bits are put into the result based on the rule
            if self.bits_reverse:
                self.current_bits |= (bit << (self.bits_remaining-1))
            else:
                self.current_bits |= (bit << (8-self.bits_remaining))        

            self.bits_remaining -= 1
            if self.bits_remaining <= 0:
                self.output.append( self.current_bits )

                self.current_bits = 0
                self.bits_remaining = 8


    def get_buffer( self ):
        if self.bytes_reverse:
            return bytes( reversed( self.output ) )
        else:
            return bytes( self.output )
