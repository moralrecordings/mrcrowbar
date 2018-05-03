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
        return 'offset_sect={:04x}, size={:04x}, data_seg={}, relocations={}, alloc_size={:04x}'.format( self.offset_sect, self.size, self.data_seg, self.relocations, self.alloc_size )


class ModuleSegment( Segment ):
    selector =          mrc.UInt16_LE( 0x08 )

    @property
    def repr( self ):
        return 'offset_sect=0x{:04x}, size=0x{:04x}, data_seg={}, alloc_size=0x{:04x}, selector={:04x}'.format( self.offset_sect, self.size, self.data_seg, self.alloc_size, self.selector )


class Resource( mrc.Block ):
    offset =        mrc.UInt16_LE( 0x00 )
    size =          mrc.UInt16_LE( 0x02 )
    preload =       mrc.Bits( 0x04, 0b01000000 )
    sharable =      mrc.Bits( 0x04, 0b00100000 )
    movable =       mrc.Bits( 0x04, 0b00010000 )
    unk1 =          mrc.UInt8( 0x05 )
    resource_id_low =   mrc.UInt8( 0x06 )
    int_id =            mrc.Bits( 0x07, 0b10000000 )
    resource_id_high =  mrc.Bits( 0x07, 0b01111111 )
    reserved =      mrc.Bytes( 0x08, length=0x04 )

    @property
    def resource_id( self ):
        return (self.resource_id_high << 8) + self.resource_id_low

    @resource_id.setter
    def resource_id( self, value ):
        self.resouce_id_high = (value >> 8) & 0b01111111
        self.resource_id_low = value & 0b11111111

    @property
    def repr( self ):
        return 'offset=0x{:04x}, size=0x{:04x}, resource_id=0x{:04x}, int_id={}'.format( self.offset, self.size, self.resource_id, self.int_id )


class ResourceInfo( mrc.Block ):
    type_id_low =   mrc.UInt8( 0x00 )
    type_id_high =  mrc.Bits( 0x01, 0b01111111 )
    int_id =        mrc.Bits( 0x01, 0b10000000 )
    count =         mrc.UInt16_LE( 0x02 )
    reserved =      mrc.Bytes( 0x04, length=0x04 )
    resources =     mrc.BlockField( Resource, 0x08, count=mrc.Ref( 'count' ) )

    @property
    def type_id( self ):
        return (self.type_id_high << 8) + self.type_id_low

    @type_id.setter
    def type_id( self, value ):
        self.type_id_high = (value >> 8) & 0b01111111
        self.type_id_low = value & 0b11111111

    @property
    def repr( self ):
        return 'type_id={}, int_id={}, count={}'.format( self.type_id, self.int_id, self.count )


class ResourceTable( mrc.Block ):
    align_shift =   mrc.UInt16_LE( 0x00 )
    resourceinfo =  mrc.BlockStream( ResourceInfo, 0x02, stream_end=b'\x00\x00' )
    name_data =     mrc.Bytes( mrc.EndOffset( 'resourceinfo' ), length=0x100 )


class ResidentName( mrc.Block ):
    size =          mrc.UInt8( 0x00 )
    name =          mrc.Bytes( 0x01, length=mrc.Ref( 'size' ) )
    index =         mrc.UInt8( mrc.EndOffset( 'name' ) )

    @property
    def repr( self ):
        return 'index=0x{:02x}, name={}'.format( self.index, self.name )


class ResidentNameTable( mrc.Block ):
    module_name_size =  mrc.UInt8( 0x00 )
    module_name =       mrc.Bytes( 0x01, length=mrc.Ref( 'module_name_size' ) )
    resnames =          mrc.BlockStream( ResidentName, mrc.EndOffset( 'module_name' ), stream_end=b'\x00\x00' )


class ImportedName( mrc.Block ):
    size =          mrc.UInt8( 0x00 )
    name =          mrc.Bytes( 0x01, length=mrc.Ref( 'size' ) )

    @property
    def repr( self ):
        return 'name={}'.format( self.name )


class ImportedNameTable( mrc.Block ):
    unk =           mrc.UInt8( 0x00 )
    impnames =      mrc.BlockStream( ImportedName, 0x01, stream_end=b'\x00' )



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


class RelocationDetail( IntEnum ):
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
    DETAIL_TYPES = {
        RelocationDetail.INTERNAL_REF: RelocationInternalRef,
        RelocationDetail.IMPORT_ORDINAL: RelocationImportOrdinal,
        RelocationDetail.IMPORT_NAME: RelocationImportName,
        RelocationDetail.OS_FIXUP: RelocationOSFixup
    }

    address_type =      mrc.UInt8( 0x00, enum=RelocationAddressType )
    detail_type =       mrc.Bits( 0x01, 0b00000011, enum=RelocationDetail )
    additive =          mrc.Bits( 0x01, 0b00000100 )
    offset =            mrc.UInt16_LE( 0x02 )
    detail =            mrc.BlockField( DETAIL_TYPES, 0x04, block_type=mrc.Ref( 'detail_type' ) )

    @property
    def repr( self ):
        return 'address_type={}, detail_type={}, offset=0x{:04x}, detail={}'.format( str( self.address_type ), str( self.detail_type ), self.offset, self.detail )


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
    ip_offset =     mrc.UInt16_LE( 0x14 )
    cs_id =         mrc.UInt16_LE( 0x16 )
    sp_offset =     mrc.UInt16_LE( 0x18 )
    ss_id =         mrc.UInt16_LE( 0x1a )
    segtable_count =        mrc.UInt16_LE( 0x1c )
    modref_count =          mrc.UInt16_LE( 0x1e )
    nonresnames_size =      mrc.UInt16_LE( 0x20 )
    segtable_offset =       mrc.UInt16_LE( 0x22 )
    restable_offset =       mrc.UInt16_LE( 0x24 )
    resnames_offset =       mrc.UInt16_LE( 0x26 )
    modref_offset =         mrc.UInt16_LE( 0x28 )
    impnames_offset =       mrc.UInt16_LE( 0x2a )
    nonresnames_rel_offset =    mrc.UInt32_LE( 0x2c )
    movable_count =         mrc.UInt16_LE( 0x30 )
    sector_shift =          mrc.UInt16_LE( 0x32 )

    exe_type =      mrc.UInt8( 0x36 )
    unk1 =          mrc.Bytes( 0x37, length=9 )


class NEModule( NEBase ):
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


    segtable =      mrc.BlockField( Segment, mrc.Ref( 'segtable_offset' ), count=mrc.Ref( 'segtable_count' ) )
    restable =      mrc.BlockField( ResourceTable, mrc.Ref( 'restable_offset' ) )
    resnametable =  mrc.BlockField( ResidentNameTable, mrc.Ref( 'resnames_offset' ) )
    modreftable =   mrc.UInt16_LE( mrc.Ref( 'modref_offset' ), count=mrc.Ref( 'modref_count' ) )
    impnamedata =   mrc.Bytes( mrc.Ref( 'impnames_offset' ), length=mrc.Ref( 'impnames_size' ) )
    entrydata =     mrc.Bytes( mrc.Ref( 'entry_offset' ), length=mrc.Ref( 'entry_size' ) )
    nonresnametable =  mrc.BlockField( ResidentNameTable, mrc.Ref( 'nonresnames_offset' ) )


    @property
    def impnames_size( self ):
        return self.entry_offset - self.impnames_offset

    @property
    def nonresnames_offset( self ):
        return self.nonresnames_rel_offset -(self._parent.ne_offset if self._parent else 0)

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.impnametable = mrc.LinearStore( self, mrc.Ref( 'impnamedata' ), ImportedName, offsets=mrc.Ref( 'modreftable' ) )


class ModuleTable( mrc.Block ):
    ne_header =     mrc.BlockField( NEModule, 0x00 )


class EXE( mrc.Block ):
    dos_magic =     mrc.Const( mrc.Bytes( 0x00, length=2 ), b'MZ' )
    dos_header =    mrc.Bytes( 0x02, length=0x3a )
    ne_offset =     mrc.UInt16_LE( 0x3c )
    # FIXME: size of the DOS stub should be dynamic based on ne_offset
    dos_stub =      mrc.Bytes( 0x3e, length=mrc.Ref( 'dos_stub_length' ) )

    ne_header =     mrc.BlockField( NEHeader, mrc.Ref( 'ne_offset' ) )

    @property
    def dos_stub_length( self ):
        return self.ne_offset - 0x3e
