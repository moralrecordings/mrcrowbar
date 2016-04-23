#!/usr/bin/python3

"""File format classes for the Commander Keen: Invasion of the Vorticons engine (DOS, 1991)"""

import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.images import base as img
from mrcrowbar import utils

# source: http://www.shikadi.net/moddingwiki/Keen_1-3_RLE_compression

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

        result = {
            'payload': bytes( out ),
            'end_offset': i
        }

        return result

# source: http://www.shikadi.net/moddingwiki/RLEW_compression

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

        result = {
            'payload': bytes( out ),
            'end_offset': i
        }

        return result



# source: http://www.shikadi.net/moddingwiki/Commander_Keen_EGA_Header

class EGAHead( mrc.Block ):
    latch_plane_size    = mrc.UInt32_LE( 0x00 )
    sprite_plane_size   = mrc.UInt32_LE( 0x04 )
    image_data_start    = mrc.UInt32_LE( 0x08 )
    sprite_data_start   = mrc.UInt32_LE( 0x0c )
    font_count          = mrc.UInt16_LE( 0x10 )
    font_offset         = mrc.UInt32_LE( 0x12 )
    unknown_1           = mrc.UInt16_LE( 0x16 )
    unknown_2           = mrc.UInt32_LE( 0x18 )
    tile_count          = mrc.UInt16_LE( 0x1a )
    tile_offset         = mrc.UInt32_LE( 0x1c )
    bitmap_count        = mrc.UInt16_LE( 0x22 )
    bitmap_offset       = mrc.UInt32_LE( 0x24 )
    sprite_count        = mrc.UInt16_LE( 0x28 )
    sprite_offset       = mrc.UInt32_LE( 0x2a )
    latch_compressed    = mrc.Bits( 0x2e, 0b00000010 )
    sprite_compressed   = mrc.Bits( 0x2e, 0b00000001 )


class EGAHeadBitmapRef( mrc.Block ):
    width_raw           = mrc.UInt16_LE( 0x00 )
    height              = mrc.UInt16_LE( 0x02 )
    location            = mrc.UInt32_LE( 0x04 )
    name                = mrc.CStringN( 0x08, 8 )


class EGAHeadSpriteRef( mrc.Block ):
    width_raw           = mrc.UInt16_LE( 0x00 )
    height              = mrc.UInt16_LE( 0x02 )
    prog_offset         = mrc.UInt16_LE( 0x04 )
    location_raw        = mrc.UInt16_LE( 0x06 )
    hitbox_left         = mrc.UInt16_LE( 0x08 )
    hitbox_top          = mrc.UInt16_LE( 0x0a )
    hitbox_right        = mrc.UInt16_LE( 0x0c )
    httbox_bottom       = mrc.UInt16_LE( 0x0e )
    name                = mrc.CStringN( 0x10, 12 )
    horiz_offset        = mrc.UInt16_LE( 0x1c )
    vert_offset         = mrc.UInt16_LE( 0x1e )

    @property
    def location( self ):
        return self.location_raw*16


class PreviewCompressor( mrc.Transform ):
    rle = RLECompressor()
    # each plane is stored with 192 bytes padding at the end
    plan = img.Planarizer( 320, 200, 4, plane_padding=192 ) 
    
    def import_data( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        stage_1 = self.rle.import_data( buffer )
        stage_2 = self.plan.import_data( stage_1['payload'] )
        result = {
            'payload': stage_2['payload'],
            'end_offset': stage_1['end_offset']
        }
        return result


class Preview( mrc.Block ):
    image_data          = mrc.Bytes( 0x0000, transform=PreviewCompressor() )

    def __init__( self, *args, **kwargs ):
        mrc.Block.__init__( self, *args, **kwargs )
        self.image = img.IndexedImage( self, width=320, height=200, palette=ibm_pc.EGA_DEFAULT_PALETTE, source=mrc.Ref( 'image_data' ) )


# source: http://www.shikadi.net/moddingwiki/Commander_Keen_1-3_Level_format

class Level( mrc.Block ):
    pass


class LevelHeader( mrc.Block ):
    width           = mrc.UInt16_LE( 0x00 )
    height          = mrc.UInt16_LE( 0x02 )
    plane_count     = mrc.Check( mrc.UInt16_LE( 0x04 ), 2 )
    plane_size      = mrc.UInt16_LE( 0x0e )


class LevelTile( mrc.Block ):
    tile_id         = mrc.UInt16_LE( 0x00 )


class Loader( mrc.Loader ):
    SEP = mrc.Loader.SEP

    KEEN_FILE_CLASS_MAP = {
        SEP+'(EGAHEAD).CK[1-3]$': EGAHead,
        SEP+'(FINALE).CK[1-3]$': Preview,
        SEP+'(PREVIEW)([2-3]).CK1': Preview
    }

    def __init__( self ):
        super( Loader, self ).__init__( self.KEEN_FILE_CLASS_MAP )
