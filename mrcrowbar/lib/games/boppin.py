#!/usr/bin/python3

import array
import itertools
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.images import base as img
from mrcrowbar.lib.compressors import lzss
from mrcrowbar import utils

# source: http://www.shikadi.net/moddingwiki/RES_Format_%28Boppin%29

BOPPIN_RES_FILENAMES = [
    'BOPPIN.CFG',
    'CANDY.IMG',
    'CANDY.TXB',
    'BOPPIN.SND',
    'BOPPIN.MUS',
    'SCORE.CFG',
    'WALLS.RES',
    'FLOORS.RES',
    'ELEVATOR.TIL',
    'SOURCE.TIL',
    'BOPPING.TIL',
    'BCKGND.TIL',
    'PRIZE.TIL',
    'MONSTER.TIL',
    'MISC.TIL',
    'CHAR.TIL',
    'UNKNOWN1',
    'UNKNOWN2',
    'UNKNOWN3',
    'UNKNOWN4',
    'BOPPIN1.LVL',
    'BOPPIN2.LVL',
    'BOPPIN3.LVL',
    'BOPPIN4.LVL',
    'ENDSCRN.BIN',
    'UNKNOWN5',
    'UNKNOWN6'
]

BOPPIN_MUS_FILENAMES = [
    'BOPBOP2.MID', 
    'MAGNETIC.MID', 
    'FRUSTRAT.MID', 
    'SAPPHIRE.MID', 
    'OPUS43.MID', 
    'FOUNDAT.MID', 
    'FELTIBUN.MID', 
    'STUMBUM.MID', 
    'STARBOP.MID', 
    'BUMBLE.MID', 
    'SKEPTICA.MID', 
    'STABHAPP.MID', 
    'STREETS.MID', 
    'DIXIE.MID', 
    'LOBERO.MID', 
    'APOGEE.MID'
]

BOPPIN_SND_FILENAMES = [
    'ADDCRED.VOC', 
    'ADDLIFE.VOC', 
    'BLKBNC1.VOC', 
    'BLKBNC2.VOC', 
    'BLKDRP.VOC', 
    'BLOCKPSH.VOC', 
    'BLOCKREZ.VOC', 
    'BODYTHUD.VOC', 
    'BOIKREZ1.VOC', 
    'BOIKREZ2.VOC', 
    'BOIKREZ3.VOC', 
    'BOIKSUI1.VOC', 
    'BOIKSUI2.VOC', 
    'YEETREZ1.VOC', 
    'YEETREZ3.VOC', 
    'YEETSUI1.VOC', 
    'YEETSU1A.VOC', 
    'YEETSUI2.VOC', 
    'BONUSTIM.VOC', 
    'BONUSTLY.VOC', 
    'BOPHIT.VOC', 
    'CRYING.VOC', 
    'DUCKING.VOC', 
    'ELEVATOR.VOC', 
    'EXPLOSN.VOC', 
    'FOOTTAP.VOC', 
    'JUMPJOY.VOC', 
    'LOGO.VOC', 
    'LOGO2.VOC', 
    'LOGO3.VOC', 
    'PING.VOC', 
    'PRIZDROP.VOC', 
    'PRIZE.VOC', 
    'PRIZELOS.VOC', 
    'PTRNFLSH.VOC', 
    'PTRNHIT.VOC', 
    'REFRACTR.VOC', 
    'WALKING.VOC', 
    'NOTEMAN.VOC', 
    'ECHOTINK.VOC', 
    'BEEFBRAS.VOC', 
    'CLEANBAS.VOC', 
    'DEEPBASS.VOC', 
    'FLICKBAS.VOC', 
    'JAHRMARK.VOC', 
    'LICKS.VOC', 
    'MARIMBA.VOC', 
    'NIGHTMAR.VOC', 
    'PIANO.VOC', 
    'SHAKER.VOC', 
    'SOFTTP12.VOC', 
    'STRINGS1.VOC', 
    'SYNBUZ.VOC', 
    'UNKNOWN.VOC', 
    'UNKNOWN2.VOC'
]


class BoppinCompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        if len( buffer ) == 0:
            return mrc.TransformResult()

        lc = lzss.LZSSCompressor()
        size_comp = utils.from_uint32_le( buffer[0:4] )

        if size_comp != len( buffer ):
            logger.info( '{}: File not compressed'.format( self ) )
            return mrc.TransformResult( payload=buffer, end_offset=len( buffer ) )

        size_raw = utils.from_uint32_le( buffer[4:8] )
        result = lc.import_data( buffer[8:] )
        if len( result.payload ) != size_raw:
            logger.warning( '{}: Was expecting a decompressed size of {}, got {}!'.format( self, size_raw, len( result.payload ) ) )

        return result

    def export_data( self, buffer, parent=None ):
        # no header, no compression!
        return mrc.TransformResult( payload=buffer )



# levels can pick:
# - 6 banks of 16x tiles
# - 2 banks of 6x bopping blocks 
# - 2 banks of 2x source blocks 
# - 2 banks of 4x wall tiles
# - 2 banks of 7x floor tiles
# - 2 banks of 2x elevator tiles
# 
# each bg bank has its own palette? might be common 256col palette for whole game
# prize bank is common, has 128 items
# each prize item has its own 16 colour palette
# colours 24-27 and 28-30 are strobing palette


class Colour( img.Colour ):
    r_8 =           mrc.UInt8( 0x00 )
    unknown_1 =     mrc.UInt8( 0x01 )
    g_8 =           mrc.UInt8( 0x02 )
    unknown_2 =     mrc.UInt8( 0x03 )
    b_8 =           mrc.UInt8( 0x04 )
    unknown_3 =     mrc.UInt8( 0x05 )


class FileLookup( mrc.Block ):
    offset =        mrc.UInt32_LE( 0x00 )
    size =          mrc.UInt32_LE( 0x04 )

    file = mrc.StoreRef( mrc.Unknown, store=mrc.Ref( '_parent.files_store' ), offset=mrc.Ref( 'offset' ), size=mrc.Ref( 'size' ), transform=BoppinCompressor() )


# stop looking for more lookup-table entries once we hit the first result that references the end of the file
def resource_stop_check( buffer, offset ):
    # we want to look at the previous entry to the current one, ignore if we're at the first entry
    if (offset < 8):
        return False
    # too near the end of the file? that's a paddling
    if (offset >= len( buffer )-8):
        return True

    block_offset = utils.from_uint32_le( buffer[offset-8:offset-4] )
    block_size = utils.from_uint32_le( buffer[offset-4:offset] )

    # ignore filler entries
    if (block_offset == 0xffffffff) and (block_size == 0):
        return False
    
    # check for references to the end of the file
    return block_offset+block_size >= len( buffer )-1



class Resource( mrc.Block ):
    files =  mrc.BlockField( FileLookup, 0x00, stride=0x08, stream=True, stop_check=resource_stop_check, fill=b'\xff\xff\xff\xff\x00\x00\x00\x00' )
    files_raw = mrc.Bytes( mrc.EndOffset( 'files' ) )
    
    def __init__( self, *args, **kwargs ):
        self.files_store = mrc.Store( parent=self, source=mrc.Ref( 'files_raw' ), base_offset=mrc.EndOffset( 'files', neg=True ) )
        super().__init__( *args, **kwargs )





class Loader( mrc.Loader ):
    _SEP = mrc.Loader._SEP

    _BOPPIN_FILE_CLASS_MAP = {
        _SEP+'(BOPPIN)(\d).(LVL)$': None,
        _SEP+'(BOPPIN).(RES)$': Resource,
    }

    def __init__( self ):
        super().__init__( self._BOPPIN_FILE_CLASS_MAP )
