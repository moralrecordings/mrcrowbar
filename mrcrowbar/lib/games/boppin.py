#!/usr/bin/python3

import array
import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.images import base as img
from mrcrowbar.utils import BitStream


class Lookup( mrc.Block ):
    _block_size =   8

    offset =        mrc.UInt32_LE( 0x00 )
    size =          mrc.UInt32_LE( 0x04 )

# stop looking for more lookup-table entries once we hit the first result that references the end of the file
resource_stop_check = lambda buffer, offset: (offset >= len( buffer )-1) or (mrc.UInt32_LE( 0x00 ).get_from_buffer( buffer[offset-8:] ) + mrc.UInt32_LE( 0x04 ).get_from_buffer( buffer[offset-8:] ) >= len( buffer )-1)

class Resource( mrc.Block ):
    lookup_table =  mrc.BlockStream( Lookup, 0x00, stride=0x08, count=64, stop_check=resource_stop_check, fill=b'\xff\xff\xff\xff\x00\x00\x00\x00' )

