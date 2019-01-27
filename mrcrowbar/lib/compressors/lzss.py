from mrcrowbar import models as mrc


# source: http://dev.gameres.com/Program/Other/LZSS.C
class LZSSCompressor( mrc.Transform ):
    N = 4096
    F = 18
    THRESHOLD = 2
    
    def import_data( self, buffer, parent=None ):
        r = self.N - self.F
        flags = 0
        text_buf = bytearray( b' '*(self.N+self.F-1) );
        result = bytearray()
        index = 0

        while index < len( buffer ):
            flags >>= 1
            if (flags & 0x100) == 0:
                flags = buffer[index] | 0xff00;
                index += 1
            if (flags & 1):
                c = buffer[index]
                index += 1
                result.append( c )
                text_buf[r] = c
                r = (r+1) & (self.N-1)
            else:
                i = buffer[index]
                j = buffer[index+1]
                index += 2
                i |= (j & 0xf0) << 4
                j = (j & 0x0f) + self.THRESHOLD
                for k in range( j+1 ):
                    c = text_buf[(i+k) & (self.N-1)]
                    result.append( c )
                    text_buf[r] = c
                    r = (r+1) & (self.N-1)
                    
        return mrc.TransformResult( payload=bytes( result ), end_offset=len( buffer ) )
