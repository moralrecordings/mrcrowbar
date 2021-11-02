"""General utility functions useful for reverse engineering."""
from __future__ import annotations

import json
import logging
import math
import re
import time
from typing import (
    Any,
    Sequence,
    Union,
    Iterator,
    List,
    Optional,
    Tuple,
    Dict,
    Match,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from mrcrowbar.blocks import Block
from typing_extensions import Literal

logger = logging.getLogger( __name__ )

from mrcrowbar import ansi, encoding as enco, statistics
from mrcrowbar.colour import ColourType, TEST_PALETTE, Transparent
from mrcrowbar.common import BytesReadType, is_bytes, bounds


def enable_logging( level: str = "WARNING" ) -> None:
    """Enable sending logs to stderr. Useful for shell sessions.

    level
        Logging threshold, as defined in the logging module of the Python
        standard library. Defaults to 'WARNING'.
    """
    log = logging.getLogger( "mrcrowbar" )
    log.setLevel( level )
    out = logging.StreamHandler()
    out.setLevel( level )
    form = logging.Formatter( "[%(levelname)s] %(name)s - %(message)s" )
    out.setFormatter( form )
    log.addHandler( out )


DIFF_COLOUR_MAP = (9, 10)


def grep_iter(
    pattern: str,
    source: BytesReadType,
    encoding: str = "utf8",
    fixed_string: bool = False,
    hex_format: bool = False,
    ignore_case: bool = False,
) -> Iterator[Match[bytes]]:
    """Return an iterator that finds the contents of a byte string that matches a regular expression pattern.

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
    regex = re.compile(
        enco.regex_pattern_to_bytes(
            pattern, encoding=encoding, fixed_string=fixed_string, hex_format=hex_format
        ),
        flags,
    )

    return regex.finditer( source )  # type: ignore


def grep(
    pattern: str,
    source: BytesReadType,
    encoding: str = "utf8",
    fixed_string: bool = False,
    hex_format: bool = False,
    ignore_case: bool = False,
) -> List[Match[bytes]]:
    """Find the contents of a byte string that matches a regular expression pattern.

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
    return list(
        grep_iter( pattern, source, encoding, fixed_string, hex_format, ignore_case )
    )


def find_iter(
    substring: Union[str, BytesReadType, Sequence[BytesReadType], Sequence[str]],
    source: Union[str, BytesReadType],
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    overlap: bool = False,
    ignore_case: bool = False,
    encodings: Union[List[str], Literal["all"]] = ["utf_8"],
    brute: bool = False,
    char_size: int = 1,
) -> Iterator[Any]:
    """Return an iterator that finds every location of a substring in a source byte string, checking against multiple encodings.

    substring
        Substring(s) to match, as a single Python string/byte string or a list

    source
        Source Python string or byte string to search

    start
        Start offset to read from (default: start)

    end
        End offset to stop reading at (default: end)

    length
        Length to read in (optional replacement for end)

    overlap
        Return overlapping matches (default: false)

    ignore_case
        Perform a case-insensitive search (default: false)

    encodings
        A list of encodings to try, or 'all' for every supported encoding (default: ['utf_8'])

    brute
        Brute-force an encoding based on recurring letter patterns (default: false)

    char_size
        Size in bytes for each character for brute-forcing (default: 1)
    """
    start, end = bounds( start, end, length, len( source ) )

    substrings = (
        [substring]
        if isinstance( substring, str ) or is_bytes( substring )
        else substring
    )
    substrings = [bytes( x ) if is_bytes( x ) else x for x in substrings]

    if ignore_case:
        source = (
            source.lower() if isinstance( source, str ) else bytes( source ).lower()
        )
        substrings = [s.lower() for s in substrings]

    if not brute:
        for substring in substrings:
            subs = {}
            if isinstance( source, str ) and isinstance( substring, str ):
                subs[substring] = "str"
            elif is_bytes( source ) and is_bytes( substring ):
                subs[substring] = "bytes"
            elif not is_bytes( source ):
                raise TypeError(
                    "Source should be of type bytes, or both source and substring should be of type str!"
                )
            else:
                if encodings == "all" or encodings == ["all"]:
                    encodings = enco.CODECS
                elif isinstance( encodings, str ):
                    encodings = [encodings]
                for encoding in encodings:
                    # strip out the automatic byte-order mark
                    encoding_test = (
                        encoding.lower()
                        .replace( " ", "" )
                        .replace( "-", "" )
                        .replace( "_", "" )
                    )
                    if encoding_test == "utf16":
                        encoding = "utf-16-le"
                    elif encoding_test == "utf32":
                        encoding = "utf-32-le"

                    if isinstance( substring, str ):
                        try:
                            test = substring.encode( encoding )
                            if test not in subs:
                                subs[test] = []
                            subs[test].append( encoding )
                        except UnicodeEncodeError:
                            continue

            for test in subs:
                pointer = start
                result = source.find( test, pointer, end )
                while result != -1:
                    yield (result, result + len( test ), substring, subs[test])
                    if overlap:
                        pointer = result + 1
                    else:
                        pointer = result + len( test )
                    result = source.find( test, pointer, end )
    else:
        matches = []

        # create a mapping of substring letters to substrings
        letter_map = {}
        if len( substrings ) > 1:
            for index, sub in enumerate( substrings ):
                for letter in sub:
                    if letter not in letter_map:
                        letter_map[letter] = set()
                    letter_map[letter].add( index )

        for substring in substrings:
            if not isinstance( substring, str ):
                continue
            submatches = []
            unk_dict, pattern = enco.regex_unknown_encoding_match(
                substring, char_size=char_size
            )
            if overlap:
                pattern = b"(?=(" + pattern + b"))"
            regex = re.compile( pattern, flags=re.DOTALL )
            for match in regex.finditer( source[start:end] ):
                groups = match.groups()
                span_0, span_1 = match.span()
                if overlap:
                    span_1 += len( groups[0] )
                    groups = groups[1:]
                submatches.append(
                    (
                        span_0 + start,
                        span_1 + start,
                        substring,
                        {
                            key: groups[unk_dict[key]]
                            for key in sorted( unk_dict.keys() )
                        },
                    )
                )
            matches.append( submatches )

        # repeat until all eliminations are made
        changed = True
        while changed:
            changed = False
            # filter out matches that don't have a letter occuring in all substrings
            for letter, subs in letter_map.items():
                subs = list( subs )
                if len( subs ) == 1:
                    continue
                # find the letter mappings that appear in all substrings
                mappings = set( m[3][letter] for m in matches[subs[0]] )
                for sub_id in subs[1:]:
                    mappings.intersection_update(
                        set( m[3][letter] for m in matches[sub_id] )
                    )

                # remove the letter mappings which are unique
                for sub_id in subs:
                    new_matches = [
                        m for m in matches[sub_id] if m[3][letter] in mappings
                    ]
                    if len( new_matches ) != len( matches[sub_id] ):
                        changed = True
                    matches[sub_id] = new_matches

        for submatches in matches:
            yield from submatches


def find(
    substring: Union[str, BytesReadType, Sequence[str], Sequence[BytesReadType]],
    source: Union[str, BytesReadType],
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    overlap: bool = False,
    ignore_case: bool = False,
    encodings: Union[str, List[str]] = ["utf_8"],
    brute: bool = False,
    char_size: int = 1,
):
    """Find every location of a substring in a source byte string, checking against multiple encodings.

    substring
        Substring to match, as a single Python string/byte string or a list

    source
        Source Python string or byte string to search

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

    brute
        Brute-force an encoding based on recurring letter patterns (default: false)

    char_size
        Size in bytes for each character for brute-forcing (default: 1)
    """
    return [
        x
        for x in find_iter(
            substring,
            source,
            start,
            end,
            length,
            overlap,
            ignore_case,
            encodings,
            brute,
            char_size,
        )
    ]


def grepdump_iter(
    pattern: str,
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    encoding: str = "utf8",
    fixed_string: bool = False,
    hex_format: bool = False,
    ignore_case: bool = False,
    major_len: int = 8,
    minor_len: int = 4,
    colour: bool = True,
    address_base: Optional[int] = None,
    before: int = 2,
    after: int = 2,
    title: Optional[str] = None,
    format: Literal["hex", "text", "json"] = "hex",
) -> Iterator[str]:
    """Return an iterator that finds the contents of a byte string that matches a regular expression pattern and renders the result.

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

    format
        Output format; one of 'hex', 'text' or 'json' (default: 'hex')

    Raises ValueError if both end and length are defined.
    """
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base - start if address_base is not None else 0
    assert format in ("hex", "text", "json")

    regex_iter = grep_iter(
        pattern, source[start:end], encoding, fixed_string, hex_format, ignore_case
    )

    if format == "hex":
        hb = ansi.HexdumpHighlightBuffer(
            source,
            start,
            end,
            None,
            major_len,
            minor_len,
            colour,
            address_base,
            before,
            after,
            title,
        )
        for match in regex_iter:
            hb.add_span( (match.span()[0] + start, match.span()[1] + start) )

            yield from hb.flush()

        yield from hb.flush( final=True )

    elif format == "text":
        for match in regex_iter:
            start_off = match.span()[0] + start + address_base_offset
            end_off = match.span()[1] + start + address_base_offset
            digits = (
                "{:0"
                + str(
                    max(
                        8,
                        math.floor(
                            math.log( end + address_base_offset ) / math.log( 16 )
                        ),
                    )
                )
                + "x}"
            )
            line = (digits + ":" + digits).format( start_off, end_off )
            line += ":{repr( match.group( 0 ) )}"
            if title:
                line = "{title}:" + line
            yield line

    elif format == "json":
        for match in regex_iter:
            yield json.dumps(
                {
                    "title": title,
                    "start_offset": match.span()[0] + start + address_base_offset,
                    "end_offset": match.span()[1] + start + address_base_offset,
                    "match": match.group( 0 ).hex(),
                }
            )


def grepdump(
    pattern: str,
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    encoding: str = "utf8",
    fixed_string: bool = False,
    hex_format: bool = False,
    ignore_case: bool = False,
    major_len: int = 8,
    minor_len: int = 4,
    colour: bool = True,
    address_base: Optional[int] = None,
    before: int = 2,
    after: int = 2,
    title: Optional[str] = None,
    format: Literal["hex", "text", "json"] = "hex",
):
    """Find the contents of a byte string that matches a regular expression pattern and renders the result.

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

    format
        Output format; one of 'hex', 'text' or 'json' (default: 'hex')

    Raises ValueError if both end and length are defined.
    """

    for line in grepdump_iter(
        pattern,
        source,
        start,
        end,
        length,
        encoding,
        fixed_string,
        hex_format,
        ignore_case,
        major_len,
        minor_len,
        colour,
        address_base,
        before,
        after,
        title,
        format,
    ):
        print( line )


def search_iter(
    pattern: str,
    source: "Block",
    prefix: str = "source",
    depth: Optional[int] = None,
    encoding: str = "utf8",
    fixed_string: bool = False,
    hex_format: bool = False,
    ignore_case: bool = False,
) -> Iterator[str]:
    """Return an iterator that finds the Fields inside a Block that match a regular expression pattern.

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

    depth = depth - 1 if depth is not None else None

    match_list = [
        x.span()
        for x in grep(
            pattern,
            source.export_data(),
            encoding,
            fixed_string,
            hex_format,
            ignore_case,
        )
    ]

    fields = source.get_field_names()

    def check_field(
        offset: int, size: int, data: Union[Block, Chunk], pref: str
    ) -> Iterator[str]:
        for match in match_list:
            if offset <= match[0] < offset + size or offset <= match[1] < offset + size:
                if isinstance( data, Block ):
                    success = False
                    for x in search_iter(
                        pattern,
                        data,
                        pref,
                        depth,
                        encoding,
                        fixed_string,
                        hex_format,
                        ignore_case,
                    ):
                        success = True
                        yield x
                    if not success:
                        # no exact match, yield entire object
                        yield pref
                elif isinstance( data, Chunk ):
                    success = False
                    for x in search_iter(
                        pattern,
                        data.obj,
                        f"{pref}.obj",
                        depth,
                        encoding,
                        fixed_string,
                        hex_format,
                        ignore_case,
                    ):
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
                yield from check_field(
                    el_offset, el_size, el, f"{prefix}.{name}[{i}]"
                )
                el_offset += el_size
        else:
            yield from check_field( offset, size, data, f"{prefix}.{name}" )


def search(
    pattern: str,
    source: "Block",
    prefix: str = "source",
    depth: Optional[int] = None,
    encoding: str = "utf8",
    fixed_string: bool = False,
    hex_format: bool = False,
    ignore_case: bool = False,
) -> List[str]:
    """Find the Fields inside a Block that match a regular expression pattern.

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
    return list(
        search_iter(
            pattern,
            source,
            prefix,
            depth,
            encoding,
            fixed_string,
            hex_format,
            ignore_case,
        )
    )


def finddump_iter(
    substring,
    source,
    start=None,
    end=None,
    length=None,
    overlap=False,
    ignore_case=False,
    encodings=["utf_8"],
    brute=False,
    char_size=1,
    major_len=8,
    minor_len=4,
    colour=True,
    address_base=None,
    before=2,
    after=2,
    title=None,
    format="hex",
):
    """Return an iterator that finds every location of a substring in a source byte string, checking against multiple encodings, and renders the result.

    substring
        Substring(s) to match, as a single Python string/byte string or a list

    source
        Source byte string or Python string to search.

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

    brute
        Brute-force an encoding based on recurring letter patterns (default: false)

    char_size
        Size in bytes for each character for brute-forcing (default: 1)

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

    format
        Output format; one of 'hex', 'text' or 'json' (default: 'hex')

    """
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    if len( source ) == 0 or (start == end == 0):
        return
    address_base_offset = address_base - start if address_base is not None else 0
    stride = minor_len * major_len
    assert format in ("hex", "text", "json")

    findings = find_iter(
        substring,
        source,
        start,
        end,
        None,
        overlap,
        ignore_case,
        encodings,
        brute,
        char_size,
    )

    if format == "hex":
        for match in findings:
            if isinstance( match[3], dict ):
                header = (
                    repr( match[2] )
                    + " - "
                    + repr( {k: v.hex() for k, v in match[3].items()} )
                )
            else:
                header = repr( match[2] ) + " - " + repr( match[3] )
            if title:
                header = title + " - " + header
            print( header )
            hb = ansi.HexdumpHighlightBuffer(
                source,
                start,
                end,
                None,
                major_len,
                minor_len,
                colour,
                address_base,
                before,
                after,
            )
            hb.add_span( (match[0], match[1]) )

            yield from hb.flush( final=True )

    elif format == "text":
        for match in findings:
            start_off = match[0] + address_base_offset
            end_off = match[1] + address_base_offset
            digits = (
                "{:0"
                + str(
                    max(
                        8,
                        math.floor(
                            math.log( end + address_base_offset ) / math.log( 16 )
                        ),
                    )
                )
                + "x}"
            )
            line = (digits + ":" + digits).format( start_off, end_off )
            line += f":{repr( source[match[0]:match[1]] )}"
            if isinstance( match[3], list ):
                line += f":{repr( match[3] )}"
            elif isinstance( match[3], dict ):
                hexmap = {k: v.hex() for k, v in match[3].items()}
                line += f":{repr( hexmap )}"
            if title:
                line = f"{title}:" + line
            yield line

    elif format == "json":
        for match in findings:
            result = {
                "title": title,
                "start_offset": match[0] + address_base_offset,
                "end_offset": match[1] + address_base_offset,
                "match": source[match[0] : match[1]].hex(),
            }
            if isinstance( match[3], list ):
                result["encodings"] = match[3]
            elif isinstance( match[3], dict ):
                result["alphabet"] = {k: v.hex() for k, v in match[3].items()}
            yield json.dumps( result )


def finddump(
    substring,
    source,
    start=None,
    end=None,
    length=None,
    overlap=False,
    ignore_case=False,
    encodings=["utf_8"],
    brute=False,
    char_size=1,
    major_len=8,
    minor_len=4,
    colour=True,
    address_base=None,
    before=2,
    after=2,
    title=None,
    format="hex",
):
    """Return an iterator that finds every location of a substring in a source byte string, checking against multiple encodings, and renders the result.

    substring
        Substring(s) to match, as a single Python string/byte string or a list

    source
        Source byte string or Python string to search.

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

    brute
        Brute-force an encoding based on recurring letter patterns (default: false)

    char_size
        Size in bytes for each character for brute-forcing (default: 1)

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

    format
        Output format; one of 'hex', 'text' or 'json' (default: 'hex')
    """
    for x in finddump_iter(
        substring,
        source,
        start,
        end,
        length,
        overlap,
        ignore_case,
        encodings,
        brute,
        char_size,
        major_len,
        minor_len,
        colour,
        address_base,
        before,
        after,
        title,
        format,
    ):
        print( x )


def diff_iter(
    source1: BytesReadType,
    source2: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> Iterator[Tuple[int, int]]:
    """Perform a diff between two equal-sized binary strings and
    return an iterator of (offset, size) tuples denoting the differences.

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
    while pointer < end_point:
        if source1[pointer] != source2[pointer]:
            if diff_start is None:
                diff_start = pointer
        else:
            if diff_start is not None:
                yield (diff_start, pointer - diff_start)
                diff_start = None
        pointer += 1
    if diff_start is not None:
        yield (diff_start, pointer - diff_start)
        diff_start = None


def diff(
    source1: BytesReadType,
    source2: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> List[Tuple[int, int]]:
    """Perform a diff between two equal-sized binary strings and
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
    return list( diff_iter( source1, source2, start, end ) )


def objdiff_iter(
    source1: Any, source2: Any, prefix: str = "source", depth: Optional[int] = None
) -> Iterator[Tuple[str, Any, Any]]:
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
    depth = depth - 1 if depth is not None else None

    def abbr( src: Any ):
        return (
            src
            if type( src ) in (int, float, str, bytes, bytearray)
            else (src.__class__.__module__, src.__class__.__name__)
        )

    if (type( source1 ) != type( source2 )) and not (
        is_bytes( source1 ) and is_bytes( source2 )
    ):
        yield (prefix, abbr( source1 ), abbr( source2 ))
    else:
        if type( source1 ) == list:
            for i in range( max( len( source1 ), len( source2 ) ) ):
                prefix_mod = f"{prefix}[{i}]"

                if i < len( source1 ) and i < len( source2 ):
                    yield from objdiff_iter(
                        source1[i], source2[i], prefix=prefix_mod, depth=depth
                    )
                elif i >= len( source2 ):
                    yield (prefix_mod, abbr( source1[i] ), None)
                else:
                    yield (prefix_mod, None, abbr( source2[i] ))
        elif is_bytes( source1 ):
            if source1 != source2:
                yield (prefix, source1, source2)
        elif type( source1 ) in (int, float, str):
            if source1 != source2:
                yield (prefix, source1, source2)
        elif hasattr( source1, "serialised" ):  # Block
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
                        yield from objdiff_iter(
                            getattr( source1, s1[1][i][0] ),
                            getattr( source2, s1[1][i][0] ),
                            prefix=f"{prefix}.{s1[1][i][0]}",
                            depth=depth,
                        )
        else:
            if source1 != source2:
                yield (prefix, source1, source2)


def objdiff(
    source1: Any, source2: Any, prefix: str = "source", depth: Optional[int] = None
) -> List[Tuple[str, Any, Any]]:
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
    return list( objdiff_iter( source1, source2, prefix, depth ) )


def objdiffdump_iter(
    source1: Any, source2: Any, prefix: str = "source", depth: Optional[int] = None
):
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
    for p, s1, s2 in objdiff_iter( source1, source2, prefix, depth ):
        if is_bytes( s1 ) and is_bytes( s2 ):
            yield f"* {p}:"
            yield from diffdump_iter( s1, s2 )
            same = False
            continue
        if s1 is not None:
            yield ansi.format_string( f"- {p}: {s1}", foreground=DIFF_COLOUR_MAP[0] )
            same = False
        if s2 is not None:
            yield ansi.format_string( f"+ {p}: {s2}", foreground=DIFF_COLOUR_MAP[1] )
            same = False
    return same


def objdiffdump(
    source1: Any, source2: Any, prefix: str = "source", depth: Optional[int] = None
):
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
    for line in objdiffdump_iter( source1, source2, prefix, depth ):
        print( line )


def histdump_iter(
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    samples: int = 0x10000,
    width: int = 64,
    address_base: Optional[int] = None,
) -> Iterator[str]:
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
    address_base_offset = address_base - start if address_base is not None else 0

    for offset in range( start, end, samples ):
        yield ansi.format_histdump_line(
            source,
            offset,
            length=samples,
            end=end,
            width=width,
            address_base_offset=address_base_offset,
        )
    return


def histdump(
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    samples: int = 0x10000,
    width: int = 64,
    address_base: Optional[int] = None,
):
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
    for line in histdump_iter(
        source, start, end, length, samples, width, address_base
    ):
        print( line )


def hexdump_iter(
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    major_len: int = 8,
    minor_len: int = 4,
    colour: bool = True,
    address_base: Optional[int] = None,
    show_offsets: bool = True,
    show_glyphs: bool = True,
):
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
    address_base_offset = address_base - start if address_base is not None else 0

    for offset in range( start, end, minor_len * major_len ):
        yield ansi.format_hexdump_line(
            source,
            offset,
            end,
            major_len,
            minor_len,
            colour,
            address_base_offset=address_base_offset,
            show_offsets=show_offsets,
            show_glyphs=show_glyphs,
        )
    return


def hexdump(
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    major_len: int = 8,
    minor_len: int = 4,
    colour: bool = True,
    address_base: Optional[int] = None,
    show_offsets: bool = True,
    show_glyphs: bool = True,
):
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
    for line in hexdump_iter(
        source,
        start,
        end,
        length,
        major_len,
        minor_len,
        colour,
        address_base,
        show_offsets,
        show_glyphs,
    ):
        print( line )


def diffdump_iter(
    source1: BytesReadType,
    source2: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    major_len: int = 8,
    minor_len: int = 4,
    colour: bool = True,
    before: int = 2,
    after: int = 2,
    address_base: Optional[int] = None,
) -> Iterator[str]:
    """Return an iterator that renders the differences between two byte strings.

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
    stride = minor_len * major_len
    start = start if start is not None else 0
    end = end if end is not None else max( len( source1 ), len( source2 ) )

    start = max( start, 0 )
    end = min( end, max( len( source1 ), len( source2 ) ) )
    address_base_offset = address_base - start if address_base is not None else 0

    diff_lines: List[int] = []
    for offset in range( start, end, stride ):
        if source1[offset : offset + stride] != source2[offset : offset + stride]:
            diff_lines.append( offset )
    show_all = before is None or after is None
    if show_all:
        show_lines = {
            x: (2 if x in diff_lines else 1) for x in range( start, end, stride )
        }
    else:
        show_lines = {
            x: (2 if x in diff_lines else 0) for x in range( start, end, stride )
        }
        for index in diff_lines:
            for b in [index - (x + 1) * stride for x in range( before )]:
                if b in show_lines and show_lines[b] == 0:
                    show_lines[b] = 1
            for a in [index + (x + 1) * stride for x in range( after )]:
                if a in show_lines and show_lines[a] == 0:
                    show_lines[a] = 1

    skip = False
    for offset in sorted( show_lines.keys() ):
        if skip == True and show_lines[offset] != 0:
            yield "..."
            skip = False
        if show_lines[offset] == 2:
            highlights: Dict[int, ColourType] = {}
            for (o, l) in diff_iter(
                source1, source2, start=offset, end=offset + stride
            ):
                for i in range( o, o + l ):
                    highlights[i] = DIFF_COLOUR_MAP[0]
            if offset < len( source1 ):
                yield ansi.format_hexdump_line(
                    source1,
                    offset,
                    min( end, len( source1 ) ),
                    major_len,
                    minor_len,
                    colour,
                    prefix="-",
                    highlight_addr=DIFF_COLOUR_MAP[0],
                    highlight_map=highlights,
                    address_base_offset=address_base_offset,
                )
            highlights = {k: DIFF_COLOUR_MAP[1] for k in highlights.keys()}
            if offset < len( source2 ):
                yield ansi.format_hexdump_line(
                    source2,
                    offset,
                    min( end, len( source2 ) ),
                    major_len,
                    minor_len,
                    colour,
                    prefix="+",
                    highlight_addr=DIFF_COLOUR_MAP[1],
                    highlight_map=highlights,
                    address_base_offset=address_base_offset,
                )
        elif show_lines[offset] == 1:
            yield ansi.format_hexdump_line(
                source1,
                offset,
                end,
                major_len,
                minor_len,
                colour,
                prefix=" ",
                address_base_offset=address_base_offset,
            )
        elif show_lines[offset] == 0:
            skip = True

    if skip == True:
        yield "..."
        skip = False

    return


def diffdump(
    source1: BytesReadType,
    source2: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    major_len: int = 8,
    minor_len: int = 4,
    colour: bool = True,
    before: int = 2,
    after: int = 2,
    address_base: Optional[int] = None,
):
    """Print the differences between two byte strings.

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
    for line in diffdump_iter(
        source1,
        source2,
        start,
        end,
        length,
        major_len,
        minor_len,
        colour,
        before,
        after,
        address_base,
    ):
        print( line )


def stats(
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    width: int = 64,
    height: int = 12,
):
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


def pixdump_iter(
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    width: int = 64,
    height: Optional[int] = None,
    palette: Optional[Sequence[ColourType]] = None,
) -> Iterator[str]:
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

    pal: Sequence[ColourType] = TEST_PALETTE if palette is None else palette

    start = 0 if (start is None) else start
    if (end is not None) and (length is not None):
        raise ValueError( "Can't define both an end and a length!" )
    elif length is not None:
        end = start + length
    elif end is not None:
        pass
    else:
        end = len( source )

    start_pos = max( start, 0 )
    end_pos = min( end, len( source ) )
    if len( source ) == 0 or (start_pos == end_pos == 0):
        return iter( () )

    if height is None:
        height = math.ceil( (end - start) / width )

    def data_fetch( x_pos: int, y_pos: int, _: int ) -> ColourType:
        index = y_pos * width + x_pos + start_pos
        if index >= end_pos:
            return Transparent()
        return pal[source[index]]

    return ansi.format_image_iter( data_fetch, width=width, height=height )


def pixdump(
    source: BytesReadType,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    width: int = 64,
    height: Optional[int] = None,
    palette: Optional[Sequence[ColourType]] = None,
):
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


def pixdump_sweep(
    source: BytesReadType,
    range: Sequence[int] = (64,),
    delay: int = 0,
    start: Optional[int] = None,
    end: Optional[int] = None,
    length: Optional[int] = None,
    height: Optional[int] = None,
    palette: Optional[Sequence[ColourType]] = None,
):
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
        time.sleep( delay )


"""
You can generate the below section using the following script:

from mrcrowbar import encoding as enco
str_type = lambda type_class, *type_args: f"({type_class.__name__}, {str(type_args)[1:-1]})"
for type_id, from_func in enco.FROM_RAW_TYPE.items():
    print(f"from_{enco.RAW_TYPE_NAME[type_id]} = enco.FROM_RAW_TYPE[{str_type(*type_id)}]")
for type_id, to_func in enco.TO_RAW_TYPE.items():
    print(f"to_{enco.RAW_TYPE_NAME[type_id]} = enco.TO_RAW_TYPE[{str_type(*type_id)}]")
for type_id, from_func in enco.FROM_RAW_TYPE_ARRAY.items():
    print(f"from_{enco.RAW_TYPE_NAME[type_id]}_array = enco.FROM_RAW_TYPE_ARRAY[{str_type(*type_id)}]")
for type_id, to_func in enco.TO_RAW_TYPE_ARRAY.items():
    print(f"to_{enco.RAW_TYPE_NAME[type_id]}_array = enco.TO_RAW_TYPE_ARRAY[{str_type(*type_id)}]")

"""

from_uint8 = enco.FROM_RAW_TYPE[(int, 1, "unsigned", None)]
from_uint8 = enco.FROM_RAW_TYPE[(int, 1, "unsigned", "little")]
from_uint8 = enco.FROM_RAW_TYPE[(int, 1, "unsigned", "big")]
from_int8 = enco.FROM_RAW_TYPE[(int, 1, "signed", None)]
from_int8 = enco.FROM_RAW_TYPE[(int, 1, "signed", "little")]
from_int8 = enco.FROM_RAW_TYPE[(int, 1, "signed", "big")]
from_uint16_le = enco.FROM_RAW_TYPE[(int, 2, "unsigned", "little")]
from_uint16_be = enco.FROM_RAW_TYPE[(int, 2, "unsigned", "big")]
from_int16_le = enco.FROM_RAW_TYPE[(int, 2, "signed", "little")]
from_int16_be = enco.FROM_RAW_TYPE[(int, 2, "signed", "big")]
from_uint32_le = enco.FROM_RAW_TYPE[(int, 4, "unsigned", "little")]
from_uint32_be = enco.FROM_RAW_TYPE[(int, 4, "unsigned", "big")]
from_int32_le = enco.FROM_RAW_TYPE[(int, 4, "signed", "little")]
from_int32_be = enco.FROM_RAW_TYPE[(int, 4, "signed", "big")]
from_uint64_le = enco.FROM_RAW_TYPE[(int, 8, "unsigned", "little")]
from_uint64_be = enco.FROM_RAW_TYPE[(int, 8, "unsigned", "big")]
from_int64_le = enco.FROM_RAW_TYPE[(int, 8, "signed", "little")]
from_int64_be = enco.FROM_RAW_TYPE[(int, 8, "signed", "big")]
from_float32_le = enco.FROM_RAW_TYPE[(float, 4, "signed", "little")]
from_float32_be = enco.FROM_RAW_TYPE[(float, 4, "signed", "big")]
from_float64_le = enco.FROM_RAW_TYPE[(float, 8, "signed", "little")]
from_float64_be = enco.FROM_RAW_TYPE[(float, 8, "signed", "big")]
from_int24_le = enco.FROM_RAW_TYPE[(int, 3, "signed", "little")]
from_uint24_le = enco.FROM_RAW_TYPE[(int, 3, "unsigned", "little")]
from_int24_be = enco.FROM_RAW_TYPE[(int, 3, "signed", "big")]
from_uint24_be = enco.FROM_RAW_TYPE[(int, 3, "unsigned", "big")]
to_uint8 = enco.TO_RAW_TYPE[(int, 1, "unsigned", None)]
to_uint8 = enco.TO_RAW_TYPE[(int, 1, "unsigned", "little")]
to_uint8 = enco.TO_RAW_TYPE[(int, 1, "unsigned", "big")]
to_int8 = enco.TO_RAW_TYPE[(int, 1, "signed", None)]
to_int8 = enco.TO_RAW_TYPE[(int, 1, "signed", "little")]
to_int8 = enco.TO_RAW_TYPE[(int, 1, "signed", "big")]
to_uint16_le = enco.TO_RAW_TYPE[(int, 2, "unsigned", "little")]
to_uint16_be = enco.TO_RAW_TYPE[(int, 2, "unsigned", "big")]
to_int16_le = enco.TO_RAW_TYPE[(int, 2, "signed", "little")]
to_int16_be = enco.TO_RAW_TYPE[(int, 2, "signed", "big")]
to_uint32_le = enco.TO_RAW_TYPE[(int, 4, "unsigned", "little")]
to_uint32_be = enco.TO_RAW_TYPE[(int, 4, "unsigned", "big")]
to_int32_le = enco.TO_RAW_TYPE[(int, 4, "signed", "little")]
to_int32_be = enco.TO_RAW_TYPE[(int, 4, "signed", "big")]
to_uint64_le = enco.TO_RAW_TYPE[(int, 8, "unsigned", "little")]
to_uint64_be = enco.TO_RAW_TYPE[(int, 8, "unsigned", "big")]
to_int64_le = enco.TO_RAW_TYPE[(int, 8, "signed", "little")]
to_int64_be = enco.TO_RAW_TYPE[(int, 8, "signed", "big")]
to_float32_le = enco.TO_RAW_TYPE[(float, 4, "signed", "little")]
to_float32_be = enco.TO_RAW_TYPE[(float, 4, "signed", "big")]
to_float64_le = enco.TO_RAW_TYPE[(float, 8, "signed", "little")]
to_float64_be = enco.TO_RAW_TYPE[(float, 8, "signed", "big")]
to_int24_le = enco.TO_RAW_TYPE[(int, 3, "signed", "little")]
to_uint24_le = enco.TO_RAW_TYPE[(int, 3, "unsigned", "little")]
to_int24_be = enco.TO_RAW_TYPE[(int, 3, "signed", "big")]
to_uint24_be = enco.TO_RAW_TYPE[(int, 3, "unsigned", "big")]
from_uint8_array = enco.FROM_RAW_TYPE_ARRAY[(int, 1, "unsigned", None)]
from_uint8_array = enco.FROM_RAW_TYPE_ARRAY[(int, 1, "unsigned", "little")]
from_uint8_array = enco.FROM_RAW_TYPE_ARRAY[(int, 1, "unsigned", "big")]
from_int8_array = enco.FROM_RAW_TYPE_ARRAY[(int, 1, "signed", None)]
from_int8_array = enco.FROM_RAW_TYPE_ARRAY[(int, 1, "signed", "little")]
from_int8_array = enco.FROM_RAW_TYPE_ARRAY[(int, 1, "signed", "big")]
from_uint16_le_array = enco.FROM_RAW_TYPE_ARRAY[(int, 2, "unsigned", "little")]
from_uint16_be_array = enco.FROM_RAW_TYPE_ARRAY[(int, 2, "unsigned", "big")]
from_int16_le_array = enco.FROM_RAW_TYPE_ARRAY[(int, 2, "signed", "little")]
from_int16_be_array = enco.FROM_RAW_TYPE_ARRAY[(int, 2, "signed", "big")]
from_uint32_le_array = enco.FROM_RAW_TYPE_ARRAY[(int, 4, "unsigned", "little")]
from_uint32_be_array = enco.FROM_RAW_TYPE_ARRAY[(int, 4, "unsigned", "big")]
from_int32_le_array = enco.FROM_RAW_TYPE_ARRAY[(int, 4, "signed", "little")]
from_int32_be_array = enco.FROM_RAW_TYPE_ARRAY[(int, 4, "signed", "big")]
from_uint64_le_array = enco.FROM_RAW_TYPE_ARRAY[(int, 8, "unsigned", "little")]
from_uint64_be_array = enco.FROM_RAW_TYPE_ARRAY[(int, 8, "unsigned", "big")]
from_int64_le_array = enco.FROM_RAW_TYPE_ARRAY[(int, 8, "signed", "little")]
from_int64_be_array = enco.FROM_RAW_TYPE_ARRAY[(int, 8, "signed", "big")]
from_float32_le_array = enco.FROM_RAW_TYPE_ARRAY[(float, 4, "signed", "little")]
from_float32_be_array = enco.FROM_RAW_TYPE_ARRAY[(float, 4, "signed", "big")]
from_float64_le_array = enco.FROM_RAW_TYPE_ARRAY[(float, 8, "signed", "little")]
from_float64_be_array = enco.FROM_RAW_TYPE_ARRAY[(float, 8, "signed", "big")]
from_int24_le_array = enco.FROM_RAW_TYPE_ARRAY[(int, 3, "signed", "little")]
from_uint24_le_array = enco.FROM_RAW_TYPE_ARRAY[(int, 3, "unsigned", "little")]
from_int24_be_array = enco.FROM_RAW_TYPE_ARRAY[(int, 3, "signed", "big")]
from_uint24_be_array = enco.FROM_RAW_TYPE_ARRAY[(int, 3, "unsigned", "big")]
to_uint8_array = enco.TO_RAW_TYPE_ARRAY[(int, 1, "unsigned", None)]
to_uint8_array = enco.TO_RAW_TYPE_ARRAY[(int, 1, "unsigned", "little")]
to_uint8_array = enco.TO_RAW_TYPE_ARRAY[(int, 1, "unsigned", "big")]
to_int8_array = enco.TO_RAW_TYPE_ARRAY[(int, 1, "signed", None)]
to_int8_array = enco.TO_RAW_TYPE_ARRAY[(int, 1, "signed", "little")]
to_int8_array = enco.TO_RAW_TYPE_ARRAY[(int, 1, "signed", "big")]
to_uint16_le_array = enco.TO_RAW_TYPE_ARRAY[(int, 2, "unsigned", "little")]
to_uint16_be_array = enco.TO_RAW_TYPE_ARRAY[(int, 2, "unsigned", "big")]
to_int16_le_array = enco.TO_RAW_TYPE_ARRAY[(int, 2, "signed", "little")]
to_int16_be_array = enco.TO_RAW_TYPE_ARRAY[(int, 2, "signed", "big")]
to_uint32_le_array = enco.TO_RAW_TYPE_ARRAY[(int, 4, "unsigned", "little")]
to_uint32_be_array = enco.TO_RAW_TYPE_ARRAY[(int, 4, "unsigned", "big")]
to_int32_le_array = enco.TO_RAW_TYPE_ARRAY[(int, 4, "signed", "little")]
to_int32_be_array = enco.TO_RAW_TYPE_ARRAY[(int, 4, "signed", "big")]
to_uint64_le_array = enco.TO_RAW_TYPE_ARRAY[(int, 8, "unsigned", "little")]
to_uint64_be_array = enco.TO_RAW_TYPE_ARRAY[(int, 8, "unsigned", "big")]
to_int64_le_array = enco.TO_RAW_TYPE_ARRAY[(int, 8, "signed", "little")]
to_int64_be_array = enco.TO_RAW_TYPE_ARRAY[(int, 8, "signed", "big")]
to_float32_le_array = enco.TO_RAW_TYPE_ARRAY[(float, 4, "signed", "little")]
to_float32_be_array = enco.TO_RAW_TYPE_ARRAY[(float, 4, "signed", "big")]
to_float64_le_array = enco.TO_RAW_TYPE_ARRAY[(float, 8, "signed", "little")]
to_float64_be_array = enco.TO_RAW_TYPE_ARRAY[(float, 8, "signed", "big")]
to_int24_le_array = enco.TO_RAW_TYPE_ARRAY[(int, 3, "signed", "little")]
to_uint24_le_array = enco.TO_RAW_TYPE_ARRAY[(int, 3, "unsigned", "little")]
to_int24_be_array = enco.TO_RAW_TYPE_ARRAY[(int, 3, "signed", "big")]
to_uint24_be_array = enco.TO_RAW_TYPE_ARRAY[(int, 3, "unsigned", "big")]
