from mrcrowbar import models as mrc
from mrcrowbar import ansi, utils
from mrcrowbar.colour import BaseColour, Black, White, Transparent, from_palette_bytes, to_palette_bytes

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

from array import array
import itertools
import collections
import math
import sys
import io
import logging
logger = logging.getLogger( __name__ )

class Colour( mrc.Block, BaseColour ):
    pass


class RGBColour( Colour ):
    r_8 = mrc.UInt8( 0x00 )
    g_8 = mrc.UInt8( 0x01 )
    b_8 = mrc.UInt8( 0x02 )


class RGBAColour( Colour ):
    r_8 = mrc.UInt8( 0x00 )
    g_8 = mrc.UInt8( 0x01 )
    b_8 = mrc.UInt8( 0x02 )
    a_8 = mrc.UInt8( 0x03 )


class Palette( mrc.BlockField ):
    def __init__( self, block_klass, offset, block_kwargs=None, count=None, fill=None, **kwargs ):
        assert issubclass( block_klass, Colour )
        super().__init__( block_klass, offset, block_kwargs, count, fill, **kwargs )

    def scrub( self, value, parent=None ):
        return [x if isinstance( x, self.block_klass ) else self.block_klass( x ) for x in value]


class Image( mrc.View ):
    def __init__( self, parent, source, width, height, frame_count=1 ):
        super().__init__( parent )
        self._source = source
        self._width = width
        self._height = height
        self._frame_count = frame_count
    
    source = mrc.view_property( '_source' )
    width = mrc.view_property( '_width' )
    height = mrc.view_property( '_height' )
    frame_count = mrc.view_property( '_frame_count' )



class CodecImage( Image ):
    """Class for viewing image data encoded in a standard image file format."""

    def __init__( self, parent, source, width=None, height=None, frame_count=1, format=None, mode=None ):
        super().__init__( parent, source, width, height, frame_count )
        self._format = format
        self._mode = mode

    format = mrc.view_property( '_format' )
    mode = mrc.view_property( '_mode' )

    def get_image( self ):
        if not PILImage:
            raise ImportError( 'Pillow must be installed for image manipulation support (see http://pillow.readthedocs.io/en/latest/installation.html)' )
        src = io.BytesIO( self.source )
        image = PILImage.open( src )
        if self.width is not None and image.size[0] != self.width:
            logger.warning( 'Image {} has width {}, was expecting {}'.format( self, image.size[0], self.width ) )
        if self.height is not None and image.size[1] != self.height:
            logger.warning( 'Image {} has height {}, was expecting {}'.format( self, image.size[1], self.height ) )
        if self.format is not None and image.format != self.format:
            logger.warning( 'Image {} is in {} format, was expecting {} format'.format( self, image.format, self.format ) )
        if self.mode is not None and image.mode != self.mode:
            logger.warning( 'Image {} is mode {}, was expecting mode {}'.format( self, image.mode, self.mode ) )
        image.load()
        return image

    def ansi_format_iter( self, x_start=0, y_start=0, width=None, height=None, frame=0, columns=1, downsample=1 ):
        """Return the ANSI escape sequence to render the image.

        x_start
            Offset from the left of the image data to render from. Defaults to 0.

        y_start
            Offset from the top of the image data to render from. Defaults to 0.

        width
            Width of the image data to render. Defaults to the image width.

        height
            Height of the image data to render. Defaults to the image height.

        frame
            Single frame number, or a list of frame numbers to render in sequence. Defaults to frame 0.

        columns
            Number of frames to render per line (useful for printing tilemaps!). Defaults to 1.

        downsample
            Shrink larger images by printing every nth pixel only. Defaults to 1.
        """

        image = self.get_image()
        frames = []
        frame_count = 1 if not hasattr( image, 'n_frames' ) else image.n_frames
        if isinstance( frame, int ):
            assert frame in range( 0, frame_count )
            frames = [frame]
        else:
            frames = [f for f in frame if f in range( 0, frame_count )]

        if not width:
            width = image.size[0]-x_start
        if not height:
            height = image.size[1]-y_start

        if image.mode == 'P':
            palette = from_palette_bytes( image.getpalette() )

            def data_fetch( x, y, fr ):
                if fr not in range( 0, frame_count ):
                    return Transparent()
                if not ((0 <= x < image.size[0]) and (0 <= y < image.size[1])):
                    return Transparent()
                image.seek( fr )
                return palette[image.getpixel( (x, y) )]

            for x in ansi.format_image_iter( data_fetch, x_start, y_start, width, height, frames, columns, downsample ):
                yield x
        return

    def print( self, *args, **kwargs ):
        for x in self.ansi_format_iter( *args, **kwargs ):
            print( x )


class IndexedImage( Image ):
    """Class for viewing indexed (palette-based) chunky image data."""

    def __init__( self, parent, source, width, height, frame_count=1, palette=None, mask=None ):
        super().__init__( parent, source, width, height, frame_count )
        self._palette = palette if (palette is not None) else []
        self._mask = mask

    palette = mrc.view_property( '_palette' )
    mask = mrc.view_property( '_mask' )

    def get_image( self ):
        if not PILImage:
            raise ImportError( 'Pillow must be installed for image manipulation support (see http://pillow.readthedocs.io/en/latest/installation.html)' )
        im = PILImage.new( 'P', (self.width, self.height) )
        im.putdata( self.source[:self.width*self.height] )
        im.putpalette( to_palette_bytes( self.palette ) )
        return im

    def set_image( self, image, change_dims=True, change_palette=False ):
        if not PILImage:
            raise ImportError( 'Pillow must be installed for image manipulation support (see http://pillow.readthedocs.io/en/latest/installation.html)' )
        if not isinstance( image, PILImage.Image ):
            raise TypeError( 'Image must be a PILImage object' )
        if image.mode != 'P':
            raise AttributeError( 'Image must be indexed (mode P)' )
        if change_dims:
            if self.width != image.width:
                logger.warning( "Changing width from {} to {}".format( self.width, image.width ) )
                self.width = image.width
            if self.height != image.height:
                logger.warning( "Changing height from {} to {}".format( self.height, image.height ) )
                self.height = image.height
        else:
            if not (self.width == image.width) and (self.height == image.height):
                raise AttributeError( 'Image is a different size, please enable change_dims if you want to resize the image' )

        old_pal = to_palette_bytes( self.palette )
        new_pal = image.palette.palette
        if old_pal != new_pal:
            if change_palette:
                self.palette = from_palette_bytes( new_pal )
            else:
                logger.warning( 'Image was provided with a different palette, please enable change_palette if you want to set the palette' )
        self.source = image.tobytes()

    def ansi_format_iter( self, x_start=0, y_start=0, width=None, height=None, frame=0, columns=1, downsample=1, frame_index=None, frame_flip_v=0, frame_flip_h=0 ):
        """Return the ANSI escape sequence to render the image.

        x_start
            Offset from the left of the image data to render from. Defaults to 0.

        y_start
            Offset from the top of the image data to render from. Defaults to 0.

        width
            Width of the image data to render. Defaults to the image width.

        height
            Height of the image data to render. Defaults to the image height.

        frame
            Single frame number/object, or a list of frames to render in sequence. Defaults to frame 0.

        columns
            Number of frames to render per line (useful for printing tilemaps!). Defaults to 1.

        downsample
            Shrink larger images by printing every nth pixel only. Defaults to 1.

        frame_index
            Constant or mrc.Ref for a frame object property denoting the index. Defaults to None
            (i.e. frame itself should be an index).

        frame_flip_v
            Constant or mrc.Ref for a frame object property for whether to mirror vertically.
            Defaults to 0.

        frame_flip_h
            Constant or mrc.Ref for a frame object property for whether to mirror horizontally.
            Defaults to 0.
        """

        assert x_start in range( 0, self.width )
        assert y_start in range( 0, self.height )
        if frame_index is not None:
            fn_index = lambda fr: mrc.property_get( frame_index, fr )
        else:
            fn_index = lambda fr: fr if fr in range( 0, self.frame_count ) else None
        fn_flip_v = lambda fr: mrc.property_get( frame_flip_v, fr )
        fn_flip_h = lambda fr: mrc.property_get( frame_flip_h, fr )

        frames = []
        try:
            frame_iter = iter( frame )
            frames = [f for f in frame_iter]
        except TypeError:
            frames = [frame]

        if not width:
            width = self.width-x_start
        if not height:
            height = self.height-y_start

        stride = width*height

        def data_fetch( x, y, fr_obj ):
            fr = fn_index( fr_obj )
            if fr is None:
                return Transparent()
            if not ((0 <= x < self.width) and (0 <= y < self.height)):
                return Transparent()
            if fn_flip_h( fr_obj ):
                x = self.width - x - 1
            if fn_flip_v( fr_obj ):
                y = self.height - y - 1
            index = self.width*y + x
            p = self.source[stride*fr+index]
            if self.mask:
                p = p if self.mask[stride*fr+index] else None
            return self.palette[p] if p is not None else Transparent()

        for x in ansi.format_image_iter( data_fetch, x_start, y_start, width, height, frames, columns, downsample ):
            yield x
        return
    
    def print( self, *args, **kwargs ):
        for x in self.ansi_format_iter( *args, **kwargs ):
            print( x )

    @property
    def repr( self ):
        return '<{}: {} bytes, {}x{}>'.format( self.__class__.__name__, self.width*self.height, self.width, self.height )


class Planarizer( mrc.Transform ):
    """Class for converting between planar and chunky image data."""

    def __init__( self, bpp: int, width: int=None, height: int=None, plane_size: int=None, plane_padding: int=0, frame_offset: int=0, frame_stride: int=None, frame_count: int=1, row_planar_size: int=None, plane_order=None ):
        """Create a Planarizer instance.

        bpp
            Bits per pixel (aka. number of bitplanes).

        width
            Width of destination image in pixels.

        height
            Height of destination image in pixels.

        plane_size
            Size of the image data for a single plane in bytes. Default is (width*height//8). Can't be specified if width or height are defined.

        plane_padding
            Additional bytes per plane not used in the chunky data.

        frame_offset
            Start of the first frame of data. The frame controls are useful for storing multiple image frames sequentially with seperate sets of bitplanes per frame. They aren't required for multiple frames stored in the same larger set of bitplanes.

        frame_stride
            Bytes between the start of each frame. Default is bpp*(plane_size+plane_padding).

        frame_count
            Number of frames.
       
        row_planar_size
            Number of bytes per row-plane in a row-planar image. Default is to process a graphic-planar image without rows.

        plane_order
            List of integers describing how to order the bitplanes in chunky output, from least significant to most significant. Defaults to all planes sequential.            
        """
        self.bpp = bpp
        self.width = width
        self.height = height
        self.plane_size = plane_size
        self.plane_padding = plane_padding
        self.frame_offset = frame_offset
        self.frame_count = frame_count
        self.frame_stride = frame_stride
        self.row_planar_size = row_planar_size
        self.plane_order = plane_order


    def import_data( self, buffer: bytes, parent=None ):
        assert utils.is_bytes( buffer )

        # load in constructor properties
        bpp = mrc.property_get( self.bpp, parent )
        width = mrc.property_get( self.width, parent )
        height = mrc.property_get( self.height, parent )
        plane_size = mrc.property_get( self.plane_size, parent )
        plane_padding = mrc.property_get( self.plane_padding, parent )
        frame_offset = mrc.property_get( self.frame_offset, parent )
        frame_count = mrc.property_get( self.frame_count, parent )
        frame_stride = mrc.property_get( self.frame_stride, parent )
        row_planar_size = mrc.property_get( self.row_planar_size, parent )
        plane_order = mrc.property_get( self.plane_order, parent )


        assert (bpp >= 0) and (bpp <= 8)
        if (width or height):
            assert (width*height) % 8 == 0
            if plane_size:
                raise Exception( 'Can\'t define plane_size when either width or height is defined.' )
        elif plane_size is None and frame_count == 1:
            # for a single frame without a plane size, assume the buffer contains everything
            assert len( buffer ) % bpp == 0
            plane_size = len( buffer ) // bpp
        else:
            assert plane_size is not None
        assert (frame_count >= 1)

        if plane_size is None:
            plane_size = math.ceil( width*height/8 )

        if frame_count >= 2 and frame_stride is None:
            frame_stride = bpp*(plane_size+plane_padding)
        else:
            frame_stride = frame_stride if frame_stride is not None else 0

        if row_planar_size:
            assert row_planar_size >= 1
        
        if not plane_order:
            plane_order = range( bpp )
        else: 
            assert all( [y in range( bpp ) for y in plane_order] )
            assert len( plane_order ) == len( set( plane_order ) )

        # because frame_stride can potentially read past the buffer, only worry about measuring
        # the last n-1 strides + one frame
        assert len( buffer ) >= frame_offset + (frame_count-1)*frame_stride + bpp*plane_size


        # our output is going to be "chunky"; each byte is a pixel (8-bit or 256 colour mode)
        raw_image = bytearray( plane_size*frame_count )

        # the input is planar. this is a packed format found occasionally in old graphics hardware,
        # and in old image formats where space was paramount.
        # the trick is you can have less than 8 bits in your colourspace! 
        # e.g. if you only need 8 colours, you can get away with a 3-bit colourspace and save 62.5% space.
        # instead of each byte being a pixel, each byte stores 8 pixels worth of data for a single plane.
        # there is one plane per bit of colourspace, and the planes are stored one after another.
        
        # in order for the calculations to be fast, planar graphics are pretty much always divisible by 8.
        # we're going to abuse this and unpack our bitplanes using 64-bit integers.
        # let's make a big array of them.
        planes = array( 'Q', (0,)*(plane_size) )
        segment_size = plane_size+plane_padding
    
        for f in range( frame_count ):
            pointer = frame_offset+f*frame_stride
            for bi, b in enumerate( plane_order ):
                for i in range( plane_size ):
                    # for the first iteration, clear the plane
                    if bi==0:
                        planes[i] = 0

                    if row_planar_size is None:
                        address = pointer+b*segment_size+i
                    else:
                        address = pointer + (row_planar_size*bpp)*(i // row_planar_size) + row_planar_size*b + (i % row_planar_size)

                    # utils.unpack_bits is a helper method which converts a 1-byte bitfield
                    # into 8 bool bytes (i.e. 1 or 0) stored as a 64-bit int.
                    # we can effectively work on 8 chunky pixels at once!
                    # because the chunky pixels are bitfields, combining planes is an easy
                    # left shift (i.e. move all the bits up by [plane ID] places) and bitwise OR
                    planes[i] |= utils.unpack_bits( buffer[address] ) << bi
                    
            # check for endianness! for most intel and ARM chips the order of bytes in hardware is reversed,
            # so we need to flip it around for the bytes to be sequential.
            if sys.byteorder == 'little':
                planes.byteswap()

            # convert our planes array to bytes, and you have your chunky pixels
            raw_image[f*plane_size*8:(f+1)*plane_size*8] = planes.tobytes()

        if frame_count > 1:
            end_offset = frame_offset + frame_count*frame_stride
        else:
            bits = plane_size*8*bpp
            end_offset = frame_offset + (bits)//8 + (1 if (bits % 8) else 0)

        return mrc.TransformResult( payload=bytes( raw_image ), end_offset=end_offset )


    def export_data( self, buffer: bytes, parent=None ):
        assert utils.is_bytes( buffer )

        # load in constructor properties
        bpp = mrc.property_get( self.bpp, parent )
        width = mrc.property_get( self.width, parent )
        height = mrc.property_get( self.height, parent )
        plane_size = mrc.property_get( self.plane_size, parent )
        plane_padding = mrc.property_get( self.plane_padding, parent )
        frame_offset = mrc.property_get( self.frame_offset, parent )
        frame_count = mrc.property_get( self.frame_count, parent )
        frame_stride = mrc.property_get( self.frame_stride, parent )

        assert (bpp >= 0) and (bpp <= 8)
        if (width or height):
            assert (width*height) % 8 == 0
            if plane_size:
                raise Exception( 'Can\'t define plane_size when either width or height is defined.' )
        elif plane_size is None and frame_count == 1:
            # for a single frame without a plane size, assume the buffer contains everything
            assert len( buffer ) % bpp == 0
            plane_size = len( buffer ) // bpp
        else:
             assert plane_size is not None

        if not plane_size:
            plane_size = math.ceil( width*height/8 )

        assert (frame_count >= 1)
        if frame_count >= 2 and frame_stride is None:
            frame_stride = bpp*(plane_size+plane_padding)
        else:
            frame_stride = frame_stride if frame_stride is not None else 0

        if frame_count == 1:
            assert len( buffer ) >= frame_offset + plane_size*8 
        else:
            assert len( buffer ) >= frame_offset + frame_count*frame_stride

        # this method just does the opposite of the above; split chunky pixels back into planes.
        planes = array( 'Q' )
        segment_size = plane_size+plane_padding
        if frame_count == 1:
            raw_planes = bytearray( frame_offset+segment_size*bpp )
        else:
            raw_planes = bytearray( frame_offset+frame_count*frame_stride )
    
        for f in range( frame_count ):
            pointer = frame_offset+f*frame_stride
            planes = planes[0:0]
            # load our chunky pixels into the 64-bit int array
            planes.frombytes( buffer[f*plane_size*8:(f+1)*plane_size*8] )
            # check for endianness!
            if sys.byteorder == 'little':
                planes.byteswap()

            for b in range( bpp ):
                for i in range( plane_size ):
                    # for each group of 8 chunky pixels, use pack_bits to fill up 8 bits
                    # of the relevant bitplane
                    raw_planes[pointer+b*segment_size+i] = utils.pack_bits( (planes[i] >> b) )

        return mrc.TransformResult( payload=raw_planes )



