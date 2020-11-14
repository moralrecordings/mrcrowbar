import math

from mrcrowbar import colour, statistics
from mrcrowbar.common import is_bytes, bounds

#: Container for ANSI escape sequences for text formatting
ANSI_FORMAT_BASE = '\x1b[{}m'
#: ANSI escape sequence for resetting the colour settings to the default.
ANSI_FORMAT_RESET_CMD = '0'
ANSI_FORMAT_RESET = ANSI_FORMAT_BASE.format( ANSI_FORMAT_RESET_CMD )
#: ANSI escape sequence for setting the foreground colour (24-bit).
ANSI_FORMAT_FOREGROUND_CMD = '38;2;{};{};{}'
#: ANSI escape sequence for setting the background colour (24-bit).
ANSI_FORMAT_BACKGROUND_CMD = '48;2;{};{};{}'
#: ANSI escape sequence for setting the foreground colour (xterm).
ANSI_FORMAT_FOREGROUND_XTERM_CMD = '38;5;{}'
#: ANSI escape sequence for setting the background colour (xterm).
ANSI_FORMAT_BACKGROUND_XTERM_CMD = '48;5;{}'
#: ANSI escape sequence for bold text
ANSI_FORMAT_BOLD_CMD = '1'
#: ANSI escape sequence for faint text
ANSI_FORMAT_FAINT_CMD = '2'
#: ANSI escape sequence for bold text
ANSI_FORMAT_ITALIC_CMD = '3'
#: ANSI escape sequence for bold text
ANSI_FORMAT_UNDERLINE_CMD = '4'
#: ANSI escape sequence for bold text
ANSI_FORMAT_BLINK_CMD = '5'
#: ANSI escape sequence for inverted text
ANSI_FORMAT_INVERTED_CMD = '7'

#: Container for ANSI escape sequence screen erasing
ANSI_ERASE_BASE = '\x1b[{}J'
#: ANSI escape sequence for clearing the visible terminal
ANSI_ERASE_SCREEN = ANSI_ERASE_BASE.format( 2 )
#: ANSI escape sequence for clearing the scrollback of the terminal
ANSI_ERASE_SCROLLBACK = ANSI_ERASE_BASE.format( 3 )

#: ANSI escape sequence to set the cursor position. (1, 1) is the top left.
ANSI_CURSOR_SET_POSITION = '\x1b[{};{}H'
#: ANSI escape sequence to move the cursor up.
ANSI_CURSOR_MOVE_UP = '\x1b[{}A'
#: ANSI escape sequence to move the cursor down.
ANSI_CURSOR_MOVE_DOWN = '\x1b[{}B'
#: ANSI escape sequence to move the cursor forward.
ANSI_CURSOR_MOVE_FORWARD = '\x1b[{}C'
#: ANSI escape sequence to move the cursor backward.
ANSI_CURSOR_MOVE_BACKWARD = '\x1b[{}D'

#: Unicode representation of a vertical bar graph.
BAR_VERT   = u' ▁▂▃▄▅▆▇█'
#: Unicode representation of a horizontal bar graph.
BAR_HORIZ  = u' ▏▎▍▌▋▊▉█'


BYTE_GLYPH_MAP = """ ☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ """

BYTE_COLOUR_MAP = (12,) + (14,)*32 + (11,)*94 + (14,)*128 + (12,)



def format_escape( foreground=None, background=None, bold=False, faint=False,
    italic=False, underline=False, blink=False, inverted=False ):
    """Returns the ANSI escape sequence to set character formatting.

    foreground
        Foreground colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    background
        Background colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    bold
        Enable bold text (default: False)

    faint
        Enable faint text (default: False)

    italic
        Enable italic text (default: False)

    underline
        Enable underlined text (default: False)

    blink
        Enable blinky text (default: False)

    inverted
        Enable inverted text (default: False)
    """
    fg_format = None
    if isinstance( foreground, int ):
        fg_format = ANSI_FORMAT_FOREGROUND_XTERM_CMD.format( foreground )
    else:
        fg_rgba = colour.normalise_rgba( foreground )
        if fg_rgba[3] != 0:
            fg_format = ANSI_FORMAT_FOREGROUND_CMD.format( *fg_rgba[:3] )

    bg_format = None
    if isinstance( background, int ):
        bg_format = ANSI_FORMAT_BACKGROUND_XTERM_CMD.format( background )
    else:
        bg_rgba = colour.normalise_rgba( background )
        if bg_rgba[3] != 0:
            bg_format = ANSI_FORMAT_BACKGROUND_CMD.format( *bg_rgba[:3] )

    colour_format = []
    if fg_format is not None:
        colour_format.append( fg_format )
    if bg_format is not None:
        colour_format.append( bg_format )
    if bold:
        colour_format.append( ANSI_FORMAT_BOLD_CMD )
    if faint:
        colour_format.append( ANSI_FORMAT_FAINT_CMD )
    if italic:
        colour_format.append( ANSI_FORMAT_ITALIC_CMD )
    if underline:
        colour_format.append( ANSI_FORMAT_UNDERLINE_CMD )
    if blink:
        colour_format.append( ANSI_FORMAT_BLINK_CMD )
    if inverted:
        colour_format.append( ANSI_FORMAT_INVERTED_CMD )

    colour_format = ANSI_FORMAT_BASE.format( ';'.join( colour_format ) )
    return colour_format


def format_string( string, foreground=None, background=None, reset=True, bold=False,
    faint=False, italic=False, underline=False, blink=False, inverted=False ):
    """Returns a Unicode string formatted with an ANSI escape sequence.

    string
        String to format

    foreground
        Foreground colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    background
        Background colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    reset
        Reset the formatting at the end (default: True)

    bold
        Enable bold text (default: False)

    faint
        Enable faint text (default: False)

    italic
        Enable italic text (default: False)

    underline
        Enable underlined text (default: False)

    blink
        Enable blinky text (default: False)

    inverted
        Enable inverted text (default: False)
    """
    colour_format = format_escape( foreground, background, bold, faint,
                                        italic, underline, blink, inverted )
    reset_format = '' if not reset else ANSI_FORMAT_RESET

    return '{}{}{}'.format( colour_format, string, reset_format )


def format_pixels( top, bottom, reset=True, repeat=1 ):
    """Return the ANSI escape sequence to render two vertically-stacked pixels as a
    single monospace character.

    top
        Top colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    bottom
        Bottom colour to use. Accepted types: None, int (xterm
        palette ID), tuple (RGB, RGBA), Colour

    reset
        Reset the formatting at the end (default: True)

    repeat
        Number of horizontal pixels to render (default: 1)
    """
    top_src = None
    if isinstance( top, int ):
        top_src = top
    else:
        top_rgba = colour.normalise_rgba( top )
        if top_rgba[3] != 0:
            top_src = top_rgba

    bottom_src = None
    if isinstance( bottom, int ):
        bottom_src = bottom
    else:
        bottom_rgba = colour.normalise_rgba( bottom )
        if bottom_rgba[3] != 0:
            bottom_src = bottom_rgba

    # short circuit for empty pixel
    if (top_src is None) and (bottom_src is None):
        return ' '*repeat 

    string = '▀'*repeat;
    colour_format = []

    if top_src == bottom_src:
        string = '█'*repeat
    elif (top_src is None) and (bottom_src is not None):
        string = '▄'*repeat

    if (top_src is None) and (bottom_src is not None):
        if isinstance( bottom_src, int ):
            colour_format.append( ANSI_FORMAT_FOREGROUND_XTERM_CMD.format( bottom_src ) )
        else:
            colour_format.append( ANSI_FORMAT_FOREGROUND_CMD.format( *bottom_src[:3] ) )
    else:
        if isinstance( top_src, int ):
            colour_format.append( ANSI_FORMAT_FOREGROUND_XTERM_CMD.format( top_src ) )
        else:
            colour_format.append( ANSI_FORMAT_FOREGROUND_CMD.format( *top_src[:3] ) )

    if top_src is not None and bottom_src is not None and top_src != bottom_src:
        if isinstance( top_src, int ):
            colour_format.append( ANSI_FORMAT_BACKGROUND_XTERM_CMD.format( bottom_src ) )
        else:
            colour_format.append( ANSI_FORMAT_BACKGROUND_CMD.format( *bottom_src[:3] ) )

    colour_format = ANSI_FORMAT_BASE.format( ';'.join( colour_format ) )
    reset_format = '' if not reset else ANSI_FORMAT_RESET

    return '{}{}{}'.format( colour_format, string, reset_format )


def format_bar_graph_iter( data, width=64, height=12, y_min=None, y_max=None ):
    if width <= 0:
        raise ValueError( 'Width of the graph must be greater than zero' )
    if height % 2:
        raise ValueError( 'Height of the graph must be a multiple of 2' )
    if y_min is None:
        y_min = min( data )
    y_min = min( y_min, 0 )
    if y_max is None:
        y_max = max( data )
    y_max = max( y_max, 0 )

    # determine top-left of vertical origin
    if y_max <= 0:
        top_height, bottom_height = 0, height
        y_scale = 8*height/y_min
    elif y_min >= 0:
        top_height, bottom_height = height, 0
        y_scale = 8*height/y_max
    else:
        top_height, bottom_height = height//2, height//2
        y_scale = 8*height/(2*max( abs( y_min ), abs( y_max ) ))

    # precalculate sizes
    sample_count = len( data )
    if sample_count == 0:
        # empty graph
        samples = [(0, 0) for x in range( width )]
    else:
        if sample_count <= width:
            sample_ranges = [(math.floor( i*sample_count/width ), math.floor( i*sample_count/width )+1) for i in range( width )]
        else:
            sample_ranges = [(round( i*sample_count/width ), round( (i+1)*sample_count/width )) for i in range( width )]
        samples = [(round( min( data[x[0]:x[1]] )*y_scale ), round( max( data[x[0]:x[1]] )*y_scale )) for x in sample_ranges]

    for y in range( top_height, 0, -1 ):
        result = []
        for _, value in samples:
            if value // 8 >= y:
                result.append( BAR_VERT[8] )
            elif value // 8 == y-1:
                result.append( BAR_VERT[value % 8] )
            else:
                result.append( BAR_VERT[0] )
        yield ''.join( result )

    for y in range( 1, bottom_height+1, 1 ):
        result = []
        for value, _ in samples:
            if -value // 8 >= y:
                result.append( BAR_VERT[8] )
            elif -value // 8 == y-1:
                result.append( format_string( BAR_VERT[8-((-value) % 8)], inverted=True ) )
            else:
                result.append( BAR_VERT[0] )
        yield ''.join( result )


def format_image_iter( data_fetch, x_start=0, y_start=0, width=32, height=32, frame=0, columns=1, downsample=1 ):
    """Return the ANSI escape sequence to render a bitmap image.

    data_fetch
        Function that takes three arguments (x position, y position, and frame) and returns
        a Colour corresponding to the pixel stored there, or Transparent if the requested 
        pixel is out of bounds.

    x_start
        Offset from the left of the image data to render from. Defaults to 0.

    y_start
        Offset from the top of the image data to render from. Defaults to 0.

    width
        Width of the image data to render. Defaults to 32.

    height
        Height of the image data to render. Defaults to 32.

    frame
        Single frame number/object, or a list to render in sequence. Defaults to frame 0.

    columns
        Number of frames to render per line (useful for printing tilemaps!). Defaults to 1.

    downsample
        Shrink larger images by printing every nth pixel only. Defaults to 1.
    """
    frames = []
    try:
        frame_iter = iter( frame )
        frames = [f for f in frame_iter]
    except TypeError:
        frames = [frame]

    rows = math.ceil( len( frames )/columns )
    for r in range( rows ):
        for y in range( 0, height, 2*downsample ):
            result = []
            for c in range( min( (len( frames )-r*columns), columns ) ):
                row = []
                for x in range( 0, width, downsample ):
                    fr = frames[r*columns + c]
                    c1 = data_fetch( x_start+x, y_start+y, fr )
                    c2 = data_fetch( x_start+x, y_start+y+downsample, fr )
                    row.append( (c1, c2) )
                prev_pixel = None
                pointer = 0
                while pointer < len( row ):
                    start = pointer
                    pixel = row[pointer]
                    while pointer < len( row ) and (row[pointer] == pixel):
                        pointer += 1
                    result.append( format_pixels( pixel[0], pixel[1], repeat=pointer-start ) )
            yield ''.join( result )
    return


BYTE_ESCAPE_MAP = [format_escape( x ) for x in BYTE_COLOUR_MAP]

def format_hexdump_line( source, offset, end=None, major_len=8, minor_len=4, colour=True,
        prefix='', highlight_addr=None, highlight_map=None, address_base_offset=0, show_offsets=True, show_glyphs=True ):
    def get_colour( index ):
        if colour:
            if highlight_map:
                if index in highlight_map:
                    return format_escape( highlight_map[index] )
            return BYTE_ESCAPE_MAP[source[index]]
        return ''

    def get_glyph():
        b = source[offset:min( offset+major_len*minor_len, end )]
        letters = []
        prev_colour = None
        for i in range( offset, min( offset+major_len*minor_len, end ) ):
            new_colour = get_colour( i )
            if prev_colour != new_colour:
                letters.append( new_colour )
                prev_colour = new_colour
            letters.append( BYTE_GLYPH_MAP[source[i]] )
        if colour:
            letters.append( ANSI_FORMAT_RESET )
        return ''.join( letters )

    if end is None:
        end = len( source )

    line = []
    if show_offsets:
        digits = ('{}{:0'+str( max( 8, math.floor( math.log( end+address_base_offset )/math.log( 16 ) ) ) )+'x}').format( prefix, offset+address_base_offset )
        line = [format_string( digits, highlight_addr ), ' │  ']

    prev_colour = None
    for major in range( major_len ):
        for minor in range( minor_len ):
            suboffset = offset+major*minor_len+minor
            if suboffset >= end:
                line.append( '   ' )
                continue
            new_colour = get_colour( suboffset )
            if prev_colour != new_colour:
                line.append( new_colour )
                prev_colour = new_colour
            line.append( '{:02x} '.format( source[suboffset] ) )

        line.append( ' ' )

    if colour:
        line.append( ANSI_FORMAT_RESET )

    if show_glyphs:
        line.append( '│ {}'.format( get_glyph() ) )
    return ''.join( line )


def format_histogram_line( buckets, palette=None ):
    if palette is None:
        palette = colour.TEST_PALETTE
    total = sum( buckets )
    floor = math.log( 1/(8*len( buckets )) )

    buckets_log = [-floor + max( floor, math.log( b/total ) ) if b else None for b in buckets]
    limit = max( [b for b in buckets_log if b is not None] )
    buckets_norm = [round( 255*(b/limit) ) if b is not None else None for b in buckets_log]
    result = []
    for b in buckets_norm:
        if b is not None:
            result.append( format_string( '█', palette[b] ) )
        else:
            result.append( ' ' )
    return ''.join( result )


def format_histdump_line( source, offset, length=None, end=None, width=64, address_base_offset=0, palette=None ):
    if length is not None:
        data = source[offset:offset+length]
    else:
        data = source[offset:]
    end = end if end else len( source )
    if palette is None:
        palette = colour.TEST_PALETTE

    digits = ('{:0'+str( max( 8, math.floor( math.log( end+address_base_offset )/math.log( 16 ) ) ) )+'x}').format( offset+address_base_offset )
    stat = statistics.Stats(data)
    return ('{} │ {} │ {:.10f}').format( digits, format_histogram_line( stat.histogram( width ), palette ), stat.entropy )

HIGHLIGHT_COLOUR = 9

class HexdumpHighlightBuffer( object ):
    def __init__( self, source, start=None, end=None, length=None, major_len=8, minor_len=4, colour=True, address_base=None, before=2, after=2, title=None ):
        assert is_bytes( source )
        self.source = source
        self.start, self.end = bounds( start, end, length, len( source ) )

        if len( source ) == 0 or (start == end == 0):
            return
        self.address_base_offset = address_base-start if address_base is not None else 0
        self.major_len = major_len
        self.minor_len = minor_len
        self.colour = colour
        self.before = before
        self.after = after
        self.title = title
        self.stride = minor_len*major_len
        self.lines = []
        self.last_printed = -1
        self.output_buffer = {}
        self.printed = False

    def update( self, marker ):
        cutoff = marker - (marker % self.stride) - self.stride
        if cutoff < self.start:
            return
        keys = [x for x in self.output_buffer.keys() if x <= cutoff and x > self.last_printed]
        keys.sort()
        if keys and not self.printed:
            if self.title:
                self.lines.append( self.title )
            self.printed = True
        for i, key in enumerate( keys ):
            if key - self.last_printed > self.stride:
                self.lines.append( '...' )
            if self.output_buffer[key]:
                self.lines.append( format_hexdump_line( self.source, key, self.end, self.major_len, self.minor_len, self.colour, prefix='!', highlight_addr=HIGHLIGHT_COLOUR, highlight_map=self.output_buffer[key], address_base_offset=self.address_base_offset ) )
            else:
                self.lines.append( format_hexdump_line( self.source, key, self.end, self.major_len, self.minor_len, self.colour, prefix=' ', address_base_offset=self.address_base_offset ) )
            del self.output_buffer[key]
            self.last_printed = key

    def add_span( self, span ):
        block_start = span[0] - (span[0] % self.stride)
        block_end = max( 0, (span[1]-1) - ((span[1]-1) % self.stride) )
        for i in range( block_start, block_end+self.stride, self.stride ):
            if i not in self.output_buffer:
                self.output_buffer[i] = {}
            if self.output_buffer[i] is not None:
                for j in range( max( i, span[0] ), min( i+self.stride, span[1] ) ):
                    self.output_buffer[i][j] = HIGHLIGHT_COLOUR
        for b in [block_start-(x+1)*self.stride for x in range( self.before )]:
            if b not in self.output_buffer and b > self.last_printed:
                self.output_buffer[b] = {}
        for a in [block_end+(x+1)*self.stride for x in range( self.after )]:
            if a not in self.output_buffer:
                self.output_buffer[a] = {}

        self.update( span[0] )

    def flush( self, final=False ):
        if final:
            self.update( len( self.source )+self.stride )
            if self.printed:
                if self.last_printed < len( self.source ) - (len( self.source ) % self.stride):
                    self.lines.append( '...' )
                self.lines.append( '' )
        lines = self.lines
        self.lines = []
        return lines
        return self.pop()

