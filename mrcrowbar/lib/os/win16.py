#!/usr/bin/python3

from mrcrowbar import models as mrc, utils

# source: http://benoit.papillault.free.fr/c/disc2/exefmt.txt


class Segment( mrc.Block ):
    offset_sect =   mrc.UInt16_LE( 0x00 )
    size =          mrc.UInt16_LE( 0x02 )
    flags =         mrc.UInt16_LE( 0x04 )
    alloc_size =    mrc.UInt16_LE( 0x06 )

    @property
    def offset( self ):
        return self.offset_sect << self._parent.sector_shift

    @property
    def repr( self ):
        return 'offset_sect={:04x}, size={:04x}, flags={:04x}, alloc_size={:04x}'.format( self.offset_sect, self.size, self.flags, self.alloc_size )




class NEHeader( mrc.Block ):
    ne_magic =      mrc.Const( mrc.Bytes( 0x00, length=2 ), b'NE' )
    linker_ver =    mrc.UInt8( 0x02 )
    linker_rev =    mrc.UInt8( 0x03 )
    entry_offset =  mrc.UInt16_LE( 0x04 )
    entry_size =    mrc.UInt16_LE( 0x06 )
    crc =           mrc.UInt32_LE( 0x08 )
    flags =         mrc.UInt16_LE( 0x0c )
    ds_id =         mrc.UInt16_LE( 0x0e )
    heap_size =     mrc.UInt16_LE( 0x10 )
    stack_size =    mrc.UInt16_LE( 0x12 )
    cs_id =         mrc.UInt16_LE( 0x14 )
    ip_offset =     mrc.UInt16_LE( 0x16 )
    ss_id =         mrc.UInt16_LE( 0x18 )
    sp_offset =     mrc.UInt16_LE( 0x1a )
    segtable_count =    mrc.UInt16_LE( 0x1c )
    modref_size =       mrc.UInt16_LE( 0x1e )
    nonresnames_size =  mrc.UInt16_LE( 0x20 )
    segtable_offset =   mrc.UInt16_LE( 0x22 )
    restable_offset =   mrc.UInt16_LE( 0x24 )
    resnames_offset =   mrc.UInt16_LE( 0x26 )
    modref_offset =     mrc.UInt16_LE( 0x28 )
    impnames_offset =   mrc.UInt16_LE( 0x2a )
    nonresnames_offset =    mrc.UInt32_LE( 0x2c )
    movable_count =     mrc.UInt16_LE( 0x30 )
    sector_shift =      mrc.UInt16_LE( 0x32 )
    resource_count =    mrc.UInt16_LE( 0x34 )
    exe_type =          mrc.UInt8( 0x36 )
    padding =           mrc.Bytes( 0x37, length=9 )

    segtable =      mrc.BlockField( Segment, mrc.Ref( 'segtable_offset' ), count=mrc.Ref( 'segtable_count' ) )



class EXE( mrc.Block ):
    dos_magic =     mrc.Const( mrc.Bytes( 0x00, length=2 ), b'MZ' )
    dos_header =    mrc.Bytes( 0x02, length=0x3a )
    ne_offset =     mrc.UInt16_LE( 0x3c )
    # FIXME: size of the DOS stub should be dynamic based on ne_offset
    dos_stub =      mrc.Bytes( 0x3e, length=0x72 )

    ne_header =    mrc.BlockField( NEHeader, 0xb0 )


    
