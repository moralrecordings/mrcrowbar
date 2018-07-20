from mrcrowbar import utils
from mrcrowbar.version import __version__

import argparse
import mmap
import os

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
        type=argparse.FileType( mode='rb' ),
        help='File to inspect',
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
        type=argparse.FileType( mode='rb' ),
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
    '--version': dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}

def mrcdump():
    parser = argparse.ArgumentParser( description='Examine the binary contents of a file.' )
    for arg, spec in ARGS_DUMP.items():
        parser.add_argument( arg, **spec )
    raw_args = parser.parse_args()

    source = mmap.mmap( raw_args.source.fileno(), 0, access=mmap.ACCESS_READ )

    if not raw_args.no_hexdump:
        utils.hexdump(
            source, start=raw_args.start, end=raw_args.end, length=raw_args.length,
            major_len=raw_args.major_len, minor_len=raw_args.minor_len,
            colour=raw_args.colour
        )
        print( '' )

    if not raw_args.no_stats:
        print( 'Source stats:' )
        utils.stats( source, raw_args.start, raw_args.end, raw_args.length, raw_args.hist_w, raw_args.hist_h )


def mrcdiff():
    parser = argparse.ArgumentParser( description='Compare the binary contents of two files.' )
    for arg, spec in ARGS_DIFF.items():
        parser.add_argument( arg, **spec )
    raw_args = parser.parse_args()

    source1 = mmap.mmap( raw_args.source1.fileno(), 0, access=mmap.ACCESS_READ )
    source2 = mmap.mmap( raw_args.source2.fileno(), 0, access=mmap.ACCESS_READ )
    before = raw_args.before if not raw_args.show_all else None
    after = raw_args.after if not raw_args.show_all else None

    utils.hexdump_diff(
        source1, source2, start=raw_args.start, end=raw_args.end,
        length=raw_args.length, major_len=raw_args.major_len,
        minor_len=raw_args.minor_len, colour=raw_args.colour,
        before=before, after=after
    )

def mrchist():
    parser = argparse.ArgumentParser( description='Display the binary contents of a file as a histogram map.' )
    for arg, spec in ARGS_HIST.items():
        parser.add_argument( arg, **spec )
    raw_args = parser.parse_args()

    source = mmap.mmap( raw_args.source.fileno(), 0, access=mmap.ACCESS_READ )

    utils.histdump( source, raw_args.start, raw_args.end, raw_args.length, raw_args.samples, raw_args.width )
