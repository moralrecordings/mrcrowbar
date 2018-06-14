"""File format class for IPS binary patches.

Sources:
https://zerosoft.zophar.net/ips.php
"""

from mrcrowbar import models as mrc

class IPSRecord( mrc.Block ):
    offset_maj = mrc.UInt8( 0x00 )
    offset_min = mrc.UInt16_BE( 0x01 )
    size =       mrc.UInt16_BE( 0x03 )
    data =       mrc.Bytes( 0x05, length=mrc.Ref( 'size' ) )

    @property
    def offset( self ):
        return (self.offset_maj << 16) + self.offset_min

    @offset.setter
    def offset( self, value ):
        self.offset_maj = (value & 0xff0000) >> 16
        self.offset_min = value & 0x00ffff

    @property
    def repr( self ):
        return 'offset: 0x{:06x}, size: 0x{:04x}'.format( self.offset, self.size )


class IPS( mrc.Block ):
    magic =     mrc.Const( mrc.Bytes( 0x00, length=5 ), b'PATCH' )
    records =   mrc.BlockStream( IPSRecord, 0x05, stream_end=b'EOF' )

    @property
    def repr( self ):
        return 'records: {}'.format( len( self.records ) )


