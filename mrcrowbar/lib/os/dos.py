#!/usr/bin/python3

from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img

class EGAColour( img.Colour ):
    _block_size =   1
    r_high =        mrc.Bits( 0x0000, 0b00000100 )
    g_high =        mrc.Bits( 0x0000, 0b00000010 )
    b_high =        mrc.Bits( 0x0000, 0b00000001 )
    r_low =         mrc.Bits( 0x0000, 0b00100000 )
    g_low =         mrc.Bits( 0x0000, 0b00010000 )
    b_low =         mrc.Bits( 0x0000, 0b00001000 )

    @property
    def r_8( self ):
        return 85*((self.r_high << 1) + self.r_low)

    @property
    def g_8( self ):
        return 85*((self.g_high << 1) + self.g_low)

    @property
    def b_8( self ):
        return 85*((self.b_high << 1) + self.b_low)

    @property
    def r( self ):
        return ((self.r_high << 1) + self.r_low)/3

    @property
    def g( self ):
        return ((self.g_high << 1) + self.g_low)/3

    @property
    def b( self ):
        return ((self.b_high << 1) + self.b_low)/3


class VGAColour( img.Colour ):
    _block_size =   3
    r_raw =         mrc.UInt8( 0x0000, range=range( 0, 64 ) )
    g_raw =         mrc.UInt8( 0x0001, range=range( 0, 64 ) )
    b_raw =         mrc.UInt8( 0x0002, range=range( 0, 64 ) )

    @property
    def r_8( self ):
        return self.r_raw*255//63

    @property
    def g_8( self ):
        return self.g_raw*255//63

    @property
    def b_8( self ):
        return self.b_raw*255//63

    @property
    def r( self ):
        return self.r_raw/63

    @property
    def g( self ):
        return self.g_raw/63

    @property
    def b( self ):
        return self.b_raw/63


