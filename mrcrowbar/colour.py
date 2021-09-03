from __future__ import annotations

import itertools
import math
from mrcrowbar.common import BytesReadType

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union


class BaseColour( object ):
    r = 0.0
    g = 0.0
    b = 0.0
    a = 1.0

    @property
    def r_8( self ) -> int:
        return round( self.r * 255 )

    @r_8.setter
    def r_8( self, value: int ) -> None:
        self.r = value / 255

    @property
    def g_8( self ) -> int:
        return round( self.g * 255 )

    @g_8.setter
    def g_8( self, value: int ) -> None:
        self.g = value / 255

    @property
    def b_8( self ) -> int:
        return round( self.b * 255 )

    @b_8.setter
    def b_8( self, value: int ) -> None:
        self.b = value / 255

    @property
    def a_8( self ) -> int:
        return round( self.a * 255 )

    @a_8.setter
    def a_8( self, value: int ) -> None:
        self.a = value / 255

    @property
    def chroma( self ) -> float:
        M = max( self.r, self.g, self.b )
        m = min( self.r, self.g, self.b )
        return M - m

    @property
    def luma( self ) -> float:
        return 0.299 * self.r + 0.587 * self.g + 0.114 * self.b

    @property
    def rgba( self ) -> Tuple[int, int, int, int]:
        return (self.r_8, self.g_8, self.b_8, self.a_8)

    def set_rgb( self, r_8: int, g_8: int, b_8: int ) -> BaseColour:
        self.r_8 = r_8
        self.g_8 = g_8
        self.b_8 = b_8
        return self

    def set_a( self, a_8: int ) -> BaseColour:
        self.a_8 = a_8
        return self

    def set_rgba( self, r_8: int, g_8: int, b_8: int, a_8: int ) -> BaseColour:
        self.r_8 = r_8
        self.g_8 = g_8
        self.b_8 = b_8
        self.a_8 = a_8
        return self

    def clone_data( self, source: BaseColour ) -> BaseColour:
        self.r_8 = source.r_8
        self.g_8 = source.g_8
        self.b_8 = source.b_8
        self.a_8 = source.a_8
        return self

    @property
    def repr( self ) -> str:
        return f"#{self.r_8:02X}{self.g_8:02X}{self.b_8:02X}{self.a_8:02X}"

    def ansi_format( self, text: Optional[str] = None ) -> str:
        from mrcrowbar.ansi import format_string

        if text is None:
            text = f" {self.repr} "
        colour = White() if self.luma < 0.5 else Black()
        return format_string( text, colour, self )

    def print( self, text: Optional[str] = None ) -> None:
        print( self.ansi_format( text ) )

    def __eq__( self, other: Any ) -> bool:
        if isinstance( other, BaseColour ):
            return (
                (self.r_8 == other.r_8)
                and (self.g_8 == other.g_8)
                and (self.b_8 == other.b_8)
                and (self.a_8 == other.a_8)
            )
        return False


class White( BaseColour ):
    r = 1.0
    g = 1.0
    b = 1.0


class Black( BaseColour ):
    r = 0.0
    g = 0.0
    b = 0.0


class Transparent( BaseColour ):
    a = 0.0


ColourType = Optional[
    Union[int, Tuple[int, int, int], Tuple[int, int, int, int], BaseColour]
]


def normalise_rgba( raw_colour: ColourType ) -> Tuple[int, int, int, int]:
    if raw_colour is None:
        return (0, 0, 0, 0)
    elif isinstance( raw_colour, BaseColour ):
        return raw_colour.rgba
    elif isinstance( raw_colour, tuple ) and len( raw_colour ) == 3:
        return (raw_colour[0], raw_colour[1], raw_colour[2], 255)
    elif isinstance( raw_colour, tuple ) and len( raw_colour ) == 4:
        return (raw_colour[0], raw_colour[1], raw_colour[2], raw_colour[3])
    raise ValueError(
        "raw_colour must be either None, a BaseColour, or a tuple (RGB/RGBA)"
    )


def to_palette_bytes(
    palette: Sequence[BaseColour], stride: int = 3, order: Sequence[int] = (0, 1, 2)
) -> bytes:
    assert stride >= max( order )
    assert min( order ) >= 0
    blanks = tuple( (0 for _ in range( stride - max( order ) - 1 )) )

    def channel( colour: BaseColour, order: int ) -> int:
        if order == 0:
            return colour.r_8
        elif order == 1:
            return colour.g_8
        elif order == 2:
            return colour.b_8
        elif order == 3:
            return colour.a_8
        raise ValueError( f"{order} is not a valid order" )

    return bytes(
        itertools.chain(
            *(tuple( (channel( c, o ) for o in order) ) + blanks for c in palette)
        )
    )


def from_palette_bytes(
    palette_bytes: BytesReadType,
    stride: int = 3,
    order: Union[Tuple[int], Tuple[int, int, int], Tuple[int, int, int, int]] = (
        0,
        1,
        2,
    ),
) -> List[BaseColour]:
    assert stride >= max( order )
    assert min( order ) >= 0
    assert len( order ) in (1, 3, 4)
    result: List[BaseColour] = []
    for i in range( math.floor( len( palette_bytes ) / stride ) ):
        if len( order ) == 1:
            result.append(
                BaseColour().set_rgb(
                    palette_bytes[stride * i + order[0]],
                    palette_bytes[stride * i + order[0]],
                    palette_bytes[stride * i + order[0]],
                )
            )
        elif len( order ) == 3:
            result.append(
                BaseColour().set_rgb(
                    palette_bytes[stride * i + order[0]],
                    palette_bytes[stride * i + order[1]],
                    palette_bytes[stride * i + order[2]],
                )
            )
        elif len( order ) == 4:
            result.append(
                BaseColour().set_rgba(
                    palette_bytes[stride * i + order[0]],
                    palette_bytes[stride * i + order[1]],
                    palette_bytes[stride * i + order[2]],
                    palette_bytes[stride * i + order[3]],
                )
            )
    return result


def mix( a: Union[int, float], b: Union[int, float], alpha: float ) -> float:
    return (b - a) * alpha + a


def mix_line( points: Sequence[Union[int, float]], alpha: float ) -> float:
    count = len( points ) - 1
    if alpha == 1:
        return points[-1]
    return mix(
        points[math.floor( alpha * count )],
        points[math.floor( alpha * count ) + 1],
        math.fmod( alpha * count, 1 ),
    )


def mix_colour( col_a: BaseColour, col_b: BaseColour, alpha: float ) -> BaseColour:
    r = round( mix( col_a.r_8, col_b.r_8, alpha ) )
    g = round( mix( col_a.g_8, col_b.g_8, alpha ) )
    b = round( mix( col_a.b_8, col_b.b_8, alpha ) )
    a = round( mix( col_a.a_8, col_b.a_8, alpha ) )

    return BaseColour().set_rgb( r, g, b ).set_a( a )


def mix_colour_line( points: Sequence[BaseColour], alpha: float ) -> BaseColour:
    count = len( points ) - 1
    if alpha == 1:
        return points[-1]
    return mix_colour(
        points[math.floor( alpha * count )],
        points[math.floor( alpha * count ) + 1],
        math.fmod( alpha * count, 1 ),
    )


TEST_PALETTE_POINTS: List[BaseColour] = [
    BaseColour().set_rgb( 0x00, 0x00, 0x00 ),
    BaseColour().set_rgb( 0x70, 0x34, 0x00 ),
    BaseColour().set_rgb( 0xe8, 0x6c, 0x00 ),
    BaseColour().set_rgb( 0xf0, 0xb0, 0x40 ),
    BaseColour().set_rgb( 0xf8, 0xec, 0xa0 ),
]


def gradient_to_palette(
    points: Sequence[BaseColour] = TEST_PALETTE_POINTS, size: int = 256
) -> List[BaseColour]:
    return [mix_colour_line( points, i / max( size - 1, 1 ) ) for i in range( size )]


TEST_PALETTE = gradient_to_palette()
