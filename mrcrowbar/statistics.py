import array
import math
from collections import Counter

class Stats( object ):
    """Helper class for performing some basic statistical analysis on binary data."""

    def __init__( self, buffer ):
        """Generate a Stats instance for a byte string and analyse the data."""
        self.samples = len( buffer )
        # Python's Counter object uses a fast path
        cc = Counter( buffer )

        #: Byte histogram for the source data.
        self.histo = array.array( 'L', (cc.get( i, 0 ) for i in range( 256 )) )

        #: Shanning entropy calculated for the source data.
        self.entropy = 0.0
        for count in self.histo:
            if count != 0:
                cover = count/self.samples
                self.entropy += -cover * math.log2( cover )

    def histogram( self, width ):
        if (256 % width) != 0:
            raise ValueError( 'Width of the histogram must be a divisor of 256' )
        elif (width <= 0):
            raise ValueError( 'Width of the histogram must be greater than zero' )
        elif (width > 256):
            raise ValueError( 'Width of the histogram must be less than or equal to 256' )
        bucket = 256//width
        return [sum( self.histo[i:i+bucket] ) for i in range( 0, 256, bucket )]

    def ansi_format( self, width=64, height=12 ):
        """Return a human readable ANSI-terminal printout of the stats.

        width
            Custom width for the graph (in characters).

        height
            Custom height for the graph (in characters).
        """
        from mrcrowbar.ansi import format_bar_graph_iter
        if (256 % width) != 0:
            raise ValueError( 'Width of the histogram must be a divisor of 256' )
        elif (width <= 0):
            raise ValueError( 'Width of the histogram must be greater than zero' )
        elif (width > 256):
            raise ValueError( 'Width of the histogram must be less than or equal to 256' )
    
        buckets = self.histogram( width )
        result = []
        for line in format_bar_graph_iter( buckets, width=width, height=height ):
            result.append( ' {}\n'.format( line ) )

        result.append( '╘'+('═'*width)+'╛\n' )
        result.append( 'entropy: {:.10f}\n'.format( self.entropy ) )
        result.append( 'samples: {}'.format( self.samples ) )
        return ''.join( result )

    def print( self, *args, **kwargs ):
        """Print the graphical version of the results produced by ansi_format()."""
        print( self.ansi_format( *args, **kwargs ) )

    def __str__( self ):
        return self.ansi_format()

