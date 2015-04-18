import itertools 

_next_position_hint = itertools.count()

class Field:
    def __init__( self ):
        self._position_hint = next(_next_position_hint)


class Bytes( Field ):
    def __init__( self, offset, length ):
        super( Bytes, self ).__init__()
        self.offset = offset
        self.length = length

    def get( self, buffer ):
        assert type( buffer ) == bytes
        return buffer[self.offset:self.offset+self.length]


class CString( Field ):
    def __init__( self, offset, **kwargs ):
        super( CString, self ).__init__()
        self.offset = offset

    def get( self, buffer ):
        assert type( buffer ) == bytes
        return buffer.split( b'\x00', 1, **kwargs )[0]


class CStringN( Field ):
    def __init__( self, offset, length ):
        super( CStringN, self ).__init__()
        self.offset = offset
        self.length = length

    def get( self, buffer ):
        assert type( buffer ) == bytes
        return buffer[self.offset:self.offset+self.length].split( b'\x00', 1, **kwargs )[0]


class ValueField( Field ):
    def __init__( self, offset, format, size, bitmask=None, default=None, range=None, **kwargs ):
        super( ValueField, self ).__init__()
        self.offset = offset
        self.format = format
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

    def get( self, buffer ):
        assert type( buffer ) == bytes
        value = struct.unpack( self.format, self._get_bytes( buffer ) )[0]
        if self.range:
            assert value in self.range
        return value


class Int8( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<b', 1, **kwargs )


class UInt8( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>B', 1, **kwargs )


class Bits( UInt8 ):
    def __init__( self, offset, bits, **kwargs ):
        UInt8.__init__( self, offset, **kwargs )
        assert type( bits ) == int
        mask_bits = bin( bits ).split('b', 1)[1]
        self.bits = [(1<<i) for i, x in enumerate( reversed( mask_bits ) ) if x == '1']

    def get( self, buffer ):
        result = UInt8.get( self, buffer )
        value = 0
        for i, x in enumerate( self.bits ):
            value += (1 << i) if (result & x) else 0
        return value


class UInt16_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<H', 2, **kwargs )


class UInt32_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<I', 4, **kwargs )


class UInt64_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<Q', 8, **kwargs )


class Int16_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<h', 2, **kwargs )


class Int32_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<i', 4, **kwargs )


class Int64_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<q', 8, **kwargs )


class Float_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<f', 4, **kwargs )


class Double_LE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '<d', 8, **kwargs )


class UInt16_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>H', 2, **kwargs )


class UInt32_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>I', 4, **kwargs )


class UInt64_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>Q', 8, **kwargs )


class Int16_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>h', 2, **kwargs )


class Int32_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>i', 4, **kwargs )


class Int64_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>q', 8, **kwargs )


class Float_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>f', 4, **kwargs )


class Double_BE( ValueField ):
    def __init__( self, offset, **kwargs ):
        ValueField.__init__( self, offset, '>d', 8, **kwargs )

