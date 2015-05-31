#!/usr/bin/python3

import array
import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.os import dos
from mrcrowbar.lib.images import base as img
from mrcrowbar.utils import BitStream


class Animated( mrc.Block ):
    _block_size =       8
    
    x_raw =             mrc.Int16_BE( 0x00, range=range( -8, 1593 ) )
    y =                 mrc.Int16_BE( 0x02, range=range( -41, 160 ) )
    obj_id =            mrc.UInt16_BE( 0x04, range=range( 0, 16 ) )
    draw_back =         mrc.Bits( 0x06, 0b10000000 )
    draw_masked =       mrc.Bits( 0x06, 0b01000000 )
    draw_upsidedown =   mrc.Bits( 0x07, 0b10000000 )

    mod_check =         mrc.Check( mrc.UInt16_BE( 0x06, bitmask=b'\x3f\x7f' ), 0x000f )

    @property
    def x( self ):
        return (self.x_raw-16) - ((self.x_raw-16) % 8)


class Terrain( mrc.Block ):
    _block_size =       4

    x_raw =             mrc.UInt16_BE( 0x00, bitmask=b'\x0f\xff', range=range( 0, 1600 ) )
    draw_back =         mrc.Bits( 0x00, 0b10000000 )
    draw_upsidedown =   mrc.Bits( 0x00, 0b01000000 )
    draw_erase =        mrc.Bits( 0x00, 0b00100000 )
    y_raw_coarse =      mrc.Int8( 0x02, range=range( -17, 82 ) )
    y_raw_fine =        mrc.Bits( 0x03, 0b10000000 )
    obj_id =            mrc.UInt8( 0x03, bitmask=b'\x3f', range=range( 0, 64 ) )

    mod_check =         mrc.Check( mrc.UInt8( 0x03, bitmask=b'\x40' ), 0x00 )

    @property
    def x( self ):
        return (self.x_raw-16)

    @property
    def y( self ):
        return (self.y_raw_coarse*2 + self.y_raw_fine)-4
    

class SteelArea( mrc.Block ):
    _block_size =       4

    x_raw_coarse =      mrc.UInt8( 0x00, range=range( 0, 200 ) )
    x_raw_fine =        mrc.Bits( 0x01, 0b10000000 )
    y_raw =             mrc.UInt8( 0x01, bitmask=b'\x2f', range=range( 0, 157 ) )
    width_raw =         mrc.Bits( 0x02, 0b11110000 )
    height_raw =        mrc.Bits( 0x02, 0b00001111 )

    mod_check =         mrc.Check( mrc.UInt8( 0x03 ), 0x00 )
    
    @property
    def x( self ):
        return (self.x_raw_coarse*2 + self.x_raw_fine)*4-16

    @property
    def y( self ):
        return (self.y_raw*4)

    @property
    def width( self ):
        return (self.width_raw+1)*4

    @property
    def height( self ):
        return (self.height_raw+1)*4


class Level( mrc.Block ):
    _block_size =       2048

    release_rate =      mrc.UInt16_BE( 0x0000, range=range( 0, 251 ) )
    num_released =      mrc.UInt16_BE( 0x0002, range=range( 0, 115 ) )
    num_to_save =       mrc.UInt16_BE( 0x0004, range=range( 0, 115 ) )
    time_limit_mins =   mrc.UInt16_BE( 0x0006, range=range( 0, 256 ) )
    num_climbers =      mrc.UInt16_BE( 0x0008, range=range( 0, 251 ) )
    num_floaters =      mrc.UInt16_BE( 0x000a, range=range( 0, 251 ) )
    num_bombers =       mrc.UInt16_BE( 0x000c, range=range( 0, 251 ) )
    num_blockers =      mrc.UInt16_BE( 0x000e, range=range( 0, 251 ) )
    num_builders =      mrc.UInt16_BE( 0x0010, range=range( 0, 251 ) )
    num_bashers =       mrc.UInt16_BE( 0x0012, range=range( 0, 251 ) )
    num_miners =        mrc.UInt16_BE( 0x0014, range=range( 0, 251 ) )
    num_diggers =       mrc.UInt16_BE( 0x0016, range=range( 0, 251 ) )
    camera_x_raw =      mrc.UInt16_BE( 0x0018, range=range( 0, 1265 ) )
    style_index =       mrc.UInt16_BE( 0x001a )
    custom_index =      mrc.UInt16_BE( 0x001c )

    animated =          mrc.BlockStream( Animated, 0x0020, stride=0x08, count=32, fill=b'\x00' )
    terrain =           mrc.BlockStream( Terrain, 0x0120, stride=0x04, count=400, fill=b'\xff' )
    steel =             mrc.BlockStream( SteelArea, 0x0760, stride=0x04, count=32, fill=b'\x00' )
    level_name =        mrc.Bytes( 0x07e0, 32, default=b'                                ' )

    @property
    def camera_x( self ):
        return self.camera_x_raw - (self.camera_x_raw % 8)


# groundXo.dat and vgagrX.dat parser
# source docs: http://www.camanis.net/lemmings/files/docs/lemmings_vgagrx_dat_groundxo_dat_file_format.txt
# extra special thanks: ccexplore

class AnimatedInfo( mrc.Block ):
    _block_size =       28

    anim_flags =        mrc.UInt16_LE( 0x0000 )
    start_frame =       mrc.UInt8( 0x0002 )
    end_frame =         mrc.UInt8( 0x0003 )
    width =             mrc.UInt8( 0x0004 )
    height =            mrc.UInt8( 0x0005 )
    frame_data_size =   mrc.UInt16_LE( 0x0006 )
    mask_rel_offset =   mrc.UInt16_LE( 0x0008 )
    
    trigger_x_raw =         mrc.UInt16_LE( 0x000e )
    trigger_y_raw =         mrc.UInt16_LE( 0x0010 )
    trigger_width_raw =     mrc.UInt8( 0x0012 )
    trigger_height_raw =    mrc.UInt8( 0x0013 )
    trigger_effect_id =     mrc.UInt8( 0x0014 )

    base_offset =       mrc.UInt16_LE( 0x0015 )
    preview_frame =     mrc.UInt16_LE( 0x0017 )

    sound_id =          mrc.UInt8( 0x001b )
    
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


class TerrainInfo( mrc.Block ):
    _block_size =       8

    width =             mrc.UInt8( 0x0000 )
    height =            mrc.UInt8( 0x0001 )
    base_offset =       mrc.UInt16_LE( 0x0002 )
    mask_rel_offset =   mrc.UInt16_LE( 0x0004 )


class Style( mrc.Block ):
    _block_size =   1056

    anim_info =     mrc.BlockStream( AnimatedInfo, 0x0000, stride=0x1c, count=16, fill=b'\x00' )
    terrain_info =  mrc.BlockStream( TerrainInfo, 0x01c0, stride=0x08, count=64, fill=b'\x00' )

    palette_ega_custom      = mrc.BlockStream( dos.EGAColour, 0x03c0, stride=0x01, count=8 )
    palette_ega_standard    = mrc.BlockStream( dos.EGAColour, 0x03c8, stride=0x01, count=8 )
    palette_ega_preview     = mrc.BlockStream( dos.EGAColour, 0x03d0, stride=0x01, count=8 )
    palette_vga_custom      = mrc.BlockStream( dos.VGAColour, 0x03d8, stride=0x03, count=8 )
    palette_vga_standard    = mrc.BlockStream( dos.VGAColour, 0x03f0, stride=0x03, count=8 )
    palette_vga_preview     = mrc.BlockStream( dos.VGAColour, 0x0408, stride=0x03, count=8 )


class SpecialCompressor( mrc.Transform ):

    def import_data( self, buffer ):
        assert type( buffer ) == bytes
        result = []
        buf_out = []
        i = 0
        while i < len( buffer ):
            if buffer[i] in range( 0x00, 0x80 ):
                count = buffer[i]+1
                buf_out.append( buffer[i+1:i+1+count] )
                i += count+1
            elif buffer[i] == 0x80:
                product = b''.join( buf_out )
                if len( product ) != 14400:
                    print( 'Warning: was expecting 14400 bytes of data, got {}'.format( len( product ) ) )
                result.append( product )
                buf_out = []
                i += 1
            else:
                count = 257-buffer[i]
                buf_out.append( buffer[i+1:i+2]*count )
                i += 2

        if buf_out:
            print( 'Warning: EOF reached before last RLE block closed' )
            result.append( b''.join( buf_out ) )

        # result is a 960x160 3bpp image, divided into 4x 40 scanline segments
        pl = img.Planarizer( 960, 40, 3 )
        unpack = [pl.import_data(x) for x in result]
        return bytes( itertools.chain( *unpack ) )


class Special( mrc.Block ):
    palette_vga =           mrc.BlockStream( dos.VGAColour, 0x0000, stride=0x03, count=8 )
    palette_ega =           mrc.BlockStream( dos.EGAColour, 0x0018, stride=0x01, count=8 )
    palette_ega_preview  =  mrc.BlockStream( dos.EGAColour, 0x0020, stride=0x01, count=8 )

    image =                 mrc.BlockField( img.RawIndexedImage, 0x0028, transform=SpecialCompressor() )


AnimField = lambda offset, width, height, bpp, frame_count: mrc.BlockField( img.RawIndexedImage, offset, transform=img.Planarizer( width, height, bpp, frame_count=frame_count ) )

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


class DATCompressor( mrc.Transform ):
    def import_data( self, buffer ):
        assert type( buffer ) == bytes

        def xor_checksum( data ):
            lrc = 0
            for b in data:
                lrc ^= b
            return lrc

        def copy_prev_data( blocklen, offset_size, state ):
            offset = state['bs'].get_bits( offset_size )
            for i in range( blocklen ):
                state['dptr'] -= 1
                state['ddata'][state['dptr']] = state['ddata'][state['dptr']+offset+1]
            return
        
        def dump_data( num_bytes, state ):
            for i in range( num_bytes ):
                state['dptr'] -= 1
                state['ddata'][state['dptr']] = state['bs'].get_bits( 8 )
            return
        
        
        pointer = 0;
        target = []
        total_num_bytes = len( buffer )
        while True:
            bit_count = buffer[pointer]
            checksum = buffer[pointer+1]
            decompressed_size = buffer[pointer+4]*0x100 + buffer[pointer+5]
            compressed_size = buffer[pointer+8]*0x100 + buffer[pointer+9]
            
            #print( '----   HEADER   ----' )
            #print( 'bit_count = {}'.format( bit_count ) )
            #print( 'checksum = {}'.format( checksum ) )
            #print( 'decompressed_size = {}'.format( decompressed_size ) )
            #print( 'compressed_size = {}'.format( compressed_size ) )
            #print( '---- END HEADER ----' )
            #print( 'Decompressing data...' )
            
            pointer += 10
            total_num_bytes -= 10
            compressed_size -= 10
            
            compressed_data = buffer[pointer:pointer+compressed_size]
            #print( 'computed checksum = {}'.format( xor_checksum( compressed_data ) ) )
            if checksum != xor_checksum( compressed_data ):
                print( 'Warning: checksum doesn\'t match header' )
            
            pointer += compressed_size
            total_num_bytes -= compressed_size
        
            bs = BitStream( compressed_data, compressed_size-1, bytes_reverse=True )
            bs.bits_remaining = bit_count
            
            state = { 
                'bs': bs,
                'dptr': decompressed_size, 
                'ddata': array.array( 'B', b'\x00'*decompressed_size ),
            }

            while True:
                if bs.get_bits( 1 )==1:
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
            
            #print( 'Done!' )
                    
            target.append( bytes( state['ddata'] ) )  
            if not total_num_bytes > 0:
                break
            
        return target



