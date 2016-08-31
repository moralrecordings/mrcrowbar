from mrcrowbar import models as mrc
from mrcrowbar import utils

from array import array

import pyaudio

SAMPLE_WIDTH_UINT8 = (pyaudio.paUInt8, b'\x80')
SAMPLE_WIDTH_INT8 = (pyaudio.paInt8, b'\x00')
SAMPLE_WIDTH_INT16_LE = (pyaudio.paInt16, b'\x00\x00')
#SAMPLE_WIDTH_INT24_LE = (pyaudio.paInt24, b'\x00\x00\x00')
SAMPLE_WIDTH_INT32_LE = (pyaudio.paInt32, b'\x00\x00\x00\x00')

AUDIO_INTERPOLATION_NONE = 0
AUDIO_INTERPOLATION_LINEAR = 1
AUDIO_INTERPOLATION_SQUARE = 2
AUDIO_INTERPOLATION_CUBIC = 3

PLAYBACK_BUFFER = 4096
RESAMPLE_RATE = 44100



class Wave( mrc.View ):
    def __init__( self, parent, source, channels, sample_width, sample_rate ):
        super( Wave, self ).__init__( parent )
        self._source = source
        self._channels = channels
        self._sample_width = sample_width
        self._sample_rate = sample_rate

    def play( self, interpolation=AUDIO_INTERPOLATION_LINEAR ):
        audio = pyaudio.PyAudio()
        data = b''
        format=self._sample_width[0]
        rate = self._sample_rate

        if interpolation == AUDIO_INTERPOLATION_NONE:
            padding = self._sample_width[1]*(2*PLAYBACK_BUFFER-(len( self._source ) % PLAYBACK_BUFFER))
            data = self._source+padding
        else:
            format = SAMPLE_WIDTH_INT16_LE[0]
            rate=RESAMPLE_RATE

            samp_array = [0.0]
            if self._sample_width == SAMPLE_WIDTH_UINT8:
                samp_array = [float( x-128 )/128 for x in array( 'B', self._source )] + [0.0]
            elif self._sample_width == SAMPLE_WIDTH_INT8:
                samp_array = [float( x )/128 for x in array( 'b', self._source )] + [0.0]
            elif self._sample_width == SAMPLE_WIDTH_INT16_LE:
                samp_array = [float( x )/32768 for x in array( 'h', self._source )] + [0.0]
            elif self._sample_width == SAMPLE_WIDTH_INT32_LE:
                samp_array = [float( x )/2147483648 for x in array( 'l', self._source )] + [0.0]
                
            samp_len = len( self._source )
            new_len = RESAMPLE_RATE*samp_len//self._sample_rate

            padding = SAMPLE_WIDTH_INT16_LE[1]*(2*PLAYBACK_BUFFER-(new_len % PLAYBACK_BUFFER))
            if interpolation == AUDIO_INTERPOLATION_LINEAR:
                data = array( 'h', (int( 
                    32768*(samp_array[self._sample_rate*i//RESAMPLE_RATE] + (
                        (self._sample_rate*i % RESAMPLE_RATE)/RESAMPLE_RATE
                    )*(
                        samp_array[(self._sample_rate*i//RESAMPLE_RATE)+1]-
                        samp_array[self._sample_rate*i//RESAMPLE_RATE]
                    )) 
                ) for i in range( new_len )) ).tobytes() + padding
            elif interpolation == AUDIO_INTERPOLATION_SQUARE:
                data = array( 'h', (int(
                    32768*samp_array[self._sample_rate*i//RESAMPLE_RATE]
                ) for i in range( new_len )) ).tobytes() + padding
           
        stream = audio.open( 
            format=format,
            channels=self._channels,
            rate=rate,
            output=True
        )
        stream.write( data )
        stream.stop_stream()
        stream.close()
