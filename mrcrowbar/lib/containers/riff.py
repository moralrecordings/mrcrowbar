from mrcrowbar import models as mrc

class RIFF( mrc.Block ):
    CHUNK_MAP = {}

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'RIFF' )
    size = mrc.UInt32_LE( 0x04 )
    form_type = mrc.Bytes( 0x08, length=4 )
    stream = mrc.ChunkStream( 0x0c, chunk_map=mrc.Ref( 'CHUNK_MAP' ), 
                             length=mrc.Ref( 'size' ), chunk_id_size=4, 
                             length_field=mrc.UInt32_LE, alignment=2, 
                             default_chunk=mrc.Unknown )

class RIFX( mrc.Block ):
    CHUNK_MAP = {}

    magic = mrc.Const( mrc.Bytes( 0x00, length=4 ), b'RIFX' )
    size = mrc.UInt32_BE( 0x04 )
    form_type = mrc.Bytes( 0x08, length=4 )
    stream = mrc.ChunkStream( 0x0c, chunk_map=mrc.Ref( 'CHUNK_MAP' ), 
                             length=mrc.Ref( 'size' ), chunk_id_size=4, 
                             length_field=mrc.UInt32_BE, alignment=2, 
                             default_chunk=mrc.Unknown )


