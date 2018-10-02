#!/usr/bin/python3

"""File format classes for the Commander Keen: Invasion of the Vorticons engine (DOS, 1991)

Sources:
RLE compressor
http://www.shikadi.net/moddingwiki/Keen_1-3_RLE_compression

RLEW compressor
http://www.shikadi.net/moddingwiki/RLEW_compression

LZW compressor
http://www.shikadi.net/moddingwiki/LZW_Compression
(Special thanks to Fleexy)

EGA header
http://www.shikadi.net/moddingwiki/Commander_Keen_EGA_Header

Level format
http://www.shikadi.net/moddingwiki/Commander_Keen_1-3_Level_format
"""

import itertools
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.images import base as img
from mrcrowbar import utils


class RLECompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        final_length = utils.from_uint32_le( buffer[0:4] )
        i = 4
        out = bytearray()
        while (len( out ) < final_length):
            byte = buffer[i]
            if byte >= 128:
                out.extend( buffer[i+1:i+byte-126] )
                i += byte-126
            else:
                out.extend( buffer[i+1:i+2]*(byte+3) )
                i += 2

        return mrc.TransformResult( payload=bytes( out ), end_offset=i )


class RLEWCompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        final_length = utils.from_uint32_le( buffer[0:4] )
        i = 4
        out = bytearray()
        while (len( out ) < final_length):
            word = buffer[i:i+2]
            if word == b'\xfe\xfe':
                count = utils.from_uint16_le( buffer[i+2:i+4] )
                data = buffer[i+4:i+6]
                out.extend( data*count )
                i += 6
            else:
                out.extend( word )
                i += 2

        return mrc.TransformResult( payload=bytes( out ), end_offset=i )


class LZWCompressor( mrc.Transform ):

    def import_data( self, buffer, parent=None ):
        decomp_size = utils.from_uint32_le( buffer[:4] )
        max_bits = utils.from_uint16_le( buffer[4:6] )      # should be 12

        lookup = [bytes((i,)) for i in range( 256 )]
        lookup.append( None )   # 256: error
        lookup.append( None )   # 257: end of data

        output = bytearray()

        bs = utils.BitReader( buffer, 6, bits_reverse=True, output_reverse=True )
        state = {'usebits': 9}

        def add_to_lookup( state, entry ):
            if len( lookup ) < (1 << max_bits):
                logger.debug( 'lookup[{}] = {}'.format( len( lookup ), entry ) )
                lookup.append( entry )
                if len( lookup ) == (1 << state['usebits'])-1:
                    state['usebits'] = min( state['usebits']+1, max_bits )
                    logger.debug( 'usebits = {}'.format(state['usebits']) )
            return
                    

        fcode = bs.get_bits( state['usebits'] )
        match = lookup[fcode]
        logger.debug( 'fcode={},match={}'.format( fcode, match ) )
        output.extend( match )
        while True:
            ncode = bs.get_bits( state['usebits'] )
            logger.debug( 'ncode={}'.format( ncode ) )
            if ncode == 257:
                # end of data
                break
            elif ncode == 256:
                # error
                raise Exception( 'Found error code, data is not valid' )
            elif ncode < len( lookup ):
                nmatch = lookup[ncode]
            else:
                nmatch = match+match[0:1]
            logger.debug( 'match={}'.format(match) )
            logger.debug( 'nmatch={}'.format(nmatch) )
            output.extend( nmatch )

            # add code to lookup 
            add_to_lookup( state, match+nmatch[0:1] )
            match = nmatch

        if len( output ) != decomp_size:
            logger.warning( '{}: was expecting data of size {}, got data of size {} instead'.format( self, decomp_size, len( output ) ) )

        return mrc.TransformResult( payload=bytes( output ), end_offset=len( buffer ) )



class EGAHeader( mrc.Block ):
    _egalatch = None           # should be manually pointed at the relevant EGALatch object

    latch_plane_size    = mrc.UInt32_LE( 0x00 )
    sprite_plane_size   = mrc.UInt32_LE( 0x04 )
    image_data_start    = mrc.UInt32_LE( 0x08 )
    sprite_data_start   = mrc.UInt32_LE( 0x0c )
    tile8_count         = mrc.UInt16_LE( 0x10 )
    tile8_offset        = mrc.UInt32_LE( 0x12 )
    tile32_count        = mrc.UInt16_LE( 0x16 )
    tile32_offset       = mrc.UInt32_LE( 0x18 )
    tile16_count        = mrc.UInt16_LE( 0x1c )
    tile16_offset       = mrc.UInt32_LE( 0x1e )
    bitmap_count        = mrc.UInt16_LE( 0x22 )
    bitmap_offset       = mrc.UInt32_LE( 0x24 )
    sprite_count        = mrc.UInt16_LE( 0x28 )
    sprite_offset       = mrc.UInt32_LE( 0x2a )
    latch_compressed    = mrc.Bits( 0x2e, 0b00000010 )
    sprite_compressed   = mrc.Bits( 0x2e, 0b00000001 )


class EGAHeaderBitmapRef( mrc.Block ):
    width_raw           = mrc.UInt16_LE( 0x00 )
    height              = mrc.UInt16_LE( 0x02 )
    location            = mrc.UInt32_LE( 0x04 )
    name                = mrc.Bytes( 0x08, length=8 )


class EGAHeaderSpriteRef( mrc.Block ):
    width_raw           = mrc.UInt16_LE( 0x00 )
    height              = mrc.UInt16_LE( 0x02 )
    prog_offset         = mrc.UInt16_LE( 0x04 )
    location_raw        = mrc.UInt16_LE( 0x06 )
    hitbox_left         = mrc.UInt16_LE( 0x08 )
    hitbox_top          = mrc.UInt16_LE( 0x0a )
    hitbox_right        = mrc.UInt16_LE( 0x0c )
    httbox_bottom       = mrc.UInt16_LE( 0x0e )
    name                = mrc.Bytes( 0x10, length=12 )
    horiz_offset        = mrc.UInt16_LE( 0x1c )
    vert_offset         = mrc.UInt16_LE( 0x1e )

    @property
    def location( self ):
        return self.location_raw*16


class EGATile8( mrc.Block ):
    image_data = mrc.Bytes( 0x00, length=mrc.Ref( '_parent.tile8_size' ) )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.tiles = img.IndexedImage( 
                        self,
                        width=8, height=8,
                        source=mrc.Ref( 'image_data' ),
                        frame_count=mrc.Ref( '_parent._parent._egahead.tile8_count' ),
                        palette=ibm_pc.EGA_DEFAULT_PALETTE
                    )


class EGATile16( mrc.Block ):
    image_data = mrc.Bytes( 0x00, length=mrc.Ref( '_parent.tile16_size' ) )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.tiles = img.IndexedImage( 
                        self,
                        width=16, height=16,
                        source=mrc.Ref( 'image_data' ),
                        frame_count=mrc.Ref( '_parent._parent._egahead.tile16_count' ),
                        palette=ibm_pc.EGA_DEFAULT_PALETTE
                    )

class EGATile32( mrc.Block ):
    image_data = mrc.Bytes( 0x00, length=mrc.Ref( '_parent.tile32_size' ) )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.tiles = img.IndexedImage( 
                        self,
                        width=32, height=32,
                        source=mrc.Ref( 'image_data' ),
                        frame_count=mrc.Ref( '_parent._parent._egahead.tile32_count' ),
                        palette=ibm_pc.EGA_DEFAULT_PALETTE
                    )


class EGATileStore( mrc.Block ):
    data = mrc.Bytes( 0x00, transform=img.Planarizer(
                        bpp=4,
                        plane_size=mrc.Ref( '_parent._egahead.latch_plane_size' )
                    ) )

    tile8 =  mrc.StoreRef( EGATile8,  mrc.Ref( 'store' ), mrc.Ref( 'tile8_offset' ),  mrc.Ref( 'tile8_size' ) )
    tile16 = mrc.StoreRef( EGATile16, mrc.Ref( 'store' ), mrc.Ref( 'tile16_offset' ), mrc.Ref( 'tile16_size' ) )
    tile32 = mrc.StoreRef( EGATile32, mrc.Ref( 'store' ), mrc.Ref( 'tile32_offset' ), mrc.Ref( 'tile32_size' ) )

    def __init__( self, *args, **kwargs ):
        self.store = mrc.Store( self, mrc.Ref( 'data' ) )
        super().__init__( *args, **kwargs )
        
    @property
    def tile8_offset( self ):
        return self._parent._egahead.tile8_offset*8

    @property
    def tile16_offset( self ):
        return self._parent._egahead.tile16_offset*8

    @property
    def tile32_offset( self ):
        return self._parent._egahead.tile32_offset*8

    @property
    def tile8_size( self ):
        return self._parent._egahead.tile8_count*8*8

    @property
    def tile16_size( self ):
        return self._parent._egahead.tile16_count*16*16

    @property
    def tile32_size( self ):
        return self._parent._egahead.tile16_count*32*32


class EGALatch( mrc.Block ):
    _egahead            = None

    tilestore           = mrc.BlockField( EGATileStore, 0x00 )


class EGALatchComp( mrc.Block ):
    _egahead            = None

    tilestore           = mrc.BlockField( EGATileStore, 0x00, transform=LZWCompressor() )
    

class SoundHeader( mrc.Block ):
    magic               = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'SND\x00' )
    size                = mrc.UInt16_LE( 0x04 )
    unknown_1           = mrc.UInt16_LE( 0x06 )
    count               = mrc.UInt16_LE( 0x08 )
    padding             = mrc.Const( mrc.Bytes( 0x0a, length=6 ), b'\x00'*6 )


class SoundRef( mrc.Block ):
    offset              = mrc.UInt16_LE( 0x00 )
    priority            = mrc.UInt8( 0x02 )
    rate                = mrc.UInt8( 0x03 )
    name                = mrc.Bytes( 0x04, 0x0c )


class PreviewCompressor( mrc.Transform ):
    rle = RLECompressor()
    # each plane is stored with 192 bytes padding at the end
    plan = img.Planarizer( bpp=4, width=320, height=200, plane_padding=192 ) 
    
    def import_data( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        stage_1 = self.rle.import_data( buffer )
        stage_2 = self.plan.import_data( stage_1.payload )
        return mrc.TransformResult( payload=stage_2.payload, end_offset=stage_1.end_offset )


class Preview( mrc.Block ):
    image_data          = mrc.Bytes( 0x0000, transform=PreviewCompressor() )

    def __init__( self, *args, **kwargs ):
        mrc.Block.__init__( self, *args, **kwargs )
        self.image = img.IndexedImage( self, width=320, height=200, palette=ibm_pc.EGA_DEFAULT_PALETTE, source=mrc.Ref( 'image_data' ) )




class Level( mrc.Unknown ):
    pass


class LevelHeader( mrc.Block ):
    width           = mrc.UInt16_LE( 0x00 )
    height          = mrc.UInt16_LE( 0x02 )
    plane_count     = mrc.UInt16_LE( 0x04, default=2 )
    unknown_1       = mrc.Bytes( 0x06, length=4 )
    ted_vars        = mrc.Bytes( 0x0a, length=4 )
    plane_size      = mrc.UInt16_LE( 0x0e )
    unknown_2       = mrc.Bytes( 0x10, length=16 )

    @property
    def plane_size_calc( self ):
        size = 2 * self.width * self.height
        return size + ((16-size)%16)


class LevelTile( mrc.Block ):
    tile_id         = mrc.UInt16_LE( 0x00 )


class ScoresItems( mrc.Block ):
    joystick        = mrc.UInt16_LE( 0x00, range( 0, 1 ) )
    battery         = mrc.UInt16_LE( 0x02, range( 0, 1 ) )
    vacuum          = mrc.UInt16_LE( 0x04, range( 0, 1 ) )
    liquor          = mrc.UInt16_LE( 0x06, range( 0, 1 ) )


class ScoresName( mrc.Block ):
    name            = mrc.Bytes( 0x00, length=13 )


class Scores( mrc.Block ):
    values          = mrc.UInt32_LE( 0x00, length=7 )
    items           = mrc.BlockField( ScoresItems, 0x1c, count=7 )
    num_cities      = mrc.UInt16_LE( 0x54, length=7, range=range( 0, 9 ) )
    unknown_1       = mrc.Bytes( 0x62, length=14 )
    names           = mrc.BlockField( ScoresName, 0x70, count=7 )
    term            = mrc.Const( mrc.Bytes( 0xcb, length=1 ), b'\x00' )


class Loader( mrc.Loader ):
    _SEP = mrc.Loader._SEP

    _KEEN_FILE_CLASS_MAP = {
        _SEP+'(EGAHEAD).CK([1-3])$': EGAHeader,
        _SEP+'(EGALATCH).CK(1)$': EGALatchComp,
        _SEP+'(EGALATCH).CK([2-3])$': EGALatch,
        _SEP+'(FINALE).CK([1-3])$': Preview,
        _SEP+'(LEVEL)([0-9]{2}).CK([1-3])$': Level,
        _SEP+'(PREVIEW)([2-3]).CK([1-3])$': Preview,
        _SEP+'(SCORES).CK([1-3])$': Scores,
    }

    _KEEN_DEPS = [
        (_SEP+'(EGALATCH).CK([1-3])$', _SEP+'(EGAHEAD).CK([1-3])$', ('EGAHEAD', '{1}'), '_egahead')
    ]


    def __init__( self ):
        super().__init__( self._KEEN_FILE_CLASS_MAP, self._KEEN_DEPS )

    def post_load( self ): 
        pass
