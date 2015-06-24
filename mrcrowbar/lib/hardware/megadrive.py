#!/usr/bin/python3

import array
import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img


# source: http://segaretro.org/Palette#Mega_Drive_Palette

class VDPColour( img.Colour ):
    _block_size =   2
    b_raw = mrc.Bits( 0x0000, 0b00001110 )
    g_raw = mrc.Bits( 0x0001, 0b11100000 )
    r_raw = mrc.Bits( 0x0001, 0b00001110 )

    @property
    def r_8( self ):
        return (self.r_raw << 5)

    @property
    def g_8( self ):
        return (self.g_raw << 5)

    @property
    def b_8( self ):
        return (self.b_raw << 5)

    @property
    def r( self ):
        return self.r_raw/7

    @property
    def g( self ):
        return self.g_raw/7

    @property
    def b( self ):
        return self.b_raw/7



# source: http://www.emulatronia.com/doctec/consolas/megadrive/genesis_rom.txt

class SuperMagicDriveInterleave( mrc.Transform ):
    def import_data( self, buffer ):
        
        def deinterleave_block( block ):
            output = array.array( 'B', b'\x00'*len( block ) )
            for i in range( len( output ) ):
                if (i % 2):
                    index = i//2
                else:
                    index = (len( output )//2) + (i//2)
                output[i] = block[index]
            return output

        output = array.array( 'B', b'\x00'*(len( buffer )-512) )

        for i in range( 0, len( buffer )-512, 16384 ):
            block = buffer[512:][i:i+16384]
            output[i:i+16384] = deinterleave_block( block )

        return output



