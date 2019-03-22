#!/usr/bin/python3

from mrcrowbar import models as mrc, ansi, utils
from mrcrowbar.lib.hardware import ibm_pc

# map of DOS code page 437 to Unicode
CP437 = """ ☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ """


def decode_nfo( buffer ):
    """Decodes a byte string in NFO format (beloved by PC scener groups) from DOS Code Page 437 
    to Unicode."""
    assert utils.is_bytes( buffer )
    return '\n'.join( [''.join( [CP437[y] for y in x] ) for x in buffer.split( b'\r\n' )] )


class B800Char( mrc.Block ):
    _palette =      ibm_pc.EGA_DEFAULT_PALETTE

    code_point =    mrc.UInt8( 0x00 )
    fg_blink =      mrc.Bits( 0x01, 0b10000000 )
    bg_colour =     mrc.Bits( 0x01, 0b01110000 )
    fg_colour =     mrc.Bits( 0x01, 0b00001111 )

    @property
    def char( self ):
        return CP437[self.code_point]

    def ansi_format( self ):
        return ansi.format_string( 
            self.char, self._palette[self.fg_colour], self._palette[self.bg_colour], blink=self.fg_blink
        )

    def __str__( self ):
        return self.ansi_format()

    def __repr__( self ):
        return '<{}: char {}, bg {}, fg {}>'.format( self.__class__.__name__, self.char, self.bg_colour, self.fg_colour )
        
    
class B800Screen( mrc.Block ):
    B800_SCREEN_WIDTH =  80

    chars = mrc.BlockField( B800Char, 0x00, count=2000 )

    @property
    def text( self ):
        return '\n'.join( 
            [''.join( 
                [c.char for c in self.chars[i*self.B800_SCREEN_WIDTH:][:self.B800_SCREEN_WIDTH]] 
            ) for i in range( (len( self.chars )+1)//self.B800_SCREEN_WIDTH )] 
        )

    def ansi_format( self ):
        result = []
        for i in range( (len( self.chars )+1)//self.B800_SCREEN_WIDTH ):
            for c in self.chars[i*self.B800_SCREEN_WIDTH:][:self.B800_SCREEN_WIDTH]:
                result.append( c.ansi_format() )
            result.append( '\n' )
        return ''.join( result )

    def print( self ):
        print( self.ansi_format() )

    def __str__( self ):
        return self.ansi_format()

    def __repr__( self ):
        return '<{}: {} chars, {}x{}>'.format( self.__class__.__name__, len( self.chars ), self.B800_SCREEN_WIDTH, 1+(len( self.chars )-1)//self.B800_SCREEN_WIDTH )


# source: https://www.fileformat.info/format/exe/corion-mz.htm

class Relocation( mrc.Block ):
    offset =    mrc.UInt16_LE( 0x00 )
    segment =   mrc.UInt16_LE( 0x02 )


class MZHeader( mrc.Block ):
    magic =         mrc.Const( mrc.Bytes( 0x00, length=2 ), b'MZ' )
    last_page_size =     mrc.UInt16_LE( 0x02 )
    page_count =    mrc.UInt16_LE( 0x04 )
    reltable_count = mrc.UInt16_LE( 0x06 )
    header_size_raw =   mrc.UInt16_LE( 0x08 )
    min_alloc_raw =     mrc.UInt16_LE( 0x0a )
    max_alloc_raw =     mrc.UInt16_LE( 0x0c )
    initial_ss =    mrc.UInt16_LE( 0x0e )
    initial_sp =    mrc.UInt16_LE( 0x10 )
    checksum =      mrc.UInt16_LE( 0x12 )
    initial_ip =    mrc.UInt16_LE( 0x14 )
    initial_cs =    mrc.UInt16_LE( 0x16 )
    reltable_offset = mrc.UInt16_LE( 0x18 )
    overlay =       mrc.UInt16_LE( 0x1a )

    @property
    def header_size( self ):
        return self.header_size_raw * 16

    @header_size.setter
    def header_size( self, value ):
        self.header_size_raw = (value // 16) + (1 if value % 16 else 0)

    @property
    def extra_offset( self ):
        return self.page_count * 512


class EXE( mrc.Block ):
    mz_header = mrc.BlockField( MZHeader, 0x00 )

