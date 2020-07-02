from mrcrowbar.common import is_bytes


BYTE_REVERSE = bytes.fromhex( '008040c020a060e0109050d030b070f0'\
                              '088848c828a868e8189858d838b878f8'\
                              '048444c424a464e4149454d434b474f4'\
                              '0c8c4ccc2cac6cec1c9c5cdc3cbc7cfc'\
                              '028242c222a262e2129252d232b272f2'\
                              '0a8a4aca2aaa6aea1a9a5ada3aba7afa'\
                              '068646c626a666e6169656d636b676f6'\
                              '0e8e4ece2eae6eee1e9e5ede3ebe7efe'\
                              '018141c121a161e1119151d131b171f1'\
                              '098949c929a969e9199959d939b979f9'\
                              '058545c525a565e5159555d535b575f5'\
                              '0d8d4dcd2dad6ded1d9d5ddd3dbd7dfd'\
                              '038343c323a363e3139353d333b373f3'\
                              '0b8b4bcb2bab6beb1b9b5bdb3bbb7bfb'\
                              '078747c727a767e7179757d737b777f7'\
                              '0f8f4fcf2faf6fef1f9f5fdf3fbf7fff' )

BIT_MASK = [(1 << size) - 1 for size in range( 0, 65 )]

mask = lambda size: BIT_MASK[size] if size in range( 0, 65 ) else (1 << size) - 1

def reverse_bits( number, size=8 ):
    number &= mask( size )
    if size == 8:
        return BYTE_REVERSE[number]
    result = 0
    width = (size + 7) // 8
    shift = (8 - size)  % 8
    for i in range( 0, width ):
        fragment = (number >> (i * 8)) & 0xff
        result |= BYTE_REVERSE[fragment] << ((width - i - 1) * 8)
    result >>= shift
    return result


def read_bits( buffer, byte_offset, bit_offset, size, bytes_reverse=False, bit_endian='big', io_endian='big' ):
    byte_start = byte_offset
    bit_start = bit_offset

    bit_diff = (bit_offset + size) if bit_endian == 'big' else (7 - bit_offset + size)

    if bytes_reverse:
        byte_end = byte_offset - bit_diff // 8
    else:
        byte_end = byte_offset + bit_diff // 8
    bit_end = bit_diff % 8 if bit_endian == 'big' else 7 - (bit_diff % 8)
    result = 0

    first_byte = buffer[byte_start]
    middle_bytes = range( byte_start + 1, byte_end ) if not bytes_reverse else range( byte_start - 1, byte_end, -1 )
    end_byte = buffer[byte_end] if byte_end in range( len( buffer ) ) else 0

    if bit_endian == 'big':
        # start
        span_mask = mask( 8 - bit_start )
        if byte_start == byte_end:
            span_mask ^= mask( 8 - bit_end )
        result |= first_byte & span_mask
        if byte_start != byte_end:

            # middle
            for i in middle_bytes:
                result <<= 8
                result |= buffer[i]

            # end
            span_mask = 0xff ^ mask( 8 - bit_end )
            result <<= 8
            result |= end_byte & span_mask
        result >>= 8 - bit_end
    else:
        # start
        span_mask = 0xff ^ mask( 7 - bit_start )
        if byte_start == byte_end:
            span_mask ^= 0xff ^ mask( 7 - bit_end )
        result |= first_byte & span_mask
        result >>= 7 - bit_start
        if byte_start != byte_end:
            bit_offset = bit_start + 1

            # middle
            for i in middle_bytes:
                result |= buffer[i] << bit_offset
                bit_offset += 8

            # end
            span_mask = mask( 7 - bit_end )
            result |= (end_byte & span_mask) << bit_offset

    if io_endian != bit_endian:
        result = reverse_bits( result, size )
    return result


def write_bits( value, buffer, byte_offset, bit_offset, size, bytes_reverse=False, bit_endian='big', io_endian='big' ):
    if value not in range( 1 << size ):
        raise ValueError( 'Value {} does not fit into {} bits'.format( value, size ) )

    byte_start = byte_offset
    bit_start = bit_offset

    if io_endian != bit_endian:
        value = reverse_bits( value, size )

    bit_diff = (bit_offset + size) if bit_endian == 'big' else (7 - bit_offset + size)

    if bytes_reverse:
        byte_end = byte_offset - bit_diff // 8
    else:
        byte_end = byte_offset + bit_diff // 8
    bit_end = bit_diff % 8 if bit_endian == 'big' else 7 - (bit_diff % 8)

    middle_bytes = range( byte_start + 1, byte_end ) if not bytes_reverse else range( byte_start - 1, byte_end, -1 )

    if bit_endian == 'big':
        # start
        span_mask = mask( 8 - bit_start )
        if byte_start == byte_end:
            span_mask ^= mask( 8 - bit_end )
            start_value = value << 8 - bit_end
        else:
            start_value = value >> size - (8 - bit_start)
        buffer[byte_start] = (0xff ^ span_mask) & buffer[byte_start] | (start_value & span_mask)
        if byte_start != byte_end:

            # middle
            for i, x in enumerate( middle_bytes ):
                buffer[x] = (value >> ((len( middle_bytes ) - i - 1) * 8 + bit_end)) & 0xff

            # end
            end_value = value << (8 - bit_end)
            span_mask = 0xff ^ mask( 8 - bit_end )
            if span_mask:
                buffer[byte_end] = (0xff ^ span_mask) & buffer[byte_end] | (end_value & span_mask)
    else:
        # start
        span_mask = 0xff ^ mask( 7 - bit_start )
        if byte_start == byte_end:
            span_mask ^= 0xff ^ mask( 7 - bit_end )
        start_value = value << 7 - bit_start
        buffer[byte_start] = (0xff ^ span_mask) & buffer[byte_start] | (start_value & span_mask)
        if byte_start != byte_end:
            bit_offset = bit_start + 1

            # middle
            for i, x in enumerate( middle_bytes ):
                buffer[x] = (value >> bit_offset) & 0xff
                bit_offset += 8

            # end
            span_mask = mask( 7 - bit_end )
            end_value = value >> bit_offset
            if span_mask:
                buffer[byte_end] = (0xff ^ span_mask) & buffer[byte_end] | (end_value & span_mask)

    return


def reverse_bytes( buffer ):
    return bytes( reversed( map( buffer, reverse_bits ) ) )


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


class BitStream( object ):
    def __init__( self, buffer=None, start_offset=None, bytes_reverse=False, bit_endian='big', io_endian='big' ):
        """Create a BitStream instance.

        buffer
            Target byte array to read/write from. Defaults to an empty array.

        start_offset
            Position in the target to start reading from. Can be an integer byte offset,
            or a tuple containing the byte and bit offsets. Defaults to the start of the
            stream, depending on the endianness and ordering options.

        bytes_reverse
            If enabled, fetch successive bytes from the source in reverse order.

        bit_endian
            Endianness of the backing storage; either 'big' or 'little'. Defaults to big
            (i.e. starting from the most-significant bit (0x80) through least-significant
            bit (0x10)).

        io_endian
            Endianness of data returned from read/write; either 'big' or 'little'. Defaults
            to big (i.e. starting from the most-significant bit (0x80) through
            least-significant bit (0x10)).

        """
        if buffer is None:
            self.buffer = bytearray()
        else:
            assert is_bytes( buffer )
            self.buffer = buffer
        self.bytes_reverse = bytes_reverse
        if bit_endian not in ('big', 'little'):
            raise TypeError( 'bit_endian should be either \'big\' or \'little\'' )
        self.bit_endian = bit_endian
        if io_endian not in ('big', 'little'):
            raise TypeError( 'io_endian should be either \'big\' or \'little\'' )
        self.io_endian = io_endian
        if start_offset is None:
            self.byte_pos = len( buffer ) - 1 if bytes_reverse else 0
            self.bit_pos = 0 if bit_endian == 'big' else 7
        elif isinstance( start_offset, int ):
            self.byte_pos = start_offset
            self.bit_pos = 0 if bit_endian == 'big' else 7
        elif isinstance( start_offset, tuple ):
            self.byte_pos, self.bit_pos = start_offset
        else:
            raise TypeError('start_offset should be of type int or tuple')

    def tell( self ):
        """Get the current byte and bit position."""
        return self.byte_pos, self.bit_pos

    def read( self, count ):
        """Get an integer containing the next [count] bits from the source."""
        """
        x.read( 3 ) # 0bABC
        x.read( 3 ) # 0bDEF
        x.read( 3 ) # 0bGHI
        x.read( 3 ) # 0bJKL

        # default:
        # ABCDEFGH IJKLxxxx
        # bit_endian == 'little'
        # HGFEDCBA xxxxLKJI
        # bytes_reverse == True:
        # IJKLxxxx ABCDEFGH
        # io_endian == 'little':
        # CBAFEDIH GLKJxxxx
        """
        result = read_bits(
            buffer=self.buffer,
            byte_offset=self.byte_pos,
            bit_offset=self.bit_pos,
            size=count,
            bytes_reverse=self.bytes_reverse,
            bit_endian=self.bit_endian,
            io_endian=self.io_endian
        )

        self.seek( (count // 8, count % 8), origin="current" )

        return result

    def write( self, value, count ):
        """Write an unsigned integer containing [count] bits to the source."""
        """
        x.write( 0bABC, 3 )
        x.write( 0bDEF, 3 )
        x.write( 0bGHI, 3 )
        x.write( 0bJKL, 3 )

        # default:
        # ABCDEFGH IJKLxxxx
        # bit_endian == 'little'
        # HGFEDCBA xxxxLKJI
        # bytes_reverse == True:
        # IJKLxxxx ABCDEFGH
        # io_endian == 'little':
        # CBAFEDIH GLKJxxxx
        """
        bit_diff = (self.bit_pos + count - 1) if self.bit_endian == 'big' else (7 - self.bit_pos + count - 1)
        new_byte_pos = self.byte_pos
        if self.bytes_reverse:
            new_byte_pos -= bit_diff // 8
        else:
            new_byte_pos += bit_diff // 8
        if new_byte_pos < 0:
            byte_count = -new_byte_pos
            self.buffer = bytearray( b'\x00'*byte_count ) + self.buffer
            self.byte_pos += byte_count
        elif new_byte_pos >= len( self.buffer ):
            byte_count = new_byte_pos - len( self.buffer ) + 1
            self.buffer = self.buffer + bytearray( b'\x00'*byte_count )

        write_bits(
            value=value,
            buffer=self.buffer,
            byte_offset=self.byte_pos,
            bit_offset=self.bit_pos,
            size=count,
            bytes_reverse=self.bytes_reverse,
            bit_endian=self.bit_endian,
            io_endian=self.io_endian
        )

        self.seek( (count // 8, count % 8), origin="current" )

    def seek( self, offset, origin="start" ):
        """Seek to a location in the target.

        offset
            Relative offset in the target to move to. Can be an integer byte offset,
            or a tuple containing the byte and bit offsets.

        origin
            Position to measure the offset from. Can be either "start", "current" or "end".
            Defaults to "start".
        """
        if isinstance( offset, int ):
            count = offset * 8
        elif isinstance( offset, tuple ):
            count = offset[0] * 8 + offset[1]
        else:
            raise TypeError("offset should be of type int or tuple")

        if origin not in ("start", "current", "end"):
            raise TypeError('origin should be one of "start", "current" or "end"')

        if origin in ("start", "end"):
            if (origin == "start") ^ (self.bytes_reverse == False):
                self.byte_pos = len( self.buffer )
                self.bit_pos = 0
            else:
                self.byte_pos = 0
                self.bit_pos = 0

        bit_diff = (self.bit_pos + count) if self.bit_endian == 'big' else (7 - self.bit_pos + count)

        if self.bytes_reverse:
            self.byte_pos -= bit_diff // 8
        else:
            self.byte_pos += bit_diff // 8

        self.bit_pos = bit_diff % 8 if self.bit_endian == 'big' else 7 - (bit_diff % 8)

    def in_bounds( self ):
        """Returns True if the current position is within the bounds of the target."""
        return self.byte_pos in range( len( self.buffer ) )

    def get_buffer( self ):
        """Return a byte string containing the target."""
        return bytes( self.buffer )

