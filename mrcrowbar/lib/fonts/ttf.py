import math

from mrcrowbar import models as mrc

# Source: https://learn.microsoft.com/en-us/typography/opentype/spec/otff
class BigGlyphMetrics( mrc.Block ):
    height = mrc.UInt8()
    width = mrc.UInt8()
    horiBearingX = mrc.Int8()
    horiBearingY = mrc.Int8()
    horiAdvance = mrc.UInt8()
    vertBearingX = mrc.Int8() 
    vertBearingY = mrc.Int8()
    vertAdvance = mrc.UInt8()

class SmallGlyphMetrics( mrc.Block ):
    height = mrc.UInt8()
    width = mrc.UInt8()
    bearingX = mrc.Int8()
    bearingY = mrc.Int8()
    advance = mrc.UInt8()

class EBDTComponent( mrc.Block ):
    glyph_id = mrc.UInt16_BE()
    x_offset = mrc.Int8() 
    y_offset = mrc.Int8()


class GlyphBitmapFormat1( mrc.Block ):
    metrics = mrc.BlockField( SmallGlyphMetrics )

    @property
    def glyph_size(self):
        return self.metrics.height * math.ceil(self.metrics.width/8) * self._parent._parent._parent.num_glyphs

    image_data = mrc.Bytes(length=mrc.Ref("glyph_size"))

class GlyphBitmapFormat2( mrc.Block ):
    metrics = mrc.BlockField( SmallGlyphMetrics )

    @property
    def glyph_size(self):
        return math.ceil(self.metrics.height *self.metrics.width/8) * self._parent._parent._parent.num_glyphs

    image_data = mrc.Bytes(length=mrc.Ref("glyph_size"))

class GlyphBitmapFormat5( mrc.Block ):
    @property
    def glyph_size(self):
        return math.ceil(self._parent._parent.subtable_data.metrics.height *self._parent._parent.subtable_data.metrics.width/8) * self._parent._parent._parent.num_glyphs

    image_data = mrc.Bytes(length=mrc.Ref("glyph_size"))

class GlyphBitmapFormat6( mrc.Block ):
    metrics = mrc.BlockField( BigGlyphMetrics )

    @property
    def glyph_size(self):
        return self.metrics.height * math.ceil(self.metrics.width/8) * self._parent._parent._parent.num_glyphs

    image_data = mrc.Bytes(length=mrc.Ref("glyph_size"))

class GlyphBitmapFormat7( mrc.Block ):
    metrics = mrc.BlockField( BigGlyphMetrics )

    @property
    def glyph_size(self):
        return math.ceil(self.metrics.height *self.metrics.width/8) * self._parent._parent._parent.num_glyphs

    image_data = mrc.Bytes(length=mrc.Ref("glyph_size"))

class GlyphData( mrc.Block ):
    data = mrc.BlockField({
        1: GlyphBitmapFormat1,
        2: GlyphBitmapFormat2,
        5: GlyphBitmapFormat5,
        6: GlyphBitmapFormat5,
        7: GlyphBitmapFormat5,
    }, block_type=mrc.Ref("_parent.image_format"))

class EBDT( mrc.Block ):
    major_version = mrc.UInt16_BE()
    minor_version = mrc.UInt16_BE()
    raw_data = mrc.Bytes()

    def __init__(self, *args, **kwargs):
        self.store = mrc.Store(self, mrc.Ref("raw_data"), base_offset=mrc.EndOffset("minor_version", neg=True))
        super().__init__(*args, **kwargs)



class IndexSubtableFormat1( mrc.Block ):
    sbit_offsets = mrc.UInt32_BE(count=mrc.Ref("_parent._parent.num_offsets"))

class IndexSubtableFormat2( mrc.Block ):
    image_size = mrc.UInt32_BE()
    metrics = mrc.BlockField(BigGlyphMetrics)

class IndexSubtableFormat3( mrc.Block ):
    sbit_offsets = mrc.UInt16_BE(count=mrc.Ref("_parent._parent.num_offsets")) 


class IndexSubtable( mrc.Block ):
    index_format = mrc.UInt16_BE()
    image_format = mrc.UInt16_BE()
    image_data_offset = mrc.UInt32_BE()
    
    subtable_data = mrc.BlockField({
        1: IndexSubtableFormat1,
        2: IndexSubtableFormat2,
        3: IndexSubtableFormat3,
    }, block_type=mrc.Ref('index_format'))
    image = mrc.StoreRef(GlyphData, mrc.Ref("_parent._parent._parent._parent.ebdt.store"), offset=mrc.Ref("image_data_offset"))


class IndexSubtableRecord( mrc.Block ):
    first_glyph_index = mrc.UInt16_BE()
    last_glyph_index = mrc.UInt16_BE()
    index_subtitle_offset = mrc.UInt32_BE()
   
    @property
    def num_glyphs(self):
        return self.last_glyph_index - self.first_glyph_index + 1

    @property
    def num_offsets(self):
        return self.last_glyph_index - self.first_glyph_index + 2

    subtable = mrc.StoreRef(IndexSubtable, mrc.Ref('_parent.store'), mrc.Ref('index_subtitle_offset'))

class IndexSubtableList( mrc.Block ):
    records = mrc.BlockField( IndexSubtableRecord, count=mrc.Ref("_parent.number_of_index_subtables") )
    raw_data = mrc.Bytes()

    def __init__(self, *args, **kwargs):
        self.store = mrc.Store(self, mrc.Ref('raw_data'), base_offset=mrc.EndOffset('records', neg=True))
        super().__init__(*args, **kwargs)

class SbitLineMetrics( mrc.Block ):
    ascender = mrc.Int8()
    descender = mrc.Int8()
    width_max = mrc.UInt8()
    caret_slope_numerator = mrc.Int8()
    caret_slope_denomenator = mrc.Int8()
    caret_offset = mrc.Int8()
    min_origin_sb = mrc.Int8()
    min_advance_sb = mrc.Int8()
    max_before_bl = mrc.Int8()
    min_after_bl = mrc.Int8()
    pad1 = mrc.Int8()
    pad2 = mrc.Int8()


class BitmapSize( mrc.Block ):
    index_subtable_list_offset = mrc.UInt32_BE()
    index_subtable_list_size = mrc.UInt32_BE()
    number_of_index_subtables = mrc.UInt32_BE()
    color_ref = mrc.UInt32_BE()
    hori = mrc.BlockField( SbitLineMetrics )
    vert = mrc.BlockField( SbitLineMetrics )
    start_glyph_index = mrc.UInt16_BE()
    end_glyph_index = mrc.UInt16_BE()
    ppem_x = mrc.UInt8()
    ppem_y = mrc.UInt8()
    bit_depth = mrc.UInt8()
    flags = mrc.Int8()

    subtables = mrc.StoreRef( IndexSubtableList, mrc.Ref('_parent.store'),
        offset=mrc.Ref('index_subtable_list_offset'),
        size=mrc.Ref('index_subtable_list_size'),
    )


class EBLC( mrc.Block ):
    major_version = mrc.Const(mrc.UInt16_BE(), 2)
    minor_version = mrc.Const(mrc.UInt16_BE(), 0)
    num_sizes = mrc.UInt32_BE()
    bitmap_sizes = mrc.BlockField( BitmapSize, count=mrc.Ref( 'num_sizes' ) )
    raw_data = mrc.Bytes()

    def __init__(self, *args, **kwargs):
        self.store = mrc.Store(
                self,
                mrc.Ref('raw_data'),
                base_offset=mrc.EndOffset('bitmap_sizes', neg=True)
        )
        super().__init__(*args, **kwargs)


class EncodingRecord( mrc.Block ):
    platform_id = mrc.UInt16_BE()
    encoding_id = mrc.UInt16_BE()


class cmap( mrc.Block ):
    version = mrc.UInt16_BE()
    num_tables = mrc.UInt16_BE()
    records = mrc.BlockField(EncodingRecord, count=mrc.Ref('num_tables'))


class TTFData( mrc.Block ):
    data = mrc.Bytes()


class TTFTableEntry( mrc.Block ):
    tag = mrc.Bytes(length=4)
    checksum = mrc.UInt32_BE()
    offset = mrc.UInt32_BE()
    length = mrc.UInt32_BE()

    data = mrc.StoreRef(TTFData, mrc.Ref('_parent.store'), mrc.Ref('offset'), size=mrc.Ref('length'))


class TTF( mrc.Block ):
    scaler_type = mrc.Const(mrc.Bytes(length=4), b'\x00\x01\x00\x00')
    num_tables = mrc.UInt16_BE()
    search_range = mrc.UInt16_BE()
    entry_selector = mrc.UInt16_BE()
    range_shift = mrc.UInt16_BE()
    table = mrc.BlockField( TTFTableEntry, count=mrc.Ref( "num_tables" ) )

    raw_data = mrc.Bytes()

    def __init__(self, *args, **kwargs):
        self.store = mrc.Store(self, mrc.Ref('raw_data'), base_offset=mrc.EndOffset('table', neg=True))
        super().__init__(*args, **kwargs)


