#!/usr/bin/python3

from enum import IntEnum

from mrcrowbar import models as mrc, utils

# source: http://benoit.papillault.free.fr/c/disc2/exefmt.txt
# http://geos.icc.ru:8080/scripts/WWWBinV.dll/ShowR?NE.rfi

class Segment( mrc.Block ):
    offset_sect =       mrc.UInt16_LE( 0x00 )
    size =              mrc.UInt16_LE( 0x02 )
    data_seg =          mrc.Bits( 0x04, 0b00000001 )
    iterated =          mrc.Bits( 0x04, 0b00001000 )
    movable =           mrc.Bits( 0x04, 0b00010000 )
    shared =            mrc.Bits( 0x04, 0b00100000 )
    preload =           mrc.Bits( 0x04, 0b01000000 )
    exec_ro =           mrc.Bits( 0x04, 0b10000000 )
    relocations =       mrc.Bits( 0x05, 0b00000001 )
    conforming =        mrc.Bits( 0x05, 0b00000010 )
    privilege_level =   mrc.Bits( 0x05, 0b00001100 )
    discardable =       mrc.Bits( 0x05, 0b00010000 )
    op_size_32 =        mrc.Bits( 0x05, 0b00100000 )
    granularity =       mrc.Bits( 0x05, 0b01000000 )

    alloc_size =        mrc.UInt16_LE( 0x06 )

    @property
    def offset( self ):
        return self.offset_sect << self._parent.sector_shift

    @property
    def repr( self ):
        return 'offset_sect={:04x}, size={:04x}, data_seg={}, alloc_size={:04x}'.format( self.offset_sect, self.size, self.data_seg, self.alloc_size )


class ModuleSegment( Segment ):
    selector =          mrc.UInt16_LE( 0x08 )

    @property
    def repr( self ):
        return 'offset_sect=0x{:04x}, size=0x{:04x}, data_seg={}, alloc_size=0x{:04x}, selector={:04x}'.format( self.offset_sect, self.size, self.data_seg, self.alloc_size, self.selector )



class RelocationInternalRef( mrc.Block ):
    index =         mrc.UInt8( 0x00 )
    check =         mrc.Const( mrc.UInt8( 0x01 ), 0 )
    offset =        mrc.UInt16_LE( 0x02 )

    @property
    def repr( self ):
        return 'index=0x{:02x}, offset=0x{:04x}'.format( self.index, self.offset )


class RelocationImportName( mrc.Block ):
    index =         mrc.UInt16_LE( 0x00 )
    offset =        mrc.UInt16_LE( 0x02 )

    @property
    def repr( self ):
        return 'index=0x{:04x}, offset=0x{:04x}'.format( self.index, self.offset )


class RelocationImportOrdinal( mrc.Block ):
    index =         mrc.UInt16_LE( 0x00 )
    ordinal =       mrc.UInt16_LE( 0x02 )

    @property
    def repr( self ):
        return 'index=0x{:04x}, ordinal=0x{:04x}'.format( self.index, self.ordinal )


class RelocationOSFixup( mrc.Block ):
    fixup =         mrc.UInt16_LE( 0x00 )
    check =         mrc.Const( mrc.UInt16_LE( 0x02 ), 0 )

    @property
    def repr( self ):
        return 'fixup=0x{:04x}'.format( self.fixup )


class RelocationFlags( IntEnum ):
    INTERNAL_REF =      0x00
    IMPORT_ORDINAL =    0x01
    IMPORT_NAME =       0x02
    OS_FIXUP =          0x03


class RelocationAddressType( IntEnum ):
    LOW_BYTE =          0x00
    SELECTOR_16 =       0x02
    POINTER_32 =        0x03
    OFFSET_16 =         0x05
    POINTER_48 =        0x0b
    OFFSET_32 =         0x0d


class Relocation( mrc.Block ):
    address_type =      mrc.UInt8( 0x00, enum=RelocationAddressType )
    flags =             mrc.Bits( 0x01, 0b00000011, enum=RelocationFlags )
    additive =          mrc.Bits( 0x01, 0b00000100 )
    offset =            mrc.UInt16_LE( 0x02 )
    data =              mrc.Bytes( 0x04, length=0x04 )

    @property
    def repr( self ):
        return 'address_type={}, flags={}, offset=0x{:04x}, data={}'.format( str( self.address_type ), str( self.flags ), self.offset, self.data.hex() )


class RelocationTable( mrc.Block ):
    count = mrc.UInt16_LE( 0x00 )
    reltable = mrc.BlockField( Relocation, 0x02, count=mrc.Ref( 'count' ) )


# source: Matt Pietrek, "Windows Internals", 1993

class NEBase( mrc.Block ):
    ne_magic =      mrc.Const( mrc.Bytes( 0x00, length=2 ), b'NE' )

    entry_offset =  mrc.UInt16_LE( 0x04 )

    flags =         mrc.UInt16_LE( 0x0c )

    heap_size =     mrc.UInt16_LE( 0x10 )
    stack_size =    mrc.UInt16_LE( 0x12 )
    cs_id =         mrc.UInt16_LE( 0x14 )
    ip_offset =     mrc.UInt16_LE( 0x16 )
    ss_id =         mrc.UInt16_LE( 0x18 )
    sp_offset =     mrc.UInt16_LE( 0x1a )
    segtable_count =        mrc.UInt16_LE( 0x1c )
    modref_count =          mrc.UInt16_LE( 0x1e )
    nonresnames_size =      mrc.UInt16_LE( 0x20 )
    segtable_offset =       mrc.UInt16_LE( 0x22 )
    restable_offset =       mrc.UInt16_LE( 0x24 )
    resnames_offset =       mrc.UInt16_LE( 0x26 )
    modref_offset =         mrc.UInt16_LE( 0x28 )
    impnames_offset =       mrc.UInt16_LE( 0x2a )
    nonresnames_offset =    mrc.UInt32_LE( 0x2c )
    movable_count =         mrc.UInt16_LE( 0x30 )
    sector_shift =          mrc.UInt16_LE( 0x32 )

    exe_type =      mrc.UInt8( 0x36 )


class ModuleTable( NEBase ):
    usage_count =       mrc.UInt16_LE( 0x02 )

    next_table =        mrc.UInt16_LE( 0x06 )
    dgroup_offset =     mrc.UInt16_LE( 0x08 )
    fileinfo_offset =   mrc.UInt16_LE( 0x0a )

    dgroup_offset =     mrc.UInt16_LE( 0x0e )

    segtable =      mrc.BlockField( ModuleSegment, mrc.Ref( 'segtable_offset' ), count=mrc.Ref( 'segtable_count' ) )


class NEHeader( NEBase ):
    linker_ver =    mrc.UInt8( 0x02 )
    linker_rev =    mrc.UInt8( 0x03 )

    entry_size =    mrc.UInt16_LE( 0x06 )
    crc =           mrc.UInt32_LE( 0x08 )

    ds_id =         mrc.UInt16_LE( 0x0e )

    resource_count =        mrc.UInt16_LE( 0x34 )

    padding =       mrc.Bytes( 0x37, length=9 )

    segtable =      mrc.BlockField( Segment, mrc.Ref( 'segtable_offset' ), count=mrc.Ref( 'segtable_count' ) )


class EXE( mrc.Block ):
    dos_magic =     mrc.Const( mrc.Bytes( 0x00, length=2 ), b'MZ' )
    dos_header =    mrc.Bytes( 0x02, length=0x3a )
    ne_offset =     mrc.UInt16_LE( 0x3c )
    # FIXME: size of the DOS stub should be dynamic based on ne_offset
    #dos_stub =      mrc.Bytes( 0x3e, length=0x72 )

    ne_header =    mrc.BlockField( NEHeader, mrc.Ref( 'ne_offset' ) )

