import struct

RAW_TYPE_NAME = {
    (int, 1, 'signed', 'little'):   'int8',
    (int, 1, 'unsigned', 'little'): 'uint8',
    (int, 1, 'signed', 'big'):      'int8',
    (int, 1, 'unsigned', 'big'):    'uint8',
    (int, 1, 'signed', None):       'int8',
    (int, 1, 'unsigned', None):     'uint8',
    (int, 2, 'signed', 'little'):   'int16_le',
    (int, 3, 'signed', 'little'):   'int24_le',
    (int, 4, 'signed', 'little'):   'int32_le',
    (int, 8, 'signed', 'little'):   'int64_le',
    (int, 2, 'unsigned', 'little'): 'uint16_le',
    (int, 3, 'unsigned', 'little'): 'uint24_le',
    (int, 4, 'unsigned', 'little'): 'uint32_le',
    (int, 8, 'unsigned', 'little'): 'uint64_le',
    (float, 4, 'signed', 'little'): 'float32_le',
    (float, 8, 'signed', 'little'): 'float64_le',
    (int, 2, 'signed', 'big'):      'int16_be',
    (int, 3, 'signed', 'big'):      'int24_be',
    (int, 4, 'signed', 'big'):      'int32_be',
    (int, 8, 'signed', 'big'):      'int64_be',
    (int, 2, 'unsigned', 'big'):    'uint16_be',
    (int, 3, 'unsigned', 'big'):    'uint24_be',
    (int, 4, 'unsigned', 'big'):    'uint32_be',
    (int, 8, 'unsigned', 'big'):    'uint64_be',
    (float, 4, 'signed', 'big'):    'float32_be',
    (float, 8, 'signed', 'big'):    'float64_be',
}
RAW_TYPE_NAME_REVERSE = {v: k for k, v in RAW_TYPE_NAME.items()}

RAW_TYPE_STRUCT = {
    (int, 1, 'unsigned'):   'B',
    (int, 1, 'signed'):     'b',
    (int, 2, 'unsigned'):   'H',
    (int, 2, 'signed'):     'h',
    (int, 4, 'unsigned'):   'I',
    (int, 4, 'signed'):     'i',
    (int, 8, 'unsigned'):   'Q',
    (int, 8, 'signed'):     'q',
    (float, 4, 'signed'):   'f',
    (float, 8, 'signed'):   'd',
}



FROM_RAW_TYPE = {}
TO_RAW_TYPE = {}
FROM_RAW_TYPE_ARRAY = {}
TO_RAW_TYPE_ARRAY = {}


def get_raw_type_struct( format_type, field_size, signedness, endian, count=None ):
    return '{}{}{}'.format(
        '>' if endian == 'big' else '<',
        count if count is not None else '',
        RAW_TYPE_STRUCT[(format_type, field_size, signedness)]
    )


def get_raw_type_description( format_type, field_size, signedness, endian ):
    TYPE_NAMES = {
        int: 'integer',
        float: 'floating-point number',
    }
    type_name = TYPE_NAMES[format_type]
    return ('{}{}-bit {}{}'.format(
        ('signed ' if signedness == 'signed'  else 'unsigned ') if format_type == int else '',
        field_size*8,
        type_name,
        ' ({}-endian)'.format(endian) if field_size>1 else ''
    ), type_name)


def _from_raw_type( type_id ):
    result = lambda buffer: struct.unpack( get_raw_type_struct( *type_id ), buffer )[0]
    result.__doc__ = 'Convert a {0} byte string to a Python {1}.'.format(
        *get_raw_type_description( *type_id )
    )
    return result


def _to_raw_type( type_id ):
    result = lambda value: struct.pack( get_raw_type_struct( *type_id ), value )
    result.__doc__ = 'Convert a Python {1} to a {0} byte string.'.format(
        *get_raw_type_description( *type_id )
    )
    return result


def _from_raw_type_array( type_id ):
    result = lambda buffer: list( struct.unpack( get_raw_type_struct( *type_id, count=len( buffer )//type_id[1] ), buffer ) )
    result.__doc__ = 'Convert a {0} byte string to a Python list of {1}s.'.format(
        *get_raw_type_description( *type_id )
    )
    return result


def _to_raw_type_array( type_id ):
    result = lambda value_list: struct.pack( get_raw_type_struct( *type_id, count=len( value_list ) ), *value_list )
    result.__doc__ = 'Convert a Python list of {1}s to a {0} byte string.'.format(
        *get_raw_type_description( *type_id )
    )
    return result


def _from_generic_array( type_id, from_raw ):
    result = lambda buffer: [from_raw( buffer[i:i+type_id[1]] ) for i in range( 0, len( buffer ), type_id[1] )]
    result.__doc__ = 'Convert a {0} byte string to a Python list of {1}s.'.format(
        *get_raw_type_description( *type_id )
    )
    return result


def _to_generic_array( type_id, to_raw ):
    result = lambda value_list: b''.join( [to_raw( value ) for value in value_list] ) 
    result.__doc__ = 'Convert a Python list of {1}s to a {0} byte string.'.format(
        *get_raw_type_description( *type_id )
    )
    return result



# autogenerate conversion methods based on struct
for format_type, field_size, signedness in RAW_TYPE_STRUCT:
    endian_choices = [None, 'little', 'big'] if field_size == 1 else ['little', 'big']
    for endian in endian_choices:
        type_id = (format_type, field_size, signedness, endian)
        FROM_RAW_TYPE[type_id] = _from_raw_type( type_id )
        TO_RAW_TYPE[type_id] = _to_raw_type( type_id )
        FROM_RAW_TYPE_ARRAY[type_id] = _from_raw_type_array( type_id )
        TO_RAW_TYPE_ARRAY[type_id] = _to_raw_type_array( type_id )

# 24-bit types

RAW_24 = ['int24_le', 'uint24_le', 'int24_be', 'uint24_be']

def _from_raw_24( type_id ):
    format_type, field_size, signedness, endian = type_id
    assert format_type == int
    assert field_size == 3
    assert endian in ('little', 'big')
    assert signedness in ('signed', 'unsigned')
    def result( buffer ):
        if endian == 'little':
            buffer = buffer + (b'\xff' if (signedness == 'signed' and buffer[2] >= 0x80) else b'\x00')
        elif endian == 'big':
            buffer = (b'\xff' if (signedness == 'signed' and buffer[0] >= 0x80) else b'\x00') + buffer
        return FROM_RAW_TYPE[(format_type, 4, signedness, endian)]( buffer )
    result.__doc__ = 'Convert a {0} byte string to a Python {1}.'.format(
        *get_raw_type_description( *type_id )
    )
    return result


def _to_raw_24( type_id ):
    format_type, field_size, signedness, endian = type_id
    assert format_type == int
    assert field_size == 3
    assert endian in ('little', 'big')
    assert signedness in ('signed', 'unsigned')
    def result( value ):
        if signedness == 'signed':
            assert value in range( -1<<23, 1<<23 )
        else:
            assert value in range( 0, 1<<24 )
        output = TO_RAW_TYPE[(format_type, 4, signedness, endian)]( value )
        if endian == 'little':
            output = output[:3]
        elif endian == 'big':
            output = output[1:]
        return output
    result.__doc__ = 'Convert a Python {1} to a {0} byte string.'.format(
        *get_raw_type_description( *type_id )
    )
    return result


for code in RAW_24:
    type_id = RAW_TYPE_NAME_REVERSE[code]
    FROM_RAW_TYPE[type_id] = _from_raw_24( type_id )
    TO_RAW_TYPE[type_id] = _to_raw_24( type_id )
    FROM_RAW_TYPE_ARRAY[type_id] = _from_generic_array( type_id, FROM_RAW_TYPE[type_id] )
    TO_RAW_TYPE_ARRAY[type_id] = _to_generic_array( type_id, TO_RAW_TYPE[type_id] )


def _load_raw_types():
    result = {}
    for type_id, from_func in FROM_RAW_TYPE.items():
        result['from_{}'.format( RAW_TYPE_NAME[type_id] )] = from_func
    for type_id, to_func in TO_RAW_TYPE.items():
        result['to_{}'.format( RAW_TYPE_NAME[type_id] )] = to_func
    for type_id, from_func in FROM_RAW_TYPE_ARRAY.items():
        result['from_{}_array'.format( RAW_TYPE_NAME[type_id] )] = from_func
    for type_id, to_func in TO_RAW_TYPE_ARRAY.items():
        result['to_{}_array'.format( RAW_TYPE_NAME[type_id] )] = to_func

    return result


def unpack( type_id, value ):
    if isinstance( type_id, str ):
        type_id = RAW_TYPE_NAME_REVERSE[type_id]
    return FROM_RAW_TYPE[type_id]( value )


def pack( type_id, value ):
    if isinstance( type_id, str ):
        type_id = RAW_TYPE_NAME_REVERSE[type_id]
    return TO_RAW_TYPE[type_id]( value )


def unpack_array( type_id, values ):
    if isinstance( type_id, str ):
        type_id = RAW_TYPE_NAME_REVERSE[type_id]
    return FROM_RAW_TYPE_ARRAY[type_id]( values )


def pack_array( type_id, values ):
    if isinstance( type_id, str ):
        type_id = RAW_TYPE_NAME_REVERSE[type_id]
    return TO_RAW_TYPE_ARRAY[type_id]( values )
