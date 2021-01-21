from array import array
from enum import IntEnum
import itertools
import math
import time

from mrcrowbar import encoding
from mrcrowbar.common import is_bytes, bounds

try:
    import miniaudio
except ImportError:
    miniaudio = None

RESAMPLE_BUFFER = 4096
NORMALIZE_BUFFER = 8192
RESAMPLE_RATE = 44100
MINIAUDIO_NORMALISE_TYPE = 'FLOAT32'
MINIAUDIO_NORMALISE_SIZE = 4

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


mix_linear = lambda a, b, alpha: (b-a)*alpha+a
mix_step = lambda a, b, alpha: a


def normalise_audio( source, format_type, field_size, signedness, endian, start=None, end=None, length=None ):
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    if format_type == float:
        return array( 'f', encoding.unpack_array( (format_type, field_size, signedness, endian), source[start:end] ) )
    elif format_type == int:
        divisor = 1 << (field_size*8-1)

        if signedness == 'signed':
            return array( 'f', (float( x )/divisor for x in encoding.unpack_array( (format_type, field_size, signedness, endian), source[start:end] )) )
        else:
            return array( 'f', (float( x-divisor )/divisor for x in encoding.unpack_array( (format_type, field_size, signedness, endian), source[start:end] )) )

    return array( 'f' )


def normalise_audio_iter( source, format_type, field_size, signedness, endian, start=None, end=None, length=None, overlap=0, chunk_size=NORMALIZE_BUFFER ):
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    increment = (chunk_size+overlap*field_size)

    for i in range( start, end, chunk_size ):
        yield normalise_audio( source, format_type, field_size, signedness, endian, start=i, end=None, length=increment )


def resample_audio_iter( source, format_type, field_size, signedness, endian, channels, sample_rate, start=None, end=None, length=None, interpolation=AudioInterpolation.LINEAR, output_rate=RESAMPLE_RATE ):
    if sample_rate == 0:
        yield 0.0
        return
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    mixer = mix_linear
    if interpolation == AudioInterpolation.STEP:
        mixer = mix_step

    new_len = (end-start)*output_rate//sample_rate

    src_inc = NORMALIZE_BUFFER
    chunk_size=src_inc*channels
    src_iter = normalise_audio_iter( source, format_type, field_size, signedness, endian, start, end, overlap=channels, chunk_size=chunk_size )
    src = next( src_iter, None )
    src_bound = src_inc

    for index_base in range( 0, new_len ):
        tgt_pos = index_base
        src_pos = sample_rate*tgt_pos/output_rate
        samp_index = math.floor( src_pos ) % src_inc
        alpha = math.fmod( src_pos, 1.0 )

        if src_pos > src_bound:
            src = next( src_iter, None )
            src_bound += src_inc

        if src is None:
            break

        a = 0.0 if samp_index >= len( src ) else src[samp_index]
        b = 0.0 if samp_index+channels >= len( src ) else src[samp_index+channels]

        yield mixer( a, b, alpha )


def play_pcm( source, channels, sample_rate, format_type, field_size, signedness, endian, start=None, end=None, length=None, interpolation=AudioInterpolation.LINEAR ):
    """Play back a byte string as PCM audio.

    source
        The byte string to play.

    channels
        Number of audio channels.

    sample_rate
        Audio sample rate in Hz.

    format_type
        Type of sample encoding; either int or float.

    field_size
        Size of each sample, in bytes.

    signedness
        Signedness of each sample; either 'signed' or 'unsigned'.

    endian
        Endianness of each sample; either 'big', 'little' or None.

    start
        Start offset to read from (default: start).

    end
        End offset to stop reading at (default: end).

    length
        Length to read in (optional replacement for end).

    interpolation
        Interpolation algorithm to use for upsampling. Defaults to AudioInterpolation.LINEAR.
    """
    assert is_bytes( source )
    start, end = bounds( start, end, length, len( source ) )

    if not miniaudio:
        raise ImportError( 'miniaudio must be installed for audio playback support (see https://github.com/irmen/pyminiaudio)' )
    
    format = getattr( miniaudio.SampleFormat, MINIAUDIO_NORMALISE_TYPE )
    playback_rate = None
    if interpolation == AudioInterpolation.NONE:
        playback_rate = sample_rate
    else:
        playback_rate = RESAMPLE_RATE

    def audio_iter():
        samp_iter = resample_audio_iter( source, format_type, field_size, signedness, endian, channels, sample_rate, start, end, output_rate=playback_rate, interpolation=interpolation )
        required_frames = yield b''
        old_time = time.time()
        while True:
            sample_data = array( 'f', itertools.islice( samp_iter, required_frames ) ) 
            if not sample_data:
                break
            new_time = time.time()
            print( (required_frames, new_time - old_time) )
            old_time = new_time
            required_frames = yield sample_data


    with miniaudio.PlaybackDevice( output_format=format, nchannels=channels, sample_rate=playback_rate ) as device:
        ai = audio_iter()
        next(ai)
        device.start(ai)
        while device.callback_generator:
            time.sleep( 0.1 )
