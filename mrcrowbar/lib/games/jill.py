"""File format classes for the games Jill of the Jungle (DOS, 1992) and 
Xargon (DOS, 1994)."""

import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.images import base as img
from mrcrowbar.lib.audio import base as aud
from mrcrowbar import utils


# source: Xargon source code release - https://www.classicdosgames.com/game/Xargon.html

PC_SPEAKER_NOTE_TABLE = [
    64   ,67   ,71   ,76   ,80   ,85   ,90   ,95   ,101  ,107  ,114  ,121   ,0    ,0    ,0    ,0,
    128  ,135  ,143  ,152  ,161  ,170  ,181  ,191  ,203  ,215  ,228  ,242   ,0    ,0    ,0    ,0,
    256  ,271  ,287  ,304  ,322  ,341  ,362  ,383  ,406  ,430  ,456  ,483   ,0    ,0    ,0    ,0,
    512  ,542  ,574  ,608  ,645  ,683  ,724  ,767  ,812  ,861  ,912  ,967   ,0    ,0    ,0    ,0,
    1024 ,1084 ,1149 ,1217 ,1290 ,1366 ,1448 ,1534 ,1625 ,1722 ,1825 ,1933  ,0    ,0    ,0    ,0,
    2048 ,2169 ,2298 ,2435 ,2580 ,2733 ,2896 ,3068 ,3250 ,3444 ,3649 ,3866  ,0    ,0    ,0    ,0,
    4096 ,4339 ,4597 ,4870 ,5160 ,5467 ,5792 ,6137 ,6501 ,6888 ,7298 ,7732  ,0    ,0    ,0    ,0,
    8192 ,8679 ,9195 ,9741 ,10321,10935,11585,12274,13003,13777,14596,15646 ,0    ,0    ,0    ,0,
    16384,17358,18390,19483,20642,21870,23170,24548,26007,27554,29192,30928 ,0    ,0    ,0    ,0
]


class Sound( mrc.Block ):
    sample_rate = 6000
    raw_data = mrc.Bytes( 0x00 )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.wave = aud.Wave( self, mrc.Ref( 'raw_data' ), channels=1,
                              sample_rate=mrc.Ref( 'sample_rate' ), format_type=int,
                              field_size=1, signedness='unsigned', endian=None )


class VCLFile( mrc.Block ):

    sound_offsets   = mrc.UInt32_LE( 0x00, count=50 )
    sound_sizes     = mrc.UInt16_LE( 0xc8, count=50 )
    sound_freqs     = mrc.UInt16_LE( 0x12c, count=50 )
    text_offsets    = mrc.UInt32_LE( 0x190, count=40 )
    text_lengths    = mrc.UInt16_LE( 0x230, count=40 )
    raw_data        = mrc.Bytes( 0x280 )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.sounds = mrc.LinearStore( self, mrc.Ref( 'raw_data' ), Sound,
                                       offsets=mrc.Ref( 'sound_offsets' ),
                                       sizes=mrc.Ref( 'sound_sizes' ),
                                       base_offset=-0x280 )


# source: http://www.shikadi.net/moddingwiki/SHA_Format

class Tileset( mrc.Block ):
    num_shapes      = mrc.UInt8( 0x00 )
    num_rots        = mrc.UInt16_LE( 0x01 )
    len_cga         = mrc.UInt16_LE( 0x03 )
    len_ega         = mrc.UInt16_LE( 0x05 )
    len_vga         = mrc.UInt16_LE( 0x07 )
    colour_depth    = mrc.UInt8( 0x09 )
    flags           = mrc.UInt16_LE( 0x0a )

    



class SHAFile( mrc.Block ):
    tileset_offsets = mrc.UInt32_LE( 0x0000, count=128 )
    tileset_sizes   = mrc.UInt16_LE( 0x0200, count=128 )
    tileset_data    = mrc.Bytes( 0x0300 )
    tilesets        = mrc.StoreRef( Tileset, mrc.Ref( 'store' ), mrc.Ref( 'tileset_offsets' ), mrc.Ref( 'tileset_sizes' ), count=128 )

    def __init__( self, *args, **kwargs ):
        self.store = mrc.Store( self, mrc.Ref( 'tileset_data' ) )
        super().__init__( *args, **kwargs )


class JillLoader( mrc.Loader ):
    """Loader for the game Jill of the Jungle (DOS, 1992)."""
    _SEP = mrc.Loader._SEP

    _JILL_FILE_CLASS_MAP = {
        _SEP+'JN([1-3])(SAVE)\.([0-9])$': None,
        _SEP+'(JILL)([1-3])\.(VCL)$': VCLFile,
        _SEP+'(JILL)([1-3])\.(SHA)$': SHAFile,
        _SEP+'(JILL)\.(DMA)$': None,
        _SEP+'(.*)\.(DDT)$': None,
        _SEP+'(.*)\.JN([1-3])$': None
    }

    def __init__( self ):
        super().__init__( self._JILL_FILE_CLASS_MAP )


class XargonLoader( mrc.Loader ):
    """Loader for the game Xargon (DOS, 1994)."""
    _SEP = mrc.Loader._SEP

    _XARGON_FILE_CLASS_MAP = {
        _SEP+'(AUDIO).XR([1-3])$': VCLFile,
        _SEP+'(BOARD)_([0-9A-Z]+).XR([1-3])$': None,
        _SEP+'(DEMO)([1-3]).XR([1-3])$': None,
        _SEP+'(GRAPHICS).XR([1-3])$': SHAFile,
        _SEP+'(INTRO).XR([1-3])$': None,
        _SEP+'(MAP).XR([1-3])$': None,
        _SEP+'(SONG)_([0-9]+).XR([1-3])$': None,
        _SEP+'(STORY).XR([1-3])$': None,
        _SEP+'(TILES).XR([1-3])$': None,
    }

    def __init__( self ):
        super().__init__( self._XARGON_FILE_CLASS_MAP )

