"""General utility functions useful for reverse engineering."""

import array
import math
import io
import struct
import mmap
import logging
logger = logging.getLogger( __name__ )


def enable_logging( level='WARNING' ):
    """Enable sending logs to stderr. Useful for shell sessions.

    level
        Logging threshold, as defined in the logging module of the Python
        standard library. Defaults to 'WARNING'.
    """
    log = logging.getLogger( 'mrcrowbar' )
    log.setLevel( level )
    out = logging.StreamHandler()
    out.setLevel( level )
    form = logging.Formatter( '[%(levelname)s] %(name)s - %(message)s' )
    out.setFormatter( form )
    log.addHandler( out )


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


BYTE_GLYPH_MAP = """ ☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ """

BYTE_COLOUR_MAP = (12,) + (14,)*32 + (11,)*94 + (14,)*128 + (12,)

HIGHLIGHT_COLOUR_MAP = (9, 10)

def _load_byte_types():
    for byte_type, (type_code, type_size) in BYTE_TYPES.items():
        globals()['from_{}'.format(byte_type)] = _from_byte_type( type_code, type_size )
        globals()['to_{}'.format(byte_type)] = _to_byte_type( type_code, type_size )

_load_byte_types()


def find_all_iter( source, substring, start=None, end=None, overlap=False ):
    """Iterate through every location a substring can be found in a source string.

    source
        The source string to search.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    overlap
        Whether to return overlapping matches (default: false)
    """
    data = source
    base = 0
    if end is not None:
        data = data[:end]
    if start is not None:
        data = data[start:]
        base = start
    pointer = 0
    increment = 1 if overlap else (len( substring ) or 1)
    while True:
        pointer = data.find( substring, pointer )
        if pointer == -1:
            return
        yield base+pointer
        pointer += increment


def find_all( source, substring, start=None, end=None, overlap=False ):
    """Return every location a substring can be found in a source string.

    source
        The source string to search.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    overlap
        Whether to return overlapping matches (default: false)
    """
    return [x for x in find_all_iter( source, substring, start, end, overlap )]


def basic_diff( source1, source2, start=None, end=None ):
    """Perform a basic diff between two equal-sized binary strings and
    return a list of (offset, size) tuples denoting the differences.

    source1
        The first byte string source.

    source2
        The second byte string source.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)
    """
    start = start if start is not None else 0
    end = end if end is not None else min( len( source1 ), len( source2 ) )
    end_point = min( end, len( source1 ), len( source2 ) )

    pointer = start
    diff_start = None
    results = []
    while pointer < end_point:
        if source1[pointer] != source2[pointer]:
            if diff_start is None:
                diff_start = pointer
        else:
            if diff_start is not None:
                results.append( (diff_start, pointer-diff_start) )
                diff_start = None
        pointer += 1
    if diff_start is not None:
        results.append( (diff_start, pointer-diff_start) )
        diff_start = None

    return results


def ansi_format_hexdump_line( source, offset, end=None, major_len=8, minor_len=4, colour=True, prefix='', highlight_addr=None, highlight_map=None ):
    def get_colour( index ):
        if highlight_map:
            if index in highlight_map:
                return highlight_map[index]
        return BYTE_COLOUR_MAP[source[index]]

    def colour_wrap( s, col ):
        if not col:
            return s
        return '{}{}{}'.format(
            ANSI_FORMAT_FOREGROUND_XTERM.format( col ),
            s, ANSI_FORMAT_RESET
        )

    def get_ascii():
        b = source[offset:min( offset+major_len*minor_len, end )]
        letters = []
        for i in range( offset, min( offset+major_len*minor_len, end ) ):
            letters.append( colour_wrap( BYTE_GLYPH_MAP[source[i]], get_colour( i ) ) )
        return ''.join( letters )

    line = [colour_wrap( '{}{:08x}'.format( prefix, offset ), highlight_addr ), ' │  ']
    for major in range( major_len ):
        for minor in range( minor_len ):
            suboffset = offset+major*minor_len+minor
            if suboffset >= end:
                line.append( '   ' )
                continue
            line.append( colour_wrap( '{:02x} '.format( source[suboffset] ), get_colour( suboffset ) ) )
        line.append( ' ' )
    line.append( '│ {}'.format( get_ascii() ) )
    return ''.join( line )


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
        lines.append( ansi_format_hexdump_line( source, offset, end, major_len, minor_len, colour ) )
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


def hexdump_diff_str( source1, source2, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, before=2, after=2 ):
    """Returns the differences between two byte strings in tabular hexadecimal/ASCII format.

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

    colour
        Add ANSI colour formatting to output (default: true)

    before
        Number of lines of context preceeding a match to show

    after
        Number of lines of context following a match to show

    Raises ValueError if both end and length are defined.
    """
    stride = minor_len*major_len
    start = start if start is not None else 0
    end = end if end is not None else max( len( source1 ), len( source2 ) )

    diff_lines = []
    for offset in range( start, end, stride ):
        if source1[offset:offset+stride] != source2[offset:offset+stride]:
            diff_lines.append( offset )
    show_all = before is None or after is None
    if show_all:
        show_lines = {x: (2 if x in diff_lines else 1) for x in range( start, end, stride )}
    else:
        show_lines = {x: (2 if x in diff_lines else 0) for x in range( start, end, stride )}
        for index in diff_lines:
            for b in [index-(x+1)*stride for x in range( before )]:
                if b in show_lines and show_lines[b] == 0:
                    show_lines[b] = 1
            for a in [index+(x+1)*stride for x in range( after )]:
                if a in show_lines and show_lines[a] == 0:
                    show_lines[a] = 1

    lines = []
    skip = False
    for offset in sorted( show_lines.keys() ):
        if skip == True and show_lines[offset] != 0:
            lines.append( '...' )
            skip = False
        if show_lines[offset] == 2:
            check = basic_diff( source1, source2, start=offset, end=offset+stride )
            highlights = {}
            for (o, l) in check:
                for i in range( o, o+l ):
                    highlights[i] = HIGHLIGHT_COLOUR_MAP[0]
            if offset < len( source1 ):
                lines.append( ansi_format_hexdump_line( source1, offset, min( end, len( source1 ) ), major_len, minor_len, colour, prefix='-', highlight_addr=HIGHLIGHT_COLOUR_MAP[0], highlight_map=highlights ) )
            highlights = {k: HIGHLIGHT_COLOUR_MAP[1] for k in highlights.keys()}
            if offset < len( source2 ):
                lines.append( ansi_format_hexdump_line( source2, offset, min( end, len( source2 ) ), major_len, minor_len, colour, prefix='+' , highlight_addr=HIGHLIGHT_COLOUR_MAP[1], highlight_map=highlights ) )
        elif show_lines[offset] == 1:
            lines.append( ansi_format_hexdump_line( source1, offset, end, major_len, minor_len, colour, prefix=' ' ) )
        elif show_lines[offset] == 0:
            skip = True

    if skip == True:
        lines.append( '...' )
        skip = False

    return '\n'.join( lines )


def hexdump_diff( source1, source2, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, before=2, after=2 ):
    """Returns the differences between two byte strings in tabular hexadecimal/ASCII format.

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

    colour
        Add ANSI colour formatting to output (default: true)

    before
        Number of lines of context preceeding a match to show

    after
        Number of lines of context following a match to show

    Raises ValueError if both end and length are defined.
    """
    print( hexdump_diff_str( source1, source2, start, end, length, major_len, minor_len, colour, before, after ) )


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
        self.samples = len( buffer )
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
        result.append( 'entropy: {}\n'.format( self.entropy ) )
        result.append( 'samples: {}'.format( self.samples ) )
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


def ansi_format_image( data_fetch, x_start=0, y_start=0, width=32, height=32, frame=0, columns=1, downsample=1 ):
    """Return the ANSI escape sequence to render a bitmap image.

    data_fetch
        Function that takes three arguments (x position, y position, and frame number) and returns
        a Colour corresponding to the pixel stored there, or Transparent if the requested pixel is 
        out of bounds.

    x_start
        Offset from the left of the image data to render from. Defaults to 0.

    y_start
        Offset from the top of the image data to render from. Defaults to 0.

    width
        Width of the image data to render. Defaults to 32.

    height
        Height of the image data to render. Defaults to 32.

    frame
        Single frame number, or a list of frame numbers to render in sequence. Defaults to frame 0.

    columns
        Number of frames to render per line (useful for printing tilemaps!). Defaults to 1.

    downsample
        Shrink larger images by printing every nth pixel only. Defaults to 1.
    """
    frames = []
    if isinstance( frame, int ):
        frames = [frame]
    else:
        frames = [f for f in frame]

    result = io.StringIO()

    palette_cache = {}
    def get_pixels( c1, c2 ):
        slug = (c1.repr, c2.repr)
        if slug not in palette_cache:
            palette_cache[slug] = ansi_format_pixels( c1, c2 )
        return palette_cache[slug]

    rows = math.ceil( len( frames )/columns )
    for r in range( rows ):
        for y in range( 0, height, 2*downsample ):
            for c in range( min( (len( frames )-r*columns), columns ) ):
                for x in range( 0, width, downsample ):
                    fr = frames[r*columns + c]
                    c1 = data_fetch( x_start+x, y_start+y, fr )
                    c2 = data_fetch( x_start+x, y_start+y+downsample, fr )
                    result.write( get_pixels( c1, c2 ) )
            result.write( '\n' )
    return result.getvalue()


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
