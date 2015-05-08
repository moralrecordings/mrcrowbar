#!/usr/bin/python3

from mrcrowbar import models as mrc

class EGAColour( mrc.Block ):
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

    def __str__( self ):
        return '#%02X%02X%02X' % (self.r_8, self.g_8, self.b_8)


class VGAColour( mrc.Block ):
    _block_size =   3
    r_raw =         mrc.UInt8( 0x0000, range=range( 0, 128 ) )
    g_raw =         mrc.UInt8( 0x0001, range=range( 0, 128 ) )
    b_raw =         mrc.UInt8( 0x0002, range=range( 0, 128 ) )

    @property
    def r_8( self ):
        return self.r_raw*255//127

    @property
    def g_8( self ):
        return self.g_raw*255//127

    @property
    def b_8( self ):
        return self.b_raw*255//127

    @property
    def r( self ):
        return self.r_raw/127

    @property
    def g( self ):
        return self.g_raw/127

    @property
    def b( self ):
        return self.b_raw/127

    def __str__( self ):
        return '#%02X%02X%02X' % (self.r_8, self.g_8, self.b_8)


