
from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img
from mrcrowbar.lib.audio import base as aud
from mrcrowbar.lib.containers import riff
from mrcrowbar import utils

import math

from enum import IntEnum

DIRECTOR_PALETTE_RAW =  '000000111111222222444444555555777777888888aaaaaa'\
                        'bbbbbbddddddeeeeee000011000022000044000055000077'\
                        '0000880000aa0000bb0000dd0000ee001100002200004400'\
                        '00550000770000880000aa0000bb0000dd0000ee00110000'\
                        '220000440000550000770000880000aa0000bb0000dd0000'\
                        'ee00000000330000660000990000cc0000ff003300003333'\
                        '0033660033990033cc0033ff006600006633006666006699'\
                        '0066cc0066ff0099000099330099660099990099cc0099ff'\
                        '00cc0000cc3300cc6600cc9900cccc00ccff00ff0000ff33'\
                        '00ff6600ff9900ffcc00ffff330000330033330066330099'\
                        '3300cc3300ff3333003333333333663333993333cc3333ff'\
                        '3366003366333366663366993366cc3366ff339900339933'\
                        '3399663399993399cc3399ff33cc0033cc3333cc6633cc99'\
                        '33cccc33ccff33ff0033ff3333ff6633ff9933ffcc33ffff'\
                        '6600006600336600666600996600cc6600ff663300663333'\
                        '6633666633996633cc6633ff666600666633666666666699'\
                        '6666cc6666ff6699006699336699666699996699cc6699ff'\
                        '66cc0066cc3366cc6666cc9966cccc66ccff66ff0066ff33'\
                        '66ff6666ff9966ffcc66ffff990000990033990066990099'\
                        '9900cc9900ff9933009933339933669933999933cc9933ff'\
                        '9966009966339966669966999966cc9966ff999900999933'\
                        '9999669999999999cc9999ff99cc0099cc3399cc6699cc99'\
                        '99cccc99ccff99ff0099ff3399ff6699ff9999ffcc99ffff'\
                        'cc0000cc0033cc0066cc0099cc00cccc00ffcc3300cc3333'\
                        'cc3366cc3399cc33cccc33ffcc6600cc6633cc6666cc6699'\
                        'cc66cccc66ffcc9900cc9933cc9966cc9999cc99cccc99ff'\
                        'cccc00cccc33cccc66cccc99ccccccccccffccff00ccff33'\
                        'ccff66ccff99ccffccccffffff0000ff0033ff0066ff0099'\
                        'ff00ccff00ffff3300ff3333ff3366ff3399ff33ccff33ff'\
                        'ff6600ff6633ff6666ff6699ff66ccff66ffff9900ff9933'\
                        'ff9966ff9999ff99ccff99ffffcc00ffcc33ffcc66ffcc99'\
                        'ffccccffccffffff00ffff33ffff66ffff99ffffccffffff'

DIRECTOR_PALETTE = [p for p in reversed( img.from_palette_bytes( bytes.fromhex( DIRECTOR_PALETTE_RAW ), stride=3, order=(0, 1, 2) ) )]


class BuiltinPalette( IntEnum ):
    SYSTEM_MAC = 0xff
    SYSTEM_WIN = 0x9b
    RAINBOW = 0xfe
    GRAYSCALE = 0xfd
    PASTELS = 0xfc
    VIVID = 0xfb
    NTSC = 0xfa
    METALLIC = 0xf9


class ChannelCompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        result = bytearray( 50*25 )
        pointer = 0
        while pointer < len( buffer ):
            size = utils.from_uint16_be( buffer[pointer:pointer+2] )
            offset = utils.from_uint16_be( buffer[pointer+2:pointer+4] )
            result[offset:offset+size] = buffer[pointer+4:pointer+4+size]
        return mrc.TransformResult( payload=result, end_offset=pointer )


class EmptyChannelV4( mrc.Block ):
    pass


class SpriteType( IntEnum ):
    INACTIVE = 0x00
    BITMAP = 0x01
    RECTANGLE = 0x02
    ROUNDED_RECTANGLE = 0x03
    OVAL = 0x04
    LINE_TOP_BOTTOM = 0x05
    LINE_BOTTOM_TOP = 0x06
    TEXT = 0x07
    BUTTON = 0x08
    CHECKBOX = 0x09
    RADIO_BUTTON = 0x0a
    PICT = 0x0b
    OUTLINED_RECTANGLE = 0x0c
    OUTLINED_ROUNDED_RECTANGLE = 0x0d
    OUTLINED_OVAL = 0x0e
    THINK_LINE = 0x0f
    CAST_MEMBER = 0x10
    FILM_LOOP = 0x11
    DIR_MOVIE = 0x12
    UNUSED = 0xff


class SpriteChannelV4( mrc.Block ):
    script_id = mrc.UInt8( 0x00 )
    type =      mrc.UInt8( 0x01, enum=SpriteType )
    fg_colour = mrc.UInt8( 0x02 )
    bg_colour = mrc.UInt8( 0x03 )
    line_size = mrc.Bits( 0x04, 0b00000011 )
    unk4 =      mrc.Bits( 0x04, 0b11111100 )
    ink =       mrc.Bits( 0x05, 0b00111111 )
    trails =    mrc.Bits( 0x05, 0b01000000 )
    unk5 =      mrc.Bits( 0x05, 0b10000000 )
    cast_id =   mrc.UInt16_BE( 0x06 )
    y_pos =     mrc.UInt16_BE( 0x08 )
    x_pos =     mrc.UInt16_BE( 0x0a )
    height =    mrc.UInt16_BE( 0x0c )
    width =     mrc.UInt16_BE( 0x0e )


class ScriptChannelV4( mrc.Block ):
    index = mrc.UInt16_BE( 0x00 )


class ChannelType( IntEnum ):
    SPRITE =          0x00
    FRAME_SCRIPT =    0x10
    PALETTE =         0x20


class ChannelV4( mrc.Block ):
    CHANNEL_MAP = {
        None: EmptyChannelV4,
#        ChannelType.SPRITE: SpriteChannelV4,
        ChannelType.FRAME_SCRIPT: ScriptChannelV4,
#        ChannelType.PALETTE: mrc.Unknown,
    }

    channel_size =      mrc.UInt16_BE( 0x00 )
    channel_offset =    mrc.UInt16_BE( 0x02 )

    @property
    def channel_row( self ):
        return self.channel_offset // 0x14

    @property
    def channel_type( self ):
        return self.channel_offset % 0x14

    @property
    def channel_type_wrap( self ):
        return (ChannelType.PALETTE if self.channel_offset == 0x14 else self.channel_type) if self.channel_size else None

    data =              mrc.BlockField( CHANNEL_MAP, 0x04, block_type=mrc.Ref( 'channel_type_wrap' ), default_klass=mrc.Unknown, length=mrc.Ref( 'channel_size' ) )

    @property
    def repr( self ):
        return 'channel_size=0x{:02x}, channel_offset=0x{:04x}, channel_row={}, channel_type={}'.format( self.channel_size, self.channel_offset, self.channel_row, self.channel_type )


class FrameV4( mrc.Block ):
    size = mrc.UInt16_BE( 0x00 )
    channels = mrc.BlockField( ChannelV4, 0x02, stream=True, length=mrc.Ref( 'size_channels' ) )

    @property
    def size_channels( self ):
        return self.size-0x02
    
    @property
    def repr( self ):
        return 'num_channnels={}'.format( len( self.channels ) )


class ScoreV4( mrc.Block ):
    size = mrc.UInt32_BE( 0x00 )
    unk1 = mrc.UInt32_BE( 0x04 )
    unk2 = mrc.UInt32_BE( 0x08 )
    unk3 = mrc.UInt16_BE( 0x0c )
    unk4 = mrc.UInt16_BE( 0x0e )
    unk5 = mrc.UInt16_BE( 0x10 )
    unk6 = mrc.UInt16_BE( 0x12 )

    frames = mrc.BlockField( FrameV4, 0x14, stream=True, length=mrc.Ref( 'size_frames' ) )
    extra = mrc.Bytes( mrc.EndOffset( 'frames' ) )

    @property
    def size_frames( self ):
        return self.size-0x14

    @property
    def repr( self ):
        return 'num_frames={}'.format( len( self.frames ) )



class SoundV4( mrc.Block ):
    unk1 = mrc.Bytes( 0x00, length=0x14 )
    channels = mrc.UInt16_BE( 0x14 )
    sample_rate = mrc.UInt16_BE( 0x16 )
    unk2 = mrc.Bytes( 0x18, length=0x06 )
    length = mrc.UInt32_BE( 0x1e )
    unk3 = mrc.UInt16_BE( 0x22 )
    length_copy = mrc.UInt32_BE( 0x24 )
    unk4 = mrc.UInt16_BE( 0x28 )
    unk5 = mrc.UInt16_BE( 0x2a )
    unk6 = mrc.UInt16_BE( 0x2c )
    unk7 = mrc.Bytes( 0x2e, length=0x12 )
    sample_bits = mrc.UInt16_BE( 0x3e )

    data = mrc.Bytes( 0x4e )

    @property
    def sample_width( self ):
        return self.sample_bits // 8

    @property
    def sample_signedness( self ):
        return 'unsigned' if self.sample_bits == 8 else 'signed'

    def __init__( self, *argc, **argv ):
        self.audio = aud.Wave( self, mrc.Ref( 'data' ), channels=mrc.Ref( 'channels' ), sample_rate=mrc.Ref( 'sample_rate' ), format_type=int, field_size=mrc.Ref( 'sample_width' ), signedness=mrc.Ref( 'sample_signedness' ), endian='big' )
        super().__init__( *argc, **argv )

    @property
    def repr( self ):
        return 'channels={}, sample_rate={}, length={}, sample_bits={}'.format( self.channels, self.sample_rate, self.length, self.sample_bits )


class SoundCastV4Extra( mrc.Block ):
    name_size = mrc.UInt8( 0x00 )
    name = mrc.CString( 0x01, length=mrc.Ref( 'name_size' ) )

    @property
    def repr( self ):
        return 'name={}'.format( self.name )


class SoundCastV4( mrc.Block ):
    unk1 = mrc.Bytes( 0x00, length=0x20 )
    extra_size = mrc.UInt8( 0x20 )
    extra = mrc.BlockField( SoundCastV4Extra, 0x21, stream=True, length=mrc.Ref( 'extra_size' ) )

    @property
    def repr( self ):
        return 'unk1={}{}'.format(
            self.unk1, ', name={}'.format( self.extra[0].name ) if self.extra else '' )

class ScriptCastV4( mrc.Block ):
    unk1        = mrc.Bytes( 0x00, length=0x14 )
    script_id   = mrc.UInt16_BE( 0x14 )
    var_count   = mrc.UInt16_BE( 0x16 )
    unk2        = mrc.UInt32_BE( 0x18 )
    vars        = mrc.UInt32_BE( 0x1c, count=mrc.Ref( 'var_count' ) )
    code        = mrc.Bytes( mrc.EndOffset( 'vars' ), length=mrc.Ref( 'code_len' ) )
    unk3        = mrc.Bytes( mrc.EndOffset( 'code' ) )

    @property
    def code_len( self ):
        return self.vars[0] if self.vars else 0

    @property
    def repr( self ):
        return 'script_id={}'.format( self.script_id )


class BitmapCompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        result = bytearray()
        pointer = 0
        while (pointer < len( buffer )):
            test = buffer[pointer]
            pointer += 1
            length = test + 1
            if test & 0x80:
                length = ((test ^ 0xff) & 0xff) + 2
                result.extend( (buffer[pointer] for i in range( length )) )
                pointer += 1
            else:
                result.extend( buffer[pointer:pointer+length] )
                pointer += length
        return mrc.TransformResult( payload=result, end_offset=pointer )


class BitmapV4( mrc.Block ):
    data = mrc.Bytes( 0x00 )


class Rect( mrc.Block ):
    top = mrc.Int16_BE( 0x00 )
    left = mrc.Int16_BE( 0x02 )
    bottom = mrc.Int16_BE( 0x04 )
    right = mrc.Int16_BE( 0x06 )

    @property
    def width( self ):
        return self.right-self.left

    @property
    def height( self ):
        return self.bottom-self.top

    @property
    def repr( self ):
        return 'top={}, left={}, bottom={}, right={}, width={}, height={}'.format( 
            self.top, self.left, self.bottom, self.right, self.width, self.height )


class ShapeType( IntEnum ):
    RECTANGLE = 1
    ROUND_RECT = 2
    OVAL = 3
    LINE = 4


class ShapeCastV4( mrc.Block ):
    type = mrc.UInt16_BE( 0x00, enum=ShapeType )
    rect = mrc.BlockField( Rect, 0x02 )
    pattern = mrc.UInt16_BE( 0x0a )
    fg_colour = mrc.UInt8( 0x0c )
    bg_colour = mrc.UInt8( 0x0d )
    fill_type = mrc.UInt8( 0x0e )
    line_thickness = mrc.UInt8( 0x0f )
    line_direction = mrc.UInt8( 0x10 )


class BitmapCastV4( mrc.Block ):
    _data = None

    bpp =           mrc.Bits16( 0x00, 0b1111000000000000 )
    pitch =         mrc.Bits16( 0x00, 0b0000111111111111 )
    initial_rect =  mrc.BlockField( Rect, 0x02 )
    bounding_rect = mrc.BlockField( Rect, 0x0a )
    reg_y =         mrc.UInt16_BE( 0x12 )
    reg_x =         mrc.UInt16_BE( 0x14 )
    #bpp =          mrc.UInt16_BE( 0x16 )
    #unk4 =         mrc.Bytes( 0x18, length=0x24 )
    #name =         mrc.Bytes( 0x3e )
    unk4 =          mrc.Bytes( 0x16 )

    @property
    def repr( self ):
        #return 'name={}, pitch={}, bpp={}, reg_x={}, reg_y={}, unk1={}, unk2={}'.format( self.name, self.pitch, self.bpp, self.reg_x, self.reg_y, self.unk1, self.unk2 )
        return 'bpp={}, pitch={}, reg_x={}, reg_y={}, initial_rect={}, bounding_rect={}'.format( self.bpp, self.pitch, self.reg_x, self.reg_y, self.initial_rect, self.bounding_rect )

    def __init__( self, *argc, **argv ):
        self.image = img.IndexedImage( self, mrc.Ref( '_data.data' ), mrc.Ref( 'pitch' ), mrc.Ref( 'initial_rect.height' ), palette=DIRECTOR_PALETTE )
        super().__init__( *argc, **argv )




class CastType( IntEnum ):
    NULL =          0x00
    BITMAP =        0x01
    FILM_LOOP =     0x02
    TEXT =          0x03
    PALETTE =       0x04
    PICTURE =       0x05
    SOUND =         0x06
    BUTTON =        0x07
    SHAPE =         0x08
    MOVIE =         0x09
    VIDEO =         0x0a
    SCRIPT =        0x0b
    RTE =           0x0c


class CastV4( mrc.Block ):
    CAST_MAP = {
        CastType.BITMAP: BitmapCastV4,
        #CastType.SOUND: SoundCastV4,
        CastType.SCRIPT: ScriptCastV4,
        CastType.SHAPE: ShapeCastV4,
    }

    size1 =     mrc.UInt16_BE( 0x00 )
    size2 =     mrc.UInt32_BE( 0x02 )
    cast_type = mrc.UInt8( 0x06, enum=CastType )
    unk1 =      mrc.UInt8( 0x07 )
    detail =    mrc.BlockField( CAST_MAP, 0x08, block_type=mrc.Ref( 'cast_type' ), default_klass=mrc.Unknown )
    garbage =   mrc.Bytes( mrc.EndOffset( 'detail' ) )

    @property
    def repr( self ):
        return 'size1: {}, size2: {}, cast_type: {}'.format( self.size1, self.size2, str( self.cast_type ) )


class KeyEntry( mrc.Block ):
    section_index   = mrc.UInt32_P( 0x00 )
    cast_index      = mrc.UInt32_P( 0x04 )
    chunk_id        = mrc.UInt32_P( 0x08 )

    @property
    def repr( self ):
        return 'chunk_id: {}, section_index: {}, cast_index: {}'.format( riff.TagB( self.chunk_id ), self.section_index, self.cast_index )


class KeyV4( mrc.Block ):
    unk1 =          mrc.UInt16_P( 0x00 )
    unk2 =          mrc.UInt16_P( 0x02 )
    slot_count =    mrc.UInt32_P( 0x04 )
    entry_count =   mrc.UInt32_P( 0x08 )
    entries =       mrc.BlockField( KeyEntry, 0x0c, count=mrc.Ref( 'slot_count' ) )
#    garbage =       mrc.Bytes( mrc.EndOffset( 'entries' ) )


class MMapEntry( mrc.Block ):
    chunk_id =  mrc.UInt32_P( 0x00 )
    length =    mrc.UInt32_P( 0x04 )
    offset =    mrc.UInt32_P( 0x08 )
    flags =     mrc.UInt16_P( 0x0c )
    unk1 =      mrc.UInt16_P( 0x0e )
    memsize =   mrc.UInt32_P( 0x10 )

    def import_data( self, *args, **kwargs ):
        return super().import_data( *args, **kwargs )

    @property
    def repr( self ):
        return 'chunk_id: {}, length: 0x{:08x}, offset: 0x{:08x}, flags: {}'.format( riff.TagB( self.chunk_id ), self.length, self.offset, self.flags )


# rough idea of the layout of a Director file
# imap chunk
# - dunno what this does
# mmap chunk
# - this is a list of all of the chunks in the director file, including lengths and offsets
# - main bodge mechanism used to allow append-only editing of director files!
# - when another bit of the file is referring to a chunk with an index, it's usually against this thing
# KEY* chunk
# - slightly different; this is a list containing mappings between CASt chunks and the referenced data
# - index is for the mmap list
# CAS* chunk
# - ordered list of CASt objects
# - matches the ordering in the Director UI
# - index is for the mmap list
# Sord chunk
# - sets some sort of order for cast members???
# - index appears to be for the CAS* list

class IMapV4( mrc.Block ):
    unk1 =          mrc.UInt32_P( 0x00 )
    mmap_offset =   mrc.UInt32_P( 0x04 )
    version =       mrc.UInt32_P( 0x08 )
    unk2 =          mrc.Bytes( 0x0c )

class MMapV4( mrc.Block ):
    unk1 =      mrc.Bytes( 0x00, length=8 )
    entries_max = mrc.UInt32_P( 0x04 )
    entries_used = mrc.UInt32_P( 0x08 )
    unk2 =      mrc.Const( mrc.Bytes( 0x0c, length=8 ), b'\xff'*8 )
    unk3 =      mrc.UInt32_P( 0x14 )
    entries =    mrc.BlockField( MMapEntry, 0x18, count=mrc.Ref( 'entries_max' ), fill=b'\xaa'*0x14 )
    garbage =   mrc.Bytes( mrc.EndOffset( 'entries' ) )

    @property
    def repr( self ):
        return 'entries_max: {}, entries_used: {}'.format( self.entries_max, self.entries_used )

class SordV4( mrc.Block ):
    unk1 = mrc.Bytes( 0x00, length=0xc )
    count = mrc.UInt32_BE( 0x0c )
    unk2 = mrc.UInt16_BE( 0x10 )
    unk3 = mrc.UInt16_BE( 0x12 )
    index = mrc.UInt16_BE( 0x14, count=mrc.Ref( 'count' ) )


class CastListV4( mrc.Block ):
    index = mrc.UInt32_BE( 0x00, stream=True )


class TextV4( mrc.Block ):
    unk1 = mrc.UInt32_BE( 0x00 )
    length = mrc.UInt32_BE( 0x04 )
    unk2 = mrc.UInt32_BE( 0x08 )
    data = mrc.Bytes( 0xc, length=mrc.Ref( 'length' ) )
    unk3 = mrc.Bytes( mrc.EndOffset( 'data' ) )



class Sprite( mrc.Block ):
    script_id = mrc.UInt8( 0x00 )
    sprite_type = mrc.UInt8( 0x01 )
    x2 = mrc.UInt16_BE( 0x02 )
    flags = mrc.UInt16_BE( 0x04 )
    cast_id = mrc.UInt16_BE( 0x06 )
    start_x = mrc.UInt16_BE( 0x08 )
    start_y = mrc.UInt16_BE( 0x0a )
    height = mrc.UInt16_BE( 0x0c )
    width = mrc.UInt16_BE( 0x0e )
    

class ScriptNamesV4( mrc.Block ):
    # used to store the names of functions invoked with CALL_EXTERNAL
    unk1 = mrc.UInt16_BE( 0x00 )
    unk2 = mrc.UInt16_BE( 0x02 )
    unk3 = mrc.UInt16_BE( 0x04 )
    unk4 = mrc.UInt16_BE( 0x06 )
    length_1 = mrc.UInt16_BE( 0x08 )
    unk5 = mrc.UInt16_BE( 0x0a )
    length_2 = mrc.UInt16_BE( 0x0c )
    unk6 = mrc.UInt16_BE( 0x0e )
    offset = mrc.UInt16_BE( 0x10 )
    count = mrc.UInt16_BE( 0x12 )
    names = mrc.StringField( mrc.Ref( 'offset' ), count=mrc.Ref( 'count' ), length_field=mrc.UInt8, encoding='latin1' )


class ScriptContextEntry( mrc.Block ):
    unk1 = mrc.UInt16_BE( 0x00 )
    unk2 = mrc.UInt16_BE( 0x02 )
    unk3 = mrc.UInt16_BE( 0x04 )
    index =     mrc.UInt16_BE( 0x06 )       # for mmap.entries
    unk4 =      mrc.Bits16( 0x08, 0b1111111111111011 )
    active =    mrc.Bits16( 0x08, 0b0000000000000100 )
    link =      mrc.Int16_BE( 0x0a )
    
    @property
    def repr( self ):
        return 'index: {}, active: {}'.format( self.index, self.active )


class ScriptContextV4( mrc.Block ):
    #test = mrc.Bytes()
    unk1 = mrc.Bytes( 0x00, length=0x8 )
    list_count = mrc.UInt32_BE( 0x08 )
    list_count_2 = mrc.UInt32_BE( 0x0c )
    list_offset = mrc.UInt16_BE( 0x10 )
    unk2 = mrc.UInt16_BE( 0x12 )
    unk3 = mrc.Bytes( 0x14, length=22 )

    entries = mrc.BlockField( ScriptContextEntry, mrc.Ref( 'list_offset' ), count=mrc.Ref( 'list_count' ) )


# source: http://fileformats.archiveteam.org/wiki/Lingo_bytecode#Header

class ScriptConstantType( IntEnum ):
    STRING =    0x0001
    UINT32 =    0x0004
    FLOAT =     0x0009


class Blank( mrc.Block ):
    value = None

    @property
    def repr( self ):
        return ''

class Write8( mrc.Block ):
    value = mrc.UInt8( 0x00 )
            
    @property
    def repr( self ):
        return '0x{:02x}'.format(self.value)

class Write16( mrc.Block ):
    value = mrc.UInt16_BE( 0x00 )
    
    @property
    def repr( self ):
        return '0x{:04x}'.format(self.value)


LINGO_V4_LIST = [
    ('EXIT', 0x01, Blank),
    ('PUSH_0', 0x03, Blank),
    ('MULT', 0x04, Blank),
    ('ADD', 0x05, Blank),
    ('SUB', 0x06, Blank),
    ('DIV', 0x07, Blank),
    ('MOD', 0x08, Blank),
    ('NEGATE', 0x09, Blank),
    ('AMPERSAND', 0x0a, Blank),
    ('CONCAT', 0x0b, Blank),
    ('LT', 0x0c, Blank),
    ('LE', 0x0d, Blank),
    ('NEQ', 0x0e, Blank),
    ('EQ', 0x0f, Blank),
    ('GT', 0x10, Blank),
    ('GE', 0x11, Blank),
    ('AND', 0x12, Blank),
    ('OR', 0x13, Blank),
    ('NOT', 0x14, Blank),
    ('CONTAINS', 0x15, Blank),
    ('STARTS', 0x16, Blank),
    ('OF', 0x17, Blank),
    ('HILITE', 0x18, Blank),
    ('INTERSECTS', 0x19, Blank),
    ('WITHIN', 0x1a, Blank),
    ('FIELD', 0x1b, Blank),
    ('TELL', 0x1c, Blank),
    ('TELL_DONE', 0x1d, Blank),
    ('LIST', 0x1e, Blank),
    ('PROPLIST', 0x1f, Blank),

    # 1 byte payload
    ('PUSH_INT', 0x41, Write8),
    ('PUSH_ARGCNORET', 0x42, Write8),
    ('PUSH_ARGC', 0x43, Write8),
    ('PUSH_CONST', 0x44, Write8),
    ('PUSH_NAME', 0x45, Write8),
    ('PUSH_OBJECT', 0x46, Write8),
    
    ('PUSH_GLOBAL', 0x49, Write8),
    ('PUSH_PROPERTY', 0x4a, Write8),
    ('PUSH_PARAM', 0x4b, Write8),
    ('PUSH_LOCAL', 0x4c, Write8),
    
    ('POP_GLOBAL', 0x4f, Write8),
    ('POP_PROPERTY', 0x50, Write8),
    ('POP_PARAM', 0x51, Write8),
    ('POP_LOCAL', 0x52, Write8),

    ('JUMP_BACK', 0x54, Write8),

    ('CALL', 0x56, Write8),
    ('CALL_EXTERNAL', 0x57, Write8),
    ('CALL_METHOD', 0x58, Write8),
    ('PUT_TEXTVAR', 0x59, Write8),
    ('PUT', 0x5a, Write8),
    ('SLICE_DEL', 0x5b, Write8),
    
    ('THE_ENTITY_GET', 0x5c, Write8),
    ('THE_ENTITY_SET', 0x5d, Write8),

    ('PUSH_PROPERTY_CTX', 0x5f, Write8),
    ('POP_PROPERTY_CTX', 0x60, Write8),
    ('PUSH_PROPERTY_OBJ', 0x61, Write8),
    ('POP_PROPERTY_OBJ', 0x62, Write8),
    ('CALL_EXTERNAL_OBJ', 0x63, Write8),
    ('PUSH_FROM_STACK', 0x64, Write8),
    ('POP_FROM_STACK', 0x65, Write8),
    ('PUSH_PROPERTY_RO', 0x66, Write8),

    # 2 byte payload
    ('PUSH_INT_U16', 0x81, Write16),
    ('PUSH_ARGCNORET_U16', 0x82, Write16),
    ('PUSH_ARGC_U16', 0x83, Write16),
    ('PUSH_CONST_U16', 0x84, Write16),

    ('PUSH_GLOBAL_U16', 0x89, Write16),
    
    ('POP_GLOBAL_U16', 0x8f, Write16),
    ('POP_PROPERTY_U16', 0x90, Write16),

    ('JUMP', 0x93, Write16),
    
    ('JUMP_IF', 0x95, Write16),
    
    ('POP_PROPERTY_CTX_U16', 0xa0, Write16),
    ('PUSH_PROPERTY_OBJ_U16', 0xa1, Write16),
    ('POP_PROPERTY_OBJ_U16', 0xa2, Write16),

    ('PUSH_PATH_U16', 0xa6, Write16),
]

# add stubs for missing instructions
LINGO_COVERAGE = set( (x[1] for x in LINGO_V4_LIST) )
for i in range( 0x00, 0x40 ):
    if i not in LINGO_COVERAGE:
        LINGO_V4_LIST.append( ('UNK_{:02X}'.format( i ), i, Blank ) )
for i in range( 0x40, 0x80 ):
    if i not in LINGO_COVERAGE:
        LINGO_V4_LIST.append( ('UNK_{:02X}'.format( i ), i, Write8 ) )
for i in range( 0x80, 0x100 ):
    if i not in LINGO_COVERAGE:
        LINGO_V4_LIST.append( ('UNK_{:02X}'.format( i ), i, Write16 ) )

LingoV4 = IntEnum( 'LingoV4', [(x[0], x[1]) for x in LINGO_V4_LIST] )
LINGO_V4_MAP = {LingoV4( x[1] ): x[2] for x in LINGO_V4_LIST}


class ScriptString( mrc.Block ):
    length = mrc.UInt32_BE( 0x00 )
    value = mrc.CString( 0x04, length=mrc.Ref( 'length' ), encoding='latin1' )

    @property
    def repr( self ):
        return self.value

class ScriptConstantString( mrc.Block ):
    offset = mrc.UInt32_BE( 0x00 )
    value = mrc.StoreRef( ScriptString, mrc.Ref( '_parent._parent.consts_store' ), offset=mrc.Ref( 'offset' ), size=None )

    @property
    def repr( self ):
        return self.value.repr

class ScriptConstantUInt32( mrc.Block ):
    value = mrc.UInt32_BE( 0x00 )

    @property
    def repr( self ):
        return '{}'.format( self.value )

class ScriptFloat( mrc.Block ):
    length = mrc.Const( mrc.UInt32_BE( 0x00 ), 0x0a )
    sign = mrc.Bits16( 0x04, bits=0x8000 )
    exponent = mrc.Bits16( 0x04, bits=0x7fff )
    integer = mrc.Bits64( 0x06, bits=0x8000000000000000 )
    fraction = mrc.Bits64( 0x06, bits=0x7fffffffffffffff )

    @property
    def value( self ):
        if (self.exponent == 0):
            f64exp = 0
        elif (self.exponent == 0x7fff):
            f64exp = 0x7ff
        else:
            normexp = self.exponent - 0x3fff    # value range from -0x3ffe to 0x3fff
            if not (-0x3fe <= normexp < 0x3ff):
                raise ValueError( 'Exponent too big for a float64' )

            f64exp = normexp + 0x3ff

        f64fract = self.fraction >> 11
        f64bin = utils.to_uint64_be( f64fract + (f64exp << 52) + 0x80000000*self.sign )
        f64 = utils.from_float64_be( f64bin )
        return f64

    @property
    def repr( self ):
        return self.value

class ScriptConstantFloat( mrc.Block ):
    offset = mrc.UInt32_BE( 0x00 )
    value = mrc.StoreRef( ScriptFloat, mrc.Ref( '_parent._parent.consts_store' ), offset=mrc.Ref( 'offset' ), size=None )

    @property
    def repr( self ):
        return self.value.repr

class ScriptConstantV4( mrc.Block ):
    SCRIPT_CONSTANT_TYPES = {
        0x0001: ScriptConstantString,
        0x0004: ScriptConstantUInt32,
        0x0009: ScriptConstantFloat
    }

    const_type = mrc.UInt16_BE( 0x00, enum=ScriptConstantType )
    const = mrc.BlockField( SCRIPT_CONSTANT_TYPES, 0x02, block_type=mrc.Ref( 'const_type' ) )

    @property
    def repr( self ):
        return '{}: {}'.format( self.const_type, self.const.repr )


class ScriptConstantV5( mrc.Block ):
    SCRIPT_CONSTANT_TYPES = {
        0x0001: ScriptConstantString,
        0x0004: ScriptConstantUInt32,
        0x0009: ScriptConstantFloat
    }

    const_type = mrc.UInt32_BE( 0x00, enum=ScriptConstantType )
    const = mrc.BlockField( SCRIPT_CONSTANT_TYPES, 0x04, block_type=mrc.Ref( 'const_type' ) )

    @property
    def repr( self ):
        return '{}: {}'.format( self.const_type, self.const.repr )


class ScriptGlobal( mrc.Block ):
    name_index = mrc.UInt16_BE( 0x00 )


class ScriptCode( mrc.Block ):
    instructions = mrc.ChunkField( LINGO_V4_MAP, 0x00, id_field=mrc.UInt8, id_enum=LingoV4, default_klass=Blank )


class ScriptArguments( mrc.Block ):
    name_index = mrc.UInt16_BE( 0x00, count=mrc.Ref( '_parent.args_count' ) )


class ScriptVariables( mrc.Block ):
    name_index = mrc.UInt16_BE( 0x00, count=mrc.Ref( '_parent.vars_count' ) )


class ScriptFunction( mrc.Block ):
    name_index = mrc.UInt16_BE( 0x00 )
    unk1 = mrc.UInt16_BE( 0x02 )
    length = mrc.UInt32_BE( 0x04 )
    offset = mrc.UInt32_BE( 0x08 )
    args_count = mrc.UInt16_BE( 0x0c )
    args_offset = mrc.UInt32_BE( 0x0e )
    vars_count = mrc.UInt16_BE( 0x12 )
    vars_offset = mrc.UInt32_BE( 0x14 )
    unk2 = mrc.UInt16_BE( 0x18 )
    unk8 = mrc.UInt16_BE( 0x1a )
    unk9 = mrc.UInt16_BE( 0x1c )
    unk10 = mrc.UInt16_BE( 0x1e )
    unk11 = mrc.UInt16_BE( 0x20 )
    unk12 = mrc.UInt16_BE( 0x22 )
    unk13 = mrc.UInt16_BE( 0x24 )
    unk14 = mrc.UInt16_BE( 0x26 )
    unk15 = mrc.UInt16_BE( 0x28 )

    code = mrc.StoreRef( ScriptCode, mrc.Ref( '_parent.code_store' ), offset=mrc.Ref( 'offset' ), size=mrc.Ref( 'length' ) )

    args = mrc.StoreRef( ScriptArguments, mrc.Ref( '_parent.code_store' ), offset=mrc.Ref( 'args_offset' ) )
    vars = mrc.StoreRef( ScriptVariables, mrc.Ref( '_parent.code_store' ), offset=mrc.Ref( 'vars_offset' ) )

    @property
    def args_size( self ):
        return self.args_count * 2

    @property
    def vars_size( self ):
        return self.vars_count * 2

    @property
    def repr( self ):
        return '{}'.format( self.name )


class ScriptV4( mrc.Block ):
    unk1 = mrc.Bytes( 0x00, length=0x10 )
    code_store_offset = mrc.UInt16_BE( 0x10 )
    unk2 = mrc.Bytes( 0x12, length=0x1c )
    cast_id = mrc.UInt16_BE( 0x2e )
    factory_name_id = mrc.Int16_BE( 0x30 )
    unk9 = mrc.Bytes( 0x32, length=0xe )

    globals_offset = mrc.UInt16_BE( 0x40 )
    globals_count = mrc.UInt16_BE( 0x42 )
    unk3 = mrc.Bytes( 0x44, length=4 )
    functions_count = mrc.UInt16_BE( 0x48 )
    unk4 = mrc.UInt16_BE( 0x4a )
    
    functions_offset = mrc.UInt16_BE( 0x4c )

    consts_count = mrc.UInt16_BE( 0x4e )

    unk6 = mrc.UInt16_BE( 0x50 )

    consts_offset = mrc.UInt16_BE( 0x52 )
    unk7 = mrc.UInt16_BE( 0x54 )
    consts_unk = mrc.UInt16_BE( 0x56 )
    unk8 = mrc.UInt16_BE( 0x58 )
    consts_base = mrc.UInt16_BE( 0x5a )

    @property
    def code_store_size( self ):
        return self.functions_offset - self.code_store_offset

    @code_store_size.setter
    def code_store_size( self, value ):
        self.functions_offset = value + self.code_store_offset
    
    @property
    def code_store_base( self ):
        return -self.code_store_offset

    code_store_raw = mrc.Bytes( mrc.Ref( 'code_store_offset' ), length=mrc.Ref( 'code_store_size' ) )

    globals = mrc.BlockField( ScriptGlobal, mrc.Ref( 'globals_offset' ), count=mrc.Ref( 'globals_count' ) )
    functions = mrc.BlockField( ScriptFunction, mrc.Ref( 'functions_offset' ), count=mrc.Ref( 'functions_count' ) )
    consts = mrc.BlockField( ScriptConstantV4, mrc.Ref( 'consts_offset' ), count=mrc.Ref( 'consts_count' ) )
    consts_raw = mrc.Bytes( mrc.EndOffset( 'consts' ) )

    @property
    def consts_store_offset( self ):
        return self.consts_base-self.get_field_end_offset( 'consts' )

    #test = mrc.Bytes( 0x00 )

    def __init__( self, *args, **kwargs ):
        self.consts_store = mrc.Store( self, mrc.Ref( 'consts_raw' ),
                                        base_offset=mrc.Ref( 'consts_store_offset' ) )
        self.code_store = mrc.Store( self, mrc.Ref( 'code_store_raw' ),
                                        base_offset=mrc.Ref( 'code_store_base' ) )

        super().__init__( *args, **kwargs )


class ScriptV5( ScriptV4 ):
    consts = mrc.BlockField( ScriptConstantV5, mrc.Ref( 'consts_offset' ), count=mrc.Ref( 'consts_count' ) )


class ConfigV4( mrc.Block ):
    length = mrc.UInt16_BE( 0x00 )
    ver1 = mrc.UInt16_BE( 0x02 )
    movie_rect = mrc.BlockField( Rect, 0x04 )
    cast_array_start = mrc.UInt16_BE( 0x0c )
    cast_array_end = mrc.UInt16_BE( 0x0e )
    frame_rate = mrc.UInt8( 0x10 )
    light_switch = mrc.UInt8( 0x11 )
    
    unk1 = mrc.Int16_BE( 0x12 )
    
    comment_font = mrc.Int16_BE( 0x14 )
    comment_size = mrc.Int16_BE( 0x16 )
    comment_style = mrc.UInt8( 0x18 )
    comment_style_2 = mrc.UInt8( 0x19 )
    stage_colour = mrc.Int16_BE( 0x1a )
    bit_depth = mrc.Int16_BE( 0x1c )
    colour_flag = mrc.UInt8( 0x1e )
    unk5 = mrc.UInt8( 0x1f )
    unk6 = mrc.Int32_BE( 0x20 )
    unk7 = mrc.Int16_BE( 0x24 )
    unk8 = mrc.Int16_BE( 0x26 )
    unk9 = mrc.Int32_BE( 0x28 )
    unk10 = mrc.Int32_BE( 0x2c )
    unk11 = mrc.Int32_BE( 0x30 )
    unk12 = mrc.UInt8( 0x34 )
    unk17 = mrc.UInt8( 0x35 )
    unk13 = mrc.Int16_BE( 0x36 )
    unk14 = mrc.Int16_BE( 0x38 )
    protection_bits = mrc.Int16_BE( 0x3a )
    unk15 = mrc.UInt32_BE( 0x3c )
    checksum = mrc.UInt32_BE( 0x40 )
    unk16 = mrc.UInt16_BE( 0x44 )
    palette_id = mrc.UInt16_BE( 0x46 )

    unk4 = mrc.Bytes( 0x48, length=0x08 )

    @property
    def checksum_v4( self ):
        mult = lambda a, b: (a * b) & 0xffffffff

        stack = []
        ax = self.movie_rect.right
        ax += 6
        stack.append( ax )
        ax = self.movie_rect.bottom
        ax += 5
        stack.append( ax )
        ax = self.movie_rect.left
        ax += 4
        stack.append( ax )
        ax = self.movie_rect.top
        ax += 3
        stack.append( ax )
        ax = self.ver1
        ax += 2
        cx = self.length
        cx += 1
        ax *= cx
        stack.append( ax )
        ax = stack.pop() // stack.pop()
        stack.append( ax )
        ax = mult( stack.pop(), stack.pop() )
        stack.append( ax )
        ax = stack.pop() // stack.pop()
        stack.append( ax )
        ax = mult( stack.pop(), stack.pop() )

        bx = ax
        ax = self.cast_array_start
        ax += 7
        bx -= ax
        stack.append( bx )

        ax = self.cast_array_end
        ax += 8
        stack.append( ax )
        ax = mult( stack.pop(), stack.pop() )

        temp_sum = ax

        ax = self.frame_rate
        ax += 9
        temp_sum -= ax

        ax = self.light_switch
        ax += 10
        temp_sum -= ax

        ax = self.unk1
        ax += 11
        temp_sum += ax

        stack.append( temp_sum )

        ax = self.comment_font
        ax += 12

        stack.append( ax )

        temp_sum = mult( stack.pop(), stack.pop() )

        ax = self.comment_size
        ax += 13
        temp_sum += ax

        stack.append( temp_sum )

        ax = self.comment_style
        ax += 14
        stack.append( ax )

        temp_sum = mult( stack.pop(), stack.pop() )

        ax = self.stage_colour
        ax += 15

        temp_sum += ax 

        ax = self.bit_depth
        ax += 16
        temp_sum += ax

        ax = self.colour_flag
        ax += 17
        temp_sum += ax

        stack.append( temp_sum )

        ax = self.unk5
        ax += 18
        stack.append( ax )

        temp_sum = mult( stack.pop(), stack.pop() )

        eax = self.unk6
        eax += 19
        temp_sum += eax
        stack.append( temp_sum )

        ax = self.unk7
        ax += 20
        stack.append( ax )

        temp_sum = mult( stack.pop(), stack.pop() )

        ax = self.unk8
        ax += 21
        temp_sum += ax

        ax = self.unk9
        ax += 22
        temp_sum += ax

        ax = self.unk10
        ax += 23
        temp_sum += ax

        ax = self.unk11
        ax += 24
        temp_sum += ax

        stack.append( temp_sum )

        ax = self.unk12
        ax += 25
        stack.append( ax )

        temp_sum = mult( stack.pop(), stack.pop() )

        ax = self.unk13
        ax += 26

        temp_sum += ax
        stack.append( temp_sum )

        ax = self.unk14
        ax += 27
        stack.append( ax )

        ax = mult( stack.pop(), stack.pop() )

        stack.append( ax )

        ax = 0xe06
        ax = self.protection_bits * ax
        ax -= 0x00bb0000
        stack.append( ax )

        ax = mult( stack.pop(), stack.pop() )

        ax ^= 0x72616c66  # 'ralf'

        return ax

        


class DirectorV4Map( riff.RIFXMap ):
    CHUNK_MAP = {
        riff.Tag( b'imap' ): IMapV4,
        riff.Tag( b'mmap' ): MMapV4,
        riff.Tag( b'KEY*' ): KeyV4,
        riff.Tag( b'Sord' ): SordV4,
        riff.Tag( b'CAS*' ): CastListV4,
        riff.Tag( b'CASt' ): CastV4,
        riff.Tag( b'snd ' ): SoundV4,
        riff.Tag( b'BITD' ): BitmapV4,
        riff.Tag( b'STXT' ): TextV4,
        riff.Tag( b'Lscr' ): ScriptV4,
        riff.Tag( b'Lnam' ): ScriptNamesV4,
        riff.Tag( b'Lctx' ): ScriptContextV4,
        riff.Tag( b'VWSC' ): ScoreV4,
        riff.Tag( b'VWCF' ): ConfigV4,
    }
DirectorV4Map.CHUNK_MAP[riff.Tag( b'RIFX' )] = DirectorV4Map


class DirectorV4( riff.RIFX ):
    CHUNK_MAP_CLASS = DirectorV4Map


class DirectorV4_LE( riff.RIFX ):
    _endian = 'little'
    CHUNK_MAP_CLASS = DirectorV4Map


class DirectorV5Map( riff.RIFXMap ):
    CHUNK_MAP = {
        riff.Tag( b'imap' ): IMapV4,
        riff.Tag( b'mmap' ): MMapV4,
        riff.Tag( b'KEY*' ): KeyV4,
        riff.Tag( b'Sord' ): SordV4,
        riff.Tag( b'CAS*' ): CastListV4,
        riff.Tag( b'CASt' ): CastV4,
        riff.Tag( b'snd ' ): mrc.Unknown,
        riff.Tag( b'BITD' ): BitmapV4,
        riff.Tag( b'STXT' ): TextV4,
        riff.Tag( b'Lscr' ): ScriptV5,
        riff.Tag( b'Lnam' ): ScriptNamesV4,
        riff.Tag( b'Lctx' ): ScriptContextV4,
        riff.Tag( b'VWSC' ): ScoreV4,
        riff.Tag( b'VWCF' ): ConfigV4,
    }
DirectorV4Map.CHUNK_MAP[riff.Tag( b'RIFX' )] = DirectorV4Map


class DirectorV5( riff.RIFX ):
    CHUNK_MAP_CLASS = DirectorV5Map


class DirectorV5_LE( riff.RIFX ):
    _endian = 'little'
    CHUNK_MAP_CLASS = DirectorV5Map


class PJ93_LE( mrc.Block ):
    _endian = 'little'
    
    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'PJ93' )
    rifx_offset = mrc.UInt32_P( 0x04 )
    fontmap_offset = mrc.UInt32_P( 0x08 )
    resfork1_offset = mrc.UInt32_P( 0x0c )
    resfork2_offset = mrc.UInt32_P( 0x10 )
    dirdib_drv_offset = mrc.UInt32_P( 0x14 )
    macromix_dll_offset = mrc.UInt32_P( 0x18 )
    rifx_offset_dup = mrc.UInt32_P( 0x1c )
    unk1 = mrc.Bytes( 0x20, length=0xc ) 


class MV93_LE( mrc.Block ):
    _endian = 'little'
    CHUNK_MAP_CLASS = DirectorV4Map.CHUNK_MAP

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'XFIR' )
    data_length = mrc.UInt32_P( 0x04 )
    magic2 = mrc.Const( mrc.Bytes( 0x08, length=4 ), b'39VM' )
    stream = mrc.ChunkField( CHUNK_MAP_CLASS, 0x0c, stream=True, id_field=mrc.UInt32_P, length_field=mrc.UInt32_P, default_klass=mrc.Unknown, alignment=0x2, fill=b'' )


class MV93( mrc.Block ):
    _endian = 'big'
    CHUNK_MAP_CLASS = DirectorV4Map.CHUNK_MAP

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'RIFX' )
    data_length = mrc.UInt32_P( 0x04 )
    magic2 = mrc.Const( mrc.Bytes( 0x08, length=4 ), b'MV93' )
    stream = mrc.ChunkField( CHUNK_MAP_CLASS, 0x0c, stream=True, id_field=mrc.UInt32_P, length_field=mrc.UInt32_P, default_klass=mrc.Unknown, alignment=0x2, fill=b'' )


class MV93_V5( mrc.Block ):
    _endian = 'big'
    CHUNK_MAP_CLASS = DirectorV5Map.CHUNK_MAP

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'RIFX' )
    data_length = mrc.UInt32_P( 0x04 )
    magic2 = mrc.Const( mrc.Bytes( 0x08, length=4 ), b'MV93' )
    stream = mrc.ChunkField( CHUNK_MAP_CLASS, 0x0c, stream=True, id_field=mrc.UInt32_P, length_field=mrc.UInt32_P, default_klass=mrc.Unknown, alignment=0x2, fill=b'' )


class DirectorV4Parser( object ):
    def __init__( self, dirfile ):
        self.dirfile = dirfile
        self.map_offset = dirfile.get_field_start_offset( 'map' ) + dirfile.map.get_field_start_offset( 'stream' )
        self.riff_offsets = [self.map_offset]
        for i, x in enumerate( dirfile.map.stream ):
            if i == 0:
                continue
            self.riff_offsets.append( self.riff_offsets[-1]+dirfile.map.get_field_size( 'stream', index=i-1 ) )

        _, self.imap = self.get_from_offset( self.map_offset )
        _, self.mmap = self.get_from_offset( self.imap.obj.mmap_offset )
        _, self.key = self.get_last_from_mmap( b'KEY*' )
        _, self.cas = self.get_last_from_mmap( b'CAS*' )
        _, self.score = self.get_last_from_mmap( b'VWSC' )
        _, self.config = self.get_last_from_mmap( b'VWCF' )
        _, self.cast_order = self.get_last_from_mmap( b'Sord' )
        #self.cast = [self.get_from_mmap_index( self.cas.obj.index[i-1] ) for i in self.cast_order.obj.index]
        self.cast = [(i, self.get_from_mmap_index( i ).obj) if i else (None, None) for i in self.cas.obj.index]
        self.cast_map = {self.config.obj.cast_array_start + i: self.get_from_mmap_index( x ).obj for i, x in enumerate( self.cas.obj.index ) if x != 0}
        _, self.script_context = self.get_last_from_mmap( b'Lctx' )
        _, self.script_names = self.get_last_from_mmap( b'Lnam' )
        self.script_ids = []
        self.scripts = []
        self.scripts_text = []
        for script_cast in [c for _, c in self.cast if c and c.cast_type == CastType.SCRIPT]:
            script_id = script_cast.detail.script_id-1
            self.script_ids.append( script_id )
            self.scripts.append( self.get_from_mmap_index( self.script_context.obj.entries[script_id].index ) )
            self.scripts_text.append( script_cast.detail.code.decode('latin').replace('\r', '\n') )
        self.bitmaps = []
        for index, cast in [(i, c) for i, c in self.cast if c and c.cast_type == CastType.BITMAP]:
            bitmaps = [self.get_from_mmap_index( x.section_index ).obj for x in self.key.obj.entries if riff.TagB( x.chunk_id ) == b'BITD' and x.cast_index == index]
            if bitmaps:
                #bitmaps[0].data = BitmapCompressor().import_data( bitmaps[0].data ).payload
                cast.detail._data = bitmaps[0]
            self.bitmaps.append((index, cast))

    def get_from_offset( self, offset ):
        for i, x in enumerate( self.riff_offsets ):
            if x == offset:
                return i, self.dirfile.map.stream[i]
        raise ValueError( 'Can\'t find a matching start offset' )

    def get_all_from_mmap( self, chunk_id, include_missing=False ):
        result = [(i, self.get_from_offset( x.offset )[1]) for i, x in enumerate( self.mmap.obj.entries ) if i < self.mmap.obj.entries_used and x.chunk_id == riff.Tag( chunk_id )]
        if not include_missing:
            result = [x for x in result if x[1].obj is not None]
        return result

    def get_last_from_mmap( self, chunk_id, include_missing=False ):
        vals = self.get_all_from_mmap( chunk_id, include_missing )
        if not vals:
            return None, None
        return vals[-1]

    def get_from_mmap_index( self, index ):
        return self.get_from_offset( self.mmap.obj.entries[index].offset )[1]

    def get_from_mmap_list( self ):
        result = []
        for i in range( self.mmap.obj.entries_used ):
            if self.mmap.obj.entries[i].offset != 0 and self.mmap.obj.entries[i].chunk_id != b'free':
                result.append( self.get_from_offset( self.mmap.obj.entries[i].offset )[1] )
            else:
                result.append( None )
        return result

    def dump_scripts( self ):
        for i, script in enumerate( self.scripts ):
            print('SCRIPT {}'.format( self.script_ids[i] ))
            print('NAMES: {}'.format( self.script_names.obj.names ))
            print('CODE:')
            print(self.scripts_text[i])
            name_lookup = lambda n: self.script_names.obj.names[n] if n in range( len( self.script_names.obj.names ) ) else 'unk_{}'.format(n)

            assert riff.TagB( script.id ) == b'Lscr'
            for j, f in enumerate(script.obj.functions):
                if f is None:
                    print('FUNCTION {} - None'.format(j))
                    continue
                print('FUNCTION {} - {}({})'.format(j, name_lookup( f.name_index ), ', '.join( [name_lookup( a ) for a in f.args.name_index] )))
                print('VARS: {}'.format(', '.join([name_lookup( v ) for v in f.vars.name_index])))
                for inst in f.code.instructions:
                    if self.script_names:
                        if inst.id in (LingoV4.CALL,):
                            print('{} # {}()'.format( inst, name_lookup( script.obj.functions[inst.obj.value].name_index ) ))
                        elif inst.id in (LingoV4.CALL_EXTERNAL,):
                            print('{} # {}()'.format( inst, name_lookup( inst.obj.value ) ))
                        elif inst.id in (LingoV4.PUSH_PROPERTY, LingoV4.POP_PROPERTY, LingoV4.PUSH_PROPERTY_CTX, LingoV4.POP_PROPERTY_CTX, LingoV4.PUSH_PROPERTY_OBJ, LingoV4.POP_PROPERTY_OBJ, LingoV4.PUSH_PROPERTY_RO, LingoV4.PUSH_GLOBAL, LingoV4.POP_GLOBAL, LingoV4.PUSH_OBJECT, LingoV4.PUSH_NAME):
                            print('{} # {}'.format( inst, name_lookup( inst.obj.value ) ))
                        elif inst.id in (LingoV4.PUSH_CONST,):
                            print('{} # {}'.format( inst, script.obj.consts[inst.obj.value // 6] ))
                        elif inst.id in (LingoV4.PUSH_PARAM, LingoV4.POP_PARAM,):
                            print('{} # {}'.format( inst, name_lookup( f.args.name_index[inst.obj.value // 6] ) if f.args.name_index else 'unk_{}'.format(inst.obj.value // 6) ))
                        elif inst.id in (LingoV4.PUSH_LOCAL, LingoV4.POP_LOCAL,):
                            print('{} # {}'.format( inst, name_lookup( f.vars.name_index[inst.obj.value // 6] ) if f.vars.name_index else 'unk_{}'.format(inst.obj.value // 6) ))
                        else:
                            print(inst)
                    else:
                        print(inst)
            for j, c in enumerate(script.obj.consts):
                print('CONST {}'.format(j))
                print(c)
            for j, g in enumerate(script.obj.globals):
                print('GLOBAL {}'.format(j))
                if self.script_names:
                    print(self.script_names.obj.names[g.name_index])
                else:
                    print(g.name_index)
            print()


def unlock_dir_file( filename, klass=DirectorV4 ):
    f = open( filename, 'r+b' )

    data = f.read()
    f.seek( 0 )
    parser = DirectorV4Parser( klass( data ) )
    index, chunk = parser.get_all_from_mmap( b'VWCF' )[0]
    if chunk.obj.protection_bits % 23:
        print('File is unprotected!')
    else:
        print('File is protected, fixing!')
        old_data = chunk.obj.export_data()
        chunk.obj.ver1 = 0x045D
        chunk.obj.protection_bits += 1
        chunk.obj.checksum = chunk.obj.checksum_v4
        new_data = chunk.obj.export_data()
        for location in utils.find_all( data, old_data ):
            f.seek( location )
            f.write( new_data )
    f.close()
