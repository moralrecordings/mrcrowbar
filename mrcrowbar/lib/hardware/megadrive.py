#!/usr/bin/python3

import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img


# source: http://segaretro.org/Palette#Mega_Drive_Palette

class VDPBlockMapping8( mrc.Block ):
    priority        = mrc.Bits( 0x0000, 0b10000000 )
    palette_line    = mrc.Bits( 0x0000, 0b01100000 )
    flip_horiz      = mrc.Bits( 0x0000, 0b00010000 )
    flip_vert       = mrc.Bits( 0x0000, 0b00001000 )

    tile_index_high = mrc.Bits( 0x0000, 0b00000111 )
    tile_index_low  = mrc.UInt8( 0x0001 )
    
    @property
    def tile_index( self ):
        return ((tile_index_high << 8) + tile_index_low) * 0x20


class VDPColour( img.Colour ):
    b_raw = mrc.Bits( 0x0000, 0b00001110 )
    g_raw = mrc.Bits( 0x0001, 0b11100000 )
    r_raw = mrc.Bits( 0x0001, 0b00001110 )

    @property
    def r_8( self ):
        return (self.r_raw << 5)

    @r_8.setter
    def r_8( self, value ):
        self.r_raw = value >> 5

    @property
    def g_8( self ):
        return (self.g_raw << 5)

    @g_8.setter
    def g_8( self, value ):
        self.g_raw = value >> 5

    @property
    def b_8( self ):
        return (self.b_raw << 5)

    @b_8.setter
    def b_8( self, value ):
        self.b_raw = value >> 5


# source: http://www.emulatronia.com/doctec/consolas/megadrive/genesis_rom.txt

class SuperMagicDriveInterleave( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        
        def deinterleave_block( block ):
            output = bytearray( len( block ) )
            for i in range( len( output ) ):
                if (i % 2):
                    index = i//2
                else:
                    index = (len( output )//2) + (i//2)
                output[i] = block[index]
            return output

        output = bytearray( len( buffer )-512 )

        for i in range( 0, len( buffer )-512, 16384 ):
            block = buffer[512:][i:i+16384]
            output[i:i+16384] = deinterleave_block( block )

        return output



