import re
import struct
from typing import Dict, List, Callable, Tuple, Type, Union, Optional
import logging
from typing_extensions import Literal

logger = logging.getLogger( __name__ )

NumberType = Union[Type[int], Type[float]]
Number = Union[int, float]

SignedEncoding = Literal["signed", "unsigned"]
EndianEncoding = Literal["big", "little", None]
NumberEncoding = Tuple[NumberType, int, SignedEncoding, EndianEncoding]

# Python doesn't provide a programmatic way of fetching the supported codec list.
# The below list is taken from the 3.7 manual.
CODECS = [
    "ascii",
    "big5",
    "big5hkscs",
    "cp037",
    "cp273",
    "cp424",
    "cp437",
    "cp500",
    "cp720",
    "cp737",
    "cp775",
    "cp850",
    "cp852",
    "cp855",
    "cp856",
    "cp857",
    "cp858",
    "cp860",
    "cp861",
    "cp862",
    "cp863",
    "cp864",
    "cp865",
    "cp866",
    "cp869",
    "cp874",
    "cp875",
    "cp932",
    "cp949",
    "cp950",
    "cp1006",
    "cp1026",
    "cp1125",
    "cp1140",
    "cp1250",
    "cp1251",
    "cp1252",
    "cp1253",
    "cp1254",
    "cp1255",
    "cp1256",
    "cp1257",
    "cp1258",
    "euc_jp",
    "euc_jis_2004",
    "euc_jisx0213",
    "euc_kr",
    "gb2312",
    "gbk",
    "gb18030",
    "hz",
    "iso2022_jp",
    "iso2022_jp_1",
    "iso2022_jp_2",
    "iso2022_jp_2004",
    "iso2022_jp_3",
    "iso2022_jp_ext",
    "iso2022_kr",
    "latin_1",
    "iso8859_2",
    "iso8859_3",
    "iso8859_4",
    "iso8859_5",
    "iso8859_6",
    "iso8859_7",
    "iso8859_8",
    "iso8859_9",
    "iso8859_10",
    "iso8859_11",
    "iso8859_13",
    "iso8859_14",
    "iso8859_15",
    "iso8859_16",
    "johab",
    "koi8_r",
    "koi8_t",
    "koi8_u",
    "kz1048",
    "mac_cyrillic",
    "mac_greek",
    "mac_iceland",
    "mac_latin2",
    "mac_roman",
    "mac_turkish",
    "ptcp154",
    "shift_jis",
    "shift_jis_2004",
    "shift_jisx0213",
    "utf_32",
    "utf_32_be",
    "utf_32_le",
    "utf_16",
    "utf_16_be",
    "utf_16_le",
    "utf_7",
    "utf_8",
    "utf_8_sig",
]

REGEX_CHARS = """()[]{}?*+-|^$\\.&~#="""
byte_escape: Callable[[int], bytes] = lambda char: f"\\x{char:02x}".encode( "utf8" )


def regex_pattern_to_bytes(
    pattern: str,
    encoding: str = "utf8",
    fixed_string: bool = False,
    hex_format: bool = False,
) -> bytes:
    result = bytearray()

    # for hex format mode, strip out all whitespace characters first
    if hex_format:
        pattern = (
            pattern.replace( " ", "" )
            .replace( "\t", "" )
            .replace( "\n", "" )
            .replace( "\r", "" )
        )

    # strip out the automatic byte-order mark
    encoding_test = (
        encoding.lower().replace( " ", "" ).replace( "-", "" ).replace( "_", "" )
    )
    if encoding_test == "utf16":
        encoding = "utf-16-le"
    elif encoding_test == "utf32":
        encoding = "utf-32-le"

    pointer = 0
    repeat_block = False
    while pointer < len( pattern ):
        if pattern[pointer] == "\\" and not hex_format and not fixed_string:
            # an escaped character!
            if re.match( r"\\x[0-9A-Fa-f]{2}", pattern[pointer : pointer + 4] ):
                # escaped hex byte
                result.extend(
                    byte_escape(
                        bytes.fromhex( pattern[pointer + 2 : pointer + 4] )[0]
                    )
                )
                pointer += 4
            elif re.match( r'\\[\\\'"abfnrtv]', pattern[pointer : pointer + 2] ):
                # escaped single character
                char_id, char_raw = "\\'\"abfnrtv", "\\'\"\a\b\f\n\r\t\v"
                char_map = {
                    char_id[i]: ord( char_raw[i] ) for i in range( len( char_id ) )
                }
                result.extend( byte_escape( char_map[pattern[pointer + 1]] ) )
                pointer += 2
            elif pattern[pointer + 1] in REGEX_CHARS:
                # escaped character that's also a regex char
                result.extend( byte_escape( ord( pattern[pointer + 1] ) ) )
                pointer += 2
            else:
                raise ValueError( f"Unknown escape sequence \\{pattern[pointer + 1]}" )

        elif pattern[pointer] in REGEX_CHARS and not fixed_string:
            # a regex special character! inject it into the output unchanged
            if pattern[pointer] == "{":
                repeat_block = True
            elif pattern[pointer] == "}":
                repeat_block = False

            result.extend( pattern[pointer].encode( "utf8" ) )
            pointer += 1
        elif repeat_block:
            # inside a repeat block, don't encode anything
            result.extend( pattern[pointer].encode( "utf8" ) )
            pointer += 1
        elif hex_format:
            # we're in hex string mode; treat as raw hexadecimal
            if not re.match( r"[0-9A-Fa-f]{2}", pattern[pointer : pointer + 2] ):
                raise ValueError(
                    f"Sequence {pattern[pointer:pointer + 2]} is not valid hexadecimal"
                )
            result.extend( byte_escape( int( pattern[pointer : pointer + 2], 16 ) ) )
            pointer += 2
        else:
            # a normal character! encode as bytes, and inject escaped digits into the output
            for char in pattern[pointer].encode( encoding ):
                result.extend( byte_escape( char ) )
            pointer += 1
    return bytes( result )


def regex_unknown_encoding_match(
    source: str, char_size: int = 1
) -> Tuple[Dict[str, int], bytes]:
    match_map: Dict[str, int] = {}
    pattern = bytearray()
    for char in source:
        if char not in match_map:
            match_id = len( match_map )
            match_group = f"?P<p{match_id}>.".encode( "utf8" )
            if char_size != 1:
                match_group += b"{" + f"{char_size}".encode( "utf8" ) + b"}"
            if len( pattern ) == 0:
                pattern += b"(" + match_group + b")"
            else:
                pattern += b"(" + match_group + b"(?<!"
                pattern += b"|".join(
                    [
                        f"(?P=p{match_map[c]})".encode( "utf8" )
                        for c in match_map
                        if c != char
                    ]
                )
                pattern += b"))"
            match_map[char] = match_id
        else:
            pattern += f"(?P=p{match_map[char]})".encode( "utf8" )
    if len( source ) == len( match_map ):
        logger.warning(
            "Input has no repeated characters! This can make an enormous number of false matches, and is likely not what you want"
        )
    return match_map, bytes( pattern )


RAW_TYPE_NAME: Dict[NumberEncoding, str] = {
    (int, 1, "signed", "little"): "int8",
    (int, 1, "unsigned", "little"): "uint8",
    (int, 1, "signed", "big"): "int8",
    (int, 1, "unsigned", "big"): "uint8",
    (int, 1, "signed", None): "int8",
    (int, 1, "unsigned", None): "uint8",
    (int, 2, "signed", "little"): "int16_le",
    (int, 3, "signed", "little"): "int24_le",
    (int, 4, "signed", "little"): "int32_le",
    (int, 8, "signed", "little"): "int64_le",
    (int, 2, "unsigned", "little"): "uint16_le",
    (int, 3, "unsigned", "little"): "uint24_le",
    (int, 4, "unsigned", "little"): "uint32_le",
    (int, 8, "unsigned", "little"): "uint64_le",
    (float, 4, "signed", "little"): "float32_le",
    (float, 8, "signed", "little"): "float64_le",
    (int, 2, "signed", "big"): "int16_be",
    (int, 3, "signed", "big"): "int24_be",
    (int, 4, "signed", "big"): "int32_be",
    (int, 8, "signed", "big"): "int64_be",
    (int, 2, "unsigned", "big"): "uint16_be",
    (int, 3, "unsigned", "big"): "uint24_be",
    (int, 4, "unsigned", "big"): "uint32_be",
    (int, 8, "unsigned", "big"): "uint64_be",
    (float, 4, "signed", "big"): "float32_be",
    (float, 8, "signed", "big"): "float64_be",
}
RAW_TYPE_NAME_REVERSE = {v: k for k, v in RAW_TYPE_NAME.items()}

RAW_TYPE_STRUCT: Dict[Tuple[NumberType, int, SignedEncoding], str] = {
    (int, 1, "unsigned"): "B",
    (int, 1, "signed"): "b",
    (int, 2, "unsigned"): "H",
    (int, 2, "signed"): "h",
    (int, 4, "unsigned"): "I",
    (int, 4, "signed"): "i",
    (int, 8, "unsigned"): "Q",
    (int, 8, "signed"): "q",
    (float, 4, "signed"): "f",
    (float, 8, "signed"): "d",
}


FROM_RAW_TYPE: Dict[NumberEncoding, Callable[[bytes], Number]] = {}
TO_RAW_TYPE: Dict[NumberEncoding, Callable[[Number], bytes]] = {}
FROM_RAW_TYPE_ARRAY: Dict[NumberEncoding, Callable[[bytes], List[Number]]] = {}
TO_RAW_TYPE_ARRAY: Dict[NumberEncoding, Callable[[List[Number]], bytes]] = {}


def get_raw_type_struct(
    format_type: NumberType,
    field_size: int,
    signedness: SignedEncoding,
    endian: EndianEncoding,
    count: Optional[int] = None,
) -> str:
    endianness = ">" if endian == "big" else "<"
    count_str = count if count is not None else ""
    return f"{endianness}{count_str}{RAW_TYPE_STRUCT[(format_type, field_size, signedness)]}"


def get_raw_type_description(
    format_type: NumberType,
    field_size: int,
    signedness: SignedEncoding,
    endian: EndianEncoding,
) -> Tuple[str, str]:
    TYPE_NAMES: Dict[NumberType, str] = {
        int: "integer",
        float: "floating-point number",
    }
    type_name = TYPE_NAMES[format_type]
    prefix = (
        ("signed " if signedness == "signed" else "unsigned ")
        if format_type == int
        else ""
    )
    suffix = f" ({endian}-endian)" if field_size > 1 else ""
    return f"{prefix}{field_size * 8}-bit {type_name}{suffix}", type_name


def _from_raw_type(
    format_type: NumberType,
    field_size: int,
    signedness: SignedEncoding,
    endian: EndianEncoding,
) -> Callable[[bytes], Number]:
    result: Callable[[bytes], Number] = lambda buffer: struct.unpack(
        get_raw_type_struct( format_type, field_size, signedness, endian ), buffer
    )[0]
    result.__doc__ = "Convert a {0} byte string to a Python {1}.".format(
        *get_raw_type_description( format_type, field_size, signedness, endian )
    )
    return result


def _to_raw_type(
    format_type: NumberType,
    field_size: int,
    signedness: SignedEncoding,
    endian: EndianEncoding,
) -> Callable[[Number], bytes]:
    result: Callable[[Number], bytes] = lambda value: struct.pack(
        get_raw_type_struct( format_type, field_size, signedness, endian ), value
    )
    result.__doc__ = "Convert a Python {1} to a {0} byte string.".format(
        *get_raw_type_description( format_type, field_size, signedness, endian )
    )
    return result


def _from_raw_type_array(
    format_type: NumberType,
    field_size: int,
    signedness: SignedEncoding,
    endian: EndianEncoding,
) -> Callable[[bytes], List[Number]]:
    result: Callable[[bytes], List[Number]] = lambda buffer: list(
        struct.unpack(
            get_raw_type_struct(
                format_type,
                field_size,
                signedness,
                endian,
                count=len( buffer ) // type_id[1],
            ),
            buffer,
        )
    )
    result.__doc__ = "Convert a {0} byte string to a Python list of {1}s.".format(
        *get_raw_type_description( format_type, field_size, signedness, endian )
    )
    return result


def _to_raw_type_array(
    format_type: NumberType,
    field_size: int,
    signedness: SignedEncoding,
    endian: EndianEncoding,
) -> Callable[[List[Number]], bytes]:
    result: Callable[[List[Number]], bytes] = lambda value_list: struct.pack(
        get_raw_type_struct(
            format_type, field_size, signedness, endian, count=len( value_list )
        ),
        *value_list,
    )
    result.__doc__ = "Convert a Python list of {1}s to a {0} byte string.".format(
        *get_raw_type_description( format_type, field_size, signedness, endian )
    )
    return result


def _from_generic_array( type_id: NumberEncoding, from_raw: Callable[[bytes], Number] ):
    result: Callable[[bytes], List[Number]] = lambda buffer: [
        from_raw( buffer[i : i + type_id[1]] )
        for i in range( 0, len( buffer ), type_id[1] )
    ]
    result.__doc__ = "Convert a {0} byte string to a Python list of {1}s.".format(
        *get_raw_type_description( *type_id )
    )
    return result


def _to_generic_array( type_id: NumberEncoding, to_raw: Callable[[Number], bytes] ):
    result: Callable[[List[Number]], bytes] = lambda value_list: b"".join(
        [to_raw( value ) for value in value_list]
    )
    result.__doc__ = "Convert a Python list of {1}s to a {0} byte string.".format(
        *get_raw_type_description( *type_id )
    )
    return result


# autogenerate conversion methods based on struct
for format_type, field_size, signedness in RAW_TYPE_STRUCT:
    endian_choices: List[EndianEncoding] = (
        [None, "little", "big"] if field_size == 1 else ["little", "big"]
    )
    endian: EndianEncoding
    for endian in endian_choices:
        type_id = (format_type, field_size, signedness, endian)
        FROM_RAW_TYPE[type_id] = _from_raw_type( *type_id )
        TO_RAW_TYPE[type_id] = _to_raw_type( *type_id )
        FROM_RAW_TYPE_ARRAY[type_id] = _from_raw_type_array( *type_id )
        TO_RAW_TYPE_ARRAY[type_id] = _to_raw_type_array( *type_id )

# 24-bit types

RAW_24 = ["int24_le", "uint24_le", "int24_be", "uint24_be"]


def _from_raw_24( type_id: NumberEncoding ):
    signedness: SignedEncoding
    endian: EndianEncoding
    format_type, field_size, signedness, endian = type_id
    assert format_type == int
    assert field_size == 3
    assert endian in ("little", "big")
    assert signedness in ("signed", "unsigned")

    def result( buffer: bytes ):
        if endian == "little":
            buffer = buffer + (
                b"\xff" if (signedness == "signed" and buffer[2] >= 0x80) else b"\x00"
            )
        elif endian == "big":
            buffer = (
                b"\xff" if (signedness == "signed" and buffer[0] >= 0x80) else b"\x00"
            ) + buffer
        return FROM_RAW_TYPE[(format_type, 4, signedness, endian)]( buffer )

    result.__doc__ = "Convert a {0} byte string to a Python {1}.".format(
        *get_raw_type_description( *type_id )
    )
    return result


def _to_raw_24( type_id: NumberEncoding ):
    signedness: SignedEncoding
    endian: EndianEncoding
    format_type, field_size, signedness, endian = type_id
    assert format_type == int
    assert field_size == 3
    assert endian in ("little", "big")
    assert signedness in ("signed", "unsigned")

    def result( value: Number ):
        if signedness == "signed":
            assert value in range( -1 << 23, 1 << 23 )
        else:
            assert value in range( 0, 1 << 24 )
        output = TO_RAW_TYPE[(format_type, 4, signedness, endian)]( value )
        if endian == "little":
            output = output[:3]
        elif endian == "big":
            output = output[1:]
        return output

    result.__doc__ = "Convert a Python {1} to a {0} byte string.".format(
        *get_raw_type_description( *type_id )
    )
    return result


for code in RAW_24:
    type_id = RAW_TYPE_NAME_REVERSE[code]
    FROM_RAW_TYPE[type_id] = _from_raw_24( type_id )
    TO_RAW_TYPE[type_id] = _to_raw_24( type_id )
    FROM_RAW_TYPE_ARRAY[type_id] = _from_generic_array(
        type_id, FROM_RAW_TYPE[type_id]
    )
    TO_RAW_TYPE_ARRAY[type_id] = _to_generic_array( type_id, TO_RAW_TYPE[type_id] )


def unpack( type_id: NumberEncoding, value: bytes ):
    if isinstance( type_id, str ):
        type_id = RAW_TYPE_NAME_REVERSE[type_id]
    return FROM_RAW_TYPE[type_id]( value )


def pack( type_id: NumberEncoding, value: Number ):
    if isinstance( type_id, str ):
        type_id = RAW_TYPE_NAME_REVERSE[type_id]
    return TO_RAW_TYPE[type_id]( value )


def unpack_array( type_id: NumberEncoding, values: bytes ):
    if isinstance( type_id, str ):
        type_id = RAW_TYPE_NAME_REVERSE[type_id]
    return FROM_RAW_TYPE_ARRAY[type_id]( values )


def pack_array( type_id: NumberEncoding, values: List[Number] ):
    if isinstance( type_id, str ):
        type_id = RAW_TYPE_NAME_REVERSE[type_id]
    return TO_RAW_TYPE_ARRAY[type_id]( values )
