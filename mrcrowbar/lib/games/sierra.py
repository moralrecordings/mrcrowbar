from mrcrowbar import models as mrc


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
