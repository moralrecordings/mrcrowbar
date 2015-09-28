#!/usr/bin/python3

from mrcrowbar import models as mrc

# map of DOS code page 437 to Unicode
CP437 = u"""\x00☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■\xa0"""

# example one-liner to read .NFO files
decode_nfo = lambda buffer: u'\n'.join( [u''.join( [CP437[y] for y in x] ) for x in buffer.split( b'\r\n' )] )


class B800Char( mrc.Block ):
    _block_size =   2
    code_point =    mrc.UInt8( 0x00 )
    bg_colour =     mrc.Bits( 0x01, 0b11110000 )
    fg_colour =     mrc.Bits( 0x01, 0b00001111 )

    @property
    def char( self ):
        return CP437[self.code_point]

    def __str__( self ):
        return self.char
    
class B800Screen( mrc.Block ):
    B800_SCREEN_WIDTH =  80

    chars = mrc.BlockStream( B800Char, 0x00, count=2000, stride=0x02 )

    @property
    def text( self ):
        return u'\n'.join( [u''.join( [c.char for c in self.chars[i*self.B800_SCREEN_WIDTH:][:self.B800_SCREEN_WIDTH]] ) for i in range( (len( self.chars )+1)//self.B800_SCREEN_WIDTH )] )

