#!/usr/bin/python3

from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img


class EGAColour( img.Colour ):
    r_high =        mrc.Bits( 0x00, 0b00000100 )
    g_high =        mrc.Bits( 0x00, 0b00000010 )
    b_high =        mrc.Bits( 0x00, 0b00000001 )
    r_low =         mrc.Bits( 0x00, 0b00100000 )
    g_low =         mrc.Bits( 0x00, 0b00010000 )
    b_low =         mrc.Bits( 0x00, 0b00001000 )

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

EGA_DEFAULT_PALETTE = (
    EGAColour( b'\x00' ), EGAColour( b'\x01' ), EGAColour( b'\x02' ), EGAColour( b'\x03' ),
    EGAColour( b'\x04' ), EGAColour( b'\x05' ), EGAColour( b'\x14' ), EGAColour( b'\x07' ),
    EGAColour( b'\x38' ), EGAColour( b'\x39' ), EGAColour( b'\x3a' ), EGAColour( b'\x3b' ),
    EGAColour( b'\x3c' ), EGAColour( b'\x3d' ), EGAColour( b'\x3e' ), EGAColour( b'\x3f' )
)


class VGAColour( img.Colour ):
    r_raw =         mrc.UInt8( 0x00, range=range( 0, 64 ) )
    g_raw =         mrc.UInt8( 0x01, range=range( 0, 64 ) )
    b_raw =         mrc.UInt8( 0x02, range=range( 0, 64 ) )

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




