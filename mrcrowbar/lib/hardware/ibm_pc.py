#!/usr/bin/python3

from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img

# source: https://en.wikipedia.org/wiki/Segment_descriptor
# https://pdos.csail.mit.edu/6.828/2005/readings/i386/s05_01.htm

class SegmentDescriptor( mrc.Block ):
    limit_low =     mrc.UInt16_LE( 0x00 )
    base_low =      mrc.UInt16_LE( 0x02 )
    base_middle =   mrc.UInt8( 0x04 )
    accessed =          mrc.Bits( 0x05, 0b00000001 )
    readable =          mrc.Bits( 0x05, 0b00000010 )
    conforming =        mrc.Bits( 0x05, 0b00000100 )
    code_seg =          mrc.Bits( 0x05, 0b00001000 )
    non_system =        mrc.Bits( 0x05, 0b00010000 )
    privilege_level =   mrc.Bits( 0x05, 0b01100000 )
    present =           mrc.Bits( 0x05, 0b10000000 )
    limit_high =    mrc.Bits( 0x06, 0b00001111 )
    available =     mrc.Bits( 0x06, 0b00010000 )
    op_size_64 =    mrc.Bits( 0x06, 0b00100000 )
    op_size_32 =    mrc.Bits( 0x06, 0b01000000 )
    granularity =   mrc.Bits( 0x06, 0b10000000 )
    base_high =     mrc.UInt8( 0x07 )

    @property
    def limit( self ):
        return self.limit_low + (self.limit_high << 16)

    @limit.setter
    def limit( self, value ):
        value &= 0xfff
        self.limit_high = (value & 0xf00) >> 16
        self.limit_low = (value & 0xff)

    @property
    def base( self ):
        return self.base_low + (self.base_middle << 16) + (self.base_high << 24)

    @base.setter
    def base( self, value ):
        value &= 0xffffffff
        self.base_high = (value & 0xff000000) >> 24
        self.base_middle = (value & 0xff0000) >> 16
        self.base_low = (value & 0xffff)

    @property
    def repr( self ):
        return 'present={}, code_seg={}, base={:08x}, limit={:05x}'.format( self.present, self.code_seg, self.base, self.limit )


class SegmentDescriptorTable( mrc.Block ):
    seglist = mrc.BlockField( SegmentDescriptor, 0x00, stream=True )


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

    @r_8.setter
    def r_8( self, value ):
        index = value//85
        self.r_low = index & 1 
        self.r_high = index >> 1

    @property
    def g_8( self ):
        return 85*((self.g_high << 1) + self.g_low)

    @g_8.setter
    def g_8( self, value ):
        index = value//85
        self.g_low = index & 1 
        self.g_high = index >> 1

    @property
    def b_8( self ):
        return 85*((self.b_high << 1) + self.b_low)

    @b_8.setter
    def b_8( self, value ):
        index = value//85
        self.b_low = index & 1 
        self.b_high = index >> 1


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

    @r_8.setter
    def r_8( self, value ):
        self.r_raw = value*63//255

    @property
    def g_8( self ):
        return self.g_raw*255//63

    @g_8.setter
    def g_8( self, value ):
        self.g_raw = value*63//255

    @property
    def b_8( self ):
        return self.b_raw*255//63

    @b_8.setter
    def b_8( self, value ):
        self.b_raw = value*63//255


