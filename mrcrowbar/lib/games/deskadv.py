
from mrcrowbar import models as mrc


class VERS( mrc.Block ):
    data = mrc.Bytes( 0x00, count=4 )


class STUP( mrc.Block ):
    pass


class SNDS( mrc.Block ):
    unknown1 =  mrc.Int16_LE( 0x00 )
    files =     mrc.CStringNStream( 0x02, mrc.UInt16_LE )


class TILE( mrc.Block ):
    pass


class ZONE( mrc.Block ):
    pass


class DAWFile( mrc.Block ):

    pass


class IndyLoader( mrc.Loader ):
    """Loader for the game Indiana Jones and his Desktop Adventures (Win32, 1996)."""
    _SEP = mrc.Loader._SEP

    _INDY_FILE_CLASS_MAP = {
        _SEP+'DESKTOP.DAW$': DAWFile,
    }

    def __init__( self ):
        super().__init__( self._INDY_FILE_CLASS_MAP )


class YodaLoader( mrc.Loader ):
    """Loader for the game Yoda Stories (Win32, 1997)."""
    _SEP = mrc.Loader._SEP

    _YODA_FILE_CLASS_MAP = {
        _SEP+'YODESK.DTA$': DAWFile,
    }

    def __init__( self ):
        super().__init__( self._YODA_FILE_CLASS_MAP )
