#!/usr/bin/python3

import struct
import array
import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.os import dos
from mrcrowbar.lib.images import base as img
from mrcrowbar.utils import BitStream


class SplashEGA( mrc.Block ):
    image =     mrc.BlockField( img.RawIndexedImage, 0x0000, block_kwargs={ 'width': 320, 'height': 200, 'palette': dos.EGA_DEFAULT_PALETTE }, transform=img.Planarizer( 320, 200, 4 ) )
    

class SplashVGA( mrc.Block ):
    palette =   mrc.BlockStream( dos.VGAColour, 0x0000, stride=0x03, count=256 )
    image =     mrc.BlockField( img.RawIndexedImage, 0x0300, block_kwargs={ 'width': 320, 'height': 200 } )


class ZIVCompressor( mrc.Transform ):
    def import_data( self, buffer ):
        assert type( buffer ) == bytes
        
        decompressed_size = ((buffer[0] & 0x0f) << 16) + (buffer[2] << 8) + buffer[3]


        
