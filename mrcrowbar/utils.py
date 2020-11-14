"""General utility functions useful for reverse engineering."""

import io
import logging
import math
import mmap
import re
import time
logger = logging.getLogger( __name__ )

from mrcrowbar import ansi, colour, encoding as enco, statistics, sound
from mrcrowbar.common import is_bytes, read, bounds

globals().update( enco._load_raw_types() )

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


DIFF_COLOUR_MAP = (9, 10)


def grep_iter( pattern, source, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False ):
    """Return an iterator that finds the contents of a byte string that match a pattern.

    pattern
        Pattern to match, as a Python string

    source
        Byte string to inspect

    encoding
        Convert strings in the pattern to a specific Python encoding (default: utf8)

    fixed_string
        Interpret the pattern as a fixed string (disable regular expressions)

    hex_format
        Interpret the pattern as raw hexidecimal (default: false)

    ignore_case
        Perform a case-insensitive search
    """
    assert isinstance( pattern, str )
    assert is_bytes( source )
    flags = re.DOTALL
    if ignore_case:
        flags |= re.IGNORECASE
    regex = re.compile( enco.regex_pattern_to_bytes( pattern, encoding=encoding, fixed_string=fixed_string, hex_format=hex_format ), flags )

    return regex.finditer( source )


def grep( pattern, source, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False ):
    """Find the contents of a byte string that match a pattern.

    pattern
        Pattern to match, as a Python string

    source
        Source byte string to search

    encoding
        Convert strings in the pattern to a specific Python encoding (default: utf8)

    fixed_string
        Interpret the pattern as a fixed string (disable regular expressions)

    hex_format
        Interpret the pattern as raw hexidecimal (default: false)

    ignore_case
        Perform a case-insensitive search
    """
    return [x for x in grep_iter( pattern, source, encoding, fixed_string, hex_format, ignore_case )]


def find_iter( source, substring, start=None, end=None, length=None, overlap=False, ignore_case=False ):
    """Return an iterator that finds every location of a substring in a source byte string.

    source
        Source byte string or Python string to search.

    substring
        Substring to match, as a byte string or a Python string

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    overlap
        Whether to return overlapping matches (default: false)

    ignore_case
        Perform a case-insensitive search
    """
    start, end = bounds( start, end, length, len( source ) )

    if ignore_case:
        source = source.lower()
        substring = substring.lower()
    pointer = start
    result = source.find( substring, pointer, end )
    while result != -1:
        yield (result, result + len( substring ))
        if overlap:
            pointer = result + 1
        else:
            pointer = result + len( substring )
        result = source.find( substring, pointer, end )


def find( source, substring, start=None, end=None, length=None, overlap=False, ignore_case=False ):
    """Find every location of a substring in a source string.

    source
        Source byte string to search.

    substring
        Substring to match, as a Python byte string

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    overlap
        Whether to return overlapping matches (default: false)

    ignore_case
        Perform a case-insensitive search
    """
    return [x for x in find_iter( source, substring, start, end, length, overlap, ignore_case )]


def find_encoded_iter( source, substring, start=None, end=None, length=None, overlap=False, ignore_case=False, encodings=['utf_8'] ):
    """Return an iterator that finds every location of a substring in a source byte string, checking against multiple encodings.

    source
        Source byte string to search.

    substring
        Substring to match, as a Python string

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    overlap
        Return overlapping matches (default: false)

    ignore_case
        Perform a case-insensitive search

    encodings
        A list of encodings to try, or 'all' for every supported encoding (default: ['utf_8'])
    """
    assert is_bytes( source )

    if encodings == 'all':
        encodings = enco.CODECS
    subs = {}
    for encoding in encodings:
        try:
            test = substring.encode( encoding )
            if test not in subs:
                subs[test] = []
            subs[test].append( encoding )
        except UnicodeEncodeError:
            continue

    for test in subs:
        for x in find_iter( source, test, start, end, length, overlap, ignore_case ):
            yield (x[0], x[1], subs[test])


def find_encoded( source, substring, start=None, end=None, length=None, overlap=False, ignore_case=False, encodings=['utf_8'] ):
    """Find every location of a substring in a source byte string, checking against multiple encodings.

    source
        Source byte string to search.

    substring
        Substring to match, as a Python string

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    overlap
        Return overlapping matches (default: false)

    ignore_case
        Perform a case-insensitive search

    encodings
        A list of encodings to try, or 'all' for every supported encoding (default: ['utf_8'])
    """
    return [x for x in find_encoded_iter( source, substring, start, end, length, overlap, ignore_case, encodings )]


def find_unknown_iter( source, substring, start=None, end=None, length=None, overlap=False, char_size=1 ):
    """Return an iterator that finds every location of a substring in a source byte string, guessing the encoding.

    source
        Source byte string to search.

    substring
        Substring to match, as a Python string

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    overlap
        Return overlapping matches (default: false)

    char_size
        Size in bytes of each character in the source (default: 1)
    """
    unk_dict, pattern = enco.regex_unknown_encoding_match( substring, char_size=char_size )
    if overlap:
        pattern = b'(?=(' + pattern + b'))'
    regex = re.compile( pattern, flags=re.DOTALL )
    for match in regex.finditer( source ):
        groups = match.groups()
        span_0, span_1 = match.span()
        if overlap:
            span_1 += len( groups[0] )
            groups = groups[1:]
        yield (span_0, span_1, {key: groups[unk_dict[key]] for key in unk_dict})


def find_unknown( source, substring, start=None, end=None, length=None, overlap=False, char_size=1 ):
    """Find every location of a substring in a source byte string, guessing the encoding.

    source
        Source byte string to search.

    substring
        Substring to match, as a Python string

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    overlap
        Return overlapping matches (default: false)

    char_size
        Size in bytes of each character in the source (default: 1)
    """
    return [x for x in find_unknown_iter( source, substring, start, end, length, overlap, char_size )]


def hexdump_grep_iter( pattern, source, start=None, end=None, length=None, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False, major_len=8, minor_len=4, colour=True, address_base=None, before=2, after=2, title=None ):
    """Return an iterator that searches a byte string for a pattern and renders the result in tabular hexadecimal/ASCII format.

    pattern
        Pattern to match, as a Python string

    source
        The byte string to print.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    encoding
        Convert strings in the pattern to a specific Python encoding (default: utf8)

    fixed_string
        Interpret the pattern as a fixed string (disable regular expressions)

    hex_format
        Interpret the pattern as raw hexidecimal (default: false)

    ignore_case
        Perform a case-insensitive search

    major_len
        Number of hexadecimal groups per line

    minor_len
        Number of bytes per hexadecimal group

    colour
        Add ANSI colour formatting to output (default: true)

    address_base
        Base address to use for labels (default: start)

    before
        Number of lines of context preceeding a match to show

    after
        Number of lines of context following a match to show

    title
        Name to print as a heading if there's a match. Useful for file names.

    Raises ValueError if both end and length are defined.
    """
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base-start if address_base is not None else 0
    stride = minor_len*major_len

    regex_iter = grep_iter( pattern, source[start:end], encoding, fixed_string, hex_format, ignore_case )

    hb = ansi.HexdumpHighlightBuffer( source, start, end, None, major_len, minor_len, colour, address_base, before, after, title )
    for match in regex_iter:
        hb.add_span( (match.span()[0]+start, match.span()[1]+start) )

        yield from hb.flush()

    yield from hb.flush( final=True )


def hexdump_grep( pattern, source, start=None, end=None, length=None, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False, major_len=8, minor_len=4, colour=True, address_base=None, before=2, after=2, title=None ):
    """Search a byte string for a pattern and print the result in tabular hexadecimal/ASCII format.

    pattern
        Pattern to match, as a Python string

    source
        The byte string to print.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    encoding
        Convert strings in the pattern to a specific Python encoding (default: utf8)

    fixed_string
        Interpret the pattern as a fixed string (disable regular expressions)

    hex_format
        Interpret the pattern as raw hexidecimal (default: false)

    ignore_case
        Perform a case-insensitive search

    major_len
        Number of hexadecimal groups per line

    minor_len
        Number of bytes per hexadecimal group

    colour
        Add ANSI colour formatting to output (default: true)

    address_base
        Base address to use for labels (default: start)

    before
        Number of lines of context preceeding a match to show

    after
        Number of lines of context following a match to show

    title
        Name to print as a heading if there's a match. Useful for file names.

    Raises ValueError if both end and length are defined.
    """

    for line in hexdump_grep_iter( pattern, source, start, end, length, encoding, fixed_string, hex_format, ignore_case, major_len, minor_len, colour, address_base, before, after, title ):
        print( line )


def listdump_grep_iter( pattern, source, start=None, end=None, length=None, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False, address_base=None, title=None ):
    """Return an iterator that searches a byte string for a pattern and renders the result in list format.

    pattern
        Pattern to match, as a Python string

    source
        The byte string to print.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    encoding
        Convert strings in the pattern to a specific Python encoding (default: utf8)

    fixed_string
        Interpret the pattern as a fixed string (disable regular expressions)

    hex_format
        Interpret the pattern as raw hexidecimal (default: false)

    ignore_case
        Perform a case-insensitive search

    major_len
        Number of hexadecimal groups per line

    minor_len
        Number of bytes per hexadecimal group

    colour
        Add ANSI colour formatting to output (default: true)

    address_base
        Base address to use for labels (default: start)

    before
        Number of lines of context preceeding a match to show

    after
        Number of lines of context following a match to show

    title
        Name to print as a heading if there's a match. Useful for file names.

    Raises ValueError if both end and length are defined.
    """

    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base-start if address_base is not None else 0

    regex_iter = grep_iter( pattern, source[start:end], encoding, fixed_string, hex_format, ignore_case )

    for match in regex_iter:
        start_off = match.span()[0]+start+address_base_offset
        end_off = match.span()[1]+start+address_base_offset
        digits = '{:0'+str( max( 8, math.floor( math.log( end+address_base_offset )/math.log( 16 ) ) ) )+'x}'
        line = (digits+':'+digits).format( start_off, end_off )
        line += ':{}'.format( repr( match.group( 0 ) ) )
        if title:
            line = '{}:'.format( title ) + line
        yield line


def listdump_grep( pattern, source, start=None, end=None, length=None, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False, address_base=None, title=None ):
    """Search a byte string for a pattern and print the result in list format.

    pattern
        Pattern to match, as a Python string

    source
        The byte string to print.

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    encoding
        Convert strings in the pattern to a specific Python encoding (default: utf8)

    fixed_string
        Interpret the pattern as a fixed string (disable regular expressions)

    hex_format
        Interpret the pattern as raw hexidecimal (default: false)

    ignore_case
        Perform a case-insensitive search

    major_len
        Number of hexadecimal groups per line

    minor_len
        Number of bytes per hexadecimal group

    colour
        Add ANSI colour formatting to output (default: true)

    address_base
        Base address to use for labels (default: start)

    before
        Number of lines of context preceeding a match to show

    after
        Number of lines of context following a match to show

    title
        Name to print as a heading if there's a match. Useful for file names.

    Raises ValueError if both end and length are defined.
    """

    for line in list_grep_iter( pattern, source, start, end, length, encoding, fixed_string, hex_format, ignore_case, address_base, title ):
        print( line )


def search_iter( pattern, source, prefix='source', depth=None, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False ):
    """Return an iterator that finds the Fields inside a Block that match a pattern.

    pattern
        Pattern to match, as a Python string

    source
        Block object to inspect

    encoding
        Convert strings in the pattern to a specific Python encoding (default: utf8)

    fixed_string
        Interpret the pattern as a fixed string (disable regular expressions)

    hex_format
        Interpret the pattern as raw hexidecimal (default: false)

    ignore_case
        Perform a case-insensitive search
    """
    from mrcrowbar.models import Block, Chunk

    contains = False
    depth = depth-1 if depth is not None else None

    match_list = [x.span() for x in grep( pattern, source.export_data(), encoding, fixed_string, hex_format, ignore_case )]

    fields = source.get_field_names()

    def check_field( offset, size, data, pref ):
        for match in match_list:
            if offset <= match[0] < offset + size or offset <= match[1] < offset+size:
                if isinstance( data, Block ):
                    success = False
                    for x in search_iter( pattern, data, pref, depth, encoding, fixed_string, hex_format, ignore_case ):
                        success = True
                        yield x
                    if not success:
                        # no exact match, yield entire object
                        yield pref
                elif isinstance( data, Chunk ):
                    success = False
                    for x in search_iter( pattern, data.obj, '{}.obj'.format( pref ), depth, encoding, fixed_string, hex_format, ignore_case ):
                        success = True
                        yield x
                    if not success:
                        yield pref
                else:
                    yield pref
                break

    for name in fields:
        offset = source.get_field_start_offset( name )
        size = source.get_field_size( name )
        data = getattr( source, name )
        if type( data ) == list:
            # field contents is a list, check each of the individual elements
            el_offset = offset
            for i, el in enumerate( data ):
                el_size = source.get_field_size( name, index=i )
                yield from check_field( el_offset, el_size, el, '{}.{}[{}]'.format( prefix, name, i ) )
                el_offset += el_size
        else:
            yield from check_field( offset, size, data, '{}.{}'.format( prefix, name ) )


def search( pattern, source, prefix='source', depth=None, encoding='utf8', fixed_string=False, hex_format=False, ignore_case=False ):
    """Find the Fields inside a Block that match a byte pattern.

    pattern
        Pattern to match, as a Python string

    source
        Block object to inspect

    encoding
        Convert strings in the pattern to a specific Python encoding (default: utf8)

    fixed_string
        Interpret the pattern as a fixed string (disable regular expressions)

    hex_format
        Interpret the pattern as raw hexidecimal (default: false)

    ignore_case
        Perform a case-insensitive search
    """
    return [x for x in search_iter( pattern, source, prefix, depth, encoding, fixed_string, hex_format, ignore_case )]


def listdump_find_encoded_iter( source, substring, start=None, end=None, length=None, overlap=False, ignore_case=False, encodings=['utf_8'] ):
    """Return an iterator that finds every location of a substring in a source byte string, checking against multiple encodings, and renders the result in list format.

    source
        Source byte string or Python string to search.

    substring
        Substring to match, as a byte string or a Python string

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    overlap
        Whether to return overlapping matches (default: false)

    ignore_case
        Perform a case-insensitive search

    encodings
        A list of encodings to try, or 'all' for every supported encoding (default: ['utf_8'])
    """
    pass



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


def diff_iter( source1, source2, prefix='source', depth=None ):
    """Return an iterator that finds differences between two objects.

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
        return src if type( src ) in (int, float, str, bytes, bytearray) else (src.__class__.__module__, src.__class__.__name__)

    if (type( source1 ) != type( source2 )) and not (is_bytes( source1 ) and is_bytes( source2 )):
        yield (prefix, abbr( source1 ), abbr( source2 ))
    else:
        if type( source1 ) == list:
            for i in range( max( len( source1 ), len( source2 ) ) ):
                prefix_mod = prefix+'[{}]'.format( i )

                if i < len( source1 ) and i < len( source2 ):
                    yield from diff_iter( source1[i], source2[i], prefix=prefix_mod, depth=depth )
                elif i >= len( source2 ):
                    yield (prefix_mod, abbr( source1[i] ), None)
                else:
                    yield (prefix_mod, None, abbr( source2[i] ))
        elif is_bytes( source1 ):
            if source1 != source2:
                yield( prefix, source1, source2 )
        elif type( source1 ) in (int, float, str):
            if source1 != source2:
                yield (prefix, source1, source2)
        elif hasattr( source1, 'serialised' ):  # Block
            s1 = source1.serialised
            s2 = source2.serialised
            if s1 != s2 and depth is not None and depth <= 0:
                yield (prefix, source1, source2)
            else:
                assert s1[0] == s2[0]
                assert len( s1[1] ) == len( s2[1] )
                for i in range( len( s1[1] ) ):
                    assert s1[1][i][0] == s2[1][i][0]
                    if s1[1][i][1] != s2[1][i][1]:
                        yield from diff_iter( getattr( source1, s1[1][i][0] ), getattr( source2, s1[1][i][0] ), prefix='{}.{}'.format( prefix, s1[1][i][0] ), depth=depth )
        else:
            if source1 != source2:
                yield (prefix, source1, source2)


def diff( source1, source2, prefix='source', depth=None ):
    """Find differences between two objects.

    source1
        The first source.

    source2
        The second source.

    prefix
        The name of the base element to display.

    depth
        Maximum number of levels to traverse.
    """
    return [x for x in diff_iter( source1, source2, prefix, depth )]


def diffdump_iter( source1, source2, prefix='source', depth=None ):
    """Return an iterator that renders a list of differences between two objects.

    source1
        First source object

    source2
        Second source object

    prefix
        The name of the base element to display.

    depth
        Maximum number of levels to traverse.
    """
    same = True
    for p, s1, s2 in diff_iter( source1, source2, prefix, depth ):
        if is_bytes( s1 ) and is_bytes( s2 ):
            yield '* {}:'.format( p )
            yield from hexdump_diff_iter( s1, s2 )
            same = False
            continue
        if s1 is not None:
            yield ansi.format_string( '- {}: {}'.format( p, s1 ), foreground=DIFF_COLOUR_MAP[0] )
            same = False
        if s2 is not None:
            yield ansi.format_string( '+ {}: {}'.format( p, s2 ), foreground=DIFF_COLOUR_MAP[1] )
            same = False
    return same


def diffdump( source1, source2, prefix='source', depth=None ):
    """Print a list of differences between two objects.

    source1
        First source object

    source2
        Second source object

    prefix
        The name of the base element to display.

    depth
        Maximum number of levels to traverse.
    """
    for line in diffdump_iter( source1, source2, prefix, depth ):
        print( line )


def histdump_iter( source, start=None, end=None, length=None, samples=0x10000, width=64, address_base=None ):
    """Return an iterator that renders a histogram of a byte string.

    source
        Source byte string to measure

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    samples
        Number of samples per histogram slice (default: 0x10000)

    width
        Width of rendered histogram (default: 64)

    address_base
        Base address to use for labelling (default: start)
    """
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base-start if address_base is not None else 0

    for offset in range( start, end, samples ):
        yield ansi.format_histdump_line( source, offset, length=samples, end=end, width=width, address_base_offset=address_base_offset )
    return


def histdump( source, start=None, end=None, length=None, samples=0x10000, width=64, address_base=None ):
    """Print a histogram of a byte string.

    source
        Source byte string to measure

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    samples
        Number of samples per histogram slice (default: 0x10000)

    width
        Width of rendered histogram (default: 64)

    address_base
        Base address to use for labelling (default: start)
    """
    for line in histdump_iter( source, start, end, length, samples, width, address_base ):
        print( line )


def hexdump_iter( source, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, address_base=None, show_offsets=True, show_glyphs=True ):
    """Return an iterator that renders a byte string in tabular hexadecimal/ASCII format.
    
    source
        Source byte string to render

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

    show_offsets
        Display offsets at the start of each line (default: true)

    show_glyphs
        Display glyph map at the end of each line (default: true)

    Raises ValueError if both end and length are defined.
    """
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base-start if address_base is not None else 0

    for offset in range( start, end, minor_len*major_len ):
        yield ansi.format_hexdump_line( source, offset, end, major_len, minor_len, colour, address_base_offset=address_base_offset, show_offsets=show_offsets, show_glyphs=show_glyphs )
    return


def hexdump( source, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, address_base=None, show_offsets=True, show_glyphs=True ):
    """Print a byte string in tabular hexadecimal/ASCII format.
    
    source
        Source byte string to print

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

    show_offsets
        Display offsets at the start of each line (default: true)

    show_glyphs
        Display glyph map at the end of each line (default: true)

    Raises ValueError if both end and length are defined.
    """
    for line in hexdump_iter( source, start, end, length, major_len, minor_len, colour, address_base, show_offsets, show_glyphs ):
        print( line )


def hexdump_diff_iter( source1, source2, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, before=2, after=2, address_base=None ):
    """Return an iterator that renders the differences between two byte strings and renders the result in tabular hexadecimal/ASCII format.

    source1
        First byte string source

    source2
        Second byte string source

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
    """Print the differences between two byte strings in tabular hexadecimal/ASCII format.

    source1
        First byte string source

    source2
        Second byte string source

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
    """Print histogram graph for a byte string.

    source
        Source byte string to render

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    width
        Width of graph to render in pixels (default: 64)

    height
        Height of graph to render in pixels (default: auto)
    """
    start, end = bounds( start, end, length, len( source ) )

    stat = statistics.Stats( source[start:end] )
    stat.print( width=width, height=height )


def pixdump_iter( source, start=None, end=None, length=None, width=64, height=None, palette=None ):
    """Return an iterator which renders the contents of a byte string as a 256 colour image.

    source
        Source byte string to render

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
            return colour.Transparent()
        return palette[source[index]]

    return ansi.format_image_iter( data_fetch, width=width, height=height )


def pixdump( source, start=None, end=None, length=None, width=64, height=None, palette=None ):
    """Print the contents of a byte string as a 256 colour image.

    source
        Source byte string to print

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
