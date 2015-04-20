#!/usr/bin/python3

import array

from mrcrowbar import models as mrc


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

    animated =          mrc.BlockStream( Animated, 0x0020, stride=0x08, count=32 )
    terrain =           mrc.BlockStream( Terrain, 0x0120, stride=0x04, count=400, fill=b'\xff' )
    steel =             mrc.BlockStream( SteelArea, 0x0760, stride=0x04, count=32 )
    level_name =        mrc.Bytes( 0x07e0, 32, default=b'                                ' )

    @property
    def camera_x( self ):
        return self.camera_x_raw - (self.camera_x_raw % 8)


class DATCompressor( mrc.Transform ):
    
    def import_data( self, buffer ):
        assert type( buffer ) == bytes
        def get_next_bits( n, state ):
            result = 0
            while True:
                state['bitcnt'] -= 1
                if state['bitcnt'] == 0:
                    state['cptr'] -= 1
                    state['curbits'] = state['cdata'][state['cptr']]
                    state['checksum'] ^= state['curbits']
                    state['bitcnt'] = 8
                result <<= 1;
                result |= (state['curbits'] & 1)
                state['curbits'] >>= 1;
                
                n -= 1
                if not n>0: 
                    break
            return result
        
        def copy_prev_data( blocklen, offset_size, state ):
            offset = get_next_bits( offset_size, state )
            for i in range( 0, blocklen ):
                state['dptr'] -= 1
                state['ddata'][state['dptr']] = state['ddata'][state['dptr']+offset+1]
            return
        
        def dump_data( numbytes, state ):
            while True:
                state['dptr'] -= 1
                state['ddata'][state['dptr']] = get_next_bits( 8, state )
                
                numbytes -= 1
                if not numbytes>0:
                    break
            return
        
        
        pointer = 0;
        target = []
        total_num_bytes = len( buffer )
        while True:
            bit_count = buffer[pointer]
            checksum = buffer[pointer+1]
            decompressed_size = buffer[pointer+4]*0x100 + buffer[pointer+5]
            compressed_size = buffer[pointer+8]*0x100 + buffer[pointer+9]
            
            print( '----   HEADER   ----' )
            print( 'bit_count = {}'.format( bit_count ) )
            print( 'checksum = {}'.format( checksum ) )
            print( 'decompressed_size = {}'.format( decompressed_size ) )
            print( 'compressed_size = {}'.format( compressed_size ) )
            print( '---- END HEADER ----' )
        
            print( 'Decompressing data...' )
            
            pointer += 10
            total_num_bytes -= 10
            compressed_size -= 10
            
            compressed_data = buffer[pointer:pointer+compressed_size]
            pointer += compressed_size
            
            total_num_bytes -= compressed_size
        
            state = { 
                'bitcnt': bit_count+1, 'cptr': (compressed_size-1), 
                'dptr': decompressed_size, 'cdata': compressed_data, 
                'ddata': [0]*decompressed_size,
                'curbits': compressed_data[-1], 'checksum': compressed_data[-1]
            }
            
            while True:
                if get_next_bits( 1, state )==1:
                    test = get_next_bits( 2, state )
                    if test==0:
                        copy_prev_data( 3, 9, state )
                    elif test==1:
                        copy_prev_data( 4, 10, state )
                    elif test==2:
                        copy_prev_data( get_next_bits( 8, state )+1, 12, state )
                    elif test==3:
                        dump_data( get_next_bits( 8, state )+9, state )
                else:
                    test = get_next_bits( 1, state )
                    if test==0:
                        dump_data( get_next_bits( 3, state )+1, state )
                    elif test==1:
                        copy_prev_data( 2, 8, state )
                
                if not (state['dptr'] > 0): 
                    break
            
            print( 'Done!' )
                    
            if checksum != state['checksum']:
                print( 'Warning: checksum doesn\'t match header' )
            
            target.append( bytes( state['ddata'] ) )  
            if not total_num_bytes > 0:
                break
            
        return target
