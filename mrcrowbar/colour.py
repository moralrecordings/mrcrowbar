import math

class BaseColour( object ):
    r_8 = 0
    g_8 = 0
    b_8 = 0
    a_8 = 255

    @property
    def r( self ) -> float:
        return self.r_8/255

    @property
    def g( self ) -> float:
        return self.g_8/255

    @property
    def b( self ) -> float:
        return self.b_8/255

    @property
    def a( self ) -> float:
        return self.a_8/255
 
    @property
    def chroma( self ) -> float:
        M = max( self.r, self.g, self.b )
        m = min( self.r, self.g, self.b )
        return M-m

    @property
    def luma( self ) -> float:
        return 0.299*self.r + 0.587*self.g + 0.114*self.b

    @property
    def rgba( self ):
        return (self.r_8, self.g_8, self.b_8, self.a_8)

    def set_rgb( self, r_8, g_8, b_8 ):
        self.r_8 = r_8
        self.g_8 = g_8
        self.b_8 = b_8
        return self

    def set_a( self, a_8 ):
        self.a_8 = a_8
        return self

    def set_rgba( self, r_8, g_8, b_8, a_8 ):
        self.r_8 = r_8
        self.g_8 = g_8
        self.b_8 = b_8
        self.a_8 = a_8
        return self

    def clone_data( self, source ):
        assert isinstance( source, BaseColour )
        self.r_8 = source.r_8
        self.g_8 = source.g_8
        self.b_8 = source.b_8
        self.a_8 = source.a_8

    @property
    def repr( self ):
        return '#{:02X}{:02X}{:02X}{:02X}'.format( self.r_8, self.g_8, self.b_8, self.a_8 )

    def ansi_format( self, text=None ):
        from mrcrowbar.ansi import format_string
        if text is None:
            text = ' {} '.format( self.repr )
        colour = White() if self.luma < 0.5 else Black()
        return format_string( text, colour, self )

    def print( self, *args, **kwargs ):
        print( self.ansi_format( *args, **kwargs ) )

    def __eq__( self, other ):
        return (self.r_8 == other.r_8) and (self.g_8 == other.g_8) and (self.b_8 == other.b_8) and (self.a_8 == other.a_8)


class White( BaseColour ):
    r_8 = 255
    g_8 = 255
    b_8 = 255


class Black( BaseColour ):
    r_8 = 0
    g_8 = 0
    b_8 = 0


class Transparent( BaseColour ):
    a_8 = 0


def normalise_rgba( raw_colour ):
    if raw_colour is None:
        return (0, 0, 0, 0)
    elif hasattr( raw_colour, 'rgba' ):
        return raw_colour.rgba
    elif len( raw_colour ) == 3:
        return (raw_colour[0], raw_colour[1], raw_colour[2], 255)
    elif len( raw_colour ) == 4:
        return (raw_colour[0], raw_colour[1], raw_colour[2], raw_colour[3])
    raise ValueError( 'raw_colour must be either None, a BaseColour, or a tuple (RGB/RGBA)' )


def to_palette_bytes( palette, stride=3, order=(0, 1, 2) ):
    assert stride >= max( order )
    assert min( order ) >= 0
    blanks = tuple((0 for i in range( stride-max( order )-1 )))
    ORDER_MAP = {0: 'r_8', 1: 'g_8', 2: 'b_8', 3: 'a_8'}
    channel = lambda c, o: getattr( c, ORDER_MAP[o] )
    return bytes( itertools.chain( *(tuple((channel( c, o ) for o in order))+blanks for c in palette) ) )


def from_palette_bytes( palette_bytes, stride=3, order=(0, 1, 2) ):
    assert stride >= max( order )
    assert min( order ) >= 0
    assert len( order ) in (1, 3, 4)
    result = []
    for i in range( math.floor( len( palette_bytes )/stride ) ):
        if len( order ) == 1:
            colour = BaseColour().set_rgb( palette_bytes[stride*i+order[0]], palette_bytes[stride*i+order[0]], palette_bytes[stride*i+order[0]] )
        elif len( order ) == 3:
            colour = BaseColour().set_rgb( palette_bytes[stride*i+order[0]], palette_bytes[stride*i+order[1]], palette_bytes[stride*i+order[2]] )
        elif len( order ) == 4:
            colour = BaseColour().set_rgba( palette_bytes[stride*i+order[0]], palette_bytes[stride*i+order[1]], palette_bytes[stride*i+order[2]], palette_bytes[stride*i+order[3]] )
        result.append( colour )
    return result


def mix( a, b, alpha ):
    return (b-a)*alpha + a


def mix_line( points, alpha ):
    count = len( points ) - 1
    if alpha == 1:
        return points[-1]
    return mix(
        points[math.floor( alpha*count )],
        points[math.floor( alpha*count )+1],
        math.fmod( alpha*count, 1 )
    )


def mix_colour( col_a, col_b, alpha ):
    r = round( mix( col_a.r_8, col_b.r_8, alpha ) )
    g = round( mix( col_a.g_8, col_b.g_8, alpha ) )
    b = round( mix( col_a.b_8, col_b.b_8, alpha ) )
    a = round( mix( col_a.a_8, col_b.a_8, alpha ) )

    return BaseColour().set_rgb( r, g, b ).set_a( a )


def mix_colour_line( points, alpha ):
    count = len( points ) - 1
    if alpha == 1:
        return points[-1]
    return mix_colour(
        points[math.floor( alpha*count )],
        points[math.floor( alpha*count )+1],
        math.fmod( alpha*count, 1 )
    )

TEST_PALETTE_POINTS = [
    BaseColour().set_rgb( 0x00, 0x00, 0x00 ),
    BaseColour().set_rgb( 0x70, 0x34, 0x00 ),
    BaseColour().set_rgb( 0xe8, 0x6c, 0x00 ),
    BaseColour().set_rgb( 0xf0, 0xb0, 0x40 ),
    BaseColour().set_rgb( 0xf8, 0xec, 0xa0 ),
]

def gradient_to_palette( points=TEST_PALETTE_POINTS, size=256 ):
    return [mix_colour_line( points, i/max(size-1, 1) ) for i in range( size )]


TEST_PALETTE = gradient_to_palette()
