#!/usr/bin/python3

import array

from mrcrowbar import models as mrc
from mrcrowbar.utils import BitStream, BitWriter


# source: https://oku.edu.mie-u.ac.jp/~okumura/compression/lzss.c

class LZSSCompressor( mrc.Transform ):
    EI = 11
    EJ = 4
    P = 1
    N = (1 << EI)
    F = ((1 << EJ) + 1)

    def import_data( self, buffer ):
        r = self.N-self.F
        buf = array.array( 'B', b' '*(self.N*2) )
        bs = BitStream( buffer, 0, bytes_reverse=False, bits_reverse=True )
        result = array.array( 'B', b'' )
    
        try:
            while True:
                if bs.get_bits( 1 ):
                    buf[r] = bs.get_bits( 8 )
                    result.append( buf[r] )
                    r += 1
                    r &= (self.N-1)
                else:
                    i = bs.get_bits( self.EI )
                    j = bs.get_bits( self.EJ )
                    for k in range( j+2 ):
                        c = buf[(i+k) & (self.N-1)]
                        result.append( c )
                        buf[r] = c
                        r += 1
                        r &= (self.N-1);

        except IndexError:
            print( 'Hit EOF, stopping!' )

        return bytes( result )

#    def export_data( self, buffer ):
#
#        bw = BitWriter( bytes_reverse=False, bits_reverse=True )
#        result = array.array( 'B', b'' )
