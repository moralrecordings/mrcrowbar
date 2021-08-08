import itertools
import contextlib
import mmap
import os
from typing import Optional, Tuple, Union, List, Any, Iterator, BinaryIO

next_position_hint = itertools.count()

Bytes = Union[bytes, bytearray, mmap.mmap, memoryview]


def is_bytes( obj: Any ) -> bool:
    """Returns whether obj is an acceptable Python byte string."""
    return isinstance( obj, getattr( Bytes, '__args__' ) )


def read( fp: BinaryIO ) -> Bytes:
    try:
        region = mmap.mmap( fp.fileno(), 0, access=mmap.ACCESS_READ )
    except:
        region = fp.read()

    return region


def bounds( start: Optional[int], end: Optional[int], length: Optional[int], src_size: int ) -> Tuple[int, int]:
    if length is not None and length < 0:
        raise ValueError( 'Length can\'t be a negative number!' )
    start = 0 if (start is None) else start

    if (end is not None) and (length is not None):
        raise ValueError( 'Can\'t define both an end and a length!' )
    elif (length is not None):
        end = start + length
    elif (end is not None):
        pass
    else:
        end = src_size

    if start < 0:
        start += src_size
    if end < 0:
        end += src_size
    start = max( start, 0 )
    end = min( end, src_size )

    return start, end


def serialise( obj: Any, fields: List[str] ):
    return ((obj.__class__.__module__, obj.__class__.__name__), tuple( (x, getattr( obj, x )) for x in fields ))


def file_path_recurse( *root_list: str ) -> Iterator[str]:
    for root in root_list:
        if os.path.isfile( root ):
            yield root
            continue
        for path, _, files in os.walk( root ):
            for item in files:
                file_path = os.path.join( path, item )
                if not os.path.isfile( file_path ):
                    continue
                yield file_path
