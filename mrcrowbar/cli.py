from mrcrowbar import common, utils
from mrcrowbar.version import __version__

import argparse
import os
import sys
import logging
logger = logging.getLogger( __name__ )

auto_int = lambda s: int( s, base=0 )

ARGS_RANGE = {
    ('--start', '-C'): dict(
        metavar='INT',
        dest='start',
        type=auto_int,
        help='Start offset to read from (default: file start)',
    ),
    ('--end', '-D'): dict(
        metavar='INT',
        dest='end',
        type=auto_int,
        help='End offset to stop reading at (default: file end)',
    ),
    ('--address-base', '-R'): dict(
        metavar='INT',
        dest='address_base',
        type=auto_int,
        help='Base address to use for labelling (default: start)',
    ),
    ('--length', '-n'): dict(
        metavar='INT',
        dest='length',
        type=auto_int,
        help='Length to read in (optional replacement for --end)'
    ),
}
ARGS_COMMON = {
    ('--major-len', '-J'): dict(
        metavar='INT',
        dest='major_len',
        type=auto_int,
        default=8,
        help='Number of hexadecimal groups per line (default: 8)',
    ),
    ('--minor-len', '-N'): dict(
        metavar='INT',
        dest='minor_len',
        type=auto_int,
        default=4,
        help='Number of bytes per hexadecimal group (default: 4)',
    ),
    ('--plain', '-p'): dict(
        dest='colour',
        action='store_false',
        help='Disable ANSI colour formatting'
    ),
    ('--version', '-V'): dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}

ARGS_DUMP = {
    'source': dict(
        metavar='FILE',
        nargs='+',
        help='File to inspect',
    ),
    ('--recursive', '-r'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    ('--no-offsets', '-O'): dict(
        dest='show_offsets',
        action='store_false',
        help='Don\'t render line offsets'
    ),
    ('--no-glyphs', '-G'): dict(
        dest='show_glyphs',
        action='store_false',
        help='Don\'t render the glyph map'
    ),
}
ARGS_DUMP.update( ARGS_RANGE )
ARGS_DUMP.update( ARGS_COMMON )

ARGS_DIFF = {
    'source1': dict(
        metavar='FILE1',
        help='File to inspect',
    ),
    'source2': dict(
        metavar='FILE2',
        help='File to compare against',
    ),
    ('--before', '-B'): dict(
        metavar='INT',
        dest='before',
        type=auto_int,
        default=2,
        help='Number of lines preceeding a match to show (default: 2)'
    ),
    ('--after', '-A'): dict(
        metavar='INT',
        dest='after',
        type=auto_int,
        default=2,
        help='Number of lines following a match to show (default: 2)'
    ),
    ('--all', '-a'): dict(
        dest='show_all',
        action='store_true',
        help='Show all lines'
    ),
}
ARGS_DIFF.update( ARGS_RANGE )
ARGS_DIFF.update( ARGS_COMMON )

ARGS_HIST = {
   'source': dict(
        metavar='FILE',
        nargs='+',
        help='File to inspect',
    ),
    ('--samples', '-s'): dict(
        metavar='INT',
        dest='samples',
        type=auto_int,
        default=0x10000,
        help='Number of samples per histogram slice (default: 65536)'
    ),
    ('--summary', '-m'): dict(
        action='store_true',
        help='Show a single histogram for the full range instead of slices',
    ),
    ('--width', '-W'): dict(
        metavar='INT',
        dest='width',
        type=auto_int,
        default=64,
        help='Histogram width (default: 64)'
    ),
    ('--height', '-H'): dict(
        metavar='INT',
        dest='height',
        type=auto_int,
        default=12,
        help='Histogram height (default: 12)'
    ),
    ('--recursive', '-r'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    ('--version', '-V'): dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}
ARGS_HIST.update( ARGS_RANGE )

ARGS_PIX = {
   'source': dict(
        metavar='FILE',
        nargs='+',
        help='File to inspect',
    ),
    ('--recursive', '-r'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    ('--width', '-W'): dict(
        metavar='INT',
        dest='width',
        type=auto_int,
        default=64,
        help='Image width (default: 64)'
    ),
    ('--version', '-V'): dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}
ARGS_PIX.update( ARGS_RANGE )

ARGS_GREP = {
    'pattern': dict(
        metavar='PATTERN',
        help='Pattern to match',
    ),
    'source': dict(
        metavar='FILE',
        nargs='+',
        help='File to inspect',
    ),
    ('--recursive', '-r'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    ('--fixed-string', '-F'): dict(
        dest='fixed_string',
        action='store_true',
        help='Interpret PATTERN as fixed string (disable regular expressions)'
    ),
    ('--hex-format', '-H'): dict(
        dest='hex_format',
        action='store_true',
        help='Interpret strings in PATTERN as hexadecimal'
    ),
    ('--ignore-case', '-i'): dict(
        dest='ignore_case',
        action='store_true',
        help='Perform a case-insensitive search'
    ),
    ('--encoding', '-e'): dict(
        metavar='ENCODING',
        dest='encoding',
        default='utf8',
        help='Convert strings in PATTERN to a specific Python encoding (default: utf8)'
    ),
    ('--before', '-B'): dict(
        metavar='INT',
        dest='before',
        type=auto_int,
        default=2,
        help='Number of lines preceeding a match to show (default: 2)'
    ),
    ('--after', '-A'): dict(
        metavar='INT',
        dest='after',
        type=auto_int,
        default=2,
        help='Number of lines following a match to show (default: 2)'
    ),
    ('--format', '-f'): dict(
        dest='format',
        default='hex',
        choices=('hex', 'text', 'json'),
        help='Output format (default: hex)'
    ),
}
ARGS_GREP.update( ARGS_RANGE )
ARGS_GREP.update( ARGS_COMMON )

ARGS_FIND = {
    'string': dict(
        metavar='STRING',
        help='String to search for, or multiple strings separated by a comma',
    ),
    'source': dict(
        metavar='FILE',
        nargs='+',
        help='File to inspect',
    ),
    ('--delimiter', '-d'): dict(
        dest='delimiter',
        default=',',
        help="Delimiter used to split the search string (default: ,)",
    ),
    ('--recursive', '-r'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    ('--overlap', '-o'): dict(
        dest='overlap',
        action='store_true',
        help='Return overlapping matches'
    ),
    ('--ignore-case', '-i'): dict(
        dest='ignore_case',
        action='store_true',
        help='Perform a case-insensitive search'
    ),
    ('--encoding', '-e'): dict(
        dest='encoding',
        help='Comma-seperated list of encodings to try, or "all" for every supported encoding (default: utf8)',
        default='utf_8',
    ),
    ('--before', '-B'): dict(
        metavar='INT',
        dest='before',
        type=auto_int,
        default=2,
        help='Number of lines preceeding a match to show (default: 2)'
    ),
    ('--after', '-A'): dict(
        metavar='INT',
        dest='after',
        type=auto_int,
        default=2,
        help='Number of lines following a match to show (default: 2)'
    ),
    ('--brute', '-b'): dict(
        dest='brute',
        action='store_true',
        help='Brute-force an encoding based on recurring letter patterns'
    ),
    ('--char-size', '-c'): dict(
        dest='char_size',
        type=int,
        help='Size in bytes of each character for brute-forcing (default: 1)',
        default=1,
    ),
    ('--format', '-f'): dict(
        dest='format',
        default='hex',
        choices=('hex', 'text', 'json'),
        help='Output format (default: hex)'
    ),
}
ARGS_FIND.update( ARGS_RANGE )
ARGS_FIND.update( ARGS_COMMON )

def get_parser( args, **kwargs ):
    parser = argparse.ArgumentParser( **kwargs )
    for arg, spec in args.items():
        if isinstance( arg, tuple ):
            parser.add_argument( *arg, **spec )
        else:
            parser.add_argument( arg, **spec )
    return parser

EPILOG_GREP = """
For convenience, mrcgrep will interpret the pattern as UTF-8 and convert it to the bytes equivalent
in the encoding you specify.

It is important to note when writing regular expressions, single character matches and counts are done
at the encoded byte level, not at the UTF-8 level! This can lead to unexpected side-effects for rules,
e.g. the pattern "[ů]" will translate to "[\\xc5\\xaf]", which matches either the first or second byte.
If you're unsure, write your expressions using escaped hexadecimal bytes (e.g. "[\\xNN]").
"""

mrcdump_parser = lambda: get_parser( args=ARGS_DUMP, description='Examine the contents of a file as hexadecimal.', )
mrcdiff_parser = lambda: get_parser( args=ARGS_DIFF, description='Compare the contents of two files as hexadecimal.' )
mrchist_parser = lambda: get_parser( args=ARGS_HIST, description='Display the contents of a file as a histogram map.' )
mrcpix_parser = lambda: get_parser( args=ARGS_PIX, description='Display the contents of a file as a 256 colour image.' )
mrcgrep_parser = lambda: get_parser( args=ARGS_GREP, description='Display the contents of a file that matches a regular expression pattern.', epilog=EPILOG_GREP )
mrcfind_parser = lambda: get_parser( args=ARGS_FIND, description='Display the contents of a file that matches a string, checking against multiple encodings.' )


def mrcdump():
    parser = mrcdump_parser()
    raw_args = parser.parse_args()

    source_paths = raw_args.source
    multi = len( raw_args.source ) != 1 or raw_args.recursive
    if raw_args.recursive:
        source_paths = common.file_path_recurse( *source_paths )

    for i, path in enumerate( source_paths ):
        try:
            with open( path, 'rb' ) as src:
                if multi:
                    print( src.name )
                with common.read( src ) as source:
                    utils.hexdump(
                        source, start=raw_args.start, end=raw_args.end, length=raw_args.length,
                        major_len=raw_args.major_len, minor_len=raw_args.minor_len,
                        colour=raw_args.colour, address_base=raw_args.address_base,
                        show_offsets=raw_args.show_offsets, show_glyphs=raw_args.show_glyphs,
                    )
                print()
        except OSError as e:
            logger.warning( '{}'.format( e ) )


def mrcdiff():
    parser = mrcdiff_parser()
    raw_args = parser.parse_args()

    before = raw_args.before if not raw_args.show_all else None
    after = raw_args.after if not raw_args.show_all else None
    sources = []
    if os.path.isdir( raw_args.source1 ) and os.path.isdir( raw_args.source2 ):
        for f in os.listdir( raw_args.source1 ):
            fx = os.path.join( raw_args.source1, f )
            fy = os.path.join( raw_args.source2, f )
            if os.path.isfile( fx ) and os.path.isfile( fy ):
                sources.append((fx, fy))
    else:
        sources.append((raw_args.source1, raw_args.source2))
    multi = len( sources ) != 1

    for source1_fn, source2_fn in sources:
        with common.read( open( source1_fn, 'rb' ) ) as source1, common.read( open( source2_fn, 'rb' ) ) as source2:
            if multi:
                print( '{} => {}'.format( source1_fn, source2_fn ) )
            utils.diffdump(
                source1, source2, start=raw_args.start, end=raw_args.end,
                length=raw_args.length, major_len=raw_args.major_len,
                minor_len=raw_args.minor_len, colour=raw_args.colour,
                before=before, after=after, address_base=raw_args.address_base,
            )

def mrchist():
    parser = mrchist_parser()
    raw_args = parser.parse_args()

    source_paths = raw_args.source
    multi = len( raw_args.source ) != 1 or raw_args.recursive
    if raw_args.recursive:
        source_paths = common.file_path_recurse( *source_paths )

    for i, path in enumerate( source_paths ):
        try:
            with open( path, 'rb' ) as src:
                if multi:
                    print( src.name )
                with common.read( src ) as source:
                    if raw_args.summary:
                        utils.stats( source, start=raw_args.start, end=raw_args.end, length=raw_args.length, width=raw_args.width, height=raw_args.height )
                    else:
                        utils.histdump( source, start=raw_args.start, end=raw_args.end,
                            length=raw_args.length, samples=raw_args.samples, width=raw_args.width,
                            address_base=raw_args.address_base,
                        )
                print()
        except OSError as e:
            logger.warning( '{}'.format( e ) )


def mrcpix():
    parser = mrcpix_parser()
    raw_args = parser.parse_args()

    source_paths = raw_args.source
    multi = len( raw_args.source ) != 1 or raw_args.recursive
    if raw_args.recursive:
        source_paths = common.file_path_recurse( *source_paths )

    for i, path in enumerate( source_paths ):
        try:
            with open( path, 'rb' ) as src:
                if multi:
                    print( src.name )
                with common.read( src ) as source:
                    utils.pixdump( source, start=raw_args.start, end=raw_args.end,
                        length=raw_args.length, width=raw_args.width,
                    )
                print()
        except OSError as e:
            logger.warning( '{}'.format( e ) )


def mrcgrep():
    parser = mrcgrep_parser()
    raw_args = parser.parse_args()

    source_paths = raw_args.source
    multi = len( raw_args.source ) != 1 or raw_args.recursive
    if raw_args.recursive:
        source_paths = common.file_path_recurse( *source_paths )

    for i, path in enumerate( source_paths ):
        try:
            with open( path, 'rb' ) as src:
                title = None
                if multi:
                    title = src.name
                with common.read( src ) as source:
                     utils.grepdump( raw_args.pattern, source,
                           encoding=raw_args.encoding, fixed_string=raw_args.fixed_string,
                           hex_format=raw_args.hex_format,
                           start=raw_args.start, end=raw_args.end,
                           length=raw_args.length,
                           major_len=raw_args.major_len,
                           minor_len=raw_args.minor_len,
                           colour=raw_args.colour,
                           before=raw_args.before, after=raw_args.after,
                           title=title,
                           ignore_case=raw_args.ignore_case,
                           format=raw_args.format
                     )
        except OSError as e:
            logger.warning( '{}'.format( e ) )


def mrcfind():
    parser = mrcfind_parser()
    raw_args = parser.parse_args()

    source_paths = raw_args.source
    multi = len( raw_args.source ) != 1 or raw_args.recursive
    if raw_args.recursive:
        source_paths = common.file_path_recurse( *source_paths )

    for i, path in enumerate( source_paths ):
        try:
            with open( path, 'rb' ) as src:
                title = None
                if multi:
                    title = src.name
                with common.read( src ) as source:
                    utils.finddump(
                        raw_args.string.split(raw_args.delimiter), source,
                        start=raw_args.start,
                        end=raw_args.end,
                        length=raw_args.length,
                        overlap=raw_args.overlap,
                        ignore_case=raw_args.ignore_case,
                        encodings=raw_args.encoding.split(','),
                        brute=raw_args.brute,
                        char_size=raw_args.char_size,
                        major_len=raw_args.major_len,
                        minor_len=raw_args.minor_len,
                        colour=raw_args.colour,
                        before=raw_args.before,
                        after=raw_args.after,
                        title=title,
                        format=raw_args.format,
                    )
        except OSError as e:
            logger.warning( '{}'.format( e ) )

