"""File format classes for the games The Lost Vikings (1992) and Blackthorne (1994).
"""
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar import models as mrc
from mrcrowbar import utils

class Config( mrc.Block ):
    pad1 = mrc.UInt16_LE( 0x00 )
    sound_type = mrc.UInt16_LE( 0x02 )
    sound_port = mrc.UInt16_LE( 0x04 )
    sound_irq = mrc.UInt16_LE( 0x06 )
    sound_dma = mrc.UInt16_LE( 0x08 )
    pad2 = mrc.UInt16_LE( 0x0a )
    unk1 = mrc.UInt16_LE( 0x0c )
    pad3 = mrc.UInt16_LE( 0x0e )
    pad4 = mrc.UInt16_LE( 0x10 )
    music_type = mrc.UInt16_LE( 0x12 )
    music_port = mrc.UInt16_LE( 0x14 )
    pad5 = mrc.UInt16_LE( 0x16 )
    pad6 = mrc.UInt16_LE( 0x18 )
    pad7 = mrc.UInt16_LE( 0x1a )
    pad8 = mrc.UInt16_LE( 0x1c )
    pad9 = mrc.UInt16_LE( 0x1e )


class Data( mrc.Block ):
    count = mrc.UInt32_LE( 0x00 )
    offsets = mrc.UInt32_LE( 0x04, bitmask=b'\xff\xff\xff\x3f', count=mrc.Ref( 'count' ) )

    data_raw = mrc.Bytes( mrc.EndOffset( 'offsets' ) )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.data = mrc.LinearStore( parent=self,
                                    source=mrc.Ref( 'data_raw' ),
                                    block_klass=mrc.Unknown,
                                    offsets=mrc.Ref( 'offsets' ),
                                    base_offset=mrc.EndOffset( 'offsets', neg=True ) )

class Tile( mrc.Block ):
    index = mrc.UInt16_LE( 0x00 )


class TileMap( mrc.Block ):
    tiles = mrc.BlockField( Tile, 0x00, stream=True )


class TileQuad( mrc.Block ):
    index =     mrc.Bits( 0x00, 0xffc0, size=2, endian='little' )
    flip_v =    mrc.Bits( 0x00, 0x0020, size=2, endian='little' )
    flip_h =    mrc.Bits( 0x00, 0x0010, size=2, endian='little' )
    unk1 =      mrc.Bits( 0x00, 0x000f, size=2, endian='little' )

    @property
    def repr( self ):
        return 'index: {}, flip_h: {}, flip_v: {}'.format( self.index, self.flip_h, self.flip_v )


class MetaTile( mrc.Block ):
    top_left = mrc.BlockField( TileQuad, 0x00 )
    top_right = mrc.BlockField( TileQuad, 0x02 )
    bottom_left = mrc.BlockField( TileQuad, 0x04 )
    bottom_right = mrc.BlockField( TileQuad, 0x06 )

    @property
    def repr( self ):
        return 'top_left: {}, top_right: {}, bottom_left: {}, bottom_right: {}'.format( self.top_left, self.top_right, self.bottom_left, self.bottom_right )


class MetaTileMap( mrc.Block ):
    metatiles = mrc.BlockField( MetaTile, 0x00, stream=True )


class LZSS( mrc.Transform ):
    def import_data( self, buffer ):
        output_size = utils.from_uint32_le( buffer[:4] )
        edx = output_size
        data_p = 4
        bx = 0
        cx = 0
        work_ram = bytearray( 0x1000 )
        output = bytearray()

        while True:
            cx >>= 1
            if cx < 0x100:
                logger.debug( '@ new pattern: {:08b}'.format( buffer[data_p] ) )
                cx = buffer[data_p] + 0xff00
                data_p += 1
            
            
            if not (cx & 1):
                info = buffer[data_p] + (buffer[data_p+1] << 8)
                data_p += 2
                work_p = info & 0xfff
                count = (info >> 12) + 3
                logger.debug( '# work_ram[0x{:04x}:0x{:04x}] = work_ram[0x{:04x}:0x{:04x}]'.format( bx, (bx+count) & 0xfff, work_p, (work_p+count) & 0xfff ) )
                logger.debug( '! output[0x{:04x}:0x{:04x}] = work_ram[0x{:04x}:0x{:04x}]'.format( len( output ), len( output )+count, work_p, (work_p+count) & 0xfff ) )
                for i in range( count ):
                    # loc_103C4
                    dat = work_ram[work_p]
                    work_ram[bx] = dat
                    work_p += 1
                    work_p &= 0xfff
                    bx += 1
                    bx &= 0xfff
                    output.append( dat )

                    edx -= 1
                    if edx == 0:
                        break

                if edx == 0:
                    break
        
            else:
                logger.debug( '# work_ram[0x{:04x}] = buffer[0x{:04x}]'.format( bx, data_p ) ) 
                logger.debug( '! output[0x{:04x}] = buffer[0x{:04x}]'.format( len( output ), data_p ) ) 
                dat = buffer[data_p]
                work_ram[bx] = dat
                data_p += 1
                bx += 1
                bx &= 0xfff
                output.append( dat )
                edx -= 1
                if edx == 0:
                    break

        logger.info( '{} - output_size: {:08x}, output_end: {:08x}, input_size: {:08x}, input_end: {:08x}'.format( self, output_size, len( output ), len( buffer ), data_p ) )

        return mrc.TransformResult( payload=bytes( output ), end_offset=data_p )


class Interlace( mrc.Transform ):
    def import_data( self, buffer ):
        assert len( buffer ) % 64 == 0
        result = bytearray( len( buffer ) )
        for i in range( 0, len( buffer ), 64 ):
            deint = buffer[i:i+64:2] + buffer[i+1:i+64:2]
            result[i:i+64] = bytes( [deint[8*(j%8)+(j//8)] for j in range( 64 )] ) 
        return mrc.TransformResult( payload=bytes( result ), end_offset=len( result ) )


# in BLACK.EXE at 0x14ef8. 
BLACKTHORNE_PALETTE_ENTRIES = [
    0x4f, 0x8c, 0x9d, 0x54, 0x109, 0x108, 0x10a, 0x55, 
    0x57, 0x52, 0x4e, 0x58, 0x116, 0x50, 0x48, 0x124, 
    0x7c, 0x53, 0x56, 0x51, 0x10b, 0x128, 0x129, 0x125, 
    0x12d, 0x12e, 0x126, 0x127, 0x12f, 0x12b, 0x12a, 0x12c, 
    0x130
]


