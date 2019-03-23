from mrcrowbar import utils
from mrcrowbar.version import __version__

import argparse

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
        nargs='+',
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
    '--version': dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}

ARGS_PIX = {
   'source': dict(
        metavar='FILE',
        nargs='+',
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
    '--width': dict(
        metavar='INT',
        dest='width',
        type=auto_int,
        default=64,
        help='Image width (default: 64)'
    ),
    '--version': dict(
        action='version',
        version='%(prog)s {}'.format( __version__ )
    ),
}

def get_parser( description, args ):
    parser = argparse.ArgumentParser( description=description )
    for arg, spec in args.items():
        parser.add_argument( arg, **spec )
    return parser

mrcdump_parser = lambda: get_parser( description='Examine the contents of a file as hexadecimal.', args=ARGS_DUMP )
mrcdiff_parser = lambda: get_parser( description='Compare the contents of two files as hexadecimal.', args=ARGS_DIFF )
mrchist_parser = lambda: get_parser( description='Display the contents of a file as a histogram map.', args=ARGS_HIST )
mrcpix_parser = lambda: get_parser( description='Display the contents of a file as a 256 colour image.', args=ARGS_PIX )

def mrcdump():
    parser = mrcdump_parser()
    raw_args = parser.parse_args()

    for i, src in enumerate( raw_args.source ):
        if len( raw_args.source ) != 1:
            print( src.name )
        with utils.read( src ) as source:

            if not raw_args.no_hexdump:
                utils.hexdump(
                    source, start=raw_args.start, end=raw_args.end, length=raw_args.length,
                    major_len=raw_args.major_len, minor_len=raw_args.minor_len,
                    colour=raw_args.colour, address_base=raw_args.address_base,
                )

            if not raw_args.no_hexdump and not raw_args.no_stats:
                print()

            if not raw_args.no_stats:
                print( 'Source stats:' )
                utils.stats( source, raw_args.start, raw_args.end, raw_args.length, raw_args.hist_w, raw_args.hist_h )
        if i != len( raw_args.source ) - 1:
            print()

def mrcdiff():
    parser = mrcdiff_parser()
    raw_args = parser.parse_args()

    before = raw_args.before if not raw_args.show_all else None
    after = raw_args.after if not raw_args.show_all else None

    with utils.read( raw_args.source1 ) as source1, utils.read( raw_args.source2 ) as source2:
        utils.hexdump_diff(
            source1, source2, start=raw_args.start, end=raw_args.end,
            length=raw_args.length, major_len=raw_args.major_len,
            minor_len=raw_args.minor_len, colour=raw_args.colour,
            before=before, after=after, address_base=raw_args.address_base,
        )

def mrchist():
    parser = mrchist_parser()
    raw_args = parser.parse_args()

    for i, src in enumerate( raw_args.source ):
        if len( raw_args.source ) != 1:
            print( src.name )
        with utils.read( src ) as source:
            utils.histdump( source, start=raw_args.start, end=raw_args.end,
                length=raw_args.length, samples=raw_args.samples, width=raw_args.width,
                address_base=raw_args.address_base,
            )
        if i != len( raw_args.source ) - 1:
            print()

def mrcpix():
    parser = mrcpix_parser()
    raw_args = parser.parse_args()

    for i, src in enumerate( raw_args.source ):
        if len( raw_args.source ) != 1:
            print( src.name )
        with utils.read( src ) as source:
            utils.pixdump( source, start=raw_args.start, end=raw_args.end,
                length=raw_args.length, width=raw_args.width,
            )
        if i != len( raw_args.source ) - 1:
            print()
