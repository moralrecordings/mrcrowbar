from mrcrowbar.colour import TEST_PALETTE
from mrcrowbar import models as mrc

from mrcrowbar.lib.images import base as img


class TIMFile( mrc.Block ):
    file_name = mrc.Bytes( length=13 )
    size = mrc.UInt32_LE()
    data = mrc.Bytes( length=mrc.Ref( "size" ) )

    @property
    def repr( self ):
        return self.file_name.split( b"\x00" )[0].decode( "utf8" )


class ResourceTIM( mrc.Block ):
    raw_data = mrc.Bytes()

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.store = mrc.Store( self, mrc.Ref( "raw_data" ) )


class TIMFileEntry( mrc.Block ):
    _file = mrc.StoreRef(
        TIMFile, mrc.Ref( "_parent._resource.store" ), mrc.Ref( "offset" )
    )

    name_hash = mrc.Int32_LE()
    offset = mrc.UInt32_LE()


class TIMFileStruct( mrc.Block ):
    _resource = None  # replace with the ResourceTIM object

    file_name = mrc.Bytes( length=13 )
    entry_count = mrc.UInt16_LE()
    entries = mrc.BlockField( TIMFileEntry, count=mrc.Ref( "entry_count" ) )


class ResourceMapTIM( mrc.Block ):
    hash_index = mrc.Bytes( length=4 )
    file_count = mrc.UInt16_LE()
    files = mrc.BlockField( TIMFileStruct, count=mrc.Ref( "file_count" ) )


class BitmapFrame( mrc.Block ):
    width = mrc.UInt16_LE()
    height = mrc.UInt16_LE()
    unk1 = mrc.UInt8()
    size = mrc.UInt32_LE()
    image_data = mrc.Bytes( length=mrc.Ref( "size" ) )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage(
            self,
            width=mrc.Ref( "width" ),
            height=mrc.Ref( "height" ),
            source=mrc.Ref( "image_data" ),
            palette=mrc.Ref( "_parent._parent._palette" ),
        )


class BitmapData( mrc.Block ):
    unk1 = mrc.UInt16_LE()
    frame_count = mrc.UInt16_LE()
    frame_offsets = mrc.UInt32_LE( count=mrc.Ref( "frame_count" ) )
    raw_data = mrc.Bytes()

    @property
    def base_offset( self ):
        return -self.get_field_end_offset( "frame_offsets" ) - 8

    def __init__( self, *args, **kwargs ):
        self.store = mrc.LinearStore(
            parent=self,
            source=mrc.Ref( "raw_data" ),
            block_klass=BitmapFrame,
            offsets=mrc.Ref( "frame_offsets" ),
            base_offset=mrc.Ref( "base_offset" ),
        )
        super().__init__( *args, **kwargs )


class BitmapTIM( mrc.Block ):
    magic = mrc.Const( mrc.Bytes( length=4 ), b"BMP:" )
    size = mrc.UInt32_LE()
    bitmap_data = mrc.BlockField( BitmapData, length=mrc.Ref( "size" ) )

    # replace this at load time
    _palette = TEST_PALETTE
