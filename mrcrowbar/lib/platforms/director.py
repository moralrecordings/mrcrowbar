
from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img
from mrcrowbar.lib.audio import base as aud
from mrcrowbar.lib.containers import riff
from mrcrowbar import utils

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


class ChannelCompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        result = bytearray( 50*25 )
        pointer = 0
        while pointer < len( buffer ):
            size = utils.from_uint16_be( buffer[pointer:pointer+2] )
            offset = utils.from_uint16_be( buffer[pointer+2:pointer+4] )
            result[offset:offset+size] = buffer[pointer+4:pointer+4+size]
        return mrc.TransformResult( payload=result, end_offset=pointer )


class ChannelV4( mrc.Block ):
    channel_size = mrc.UInt16_BE( 0x00 )
    channel_offset = mrc.UInt16_BE( 0x02 )
    data = mrc.Bytes( 0x04, length=mrc.Ref( 'channel_size' ) )

    @property
    def channel_row( self ):
        return self.channel_offset // 0x14

    @property
    def channel_type( self ):
        return self.channel_offset % 0x14

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


class FramesV4( mrc.Block ):
    size = mrc.UInt32_BE( 0x00 )
    unk1 = mrc.UInt32_BE( 0x04 )
    unk2 = mrc.UInt32_BE( 0x08 )
    unk3 = mrc.UInt16_BE( 0x0c )
    unk4 = mrc.UInt16_BE( 0x0e )
    unk5 = mrc.UInt16_BE( 0x10 )
    unk6 = mrc.UInt16_BE( 0x12 )

    frames = mrc.BlockField( FrameV4, 0x14, stream=True, length=mrc.Ref( 'size_frames' ) )

    @property
    def size_frames( self ):
        return self.size-0x14

    @property
    def repr( self ):
        return 'num_frames={}'.format( len( self.frames ) )



class SoundV4( mrc.Block ):
    unk1 = mrc.UInt16_BE( 0x00 )
    unk2 = mrc.UInt32_BE( 0x04 )
    unk3 = mrc.UInt16_BE( 0x0c )
    channels = mrc.UInt16_BE( 0x14 )
    sample_rate = mrc.UInt16_BE( 0x16 )
    unk4 = mrc.UInt16_BE( 0x18 )
    length = mrc.UInt32_BE( 0x1e )
    unk5 = mrc.UInt16_BE( 0x22 )
    length_copy = mrc.UInt32_BE( 0x24 )
    unk6 = mrc.UInt16_BE( 0x28 )
    playback_rate = mrc.UInt16_BE( 0x2a )
    unk7 = mrc.UInt16_BE( 0x2c )
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
4
class ScriptCastV4( mrc.Block ):
    unk1        = mrc.Bytes( 0x00, length=0x14 )
    script_id   = mrc.UInt16_BE( 0x14 )
    unk4_size   = mrc.UInt16_BE( 0x16 )
    unk3        = mrc.UInt32_BE( 0x18 )
    unk4        = mrc.UInt32_BE( 0x1c, count=mrc.Ref( 'unk4_size' ) )
    extra       = mrc.Bytes( mrc.EndOffset( 'unk4' ) )

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


class BitmapCastV4( mrc.Block ):
    _data = None

    bpp =           mrc.Bits16( 0x00, 0b1111000000000000 )
    pitch =         mrc.Bits16( 0x00, 0b0000111111111111 )
    initial_rect =  mrc.BlockField( Rect, 0x02 )
    bounding_rect = mrc.BlockField( Rect, 0x0a )
    reg_x =         mrc.UInt16_BE( 0x12 )
    reg_y =         mrc.UInt16_BE( 0x14 )
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
        CastType.SOUND: SoundCastV4,
        CastType.SCRIPT: ScriptCastV4,
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
    unk3 =          mrc.UInt32_P( 0x04 )
    entry_count =   mrc.UInt32_P( 0x08 )
    entries =       mrc.BlockField( KeyEntry, 0x0c, count=mrc.Ref( 'entry_count' ) )
    garbage =       mrc.Bytes( mrc.EndOffset( 'entries' ) )


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

class MMapV4( mrc.Block ):
    unk1 =      mrc.Bytes( 0x00, length=8 )
    entries_max = mrc.UInt32_P( 0x04 )
    entries_used = mrc.UInt32_P( 0x08 )
    unk2 =      mrc.Const( mrc.Bytes( 0x0c, length=8 ), b'\xff'*8 )
    unk3 =      mrc.UInt32_P( 0x14 )
    entries =    mrc.BlockField( MMapEntry, 0x18, count=mrc.Ref( 'entries_max' ), fill=b'\xaa'*0x14 )
    
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
    

class ScriptContextEntry( mrc.Block ):
    data = mrc.Bytes( 0x00, length=12 )


class ScriptNamesV4( mrc.Block ):
    # used to store the names of functions invoked with CALL_EXTERNAL
    unk1 = mrc.UInt32_BE( 0x00 )
    unk2 = mrc.UInt32_BE( 0x04 )
    unk3 = mrc.UInt32_BE( 0x08 )
    unk4 = mrc.UInt32_BE( 0x0c )
    unk5 = mrc.UInt16_BE( 0x10 )
    count = mrc.UInt16_BE( 0x12 )
    names = mrc.StringField( 0x14, count=mrc.Ref( 'count' ), length_field=mrc.UInt8 )


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
    ('EXEC', 0x1c, Blank),
    ('EXEC_END', 0x1d, Blank),
    ('DICT', 0x1f, Blank),

    # 1 byte payload
    ('PUSH', 0x41, Write8),
    ('ARGLIST', 0x42, Write8),
    ('LIST', 0x43, Write8),
    ('PUSH_CONST', 0x44, Write8),
    ('PUSH_SYMBOL', 0x45, Write8),
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
    ('AFTER', 0x59, Write8),
    ('BEFORE', 0x5a, Write8),
    ('SLICE_DEL', 0x5b, Write8),
    
    ('KERNEL_CALL', 0x5c, Write8),
    ('KERNEL_SET', 0x5d, Write8),

    ('PUSH_PROPERTY_CTX', 0x5f, Write8),
    ('POP_PROPERTY_CTX', 0x60, Write8),
    ('PUSH_PROPERTY_OBJ', 0x61, Write8),
    ('POP_PROPERTY_OBJ', 0x62, Write8),
    ('CALL_EXTERNAL_OBJ', 0x63, Write8),
    ('PUSH_FROM_STACK', 0x64, Write8),
    ('POP_FROM_STACK', 0x65, Write8),
    ('PUSH_PATH', 0x66, Write8),

    # 2 byte payload
    ('PUSH_U16', 0x81, Write16),
    ('ARGLIST_U16', 0x82, Write16),
    ('LIST_U16', 0x83, Write16),
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

LingoV4 = IntEnum( 'LingoV4', [(x[0], x[1]) for x in LINGO_V4_LIST] )
LINGO_V4_MAP = {LingoV4( x[1] ): x[2] for x in LINGO_V4_LIST}


class ScriptString( mrc.Block ):
    length = mrc.UInt32_BE( 0x00 )
    value = mrc.CString( 0x04, length=mrc.Ref( 'length' ) )

    @property
    def repr( self ):
        return self.value.decode( 'utf-8' )

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
    length = mrc.UInt32_BE( 0x00 )
    data = mrc.Bytes( 0x04, length=mrc.Ref( 'length' ) )

    @property
    def repr( self ):
        return self.data.hex()

class ScriptConstantFloat( mrc.Block ):
    offset = mrc.UInt32_BE( 0x00 )
    value = mrc.StoreRef( ScriptFloat, mrc.Ref( '_parent._parent.consts_store' ), offset=mrc.Ref( 'offset' ), size=None )

    @property
    def repr( self ):
        return self.value.repr

class ScriptConstant( mrc.Block ):
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


class ScriptCode( mrc.Block ):
    instructions = mrc.ChunkField( LINGO_V4_MAP, 0x00, id_field=mrc.UInt8, id_enum=LingoV4, default_klass=Blank )


class ScriptFunction( mrc.Block ):
    name_index = mrc.UInt16_BE( 0x00 )
    unk1 = mrc.UInt16_BE( 0x02 )
    length = mrc.UInt32_BE( 0x04 )
    offset = mrc.UInt32_BE( 0x08 )
    arg_count = mrc.UInt16_BE( 0x0c )
    unk2 = mrc.UInt32_BE( 0x0e )
    var_count = mrc.UInt16_BE( 0x12 )
    unk3 = mrc.UInt32_BE( 0x14 )
    count3 = mrc.UInt16_BE( 0x18 )
    unk4 = mrc.UInt32_BE( 0x1a )
    unk5 = mrc.UInt32_BE( 0x1e )
    unk6 = mrc.UInt16_BE( 0x22 )
    count4 = mrc.UInt16_BE( 0x24 )
    unk7 = mrc.UInt32_BE( 0x26 )

    code = mrc.StoreRef( ScriptCode, mrc.Ref( '_parent.code_store' ), offset=mrc.Ref( 'offset' ), size=mrc.Ref( 'length' ) )


class ScriptV4( mrc.Block ):
    unk1 = mrc.Bytes( 0x00, length=0x10 )
    code_store_offset = mrc.UInt16_BE( 0x10 )
    unk2 = mrc.Bytes( 0x12, length=0x2e )

    functions_offset = mrc.UInt16_BE( 0x40 )

    unk3 = mrc.Bytes( 0x42, length=6 )
    functions_count = mrc.UInt16_BE( 0x48 )
    unk4 = mrc.UInt16_BE( 0x4a )
    
    unk5 = mrc.UInt16_BE( 0x4c )

    consts_count = mrc.UInt16_BE( 0x4e )

    consts_offset = mrc.UInt16_BE( 0x52 )
    consts_unk = mrc.UInt16_BE( 0x56 )
    consts_base = mrc.UInt16_BE( 0x5a )

    #unk6 = mrc.Bytes( 0x5c, length=0xc )

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

    functions = mrc.BlockField( ScriptFunction, mrc.Ref( 'functions_offset' ), count=mrc.Ref( 'functions_count' ) )
    consts = mrc.BlockField( ScriptConstant, mrc.Ref( 'consts_offset' ), count=mrc.Ref( 'consts_count' ) )
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




class DirectorV4Map( riff.RIFXMap ):
    CHUNK_MAP = {
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
        riff.Tag( b'VWSC' ): FramesV4,
    }
DirectorV4Map.CHUNK_MAP[riff.Tag( b'RIFX' )] = DirectorV4Map


class DirectorV4( riff.RIFX ):
    CHUNK_MAP_CLASS = DirectorV4Map


class PJ93( mrc.Block ):
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


class MV93( mrc.Block ):
    _endian = 'little'

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'XFIR' )
    unk1 = mrc.Bytes( 0x04, length=0x4 )
    magic2 = mrc.Const( mrc.Bytes( 0x08, length=4 ), b'39VM' )
    stream = mrc.ChunkField( DirectorV4Map.CHUNK_MAP, mrc.EndOffset( 'magic2' ), stream=True, id_field=mrc.UInt32_P, length_field=mrc.UInt32_P, default_klass=mrc.Unknown, alignment=0x2, fill=b'' )


class MV93_BE( mrc.Block ):
    _endian = 'big'

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'RIFX' )
    unk1 = mrc.Bytes( 0x04, length=0x4 )
    magic2 = mrc.Const( mrc.Bytes( 0x08, length=4 ), b'MV93' )
    stream = mrc.ChunkField( DirectorV4Map.CHUNK_MAP, mrc.EndOffset( 'magic2' ), stream=True, id_field=mrc.UInt32_P, length_field=mrc.UInt32_P, default_klass=mrc.Unknown, alignment=0x2, fill=b'' )
