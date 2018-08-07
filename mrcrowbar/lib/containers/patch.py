"""File format classes for binary patches.

Sources:
IPS
https://zerosoft.zophar.net/ips.php

UPS
http://individual.utoronto.ca/dmeunier/ups-spec.pdf
"""

from mrcrowbar import models as mrc
from mrcrowbar import utils



class IPSRecord( mrc.Block ):
    offset_maj = mrc.UInt8( 0x00 )
    offset_min = mrc.UInt16_BE( 0x01 )
    size =       mrc.UInt16_BE( 0x03 )
    data =       mrc.Bytes( 0x05, length=mrc.Ref( 'size' ) )

    @property
    def offset( self ):
        return (self.offset_maj << 16) + self.offset_min

    @offset.setter
    def offset( self, value ):
        self.offset_maj = (value & 0xff0000) >> 16
        self.offset_min = value & 0x00ffff

    @property
    def repr( self ):
        return 'offset: 0x{:06x}, size: 0x{:04x}'.format( self.offset, self.size )


class IPS( mrc.Block ):
    magic =     mrc.Const( mrc.Bytes( 0x00, length=5 ), b'PATCH' )
    records =   mrc.BlockField( IPSRecord, 0x05, stream=True, stream_end=b'EOF' )

    @property
    def repr( self ):
        return 'records: {}'.format( len( self.records ) )

    def create( self, source, target ):
        pass

    def patch( self, source ):
        return source


class UIntVLV( mrc.Field ):
    def __init__( self, offset, default=0, **kwargs ):
        super().__init__( default=default, **kwargs )
        self.offset = offset
        
    def get_from_buffer( self, buffer, parent=None ):
        assert utils.is_bytes( buffer )
        offset = mrc.property_get( self.offset, parent )
        pointer = offset
        total = 0
        shift = 0
        while pointer < len( buffer ):
            test = buffer[pointer]
            pointer += 1 
            total += (test & 0x7f) << shift
            shift += 7
            if test & 0x80:
                break
            total += 1 << shift
        return total

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super().update_buffer_with_value( value, buffer, parent )
        offset = mrc.property_get( self.offset, parent )
        length = self.get_size( value, parent )
        remainder = value
        if len( buffer ) < offset+length:
            buffer.extend( b'\x00'*(offset+length-len( buffer )) )
        for i in range( length ):
            buffer[offset+i] = remainder & 0x7f
            remainder >>= 7
            if remainder == 0:
                buffer[offset+i] |= 0x80
                break
            remainder -= 1
        return

    def get_start_offset( self, value, parent=None, index=None ):
        assert index is None
        offset = mrc.property_get( self.offset, parent )
        return offset

    def get_size( self, value, parent=None, index=None ):
        assert index is None
        test = value
        count = 1
        test >>= 7
        while test > 0:
            count += 1
            test >>= 7
            if test == 0:
                break
            test -= 1
        return count

    def validate( self, value, parent=None ):
        if (type( value ) != int):
            raise mrc.FieldValidationError( 'Expecting type {}, not {}'.format( self.format_type, type( value[i] ) ) )
        if value < 0:
            raise mrc.FieldValidationError( 'Value must be unsigned' )
        return


class XORData( mrc.Bytes ):
    def __init__( self, offset, *args, **kwargs ):
        super().__init__( offset, stream_end=b'\x00', *args, **kwargs )

    def validate( self, value, parent=None ):
        super().validate( value, parent )
        if value.find( b'\x00' ) != -1:
            raise mrc.FieldValidationError( 'XOR data can\'t contain a null character' )
        return


class UPSBlock( mrc.Block ):
    rel_offset =    UIntVLV( 0x00 )
    xor_data =      XORData( mrc.EndOffset( 'rel_offset' ) )

    @property
    def repr( self ):
        return 'rel_offset: 0x{:x}, size: {}'.format( self.rel_offset, len( self.xor_data ) )

class UPS( mrc.Block ):
    STOP_CHECK =    lambda buffer, pointer: pointer >= len( buffer )-12

    magic =         mrc.Const( mrc.Bytes( 0x00, length=4 ), b'UPS1' )
    input_size =    UIntVLV( 0x04 )
    output_size =   UIntVLV( mrc.EndOffset( 'input_size' ) )
    blocks =        mrc.BlockField( UPSBlock, mrc.EndOffset( 'output_size' ), stream=True, stop_check=STOP_CHECK )
    input_crc32 =   mrc.UInt32_LE( mrc.EndOffset( 'blocks' ) )
    output_crc32 =  mrc.UInt32_LE( mrc.EndOffset( 'input_crc32' ) )
    patch_crc32 =   mrc.UInt32_LE( mrc.EndOffset( 'output_crc32' ) )


