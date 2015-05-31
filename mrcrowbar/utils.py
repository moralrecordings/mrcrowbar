

class BitStream( object ):
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

