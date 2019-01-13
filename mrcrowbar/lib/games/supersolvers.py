from mrcrowbar import models as mrc
from mrcrowbar import utils

class AECompressor( mrc.Transform ):
    def import_data( self, buffer ):
        unk1 = buffer[0]
        flags = buffer[1]
        
        rle_c = RLECompressor()
        dict_c = DictCompressor()

        pointer = 2
        if (flags & 2 != 0) and (flags & 1 != 0):
            pass1 = dict_c.import_data( buffer[2:] )
            pass2 = rle_c.import_data( pass1.payload )
            return mrc.TransformResult( payload=pass2.payload, end_offset=pass1.end_offset+2 )
        elif (flags & 2 != 0) and (flags & 1 == 0):
            pass1 = dict_c.import_data( buffer[2:] )
            return mrc.TransformResult( payload=pass1.payload, end_offset=pass1.end_offset+2 )
        elif (flags & 2 == 0) and (flags & 1 != 0):
            pass1 = rle_c.import_data( buffer[2:] )
            return mrc.TransformResult( payload=pass1.payload, end_offset=pass1.end_offset+2 )
        # no compression
        return mrc.TransformResult( payload=buffer[2:], end_offset=len( buffer ) )


class RLECompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):
        pointer = 0

        dest = bytearray()

        while pointer < len( buffer ):
            test = utils.from_int8( buffer[pointer:pointer+1] )
            pointer += 1
            if test > 0:
                dest.extend( buffer[pointer:pointer+test] )
                pointer += test
            else:
                count = 1-test
                al = buffer[pointer]
                pointer += 1
                for i in range( count ):
                    dest.append( al )

        return mrc.TransformResult( payload=bytes( dest ), end_offset=len( buffer ) )


class DictCompressor( mrc.Transform ):
    def import_data( self, buffer, parent=None ):

        src = bytearray( buffer )
        dest = bytearray()
        lookup_pointer = 0
        bit_size = 9

        bitstore = utils.BitReader( src, start_offset=2, bits_reverse=True, output_reverse=True )
        eof = False

        loop = 0
        while True:
            if loop % 2 == 0:
                src[lookup_pointer:lookup_pointer+2] = utils.to_uint16_le( len( dest ) )
                lookup_pointer += 2

            while True:
                test = 0

                try:
                    test = bitstore.get_bits( bit_size )
                except IndexError:
                    eof = True 
                    break

                if test != 0x100:
                    break
                bit_size += 1


            if eof:
                break

            if test <= 0xff:
                dest.append( test & 0xff )
            else:
                index = (test - 0x101) << 1
                if index > len( src ):
                    print( 'Out of bounds! 0x{:04x}'.format(index) )
                    break
                start = utils.from_uint16_le( src[index:index+2] )
                end = utils.from_uint16_le( src[index+2:index+4] )
                dest.extend( dest[start:end] )

            loop += 1


        return mrc.TransformResult( payload=bytes( dest ), end_offset=len( buffer ) )




def offset_stream_end( buffer, offset ):
    return offset >= utils.from_uint32_le( buffer[0:4] )


class AEDAT( mrc.Block ):
    offsets = mrc.UInt32_LE( 0x00, stream=True, stop_check=offset_stream_end )
    
    raw_data = mrc.Bytes()

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.data = mrc.LinearStore( self, source=mrc.Ref( 'raw_data' ), 
                                       offsets=mrc.Ref( 'offsets' ), 
                                       base_offset=mrc.EndOffset( 'offsets', neg=True ),
                                       block_klass=mrc.Unknown )
