import itertools 

_next_position_hint = itertools.count()


class FieldValidationError( Exception ):
    pass


class Field:
    def __init__( self, default=None, **kwargs ):
        self._position_hint = next( _next_position_hint )
        self.default = default

    def validate( self, value ):
        pass 


class BlockStream( Field ):
    def __init__( self, block_klass, offset, stride, count, fill=b'\x00', **kwargs ):
        super( BlockStream, self ).__init__( **kwargs )
        self.block_klass = block_klass
        self.offset = offset
        self.stride = stride
        self.fill = fill


class BlockField( Field ):
    def __init__( self, block_klass, offset, fill=b'\x00', **kwargs ):
        super( BlockField, self ).__init__( **kwargs )
        self.block_klass = block_klass
        self.offset = offset
        self.fill = fill

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        if self.block:
            return self.block.export_data()
        else:
            return (self.fill*int( 1+self.block_klass._block_size/len(self.fill) ))[:self.block_klass._block_size]


class Bytes( Field ):
    def __init__( self, offset, length, default=None, **kwargs ):
        if default is not None:
            assert type( default ) == bytes
            assert len( default ) == length
        else:
            default = b'\x00'*length
        super( Bytes, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        return buffer[self.offset:self.offset+self.length]

    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (len( value ) != self.length):
            raise FieldValidationError( 'Expecting length of {}, not {}'.format( self.length, len( value ) ) )
        return


class CString( Field ):
    def __init__( self, offset, default=b'', **kwargs ):
        assert type( default ) == bytes
        super( CString, self ).__init__( default=default, **kwargs )
        self.offset = offset

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        return buffer.split( b'\x00', 1, **kwargs )[0]

    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        return 

class CStringN( Field ):
    def __init__( self, offset, length, default=b'', **kwargs ):
        assert type( default ) == bytes
        super( CStringN, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        return buffer[self.offset:self.offset+self.length].split( b'\x00', 1, **kwargs )[0]

    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (len( value ) > self.length):
            raise FieldValidationError( 'Expecting length <= {}, not {}'.format( self.length, len( value ) ) )
        return
    

class ValueField( Field ):
    def __init__( self, offset, format, size, format_type, format_range, default=0, bitmask=None, range=None, **kwargs ):
        super( ValueField, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.format = format
        self.format_type = format_type
        self.format_range = format_range
        if bitmask:
            assert type( bitmask ) == bytes
            assert len( bitmask ) == size
        self.size = size
        self.bitmask = bitmask
        self.range = range

    def _get_bytes( self, buffer ):
        data = buffer[self.offset:self.offset+self.size]
        assert len( data ) == self.size
        if self.bitmask:
            return (int.from_bytes( data, byteorder='big' ) & 
                    int.from_bytes( self.bitmask, byteorder='big' )
                    ).to_bytes( self.size, byteorder='big' )
        else:
            return data

    def get_from_buffer( self, buffer ):
        assert type( buffer ) == bytes
        value = struct.unpack( self.format, self._get_bytes( buffer ) )[0]
        if self.range:
            assert value in self.range
        return value

    def validate( self, value ):
        if (type( value ) != self.format_type):
            raise FieldValidationError( 'Expecting type {}, not {}'.format( self.format_type, type( value ) ) )
        if self.format_range and (value not in self.format_range):
            raise FieldValidationError( 'Value {} not in format range ({})'.format( value, self.format_range ) )
        if self.range and (value not in self.range):
            raise FieldValidationError( 'Value {} not in range ({})'.format( value, self.range ) )
        return


class Int8( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<b', 1, int, range(-1<<7, 1<<7), **kwargs )


class UInt8( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>B', 1, int, range( 0, 1<<8 ), **kwargs )


class Bits( UInt8 ):
    def __init__( self, offset, bits, default=0, **kwargs ):
        UInt8.__init__( self, offset, default=default, **kwargs )
        assert type( bits ) == int
        mask_bits = bin( bits ).split('b', 1)[1]
        self.bits = [(1<<i) for i, x in enumerate( reversed( mask_bits ) ) if x == '1']
        self.format_range = range( 0, 1<<len(self.bits) )

    def get_from_buffer( self, buffer ):
        result = UInt8.get_from_buffer( self, buffer )
        value = 0
        for i, x in enumerate( self.bits ):
            value += (1 << i) if (result & x) else 0
        return value


class UInt16_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<H', 2, int, range( 0, 1<<16 ), **kwargs )


class UInt32_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<I', 4, int, range( 0, 1<<32 ), **kwargs )


class UInt64_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<Q', 8, int, range( 0, 1<<64 ), **kwargs )


class Int16_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<h', 2, int, range( -1<<15, 1<<15 ), **kwargs )


class Int32_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<i', 4, int, range( -1<<31, 1<<31 ), **kwargs )


class Int64_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<q', 8, int, range( -1<<63, 1<<63 ), **kwargs )


class Float_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<f', 4, float, None, **kwargs )


class Double_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<d', 8, float, None, **kwargs )


class UInt16_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>H', 2, int, range( 0, 1<<16 ), **kwargs )


class UInt32_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>I', 4, int, range( 0, 1<<32 ), **kwargs )


class UInt64_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>Q', 8, int, range( 0, 1<<64 ), **kwargs )


class Int16_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>h', 2, int, range( -1<<15, 1<<15 ), **kwargs )


class Int32_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>i', 4, int, range( -1<<31, 1<<31 ), **kwargs )


class Int64_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>q', 8, int, range( -1<<63, 1<<63 ), **kwargs )


class Float_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>f', 4, float, None,  **kwargs )


class Double_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>d', 8, float, None,  **kwargs )


