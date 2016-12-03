from mrcrowbar import models as mrc
from mrcrowbar import utils

from PIL import Image as PILImage

from array import array
import itertools
import collections
import math
import sys


class Colour( mrc.Block ):
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

    @property
    def luma( self ) -> float:
        return 0.299*self.r + 0.587*self.g + 0.114*self.b

    def set_rgb( self, r_8, g_8, b_8 ):
        self.r_8 = r_8
        self.g_8 = g_8
        self.b_8 = b_8

    def clone_data( self, source ):
        assert isinstance( source, Colour )
        self.r_8 = source.r_8
        self.g_8 = source.g_8
        self.b_8 = source.b_8
        self.a_8 = source.a_8

    @property
    def repr( self ):
        return '#{:02X}{:02X}{:02X}{:02X}'.format( self.r_8, self.g_8, self.b_8, self.a_8 )

    def ansi_format( self, text=None ):
        if text is None:
            text = ' {} '.format( self.repr )
        colour = White() if self.luma < 0.5 else Black()
        return utils.ansi_format_string( text, colour, self )

    def __str__( self ):
        return self.ansi_format()

    def __eq__( self, other ):
        return (self.r_8 == other.r_8) and (self.g_8 == other.g_8) and (self.b_8 == other.b_8) and (self.a_8 == other.a_8)


class White( Colour ):
    r_8 = 255
    g_8 = 255
    b_8 = 255


class Black( Colour ):
    r_8 = 0
    g_8 = 0
    b_8 = 0


class Transparent( Colour ):
    a_8 = 0


class RGBColour( Colour ):
    r_8 = mrc.UInt8( 0x00 )
    g_8 = mrc.UInt8( 0x01 )
    b_8 = mrc.UInt8( 0x02 )


class Palette( mrc.BlockField ):
    def __init__( self, block_klass, offset, block_kwargs=None, count=None, fill=None, **kwargs ):
        assert issubclass( block_klass, Colour )
        super( Palette, self ).__init__( block_klass, offset, block_kwargs, count, fill, **kwargs )

    def scrub( self, value, parent=None ):
        return [x if isinstance( x, self.block_klass ) else self.block_klass( x ) for x in value]


class Image( mrc.View ):
    def __init__( self, parent, source, width, height, frame_count=1 ):
        super( Image, self ).__init__( parent )
        self._source = source
        self._width = width
        self._height = height
        self._frame_count = frame_count
    
    @property
    def source( self ):
        return mrc.property_get( self._source, self._parent )

    @source.setter
    def source( self, value ):
        return mrc.property_set( self._source, self._parent, value )
 
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

    @property
    def frame_count( self ):
        return mrc.property_get( self._frame_count, self._parent )

    @frame_count.setter
    def frame_count( self, value ):
        return mrc.property_set( self._frame_count, self._parent, value )


def to_palette_bytes( palette ):
    return itertools.chain( *((c.r_8, c.g_8, c.b_8) for c in palette) )


def from_palette_bytes( palette_bytes ):
    result = []
    for i in range( math.floor( len( palette_bytes )/3 ) ):
        colour = Colour()
        colour.set_rgb( palette_bytes[3*i], palette_bytes[3*i+1], palette_bytes[3*i+2] )
        result.append( colour )
    return result


class IndexedImage( Image ):
    def __init__( self, parent, source, width, height, frame_count=1, palette=None ):
        super( IndexedImage, self ).__init__( parent, source, width, height, frame_count )
        self._palette = palette if (palette is not None) else []

    @property
    def palette( self ):
        return mrc.property_get( self._palette, self._parent )

    @palette.setter
    def palette( self, value ):
        return mrc.property_set( self._palette, self._parent, value )

    def get_image( self ):
        im = PILImage.new( 'P', (self.width, self.height) )
        im.putdata( self.source[:self.width*self.height] )
        im.putpalette( to_palette_bytes( self.palette ) )
        return im

    def set_image( self, image, change_dims=True, change_palette=False ):
        if not isinstance( image, PILImage.Image ):
            raise TypeError( 'image must be a PILImage object!' )
        if image.mode != 'P':
            raise AttributeError( 'image must be indexed (mode P)' )
        if change_dims:
            if self.width != image.width:
                print( "Changing width from {} to {}".format( self.width, image.width ) )
                self.width = image.width
            if self.height != image.height:
                print( "Changing height from {} to {}".format( self.height, image.height ) )
                self.height = image.height
        else:
            assert (self.width == image.width) and (self.height == image.height)

        old_pal = to_palette_bytes( self.palette )
        new_pal = image.palette.palette
        if old_pal != new_pal:
            if change_palette:
                self.palette = from_palette_bytes( new_pal )
            else:
                print( "WARNING: Palette of new image is different!" )
        self.source = image.tobytes()

    def ansi_format( self, x_start=0, y_start=0, width=None, height=None, frame=0 ):
        assert x_start in range( 0, self.width )
        assert y_start in range( 0, self.height )
        assert frame in range( 0, self.frame_count )
        if not width:
            width = self.width-x_start
        if not height:
            height = self.height-y_start
        result = []
        for y in range( 0, height, 2 ):
            for x in range( 0, width ):
                stride = width*height
                i1 = self.width*(y_start+y) + (x_start+x)
                i2 = self.width*(y_start+y+1) + (x_start+x)
                p1 = self.palette[self.source[stride*frame+i1]]
                p2 = self.palette[self.source[stride*frame+i2]] if (i2) < (self.width*self.height) else Transparent()
                result.append( utils.ansi_format_pixels( p1, p2 ) )
            result.append( '\n' )
        return u''.join( result )
    
    def print( self, *args, **kwargs ):
        print( self.ansi_format( *args, **kwargs ) )

    def __str__( self ):
        return self.ansi_format()

    def __repr__( self ):
        return '<{}: {} bytes, {}x{}>'.format( self.__class__.__name__, self.width*self.height, self.width, self.height )


class Planarizer( mrc.Transform ):
    def __init__( self, width: int, height: int, bpp: int, plane_padding: int=0, frame_offset: int=0, frame_stride: int=None, frame_count: int=1 ):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.plane_padding = plane_padding
        self.frame_offset = frame_offset
        self.frame_count = frame_count
        self.frame_stride = frame_stride


    def import_data( self, buffer: bytes, parent=None ):
        assert utils.is_bytes( buffer )

        # load in constructor properties
        width = mrc.property_get( self.width, parent )
        height = mrc.property_get( self.height, parent )
        bpp = mrc.property_get( self.bpp, parent )
        plane_padding = mrc.property_get( self.plane_padding, parent )
        frame_offset = mrc.property_get( self.frame_offset, parent )
        frame_count = mrc.property_get( self.frame_count, parent )
        frame_stride = mrc.property_get( self.frame_stride, parent )
        if frame_count >= 2 and frame_stride is None:
            frame_stride = bpp*((width*height//8)+plane_padding)
        else:
            frame_stride = frame_stride if frame_stride is not None else 0
        assert (width*height) % 8 == 0
        assert (bpp >= 0) and (bpp <= 8)
        assert (frame_count >= 1)
        # because frame_stride can potentially read past the buffer, only worry about measuring
        # the last n-1 strides + one frame
        assert len( buffer ) >= frame_offset + (frame_count-1)*frame_stride + math.ceil( (bpp*width*height)/8 ) 


        # our output is going to be "chunky"; each byte is a pixel (8-bit or 256 colour mode)
        raw_image = bytearray( width*height*frame_count )

        # the input is planar. this is a packed format found occasionally in old graphics hardware,
        # and in old image formats where space was paramount.
        # the trick is you can have less than 8 bits in your colourspace! 
        # e.g. if you only need 8 colours, you can get away with a 3-bit colourspace and save 62.5% space.
        # instead of each byte being a pixel, each byte stores 8 pixels worth of data for a single plane.
        # there is one plane per bit of colourspace, and the planes are stored one after another.
        
        # in order for the calculations to be fast, planar graphics are pretty much always divisible by 8.
        # we're going to abuse this and unpack our bitplanes using 64-bit integers.
        # let's make a big array of them.
        planes = array( 'Q', (0,)*(width*height//8) )
        plane_size = (width*height//8)+plane_padding
    
        for f in range( frame_count ):
            pointer = frame_offset+f*frame_stride
            for b in range( bpp ):
                for i in range( width*height//8 ):
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
            raw_image[f*(width*height):(f+1)*(width*height)] = planes.tobytes()

        if frame_count > 1:
            end_offset = frame_offset + frame_count*frame_stride
        else:
            bits = width*height*bpp
            end_offset = frame_offset + (bits)//8 + (1 if (bits % 8) else 0)

        result = {
            'payload': bytes( raw_image ),
            'end_offset': end_offset
        }

        return result


    def export_data( self, buffer: bytes, parent=None ):
        assert utils.is_bytes( buffer )

        # load in constructor properties
        width = mrc.property_get( self.width, parent )
        height = mrc.property_get( self.height, parent )
        bpp = mrc.property_get( self.bpp, parent )
        plane_padding = mrc.property_get( self.plane_padding, parent )
        frame_offset = mrc.property_get( self.frame_offset, parent )
        frame_count = mrc.property_get( self.frame_count, parent )
        frame_stride = mrc.property_get( self.frame_stride, parent )
        if frame_count >= 2 and frame_stride is None:
            frame_stride = bpp*((width*height//8)+plane_padding)
        else:
            frame_stride = frame_stride if frame_stride is not None else 0
        assert (width*height) % 8 == 0
        assert (bpp >= 0) and (bpp <= 8)
        if frame_count == 1:
            assert len( buffer ) >= frame_offset + width*height 
        else:
            assert len( buffer ) >= frame_offset + frame_count*frame_stride

        # this method just does the opposite of the above; split chunky pixels back into planes.
        planes = array( 'Q' )
        plane_size = (width*height//8)+plane_padding
        if frame_count == 1:
            raw_planes = bytearray( frame_offset+plane_size*bpp )
        else:
            raw_planes = bytearray( frame_offset+frame_count*frame_stride )
    
        for f in range( frame_count ):
            pointer = frame_offset+f*frame_stride
            planes = planes[0:0]
            # load our chunky pixels into the 64-bit int array
            planes.frombytes( buffer[f*(width*height):(f+1)*(width*height)] )
            # check for endianness!
            if sys.byteorder == 'little':
                planes.byteswap()

            for b in range( bpp ):
                for i in range( width*height//8 ):
                    # for each group of 8 chunky pixels, use pack_bits to fill up 8 bits
                    # of the relevant bitplane
                    raw_planes[pointer+b*plane_size+i] = utils.pack_bits( (planes[i] >> b) )

        result = {
            'payload': raw_planes
        }
        return result



