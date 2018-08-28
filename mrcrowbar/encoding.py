import struct


def _byte_type_to_text( code, size ):
    raw_type = 'float' if code[1] in 'fd' else 'integer'
    is_signed = code[1].islower()
    endianness = 'big' if code[0] == '>' else 'little'
    return ('{}{}-bit {}{}'.format(
        ('signed ' if is_signed else 'unsigned ') if raw_type == 'integer' else '',
        size*8,
        raw_type,
        ' ({}-endian)'.format(endianness) if size>1 else ''
    ), raw_type)


def _from_byte_type( code, size ):
    result = lambda buffer: struct.unpack( code, buffer[:size] )[0]
    result.__doc__ = 'Convert a {0} byte string to a Python {1}.'.format(
        *_byte_type_to_text( code, size )
    )
    return result


def _to_byte_type( code, size ):
    result = lambda value: struct.pack( code, value )
    result.__doc__ = 'Convert a Python {1} to a {0} byte string.'.format(
        *_byte_type_to_text( code, size )
    )
    return result


def _map_entry( label, code, size ):
    return (label, _from_byte_type( code, size ), _to_byte_type( code, size ))


BYTE_TYPE_MAP = {
    (int, 1, 'signed', None):       _map_entry( 'int8', '<b', 1 ),
    (int, 1, 'unsigned', None):     _map_entry( 'uint8', '<B', 1 ),
    (int, 2, 'signed', 'little'):   _map_entry( 'int16_le', '<h', 2 ),
    (int, 4, 'signed', 'little'):   _map_entry( 'int32_le', '<i', 4 ),
    (int, 8, 'signed', 'little'):   _map_entry( 'int64_le', '<q', 8 ),
    (int, 2, 'unsigned', 'little'): _map_entry( 'uint16_le', '<H', 2 ),
    (int, 4, 'unsigned', 'little'): _map_entry( 'uint32_le', '<I', 4 ),
    (int, 8, 'unsigned', 'little'): _map_entry( 'uint64_le', '<Q', 8 ),
    (float, 4, 'signed', 'little'): _map_entry( 'float32_le', '<f', 4 ),
    (float, 8, 'signed', 'little'): _map_entry( 'float64_le', '<d', 8 ),
    (int, 2, 'signed', 'big'):      _map_entry( 'int16_be', '>h', 2 ),
    (int, 4, 'signed', 'big'):      _map_entry( 'int32_be', '>i', 4 ),
    (int, 8, 'signed', 'big'):      _map_entry( 'int64_be', '>q', 8 ),
    (int, 2, 'unsigned', 'big'):    _map_entry( 'uint16_be', '>H', 2 ),
    (int, 4, 'unsigned', 'big'):    _map_entry( 'uint32_be', '>I', 4 ),
    (int, 8, 'unsigned', 'big'):    _map_entry( 'uint64_be', '>Q', 8 ),
    (float, 4, 'signed', 'big'):    _map_entry( 'float32_be', '>f', 4 ),
    (float, 8, 'signed', 'big'):    _map_entry( 'float64_be', '>d', 8 ),
}


def _load_byte_types():
    result = {}
    for (byte_type, from_func, to_func) in BYTE_TYPE_MAP.values():
        result['from_{}'.format(byte_type)] = from_func
        result['to_{}'.format(byte_type)] = to_func
    return result


def unpack( type_id, value ):
    return BYTE_TYPE_MAP[type_id][1]( value )


def pack( type_id, value ):
    return BYTE_TYPE_MAP[type_id][2]( value )

