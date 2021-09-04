from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img
from mrcrowbar.utils import from_uint32_be as Tag, to_uint32_be as TagB


class RIFF( mrc.Block ):
    CHUNK_MAP = {}

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b"RIFF" )
    size = mrc.UInt32_LE( 0x04 )
    form_type = mrc.Bytes( 0x08, length=4 )
    stream = mrc.ChunkField(
        mrc.Ref( "CHUNK_MAP" ),
        0x0c,
        length=mrc.Ref( "size" ),
        id_field=mrc.UInt32_BE,
        length_field=mrc.UInt32_LE,
        alignment=2,
        default_klass=mrc.Unknown,
    )


class RIFXMap( mrc.Block ):
    CHUNK_MAP = {}
    form_type = mrc.Bytes( 0x00, length=4 )
    stream = mrc.ChunkField(
        mrc.Ref( "CHUNK_MAP" ),
        0x04,
        id_field=mrc.UInt32_P,
        length_field=mrc.UInt32_P,
        alignment=2,
        fill=b"",
        default_klass=mrc.Unknown,
    )


class RIFX( mrc.Block ):
    _endian = "big"
    CHUNK_MAP_CLASS = RIFXMap

    magic = mrc.Const( mrc.UInt32_P( 0x00 ), Tag( b"RIFX" ) )
    size = mrc.UInt32_P( 0x04 )
    map = mrc.BlockField( mrc.Ref( "CHUNK_MAP_CLASS" ), 0x08, length=mrc.Ref( "size" ) )


class XFIR( RIFX ):
    _endian = "little"


# source: Palette File Format - https://www.aelius.com/njh/wavemetatools/doc/riffmci.pdf
class PALEntry( img.Colour ):
    r_raw = mrc.UInt8()
    g_raw = mrc.UInt8()
    b_raw = mrc.UInt8()
    flags = mrc.UInt8()

    @property
    def r( self ) -> float:
        return self.r_raw / 255

    @r.setter
    def r( self, value: float ) -> None:
        self.r_raw = round( value * 255 )

    @property
    def g( self ) -> float:
        return self.g_raw / 255

    @g.setter
    def g( self, value: float ) -> None:
        self.g_raw = round( value * 255 )

    @property
    def b( self ) -> float:
        return self.b_raw / 255

    @b.setter
    def b( self, value: float ) -> None:
        self.b_raw = round( value * 255 )


class PALData( mrc.Block ):
    version = mrc.UInt16_LE()
    entry_count = mrc.UInt16_LE()
    entries = mrc.BlockField( PALEntry, count=mrc.Ref( 'entry_count' ) )


class PAL( RIFF ):
    CHUNK_MAP = {Tag( b'data' ): PALData}

    form_type = mrc.Const( mrc.Bytes( 0x08, length=4 ), b'PAL ' )
