#!/usr/bin/python3

from mrcrowbar import models as mrc

from PIL import Image

import array
import itertools


class Colour( mrc.Block ):
    _block_size = 0
    r_8 = 0
    g_8 = 0
    b_8 = 0
    a_8 = 255

    @property
    def r( self ):
        return self.r_8/255

    @property
    def g( self ):
        return self.g_8/255

    @property
    def b( self ):
        return self.b_8/255

    @property
    def a( self ):
        return self.a_8/255

    def __str__( self ):
        return '#{:02X}{:02X}{:02X}{:02X}'.format( self.r_8, self.g_8, self.b_8, self.a_8 )


class RGBColour( Colour ):
    _block_size = 3

    r_8 = mrc.UInt8( 0x00 )
    g_8 = mrc.UInt8( 0x01 )
    b_8 = mrc.UInt8( 0x02 )


class RawIndexedImage( mrc.Block ):
    _width =            0
    _height =           0
    _palette =          []

    data = mrc.Bytes( 0x0000 )

    def __init__( self, buffer, width=0, height=0, palette=None, **kwargs ):
        self._width = width
        self._height = height
        if palette is not None:
            self._palette = palette
        #assert len( buffer ) == width*height
        super( RawIndexedImage, self ).__init__( buffer, **kwargs )

    def get_image( self ):
        im = Image.new( 'P', (self._width, self._height) )
        im.putdata( self.data[:self._width*self._height] )
        im.putpalette( itertools.chain( *[(c.r_8, c.g_8, c.b_8) for c in self._palette] ) )
        return im
    
    
class Planarizer( mrc.Transform ):
    def __init__( self, width, height, bpp, frame_offset=0, frame_stride=0, frame_count=1 ):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.frame_offset = frame_offset
        self.frame_stride = frame_stride
        self.frame_count = frame_count

    def import_data( self, buffer ):
        assert type( buffer ) == bytes
        def get_bit( state ):
            result = 1 if (buffer[state['index']] & (1 << (7-state['pos']))) else 0
            state['pos'] += 1
            state['index'] += state['pos']//8
            state['pos'] %= 8
            return result

        raw_image = array.array( 'B', b'\x00'*self.width*self.height*self.frame_count )

        for f in range( self.frame_count ):
            state = {'index': self.frame_offset + f*self.frame_stride, 'pos': 0} 
            for b in range( self.bpp ):
                for i in range( self.width*self.height ):
                    raw_image[f*self.width*self.height + i] += get_bit( state ) << b

        return bytes( raw_image )

