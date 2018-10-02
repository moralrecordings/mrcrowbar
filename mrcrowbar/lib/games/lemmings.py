"""File format classes for the game Lemmings (DOS, 1991).

Sources:
DAT compressor
http://www.camanis.net/lemmings/files/docs/lemmings_dat_file_format.txt

Level file format
http://www.camanis.net/lemmings/files/docs/lemmings_lvl_file_format.txt

Vgagr/Ground DAT file formats
http://www.camanis.net/lemmings/files/docs/lemmings_vgagrx_dat_groundxo_dat_file_format.txt

Main DAT file format
http://www.camanis.net/lemmings/files/docs/lemmings_main_dat_file_format.txt

Vgaspec compressor/DAT file format
http://www.camanis.net/lemmings/files/docs/lemmings_vgaspecx_dat_file_format.txt

Extra special thanks to ccexplore and Mindless
"""

import itertools
from enum import IntEnum
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.images import base as img
from mrcrowbar import utils



class DATCompressor( mrc.Transform ):

    @staticmethod
    def _xor_checksum( data ):
        lrc = 0
        for b in data:
            lrc ^= b
        return lrc

    def import_data( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )      
        
        pointer = 0;
        total_num_bytes = len( buffer )
        
        bit_count = utils.from_uint8( buffer[pointer:pointer+1] )
        checksum = utils.from_uint8( buffer[pointer+1:pointer+2] )
        decompressed_size = utils.from_uint32_be( buffer[pointer+2:pointer+6] )
        compressed_size = utils.from_uint32_be( buffer[pointer+6:pointer+10] )
        
        pointer += 10
        total_num_bytes -= 10
        compressed_size -= 10
        
        compressed_data = buffer[pointer:pointer+compressed_size]
        if checksum != self._xor_checksum( compressed_data ):
            logger.warning( '{}: Checksum doesn\'t match header'.format( self ) )  
        
        pointer += compressed_size
        total_num_bytes -= compressed_size
    
        bs = utils.BitReader( compressed_data, compressed_size-1, bytes_reverse=True, output_reverse=True )
        bs.bits_remaining = bit_count
        
        def copy_prev_data( blocklen, offset_size, state ):
            offset = bs.get_bits( offset_size )
            for i in range( blocklen ):
                state['dptr'] -= 1
                state['ddata'][state['dptr']] = state['ddata'][state['dptr']+offset+1]
            return
        
        def dump_data( num_bytes, state ):
            for i in range( num_bytes ):
                state['dptr'] -= 1
                state['ddata'][state['dptr']] = bs.get_bits( 8 )
            return

        state = { 
            'dptr': decompressed_size, 
            'ddata': bytearray( decompressed_size ),
        }

        while True:
            if bs.get_bits( 1 ) == 1:
                test = bs.get_bits( 2 )
                if test==0:
                    copy_prev_data( 3, 9, state )
                elif test==1:
                    copy_prev_data( 4, 10, state )
                elif test==2:
                    copy_prev_data( bs.get_bits( 8 )+1, 12, state )
                elif test==3:
                    dump_data( bs.get_bits( 8 )+9, state )
            else:
                test = bs.get_bits( 1 )
                if test==0:
                    dump_data( bs.get_bits( 3 )+1, state )
                elif test==1:
                    copy_prev_data( 2, 8, state )
            if not (state['dptr'] > 0): 
                break
        
        return mrc.TransformResult( payload=bytes( state['ddata'] ), end_offset=pointer )


    def export_data( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )

        decompressed_size = len( buffer )

        bs = utils.BitWriter( bits_reverse=True )

        pointer = 0

        def encode_raw_data( length, bs ):
            assert length <= 255+9

            if length > 8:
                bs.put_bits( length-9, 8 )
                bs.put_bits( 0x7, 3 )
            elif length > 0:
                bs.put_bits( length-1, 3 )
                bs.put_bits( 0x0, 2 )

        def find_reference():
            # main form of compression is of the form:
            # - while decompressing from end to start
            # - look forward [up to max_offset] bytes in the decompressed data
            # - copy [up to max_length] bytes to the current decompression position
            # the largest offset supported by the file format is 4096, but this means
            # every call to find_reference loops 4096 times.
            # this takes foreeeever in Python!
            # because the compression is worthless and time is money, max_offset has 
            # been slashed to 16 to speed up proceedings.
            #max_offset = (1 << 12) + 1
            max_offset = (1 << 4) + 1
            # largest length supported by the file format is 256
            max_length = (1 << 8) + 1

            length = 4  # throw away short references
            offset = 0 
            short_offset = [0, 0, 0]
            
            for i in range( pointer+1, pointer+max_offset ):
                temp_len = 0
                while (temp_len < max_length) and (i+temp_len < decompressed_size):
                    # record short references
                    if (temp_len >= 2) and (temp_len <= 4):
                        if short_offset[temp_len-2] == 0:
                            short_offset[temp_len-2] = i-pointer

                    if buffer[pointer+temp_len] != buffer[i+temp_len]:
                        break
                    temp_len += 1
                
                if temp_len == max_length:
                    temp_len -= 1

                # largest reference so far? use it 
                if temp_len > length:
                    length = temp_len
                    offset = i-pointer

            assert length < max_length
            assert offset < max_offset
    
            # no long references? try short
            if (offset == 0):
                for i in (2, 1, 0):
                    max_short_offset = (1 << (i+8))+1
                    if (short_offset[i] > 0) and (short_offset[i] < max_short_offset):
                        length = i+2
                        offset = short_offset[i]
                        break

            return length, offset
        
        raw = 0
        while pointer < decompressed_size:
            length, ref = find_reference()
            if ref > 0:
                if raw > 0:
                    encode_raw_data( raw, bs )
                    raw = 0
                if length > 4:
                    bs.put_bits( ref-1, 12 )
                    bs.put_bits( length-1, 8 )
                    bs.put_bits( 0x6, 3 )
                elif length == 4:
                    bs.put_bits( ref-1, 10 )
                    bs.put_bits( 0x5, 3 )
                elif length == 3:
                    bs.put_bits( ref-1, 9 )
                    bs.put_bits( 0x4, 3 )
                elif length == 2:
                    bs.put_bits( ref-1, 8 )
                    bs.put_bits( 0x1, 2 )

                pointer += length
            else:
                bs.put_bits( buffer[pointer], 8 )

                raw += 1
                if raw == 264:
                    encode_raw_data( raw, bs )
                    raw = 0

                pointer += 1

        encode_raw_data( raw, bs )

    
        compressed_data = bs.get_buffer()
        compressed_size = len( compressed_data ) + 10
        checksum = self._xor_checksum( compressed_data )

        output = bytearray( 6 )
        output[0:1] = utils.to_uint8( 8-(bs.bits_remaining % 8) )
        output[1:2] = utils.to_uint8( checksum )
        output[2:6] = utils.to_uint32_be( decompressed_size )
        output[6:10] = utils.to_uint32_be( compressed_size )
        output.extend( compressed_data )

        return mrc.TransformResult( payload=bytes( output ) )
            


class SpecialCompressor( mrc.Transform ):
    DECOMPRESSED_SIZE = 14400    

    plan = img.Planarizer( bpp=3, width=960, height=40 )

    def import_data( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        result = []
        buf_out = []
        i = 0
        while i < len( buffer ):
            # 0x00 <= n < 0x80: copy next n+1 bytes to output stream
            if buffer[i] in range( 0x00, 0x80 ):
                count = buffer[i]+1
                buf_out.append( buffer[i+1:i+1+count] )
                i += count+1
            # n == 0x80: end of segment
            elif buffer[i] == 0x80:
                product = b''.join( buf_out )
                if len( product ) != self.DECOMPRESSED_SIZE:
                    logger.warning( '{}: was expecting {} bytes of data, got {}'.format( self, self.DECOMPRESSED_SIZE, len( product ) ) )
                result.append( product )
                buf_out = []
                i += 1
            # 0x81 <= n < 0xff: repeat next byte (257-n) times
            else:
                count = 257-buffer[i]
                buf_out.append( buffer[i+1:i+2]*count )
                i += 2

        if buf_out:
            logger.warning( '{}: EOF reached before last RLE block closed'.format( self ) )
            result.append( b''.join( buf_out ) )

        # result is a 960x160 3bpp image, divided into 4x 40 scanline segments
        unpack = (self.plan.import_data( x ).payload for x in result)
        
        return mrc.TransformResult( payload=bytes( itertools.chain( *unpack ) ), end_offset=i )

    def export_data( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        assert len( buffer ) == 960*160
        
        segments = (buffer[960*40*i:960*40*(i+1)] for i in range(4))
        segments = (self.plan.export_data( x ).payload for x in segments)
        
        result = bytearray()

        for segment in segments:
            pointer = 0
            while pointer < len( segment ):
                start = pointer
                end = pointer+1
                if end >= len( segment ):
                    result.append( 0x00 )
                    result.append( segment[start] )
                    pointer += 1
                elif segment[end] == segment[start]:
                    while ((end+1) < len( segment )) and (segment[end+1] == segment[end]) and (end-start < 127):
                        end += 1
                    result.append( 257-(end+1-start) )
                    result.append( segment[start] )
                    pointer = end+1
                else:
                    while ((end+1) < len( segment )) and (segment[end+1] != segment[end]) and (end-1-start < 128):
                        end += 1
                    result.append( end-1-start )
                    result.extend( segment[start:end] )
                    pointer = end

            result.append( 0x80 )
        
        return mrc.TransformResult( payload=bytes( result ) )
                    



# this palette is actually stored in the first half of each GroundDat palette block,
# but it's handy to have a static copy for e.g. checking out the MainAnims block
LEMMINGS_VGA_DEFAULT_PALETTE = (
    ibm_pc.VGAColour( b'\x00\x00\x00' ),
    ibm_pc.VGAColour( b'\x10\x10\x38' ),
    ibm_pc.VGAColour( b'\x00\x2c\x00' ),
    ibm_pc.VGAColour( b'\x3c\x34\x34' ),
    ibm_pc.VGAColour( b'\x3c\x3c\x00' ),
    ibm_pc.VGAColour( b'\x3c\x08\x08' ),
    ibm_pc.VGAColour( b'\x20\x20\x20' ),
    ibm_pc.VGAColour( b'\x38\x20\x08' ),  # dirt colour
)


# the following palette is embedded in the Lemmings executable
LEMMINGS_VGA_MENU_PALETTE = (
    ibm_pc.VGAColour( b'\x00\x00\x00' ),
    ibm_pc.VGAColour( b'\x20\x10\x08' ),
    ibm_pc.VGAColour( b'\x18\x0c\x08' ),
    ibm_pc.VGAColour( b'\x0c\x00\x04' ),
    ibm_pc.VGAColour( b'\x08\x02\x1f' ),
    ibm_pc.VGAColour( b'\x10\x0b\x24' ),
    ibm_pc.VGAColour( b'\x1a\x16\x29' ),
    ibm_pc.VGAColour( b'\x26\x23\x2f' ),
    ibm_pc.VGAColour( b'\x00\x14\x00' ),
    ibm_pc.VGAColour( b'\x00\x18\x04' ),
    ibm_pc.VGAColour( b'\x00\x1c\x08' ),
    ibm_pc.VGAColour( b'\x00\x20\x10' ),
    ibm_pc.VGAColour( b'\x34\x34\x34' ),
    ibm_pc.VGAColour( b'\x2c\x2c\x00' ),
    ibm_pc.VGAColour( b'\x10\x14\x2c' ),
    ibm_pc.VGAColour( b'\x38\x20\x24' ),
)

##########
# levelXXX.dat parser
##########

class Interactive( mrc.Block ):
    """Represents a single interactive piece placed in a level."""
    
    #: Raw value for the x position of the left edge.
    x_raw =             mrc.Int16_BE( 0x00, range=range( -8, 1601 ) )
    #: The y position of the top edge.
    y =                 mrc.Int16_BE( 0x02, range=range( -41, 201 ) )
    #: Index of the InteractiveInfo block in the accompanying GroundDAT.
    obj_id =            mrc.UInt16_BE( 0x04, range=range( 0, 16 ) )
    #: If 1, blit image behind background.
    draw_back =         mrc.Bits( 0x06, 0b10000000 )
    #: If 1, draw piece flipped vertically.
    draw_masked =       mrc.Bits( 0x06, 0b01000000 )
    #: If 1, draw piece as a hole.
    draw_upsidedown =   mrc.Bits( 0x07, 0b10000000 )

    #: Check to ensure the last chunk of the block is empty.
    mod_check =         mrc.Const( mrc.UInt16_BE( 0x06, bitmask=b'\x3f\x7f' ), 0x000f )

    @property
    def x( self ):
        """The x position of the left edge."""
        return (self.x_raw-16) - ((self.x_raw-16) % 8)

    @property
    def repr( self ):
        return "obj_id={}, x={}, y={}".format( self.obj_id, self.x, self.y )


class Terrain( mrc.Block ):
    """Represents a single terrain piece placed in a level."""

    #: Raw value for the x position of the left edge.
    x_raw =             mrc.UInt16_BE( 0x00, bitmask=b'\x0f\xff' )
    #: If 1, blit image behind background.
    draw_back =         mrc.Bits( 0x00, 0b10000000 )
    #: If 1, draw piece flipped vertically.
    draw_upsidedown =   mrc.Bits( 0x00, 0b01000000 )
    #: If 1, draw piece as a hole.
    draw_erase =        mrc.Bits( 0x00, 0b00100000 )
    #: Raw value (coarse component) for the y position of the top edge.
    y_raw_coarse =      mrc.Int8( 0x02 )
    #: Raw value (fine component) for the y position of the top edge.
    y_raw_fine =        mrc.Bits( 0x03, 0b10000000 )

    unknown_1 =         mrc.Bits( 0x03, 0b01000000 )

    #: Index of the TerrainInfo block in the accompanying GroundDAT.
    obj_id =            mrc.UInt8( 0x03, bitmask=b'\x3f', range=range( 0, 64 ) )


    @property
    def x( self ):
        """The x position of the left edge."""
        return (self.x_raw-16)

    @property
    def y( self ):
        """The y position of the top edge."""
        return (self.y_raw_coarse*2 + self.y_raw_fine)-4
   
    @property
    def repr( self ):
        return "obj_id={}, x={}, y={}".format( self.obj_id, self.x, self.y )


class SteelArea( mrc.Block ):
    """Represents an indestructable rectangular area in a level."""
    
    #: Raw value (coarse component) for the x position of the left edge.
    x_raw_coarse =      mrc.UInt8( 0x00, range=range( 0, 200 ) )
    #: Raw value (fine component) for the x position of the left edge.
    x_raw_fine =        mrc.Bits( 0x01, 0b10000000 )
    #: Raw value for the y position of the area's top edge.
    y_raw =             mrc.UInt8( 0x01, bitmask=b'\x7f', range=range( 0, 128 ) )
    #: Raw value for the width.
    width_raw =         mrc.Bits( 0x02, 0b11110000 )
    #: Raw value for the height.
    height_raw =        mrc.Bits( 0x02, 0b00001111 )

    #: Check to ensure the last byte of the block is empty.
    mod_check =         mrc.Const( mrc.UInt8( 0x03 ), 0x00 )
    
    @property
    def x( self ):
        """The x position of the left edge."""
        return (self.x_raw_coarse*2 + self.x_raw_fine)*4-16

    @property
    def y( self ):
        """The y position of the top edge."""
        return (self.y_raw*4)

    @property
    def width( self ):
        """Width of the steel area."""
        return (self.width_raw+1)*4

    @property
    def height( self ):
        """Height of the steel area."""
        return (self.height_raw+1)*4

    @property
    def repr( self ):
        return "x={}, y={}, width={}, height={}".format( self.x, self.y, self.width, self.height )


class Level( mrc.Block ):
    """Represents a single Lemmings level."""

    #: Minimum Lemming release-rate.
    release_rate =      mrc.UInt16_BE( 0x0000, range=range( 0, 251 ) )
    #: Number of Lemmings released.
    num_released =      mrc.UInt16_BE( 0x0002, range=range( 0, 115 ) )
    #: Number of Lemmings required to be saved.
    num_to_save =       mrc.UInt16_BE( 0x0004, range=range( 0, 115 ) )
    #: Time limit for the level (minutes).
    time_limit_mins =   mrc.UInt16_BE( 0x0006, range=range( 0, 256 ) )
    #: Number of Climber skills.
    num_climbers =      mrc.UInt16_BE( 0x0008, range=range( 0, 251 ) )
    #: Number of Floater skills.
    num_floaters =      mrc.UInt16_BE( 0x000a, range=range( 0, 251 ) )
    #: Number of Bomber skills.
    num_bombers =       mrc.UInt16_BE( 0x000c, range=range( 0, 251 ) )
    #: Number of Blocker skills.
    num_blockers =      mrc.UInt16_BE( 0x000e, range=range( 0, 251 ) )
    #: Number of Builder skills.
    num_builders =      mrc.UInt16_BE( 0x0010, range=range( 0, 251 ) )
    #: Number of Basher skills.
    num_bashers =       mrc.UInt16_BE( 0x0012, range=range( 0, 251 ) )
    #: Number of Miner skills.
    num_miners =        mrc.UInt16_BE( 0x0014, range=range( 0, 251 ) )
    #: Number of Digger skills.
    num_diggers =       mrc.UInt16_BE( 0x0016, range=range( 0, 251 ) )
    #: Raw value for the start x position of the camera.
    camera_x_raw =      mrc.UInt16_BE( 0x0018, range=range( 0, 1265 ) )
    
    #: Index denoting which graphical Style to use.
    style_index =       mrc.UInt16_BE( 0x001a )
    #: Index denoting which Special graphic to use (optional).
    custom_index =      mrc.UInt16_BE( 0x001c )

    #: List of Interactive object references (32 slots).
    interactives =      mrc.BlockField( Interactive, 0x0020, count=32, fill=b'\x00'*8 )
    #: List of Terrain object references (400 slots).
    terrains =          mrc.BlockField( Terrain, 0x0120, count=400, fill=b'\xff'*4 )
    #: List of SteelArea object references (32 slots).
    steel_areas =       mrc.BlockField( SteelArea, 0x0760, count=32, fill=b'\x00'*4 )
    #: Name of the level (ASCII string).
    name =              mrc.Bytes( 0x07e0, 32, default=b'                                ' )

    @property
    def camera_x( self ):
        """Start x position of the camera."""
        return self.camera_x_raw - (self.camera_x_raw % 8)

    @property
    def repr( self ):
        return self.name.strip().decode( 'utf8' )


class LevelDAT( mrc.Block ):
    levels  = mrc.BlockField( Level, 0x0000, stream=True, transform=DATCompressor() )

##########
# oddtable.dat parser
##########

class OddRecord( mrc.Block ):
    """Represents an alternative set of conditions for a level.
    
    Used in Lemmings to repeat the same level with a different difficulty.
    """

    #: Minimum Lemming release-rate.
    release_rate =      mrc.UInt16_BE( 0x0000, range=range( 0, 251 ) )
    #: Number of Lemmings released.
    num_released =      mrc.UInt16_BE( 0x0002, range=range( 0, 115 ) )
    #: Number of Lemmings required to be saved.
    num_to_save =       mrc.UInt16_BE( 0x0004, range=range( 0, 115 ) )
    #: Time limit for the level (minutes).
    time_limit_mins =   mrc.UInt16_BE( 0x0006, range=range( 0, 256 ) )
    #: Number of Climber skills.
    num_climbers =      mrc.UInt16_BE( 0x0008, range=range( 0, 251 ) )
    #: Number of Floater skills.
    num_floaters =      mrc.UInt16_BE( 0x000a, range=range( 0, 251 ) )
    #: Number of Bomber skills.
    num_bombers =       mrc.UInt16_BE( 0x000c, range=range( 0, 251 ) )
    #: Number of Blocker skills.
    num_blockers =      mrc.UInt16_BE( 0x000e, range=range( 0, 251 ) )
    #: Number of Builder skills.
    num_builders =      mrc.UInt16_BE( 0x0010, range=range( 0, 251 ) )
    #: Number of Basher skills.
    num_bashers =       mrc.UInt16_BE( 0x0012, range=range( 0, 251 ) )
    #: Number of Miner skills.
    num_miners =        mrc.UInt16_BE( 0x0014, range=range( 0, 251 ) )
    #: Number of Digger skills.
    num_diggers =       mrc.UInt16_BE( 0x0016, range=range( 0, 251 ) )

    #: Name of the level (ASCII string).
    name =              mrc.Bytes( 0x0018, 32, default=b'                                ' )

    @property
    def repr( self ):
        return self.name.strip().decode( 'utf8' )


class OddtableDAT( mrc.Block ):
    """Represents a collection of OddRecord objects."""
    
    #: List of OddRecord objects (80 slots).
    records =           mrc.BlockField( OddRecord, 0x0000, count=80 )


##########
# groundXo.dat and vgagrX.dat parser
##########

class InteractiveImage( mrc.Block ):
    """Represents the sprite data for an interactive object."""

    image_data  =       mrc.Bytes( 
                            0x0000, transform=img.Planarizer( 
                                bpp=4, 
                                width=mrc.Ref( '_parent.width' ), 
                                height=mrc.Ref( '_parent.height' ), 
                                frame_count=mrc.Ref( '_parent.end_frame' ), 
                                frame_stride=mrc.Ref( '_parent.frame_data_size' ) 
                            ) 
                        )
    mask_data   =       mrc.Bytes( 
                            mrc.Ref( '_parent.mask_rel_offset' ), 
                            transform=img.Planarizer( 
                                bpp=1, 
                                width=mrc.Ref( '_parent.width' ), 
                                height=mrc.Ref( '_parent.height' ), 
                                frame_count=mrc.Ref( '_parent.end_frame' ), 
                                frame_stride=mrc.Ref( '_parent.frame_data_size' ) 
                            ) 
                        )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage( 
                        self, 
                        width=mrc.Ref( '_parent.width' ), 
                        height=mrc.Ref( '_parent.height' ), 
                        source=mrc.Ref( 'image_data' ), 
                        frame_count=mrc.Ref( '_parent.end_frame' ), 
                        palette=mrc.Ref( '_parent._parent.palette' ),
                        mask=mrc.Ref( 'mask_data' )
                    )


class TriggerEffect( IntEnum ):
    NONE =          0x00
    EXIT_LEVEL =    0x01
    TRAP =          0x04
    DROWN =         0x05
    DISINTEGRATE =  0x06
    ONEWAY_LEFT =   0x07
    ONEWAY_RIGHT =  0x08
    STEEL =         0x09  # not used?


class SoundEffect( IntEnum ):
    NONE =          0x00
    SKILL_SELECT =  0x01
    HATCH_OPEN =    0x02
    LETS_GO =       0x03
    ASSIGN =        0x04
    OH_NO =         0x05
    ELECTRIC_TRAP = 0x06
    CRUSH_TRAP =    0x07
    SPLAT =         0x08
    ROPE_TRAP =     0x09
    HIT_STEEL =     0x0a
    UNKNOWN_1 =     0x0b
    BOMBER =        0x0c
    FIRE_TRAP =     0x0d
    HEAVY_TRAP =    0x0e
    BEAR_TRAP =     0x0f
    YIPPEE =        0x10
    DROWN =         0x11
    BUILDER =       0x12


class InteractiveInfo( mrc.Block ):
    """Contains a Ground style definition for an interactive object."""

    anim_flags =        mrc.UInt16_LE( 0x0000 )
    start_frame =       mrc.UInt8( 0x0002 )
    end_frame =         mrc.UInt8( 0x0003 )
    width =             mrc.UInt8( 0x0004 )
    height =            mrc.UInt8( 0x0005 )
    frame_data_size =   mrc.UInt16_LE( 0x0006 )
    mask_rel_offset =   mrc.UInt16_LE( 0x0008 )

    unknown_1 =         mrc.UInt16_LE( 0x000a )
    unknown_2 =         mrc.UInt16_LE( 0x000c )
    
    trigger_x_raw =         mrc.UInt16_LE( 0x000e )
    trigger_y_raw =         mrc.UInt16_LE( 0x0010 )
    trigger_width_raw =     mrc.UInt8( 0x0012 )
    trigger_height_raw =    mrc.UInt8( 0x0013 )
    trigger_effect =        mrc.UInt8( 0x0014, enum=TriggerEffect )

    base_offset =       mrc.UInt16_LE( 0x0015 )
    preview_frame =     mrc.UInt16_LE( 0x0017 )

    unknown_3 =         mrc.UInt16_LE( 0x0019 )

    #: Sound effect to play. Only used when trigger_effect is set to TRAP.
    sound_effect =      mrc.UInt8( 0x001b, enum=SoundEffect )
   
    vgagr =             mrc.StoreRef( InteractiveImage, mrc.Ref( '_parent._vgagr.interact_store.store' ), mrc.Ref( 'base_offset' ), mrc.Ref( 'size' ) )

    @property
    def size( self ):
        return self.frame_data_size*self.end_frame

    @property
    def plane_padding( self ):
        return self.width*self.height//8

    @property
    def trigger_x( self ):
        return self.trigger_x_raw * 4

    @property
    def trigger_y( self ):
        return self.trigger_y_raw * 4 - 4

    @property
    def trigger_width( self ):
        return self.trigger_width_raw * 4

    @property
    def trigger_height( self ):
        return self.trigger_height_raw * 4


class TerrainImage( mrc.Block ):
    image_data =        mrc.Bytes( 
                            0x0000, transform=img.Planarizer( 
                                bpp=4,
                                width=mrc.Ref( '_parent.width' ), 
                                height=mrc.Ref( '_parent.height' ), 
                            ) 
                        )
    mask_data =         mrc.Bytes( 
                            mrc.Ref( '_parent.mask_offset' ), 
                            transform=img.Planarizer( 
                                bpp=1, 
                                width=mrc.Ref( '_parent.width' ), 
                                height=mrc.Ref( '_parent.height' ), 
                            ) 
                        )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage( 
                        self, 
                        width=mrc.Ref( '_parent.width' ), 
                        height=mrc.Ref( '_parent.height' ), 
                        source=mrc.Ref( 'image_data' ), 
                        palette=mrc.Ref( '_parent._parent.palette' ),
                        mask=mrc.Ref( 'mask_data' )
                    )


class TerrainInfo( mrc.Block ):

    width =             mrc.UInt8( 0x0000 )
    height =            mrc.UInt8( 0x0001 )
    base_offset =       mrc.UInt16_LE( 0x0002 )
    mask_rel_offset =   mrc.UInt16_LE( 0x0004 )
    unknown_1 =         mrc.UInt16_LE( 0x0006 )

    vgagr =             mrc.StoreRef( TerrainImage, mrc.Ref( '_parent._vgagr.terrain_store.store' ), mrc.Ref( 'base_offset' ), mrc.Ref( 'size' ) )

    @property
    def size( self ):
        return self.width*self.height*5//8

    @property
    def mask_offset( self ):
        return self.mask_rel_offset-self.base_offset
        #return self.width*self.height*4//8

    @property
    def mask_stride( self ):
        return self.width*self.height*4//8

    @property
    def mask_size( self ):
        return self.width*self.height//8


class GroundDAT( mrc.Block ):
    """Represents a single graphical style."""

    _vgagr = None           # should be replaced by the correct VgagrDAT object

    #: Information for every type of interactive piece.
    interactive_info        = mrc.BlockField( InteractiveInfo, 0x0000, count=16, fill=b'\x00'*28 )
    #: Information for every type of terrain piece.
    terrain_info            = mrc.BlockField( TerrainInfo, 0x01c0, count=64, fill=b'\x00'*8 )

    #: Extended EGA palette used for rendering the level preview.
    palette_ega_preview     = img.Palette( ibm_pc.EGAColour, 0x03c0, count=8 )
    #: Copy of EGA palette used for rendering lemmings/action bar.
    #: Colours 0-6 are not used by the game, instead there is a palette embedded
    #: in the executable. 
    #: Colour 7 is used for drawing the minimap and dirt particles.
    palette_ega_standard    = img.Palette( ibm_pc.EGAColour, 0x03c8, count=8 )
    #: EGA palette used for rendering interactive/terrain pieces.
    palette_ega_custom      = img.Palette( ibm_pc.EGAColour, 0x03d0, count=8 )
    #: VGA palette used for rendering interactive/terrain pieces.
    palette_vga_custom      = img.Palette( ibm_pc.VGAColour, 0x03d8, count=8 )
    #: Copy of VGA palette used for rendering lemmings/action bar.
    #: Colours 0-6 are not used by the game, instead there is a palette embedded
    #: in the executable. 
    #: Colour 7 is used for drawing the minimap and dirt particles.
    palette_vga_standard    = img.Palette( ibm_pc.VGAColour, 0x03f0, count=8 )
    #: VGA palette used for rendering the level preview.
    palette_vga_preview     = img.Palette( ibm_pc.VGAColour, 0x0408, count=8 )

    @property
    def palette( self ):
        if not hasattr( self, '_palette' ):
            self._palette = [img.Transparent()] + self.palette_vga_standard[1:] + self.palette_vga_custom
        return self._palette


class VgagrStore( mrc.Block ):
    """Represents a blob store for style graphics."""
    data = mrc.Bytes( 0x0000 )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.store = mrc.Store( self, mrc.Ref( 'data' ) )


class VgagrDAT( mrc.Block ):
    stores = mrc.BlockField( VgagrStore, 0x0000, stream=True, transform=DATCompressor() )

    @property
    def terrain_store( self ):
        return self.stores[0]

    @property
    def interact_store( self ):
        return self.stores[1]


##########
# main.dat parser
##########

class Anim( mrc.Block ):
    image_data           =  mrc.Bytes( 0x0000, transform=img.Planarizer( bpp=mrc.Ref( 'bpp' ), width=mrc.Ref( 'width' ), height=mrc.Ref( 'height' ), frame_count=mrc.Ref( 'frame_count' ) ) )

    def __init__( self, width, height, bpp, frame_count, *args, **kwargs ):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.frame_count = frame_count
        self.image = img.IndexedImage( self, width=width, height=height, source=mrc.Ref( 'image_data' ), frame_count=frame_count, palette=LEMMINGS_VGA_DEFAULT_PALETTE )
        super().__init__( *args, **kwargs )


AnimField = lambda offset, width, height, bpp, frame_count: mrc.BlockField( Anim, offset, block_kwargs={ 'width': width, 'height': height, 'bpp': bpp, 'frame_count': frame_count } )


# the following animation/sprite lookup tables are embedded in the Lemmings executable
class MainAnims( mrc.Block ):
    anim_walker_r =         AnimField( 0x0000, 16, 10, 2, 8 )
    anim_bounder_r =        AnimField( 0x0140, 16, 10, 2, 1 )
    anim_walker_l =         AnimField( 0x0168, 16, 10, 2, 8 )
    anim_bounder_l =        AnimField( 0x02a8, 16, 10, 2, 1 )
    anim_digger =           AnimField( 0x02d0, 16, 14, 3, 16 )
    anim_climber_r =        AnimField( 0x0810, 16, 12, 2, 8 )
    anim_climber_l =        AnimField( 0x0990, 16, 12, 2, 8 )
    anim_drowner =          AnimField( 0x0b10, 16, 10, 2, 16 )
    anim_postclimber_r =    AnimField( 0x0d90, 16, 12, 2, 8 )
    anim_postclimber_l =    AnimField( 0x0f10, 16, 12, 2, 8 )
    anim_builder_r =        AnimField( 0x1090, 16, 13, 3, 16 )
    anim_builder_l =        AnimField( 0x1570, 16, 13, 3, 16 )
    anim_basher_r =         AnimField( 0x1a50, 16, 10, 3, 32 )
    anim_basher_l =         AnimField( 0x21d0, 16, 10, 3, 32 )
    anim_miner_r =          AnimField( 0x2950, 16, 13, 3, 24 )
    anim_miner_l =          AnimField( 0x30a0, 16, 13, 3, 24 )
    anim_faller_r =         AnimField( 0x37f0, 16, 10, 2, 4 )
    anim_faller_l =         AnimField( 0x3890, 16, 10, 2, 4 )
    anim_prefloater_r =     AnimField( 0x3930, 16, 16, 3, 4 )
    anim_floater_r =        AnimField( 0x3ab0, 16, 16, 3, 4 )
    anim_prefloater_l =     AnimField( 0x3c30, 16, 16, 3, 4 )
    anim_floater_l =        AnimField( 0x3db0, 16, 16, 3, 4 )
    anim_splatter =         AnimField( 0x3f30, 16, 10, 2, 16 )
    anim_leaver =           AnimField( 0x41b0, 16, 13, 2, 8 )
    anim_burner =           AnimField( 0x4350, 16, 14, 4, 14 )
    anim_blocker =          AnimField( 0x4970, 16, 10, 2, 16 )
    anim_shrugger_r =       AnimField( 0x4bf0, 16, 10, 2, 8 )
    anim_shrugger_l =       AnimField( 0x4d30, 16, 10, 2, 8 )
    anim_goner =            AnimField( 0x4e70, 16, 10, 2, 16 )
    anim_exploder =         AnimField( 0x5070, 32, 32, 3, 1 )


class MainMasks( mrc.Block ):
    mask_basher_r =         AnimField( 0x0000, 16, 10, 1, 4 )
    mask_basher_l =         AnimField( 0x0050, 16, 10, 1, 4 )
    mask_miner_r =          AnimField( 0x00a0, 16, 13, 1, 2 )
    mask_miner_l =          AnimField( 0x00d4, 16, 13, 1, 2 )
    mask_exploder =         AnimField( 0x0108, 16, 22, 1, 1 )

    number_9 =              AnimField( 0x0134, 8, 8, 1, 1 )
    number_8 =              AnimField( 0x013c, 8, 8, 1, 1 )
    number_7 =              AnimField( 0x0144, 8, 8, 1, 1 )
    number_6 =              AnimField( 0x014c, 8, 8, 1, 1 )
    number_5 =              AnimField( 0x0154, 8, 8, 1, 1 )
    number_4 =              AnimField( 0x015c, 8, 8, 1, 1 )
    number_3 =              AnimField( 0x0164, 8, 8, 1, 1 )
    number_2 =              AnimField( 0x016c, 8, 8, 1, 1 )
    number_1 =              AnimField( 0x0174, 8, 8, 1, 1 )
    number_0 =              AnimField( 0x017c, 8, 8, 1, 1 )


class MainHUDGraphicsHP( mrc.Block ):
    pass


class MainMenuGraphics( mrc.Block ):
    pass


class MainMenuAnims( mrc.Block ):
    pass


class MainSection5( mrc.Block ):
    pass


class MainHUDGraphics( mrc.Block ):
    pass


class MainDAT( mrc.Block ):
    pass
    #main_anims = mrc.BlockField( MainAnims, 0x0000, stream=True, transform=DATCompressor() )
    #main_masks = mrc.BlockField( MainMasks, mrc.EndOffset( 'main_anims' ), stream=True, transform=DATCompressor() )
    #main_hud_graphics_hp = mrc.BlockField( MainHUDGraphicsHP, transform=DATCompressor() )
    #main_menu_graphics = mrc.BlockField( MainMenuGraphics, transform=DATCompressor() )
    #main_menu_anims = mrc.BlockField( MainMenuAnims, transform=DATCompressor() )
    #main_section_5 = mrc.BlockField( MainSection5, transform=DATCompressor() )
    #main_hud_graphics = mrc.BlockField( MainHUDGraphics, transform=DATCompressor() )

    
##########
# vgaspecX.dat parser
##########

class Special( mrc.Block ):
    palette_vga =           img.Palette( ibm_pc.VGAColour, 0x0000, count=8 )
    palette_ega =           img.Palette( ibm_pc.EGAColour, 0x0018, count=8 )
    palette_ega_preview  =  img.Palette( ibm_pc.EGAColour, 0x0020, count=8 )

    image_data           =  mrc.Bytes( 0x0028, transform=SpecialCompressor() )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage( self, width=960, height=160, source=mrc.Ref( 'image_data' ), palette=mrc.Ref( 'palette_vga' ) )


class VgaspecDAT( mrc.Block ):
    special = mrc.BlockField( Special, 0x0000, transform=DATCompressor() )


##########
# file loader
##########
    
class Loader( mrc.Loader ):
    _SEP = mrc.Loader._SEP

    _LEMMINGS_FILE_CLASS_MAP = {
        _SEP+'(ADLIB).DAT$': None,
        _SEP+'(CGAGR)(\d).DAT$': None,
        _SEP+'(CGAMAIN).DAT$': None,
        _SEP+'(CGASPEC)(\d).DAT$': None,
        _SEP+'(GROUND)(\d)O.DAT$': GroundDAT,
        _SEP+'(LEVEL)00(\d).DAT$': LevelDAT,
        _SEP+'(MAIN).DAT$': MainDAT,
        _SEP+'(ODDTABLE).DAT$': OddtableDAT,
        _SEP+'(RUSSELL).DAT$': None,
        _SEP+'(TGAMAIN).DAT$': None,
        _SEP+'(VGAGR)(\d).DAT$': VgagrDAT,
        _SEP+'(VGASPEC)(\d).DAT$': VgaspecDAT,
    }

    _LEMMINGS_DEPS = [
        (_SEP+'(GROUND)(\d)O.DAT$', _SEP+'(VGAGR)(\d).DAT$', ('VGAGR', '{1}'), '_vgagr')
    ]

    def __init__( self ):
        super().__init__( self._LEMMINGS_FILE_CLASS_MAP, dependency_list=self._LEMMINGS_DEPS )

    def post_load( self ):

        # TODO: wire up inter-file class relations here
        return
