from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img
from mrcrowbar.lib.audio import base as aud
from mrcrowbar import utils

# taken from KNPS.DLL at offset 0x13772 (1236:0372), len 0x400

KLIK_PALETTE_RAW =  '00000000800000000080000080800000000080008000800000808000c0c0c000'\
                    'c0dcc000a6caf000ffa70004d7870004b36b07048b4f07046737070443230704'\
                    '27002f043b003f044f004f04630057047300570483005b0497005704a7004f04'\
                    'b7004704cb003b04cf002f04d3001f04db001304df000704e3000004e7130004'\
                    'ef230004f3330004f7430004ff570004ff630004ff6f0004ff7f0004ff8b0004'\
                    'ff970004ffa30004ffaf0004ffbf0004ffcb0004ffd70004ffe30004ffef0004'\
                    'ffff0004efff0004dfff0004cfff0004bfff0004afff00049fff00048fff0004'\
                    '7fff00046fff00045fff00044fff00043fff00042fff00041fff00040fff0004'\
                    '00ff000400f3000400e7000400df000400d3000400c7000400bf000400b30004'\
                    '00a70004009b0004008f000400830004007b0004006f000400630004005b0004'\
                    '00530004005b070400670b0400731304007b1f040087270400933704009b4304'\
                    '00a7530400b3630400bb730400c7870400d39f0400dfb30400e7cb0400f3e304'\
                    '00ffff0400e7fb0400d3f70400bbf30400a7ef040093e704007fe304006fdf04'\
                    '005bdb04004bd7040037d3040027cf040017cb040007c7040000c3040f00bf04'\
                    '1b00bb043300b3044b00ab045f00a3046f009b047f0093048b00870483006b04'\
                    '7b0053048b0063049b007304ab008704bb009b04cb00b304db00cb04eb00e304'\
                    'ff00ff04ff00f304ff00e704ff00db04ff00cf04ff00c704ff00bb04ff00af04'\
                    'ff00a304ff009b04ff008f04ff008304ff007704ff006b04ff006304ff005704'\
                    'ff004b04ff003f04ff003704ff002b04ff001f04ff001304ff000704ff000004'\
                    'ffffff04efefef04dfdfdf04cfcfcf04bfbfbf04afafaf049f9f9f048f8f8f04'\
                    '7f7f7f046f6f6f045f5f5f044f4f4f043f3f3f042f2f2f041f1f1f040f0f0f04'\
                    '00000004fff3e704f7e3d304efd7bf04e7c7ab04dfbb9b04d7af8b04cfa37b04'\
                    'c7976b04bf8b5f04b77f4f04af774304a76b37049f632f04975723048f4f1b04'\
                    '8747130400000004fb000004ef000704e3000f04d7001704cf001b04c3002304'\
                    'b7002704ab002b04a3002f0497002f048b00330483003304770033046b003304'\
                    '5f002f0457002f040000bf04000097040000730400005b0400003f0400000004'\
                    'ff003b04ff1f6304ff438f04ff639f04ff87bf04ffa7cf04ffcbff0487471304'\
                    '733b0f0463330b04532b0b0443230704331b07041f0f00040f07000400000004'\
                    '87c3d30467abbf044b9baf042f879b041b738b040b63770400536704003f4f04'\
                    '002f3b04ff00ff04000000040000000400000004000000040000000400000004'\
                    '000000040000000400000004000000040000000400000004fffbf000a0a0a400'\
                    '80808000ff00000000ff0000ffff00000000ff00ff00ff0000ffff00ffffff00'

KLIK_PALETTE = img.from_palette_bytes( bytes.fromhex( KLIK_PALETTE_RAW ), stride=4, order=(0, 1, 2) )
KLIK_PALETTE[0] = img.Transparent()


# source: forum post by Jeremy Penner
# https://www.glorioustrainwrecks.com/node/294

class ImageRLE( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        pointer = 0
        result = bytearray()
        while pointer < len( buffer ):
            test = buffer[pointer]
            pointer += 1
            if test & 0x80:
                result += buffer[pointer:pointer+(test & 0x7f)]
                pointer += (test & 0x7f)
            else:
                result += buffer[pointer:pointer+1]*test
                pointer += 1
        return mrc.TransformResult( payload=bytes( result ), end_offset=pointer )


class ImageData( mrc.Block ):
    unk1 = mrc.Bytes( 0x00, length=6 )
    size = mrc.UInt16_LE( 0x06 )
    unk2 = mrc.UInt16_LE( 0x08 )
    width_raw = mrc.UInt16_LE( 0x0a )
    height = mrc.UInt16_LE( 0x0c )
    unk3 = mrc.UInt16_LE( 0x0e, count=5 )
    data = mrc.Bytes( 0x18, length=mrc.Ref( 'size' ), transform=ImageRLE() )

    @property
    def width( self ):
        return self.width_raw - (self.width_raw % 2) + (2 if (self.width_raw % 2) else 0)

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage( self, mrc.Ref( 'data' ), mrc.Ref( 'width' ), mrc.Ref( 'height' ), palette=KLIK_PALETTE )


class ImageEntry( mrc.Block ):
    offset = mrc.UInt32_LE( 0x00 )
    size = mrc.UInt32_LE( 0x04 )
    image = mrc.StoreRef( ImageData, mrc.Ref( '_parent.images' ), mrc.Ref( 'offset' ), mrc.Ref( 'size' ) )


class IMGFile( mrc.Block ):
    count = mrc.UInt32_LE( 0x00 )
    entries = mrc.BlockField( ImageEntry, 0x04, count=mrc.Ref( 'count' ) )
    images_raw = mrc.Bytes( mrc.EndOffset( 'entries' ) )

    def __init__( self, *args, **kwargs ):
        self.images = mrc.Store( parent=self,
                                 source=mrc.Ref( 'images_raw' ),
                                 base_offset=mrc.EndOffset( 'entries', neg=True ) )
        super().__init__( *args, **kwargs )


class SoundData( mrc.Block ):
    unk1 = mrc.UInt32_LE( 0x00 )
    unk2 = mrc.UInt16_LE( 0x04 )
    unk3 = mrc.UInt32_LE( 0x06 )
    unk4 = mrc.Bytes( 0x0a, length=0x12 )
    unk5 = mrc.UInt32_LE( 0x1c )
    unk6 = mrc.UInt16_LE( 0x20 )
    unk7 = mrc.UInt16_LE( 0x22 )
    sample_rate = mrc.UInt32_LE( 0x24 )
    playback_rate = mrc.UInt32_LE( 0x28 )
    channels = mrc.UInt16_LE( 0x2c )
    sample_bits = mrc.UInt16_LE( 0x2e )
    data = mrc.Bytes( 0x30 )

    @property
    def sample_signedness( self ):
        return 'unsigned' if self.sample_bits == 8 else 'signed'

    @property
    def sample_width( self ):
        return self.sample_bits // 8

    def __init__( self, *argc, **argv ):
        self.audio = aud.Wave( self, mrc.Ref( 'data' ), mrc.Ref( 'channels' ), mrc.Ref( 'sample_rate' ), int, mrc.Ref( 'sample_width' ), mrc.Ref( 'sample_signedness' ), 'big' )
        super().__init__( *argc, **argv )


class SoundEntry( mrc.Block ):
    offset = mrc.UInt32_LE( 0x00 )
    size = mrc.UInt32_LE( 0x04 )
    sound = mrc.StoreRef( SoundData, mrc.Ref( '_parent.sounds' ), mrc.Ref( 'offset' ), mrc.Ref( 'size' ) )


class SNDFile( mrc.Block ):
    count = mrc.UInt32_LE( 0x00 )
    entries = mrc.BlockField( SoundEntry, 0x04, count=mrc.Ref( 'count' ) )
    sound_raw = mrc.Bytes( mrc.EndOffset( 'entries' ) )

    def __init__( self, *args, **kwargs ):
        self.sounds = mrc.Store( parent=self,
                                 source=mrc.Ref( 'sound_raw' ),
                                 base_offset=mrc.EndOffset( 'entries', neg=True ) )
        super().__init__( *args, **kwargs )



class MusicData( mrc.Block ):
    unk1 = mrc.Bytes( 0x00, length=0x20 )
    midi = mrc.Bytes( 0x20 )


class MusicEntry( mrc.Block ):
    offset = mrc.UInt32_LE( 0x00 )
    size = mrc.UInt32_LE( 0x04 )
    music = mrc.StoreRef( MusicData, mrc.Ref( '_parent.tracks' ), mrc.Ref( 'offset' ), mrc.Ref( 'size' ) )


class MUSFile( mrc.Block ):
    count = mrc.UInt32_LE( 0x00 )
    entries = mrc.BlockField( MusicEntry, 0x04, count=mrc.Ref( 'count' ) )
    music_raw = mrc.Bytes( mrc.EndOffset( 'entries' ) )

    def __init__( self, *args, **kwargs ):
        self.tracks = mrc.Store( parent=self,
                                 source=mrc.Ref( 'music_raw' ),
                                 base_offset=mrc.EndOffset( 'entries', neg=True ) )
        super().__init__( *args, **kwargs )
