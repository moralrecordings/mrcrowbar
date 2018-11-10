from mrcrowbar import models as mrc
from mrcrowbar import utils, encoding

from array import array
from enum import IntEnum

try:
    import pyaudio
except ImportError:
    pyaudio = None

class AudioInterpolation( IntEnum ):
    #: Perform no audio interpolation and let PortAudio sort it out. 
    #: (Sounds like CUBIC)
    NONE = 0
    #: Perform sharp linear interpolation between samples. 
    #: This is the algorithm used by most early DSPs, such as the one in the original 
    #: Sound Blaster, and has a pleasing brightness and crispness to it.
    LINEAR = 1
    #: Perform sharp step interpolation between samples.
    #: I'm sure if you go nasty enough, you could find a DSP that sounds like this.
    #: This sounds like LINEAR, except with more distortion.
    STEP = 2
    #: Perform smooth cubic spline interpolation between samples. 
    #: This algorithm is used by modern upsampling engines, as it doesn't introduce
    #: high-frequency noise and supposedly sounds more accurate. 
    CUBIC = 3

PLAYBACK_BUFFER = 4096
RESAMPLE_RATE = 44100
PYAUDIO_NORMALISE_TYPE = 'paFloat32'


def normalise_audio( source, format_type, field_size, signedness, endian ):
    if format_type == float:
        return array( 'f', encoding.unpack_array( (format_type, field_size, signedness, endian), source ) )
    elif format_type == int:
        divisor = 1 << (field_size*8-1)

        if signedness == 'signed':
            return array( 'f', (float( x )/divisor for x in encoding.unpack_array( (format_type, field_size, signedness, endian), source )) )
        else:
            return array( 'f', (float( x-divisor )/divisor for x in encoding.unpack_array( (format_type, field_size, signedness, endian), source )) )

    return array( 'f' )


def resample_audio( norm_source, sample_rate, interpolation ):
    if sample_rate == 0:
        return array( 'f' )

    samp_len = len( norm_source )-1
    new_len = RESAMPLE_RATE*samp_len//sample_rate

    if interpolation == AudioInterpolation.LINEAR:
        return array( 'f', (( 
            (norm_source[sample_rate*i//RESAMPLE_RATE] + (
                (sample_rate*i % RESAMPLE_RATE)/RESAMPLE_RATE
            )*(
                norm_source[(sample_rate*i//RESAMPLE_RATE)+1]-
                norm_source[sample_rate*i//RESAMPLE_RATE]
            )) 
        ) for i in range( new_len )) )
    elif interpolation == AudioInterpolation.STEP:
        return array( 'f', (
            norm_source[sample_rate*i//RESAMPLE_RATE]
            for i in range( new_len )) )
    return array( 'f' )


class Wave( mrc.View ):
    def __init__( self, parent, source, channels, sample_rate, format_type, field_size, signedness, endian ):
        super().__init__( parent )
        self._source = source
        self._channels = channels
        self._sample_rate = sample_rate
        self._format_type = format_type
        self._field_size = field_size
        self._signedness = signedness
        self._endian = endian

    source = mrc.view_property( '_source' )
    channels = mrc.view_property( '_channels' )
    sample_rate = mrc.view_property( '_sample_rate' )
    format_type = mrc.view_property( '_format_type' )
    field_size = mrc.view_property( '_field_size' )
    signedness = mrc.view_property( '_signedness' )
    endian = mrc.view_property( '_endian' )

    def normalised( self ):
        return normalise_audio( self.source, self.format_type, self.field_size, self.signedness, self.endian )

    def ansi_format( self, width=64, height=12 ):
        audio = self.normalised()
        result = []
        for line in utils.ansi_format_bar_graph_iter( audio, width=width, height=height, y_min=-1, y_max=1 ):
            result.append( '{}\n'.format( line ) )
        return ''.join( result )

    def print( self, *args, **kwargs ):
        """Print the graphical version of the results produced by ansi_format()."""
        print( self.ansi_format( *args, **kwargs ) )

    def play( self, interpolation=AudioInterpolation.LINEAR ):
        if not pyaudio:
            raise ImportError( 'pyaudio must be installed for audio playback support (see https://people.csail.mit.edu/hubert/pyaudio)' )
        audio = pyaudio.PyAudio()
        format = getattr( pyaudio, PYAUDIO_NORMALISE_TYPE )
        rate = self.sample_rate

        samp_array = self.normalised()
        samp_array.append( 0.0 )

        if interpolation != AudioInterpolation.NONE:
            rate = RESAMPLE_RATE
                
            samp_len = len( samp_array )
            new_len = RESAMPLE_RATE*samp_len//self.sample_rate if self.sample_rate else 0

            samp_array = resample_audio( samp_array, self.sample_rate, interpolation )
            
        padding = -(len( samp_array ) % -PLAYBACK_BUFFER)
        samp_array.extend( (0.0,)*padding )
           
        stream = audio.open( 
            format=format,
            channels=self.channels,
            rate=rate,
            output=True
        )
        stream.write( samp_array.tobytes() )
        stream.stop_stream()
        stream.close()
