from mrcrowbar import models as mrc
from mrcrowbar import bits, utils

from collections import namedtuple

# LPC chip constants taken from mame/src/devices/sound/tms5110r.hxx

TI_0280_PATENT_ENERGY = (0,  0,  1,  1,  2,  3,  5,  7,
			 10, 15, 21, 30, 43, 61, 86, 0 )
TI_028X_LATER_ENERGY = (0,  1,  2,  3,  4,  6,  8, 11,
		       16, 23, 33, 47, 63, 85,114, 0  )
TI_0280_2801_PATENT_PITCH = (0,  41,  43,  45,  47,  49,  51,  53,
		            55,  58,  60,  63,  66,  70,  73,  76,
		            79,  83,  87,  90,  94,  99, 103, 107,
		           112, 118, 123, 129, 134, 140, 147, 153 )
TI_5110_PITCH = (0,  15,  16,  17,  19,  21,  22,  25,
		26,  29,  32,  36,  40,  42,  46,  50,
		55,  60,  64,  68,  72,  76,  80,  84,
		86,  93, 101, 110, 120, 132, 144, 159 )
TI_5220_PITCH = (0,  15,  16,  17,  18,  19,  20,  21,
		22,  23,  24,  25,  26,  27,  28,  29,
		30,  31,  32,  33,  34,  35,  36,  37,
		38,  39,  40,  41,  42,  44,  46,  48,
		50,  52,  53,  56,  58,  60,  62,  65,
		68,  70,  72,  76,  78,  80,  84,  86,
		91,  94,  98, 101, 105, 109, 114, 118,
	       122, 127, 132, 137, 142, 148, 153, 159 )
TI_0280_PATENT_LPC = (
# K1
	( -501, -497, -493, -488, -480, -471, -460, -446,
          -427, -405, -378, -344, -305, -259, -206, -148,
           -86,  -21,   45,  110,  171,  227,  277,  320,
           357,  388,  413,  434,  451,  464,  474,  498 ),
# K2
        ( -349, -328, -305, -280, -252, -223, -192, -158,
          -124,  -88,  -51,  -14,   23,   60,   97,  133,
           167,  199,  230,  259,  286,  310,  333,  354,
           372,  389,  404,  417,  429,  439,  449,  506 ),
# K3
        ( -397, -365, -327, -282, -229, -170, -104,  -36,
            35,  104,  169,  228,  281,  326,  364,  396),
# K4
        ( -369, -334, -293, -245, -191, -131,  -67,   -1,
            64,  128,  188,  243,  291,  332,  367,  397 ),
# K5
        ( -319, -286, -250, -211, -168, -122,  -74,  -25,
            24,   73,  121,  167,  210,  249,  285,  318 ),
# K6
        ( -290, -252, -209, -163, -114,  -62,   -9,   44,
            97,  147,  194,  238,  278,  313,  344,  371 ),
# K7
        ( -291, -256, -216, -174, -128,  -80,  -31,   19,
            69,  117,  163,  206,  246,  283,  316,  345 ),
# K8
        ( -218, -133,  -38,   59,  152,  235,  305,  361 ),
# K9
        ( -226, -157,  -82,   -3,   76,  151,  220,  280 ),
# K10
        ( -179, -122,  -61,    1,   62,  123,  179,  231 ),
)
TI_5110_5220_LPC = (
# K1
        ( -501, -498, -497, -495, -493, -491, -488, -482,
          -478, -474, -469, -464, -459, -452, -445, -437,
          -412, -380, -339, -288, -227, -158,  -81,   -1,
            80,  157,  226,  287,  337,  379,  411,  436 ),
# K2
        ( -328, -303, -274, -244, -211, -175, -138,  -99,
           -59,  -18,   24,   64,  105,  143,  180,  215,
           248,  278,  306,  331,  354,  374,  392,  408,
           422,  435,  445,  455,  463,  470,  476,  506 ),
# K3
        ( -441, -387, -333, -279, -225, -171, -117,  -63,
            -9,   45,   98,  152,  206,  260,  314,  368 ),
# K4
        ( -328, -273, -217, -161, -106,  -50,    5,   61,
           116,  172,  228,  283,  339,  394,  450,  506 ),
# K5
        ( -328, -282, -235, -189, -142,  -96,  -50,   -3,
            43,   90,  136,  182,  229,  275,  322,  368 ),
# K6
        ( -256, -212, -168, -123,  -79,  -35,   10,   54,
            98,  143,  187,  232,  276,  320,  365,  409 ),
# K7
        ( -308, -260, -212, -164, -117,  -69,  -21,   27,
            75,  122,  170,  218,  266,  314,  361,  409 ),
# K8
        ( -256, -161,  -66,   29,  124,  219,  314,  409 ),
# K9
        ( -256, -176,  -96,  -15,   65,  146,  226,  307 ),
# K10
        ( -205, -132,  -59,   14,   87,  160,  234,  307 ),
)


find_closest_index = lambda source, value: source.index(sorted(source, key=lambda x: abs(x - value))[0])


VoicedFrame = namedtuple( 'VoicedFrame', ['energy', 'pitch', 'k1', 'k2', 'k3', 'k4', 'k5', 'k6', 'k7', 'k8', 'k9', 'k10'] )
UnvoicedFrame = namedtuple( 'UnvoicedFrame', ['energy', 'k1', 'k2', 'k3', 'k4'] )
RepeatedFrame = namedtuple( 'RepeatedFrame', ['energy', 'pitch'] )
SilentFrame = namedtuple( 'SilentFrame', [] )
StopFrame = namedtuple( 'StopFrame', [] )


# source: http://furrtek.free.fr/index.php?a=speakandspell&ss=6&i=2

class SpeakAndSpellROM( mrc.Block ):
    count_a = mrc.UInt8( 0x00 )
    count_b = mrc.UInt8( 0x01 )
    count_c = mrc.UInt8( 0x02 )
    count_d = mrc.UInt8( 0x03 )
    offset_a = mrc.Pointer( mrc.UInt16_LE( 0x04 ), mrc.EndOffset( 'common' ) )
    offset_b = mrc.Pointer( mrc.UInt16_LE( 0x06 ), mrc.EndOffset( 'list_a' ) )
    offset_c = mrc.Pointer( mrc.UInt16_LE( 0x08 ), mrc.EndOffset( 'list_b' ) )
    offset_d = mrc.Pointer( mrc.UInt16_LE( 0x0a ), mrc.EndOffset( 'list_c' ) )
    
    @property
    def common_len( self ):
        return (self.offset_a - 0x0c) // 2

    @common_len.setter
    def common_len( self, value ):
        self.offset_a = value * 2 + 0x0c 

    common = mrc.UInt16_LE( 0x0c, count=mrc.Ref( 'common_len' ) ) 
    list_a = mrc.UInt16_LE( mrc.Ref( 'offset_a' ), count=mrc.Ref( 'count_a' ) ) 
    list_b = mrc.UInt16_LE( mrc.Ref( 'offset_b' ), count=mrc.Ref( 'count_b' ) ) 
    list_c = mrc.UInt16_LE( mrc.Ref( 'offset_c' ), count=mrc.Ref( 'count_c' ) ) 
    list_d = mrc.UInt16_LE( mrc.Ref( 'offset_d' ), count=mrc.Ref( 'count_d' ) ) 

    raw_data = mrc.Bytes( mrc.EndOffset( 'list_d' ) )


def parse_tms5110_rom( buffer ):
    index_end = utils.from_uint16_le( buffer[0:2] )
    index = utils.from_uint16_le_array( buffer[0:index_end] )
    index2 = index + [len( buffer )]
    segments = [buffer[index2[i]:] for i in range( len( index ) ) ]
    streams = [TMS5110Stream.parse_stream( seg ) for seg in segments]
    return {
        'index': index,
        'segments': segments, 
        'streams': streams
    }


class TMSBase( object ):

    @classmethod
    def dump_stream( cls, frames ):
        writer = bits.BitStream( bytearray(), io_endian='big', bit_endian='little' )
        for frame in frames:
            if isinstance( frame, SilentFrame ):
                writer.write( 0b0000, cls.ENERGY_BITS )
            elif isinstance( frame, StopFrame ):
                writer.write( 0b1111, cls.ENERGY_BITS )
            elif isinstance( frame, RepeatedFrame ):
                writer.write( find_closest_index( cls.ENERGY_LUT[1:-1], frame.energy ) + 1, cls.ENERGY_BITS )
                writer.write( 1, cls.REPEAT_BITS )
                writer.write( find_closest_index( cls.PITCH_LUT, frame.pitch ), cls.PITCH_BITS )
            elif isinstance( frame, UnvoicedFrame ):
                writer.write( find_closest_index( cls.ENERGY_LUT[1:-1], frame.energy ) + 1, cls.ENERGY_BITS )
                writer.write( 0, cls.REPEAT_BITS )
                writer.write( 0, cls.PITCH_BITS )
                writer.write( find_closest_index( cls.K_LUT[0], frame.k1 ), cls.K_BITS[0] )
                writer.write( find_closest_index( cls.K_LUT[1], frame.k2 ), cls.K_BITS[1] )
                writer.write( find_closest_index( cls.K_LUT[2], frame.k3 ), cls.K_BITS[2] )
                writer.write( find_closest_index( cls.K_LUT[3], frame.k4 ), cls.K_BITS[3] )
            elif isinstance( frame, VoicedFrame ):
                writer.write( find_closest_index( cls.ENERGY_LUT[1:-1], frame.energy ) + 1, cls.ENERGY_BITS )
                writer.write( 0, cls.REPEAT_BITS )
                writer.write( find_closest_index( cls.PITCH_LUT[1:], frame.pitch ) + 1, cls.PITCH_BITS )
                writer.write( find_closest_index( cls.K_LUT[0], frame.k1 ), cls.K_BITS[0] )
                writer.write( find_closest_index( cls.K_LUT[1], frame.k2 ), cls.K_BITS[1] )
                writer.write( find_closest_index( cls.K_LUT[2], frame.k3 ), cls.K_BITS[2] )
                writer.write( find_closest_index( cls.K_LUT[3], frame.k4 ), cls.K_BITS[3] )
                writer.write( find_closest_index( cls.K_LUT[4], frame.k5 ), cls.K_BITS[4] )
                writer.write( find_closest_index( cls.K_LUT[5], frame.k6 ), cls.K_BITS[5] )
                writer.write( find_closest_index( cls.K_LUT[6], frame.k7 ), cls.K_BITS[6] )
                writer.write( find_closest_index( cls.K_LUT[7], frame.k8 ), cls.K_BITS[7] )
                writer.write( find_closest_index( cls.K_LUT[8], frame.k9 ), cls.K_BITS[8] )
                writer.write( find_closest_index( cls.K_LUT[9], frame.k10 ), cls.K_BITS[9] )

        return writer.get_buffer()

        

    @classmethod
    def parse_stream( cls, buffer ):

        frames = []
        reader = bits.BitStream( buffer, io_endian='big', bit_endian='little' )

        while not reader.tell() == (len( buffer ), 0):
            energy = reader.read( cls.ENERGY_BITS )
            if energy == 0b0000:
                frames.append( SilentFrame() )
                continue
            if energy == 0b1111:
                frames.append( StopFrame() )
                break
            repeat = reader.read( cls.REPEAT_BITS )
            pitch = reader.read( cls.PITCH_BITS )
            if repeat:
                frames.append( RepeatedFrame( energy=cls.ENERGY_LUT[energy], pitch=cls.PITCH_LUT[pitch] ) )
                continue
            k1 = reader.read( cls.K_BITS[0] )
            k2 = reader.read( cls.K_BITS[1] )
            k3 = reader.read( cls.K_BITS[2] )
            k4 = reader.read( cls.K_BITS[3] )
            if pitch == 0b000000:
                frames.append( UnvoicedFrame( 
                    energy=cls.ENERGY_LUT[energy],
                    k1=cls.K_LUT[0][k1],
                    k2=cls.K_LUT[1][k2],
                    k3=cls.K_LUT[2][k3],
                    k4=cls.K_LUT[3][k4]
                ) )
                continue

            k5 = reader.read( cls.K_BITS[4] )
            k6 = reader.read( cls.K_BITS[5] )
            k7 = reader.read( cls.K_BITS[6] )
            k8 = reader.read( cls.K_BITS[7] )
            k9 = reader.read( cls.K_BITS[8] )
            k10 = reader.read( cls.K_BITS[9] )
            #print(f'{energy:04b}, {repeat:01b}, {pitch:05b}, {k1:05b}, {k2:05b}, {k3:04b}, {k4:04b}, {k5:04b}, {k6:04b}, {k7:04b}, {k8:03b}, {k9:03b}, {k10:03b}')
            frames.append( VoicedFrame( 
                energy=cls.ENERGY_LUT[energy],
                pitch=cls.PITCH_LUT[pitch],
                k1=cls.K_LUT[0][k1],
                k2=cls.K_LUT[1][k2],
                k3=cls.K_LUT[2][k3],
                k4=cls.K_LUT[3][k4],
                k5=cls.K_LUT[4][k5],
                k6=cls.K_LUT[5][k6],
                k7=cls.K_LUT[6][k7],
                k8=cls.K_LUT[7][k8],
                k9=cls.K_LUT[8][k9],
                k10=cls.K_LUT[9][k10]
            ) )
        return {
            'frames': frames,
            'size': reader.tell()[0],
        }


class TMS0280Stream( TMSBase ):
    ENERGY_BITS = 4
    REPEAT_BITS = 1
    PITCH_BITS = 5
    K_BITS = [5, 5, 4, 4, 4, 4, 4, 3, 3, 3]
    ENERGY_LUT = TI_0280_PATENT_ENERGY
    PITCH_LUT = TI_0280_2801_PATENT_PITCH
    K_LUT = TI_0280_PATENT_LPC


class TMS5110Stream( TMSBase ):
    ENERGY_BITS = 4
    REPEAT_BITS = 1
    PITCH_BITS = 5
    K_BITS = [5, 5, 4, 4, 4, 4, 4, 3, 3, 3]
    ENERGY_LUT = TI_028X_LATER_ENERGY
    PITCH_LUT = TI_5110_PITCH
    K_LUT = TI_5110_5220_LPC


class TMS5220Stream( TMSBase ):
    ENERGY_BITS = 4
    REPEAT_BITS = 1
    PITCH_BITS = 6
    K_BITS = [5, 5, 4, 4, 4, 4, 4, 3, 3, 3]
    ENERGY_LUT = TI_028X_LATER_ENERGY
    PITCH_LUT = TI_5220_PITCH
    K_LUT = TI_5110_5220_LPC


