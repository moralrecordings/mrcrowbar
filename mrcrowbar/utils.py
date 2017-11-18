"""General utility functions useful for reverse engineering."""

import array
import math
import struct
import difflib
import mmap

def is_bytes( obj ):
    """Returns whether obj is an acceptable Python byte string."""
    return isinstance( obj, (bytes, bytearray, mmap.mmap) )


def _from_byte_type( code, size ):
    result = lambda buffer: struct.unpack( code, buffer[:size] )[0]
    result.__doc__ = "Convert a {0} byte string to a Python {1}.".format(
        *_byte_type_to_text( code, size )
    )
    return result

def _to_byte_type( code, size ):
    result = lambda value: struct.pack( code, value )
    result.__doc__ = "Convert a Python {1} to a {0} byte string.".format(
        *_byte_type_to_text( code, size )
    )
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

BYTE_REVERSE =  b'\x00\x80@\xc0 \xa0`\xe0\x10\x90P\xd00\xb0p\xf0' \
                b'\x08\x88H\xc8(\xa8h\xe8\x18\x98X\xd88\xb8x\xf8' \
                b'\x04\x84D\xc4$\xa4d\xe4\x14\x94T\xd44\xb4t\xf4' \
                b'\x0c\x8cL\xcc,\xacl\xec\x1c\x9c\\\xdc<\xbc|\xfc' \
                b'\x02\x82B\xc2"\xa2b\xe2\x12\x92R\xd22\xb2r\xf2' \
                b'\n\x8aJ\xca*\xaaj\xea\x1a\x9aZ\xda:\xbaz\xfa' \
                b'\x06\x86F\xc6&\xa6f\xe6\x16\x96V\xd66\xb6v\xf6' \
                b'\x0e\x8eN\xce.\xaen\xee\x1e\x9e^\xde>\xbe~\xfe' \
                b'\x01\x81A\xc1!\xa1a\xe1\x11\x91Q\xd11\xb1q\xf1' \
                b'\t\x89I\xc9)\xa9i\xe9\x19\x99Y\xd99\xb9y\xf9' \
                b'\x05\x85E\xc5%\xa5e\xe5\x15\x95U\xd55\xb5u\xf5' \
                b'\r\x8dM\xcd-\xadm\xed\x1d\x9d]\xdd=\xbd}\xfd' \
                b'\x03\x83C\xc3#\xa3c\xe3\x13\x93S\xd33\xb3s\xf3' \
                b'\x0b\x8bK\xcb+\xabk\xeb\x1b\x9b[\xdb;\xbb{\xfb' \
                b"\x07\x87G\xc7'\xa7g\xe7\x17\x97W\xd77\xb7w\xf7" \
                b'\x0f\x8fO\xcf/\xafo\xef\x1f\x9f_\xdf?\xbf\x7f\xff'

BYTE_GLYPH_MAP = """ ☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ """

BYTE_COLOUR_MAP = (12,) + (14,)*32 + (11,)*94 + (14,)*128 + (12,)


def _load_byte_types():
    for byte_type, (type_code, type_size) in BYTE_TYPES.items():
        globals()['from_{}'.format(byte_type)] = _from_byte_type( type_code, type_size )
        globals()['to_{}'.format(byte_type)] = _to_byte_type( type_code, type_size )

_load_byte_types()


def hexdump_str( source, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True ):
    """Return the contents of a byte string in tabular hexadecimal/ASCII format.
    
    source
        The byte string to print.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    major_len
        Number of hexadecimal groups per line

    minor_len
        Number of bytes per hexadecimal group

    colour
        Add ANSI colour formatting to output (default: true)

    Raises ValueError if both end and length are defined.
    """
    assert is_bytes( source )
    colour_wrap = lambda s, index: s if not colour else '{}{}{}'.format(
        ANSI_FORMAT_FOREGROUND_XTERM.format( BYTE_COLOUR_MAP[index] ),
        s, ANSI_FORMAT_RESET
    )
    to_string = lambda b: ''.join( map( lambda x: colour_wrap( BYTE_GLYPH_MAP[x], x ), b ) )

    start = 0 if (start is None) else start
    if (end is not None) and (length is not None):
        raise ValueError( 'Can\'t define both an end and a length!' )
    elif (length is not None):
        end = start+length
    elif (end is not None):
        pass
    else:
        end = len( source ) 

    if len( source ) == 0 or (start == end == 0):
        return

    lines = []
    for offset in range( start, end, minor_len*major_len ):
        line = ['{:08x} │  '.format( offset )]
        for major in range( major_len ):
            for minor in range( minor_len ):
                suboffset = offset+major*minor_len+minor
                if suboffset >= end:
                    line.append( '   ' )
                    continue
                line.append( colour_wrap( '{:02x} '.format( source[suboffset] ), source[suboffset] ) )
            line.append( ' ' )
        line.append( '│ {}'.format( to_string( source[offset:offset+major_len*minor_len] ) ) )
        lines.append( ''.join( line ) )
    lines.append( '' )
    return '\n'.join(lines)


def hexdump( source, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True ):
    """Print the contents of a byte string in tabular hexadecimal/ASCII format.
    
    source
        The byte string to print.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    major_len
        Number of hexadecimal groups per line

    minor_len
        Number of bytes per hexadecimal group

    colour
        Add ANSI colour formatting to output (default: true)

    Raises ValueError if both end and length are defined.
    """
    print( hexdump_str( source, start, end, length, major_len, minor_len ) )


def hexdump_diff( source1, source2, start=None, end=None, length=None, major_len=8, minor_len=4 ):
    """Print the differences between two byte strings in tabular hexadecimal/ASCII format.
    
    source1
        The first byte string source.
        
    source2
        The second byte string source.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    major_len
        Number of hexadecimal groups per line

    minor_len
        Number of bytes per hexadecimal group

    Raises ValueError if both end and length are defined.
    """
    hex1 = hexdump_str( source1, start, end, length, major_len, minor_len, colour=False ).splitlines( 1 )
    hex2 = hexdump_str( source2, start, end, length, major_len, minor_len, colour=False ).splitlines( 1 )
    diff = difflib.Differ()
    print( ''.join( diff.compare( hex1, hex2 ) ) )



#: Unicode representation of a vertical bar graph.
BAR_VERT   = u' ▁▂▃▄▅▆▇█'
#: Unicode representation of a horizontal bar graph.
BAR_HORIZ  = u' ▏▎▍▌▋▊▉█'

class Stats( object ):
    """Helper class for performing some basic statistical analysis on binary data."""

    def __init__( self, buffer ):
        """Generate a Stats instance for a byte string and analyse the data."""
        assert is_bytes( buffer )

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
            Custom width for the graph (in characters).

        height
            Custom height for the graph (in characters).
        """
        bucket = 256//width
        buckets = [sum( self.histo[i:i+bucket] ) for i in range( 0, 256, bucket )]
        scale = height*8.0/max( buckets ) if max( buckets ) else height*8.0
        buckets_norm = [b*scale for b in buckets]
        result = []
        for y_pos in range( height, 0, -1 ):
            result.append( ' ' )
            for _, x_value in enumerate( buckets_norm ):
                if (x_value // 8) >= y_pos:
                    result.append( BAR_VERT[8] )
                elif (x_value // 8) == y_pos-1:
                    result.append( BAR_VERT[round( x_value % 8 )] )
                else:
                    result.append( BAR_VERT[0] )
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


#: ANSI escape sequence for resetting the colour settings to the default.
ANSI_FORMAT_RESET = '\x1b[0m'
#: ANSI escape sequence for setting the foreground colour (24-bit).
ANSI_FORMAT_FOREGROUND = '\x1b[38;2;{};{};{}m'
#: ANSI escape sequence for setting the background colour (24-bit).
ANSI_FORMAT_BACKGROUND = '\x1b[48;2;{};{};{}m'
#: ANSI escape sequence for setting the foreground colour (xterm).
ANSI_FORMAT_FOREGROUND_XTERM = '\x1b[38;5;{}m'
#: ANSI escape sequence for setting the background colour (xterm).
ANSI_FORMAT_BACKGROUND_XTERM = '\x1b[48;5;{}m'
#: ANSI escape sequence for setting the foreground and background colours (24-bit).
ANSI_FORMAT_COLOURS = '\x1b[38;2;{};{};{};48;2;{};{};{}m'

def ansi_format_pixels( top, bottom ):
    """Return the ANSI escape sequence to render two vertically-stacked Colours as a
    single monospace character."""
    if top.a_8 == 0 and bottom.a_8 == 0:
        return ' '
    elif top == bottom:
        return '{}█{}'.format(
            ANSI_FORMAT_FOREGROUND.format(
                top.r_8, top.g_8, top.b_8
            ), ANSI_FORMAT_RESET
        )
    elif top.a_8 == 0 and bottom.a_8 != 0:
        return '{}▄{}'.format(
            ANSI_FORMAT_FOREGROUND.format(
                bottom.r_8, bottom.g_8, bottom.b_8
            ), ANSI_FORMAT_RESET
        )
    elif top.a_8 != 0 and bottom.a_8 == 0:
        return '{}▀{}'.format(
            ANSI_FORMAT_FOREGROUND.format(
                top.r_8, top.g_8, top.b_8
            ), ANSI_FORMAT_RESET
        )
    return '{}▀{}'.format(
        ANSI_FORMAT_COLOURS.format(
            top.r_8, top.g_8, top.b_8,
            bottom.r_8, bottom.g_8, bottom.b_8,
        ), ANSI_FORMAT_RESET
    )


def ansi_format_string( string, foreground, background ):
    """Return the ANSI escape sequence to render a Unicode string with a
    foreground and a background Colour."""
    # FIXME: add better support for transparency
    fmt = ANSI_FORMAT_COLOURS.format(
        foreground.r_8, foreground.g_8, foreground.b_8,
        background.r_8, background.g_8, background.b_8
    )
    return '{}{}{}'.format( fmt, string, ANSI_FORMAT_RESET )


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
            If enabled, fetch bits starting from the most-significant bit (i.e. 0x80)
            through least-significant bit (0x01).

        output_reverse
            If enabled, return fetched bits starting from the most-significant bit (e.g. 
            0x80) through least-significant bit (0x01).

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
