"""File format classes for the games Jill of the Jungle (DOS, 1992) and 
Xargon (DOS, 1994)."""

import itertools

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.images import base as img
from mrcrowbar import utils


class SoundRef( mrc.Block ):
    offset = mrc.UInt32_LE( 0x00 )
    length = mrc.UInt16_LE( 0x04 )
    playback_freq = mrc.UInt16_LE( 0x06 )


class TextRef( mrc.Block ):
    offset = mrc.UInt32_LE( 0x00 )
    length = mrc.UInt16_LE( 0x04 )


class VCL( mrc.Block ):

    pass


class JillLoader( mrc.Loader ):
    """Loader for the game Jill of the Jungle (DOS, 1992)."""
    _SEP = mrc.Loader._SEP

    _JILL_FILE_CLASS_MAP = {
        _SEP+'JN[1-3]SAVE.[0-9]$': None,
        _SEP+'JILL[1-3].VCL$': None,
    }

    def __init__( self ):
        super( JillLoader, self ).__init__( self._JILL_FILE_CLASS_MAP )

