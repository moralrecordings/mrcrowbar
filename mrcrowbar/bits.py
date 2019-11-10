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

def reverse_bits( byte ):
    return BYTE_REVERSE[byte]


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

    def __init__( self, buffer, start_offset, bytes_reverse=False, bits_reverse=False, output_reverse=False, bytes_to_cache=1 ):
        """Create a BitReader instance.

        buffer
            Source byte string to read from.

        start_offset
            Position in the block to start reading from.

        bytes_reverse
            If enabled, fetch successive bytes from the source in reverse order.

        bits_reverse
            If enabled, fetch bits starting from the most-significant bit (0x80)
            through least-significant bit (0x01).

        output_reverse
            If enabled, return fetched bits starting from the most-significant bit
            (0x80) through least-significant bit (0x01).

        bytes_to_cache
            Number of bytes to cache. Defaults to 1. Only useful for algorithms which
            change the position pointer mid-read.
        """
        assert is_bytes( buffer )
        assert start_offset in range( len( buffer ) )
        self.buffer = buffer
        self.bits_reverse = bits_reverse
        self.bytes_reverse = bytes_reverse
        self.output_reverse = output_reverse
        self.pos = start_offset
        self.bytes_to_cache = bytes_to_cache
        self._fill_buffer()


    def _fill_buffer( self ):
        self.bits_remaining = 8*self.bytes_to_cache
        self.current_bits = 0
        for i in range( self.bytes_to_cache ):
            if self.pos not in range( len( self.buffer ) ):
                raise IndexError( 'Hit the end of the buffer, no more bytes' )
            self.current_bits |= self.buffer[self.pos] << (8*i)
            new_pos = self.pos + (-1 if self.bytes_reverse else 1)
            self.pos = new_pos


    def set_offset( self, offset ):
        """Set the current read offset (in bytes) for the instance."""
        assert offset in range( len( self.buffer ) )
        self.pos = offset
        self._fill_buffer()


    def get_bits( self, count ):
        """Get an integer containing the next [count] bits from the source."""
        result = 0
        for i in range( count ):
            if self.bits_remaining <= 0:
                self._fill_buffer()
            if self.bits_reverse:
                bit = (1 if (self.current_bits & (0x80 << 8*(self.bytes_to_cache-1))) else 0)
                self.current_bits <<= 1
                self.current_bits &= 0xff
            else:
                bit = (self.current_bits & 1)
                self.current_bits >>= 1

            self.bits_remaining -= 1

            if self.output_reverse:
                result <<= 1
                result |= bit
            else:
                result |= bit << i
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
        if last_byte is not None:
            result = bytearray( result )
            result.append( last_byte )

        if self.bytes_reverse:
            return bytes( reversed( result ) )
        else:
            return bytes( result )
