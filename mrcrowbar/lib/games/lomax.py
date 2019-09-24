from mrcrowbar import models as mrc
from mrcrowbar import utils
from mrcrowbar.lib.images import base as img


class FourBit( mrc.Transform ):
    def __init__( self, enable=True ):
        self.enable = enable

    def import_data( self, buffer, parent=None ):
        enable = mrc.property_get( self.enable, parent )
        
        if not enable:
            return mrc.TransformResult( payload=buffer, end_offset=len( buffer ) )

        output = bytearray( len( buffer )*2 )
        for i in range( len( buffer ) ):
            output[2*i] = buffer[i] & 0x0f
            output[2*i+1] = buffer[i] >> 4
        return mrc.TransformResult( payload=output, end_offset=len( buffer ) )
    
    def export_data( self, buffer, parent=None ):
        enable = mrc.property_get( self.enable, parent )
        
        if not enable:
            return mrc.TransformResult( payload=buffer )
        
        if buffer:
            assert max( buffer ) <= 0xf 
        output = bytearray( len( buffer )//2 )
        for i in range( len( buffer ) ):
            if i % 2:
                output[i//2] |= buffer[i] << 4
            else:
                output[i//2] |= buffer[i]
        return mrc.TransformResult( payload=output, end_offset=len( buffer ) )


class Colour15( img.Colour ):
    r_raw = mrc.Bits16( 0x00, bits=0b0111110000000000, endian='little', )
    g_raw = mrc.Bits16( 0x00, bits=0b0000001111100000, endian='little', )
    b_raw = mrc.Bits16( 0x00, bits=0b0000000000011111, endian='little', )

    @property
    def r_8( self ):
        return (self.r_raw << 3) + 7

    @property
    def g_8( self ):
        return (self.g_raw << 3) + 7

    @property
    def b_8( self ):
        return (self.b_raw << 3) + 7


class Palette( mrc.Block ):
    colours = mrc.BlockField( Colour15, count=256 )


class AnimFrame( mrc.Block ):
    width = mrc.UInt16_LE( 0x00 )
    height = mrc.UInt16_LE( 0x02 )
    unk1 = mrc.UInt16_LE( 0x04 )
    unk2 = mrc.UInt16_LE( 0x06 )
    raw_data = mrc.Bytes( 0x08, length=mrc.Ref( 'size' ), transform=FourBit( enable=mrc.Ref( '_parent.four_bit' ) ) )


    @property
    def size( self ):
        if self._parent and self._parent.four_bit:
            return self.width*self.height//2
        return self.width*self.height


    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage(
            self, width=mrc.Ref( 'width' ), height=mrc.Ref( 'height' ),
            source=mrc.Ref( 'raw_data' ), palette=mrc.Ref( '_parent.palette' )
        )


class ANIM( mrc.Block ):
    unk1 = mrc.UInt16_LE( 0x00 )
    unk2 = mrc.UInt16_LE( 0x02 )
    num_frames = mrc.UInt16_LE( 0x04 )
    palette_id = mrc.UInt8( 0x06 )
    four_bit = mrc.Bits( 0x07, bits=0b10000000 )
    unk4 = mrc.Bits( 0x07, bits=0b01111111 )
    unk5 = mrc.UInt32_LE( 0x08 )
 
    frames = mrc.BlockField( AnimFrame, 0x0c, count=mrc.Ref( 'num_frames' ), alignment=4 )

    @property
    def palette( self ):
        if self._parent:
            # HACK: get the first HEAD chunk and use the palette list
            head = next( (x.obj for x in self._parent.chunks if x.id == b'HEAD'), None )
            return head.palettes[self.palette_id].colours if head else None
        return []


class HEAD( mrc.Block ):
    unk1 = mrc.UInt32_BE( 0x00 )
    unk2 = mrc.UInt32_BE( 0x04 )
    palettes = mrc.BlockField( Palette, 0x08, count=10 )
    unk3 = mrc.Bytes( 0x1408, length=0x50 )
    unk4 = mrc.Bytes( 0x1458, length=0x20 )


class World( mrc.Block ):
    BLOCK_MAP = {
        b'HEAD': HEAD,
        b'ANIM': ANIM,
    }

    chunks = mrc.ChunkField( BLOCK_MAP, 0x00, id_size=4, length_field=mrc.UInt32_BE, default_klass=mrc.Unknown )
