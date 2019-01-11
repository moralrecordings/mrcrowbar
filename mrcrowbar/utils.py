"""General utility functions useful for reverse engineering."""

import array
import math
import io
import mmap
import logging
from collections import Counter
logger = logging.getLogger( __name__ )

from mrcrowbar import encoding
globals().update( encoding._load_raw_types() )

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
    return isinstance( obj, (bytes, bytearray, mmap.mmap, memoryview) )



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


def ansi_format_histdump_line( source, offset, length=None, end=None, width=64, address_base_offset=0 ):
    if length is not None:
        data = source[offset:offset+length]
    else:
        data = source[offset:]
    end = end if end else len( source )
    digits = ('{:0'+str( max( 8, math.floor( math.log( end+address_base_offset )/math.log( 16 ) ) ) )+'x}').format( offset+address_base_offset )
    stat = Stats(data)
    return ('{} │ {} │ {:.10f}').format( digits, stat.ansi_format_histogram_line( width ), stat.entropy )


def histdump_iter( source, start=None, end=None, length=None, samples=0x10000, width=64, address_base=None ):
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

    start = max( start, 0 )
    end = min( end, len( source ) )
    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base-start if address_base is not None else 0

    for offset in range( start, end, samples ):
        yield ansi_format_histdump_line( source, offset, length=samples, end=end, width=width, address_base_offset=address_base_offset )
    return


def histdump( source, start=None, end=None, length=None, samples=0x10000, width=64, address_base=None ):
    for line in histdump_iter( source, start, end, length, samples, width, address_base ):
        print( line )


def ansi_format_hexdump_line( source, offset, end=None, major_len=8, minor_len=4, colour=True,
        prefix='', highlight_addr=None, highlight_map=None, address_base_offset=0 ):
    def get_colour( index ):
        if colour:
            if highlight_map:
                if index in highlight_map:
                    return ansi_format_escape( highlight_map[index] )
            return ansi_format_escape( BYTE_COLOUR_MAP[source[index]] )
        return ''

    def get_glyph():
        b = source[offset:min( offset+major_len*minor_len, end )]
        letters = []
        prev_colour = None
        for i in range( offset, min( offset+major_len*minor_len, end ) ):
            new_colour = get_colour( i )
            if prev_colour != new_colour:
                letters.append( new_colour )
                prev_colour = new_colour
            letters.append( BYTE_GLYPH_MAP[source[i]] )
        if colour:
            letters.append( ANSI_FORMAT_RESET )
        return ''.join( letters )

    if end is None:
        end = len( source )

    digits = ('{}{:0'+str( max( 8, math.floor( math.log( end+address_base_offset )/math.log( 16 ) ) ) )+'x}').format( prefix, offset+address_base_offset )

    line = [ansi_format_string( digits, highlight_addr ), ' │  ']
    prev_colour = None
    for major in range( major_len ):
        for minor in range( minor_len ):
            suboffset = offset+major*minor_len+minor
            if suboffset >= end:
                line.append( '   ' )
                continue
            new_colour = get_colour( suboffset )
            if prev_colour != new_colour:
                line.append( new_colour )
                prev_colour = new_colour
            line.append( '{:02x} '.format( source[suboffset] ) )

        line.append( ' ' )

    if colour:
        line.append( ANSI_FORMAT_RESET )

    line.append( '│ {}'.format( get_glyph() ) )
    return ''.join( line )


def hexdump_iter( source, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, address_base=None ):
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

    address_base
        Base address to use for labels (default: start)

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

    start = max( start, 0 )
    end = min( end, len( source ) )
    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base-start if address_base is not None else 0

    for offset in range( start, end, minor_len*major_len ):
        yield ansi_format_hexdump_line( source, offset, end, major_len, minor_len, colour, address_base_offset=address_base_offset )
    return


def hexdump( source, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, address_base=None ):
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

    address_base
        Base address to use for labels (default: start)

    Raises ValueError if both end and length are defined.
    """
    for line in hexdump_iter( source, start, end, length, major_len, minor_len, colour, address_base ):
        print( line )


def hexdump_diff_iter( source1, source2, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, before=2, after=2, address_base=None ):
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

    address_base
        Base address to use for labels (default: start)

    Raises ValueError if both end and length are defined.
    """
    stride = minor_len*major_len
    start = start if start is not None else 0
    end = end if end is not None else max( len( source1 ), len( source2 ) )

    start = max( start, 0 )
    end = min( end, max( len( source1 ), len( source2 ) ) )
    address_base_offset = address_base-start if address_base is not None else 0

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

    skip = False
    for offset in sorted( show_lines.keys() ):
        if skip == True and show_lines[offset] != 0:
            yield '...'
            skip = False
        if show_lines[offset] == 2:
            check = basic_diff( source1, source2, start=offset, end=offset+stride )
            highlights = {}
            for (o, l) in check:
                for i in range( o, o+l ):
                    highlights[i] = HIGHLIGHT_COLOUR_MAP[0]
            if offset < len( source1 ):
                yield ansi_format_hexdump_line( source1, offset, min( end, len( source1 ) ), major_len, minor_len, colour, prefix='-', highlight_addr=HIGHLIGHT_COLOUR_MAP[0], highlight_map=highlights, address_base_offset=address_base_offset )
            highlights = {k: HIGHLIGHT_COLOUR_MAP[1] for k in highlights.keys()}
            if offset < len( source2 ):
                yield ansi_format_hexdump_line( source2, offset, min( end, len( source2 ) ), major_len, minor_len, colour, prefix='+' , highlight_addr=HIGHLIGHT_COLOUR_MAP[1], highlight_map=highlights, address_base_offset=address_base_offset )
        elif show_lines[offset] == 1:
            yield ansi_format_hexdump_line( source1, offset, end, major_len, minor_len, colour, prefix=' ', address_base_offset=address_base_offset )
        elif show_lines[offset] == 0:
            skip = True

    if skip == True:
        yield '...'
        skip = False

    return


def hexdump_diff( source1, source2, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, before=2, after=2, address_base=None ):
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

    address_base
        Base address to use for labels (default: start)

    Raises ValueError if both end and length are defined.
    """
    for line in hexdump_diff_iter( source1, source2, start, end, length, major_len, minor_len, colour, before, after, address_base ):
        print( line )


#: Unicode representation of a vertical bar graph.
BAR_VERT   = u' ▁▂▃▄▅▆▇█'
#: Unicode representation of a horizontal bar graph.
BAR_HORIZ  = u' ▏▎▍▌▋▊▉█'

class Stats( object ):
    """Helper class for performing some basic statistical analysis on binary data."""

    def __init__( self, buffer ):
        """Generate a Stats instance for a byte string and analyse the data."""
        assert is_bytes( buffer )

        self.samples = len( buffer )
        # Python's Counter object uses a fast path
        cc = Counter( buffer )

        #: Byte histogram for the source data.
        self.histo = array.array( 'L', (cc.get( i, 0 ) for i in range( 256 )) )

        #: Shanning entropy calculated for the source data.
        self.entropy = 0.0
        for count in self.histo:
            if count != 0:
                cover = count/self.samples
                self.entropy += -cover * math.log2( cover )

    def histogram( self, width ):
        if (256 % width) != 0:
            raise ValueError( 'Width of the histogram must be a divisor of 256' )
        elif (width <= 0):
            raise ValueError( 'Width of the histogram must be greater than zero' )
        elif (width > 256):
            raise ValueError( 'Width of the histogram must be less than or equal to 256' )
        bucket = 256//width
        return [sum( self.histo[i:i+bucket] ) for i in range( 0, 256, bucket )]

    def ansi_format_histogram_line( self, width=64 ):
        buckets = self.histogram( width )
        total = sum( buckets )
        floor = math.log( 1/(8*len( buckets )) )

        buckets_log = [-floor + max( floor, math.log( b/total ) ) if b else None for b in buckets]
        limit = max( [b for b in buckets_log if b is not None] )
        buckets_norm = [round( 255*(b/limit) ) if b is not None else None for b in buckets_log]
        result = []
        for b in buckets_norm:
            if b is not None:
                result.append( ansi_format_string( '█', HEATMAP_COLOURS[b] ) )
            else:
                result.append( ' ' )
        return ''.join( result )

    def ansi_format( self, width=64, height=12 ):
        """Return a human readable ANSI-terminal printout of the stats.

        width
            Custom width for the graph (in characters).

        height
            Custom height for the graph (in characters).
        """
        if (256 % width) != 0:
            raise ValueError( 'Width of the histogram must be a divisor of 256' )
        elif (width <= 0):
            raise ValueError( 'Width of the histogram must be greater than zero' )
        elif (width > 256):
            raise ValueError( 'Width of the histogram must be less than or equal to 256' )

        buckets = self.histogram( width )
        result = []
        for line in ansi_format_bar_graph_iter( buckets, width=width, height=height ):
            result.append( ' {}\n'.format( line ) )

        result.append( '╘'+('═'*width)+'╛\n' )
        result.append( 'entropy: {:.10f}\n'.format( self.entropy ) )
        result.append( 'samples: {}'.format( self.samples ) )
        return ''.join( result )

    def print( self, *args, **kwargs ):
        """Print the graphical version of the results produced by ansi_format()."""
        print( self.ansi_format( *args, **kwargs ) )

    def __str__( self ):
        return self.ansi_format()


def stats( source, start=None, end=None, length=None, width=64, height=12 ):
    start = 0 if (start is None) else start
    if (end is not None) and (length is not None):
        raise ValueError( 'Can\'t define both an end and a length!' )
    elif (length is not None):
        end = start+length
    elif (end is not None):
        pass
    else:
        end = len( source )

    stat = Stats( source[start:end] )
    stat.print( width=width, height=height )


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


def mix( a, b, alpha ):
    return (b-a)*alpha + a

def mix_line( points, alpha ):
    count = len( points ) - 1
    if alpha == 1:
        return points[-1]
    return mix(
        points[math.floor( alpha*count )],
        points[math.floor( alpha*count )+1],
        math.fmod( alpha*count, 1 )
    )

HEATMAP_LINES = (
    (0x00, 0x70, 0xe8, 0xf0, 0xf8),
    (0x00, 0x34, 0x6c, 0xb0, 0xec),
    (0x00, 0x00, 0x00, 0x40, 0xa0),
)
HEATMAP_COLOURS = [[round( mix_line( HEATMAP_LINES[j], i/255 ) ) for j in range( 3 )] for i in range( 256 )]

#: ANSI escape sequence container
ANSI_FORMAT_BASE = '\x1b[{}m'
#: ANSI escape sequence for resetting the colour settings to the default.
ANSI_FORMAT_RESET_CMD = '0'
ANSI_FORMAT_RESET = ANSI_FORMAT_BASE.format( ANSI_FORMAT_RESET_CMD )
#: ANSI escape sequence for setting the foreground colour (24-bit).
ANSI_FORMAT_FOREGROUND_CMD = '38;2;{};{};{}'
#: ANSI escape sequence for setting the background colour (24-bit).
ANSI_FORMAT_BACKGROUND_CMD = '48;2;{};{};{}'
#: ANSI escape sequence for setting the foreground colour (xterm).
ANSI_FORMAT_FOREGROUND_XTERM_CMD = '38;5;{}'
#: ANSI escape sequence for setting the background colour (xterm).
ANSI_FORMAT_BACKGROUND_XTERM_CMD = '48;5;{}'
#: ANSI escape sequence for bold text
ANSI_FORMAT_BOLD_CMD = '1'
#: ANSI escape sequence for faint text
ANSI_FORMAT_FAINT_CMD = '2'
#: ANSI escape sequence for bold text
ANSI_FORMAT_ITALIC_CMD = '3'
#: ANSI escape sequence for bold text
ANSI_FORMAT_UNDERLINE_CMD = '4'
#: ANSI escape sequence for bold text
ANSI_FORMAT_BLINK_CMD = '5'
#: ANSI escape sequence for inverted text
ANSI_FORMAT_INVERTED_CMD = '7'

def normalise_rgba( raw_colour ):
    if raw_colour is None:
        return (0, 0, 0, 0)
    elif hasattr( raw_colour, 'rgba' ):
        return raw_colour.rgba
    elif len( raw_colour ) == 3:
        return (raw_colour[0], raw_colour[1], raw_colour[2], 255)
    elif len( raw_colour ) == 4:
        return (raw_colour[0], raw_colour[1], raw_colour[2], raw_colour[3])
    raise ValueError( 'raw_colour must be either None, a Colour, or a tuple (RGB/RGBA)' )


def ansi_format_escape( foreground=None, background=None, bold=False, faint=False,
    italic=False, underline=False, blink=False, inverted=False ):
    """Returns the ANSI escape sequence to set character formatting.

    foreground
        Foreground colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    background
        Background colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    bold
        Enable bold text (default: False)

    faint
        Enable faint text (default: False)

    italic
        Enable italic text (default: False)

    underline
        Enable underlined text (default: False)

    blink
        Enable blinky text (default: False)

    inverted
        Enable inverted text (default: False)
    """
    fg_format = None
    if isinstance( foreground, int ):
        fg_format = ANSI_FORMAT_FOREGROUND_XTERM_CMD.format( foreground )
    else:
        fg_rgba = normalise_rgba( foreground )
        if fg_rgba[3] != 0:
            fg_format = ANSI_FORMAT_FOREGROUND_CMD.format( *fg_rgba[:3] )

    bg_format = None
    if isinstance( background, int ):
        bg_format = ANSI_FORMAT_BACKGROUND_XTERM_CMD.format( background )
    else:
        bg_rgba = normalise_rgba( background )
        if bg_rgba[3] != 0:
            bg_format = ANSI_FORMAT_BACKGROUND_CMD.format( *bg_rgba[:3] )

    colour_format = []
    if fg_format is not None:
        colour_format.append( fg_format )
    if bg_format is not None:
        colour_format.append( bg_format )
    if bold:
        colour_format.append( ANSI_FORMAT_BOLD_CMD )
    if faint:
        colour_format.append( ANSI_FORMAT_FAINT_CMD )
    if italic:
        colour_format.append( ANSI_FORMAT_ITALIC_CMD )
    if underline:
        colour_format.append( ANSI_FORMAT_UNDERLINE_CMD )
    if blink:
        colour_format.append( ANSI_FORMAT_BLINK_CMD )
    if inverted:
        colour_format.append( ANSI_FORMAT_INVERTED_CMD )

    colour_format = ANSI_FORMAT_BASE.format( ';'.join( colour_format ) )
    return colour_format


def ansi_format_string( string, foreground=None, background=None, reset=True, bold=False,
    faint=False, italic=False, underline=False, blink=False, inverted=False ):
    """Returns a Unicode string formatted with an ANSI escape sequence.

    string
        String to format

    foreground
        Foreground colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    background
        Background colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    reset
        Reset the formatting at the end (default: True)

    bold
        Enable bold text (default: False)

    faint
        Enable faint text (default: False)

    italic
        Enable italic text (default: False)

    underline
        Enable underlined text (default: False)

    blink
        Enable blinky text (default: False)

    inverted
        Enable inverted text (default: False)
    """
    colour_format = ansi_format_escape( foreground, background, bold, faint,
                                        italic, underline, blink, inverted )
    reset_format = '' if not reset else ANSI_FORMAT_RESET

    return '{}{}{}'.format( colour_format, string, reset_format )


def ansi_format_pixels( top, bottom, reset=True, repeat=1 ):
    """Return the ANSI escape sequence to render two vertically-stacked pixels as a
    single monospace character.

    top
        Top colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    bottom
        Bottom colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    reset
        Reset the formatting at the end (default: True)

    repeat
        Number of horizontal pixels to render (default: 1)
    """
    top_src = None
    if isinstance( top, int ):
        top_src = top
    else:
        top_rgba = normalise_rgba( top )
        if top_rgba[3] != 0:
            top_src = top_rgba

    bottom_src = None
    if isinstance( bottom, int ):
        bottom_src = bottom
    else:
        bottom_rgba = normalise_rgba( bottom )
        if bottom_rgba[3] != 0:
            bottom_src = bottom_rgba

    # short circuit for empty pixel
    if (top_src is None) and (bottom_src is None):
        return ' '*repeat 

    string = '▀'*repeat;
    colour_format = []

    if top_src == bottom_src:
        string = '█'*repeat
    elif (top_src is None) and (bottom_src is not None):
        string = '▄'*repeat

    if (top_src is None) and (bottom_src is not None):
        if isinstance( bottom_src, int ):
            colour_format.append( ANSI_FORMAT_FOREGROUND_XTERM_CMD.format( bottom_src ) )
        else:
            colour_format.append( ANSI_FORMAT_FOREGROUND_CMD.format( *bottom_src[:3] ) )
    else:
        if isinstance( top_src, int ):
            colour_format.append( ANSI_FORMAT_FOREGROUND_XTERM_CMD.format( top_src ) )
        else:
            colour_format.append( ANSI_FORMAT_FOREGROUND_CMD.format( *top_src[:3] ) )

    if top_src is not None and bottom_src is not None and top_src != bottom_src:
        if isinstance( top_src, int ):
            colour_format.append( ANSI_FORMAT_BACKGROUND_XTERM_CMD.format( bottom_src ) )
        else:
            colour_format.append( ANSI_FORMAT_BACKGROUND_CMD.format( *bottom_src[:3] ) )

    colour_format = ANSI_FORMAT_BASE.format( ';'.join( colour_format ) )
    reset_format = '' if not reset else ANSI_FORMAT_RESET

    return '{}{}{}'.format( colour_format, string, reset_format )

#: Shorthand for ansi_format_string()
colour = ansi_format_string

#: Shorthand for ansi_format_pixels()
pixels = ansi_format_pixels


def ansi_format_bar_graph_iter( data, width=64, height=12, y_min=None, y_max=None ):
    if width <= 0:
        raise ValueError( 'Width of the graph must be greater than zero' )
    if height % 2:
        raise ValueError( 'Height of the graph must be a multiple of 2' )
    if y_min is None:
        y_min = min( data )
    y_min = min( y_min, 0 )
    if y_max is None:
        y_max = max( data )
    y_max = max( y_max, 0 )

    # determine top-left of vertical origin
    if y_max <= 0:
        top_height, bottom_height = 0, height
        y_scale = 8*height/y_min
    elif y_min >= 0:
        top_height, bottom_height = height, 0
        y_scale = 8*height/y_max
    else:
        top_height, bottom_height = height//2, height//2
        y_scale = 8*height/(2*max( abs( y_min ), abs( y_max ) ))

    # precalculate sizes
    sample_count = len( data )
    if sample_count == 0:
        # empty graph
        samples = [(0, 0) for x in range( width )]
    else:
        if sample_count <= width:
            sample_ranges = [(math.floor( i*sample_count/width ), math.floor( i*sample_count/width )+1) for i in range( width )]
        else:
            sample_ranges = [(round( i*sample_count/width ), round( (i+1)*sample_count/width )) for i in range( width )]
        samples = [(round( min( data[x[0]:x[1]] )*y_scale ), round( max( data[x[0]:x[1]] )*y_scale )) for x in sample_ranges]

    for y in range( top_height, 0, -1 ):
        result = []
        for _, value in samples:
            if value // 8 >= y:
                result.append( BAR_VERT[8] )
            elif value // 8 == y-1:
                result.append( BAR_VERT[value % 8] )
            else:
                result.append( BAR_VERT[0] )
        yield ''.join( result )

    for y in range( 1, bottom_height+1, 1 ):
        result = []
        for value, _ in samples:
            if -value // 8 >= y:
                result.append( BAR_VERT[8] )
            elif -value // 8 == y-1:
                result.append( ansi_format_string( BAR_VERT[8-((-value) % 8)], inverted=True ) )
            else:
                result.append( BAR_VERT[0] )
        yield ''.join( result )


def ansi_format_image_iter( data_fetch, x_start=0, y_start=0, width=32, height=32, frame=0, columns=1, downsample=1 ):
    """Return the ANSI escape sequence to render a bitmap image.

    data_fetch
        Function that takes three arguments (x position, y position, and frame) and returns
        a Colour corresponding to the pixel stored there, or Transparent if the requested 
        pixel is out of bounds.

    x_start
        Offset from the left of the image data to render from. Defaults to 0.

    y_start
        Offset from the top of the image data to render from. Defaults to 0.

    width
        Width of the image data to render. Defaults to 32.

    height
        Height of the image data to render. Defaults to 32.

    frame
        Single frame number/object, or a list to render in sequence. Defaults to frame 0.

    columns
        Number of frames to render per line (useful for printing tilemaps!). Defaults to 1.

    downsample
        Shrink larger images by printing every nth pixel only. Defaults to 1.
    """
    frames = []
    try:
        frame_iter = iter( frame )
        frames = [f for f in frame_iter]
    except TypeError:
        frames = [frame]

    rows = math.ceil( len( frames )/columns )
    for r in range( rows ):
        for y in range( 0, height, 2*downsample ):
            result = []
            for c in range( min( (len( frames )-r*columns), columns ) ):
                row = []
                for x in range( 0, width, downsample ):
                    fr = frames[r*columns + c]
                    c1 = data_fetch( x_start+x, y_start+y, fr )
                    c2 = data_fetch( x_start+x, y_start+y+downsample, fr )
                    row.append( (c1, c2) )
                prev_pixel = None
                pointer = 0
                while pointer < len( row ):
                    start = pointer
                    pixel = row[pointer]
                    while pointer < len( row ) and (row[pointer] == pixel):
                        pointer += 1
                    result.append( ansi_format_pixels( pixel[0], pixel[1], repeat=pointer-start ) )
            yield ''.join( result )
    return


def pixdump_iter( source, start=None, end=None, length=None, width=64, palette=None ):
    """Return the contents of a byte string as a 256 colour image.

    source
        The byte string to print.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    width
        Width of image to render in pixels (default: 64)

    palette
        List of Colours to use (default: test palette)
    """
    assert is_bytes( source )

    if not palette:
        palette = HEATMAP_COLOURS

    start = 0 if (start is None) else start
    if (end is not None) and (length is not None):
        raise ValueError( 'Can\'t define both an end and a length!' )
    elif (length is not None):
        end = start+length
    elif (end is not None):
        pass
    else:
        end = len( source )

    start = max( start, 0 )
    end = min( end, len( source ) )
    if len( source ) == 0 or (start == end == 0):
        return

    height = math.ceil( (end-start)/width )

    def data_fetch( x_pos, y_pos, frame ):
        index = y_pos*width + x_pos + start
        if index >= end:
            return (0, 0, 0, 0)
        return palette[source[index]]

    return ansi_format_image_iter( data_fetch, width=width, height=height )


def pixdump( source, start=None, end=None, length=None, width=64, palette=None ):
    """Print the contents of a byte string as a 256 colour image.

    source
        The byte string to print.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    width
        Width of image to render in pixels (default: 64)

    palette
        List of Colours to use (default: test palette)
    """

    for line in pixdump_iter( source, start, end, length, width, palette ):
        print( line )


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
