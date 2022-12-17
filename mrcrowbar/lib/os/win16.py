#!/usr/bin/python3

from __future__ import annotations

from enum import IntEnum

from mrcrowbar import models as mrc

# source: http://benoit.papillault.free.fr/c/disc2/exefmt.txt
# http://geos.icc.ru:8080/scripts/WWWBinV.dll/ShowR?NE.rfi
# Pietrek, Matt,. Windows Internals: The Implementation of the Windows Operating Environment, 1993, Addison-Wesley


class ResidentName( mrc.Block ):
    size = mrc.UInt8( 0x00 )
    name = mrc.Bytes( 0x01, length=mrc.Ref( "size" ) )
    index = mrc.UInt16_LE( mrc.EndOffset( "name" ) )

    @property
    def repr( self ):
        return f"index=0x{self.index:02x}, name={self.name}"


class ResidentNameTable( mrc.Block ):
    module_name_size = mrc.UInt8( 0x00 )
    module_name = mrc.Bytes( 0x01, length=mrc.Ref( "module_name_size" ) )
    padding = mrc.UInt16_LE( mrc.EndOffset( "module_name" ) )
    resnames = mrc.BlockField(
        ResidentName, mrc.EndOffset( "padding" ), stream=True, stream_end=b"\x00"
    )


class ImportedName( mrc.Block ):
    size = mrc.UInt8( 0x00 )
    name = mrc.Bytes( 0x01, length=mrc.Ref( "size" ) )

    @property
    def repr( self ):
        return f"name={self.name}"


class ImportedNameTable( mrc.Block ):
    unk = mrc.UInt8( 0x00 )
    impnames = mrc.BlockField( ImportedName, 0x01, stream=True, stream_end=b"\x00" )


class RelocationInternalRef( mrc.Block ):
    index = mrc.UInt8( 0x00 )
    check = mrc.Const( mrc.UInt8( 0x01 ), 0 )
    offset = mrc.UInt16_LE( 0x02 )

    @property
    def repr( self ):
        return f"index=0x{self.index:02x}, offset=0x{self.offset:04x}"


class RelocationImportName( mrc.Block ):
    index = mrc.UInt16_LE( 0x00 )
    name_offset = mrc.UInt16_LE( 0x02 )
    name = mrc.StoreRef(
        ImportedName,
        mrc.Ref( "_parent._parent._parent._parent._parent.impnamestore" ),
        mrc.Ref( "name_offset" ),
        size=32,
    )

    @property
    def repr( self ):
        return f"index=0x{self.index:04x}, name={self.name}"


class RelocationImportOrdinal( mrc.Block ):
    index = mrc.UInt16_LE( 0x00 )
    ordinal = mrc.UInt16_LE( 0x02 )

    @property
    def repr( self ):
        return f"index=0x{self.index:04x}, ordinal=0x{self.ordinal:04x}"


class RelocationOSFixupType( IntEnum ):
    FIARQQ_FJARQQ = 0x0001
    FISRQQ_FJSRQQ = 0x0002
    FICRQQ_FJCRQQ = 0x0003
    FIERQQ = 0x0004
    FIDRQQ = 0x0005
    FIWRQQ = 0x0006


class RelocationOSFixup( mrc.Block ):
    fixup = mrc.UInt16_LE( 0x00, enum=RelocationOSFixupType )
    check = mrc.Const( mrc.UInt16_LE( 0x02 ), 0 )

    @property
    def repr( self ):
        return f"fixup=0x{self.fixup:04x}"


class RelocationDetail( IntEnum ):
    INTERNAL_REF = 0x00
    IMPORT_ORDINAL = 0x01
    IMPORT_NAME = 0x02
    OS_FIXUP = 0x03


class RelocationAddressType( IntEnum ):
    LOW_BYTE = 0x00
    SELECTOR_16 = 0x02
    POINTER_32 = 0x03
    OFFSET_16 = 0x05
    POINTER_48 = 0x0b
    OFFSET_32 = 0x0d


class Relocation( mrc.Block ):
    DETAIL_TYPES = {
        RelocationDetail.INTERNAL_REF: RelocationInternalRef,
        RelocationDetail.IMPORT_ORDINAL: RelocationImportOrdinal,
        RelocationDetail.IMPORT_NAME: RelocationImportName,
        RelocationDetail.OS_FIXUP: RelocationOSFixup,
    }

    address_type = mrc.UInt8( 0x00, enum=RelocationAddressType )
    detail_type = mrc.Bits( 0x01, 0b00000011, enum=RelocationDetail )
    additive = mrc.Bits( 0x01, 0b00000100 )
    offset = mrc.UInt16_LE( 0x02 )
    detail = mrc.BlockField( DETAIL_TYPES, 0x04, block_type=mrc.Ref( "detail_type" ) )

    @property
    def repr( self ):
        return f"address_type={self.address_type}, detail_type={self.detail_type}, offset=0x{self.offset:04x}, detail={self.detail}"


class NullRelocationTable( mrc.Block ):
    pass


class RelocationTable( mrc.Block ):
    count = mrc.UInt16_LE( 0x00 )
    reltable = mrc.BlockField( Relocation, 0x02, count=mrc.Ref( "count" ) )


class Segment( mrc.Block ):
    RELOCATION_TYPES = {1: RelocationTable, 0: NullRelocationTable}

    data = mrc.Bytes( 0x00, length=mrc.Ref( "_parent.size" ) )
    relocations = mrc.BlockField(
        RELOCATION_TYPES,
        mrc.EndOffset( "data" ),
        block_type=mrc.Ref( "_parent.relocations" ),
    )


class SegmentHeader( mrc.Block ):
    offset_sect = mrc.UInt16_LE( 0x00 )
    size = mrc.UInt16_LE( 0x02 )
    data_seg = mrc.Bits( 0x04, 0b00000001 )
    unk1 = mrc.Bits( 0x04, 0b00000010 )
    unk2 = mrc.Bits( 0x04, 0b00000100 )
    iterated = mrc.Bits( 0x04, 0b00001000 )
    movable = mrc.Bits( 0x04, 0b00010000 )
    shared = mrc.Bits( 0x04, 0b00100000 )
    preload = mrc.Bits( 0x04, 0b01000000 )
    exec_ro = mrc.Bits( 0x04, 0b10000000 )
    relocations = mrc.Bits( 0x05, 0b00000001 )
    conforming = mrc.Bits( 0x05, 0b00000010 )
    privilege_level = mrc.Bits( 0x05, 0b00001100 )
    discardable = mrc.Bits( 0x05, 0b00010000 )
    op_size_32 = mrc.Bits( 0x05, 0b00100000 )
    granularity = mrc.Bits( 0x05, 0b01000000 )
    unk3 = mrc.Bits( 0x05, 0b10000000 )

    alloc_size = mrc.UInt16_LE( 0x06 )

    segment = mrc.StoreRef(
        Segment,
        mrc.Ref( "_parent._parent.segdatastore" ),
        offset=mrc.Ref( "offset" ),
        size=None,
    )

    @property
    def offset( self ):
        return self.offset_sect << self._parent.sector_shift

    @offset.setter
    def offset( self, value ):
        assert value % (1 << self._parent.sector_shift) == 0
        self.offset_sect = value >> self._parent.sector_shift

    @property
    def repr( self ):
        return f"offset_sect={self.offset_sect:04x}, size={self.size:04x}, data_seg={self.data_seg}, relocations={self.relocations}, alloc_size={self.alloc_size:04x}"


class ModuleSegmentHeader( SegmentHeader ):
    selector = mrc.UInt16_LE( 0x08 )

    @property
    def repr( self ):
        return f"offset_sect=0x{self.offset_sect:04x}, size=0x{self.size:04x}, data_seg={self.data_seg}, alloc_size=0x{self.alloc_size:04x}, selector={self.selector:04x}"


class Resource( mrc.Block ):
    offset = mrc.UInt16_LE( 0x00 )
    size = mrc.UInt16_LE( 0x02 )
    unk2 = mrc.Bits( 0x04, 0b10000000 )
    preload = mrc.Bits( 0x04, 0b01000000 )
    sharable = mrc.Bits( 0x04, 0b00100000 )
    movable = mrc.Bits( 0x04, 0b00010000 )
    in_memory = mrc.Bits( 0x04, 0b00000100 )
    unk2 = mrc.Bits( 0x04, 0b00000011 )
    unk3 = mrc.Bits( 0x05, 0b11100000 )
    discardable = mrc.Bits( 0x05, 0b00010000 )
    unk4 = mrc.Bits( 0x05, 0b00001111 )
    int_id = mrc.Bits16( 0x06, 0b1000000000000000, endian="little" )
    resource_id = mrc.Bits16( 0x06, 0b0111111111111111, endian="little" )
    reserved = mrc.Bytes( 0x08, length=0x04 )

    @property
    def repr( self ):
        return f"offset=0x{self.offset:04x}, size=0x{self.size:04x}, resource_id=0x{self.resource_id:04x}, int_id={self.int_id}"


class ResourceInfo( mrc.Block ):
    int_id = mrc.Bits16( 0x00, 0b1000000000000000, endian="little" )
    type_id = mrc.Bits16( 0x00, 0b0111111111111111, endian="little" )
    count = mrc.UInt16_LE( 0x02 )
    reserved = mrc.Bytes( 0x04, length=0x04 )
    resources = mrc.BlockField( Resource, 0x08, count=mrc.Ref( "count" ) )

    @property
    def repr( self ):
        return f"type_id={self.type_id}, int_id={self.int_id}, count={self.count}"


class ResourceTable( mrc.Block ):
    align_shift = mrc.UInt16_LE( 0x00 )
    resourceinfo = mrc.BlockField(
        ResourceInfo, 0x02, stream=True, stream_end=b"\x00\x00"
    )
    # name_data =     mrc.Bytes( mrc.EndOffset( 'resourceinfo' ), length=0x107 )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        # self.store = mrc.Store( self, mrc.Ref( 'name_data' ) )


class EmptySegmentIndicator( mrc.Block ):
    pass


class MovableSegmentIndicator( mrc.Block ):
    exported = mrc.Bits( 0x00, 0b00000001 )
    shared = mrc.Bits( 0x00, 0b00000010 )
    seg_id = mrc.UInt8( 0x01 )
    offset = mrc.UInt16_LE( 0x02 )
    unk = mrc.Bytes( 0x04, length=2 )

    @property
    def repr( self ):
        return f"seg_id={self.seg_id}, offset=0x{self.offset:04x}, exported={self.exported}, shared={self.shared}"


class FixedSegmentIndicator( mrc.Block ):
    exported = mrc.Bits( 0x00, 0b00000001 )
    shared = mrc.Bits( 0x00, 0b00000010 )
    offset = mrc.UInt16_LE( 0x01 )

    @property
    def repr( self ):
        return f"offset=0x{self.offset:04x}, exported={self.exported}, shared={self.shared}"


class EntryBundle( mrc.Block ):
    # awful hack for validating blockfield
    INDICATOR_MAP = {k: FixedSegmentIndicator for k in range( 1, 255 )}
    INDICATOR_MAP[0] = EmptySegmentIndicator
    INDICATOR_MAP[255] = MovableSegmentIndicator

    count = mrc.UInt8( 0x00 )
    indicator = mrc.UInt8( 0x01 )
    indicators = mrc.BlockField(
        INDICATOR_MAP, 0x02, count=mrc.Ref( "count" ), block_type=mrc.Ref( "indicator" )
    )

    @property
    def repr( self ):
        return f"count={self.count}, indicator={self.indicator}"


class ModuleReference( mrc.Block ):
    name_offset = mrc.UInt16_LE( 0x00 )

    name = mrc.StoreRef(
        ImportedName,
        mrc.Ref( "_parent.impnamestore" ),
        mrc.Ref( "name_offset" ),
        size=32,
    )

    @property
    def repr( self ):
        return f"name={self.name}"


class NEBase( mrc.Block ):
    ne_magic = mrc.Const( mrc.Bytes( 0x00, length=2 ), b"NE" )

    entry_offset = mrc.UInt16_LE( 0x04 )

    flags = mrc.UInt16_LE( 0x0c )

    heap_size = mrc.UInt16_LE( 0x10 )
    stack_size = mrc.UInt16_LE( 0x12 )
    ip_offset = mrc.UInt16_LE( 0x14 )
    cs_id = mrc.UInt16_LE( 0x16 )
    sp_offset = mrc.UInt16_LE( 0x18 )
    ss_id = mrc.UInt16_LE( 0x1a )
    segtable_count = mrc.UInt16_LE( 0x1c )
    modref_count = mrc.UInt16_LE( 0x1e )
    nonresnames_size = mrc.UInt16_LE( 0x20 )
    segtable_offset = mrc.UInt16_LE( 0x22 )
    restable_offset = mrc.UInt16_LE( 0x24 )
    resnames_offset = mrc.UInt16_LE( 0x26 )
    modref_offset = mrc.UInt16_LE( 0x28 )
    impnames_offset = mrc.UInt16_LE( 0x2a )
    nonresnames_rel_offset = mrc.UInt32_LE( 0x2c )
    movable_count = mrc.UInt16_LE( 0x30 )
    sector_shift = mrc.UInt16_LE( 0x32 )

    exe_type = mrc.UInt8( 0x36 )
    unk1 = mrc.Bytes( 0x37, length=9 )

    @property
    def impnames_size( self ):
        return self.entry_offset - self.impnames_offset


class NEModule( NEBase ):
    usage_count = mrc.UInt16_LE( 0x02 )

    next_table = mrc.UInt16_LE( 0x06 )
    dgroup_offset = mrc.UInt16_LE( 0x08 )
    fileinfo_offset = mrc.UInt16_LE( 0x0a )

    dgroup_segid = mrc.UInt16_LE( 0x0e )

    segtable = mrc.BlockField(
        ModuleSegmentHeader,
        mrc.Ref( "segtable_offset" ),
        count=mrc.Ref( "segtable_count" ),
    )
    restable = mrc.BlockField( ResourceTable, mrc.Ref( "restable_offset" ) )
    resnametable = mrc.BlockField( ResidentNameTable, mrc.Ref( "resnames_offset" ) )
    modreftable = mrc.BlockField(
        ModuleReference, mrc.Ref( "modref_offset" ), count=mrc.Ref( "modref_count" )
    )
    impnamedata = mrc.Bytes(
        mrc.Ref( "impnames_offset" ), length=mrc.Ref( "impnames_size" )
    )
    # entrydata =     mrc.BlockField( EntryBundle, mrc.Ref( 'entry_offset' ), stream=True, length=mrc.Ref( 'entry_size' ) )
    # nonresnametable =  mrc.BlockField( ResidentNameTable, mrc.Ref( 'nonresnames_rel_offset' ) )

    def __init__( self, *args, **kwargs ):
        self.impnamestore = mrc.Store( self, mrc.Ref( "impnamedata" ) )
        super().__init__( *args, **kwargs )


class NEHeader( NEBase ):
    linker_ver = mrc.UInt8( 0x02 )
    linker_rev = mrc.UInt8( 0x03 )

    entry_size = mrc.UInt16_LE( 0x06 )
    crc = mrc.UInt32_LE( 0x08 )

    ds_id = mrc.UInt16_LE( 0x0e )

    resource_count = mrc.UInt16_LE( 0x34 )

    segtable = mrc.BlockField(
        SegmentHeader, mrc.Ref( "segtable_offset" ), count=mrc.Ref( "segtable_count" )
    )
    restable = mrc.BlockField( ResourceTable, mrc.Ref( "restable_offset" ) )
    resnametable = mrc.BlockField( ResidentNameTable, mrc.Ref( "resnames_offset" ) )
    modreftable = mrc.BlockField(
        ModuleReference, mrc.Ref( "modref_offset" ), count=mrc.Ref( "modref_count" )
    )
    impnamedata = mrc.Bytes(
        mrc.Ref( "impnames_offset" ), length=mrc.Ref( "impnames_size" )
    )
    # entrydata =     mrc.BlockField( EntryBundle, mrc.Ref( 'entry_offset' ), stream=True, length=mrc.Ref( 'entry_size' ) )
    entrydata = mrc.Bytes( mrc.Ref( "entry_offset" ), length=mrc.Ref( "entry_size" ) )
    nonresnametable = mrc.BlockField(
        ResidentNameTable, mrc.Ref( "nonresnames_offset" )
    )

    @property
    def nonresnames_offset( self ):
        return self.nonresnames_rel_offset - (
            self._parent.ne_offset if self._parent else 0
        )

    def __init__( self, *args, **kwargs ):
        self.impnamestore = mrc.Store( self, mrc.Ref( "impnamedata" ) )
        super().__init__( *args, **kwargs )


class ModuleTable( mrc.Block ):
    ne_header = mrc.BlockField( NEModule, 0x00 )

    segdata = mrc.Bytes( mrc.EndOffset( "ne_header", align=mrc.Ref( "sector_align" ) ) )

    @property
    def sector_align( self ):
        if self.ne_header:
            return 1 << self.ne_header.sector_shift
        return 32

    def __init__( self, *args, **kwargs ):
        self.segdatastore = mrc.Store(
            self,
            mrc.Ref( "segdata" ),
            base_offset=mrc.EndOffset(
                "ne_header", neg=True, align=mrc.Ref( "sector_align" )
            ),
            align=mrc.Ref( "sector_align" ),
        )
        super().__init__( *args, **kwargs )


class EXE( mrc.Block ):
    dos_magic = mrc.Const( mrc.Bytes( 0x00, length=2 ), b"MZ" )
    dos_header = mrc.Bytes( 0x02, length=0x3a )
    ne_offset = mrc.UInt16_LE( 0x3c )
    dos_stub = mrc.Bytes( 0x3e, length=mrc.Ref( "dos_stub_length" ) )

    ne_header = mrc.BlockField( NEHeader, mrc.Ref( "ne_offset" ) )

    segdata = mrc.Bytes( mrc.EndOffset( "ne_header", align=mrc.Ref( "sector_align" ) ) )

    @property
    def sector_align( self ):
        if self.ne_header:
            return 1 << self.ne_header.sector_shift
        return 32

    @property
    def dos_stub_length( self ):
        return self.ne_offset - 0x3e

    def __init__( self, *args, **kwargs ):
        self.segdatastore = mrc.Store(
            self,
            mrc.Ref( "segdata" ),
            base_offset=mrc.EndOffset(
                "ne_header", neg=True, align=mrc.Ref( "sector_align" )
            ),
            align=mrc.Ref( "sector_align" ),
        )
        super().__init__( *args, **kwargs )
