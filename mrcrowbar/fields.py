import struct
import itertools 

_next_position_hint = itertools.count()


class FieldValidationError( Exception ):
    pass


class Field( object ):
    def __init__( self, default=None, **kwargs ):
        self._position_hint = next( _next_position_hint )
        self.default = default

    def get_from_buffer( self, buffer, parent=None ):
        return None

    def update_buffer_with_value( self, value, buffer, parent=None ):
        assert type( buffer ) == bytearray
        self.validate( value )
        return

    def validate( self, value, parent=None ):
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


def property_get( prop, parent ):
    if type( prop ) == Ref:
        return prop.get( parent )
    return prop

def property_set( prop, parent, value ):
    if type( prop ) == Ref:
        return prop.set( parent, value )
    raise AttributeError( "property was declared as a constant" )


class View( object ):
    def __init__( self, parent, *args, **kwargs ):
        self._parent = parent


class BlockStream( Field ):
    def __init__( self, block_klass, offset, block_kwargs=None, transform=None, **kwargs ):
        super( BlockStream, self ).__init__( **kwargs )
        self.block_klass = block_klass
        self.offset = offset
        self.block_kwargs = block_kwargs if block_kwargs else {}
        self.transform = transform

    def get_from_buffer( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        offset = property_get( self.offset, parent )

        pointer = offset
        result = []
        while pointer < len( buffer ):
            if self.transform:
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
        self.offset = offset
        self.count = count
        self.stop_check = stop_check
        self.fill = fill

    def get_from_buffer( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )

        result = []
        stride = self.block_klass._block_size
        for i in range( count ):
            sub_buffer = buffer[offset + i*stride:][:stride]
            # if data matches the fill pattern, leave a None in the list
            if self.fill and (sub_buffer == bytes(( self.fill[j % len(self.fill)] for j in range(len(sub_buffer)) ))):
                result.append( None )
            else:
                # run the stop check (if exists): if it returns true, we've hit the end of the stream
                if self.stop_check and (self.stop_check( buffer, offset+i*stride )):
                    break
                block = self.block_klass( sub_buffer )
                block._parent = parent
                result.append( block )
                    
        return result
        
    def update_buffer_with_value( self, value, buffer, parent=None ):
        super( BlockList, self ).update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )

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
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )
        buffer[offset:offset+len( block_data )] = block_data
        return

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        count = property_get( self.count, parent )

        try:
            it = iter( value )
        except TypeError:
            raise FieldValidationError( 'Type {} not iterable'.format( type( value ) ) )
        if count:
            assert len( value ) <= count
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
        offset = property_get( self.offset, parent )

        result = None
        if self.transform:
            result = self.block_klass( self.transform.import_data( buffer[offset:] )['payload'], **self.block_kwargs )
        else:
            result = self.block_klass( buffer[offset:], **self.block_kwargs )

        result._parent = parent
        return result
        #return (self.fill*int( 1+self.block_klass._block_size/len(self.fill) ))[:self.block_klass._block_size]

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super( BlockField, self ).update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )

        if self.transform:
            block_data = self.transform.export_data( value.export_data() )
        else:
            block_data = value.export_data()
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )
        buffer[offset:offset+len( block_data )] = block_data
        return

    def validate( self, value ):
        if not isinstance( value, self.block_klass ):
            raise FieldValidationError( 'Expecting block class {}, not {}'.format( self.block_klass, type( value ) ) )
        return
        

class Bytes( Field ):
    def __init__( self, offset, length=None, default=None, transform=None, **kwargs ):
        if default is not None:
            assert type( default ) == bytes
        else:
            default = b''
        super( Bytes, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length
        self.transform = transform

    def get_from_buffer( self, buffer, parent=None, **kwargs ):
        assert type( buffer ) == bytes
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        data = buffer[offset:]
        if length is not None:
            data = buffer[offset:offset+length]

        if self.transform:
            data = self.transform.import_data( data )['payload']
    
        return data

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super( Bytes, self ).update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )
        
        data = value
        if self.transform:
            data = self.transform.export_data( data )

        if len( buffer ) < offset+len( data ):
            buffer.extend( b'\x00'*(offset+len( data )-len( buffer )) )    
        buffer[offset:offset+len( data )] = data
        return

    def validate( self, value, parent=None ):
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (length is not None) and (len( value ) != length):
            raise FieldValidationError( 'Expecting length of {}, not {}'.format( length, len( value ) ) )
        return


class CString( Field ):
    def __init__( self, offset, default=b'', **kwargs ):
        assert type( default ) == bytes
        super( CString, self ).__init__( default=default, **kwargs )
        self.offset = offset

    def get_from_buffer( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        offset = property_get( self.offset, parent )

        return buffer[offset:].split( b'\x00', 1 )[0]

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super( CString, self ).update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )

        block_data = value + b'\x00'
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )    
        buffer[offset:offset+len( block_data )] = block_data
        return

    def validate( self, value, parent=None ):
        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        return 


class CStringN( Field ):
    def __init__( self, offset, length, default=b'', **kwargs ):
        assert type( default ) == bytes
        super( CStringN, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.length = length

    def get_from_buffer( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        return buffer[offset:offset+length].split( b'\x00', 1 )[0]

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super( CStringN, self ).update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )
        length = property_get( self.length, parent )

        block_data = value + b'\x00'*(length - len( value ))
        if len( buffer ) < offset+len( block_data ):
            buffer.extend( b'\x00'*(offset+len( block_data )-len( buffer )) )    
        buffer[offset:offset+len( block_data )] = block_data
        return

    def validate( self, value, parent=None ):
        length = property_get( self.length, parent )

        if type( value ) != bytes:
            raise FieldValidationError( 'Expecting type {}, not {}'.format( bytes, type( value ) ) )
        if (len( value ) > length):
            raise FieldValidationError( 'Expecting length <= {}, not {}'.format( length, len( value ) ) )
        return
    

class ValueField( Field ):
    def __init__( self, format, field_size, format_type, format_range, offset, default=0, bitmask=None, range=None, **kwargs ):
        super( ValueField, self ).__init__( default=default, **kwargs )
        self.offset = offset
        self.format = format
        self.format_type = format_type
        self.format_range = format_range
        if bitmask:
            assert type( bitmask ) == bytes
            assert len( bitmask ) == field_size
        self.field_size = field_size
        self.bitmask = bitmask
        self.range = range

    def get_from_buffer( self, buffer, parent=None ):
        assert type( buffer ) == bytes
        offset = property_get( self.offset, parent )

        data = buffer[offset:offset+self.field_size]
        assert len( data ) == self.field_size
        if self.bitmask:
            data = (int.from_bytes( data, byteorder='big' ) & 
                    int.from_bytes( self.bitmask, byteorder='big' )
                    ).to_bytes( self.field_size, byteorder='big' )

        value = struct.unpack( self.format, data )[0]
        if self.range and (value not in self.range):
            print( 'WARNING: value {} outside of range {}'.format( value, self.range ) )
        return value

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super( ValueField, self ).update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )

        if (len( buffer ) < offset+self.field_size):
            buffer.extend( b'\x00'*(offset+self.field_size-len( buffer )) )
        data = struct.pack( self.format, value ) 
        
        # force check for no data loss in the value from bitmask
        if self.bitmask:
            assert (int.from_bytes( data, byteorder='big' ) & 
                    int.from_bytes( self.bitmask, byteorder='big' ) ==
                    int.from_bytes( data, byteorder='big' ))
        
            for i in range( self.field_size ):
                # set bitmasked areas of target to 0
                array[i+offset] &= (~ self.bitmask[i])
                # OR target with replacement bitmasked portion
                array[i+offset] |= (data[i] & self.bitmask[i])
        else:
            for i in range( self.field_size ):
                array[i+offset] = data[i]
        return

    def validate( self, value, parent=None ):
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
        super( Bits, self ).__init__( offset, default=default, *args, **kwargs )
        assert type( bits ) == int
        mask_bits = bin( bits ).split( 'b', 1 )[1]
        self.bits = [(1<<i) for i, x in enumerate( reversed( mask_bits ) ) if x == '1']
        self.format_range = range( 0, 1<<len( self.bits ) )

    def get_from_buffer( self, buffer, parent=None ):
        result = super( Bits, self ).get_from_buffer( buffer, parent )
        value = 0
        for i, x in enumerate( self.bits ):
            value += (1 << i) if (result & x) else 0
        return value

    def update_buffer_with_value( self, value, buffer, parent=None ):
        super( Bits, self ).update_buffer_with_value( value, buffer, parent )
        offset = property_get( self.offset, parent )

        for i, x in enumerate( self.bits ):
            buffer[offset] &= 0xff - x
            if (value & (1 << i)):
                buffer[offset] |= x
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


