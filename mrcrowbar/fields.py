import struct
import itertools 

_next_position_hint = itertools.count()


class FieldValidationError( Exception ):
    pass


class Field( object ):
    _field_size = 0

    def __init__( self, default=None, **kwargs ):
        self._position_hint = next( _next_position_hint )
        self.default = default

    def get_from_buffer( self, buffer, **kwargs ):
        return None

    def update_buffer_with_value( self, value, buffer ):
        assert type( buffer ) == bytearray
        self.validate( value )
        return

    def size( self ):
        return self._field_size

    def validate( self, value ):
        pass 


class Ref( object ):
    # very simple path syntax for now: walk down the chain of properties
    def __init__( self, path, allow_write=False ):
        self.path = path.split( '.' )
        self.allow_write = allow_write 

    def get( self, instance ):
        target = instance
        for attr in self.path:
            target = getattr( target, attr )
        return target

    def set( self, instance, value ):
        if not self.allow_write:
            raise AttributeError( "can't set Ref directly" )
        target = instance
        for attr in self.path[:-1]:
            target = getattr( target, attr )
        setattr( target, self.path[-1], value )
        return


class BlockStream( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, transform=None, **kwargs ):
        super( BlockStream, self ).__init__( **kwargs )
        self.block_klass = block_klass
        self.offset = offset
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.transform = transform

    def get_from_buffer( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        result = []
        if self.transform:
            pointer = self.offset
            while pointer < len( buffer ):
                data = self.transform.import_data( buffer[pointer:] )
                block = self.block_klass( data['payload'], **self.block_kwargs )
                block._parent = parent
                result.append( block )
                pointer += data['end_offset']
        else:
            block = self.block_klass( buffer[pointer:], **self.block_kwargs )
            assert block.size() > 0
            block._parent = parent
            result.append( block )
            pointer += block.size()
        return result


class BlockList( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, count=0, stop_check=None, fill=None, **kwargs ):
        super( BlockList, self ).__init__( **kwargs )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self._offset = offset
        self._count = count
        self.stop_check = stop_check
        self.fill = fill

    @property
    def offset( self ):
        if type( self._offset ) == Ref:
            return self._offset.get( )
        return self._offset

    @property
    def count( self ):
        if type( self._count ) == Ref:
            return self._count.get( )
        return self._count

    def get_from_buffer( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        result = []
        stride = self.block_klass._block_size
        for i in range( self.count ):
            sub_buffer = buffer[self.offset + i*stride:][:stride]
            # if data matches the fill pattern, leave a None in the list
            if self.fill and (sub_buffer == bytes(( self.fill[j % len(self.fill)] for j in range(len(sub_buffer)) ))):
                result.append( None )
            else:
                # run the stop check (if exists): if it returns true, we've hit the end of the stream
                if self.stop_check and (self.stop_check( buffer, self.offset+i*stride )):
                    break
                block = self.block_klass( sub_buffer )
                block._parent = parent
                result.append( block )
                    
                    
        return result
        
    def update_buffer_with_value( self, value, buffer ):
        super( BlockList, self ).update_buffer_with_value( value, buffer )
        block_data = bytearray()
        stride = self.block_klass._block_size
        for b in value:
            if b is None:
                if self.fill:
                    block_data += bytes(( self.fill[j % len(self.fill)] for j in range(stride) ))
                else:
                    block_data += b'\x00'*stride
            else:
                block_data += b.export_data()
        if len( buffer ) < self.offset+len( block_data ):
            buffer.extend( b'\x00'*(self.offset+len( block_data )-len( buffer )) )
        buffer[self.offset:self.offset+len( block_data )] = block_data
        return


    def validate( self, value ):
        try:
            it = iter( value )
        except TypeError:
            raise FieldValidationError( 'Type {} not iterable'.format( type( value ) ) )
        if self.count:
            assert len( value ) <= self.count
        for b in value:
            if (b is not None) and (not isinstance( b, self.block_klass )):
                 raise FieldValidationError( 'Expecting block class {}, not {}'.format( self.block_klass, type( b ) ) )

class BlockField( Field ):
    def __init__( self, block_klass, offset=None, block_kwargs=None, fill=None, transform=None, **kwargs ):
        super( BlockField, self ).__init__( **kwargs )
        self.block_klass = block_klass
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.offset = offset
        self.fill = fill
        self.transform = transform

    def get_from_buffer( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        result = None
        if self.transform:
            result = self.block_klass( self.transform.import_data( buffer[self.offset:] )['payload'], **self.block_kwargs )
        else:
            result = self.block_klass( buffer[self.offset:], **self.block_kwargs )

        result._parent = parent
        return result
        #return (self.fill*int( 1+self.block_klass._block_size/len(self.fill) ))[:self.block_klass._block_size]

    def update_buffer_with_value( self, value, buffer ):
        super( BlockField, self ).update_buffer_with_value( value, buffer )
        if self.transform:
            block_data = self.transform.export_data( value.export_data() )
        else:
            block_data = value.export_data()
        if len( buffer ) < self.offset+len( block_data ):
            buffer.extend( b'\x00'*(self.offset+len( block_data )-len( buffer )) )
        buffer[self.offset:self.offset+len( block_data )] = block_data
        return

    def validate( self, value ):
        if not isinstance( value, self.block_klass ):
            raise FieldValidationError( 'Expecting block class {}, not {}'.format( self.block_klass, type( value ) ) )
        return
        


class Bytes( Field ):
    def __init__( self, offset, length=None, default=None, **kwargs ):
        if length is not None:
            if default is not None:
                assert type( default ) == bytes
                assert len( default ) == length
            else:
                default = b'\x00'*length
        else:
            if default is not None:
                assert type( default ) == bytes
            else:
                default = b''
        super( Bytes, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length
        if length:
            self._field_size = length

    def get_from_buffer( self, buffer, **kwargs ):
        assert type( buffer ) == bytes
        if self.length is not None:
            return buffer[self.offset:self.offset+self.length]
        else:
            return buffer[self.offset:]

    def update_buffer_with_value( self, value, buffer ):
        super( Bytes, self ).update_buffer_with_value( value, buffer )
        block_data = value
        if len( buffer ) < self.offset+len( block_data ):
            buffer.extend( b'\x00'*(self.offset+len( block_data )-len( buffer )) )    
        buffer[self.offset:self.offset+len( block_data )] = block_data
        return


    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (self.length is not None) and (len( value ) != self.length):
            raise FieldValidationError( 'Expecting length of {}, not {}'.format( self.length, len( value ) ) )
        return


class CString( Field ):
    def __init__( self, offset, default=b'', **kwargs ):
        assert type( default ) == bytes
        super( CString, self ).__init__( default=default, **kwargs )
        self.offset = offset

    def get_from_buffer( self, buffer, **kwargs ):
        assert type( buffer ) == bytes
        return buffer.split( b'\x00', 1, **kwargs )[0]

    def update_buffer_with_value( self, value, buffer ):
        super( CString, self ).update_buffer_with_value( value, buffer )
        block_data = value + b'\x00'
        if len( buffer ) < self.offset+len( block_data ):
            buffer.extend( b'\x00'*(self.offset+len( block_data )-len( buffer )) )    
        buffer[self.offset:self.offset+len( block_data )] = block_data
        return

    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        return 

class CStringN( Field ):
    def __init__( self, offset, length, default=b'', **kwargs ):
        assert type( default ) == bytes
        super( CStringN, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self._field_size = length

    def get_from_buffer( self, buffer, **kwargs ):
        assert type( buffer ) == bytes
        return buffer[self.offset:self.offset+self._field_size].split( b'\x00', 1, **kwargs )[0]

    def update_buffer_with_value( self, value, buffer ):
        super( CStringN, self ).update_buffer_with_value( value, buffer )
        block_data = value + b'\x00'*(self._field_size - len( value ))
        if len( buffer ) < self.offset+len( block_data ):
            buffer.extend( b'\x00'*(self.offset+len( block_data )-len( buffer )) )    
        buffer[self.offset:self.offset+len( block_data )] = block_data
        return

    def validate( self, value ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (len( value ) > self._field_size):
            raise FieldValidationError( 'Expecting length <= {}, not {}'.format( self._field_size, len( value ) ) )
        return
    

class ValueField( Field ):
    def __init__( self, format, size, format_type, format_range, offset, default=0, bitmask=None, range=None, **kwargs ):
        super( ValueField, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.format = format
        self.format_type = format_type
        self.format_range = format_range
        if bitmask:
            assert type( bitmask ) == bytes
            assert len( bitmask ) == size
        self._field_size = size
        self.bitmask = bitmask
        self.range = range

    def _get_bytes( self, buffer ):
        data = buffer[self.offset:self.offset+self._field_size]
        assert len( data ) == self._field_size
        if self.bitmask:
            return (int.from_bytes( data, byteorder='big' ) & 
                    int.from_bytes( self.bitmask, byteorder='big' )
                    ).to_bytes( self._field_size, byteorder='big' )
        else:
            return data

    def _set_bytes( self, data, array ):
        # force check for no data loss in the value from bitmask
        if self.bitmask:
            assert (int.from_bytes( data, byteorder='big' ) & 
                    int.from_bytes( self.bitmask, byteorder='big' ) ==
                    int.from_bytes( data, byteorder='big' ))
        
            for i in range( self._field_size ):
                # set bitmasked areas of target to 0
                array[i+self.offset] &= (~ self.bitmask[i])
                # OR target with replacement bitmasked portion
                array[i+self.offset] |= (data[i] & self.bitmask[i])
        else:
            for i in range( self._field_size ):
                array[i+self.offset] = data[i]
        return

    def get_from_buffer( self, buffer, **kwargs ):
        assert type( buffer ) == bytes
        value = struct.unpack( self.format, self._get_bytes( buffer ) )[0]
        if self.range and (value not in self.range):
            print( 'WARNING: value {} outside of range {}'.format( value, self.range ) )
        return value

    def update_buffer_with_value( self, value, buffer ):
        super( ValueField, self ).update_buffer_with_value( value, buffer )
        if (len( buffer ) < self.offset+self._field_size):
            buffer.extend( b'\x00'*(self.offset+self._field_size-len( buffer )) )
        data = struct.pack( self.format, value ) 
        self._set_bytes( data, buffer )
        return

    def validate( self, value ):
        if (type( value ) != self.format_type):
            raise FieldValidationError( 'Expecting type {}, not {}'.format( self.format_type, type( value ) ) )
        if self.format_range and (value not in self.format_range):
            raise FieldValidationError( 'Value {} not in format range ({})'.format( value, self.format_range ) )
        if self.range and (value not in self.range):
            raise FieldValidationError( 'Value {} not in range ({})'.format( value, self.range ) )
        return


class Int8( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<b', 1, int, range( -1<<7, 1<<7 ), *args, **kwargs )


class UInt8( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>B', 1, int, range( 0, 1<<8 ), *args, **kwargs )


class Bits( UInt8 ):
    def __init__( self, offset, bits, default=0, *args, **kwargs ):
        UInt8.__init__( self, offset, default=default, *args, **kwargs )
        assert type( bits ) == int
        mask_bits = bin( bits ).split( 'b', 1 )[1]
        self.bits = [(1<<i) for i, x in enumerate( reversed( mask_bits ) ) if x == '1']
        self.format_range = range( 0, 1<<len( self.bits ) )

    def get_from_buffer( self, buffer, **kwargs ):
        result = UInt8.get_from_buffer( self, buffer )
        value = 0
        for i, x in enumerate( self.bits ):
            value += (1 << i) if (result & x) else 0
        return value

    def update_buffer_with_value( self, value, buffer ):
        super( ValueField, self ).update_buffer_with_value( value, buffer )
        for i, x in enumerate( self.bits ):
            buffer[self.offset] &= 0xff - x
            if (value & (1 << i)):
                buffer[self.offset] |= x
        return


class UInt16_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<H', 2, int, range( 0, 1<<16 ), *args, **kwargs )


class UInt32_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<I', 4, int, range( 0, 1<<32 ), *args, **kwargs )


class UInt64_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<Q', 8, int, range( 0, 1<<64 ), *args, **kwargs )


class Int16_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<h', 2, int, range( -1<<15, 1<<15 ), *args, **kwargs )


class Int32_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<i', 4, int, range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<q', 8, int, range( -1<<63, 1<<63 ), *args, **kwargs )


class Float_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<f', 4, float, None, *args, **kwargs )


class Double_LE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '<d', 8, float, None, *args, **kwargs )


class UInt16_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>H', 2, int, range( 0, 1<<16 ), *args, **kwargs )


class UInt32_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>I', 4, int, range( 0, 1<<32 ), *args, **kwargs )


class UInt64_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>Q', 8, int, range( 0, 1<<64 ), *args, **kwargs )


class Int16_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>h', 2, int, range( -1<<15, 1<<15 ), *args, **kwargs )


class Int32_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>i', 4, int, range( -1<<31, 1<<31 ), *args, **kwargs )


class Int64_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>q', 8, int, range( -1<<63, 1<<63 ), *args, **kwargs )


class Float_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>f', 4, float, None, *args, **kwargs )


class Double_BE( ValueField ):
    def __init__( self, *args, **kwargs ):
        ValueField.__init__( self, '>d', 8, float, None, *args, **kwargs )


