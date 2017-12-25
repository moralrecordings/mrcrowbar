"""File format classes for the Tyrian engine (DOS, 1995).
"""

from mrcrowbar import models as mrc
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar import utils

class Patch( mrc.Block ):
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


class Song( mrc.Block ):
    mode =              mrc.UInt8( 0x0000 )
    speed =             mrc.UInt16_LE( 0x0001 )
    tempo =             mrc.UInt8( 0x0003 )
    pattlen =           mrc.UInt8( 0x0004 )
    chandelay =         mrc.UInt8( 0x0005, count=9 )
    regbd =             mrc.UInt8( 0x000e )
    patch_count =       mrc.UInt16_LE( 0x000f )

    patches =           mrc.BlockField( Patch, 0x0011, count=mrc.Ref( 'patch_count' ) )
    
    #data =      Bytes( 0x0000 )


class MUSFile( mrc.Block ):
    song_count =    mrc.UInt16_LE( 0x00 )
    song_offsets =  mrc.UInt32_LE( 0x02, count=mrc.Ref( 'song_count' ) )

    songs_raw =     mrc.Bytes( mrc.Ref( 'song_data_offset' ) )
    
    @property
    def song_data_offset( self ):
        return self.get_field_end_offset( 'song_offsets' )

    @property
    def song_data_neg_offset( self ):
        return -self.get_field_end_offset( 'song_offsets' )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.songs = mrc.LinearStore( parent=self, 
                                     source=mrc.Ref( 'songs_raw' ), 
                                     block_klass=Song,
                                     offsets=mrc.Ref( 'song_offsets' ),
                                     base_offset=mrc.Ref( 'song_data_neg_offset' ) )

