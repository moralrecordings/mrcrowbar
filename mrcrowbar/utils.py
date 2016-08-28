"""General utility functions useful for reverse engineering."""

import array
import math
import struct

def _from_byte_type( code, size ):
    result = lambda buffer: struct.unpack( code, buffer[:size] )[0]
    result.__doc__ = "Convert a {0} byte string to a Python {1}.".format( *_byte_type_to_text( code, size ) )
    return result

def _to_byte_type( code, size ):
    result = lambda value: struct.pack( code, value )
    result.__doc__ = "Convert a Python {1} to a {0} byte string.".format( *_byte_type_to_text( code, size ) )
    return result

def _byte_type_to_text( code, size ):
    raw_type = 'float' if code[1] in 'fd' else 'integer'
    is_signed = code[1].islower()
    endianness = 'big' if code[0] == '>' else 'little'
    return ('{}{}-bit {}{}'.format(
        ('signed ' if is_signed else 'unsigned ') if raw_type == 'integer' else '',
        size*8,
        raw_type,
        ' ({}-endian)'.format(endianness) if size>1 else ''
    ), raw_type)

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
        globals()['to_{}'.format(byte_type)] = _to_byte_type( type_code, type_size )

_load_byte_types()


class Stats( object ):
    """Helper class for performing some basic statistical analysis on binary data."""

    def __init__( self, buffer ):
        """Generate a Stats instance for a byte string and analyse the data."""
        assert isinstance( buffer, bytes )

        #: Byte histogram for the source data.
        self.histo = array.array( 'I', [0]*256 )
        # do histogram expensively for now, to avoid pulling in e.g numpy
        for byte in buffer:
            self.histo[byte] += 1

        #: Shanning entropy calculated for the source data.
        self.entropy = 0.0
        for count in self.histo:
            if count != 0:
                cover = count/len( buffer )
                self.entropy += -cover * math.log2( cover )

    def ansi_format( self, width=64, height=12 ):
        """Return a human readable ANSI-terminal printout of the stats.

        width
            Custom width for the graph (in characters)

        height
            Custom height for the graph (in characters)
        """
        FRACTION = u' ▁▂▃▄▅▆▇█'
        bucket = 256//width
        buckets = [sum( self.histo[i:i+bucket] ) for i in range( 0, 256, bucket )]
        scale = height*8.0/max( buckets )
        buckets_norm = [b*scale for b in buckets]
        result = []
        for y_pos in range( height, 0, -1 ):
            result.append( ' ' )
            for _, x_value in enumerate( buckets_norm ):
                if (x_value // 8) >= y_pos:
                    result.append( FRACTION[8] )
                elif (x_value // 8) == y_pos-1:
                    result.append( FRACTION[round( x_value % 8 )] )
                else:
                    result.append( FRACTION[0] )
            result.append( '\n' )

        result.append( '╘'+('═'*width)+'╛\n' )
        result.append( 'entropy: {}'.format( self.entropy ) )
        return ''.join(result)

    def print( self, *args, **kwargs ):
        """Print the graphical version of the results produced by ansi_format()."""
        print( self.ansi_format( *args, **kwargs ) )

    def __str__( self ):
        return self.ansi_format()


def unpack_bits( byte ):
    """Expand a bitfield into a 64-bit int (8 bool bytes)."""
    longbits = byte & (0x00000000000000ff)
    longbits = (longbits | (longbits<<28)) & (0x0000000f0000000f)
    longbits = (longbits | (longbits<<14)) & (0x0003000300030003)
    longbits = (longbits | (longbits<<7)) & (0x0101010101010101)
    return longbits


def pack_bits( longbits ):
    """Crunch a 64-bit int (8 bool bytes) into a bitfield."""
    byte = longbits & (0x0101010101010101)
    byte = (byte | (byte>>7)) & (0x0003000300030003)
    byte = (byte | (byte>>14)) & (0x0000000f0000000f)
    byte = (byte | (byte>>28)) & (0x00000000000000ff)
    return byte


class BitReader( object ):
    """Class for reading data as a stream of bits."""

    def __init__( self, buffer, start_offset, bytes_reverse=False, bits_reverse=False ):
        """Create a BitReader instance.

        buffer
            Source byte string to read from.

        start_offset
            Position in the block to start reading from.

        bytes_reverse
            If enabled, fetch successive bytes from the source in reverse order.

        bits_reverse
            If enabled, fetch bits starting from the most-significant bit (i.e. 0x80)
            through least-significant bit (0x01).
        """
        assert isinstance( buffer, bytes )
        assert start_offset in range( len( buffer ) )
        self.buffer = buffer
        self.bits_reverse = bits_reverse
        self.bytes_reverse = bytes_reverse
        self.pos = start_offset
        self.bits_remaining = 8
        self.current_bits = self.buffer[self.pos]


    def set_offset( self, offset ):
        """Set the current read offset (in bytes) for the instance."""
        assert offset in range( len( self.buffer ) )
        self.pos = offset
        self.bits_remaining = 8
        self.current_bits = self.buffer[self.pos]


    def get_bits( self, count ):
        """Get an integer containing the next [count] bits from the source.

        The result is always stored from least-significant bit to most-significant bit.
        """
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
    """Class for writing data as a stream of bits."""

    def __init__( self, bytes_reverse=False, bits_reverse=False, insert_at_msb=False ):
        """Create a BitWriter instance.

        bytes_reverse
            If enabled, write bytes to the target in reverse order.

        bits_reverse
            If enabled, make the insert order for bits from most-significant to
            least-significant.

        insert_at_msb
            If enabled, start filling each byte from the most-significant bit end (0x80).
        """
        self.output = bytearray()
        self.bits_reverse = bits_reverse
        self.bytes_reverse = bytes_reverse
        self.insert_at_msb = insert_at_msb
        self.bits_remaining = 8
        self.current_bits = 0

    def put_bits( self, value, count ):
        """Push bits into the target.

        value
            Integer containing bits to push, ordered from least-significant bit to
            most-significant bit.

        count
            Number of bits to push to the target.
        """
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
        """Return a byte string containing the target as currently written."""
        last_byte = self.current_bits if (self.bits_remaining < 8) else None

        result = self.output
        if last_byte:
            result = bytearray( result )
            result.append( last_byte )

        if self.bytes_reverse:
            return bytes( reversed( result ) )
        else:
            return bytes( result )
