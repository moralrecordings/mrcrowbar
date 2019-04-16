from mrcrowbar import models as mrc
from mrcrowbar.utils import from_uint32_be as Tag, to_uint32_be as TagB

class RIFF( mrc.Block ):
    CHUNK_MAP = {}

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'RIFF' )
    size = mrc.UInt32_LE( 0x04 )
    form_type = mrc.Bytes( 0x08, length=4 )
    stream = mrc.ChunkField( mrc.Ref( 'CHUNK_MAP' ), 0x0c,
                             length=mrc.Ref( 'size' ), chunk_id_field=mrc.UInt32_BE,
                             chunk_length_field=mrc.UInt32_LE, alignment=2,
                             default_klass=mrc.Unknown )


class RIFXMap( mrc.Block ):
    CHUNK_MAP = {}
    form_type = mrc.Bytes( 0x00, length=4 )
    stream = mrc.ChunkField( mrc.Ref( 'CHUNK_MAP' ), 0x04,
                             chunk_id_field=mrc.UInt32_P,
                             chunk_length_field=mrc.UInt32_P, alignment=2,
                             fill=b'',
                             default_klass=mrc.Unknown )


class RIFX( mrc.Block ):
    _endian = 'big'
    CHUNK_MAP_CLASS = RIFXMap

    magic = mrc.Const( mrc.UInt32_P( 0x00 ), Tag( b'RIFX' ) )
    size = mrc.UInt32_P( 0x04 )
    map = mrc.BlockField( mrc.Ref( 'CHUNK_MAP_CLASS' ), 0x08, length=mrc.Ref( 'size' ) )
    


class XFIR( RIFX ):
    _endian = 'little'

