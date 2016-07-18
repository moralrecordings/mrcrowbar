import struct

def _from_byte_type( code, size ):
    return lambda buffer: struct.unpack( code, buffer[:size] )[0]

def _to_byte_type( code ):
    return lambda value: struct.pack( code, value )

BYTE_TYPES = {
    'int8':         ('<b', 1),
    'uint8':        ('>B', 1),
    'uint16_le':    ('<H', 2),
    'uint32_le':    ('<I', 4),
    'uint64_le':    ('<Q', 8),
    'int16_le':     ('<h', 2),
    'int32_le':     ('<i', 4),
    'int64_le':     ('<q', 8),
    'float_le':     ('<f', 4),
    'double_le':    ('<d', 8),
    'uint16_be':    ('>H', 2),
    'uint32_be':    ('>I', 4),
    'uint64_be':    ('>Q', 8),
    'int16_be':     ('>h', 2),
    'int32_be':     ('>i', 4),
    'int64_be':     ('>q', 8),
    'float_be':     ('>f', 4),
    'double_be':    ('>d', 8),
}

def _load_byte_types():
    for byte_type, (type_code, type_size) in BYTE_TYPES.items():
        globals()['from_{}'.format(byte_type)] = _from_byte_type( type_code, type_size )
        globals()['to_{}'.format(byte_type)] = _to_byte_type( type_code )

_load_byte_types()


def unpack_bits(byte):
    """Expand a bitfield into a 64-bit int (8 bool bytes)"""
    longbits = byte & (0x00000000000000ff)
    longbits = (longbits | (longbits<<28)) & (0x0000000f0000000f)
    longbits = (longbits | (longbits<<14)) & (0x0003000300030003)
    longbits = (longbits | (result<<7)) & (0x0101010101010101)
    return longbits


def pack_bits(longbits):
    """Crunch a 64-bit int (8 bool bytes) into a bitfield"""
    byte = longbits & (0x0101010101010101)
    byte = (byte | (byte>>7)) & (0x0003000300030003)
    byte = (byte | (byte>>14)) & (0x0000000f0000000f)
    byte = (byte | (byte>>28)) & (0x00000000000000ff)
    return byte


class BitReader( object ):
    def __init__( self, buffer, start_offset, bytes_reverse=False, bits_reverse=False ):
        assert isinstance( buffer, bytes )
        assert start_offset in range( len( buffer ) )
        self.buffer = buffer
        self.bits_reverse = bits_reverse
        self.bytes_reverse = bytes_reverse
        self.pos = start_offset
        self.bits_remaining = 8
        self.current_bits = self.buffer[self.pos]


    def set_offset( self, offset ):
        assert offset in range( len( self.buffer ) )
        self.pos = offset
        self.bits_remaining = 8
        self.current_bits = self.buffer[self.pos]


    def get_bits( self, count ):
        result = 0
        for _ in range( count ):
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
    def __init__( self, bytes_reverse=False, bits_reverse=False, insert_at_msb=False ):
        self.output = bytearray()
        self.bits_reverse = bits_reverse
        self.bytes_reverse = bytes_reverse
        self.insert_at_msb = insert_at_msb
        self.bits_remaining = 8
        self.current_bits = 0


    def put_bits( self, value, count ):
        for _ in range( count ):

            # bits are retrieved from the source LSB first
            bit = (value & 1)
            value >>= 1

            # however, bits are put into the result based on the rule
            if self.bits_reverse:
                if self.insert_at_msb:
                    self.current_bits |= (bit << (self.bits_remaining-1))
                else:
                    self.current_bits <<= 1
                    self.current_bits |= bit
            else:
                if self.insert_at_msb:
                    self.current_bits >>= 1
                    self.current_bits |= (bit << 7)
                else:
                    self.current_bits |= (bit << (8-self.bits_remaining))

            self.bits_remaining -= 1
            if self.bits_remaining <= 0:
                self.output.append( self.current_bits )

                self.current_bits = 0
                self.bits_remaining = 8


    def get_buffer( self ):
        last_byte = self.current_bits if (self.bits_remaining < 8) else None

        result = self.output
        if last_byte:
            result = bytearray( result )
            result.append( last_byte )

        if self.bytes_reverse:
            return bytes( reversed( result ) )
        else:
            return bytes( result )
