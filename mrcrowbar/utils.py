"""General utility functions useful for reverse engineering."""

import math
import io
import mmap
import logging
import time
logger = logging.getLogger( __name__ )

from mrcrowbar import ansi, colour, encoding, statistics, sound
from mrcrowbar.common import is_bytes, read, bounds

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

DIFF_COLOUR_MAP = (9, 10)


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


def diff( source1, source2, prefix='source', depth=None ):
    """Perform a diff between two objects.

    source1
        The first source.

    source2
        The second source.

    prefix
        The name of the base element to display.

    depth
        Maximum number of levels to traverse.
    """
    depth = depth-1 if depth is not None else None
    def abbr( src ):
        return src if type( src ) in (int, float, str, bytes) else (src.__class__.__module__, src.__class__.__name__)

    if type( source1 ) != type( source2 ):
        print( ansi.format_string( '- {}: {}'.format( prefix, abbr( source1 ) ), foreground=DIFF_COLOUR_MAP[0] ) )
        print( ansi.format_string( '+ {}: {}'.format( prefix, abbr( source2 ) ), foreground=DIFF_COLOUR_MAP[1] ) )
    else:
        if type( source1 ) == list:
            for i in range( max( len( source1 ), len( source2 ) ) ):
                prefix_mod = prefix+'[{}]'.format( i )
                if i < len( source1 ) and i < len( source2 ):
                    diff( source1[i], source2[i], prefix=prefix_mod, depth=depth )
                elif i >= len( source2 ):
                    print( ansi.format_string( '- {}: {}'.format( prefix_mod, abbr( source1[i] ) ), foreground=DIFF_COLOUR_MAP[0] ) )
                else:
                    print( ansi.format_string( '+ {}: {}'.format( prefix_mod, abbr( source2[i] ) ), foreground=DIFF_COLOUR_MAP[1] ) )
        elif type( source1 ) == bytes:
            if source1 != source2:
                print( '* {}:'.format( prefix ) )
                for line in hexdump_diff_iter( source1, source2 ):
                    print( line )
        elif type( source1 ) in (int, float, str):
            if source1 != source2:
                print( ansi.format_string( '- {}: {}'.format( prefix, source1 ), foreground=DIFF_COLOUR_MAP[0] ) )
                print( ansi.format_string( '+ {}: {}'.format( prefix, source2 ), foreground=DIFF_COLOUR_MAP[1] ) )
        elif hasattr( source1, 'serialised' ):  # Block
            s1 = source1.serialised
            s2 = source2.serialised
            if s1 != s2 and depth is not None and depth <= 0:
                print( ansi.format_string( '- {}: {}'.format( prefix, abbr( source1 ) ), foreground=DIFF_COLOUR_MAP[0] ) )
                print( ansi.format_string( '+ {}: {}'.format( prefix, abbr( source2 ) ), foreground=DIFF_COLOUR_MAP[1] ) )
            else:
                assert s1[0] == s2[0]
                assert len( s1[1] ) == len( s2[1] )
                for i in range( len( s1[1] ) ):
                    assert s1[1][i][0] == s2[1][i][0]
                    if s1[1][i][1] != s2[1][i][1]:
                        diff( getattr( source1, s1[1][i][0] ), getattr( source2, s1[1][i][0] ), prefix='{}.{}'.format( prefix, s1[1][i][0] ), depth=depth )
        else:
            if source1 != source2:
                print( ansi.format_string( '- {}: {}'.format( prefix, abbr( source1 ) ), foreground=DIFF_COLOUR_MAP[0] ) )
                print( ansi.format_string( '+ {}: {}'.format( prefix, abbr( source2 ) ), foreground=DIFF_COLOUR_MAP[1] ) )


def histdump_iter( source, start=None, end=None, length=None, samples=0x10000, width=64, address_base=None ):
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    start = max( start, 0 )
    end = min( end, len( source ) )
    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base-start if address_base is not None else 0

    for offset in range( start, end, samples ):
        yield ansi.format_histdump_line( source, offset, length=samples, end=end, width=width, address_base_offset=address_base_offset )
    return


def histdump( source, start=None, end=None, length=None, samples=0x10000, width=64, address_base=None ):
    for line in histdump_iter( source, start, end, length, samples, width, address_base ):
        print( line )


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
    start, end = bounds( start, end, length, len( source ) )

    start = max( start, 0 )
    end = min( end, len( source ) )
    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base-start if address_base is not None else 0

    for offset in range( start, end, minor_len*major_len ):
        yield ansi.format_hexdump_line( source, offset, end, major_len, minor_len, colour, address_base_offset=address_base_offset )
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
                    highlights[i] = DIFF_COLOUR_MAP[0]
            if offset < len( source1 ):
                yield ansi.format_hexdump_line( source1, offset, min( end, len( source1 ) ), major_len, minor_len, colour, prefix='-', highlight_addr=DIFF_COLOUR_MAP[0], highlight_map=highlights, address_base_offset=address_base_offset )
            highlights = {k: DIFF_COLOUR_MAP[1] for k in highlights.keys()}
            if offset < len( source2 ):
                yield ansi.format_hexdump_line( source2, offset, min( end, len( source2 ) ), major_len, minor_len, colour, prefix='+' , highlight_addr=DIFF_COLOUR_MAP[1], highlight_map=highlights, address_base_offset=address_base_offset )
        elif show_lines[offset] == 1:
            yield ansi.format_hexdump_line( source1, offset, end, major_len, minor_len, colour, prefix=' ', address_base_offset=address_base_offset )
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


def stats( source, start=None, end=None, length=None, width=64, height=12 ):
    start, end = bounds( start, end, length, len( source ) )

    stat = statistics.Stats( source[start:end] )
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


def pixdump_iter( source, start=None, end=None, length=None, width=64, height=None, palette=None ):
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

    height
        Height of image to render in pixels (default: auto)

    palette
        List of Colours to use (default: test palette)
    """
    assert is_bytes( source )

    if not palette:
        palette = colour.TEST_PALETTE

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
        return iter(())

    if height is None:
        height = math.ceil( (end-start)/width )

    def data_fetch( x_pos, y_pos, frame ):
        index = y_pos*width + x_pos + start
        if index >= end:
            return (0, 0, 0, 0)
        return palette[source[index]]

    return ansi.format_image_iter( data_fetch, width=width, height=height )


def pixdump( source, start=None, end=None, length=None, width=64, height=None, palette=None ):
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

    height
        Height of image to render in pixels (default: auto)

    palette
        List of Colours to use (default: test palette)
    """

    for line in pixdump_iter( source, start, end, length, width, height, palette ):
        print( line )


def pixdump_sweep( source, range=(64,), delay=None, start=None, end=None, length=None, height=None, palette=None ):
    """Test printing the contents of a byte string as a 256 colour image for a range of widths.

    source
        The byte string to print.

    range
        List of widths to render (default: [64])

    delay
        Number of seconds to wait between each print (default: 0)

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    height
        Height of image to render in pixels (default: auto)

    palette
        List of Colours to use (default: test palette)
    """
    for w in range:
        print( w )
        for line in pixdump_iter( source, start, end, length, w, height, palette ):
            print( line )
        print()
        if delay is not None:
            time.sleep( delay )


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
