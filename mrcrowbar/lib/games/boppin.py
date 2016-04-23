#!/usr/bin/python3

import array
import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.images import base as img
from mrcrowbar.lib.compressors import lzss
from mrcrowbar import utils


class Lookup( mrc.Block ):
    _block_size =   8

    offset =        mrc.UInt32_LE( 0x00 )
    size =          mrc.UInt32_LE( 0x04 )

# stop looking for more lookup-table entries once we hit the first result that references the end of the file
def resource_stop_check( buffer, offset ):
    # we want to look at the previous entry to the current one, ignore if we're at the first entry
    if (offset < 8):
        return False
    # too near the end of the file? that's a paddling
    if (offset >= len( buffer )-8):
        return True

    block_offset = utils.from_uint32_le( buffer[offset-8:] )
    block_size = utils.from_uint32_le( buffer[offset-4:] )

    # ignore filler entries
    if (block_offset == 0xffffffff) and (block_size == 0):
        return False
    
    # check for references to the end of the file
    return block_offset+block_size >= len( buffer )-1



class Resource( mrc.Block ):
    lookup_table =  mrc.BlockStream( Lookup, 0x00, stride=0x08, count=64, stop_check=resource_stop_check, fill=b'\xff\xff\xff\xff\x00\x00\x00\x00' )


class BoppinCompressor( mrc.Transform ):
    
    def import_data( self, buffer, parent=None ):
        lc = lzss.LZSSCompressor()
        size_comp = utils.from_uint32_le( buffer )

        if size_comp != len( buffer ):
            print( 'File not compressed!' )
            return buffer
        
        size_raw = utils.from_uint32_le( buffer[4:] )
        result = lc.import_data( buffer[8:] )
        if len( result ) != size_raw:
            print( 'Was expecting a decompressed size of {}, got {}!'.format( size_raw, len( result ) ) )
        return result


