"""File format classes for the Tyrian engine (DOS, 1995).
"""

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar import utils

class SongPatch( mrc.Block ):
    mod_visc =          mrc.UInt8( 0x0000 )
    mod_vol =           mrc.UInt8( 0x0001 )
    mod_ad =            mrc.UInt8( 0x0002 )
    mod_sr =            mrc.UInt8( 0x0003 )
    mod_wave =          mrc.UInt8( 0x0004 )
    car_misc =          mrc.UInt8( 0x0005 )
    car_vol =           mrc.UInt8( 0x0006 )
    car_ad =            mrc.UInt8( 0x0007 )
    car_sr =            mrc.UInt8( 0x0008 )
    car_wave =          mrc.UInt8( 0x0009 )
    feedback =          mrc.UInt8( 0x000a )
    keyoff =            mrc.UInt8( 0x000b )
    portamento =        mrc.UInt8( 0x000c )
    glide =             mrc.UInt8( 0x000d )
    finetune =          mrc.UInt8( 0x000e )
    vibrato =           mrc.UInt8( 0x000f )
    vibdelay =          mrc.UInt8( 0x0010 )
    mod_trem =          mrc.UInt8( 0x0011 )
    car_trem =          mrc.UInt8( 0x0012 )
    tremwait =          mrc.UInt8( 0x0013 )
    arpeggio =          mrc.UInt8( 0x0014 )
    arp_tab =           mrc.UInt8( 0x0015, count=12 )
    start =             mrc.UInt16_LE( 0x0021 )
    size =              mrc.UInt16_LE( 0x0023 )
    fms =               mrc.UInt8( 0x0025 )
    transp =            mrc.UInt16_LE( 0x0026 )
    midinst =           mrc.UInt8( 0x0028 )
    midvelo =           mrc.UInt8( 0x0029 )
    midkey =            mrc.UInt8( 0x002a )
    midtrans =          mrc.UInt8( 0x002b )
    middum1 =           mrc.UInt8( 0x002c )
    middum2 =           mrc.UInt8( 0x002d )


class SongPositionChannel( mrc.Block ):
    pattern_num_raw =   mrc.UInt16_LE( 0x00 )
    transpose =         mrc.UInt8( 0x02 )

    @property
    def pattern_num( self ):
        return self.pattern_num_raw//2


class SongPosition( mrc.Block ):
    channels =           mrc.BlockField( SongPositionChannel, 0x00, count=9 )


class SongPattern( mrc.Block ):
    func =              mrc.UInt8( 0x00 )
    value =             mrc.UInt8( 0x01 )


class Song( mrc.Block ):
    mode =              mrc.UInt8( 0x0000 )
    speed =             mrc.UInt16_LE( 0x0001 )
    tempo =             mrc.UInt8( 0x0003 )
    pattlen =           mrc.UInt8( 0x0004 )
    chandelay =         mrc.UInt8( 0x0005, count=9 )
    regbd =             mrc.UInt8( 0x000e )

    patch_count =       mrc.UInt16_LE( 0x000f )
    patches =           mrc.BlockField( SongPatch, 0x0011, count=mrc.Ref( 'patch_count' ) )

    position_count =    mrc.UInt16_LE( mrc.EndOffset( 'patches' ) )
    positions =         mrc.BlockField( SongPosition, mrc.EndOffset( 'position_count' ), count=mrc.Ref( 'position_count' ) )

    num_digital =       mrc.UInt16_LE( mrc.EndOffset( 'positions' ) )
    patterns =          mrc.BlockField( SongPattern, mrc.EndOffset( 'num_digital' ), stream=True )


class MUSFile( mrc.Block ):
    song_count =    mrc.UInt16_LE( 0x00 )
    song_offsets =  mrc.UInt32_LE( 0x02, count=mrc.Ref( 'song_count' ) )

    songs_raw =     mrc.Bytes( mrc.EndOffset( 'song_offsets' ) )
    

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.songs = mrc.LinearStore( parent=self, 
                                     source=mrc.Ref( 'songs_raw' ), 
                                     block_klass=Song,
                                     offsets=mrc.Ref( 'song_offsets' ),
                                     base_offset=mrc.EndOffset( 'song_offsets', neg=True ) )

