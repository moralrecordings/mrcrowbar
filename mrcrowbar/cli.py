from mrcrowbar import common, utils
from mrcrowbar.version import __version__

import argparse
import os
import sys
import logging
logger = logging.getLogger( __name__ )

auto_int = lambda s: int( s, base=0 )

ARGS_COMMON = {
    '--start': dict(
        metavar='INT',
        dest='start',
        type=auto_int,
        help='Start offset to read from (default: file start)',
    ),
    '--end': dict(
        metavar='INT',
        dest='end',
        type=auto_int,
        help='End offset to stop reading at (default: end)',
    ),
    '--address-base': dict(
        metavar='INT',
        dest='address_base',
        type=auto_int,
        help='Base address to use for labelling (default: start)',
    ),
    '--length': dict(
        metavar='INT',
        dest='length',
        type=auto_int,
        help='Length to read in (optional replacement for --end)'
    ),
    '--major-len': dict(
        metavar='INT',
        dest='major_len',
        type=auto_int,
        default=8,
        help='Number of hexadecimal groups per line (default: 8)',
    ),
    '--minor-len': dict(
        metavar='INT',
        dest='minor_len',
        type=auto_int,
        default=4,
        help='Number of bytes per hexadecimal group (default: 4)',
    ),
    '--plain': dict(
        dest='colour',
        action='store_false',
        help='Disable ANSI colour formatting'
    ),
    '--version': dict(
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
    ('-r', '--recursive'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    '--no-hexdump': dict(
        dest='no_hexdump',
        action='store_true',
        help='Don\'t render a hex dump'
    ),
    '--no-stats': dict(
        dest='no_stats',
        action='store_true',
        help='Don\'t render statistics'
    ),
    '--no-offsets': dict(
        dest='show_offsets',
        action='store_false',
        help='Don\'t render line offsets'
    ),
    '--no-glyphs': dict(
        dest='show_glyphs',
        action='store_false',
        help='Don\'t render the glyph map'
    ),
    '--hist-w': dict(
        dest='hist_w',
        type=auto_int,
        default=64,
        help='Histogram width (default: 64)'
    ),
    '--hist-h': dict(
        dest='hist_h',
        type=auto_int,
        default=12,
        help='Histogram height (default: 12)'
    ),
}
ARGS_DUMP.update( ARGS_COMMON )

ARGS_DIFF = {
    'source1': dict(
        metavar='FILE1',
        type=argparse.FileType( mode='rb' ),
        help='File to inspect',
    ),
    'source2': dict(
        metavar='FILE2',
        type=argparse.FileType( mode='rb' ),
        help='File to compare against',
    ),
    '--before': dict(
        metavar='INT',
        dest='before',
        type=auto_int,
        default=2,
        help='Number of lines preceeding a match to show (default: 2)'
    ),
    '--after': dict( 
        metavar='INT',
        dest='after',
        type=auto_int,
        default=2,
        help='Number of lines following a match to show (default: 2)'
    ),
    '--all': dict(
        dest='show_all',
        action='store_true',
        help='Show all lines'
    ),
}
ARGS_DIFF.update( ARGS_COMMON )

ARGS_HIST = {
   'source': dict(
        metavar='FILE',
        nargs='+',
        help='File to inspect',
    ),
    '--start': dict(
        metavar='INT',
        dest='start',
        type=auto_int,
        help='Start offset to read from (default: file start)',
    ),
    '--end': dict(
        metavar='INT',
        dest='end',
        type=auto_int,
        help='End offset to stop reading at (default: end)',
    ),
    '--address-base': dict(
        metavar='INT',
        dest='address_base',
        type=auto_int,
        help='Base address to use for labelling (default: start)',
    ),
    '--length': dict(
        metavar='INT',
        dest='length',
        type=auto_int,
        help='Length to read in (optional replacement for --end)'
    ),
    '--samples': dict(
        metavar='INT',
        dest='samples',
        type=auto_int,
        default=0x10000,
        help='Number of samples per histogram slice (default: 65536)'
    ),
    '--width': dict(
        metavar='INT',
        dest='width',
        type=auto_int,
        default=64,
        help='Histogram width (default: 64)'
    ),
    ('-r', '--recursive'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    '--version': dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}

ARGS_PIX = {
   'source': dict(
        metavar='FILE',
        nargs='+',
        help='File to inspect',
    ),
    '--start': dict(
        metavar='INT',
        dest='start',
        type=auto_int,
        help='Start offset to read from (default: file start)',
    ),
    '--end': dict(
        metavar='INT',
        dest='end',
        type=auto_int,
        help='End offset to stop reading at (default: end)',
    ),
    '--length': dict(
        metavar='INT',
        dest='length',
        type=auto_int,
        help='Length to read in (optional replacement for --end)'
    ),
    '--width': dict(
        metavar='INT',
        dest='width',
        type=auto_int,
        default=64,
        help='Image width (default: 64)'
    ),
    ('-r', '--recursive'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    '--version': dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}

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
    ('-r', '--recursive'): dict(
        dest='recursive',
        action='store_true',
        help='Read all files under each directory, recursively'
    ),
    ('-F', '--fixed-string'): dict(
        dest='fixed_string',
        action='store_true',
        help='Interpret PATTERN as fixed string (disable regular expressions)'
    ),
    ('-H', '--hex-format'): dict(
        dest='hex_format',
        action='store_true',
        help='Interpret strings in PATTERN as hexadecimal'
    ),
    ('-i', '--ignore-case'): dict(
        dest='ignore_case',
        action='store_true',
        help='Perform a case-insensitive search'
    ),
    '--encoding': dict(
        metavar='ENCODING',
        dest='encoding',
        default='utf8',
        help='Convert strings in PATTERN to a specific Python encoding (default: utf8)'
    ),
    '--start': dict(
        metavar='INT',
        dest='start',
        type=auto_int,
        help='Start offset to read from (default: file start)',
    ),
    '--end': dict(
        metavar='INT',
        dest='end',
        type=auto_int,
        help='End offset to stop reading at (default: end)',
    ),
    '--length': dict(
        metavar='INT',
        dest='length',
        type=auto_int,
        help='Length to read in (optional replacement for --end)'
    ),
    '--before': dict(
        metavar='INT',
        dest='before',
        type=auto_int,
        default=2,
        help='Number of lines preceeding a match to show (default: 2)'
    ),
    '--after': dict(
        metavar='INT',
        dest='after',
        type=auto_int,
        default=2,
        help='Number of lines following a match to show (default: 2)'
    ),
    '--no-hexdump': dict(
        dest='no_hexdump',
        action='store_true',
        help='Don\'t render a hex dump'
    ),
    '--version': dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}

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
mrcgrep_parser = lambda: get_parser( args=ARGS_GREP, description='Display the contents of a file that match a pattern.', epilog=EPILOG_GREP )



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

                    if not raw_args.no_hexdump:
                        utils.hexdump(
                            source, start=raw_args.start, end=raw_args.end, length=raw_args.length,
                            major_len=raw_args.major_len, minor_len=raw_args.minor_len,
                            colour=raw_args.colour, address_base=raw_args.address_base,
                            show_offsets=raw_args.show_offsets, show_glyphs=raw_args.show_glyphs,
                        )

                    if not raw_args.no_hexdump and not raw_args.no_stats:
                        print()

                    if not raw_args.no_stats:
                        print( 'Source stats:' )
                        utils.stats( source, raw_args.start, raw_args.end, raw_args.length, raw_args.hist_w, raw_args.hist_h )
                print()
        except OSError as e:
            logger.warning( '{}'.format( e ) )


def mrcdiff():
    parser = mrcdiff_parser()
    raw_args = parser.parse_args()

    before = raw_args.before if not raw_args.show_all else None
    after = raw_args.after if not raw_args.show_all else None

    with common.read( raw_args.source1 ) as source1, common.read( raw_args.source2 ) as source2:
        utils.hexdump_diff(
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
                    if raw_args.no_hexdump:
                        utils.listdump_grep( raw_args.pattern, source,
                            encoding=raw_args.encoding, fixed_string=raw_args.fixed_string,
                            hex_format=raw_args.hex_format,
                            start=raw_args.start, end=raw_args.end,
                            length=raw_args.length,
                            title=title,
                            ignore_case=raw_args.ignore_case
                        )
                    else:
                        utils.hexdump_grep( raw_args.pattern, source,
                            encoding=raw_args.encoding, fixed_string=raw_args.fixed_string,
                            hex_format=raw_args.hex_format,
                            start=raw_args.start, end=raw_args.end,
                            length=raw_args.length,
                            before=raw_args.before, after=raw_args.after,
                            title=title,
                            ignore_case=raw_args.ignore_case
                        )
        except OSError as e:
            logger.warning( '{}'.format( e ) )
