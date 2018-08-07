"""File format classes for games released by Presage Software."""

from mrcrowbar import models as mrc
from mrcrowbar import utils


class PRSChunk( mrc.Block ):
    tag = mrc.Bytes( 0x00, length=4 )
    unk1 = mrc.UInt16_LE( 0x04 )
    name = mrc.CStringN( 0x06, length=0x12 )
    size = mrc.UInt32_LE( 0x18 )  # length of chunk header + data
    data = mrc.Bytes( 0x1c, length=mrc.Ref( 'size_data' ) )

    @property
    def size_data( self ):
        return self.size - 0x1c


class PRSFile( mrc.Block ):
    magic = mrc.Const( mrc.Bytes( 0x00, length=0x18 ), b'PRS Format Resource File' )
    unk1 = mrc.UInt8( 0x18 )
    unk2 = mrc.UInt8( 0x19 )
    unk3 = mrc.UInt8( 0x1f )
    chunks = mrc.BlockField( PRSChunk, 0x30, stream=True )
