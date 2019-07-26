from enum import IntEnum
from mrcrowbar import models as mrc


class DataBlock( mrc.Block ):
    compat_stop = mrc.Const( mrc.UInt8( 0x00 ), 0x66 )
    data_type = mrc.UInt8( 0x01 )
    length = mrc.UInt32_LE( 0x02 )
    data = mrc.Bytes( 0x06, length=mrc.Ref( 'length' ) )


class MemoryWrite( mrc.Block ):
    compat_stop = mrc.Const( mrc.UInt8( 0x00 ), 0x66 )
    chip_type = mrc.UInt8( 0x01 )
    read_offset = mrc.UInt24_LE( 0x02 )
    write_offset = mrc.UInt24_LE( 0x05 )
    length = mrc.UInt24_LE( 0x08 )


class Blank( mrc.Block ):
    
    @property
    def repr( self ):
        return ''


class Write8( mrc.Block ):
    value = mrc.UInt8( 0x00 )

    @property
    def repr( self ):
        return 'value=0x{:02x}'.format( self.value )


class Write16( mrc.Block ):
    value = mrc.UInt16_LE( 0x00 )

    @property
    def repr( self ):
        return 'value=0x{:04x}'.format( self.value )


class RegisterWrite8( mrc.Block ):
    register = mrc.UInt8( 0x00 )
    value = mrc.UInt8( 0x00 )

    @property
    def repr( self ):
        return 'register=0x{:02x}, value=0x{:02x}'.format( self.register, self.value )


class Reserved8( mrc.Block ):
    unk1 = mrc.UInt8( 0x00 )


class Reserved16( mrc.Block ):
    unk1 = mrc.UInt8( 0x00 )
    unk2 = mrc.UInt8( 0x01 )


class Reserved24( mrc.Block ):
    unk1 = mrc.UInt8( 0x00 )
    unk2 = mrc.UInt8( 0x01 )
    unk3 = mrc.UInt8( 0x02 )


class Reserved32( mrc.Block ):
    unk1 = mrc.UInt8( 0x00 )
    unk2 = mrc.UInt8( 0x01 )
    unk3 = mrc.UInt8( 0x02 )
    unk4 = mrc.UInt8( 0x03 )


class PSGData( mrc.Block ):
    type = mrc.Bits( 0x00, 0b10000000 )
    data_raw = mrc.Bits( 0x00, 0b01111111 )

    @property
    def channel( self ):
        return None if not self.type else ((self.data_raw >> 5) & 0x3)
    
    @channel.setter
    def channel( self, value ):
        assert self.type
        self.data_raw &= 0b0011111
        self.data_raw |= (value & 0x3) << 5

    @property
    def control( self ):
        return None if not self.type else ('VOLUME' if ((self.data_raw >> 4) & 1) else 'TONE')

    @control.setter
    def control( self, value ):
        assert self.type
        self.data_raw &= 0b1101111
        if value == 'VOLUME':
            self.data_raw |= 0b0010000

    @property
    def data( self ):
        return self.data_raw & 0xf if self.type else self.data_raw & 0x3f

    @data.setter
    def data( self, value ):
        if self.type:
            self.data_raw &= 0b1110000
            self.data_raw |= value & 0xf
        else:
            self.data_raw &= 0b1000000
            self.data_raw |= value & 0x3f

    @property
    def repr( self ):
        result = 'type={}'.format( 'LATCH' if self.type else 'DATA' )
        if self.type:
            result += ', channel={}'.format( self.channel )
            result += ', control={}'.format( self.control )
            result += ', data={:04b}'.format( self.data )
        else:
            result += ', data={:06b}'.format( self.data )
        return result


# source: http://www.smspower.org/uploads/Music/vgmspec170.txt

COMMAND_LIST = [
    ('GG_STEREO', 0x4f, Write8),
    ('SN76489', 0x50, PSGData),
    ('YM2413', 0x51, RegisterWrite8),
    ('YM2612_0', 0x52, RegisterWrite8),
    ('YM2612_1', 0x53, RegisterWrite8),
    ('YM2151', 0x54, RegisterWrite8),
    ('YM2203', 0x55, RegisterWrite8),
    ('YM2608_0', 0x56, RegisterWrite8),
    ('YM2608_1', 0x57, RegisterWrite8),
    ('YM2610_0', 0x58, RegisterWrite8),
    ('YM2610_1', 0x59, RegisterWrite8),
    ('YM3812', 0x5a, RegisterWrite8),
    ('YM3526', 0x5b, RegisterWrite8),
    ('Y8950', 0x5c, RegisterWrite8),
    ('YMZ280B', 0x5d, RegisterWrite8),
    ('YMF262_0', 0x5e, RegisterWrite8),
    ('YMF262_1', 0x5f, RegisterWrite8),
    ('WAIT', 0x61, Write16),
    ('WAIT_735_60HZ', 0x62, Blank),
    ('WAIT_882_50HZ', 0x63, Blank),
    ('END_OF_DATA', 0x66, Blank),
    ('DATA_BLOCK', 0x67, DataBlock),
    ('MEMORY_WRITE', 0x68, MemoryWrite),
]
for i in range( 16 ):
    COMMAND_LIST.append( ( 'WAIT_{}'.format( i+1 ), 0x70+i, Blank ) )
for i in range( 16 ):
    COMMAND_LIST.append( ( 'YM2612_0_2A_WAIT_{}'.format( i ), 0x80+i, Blank ) )

for i in range( 0x30, 0x40 ):
    COMMAND_LIST.append( ( 'RESERVED_{:02X}'.format( i ), i,  Reserved8 ) )
for i in range( 0x40, 0x4f ):
    COMMAND_LIST.append( ( 'RESERVED_{:02X}'.format( i ), i,  Reserved16 ) )
for i in range( 0xa1, 0xb0 ):
    COMMAND_LIST.append( ( 'RESERVED_{:02X}'.format( i ), i,  Reserved16 ) )
for i in range( 0xc5, 0xd0 ):
    COMMAND_LIST.append( ( 'RESERVED_{:02X}'.format( i ), i,  Reserved24 ) )
for i in range( 0xd5, 0xe0 ):
    COMMAND_LIST.append( ( 'RESERVED_{:02X}'.format( i ), i,  Reserved24 ) )
for i in range( 0xe1, 0x100 ):
    COMMAND_LIST.append( ( 'RESERVED_{:02X}'.format( i ), i,  Reserved32 ) )

Command = IntEnum( 'Command', [(x[0], x[1]) for x in COMMAND_LIST] )
COMMAND_MAP = {Command(x[1]): x[2] for x in COMMAND_LIST}


class VGM150( mrc.Block ):
    magic               = mrc.Const( mrc.Bytes( 0x00, length=0x04, default=b'Vgm ' ), b'Vgm ' )
    eof_offset          = mrc.UInt32_LE( 0x04 )
    version             = mrc.UInt32_LE( 0x08 )
    sn76489_clock       = mrc.UInt32_LE( 0x0c )
    ym2413_clock        = mrc.UInt32_LE( 0x10 )
    gd3_offset          = mrc.UInt32_LE( 0x14 )
    total_sample_count  = mrc.UInt32_LE( 0x18 )
    loop_offset         = mrc.UInt32_LE( 0x1c )
    loop_sample_count   = mrc.UInt32_LE( 0x20 )
    rate                = mrc.UInt32_LE( 0x24 )
    sn76489_feedback    = mrc.UInt16_LE( 0x28 )
    sn76489_shiftwidth  = mrc.UInt8( 0x2a )
    sn76489_flags       = mrc.UInt8( 0x2b )
    ym2612_clock        = mrc.UInt32_LE( 0x2c )
    ym2151_clock        = mrc.UInt32_LE( 0x30 )
    vgm_data_offset_raw = mrc.UInt32_LE( 0x34 )
    header_extra        = mrc.Bytes( 0x38, length=0x08, default=b'\x00'*8 )

    @property
    def vgm_data_offset( self ):
        if self.version >= 0x150:
            return self.vgm_data_offset_raw + 0x34
        return 0x40

    vgm_data = mrc.ChunkField( COMMAND_MAP, mrc.Ref( 'vgm_data_offset' ), id_field=mrc.UInt8, id_enum=Command, default_klass=mrc.Unknown, stream_end=b'\x66' )
    extra = mrc.Bytes( mrc.EndOffset( 'vgm_data' ), default=b'' )



