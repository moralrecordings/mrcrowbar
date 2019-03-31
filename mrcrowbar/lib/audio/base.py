from mrcrowbar import models as mrc
from mrcrowbar import ansi, encoding, sound

from array import array


class Wave( mrc.View ):
    def __init__( self, parent, source, channels, sample_rate, format_type, field_size, signedness, endian ):
        """View for for accessing PCM wave audio.

        parent
            Parent object.

        source
            Raw audio data, in bytes.

        channels
            Number of audio channels.

        sample_rate
            Playback sample rate, in Hz.

        format_type
            Python type corresponding to the sample format. Either int or float.

        field_size
            Number of bytes per sample.

        signedness
            Signedness of sample format. Either 'signed' or 'unsigned'.

        endian
            Endianness of sample format. Either 'big', 'little' or None.
        """
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
        return sound.normalise_audio( self.source, self.format_type, self.field_size, self.signedness, self.endian )

    def ansi_format( self, width=64, height=12 ):
        audio = self.normalised()
        result = []
        for line in ansi.format_bar_graph_iter( audio, width=width, height=height, y_min=-1, y_max=1 ):
            result.append( '{}\n'.format( line ) )
        return ''.join( result )

    def print( self, *args, **kwargs ):
        """Print the graphical version of the results produced by ansi_format()."""
        print( self.ansi_format( *args, **kwargs ) )

    def play( self, interpolation=sound.AudioInterpolation.LINEAR ):
        return sound.play_pcm( self.source, self.channels, self.sample_rate,
                               self.format_type, self.field_size, self.signedness,
                               self.endian, interpolation=interpolation )

