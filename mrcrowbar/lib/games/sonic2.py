#!/usr/bin/python3

import array
import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import megadrive as md
from mrcrowbar.lib.images import base as img
from mrcrowbar.utils import BitReader



# source: http://segaretro.org/Nemesis_compression

class NemesisCompressor( mrc.Transform ):
    def import_data( self, buffer ):
        assert type( buffer ) == bytes
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
            'output': array.array( 'B', b'\x00'*64*pattern_count ),
            'output_index': 0,
            'current_row': [],
            'prev_row': array.array( 'B', b'\x00'*8 )
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
       
    


