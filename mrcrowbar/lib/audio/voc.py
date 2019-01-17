"""File format classes for the Creative Voice audio format.

Sources:
http://www.shikadi.net/moddingwiki/VOC_Format
"""

from mrcrowbar.lib.audio import base as aud
from mrcrowbar import models as mrc
import enum


class VOCCodec( enum.IntEnum ):
    PCM_UINT8 = 0x00
    ADPCM_CREATIVE_4_8 = 0x01
    ADPCM_CREATIVE_3_8 = 0x02
    ADPCM_CREATIVE_2_8 = 0x03
    PCM_INT16 = 0x04
    PCM_ALAW = 0x06
    PCM_ULAW = 0x07


class VOCTypedSoundData( mrc.Block ):
    freq_divisor = mrc.UInt8( 0x00 )
    codec = mrc.UInt8( 0x01, enum=VOCCodec )
    data = mrc.Bytes( 0x02 )

    @property
    def sample_rate( self ):
        return 1000000 // (256 - self.freq_divisor)

    @property
    def signedness( self ):
        if self.codec == VOCCodec.PCM_UINT8:
            return 'unsigned'
        elif self.codec == VOCCodec.PCM_INT16:
            return 'signed'
        return None

    @property
    def sample_width( self ):
        if self.codec == VOCCodec.PCM_UINT8:
            return 1
        elif self.codec == VOCCodec.PCM_INT16:
            return 2
        return None



class VOCSoundData( mrc.Block ):
    data = mrc.Bytes( 0x00 )


class VOCSilence( mrc.Block ):
    length_raw = mrc.UInt16_LE( 0x00 )
    freq_divisor = mrc.UInt8( 0x00 )

    @property
    def length( self ):
        return self.length+1

    @property
    def sample_rate( self ):
        return 1000000 // (256 - self.freq_divisor)


class VOCMarker( mrc.Block ):
    value = mrc.UInt16_LE( 0x00 )


class VOCText( mrc.Block ):
    text = mrc.CString( 0x00 )


class VOCRepeatStart( mrc.Block ):
    count_raw = mrc.UInt16_LE( 0x00 )

    @property
    def count( self ):
        return self.count_raw + 1


class VOCRepeatEnd( mrc.Block ):
    pass


class VOCExtra( mrc.Block ):
    freq_divisor = mrc.UInt16_LE( 0x00 )
    codec = mrc.UInt8( 0x02, enum=VOCCodec )
    channels_raw = mrc.UInt8( 0x03 )

    @property
    def channels( self ):
        return self.channels_raw + 1

    @property
    def sample_rate( self ):
        return 256000000 // ((self.channels)*(65536 - self.freq_divisor))


class VOCSoundData12( mrc.Block ):
    sample_rate = mrc.UInt32_LE( 0x00 )
    sample_bits = mrc.UInt8( 0x04 )
    channels_raw = mrc.UInt8( 0x05 )
    codec = mrc.UInt16_LE( 0x06 )
    reserved = mrc.Const( mrc.UInt32_LE( 0x08 ), 0 )
    data = mrc.Bytes( 0x0c )

    @property
    def channels( self ):
        return self.channels_raw + 1


VOC_CHUNK_MAP = {
    0x01: VOCTypedSoundData,
    0x02: VOCSoundData,
    0x03: VOCSilence,
    0x04: VOCMarker,
    0x05: VOCText,
    0x06: VOCRepeatStart,
    0x07: VOCRepeatEnd,
    0x08: VOCExtra,
    0x09: VOCSoundData12,
}


class VOC( mrc.Block ):
    magic = mrc.Const( mrc.Bytes( 0x00, length=0x14 ), b'Creative Voice File\x1a' )
    header_size = mrc.UInt16_LE( 0x14 )
    version = mrc.Bytes( 0x16, length=2 )
    checksum = mrc.Bytes( 0x18, length=2 )

    chunks = mrc.ChunkField( VOC_CHUNK_MAP, 0x1a, stream=True, chunk_id_field=mrc.UInt8, chunk_length_field=mrc.UInt24_LE, stream_end=b'\x00' )

    @property
    def audio_chunk( self ):
        # TODO: this is pretty cheap theatrics
        test = [x for x in self.chunks if x.id == 1]
        if test:
            return test[0].obj
        return None

    def __init__( self, *args, **kwargs ):
        self.audio = aud.Wave( self, mrc.Ref( 'audio_chunk.data' ), channels=1, sample_rate=mrc.Ref( 'audio_chunk.sample_rate' ), format_type=int, field_size=mrc.Ref( 'audio_chunk.sample_width' ), signedness=mrc.Ref( 'audio_chunk.signedness' ),  endian='little' )
        super().__init__( *args, **kwargs )
