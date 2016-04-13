#!/usr/bin/python3

from mrcrowbar import models as mrc
from mrcrowbar import utils

import PIL

from array import array
import itertools
import math
import sys


class Colour( mrc.Block ):
    _block_size = 0
    r_8 = 0
    g_8 = 0
    b_8 = 0
    a_8 = 255

    @property
    def r( self ) -> float:
        return self.r_8/255

    @property
    def g( self ) -> float:
        return self.g_8/255

    @property
    def b( self ) -> float:
        return self.b_8/255

    @property
    def a( self ) -> float:
        return self.a_8/255

    def __str__( self ):
        return '#{:02X}{:02X}{:02X}{:02X}'.format( self.r_8, self.g_8, self.b_8, self.a_8 )

    def __eq__( self, other ):
        return (self.r_8 == other.r_8) and (self.g_8 == other.g_8) and (self.b_8 == other.b_8) and (self.a_8 == other.a_8)


class Transparent( Colour ):
    a_8 = 0


class RGBColour( Colour ):
    _block_size = 3

    r_8 = mrc.UInt8( 0x00 )
    g_8 = mrc.UInt8( 0x01 )
    b_8 = mrc.UInt8( 0x02 )


class Image( mrc.View ):
    def __init__( self, parent, width, height ):
        super( Image, self ).__init__( parent )
        self._width = width
        self._height = height
 
    @property
    def width( self ):
        return mrc.property_get( self._width, self._parent )

    @width.setter
    def width( self, value ):
        return mrc.property_set( self._width, self._parent, value )

    @property
    def height( self ):
        return mrc.property_get( self._height, self._parent )

    @height.setter
    def height( self, value ):
        return mrc.property_set( self._height, self._parent, value )


class IndexedImage( Image ):
    def __init__( self, parent, width, height, source, palette=None ):
        super( IndexedImage, self ).__init__( parent, width, height )
        self._source = source
        self._palette = palette if (palette is not None) else []

    @property
    def source( self ):
        return mrc.property_get( self._source, self._parent )

    @source.setter
    def source( self, value ):
        return mrc.property_set( self._source, self._parent, value )

    @property
    def palette( self ):
        return mrc.property_get( self._palette, self._parent )

    @palette.setter
    def palette( self, value ):
        return mrc.property_set( self._palette, self._parent, value )

    def get_image( self ):
        im = PIL.Image.new( 'P', (self.width, self.height) )
        im.putdata( self.source[:self.width, self.height] )
        im.putpalette( itertools.chain( *((c.r_8, c.g_8, c.b_8) for c in self.palette) ) )
        return im

    def ansi_format( self, x_start=0, y_start=0, width=None, height=None ):
        assert x_start in range( 0, self.width )
        assert y_start in range( 0, self.height )
        if not width:
            width = self.width-x_start
        if not height:
            height = self.height-y_start
        result = []
        for y in range( 0, height, 2 ):
            for x in range( 0, width ):
                p1 = self.palette[self.source[self.width*(y_start+y) + (x_start+x)]]
                p2 = self.palette[self.source[self.width*(y_start+y+1) + (x_start+x)]] if (self.width*(y_start+y+1) + (x_start+x)) < len( self.source ) else Transparent()
                if p1.a_8 == 0 and p2.a_8 == 0:
                    result.append( u'\x1b[0m ' )
                elif p1 == p2:
                    result.append( u'\x1b[38;2;{};{};{}m█'.format( p1.r_8, p1.g_8, p1.b_8 ) )
                elif p1.a_8 == 0 and p2.a_8 != 0:
                    result.append( u'\x1b[38;2;{};{};{}m▄'.format( p2.r_8, p2.g_8, p2.b_8 ) )
                elif p1.a_8 != 0 and p2.a_8 == 0:
                    result.append( u'\x1b[38;2;{};{};{}m▀'.format( p1.r_8, p1.g_8, p1.b_8 ) )
                else:
                    result.append( u'\x1b[38;2;{};{};{};48;2;{};{};{}m▀\x1b[0m'.format( p1.r_8, p1.g_8, p1.b_8, p2.r_8, p2.g_8, p2.b_8 ) )

            result.append( u'\x1b[0m\n' )
        return u''.join( result )
    
    def print( self, *args, **kwargs ):
        print( self.ansi_format( *args, **kwargs ) )

    def __str__( self ):
        return self.ansi_format()

    def __repr__( self ):
        return '<{}: {} bytes, {}x{}>'.format( self.__class__.__name__, self.width*self.height, self.width, self.height )


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
        im = PIL.Image.new( 'P', (self._width, self._height) )
        im.putdata( self.data[:self._width*self._height] )
        im.putpalette( itertools.chain( *((c.r_8, c.g_8, c.b_8) for c in self._palette) ) )
        return im

    def ansi_format( self, x_start=0, y_start=0, width=None, height=None ):
        assert x_start in range( 0, self._width )
        assert y_start in range( 0, self._height )
        if not width:
            width = self._width-x_start
        if not height:
            height = self._height-y_start
        result = []
        for y in range( 0, height, 2 ):
            for x in range( 0, width ):
                p1 = self._palette[self.data[self._width*(y_start+y) + (x_start+x)]]
                p2 = self._palette[self.data[self._width*(y_start+y+1) + (x_start+x)]] if (self._width*(y_start+y+1) + (x_start+x)) < len( self.data ) else Transparent()
                if p1.a_8 == 0 and p2.a_8 == 0:
                    result.append( u'\x1b[0m ' )
                elif p1 == p2:
                    result.append( u'\x1b[38;2;{};{};{}m█'.format( p1.r_8, p1.g_8, p1.b_8 ) )
                elif p1.a_8 == 0 and p2.a_8 != 0:
                    result.append( u'\x1b[38;2;{};{};{}m▄'.format( p2.r_8, p2.g_8, p2.b_8 ) )
                elif p1.a_8 != 0 and p2.a_8 == 0:
                    result.append( u'\x1b[38;2;{};{};{}m▀'.format( p1.r_8, p1.g_8, p1.b_8 ) )
                else:
                    result.append( u'\x1b[38;2;{};{};{};48;2;{};{};{}m▀\x1b[0m'.format( p1.r_8, p1.g_8, p1.b_8, p2.r_8, p2.g_8, p2.b_8 ) )

            result.append( u'\x1b[0m\n' )
        return u''.join( result )
    
    def print( self, *args, **kwargs ):
        print( self.ansi_format( *args, **kwargs ) )

    def __str__( self ):
        return self.ansi_format()

    def __repr__( self ):
        return '<{}: {} bytes, {}x{}>'.format( self.__class__.__name__, len( self.data ), self._width, self._height )
    

class Planarizer( mrc.Transform ):
    def __init__( self, width: int, height: int, bpp: int, plane_padding: int=0, frame_offset: int=0, frame_stride: int=0, frame_count: int=1 ):
        assert (width*height) % 8 == 0
        self.width = width
        self.height = height
        assert (bpp >= 0) and (bpp <= 8)
        self.bpp = bpp
        self.plane_padding = plane_padding
        self.frame_offset = frame_offset
        self.frame_stride = frame_stride
        self.frame_count = frame_count


    def import_data( self, buffer: bytes ):
        assert type( buffer ) == bytes
        if self.frame_count == 1:
            assert len( buffer ) >= self.frame_offset + math.ceil( (self.bpp*self.width*self.height)/8 )
        else:
            assert len( buffer ) >= self.frame_offset + self.frame_count*self.frame_stride

        # our output is going to be "chunky"; each byte is a pixel (8-bit or 256 colour mode)
        raw_image = bytearray( self.width*self.height*self.frame_count )

        # the input is planar. this is a packed format found occasionally in old graphics hardware,
        # and in old image formats where space was paramount.
        # the trick is you can have less than 8 bits in your colourspace! 
        # e.g. if you only need 8 colours, you can get away with a 3-bit colourspace and save 62.5% space.
        # instead of each byte being a pixel, each byte stores 8 pixels worth of data for a single plane.
        # there is one plane per bit of colourspace, and the planes are stored one after another.
        
        # in order for the calculations to be fast, planar graphics are pretty much always divisible by 8.
        # we're going to abuse this and unpack our bitplanes using 64-bit integers.
        # let's make a big array of them.
        planes = array( 'Q', (0,)*(self.width*self.height//8) )
        plane_size = (self.width*self.height//8)+self.plane_padding
    
        for f in range( self.frame_count ):
            pointer = self.frame_offset+f*self.frame_stride
            for b in range( self.bpp ):
                for i in range( self.width*self.height//8 ):
                    # for the first iteration, clear the plane
                    if b==0:
                        planes[i] = 0

                    # utils.unpack_bits is a helper method which converts a 1-byte bitfield
                    # into 8 bool bytes (i.e. 1 or 0) stored as a 64-bit int.
                    # we can effectively work on 8 chunky pixels at once!
                    # because the chunky pixels are bitfields, combining planes is an easy
                    # left shift (i.e. move all the bits up by [plane ID] places) and bitwise OR
                    planes[i] |= utils.unpack_bits( buffer[pointer+b*plane_size+i] ) << b
                    
            # check for endianness! for most intel and ARM chips the order of bytes in hardware is reversed,
            # so we need to flip it around for the bytes to be sequential.
            if sys.byteorder == 'little':
                planes.byteswap()

            # convert our planes array to bytes, and you have your chunky pixels
            raw_image[f*(self.width*self.height):(f+1)*(self.width*self.height)] = planes.tobytes()

        if self.frame_count > 1:
            end_offset = self.frame_offset + self.frame_count*self.frame_stride
        else:
            bits = self.width*self.height*self.bpp
            end_offset = self.frame_offset + (bits)//8 + (1 if (bits % 8) else 0)

        result = {
            'payload': bytes( raw_image ),
            'end_offset': end_offset
        }

        return result


    def export_data( self, buffer: bytes ):
        assert type( buffer ) == bytes
        if self.frame_count == 1:
            assert len( buffer ) >= self.frame_offset + self.width*self.height 
        else:
            assert len( buffer ) >= self.frame_offset + self.frame_count*self.frame_stride

        # this method just does the opposite of the above; split chunky pixels back into planes.
        planes = array( 'Q' )
        plane_size = (self.width*self.height//8)+self.plane_padding
        if self.frame_count == 1:
            raw_planes = bytearray( self.frame_offset+plane_size*self.bpp )
        else:
            raw_planes = bytearray( self.frame_offset+self.frame_count*self.frame_stride )
    
        for f in range( self.frame_count ):
            pointer = self.frame_offset+f*self.frame_stride
            planes = planes[0:0]
            # load our chunky pixels into the 64-bit int array
            planes.frombytes( buffer[f*(self.width*self.height):(f+1)*(self.width*self.height)] )
            # check for endianness!
            if sys.byteorder == 'little':
                planes.byteswap()

            for b in range( self.bpp ):
                for i in range( self.width*self.height//8 ):
                    # for each group of 8 chunky pixels, use pack_bits to fill up 8 bits
                    # of the relevant bitplane
                    raw_planes[pointer+b*plane_size+i] = utils.pack_bits( (planes[i] >> b) )

        result = {
            'payload': raw_planes
        }
        return result



