
import itertools

from mrcrowbar import models as mrc, utils
from mrcrowbar.lib.hardware import megadrive as md
from mrcrowbar.lib.images import base as img
from mrcrowbar.utils import BitReader


class LevelPalette( mrc.Block ):
    palette =   mrc.BlockField( md.VDPColour, 0x0000, count=16 )


# source: http://segaretro.org/Enigma_compression

class EnigmaCompressor( mrc.Transform ):
    def __init__( self, starting_tile ):
        assert type( starting_tile ) == md.VDPBlockMapping8
        self.starting_tile = starting_tile

    def import_data( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        inline_copy_bits = buffer[0]

        high_priority_flag = mrc.Bits( 0x01, 0b00010000 ).get_from_buffer( buffer )
        palette_offset = mrc.Bits( 0x01, 0b00001100 ).get_from_buffer( buffer )
        flip_horiz = mrc.Bits( 0x01, 0b00000010 ).get_from_buffer( buffer )
        flip_vert = mrc.Bits( 0x01, 0b00000001 ).get_from_buffer( buffer )

        incremental_copy = mrc.UInt16_BE( 0x02 ).get_from_buffer( buffer )
        literal_copy = mrc.UInt16_BE( 0x04 ).get_from_buffer( buffer )

        bs = BitStream( buffer[0x06:], 0, bits_reverse=True )
        output = bytearray()
        #while True:
        #    test = bs.get_bits( 1 )
        #    if test == 1:
        #        test = bs.get_bits( 2 )
        #        repeat_count = bs.get_bits( 4 )+1
        #        if (test == 3) and (repeat_count == 0x0f):
        #            break
        #        
        #        if high_priority_flag:
        #
        # 
        #        if test == 0:
        #            
        #        elif test == 1:
        #
        #        elif test == 2:
        #        
        #        else:
        #
        #    else:
        #        test = bs.get_bits( 1 )
        #        repeat_count = bs.get_bits( 4 )+1
        #        if test == 0:
        #            for i in range( repeat_count ):
        #                output.append( (incremental_copy >> 8) )
        #                output.append( (incremental_copy & 0xff ) )
        #                incremental_copy += 1
        #        else:
        #            for i in range( repeat_count ):
        #                output.append( (literal_copy >> 8) )
        #                output.append( (literal_copy & 0xff) )






# source: http://segaretro.org/Nemesis_compression

class NemesisCompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        pattern_count = mrc.UInt16_BE( 0x0000 ).get_from_buffer( buffer )
        xor_mode = (pattern_count & 0x8000) != 0
        pattern_count &= 0x7fff

        index = 2
        lut = {}
        prev_pal_index = 0
        while index < len( buffer ):
            test = buffer[index]
            if test == 0xff:
                break
            elif test & 0x80:
                code_raw = buffer[index+2]
                bit_count = buffer[index+1] & 0x0f
                code = ''.join(['1' if (code_raw & (1<<i) ) else '0' for i in range( bit_count-1, -1, -1 )])

                lut[code] = {
                    'pal_index': buffer[index] & 0x0f,
                    'copy_count': ((buffer[index+1] & 0xf0) >> 4) + 1,
                }
                prev_pal_index = lut[code]['pal_index']
                index += 3
            else:
                code_raw = buffer[index+1]
                bit_count = buffer[index] & 0x0f
                code = ''.join(['1' if (code_raw & (1<<i) ) else '0' for i in range( bit_count-1, -1, -1 )])

                lut[code] = {
                    'pal_index': prev_pal_index,
                    'copy_count': ((buffer[index] & 0xf0) >> 4) + 1,
                }
                index += 2

        bs = BitReader( buffer[index+1:], 0, bits_reverse=True )

        state = {
            'output': bytearray( 64*pattern_count ),
            'output_index': 0,
            'current_row': [],
            'prev_row': bytearray( 8 )
        }

        def push_pal( pal, state ):
            state['current_row'].append( pal )
            if len( state['current_row'] ) == 8:
                output_index = state['output_index']
                for i in range( 8 ):
                    state['output'][output_index+i] = state['current_row'][i]
                if xor_mode:
                    for i in range( 8 ):
                        state['output'][output_index+i] ^= state['prev_row'][i]
                    prev_row = state['output'][output_index:output_index+8]
                state['output_index'] += 8
                state['current_row'].clear()
            return

        max_key_size = max( [len(x) for x in lut.keys()] )
        while state['output_index'] < 64*pattern_count:
            test = ''
            for i in range( max_key_size ):
                test += '1' if bs.get_bits( 1 ) else '0'
                if test in lut or test == '111111':
                    break

            if test in lut:
                for i in range( lut[test]['copy_count'] ):
                    push_pal( lut[test]['pal_index'], state )
            elif test == '111111':
                copy_count = bs.get_bits( 3 )
                pal_index = bs.get_bits( 4 )
                for i in range( copy_count ):
                    push_pal( pal_index, state )
            else:
                raise Exception( 'Invalid code found in data stream, aborting' )
                
        return bytes( state['output'] )
       
    


