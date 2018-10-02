#!/usr/bin/python3

"""File format classes for the Secret Agent engine (DOS, 1992)

Sources:
ProGraphx tileset format
http://www.shikadi.net/moddingwiki/ProGraphx_Toolbox_tileset_format

Secret Agent encryption
http://www.shikadi.net/moddingwiki/Secret_Agent_encryption
"""

from mrcrowbar import models as mrc
from mrcrowbar import utils
from mrcrowbar.lib.hardware import ibm_pc 
from mrcrowbar.lib.images import base as img


class SAMEncryption( mrc.Transform ):
    KEY = b'Copyright 1991 Peder Jungck\x00'

    def __init__( self, length=None ):
        self.length = length

    def import_data( self, buffer, parent=None ):
        limit = len( buffer ) if not self.length else min( len( buffer ), self.length )
        payload = bytes( [utils.BYTE_REVERSE[c] ^ self.KEY[i%len( self.KEY )]
                            for i, c in enumerate( buffer[:limit] )] )
        return mrc.TransformResult( payload=payload, end_offset=limit )

    def export_data( self, buffer, parent=None ):
        payload = bytes( [utils.BYTE_REVERSE[c ^ self.KEY[i%len( self.KEY )]]
                            for i, c in enumerate( buffer )] )
        return mrc.TransformResult( payload=payload )


class SAMTileset16( mrc.Block ):
    count = mrc.UInt8( 0x00 )
    width_raw = mrc.UInt8( 0x01 )
    height = mrc.UInt8( 0x02 )
    mask_data = mrc.Bytes( 0x03, 
                        length=0x1f7d, 
                        transform=img.Planarizer(
                            bpp=5, 
                            plane_size=mrc.Ref( 'plane_size' ),
                            row_planar_size=1,
                            plane_order=(0,)
                        ) )
    image_data = mrc.Bytes( 0x03, 
                        length=0x1f7d, 
                        transform=img.Planarizer(
                            bpp=5, 
                            plane_size=mrc.Ref( 'plane_size' ),
                            row_planar_size=1,
                            plane_order=(1,2,3,4)
                        ) )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage( 
                        self,
                        width=mrc.Ref( 'width' ),
                        height=mrc.Ref( 'height' ),
                        source=mrc.Ref( 'image_data' ),
                        frame_count=mrc.Ref( 'count' ),
                        palette=ibm_pc.EGA_DEFAULT_PALETTE,
                        mask=mrc.Ref( 'mask_data' )
                    )
        

    @property
    def plane_size( self ):
        return self.count*self.width_raw*self.height
    
    @property
    def width( self ):
        return self.width_raw*8


class SAMGfx16( mrc.Block ):
    tilesets = mrc.BlockField( SAMTileset16, 0x00, transform=SAMEncryption( length=0x1f80 ) )


class SAMTileset8( mrc.Block ):
    count = mrc.UInt8( 0x00 )
    width_raw = mrc.UInt8( 0x01 )
    height = mrc.UInt8( 0x02 )
    mask_data = mrc.Bytes( 0x03, 
                        length=0x7fd, 
                        transform=img.Planarizer(
                            bpp=5, 
                            plane_size=mrc.Ref( 'plane_size' ),
                            row_planar_size=1,
                            plane_order=(0,)
                        ) )
    image_data = mrc.Bytes( 0x03, 
                        length=0x7fd, 
                        transform=img.Planarizer(
                            bpp=5, 
                            plane_size=mrc.Ref( 'plane_size' ),
                            row_planar_size=1,
                            plane_order=(1,2,3,4)
                        ) )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage( 
                        self,
                        width=mrc.Ref( 'width' ),
                        height=mrc.Ref( 'height' ),
                        source=mrc.Ref( 'image_data' ),
                        frame_count=mrc.Ref( 'count' ),
                        palette=ibm_pc.EGA_DEFAULT_PALETTE
                    )
        self.mask = img.IndexedImage( 
                        self,
                        width=mrc.Ref( 'width' ),
                        height=mrc.Ref( 'height' ),
                        source=mrc.Ref( 'mask_data' ),
                        frame_count=mrc.Ref( 'count' ),
                        palette=ibm_pc.EGA_DEFAULT_PALETTE
                    )

    @property
    def plane_size( self ):
        return self.count*self.width_raw*self.height
    
    @property
    def width( self ):
        return self.width_raw*8


class SAMGfx8( mrc.Block ):
    tilesets = mrc.BlockField( SAMTileset8, 0x00, transform=SAMEncryption( length=0x800 ) )


class Loader( mrc.Loader ):
    _SEP = mrc.Loader._SEP

    _SAM_FILE_CLASS_MAP = {
        _SEP+'(SAM)([1-3]).(APO|CRD|END|TTL)$': None,
        _SEP+'(SAM)([1-3])0(1).(GFX)$': SAMGfx16,
        _SEP+'(SAM)([1-3])0(2).(GFX)$': SAMGfx8,
        _SEP+'(SAM)([1-3])0(3).(GFX)$': None,
        _SEP+'(SAM)([1-3])0([1-3])E.(SND)$': None,
    }

    def __init__( self ):
        super().__init__( self._SAM_FILE_CLASS_MAP )

    def post_load( self ):

        #for key, obj in file_map.items():
        #    pass
        pass
