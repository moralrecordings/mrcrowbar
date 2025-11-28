from mrcrowbar import models as mrc


class FONGlyphEntry( mrc.Block ):
    char_width = mrc.UInt16_LE()
    offset = mrc.UInt16_LE()


class FON( mrc.Block ):
    version = mrc.UInt16_LE()
    size = mrc.UInt32_LE()
    copyright = mrc.Bytes(length=60)
    font_type = mrc.UInt16_LE()
    points = mrc.UInt16_LE()
    vert_res = mrc.UInt16_LE()
    horiz_res = mrc.UInt16_LE()
    ascent = mrc.UInt16_LE()
    internal_leading = mrc.UInt16_LE()
    external_leading = mrc.UInt16_LE()
    italic = mrc.UInt8()
    underline = mrc.UInt8()
    strikethrough = mrc.UInt8()
    weight = mrc.UInt16_LE()
    charset = mrc.UInt8()
    pix_width = mrc.UInt16_LE()
    pix_height = mrc.UInt16_LE()
    pitch_and_family = mrc.UInt8()
    avg_width = mrc.UInt16_LE()
    max_width = mrc.UInt16_LE()
    first_char = mrc.UInt8()
    last_char = mrc.UInt8()
    default_char = mrc.UInt8()
    break_char = mrc.UInt8()
    width_bytes = mrc.UInt16_LE()
    device = mrc.UInt32_LE()
    face = mrc.UInt32_LE()
    bits_pointer = mrc.UInt32_LE()
    bits_offset = mrc.UInt32_LE()
    reserved = mrc.UInt8()

    @property
    def is_v1(self):
        return self.version == 0x100

    unused1 = mrc.Bytes(length=1, exists=mrc.Ref( 'is_v1' ))

    @property
    def is_v3(self):
        return self.version == 0x300

    unused2 = mrc.Bytes(length=30, exists=mrc.Ref( 'is_v3' ))

    @property
    def char_count(self):
        return self.last_char - self.first_char + 2

    glyph_entries = mrc.BlockField(FONGlyphEntry, count=mrc.Ref( "char_count" ))
    data = mrc.Bytes()
