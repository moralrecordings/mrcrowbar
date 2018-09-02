from mrcrowbar import models as mrc

class MacBinary( mrc.Block ):
    version_old =   mrc.Const( mrc.UInt8( 0x00 ), 0 )
    name_size =     mrc.UInt8( 0x01, range=range( 1, 64 ) )
    name =          mrc.Bytes( 0x02, length=mrc.Ref( 'name_size' ) )
    type =          mrc.Bytes( 0x41, length=4 )
    creator =       mrc.Bytes( 0x45, length=4 )
    locked =        mrc.Bits( 0x49, 0b10000000 )
    invisible =     mrc.Bits( 0x49, 0b01000000 )
    bundle =        mrc.Bits( 0x49, 0b00100000 )
    system =        mrc.Bits( 0x49, 0b00010000 )
    bozo =          mrc.Bits( 0x49, 0b00001000 )
    busy =          mrc.Bits( 0x49, 0b00000100 )
    changed =       mrc.Bits( 0x49, 0b00000010 )
    inited =        mrc.Bits( 0x49, 0b00000001 )
    const1 =        mrc.Const( mrc.UInt8( 0x4a ), 0 )
    pos_y =         mrc.UInt16_BE( 0x4b )
    pos_x =         mrc.UInt16_BE( 0x4d )
    folder_id =     mrc.UInt16_BE( 0x4f )
    protected =     mrc.Bits( 0x51, 0b00000001 )
    const2 =        mrc.Const( mrc.UInt8( 0x52 ), 0 )
    data_size =     mrc.UInt32_BE( 0x53 )
    resource_size = mrc.UInt32_BE( 0x57 )
    created =       mrc.UInt32_BE( 0x5a )
    modified =      mrc.UInt32_BE( 0x5e )


    data =          mrc.Bytes( 0x80, length=mrc.Ref( 'data_size' ) )
    resource =      mrc.Bytes( mrc.EndOffset( 'data', align=0x80 ), length=mrc.Ref( 'resource_size' ) )


