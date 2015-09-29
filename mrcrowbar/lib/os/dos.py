#!/usr/bin/python3

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc

# map of DOS code page 437 to Unicode
CP437 = u"""\x00☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■\xa0"""

# example one-liner to read .NFO files
decode_nfo = lambda buffer: u'\n'.join( [u''.join( [CP437[y] for y in x] ) for x in buffer.split( b'\r\n' )] )


class B800Char( mrc.Block ):
    _block_size =   2
    _palette =      ibm_pc.EGA_DEFAULT_PALETTE

    code_point =    mrc.UInt8( 0x00 )
    bg_colour =     mrc.Bits( 0x01, 0b11110000 )
    fg_colour =     mrc.Bits( 0x01, 0b00001111 )

    @property
    def char( self ):
        return CP437[self.code_point]

    @property
    def ansi_format( self ):
        fg = '{};{};{}'.format( self._palette[self.fg_colour].r_8, 
                                self._palette[self.fg_colour].g_8, 
                                self._palette[self.fg_colour].b_8 )
        bg = '{};{};{}'.format( self._palette[self.bg_colour].r_8, 
                                self._palette[self.bg_colour].g_8, 
                                self._palette[self.bg_colour].b_8 )
        return u'\x1b[38;2;{};48;2;{}m{}'.format( fg, bg, self.char )

    def __str__( self ):
        return u'{}\x1b[0m'.format( self.ansi_format )
        
    
class B800Screen( mrc.Block ):
    B800_SCREEN_WIDTH =  80

    chars = mrc.BlockStream( B800Char, 0x00, count=2000, stride=0x02 )

    @property
    def text( self ):
        return u'\n'.join( [u''.join( [c.char for c in self.chars[i*self.B800_SCREEN_WIDTH:][:self.B800_SCREEN_WIDTH]] ) for i in range( (len( self.chars )+1)//self.B800_SCREEN_WIDTH )] )

    def print( self ):
        result = u''
        for i in range( (len( self.chars )+1)//self.B800_SCREEN_WIDTH ):
            for c in self.chars[i*self.B800_SCREEN_WIDTH:][:self.B800_SCREEN_WIDTH]:
                result += c.ansi_format
            result += u'\x1b[0m\n'
        print( result )
