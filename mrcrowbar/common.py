import itertools
import contextlib
import mmap

next_position_hint = itertools.count()


def is_bytes( obj ):
    """Returns whether obj is an acceptable Python byte string."""
    return isinstance( obj, (bytes, bytearray, mmap.mmap, memoryview) )


def read( fp ):
    try:
        region = mmap.mmap( fp.fileno(), 0, access=mmap.ACCESS_READ )
    except:
        data = fp.read()

        # add a fake context manager so "with" statements still work
        @contextlib.contextmanager
        def ctx():
            yield data

        region = ctx()

    return region


def bounds( start, end, length, src_size ):
    start = 0 if (start is None) else start
    if (end is not None) and (length is not None):
        raise ValueError( 'Can\'t define both an end and a length!' )
    elif (length is not None):
        end = start+length
    elif (end is not None):
        pass
    else:
        end = src_size
    return start, end


def serialise( obj, fields ):
    return ((obj.__class__.__module__, obj.__class__.__name__), tuple( (x, getattr( obj, x )) for x in fields ))
