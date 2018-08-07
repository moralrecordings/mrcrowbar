
from mrcrowbar import models as mrc
from mrcrowbar.lib.images import base as img


# taken from yodesk.exe at offset 0x550EF (.data:0x4572F0), len 0x400
YODA_PALETTE_RAW =  '0000000000000000000000000000000000000000000000000000000000000000'\
                    '0000000000000000ffff8b00c3cf4b008ba31b00577700008ba31b00c3cf4b00'\
                    'fbfbfb00ebe7e700dbd3d300cbc3c300bbb3b300aba3a3009b8f8f008b7f7f00'\
                    '7b6f6f00675b5b00574b4b00473b3b00332b2b00231b1b00130f0f0000000000'\
                    '00c7430000b7430000ab3f00009f3f0000933f0000873b00007b3700006f3300'\
                    '0063330000532b0000472700003b2300002f1b000023130000170f00000b0700'\
                    '4b7bbb004373b300436bab003b63a3003b639b00335b9300335b8b002b538300'\
                    '2b4b7300234b6b0023435f001b3b53001b3747001b334300132b3b000b232b00'\
                    'd7ffff00bbefef00a3dfdf008bcfcf0077c3c30063b3b30053a3a30043939300'\
                    '33878700277777001b676700135b5b000b4b4b00073b3b00002b2b00001f1f00'\
                    'dbebfb00d3e3fb00c3dbfb00bbd3fb00b3cbfb00a3c3fb009bbbfb008fb7fb00'\
                    '83b3f70073a7fb00639bfb005b93f3005b8beb00538bdb005383d3004b7bcb00'\
                    '9bc7ff008fb7f70087b3ef007fa7f300739fef005383cf003b6bb3002f5ba300'\
                    '234f93001b438300133b77000b2f670007275700001b470000133700000f2b00'\
                    'fbfbe700f3f3d300ebe7c700e3dfb700dbd7a700d3cf9700cbc78b00c3bb7f00'\
                    'bbb37300afa763009b934700877b33006f671f005b530f004743000037330000'\
                    'fff7f700efdfdf00dfc7c700cfb3b300bf9f9f00b38b8b00a37b7b00936b6b00'\
                    '83575700734b4b00673b3b00572f2f0047272700371b1b00271313001b0b0b00'\
                    'f7b33700e7930700fb530b00fb000000cb0000009f0000006f00000043000000'\
                    'bfbbfb008f8bfb005f5bfb0093bbff005f97f7003b7bef002363c3001353b300'\
                    '0000ff000000ef000000e3000000d3000000c3000000b7000000a70000009b00'\
                    '00008b0000007f0000006f000000630000005300000047000000370000002b00'\
                    '00ffff0000e3f70000cff30000b7ef0000a3eb00008be7000077df000063db00'\
                    '004fd700003fd300002fcf0097ffff0083dfef0073c3df005fa7cf00538bc300'\
                    '2b2b0000232300001b1b000013130000ff0b0000ff004b00ff00a300ff00ff00'\
                    '00ff0000004b0000ffff0000ff332f000000ff00001f9700df00ff0073007700'\
                    '6b7bc3005757ab005747930053377f004f276700471b4f003b133b0027777700'\
                    '237373001f6f6f001b6b6b001b6767001b6b6b001f6f6f002373730027777700'\
                    'ffffef00f7f7db00f3efcb00efebbb00f3efcb00e7930700e7970f00eb9f1700'\
                    'efa32300f3ab2b00f7b33700efa72700eb9f1b00e7970f000bcbfb000ba3fb00'\
                    '0b73fb000b4bfb000b23fb000b73fb0000139300000bd3000000000000000000'\
                    '00000000000000000000000000000000000000000000000000000000ffffff00'

YODA_PALETTE = img.from_palette_bytes( bytes.fromhex( YODA_PALETTE_RAW ), stride=4, order=(2, 1, 0) )
YODA_PALETTE[0] = img.Transparent()

class VERS( mrc.Block ):
    data = mrc.Bytes( 0x00, count=4 )


class STUP( mrc.Block ):
    pass


class SNDS( mrc.Block ):
    unknown1 =  mrc.Int16_LE( 0x00 )
    files =     mrc.CStringNStream( 0x02, mrc.UInt16_LE )


# 1, 1, 1, 0 - player sprites
# 1, 1, 2, 0 - enemy sprites
# 1, 1, 4, 0 - NPC sprites

# 2, 0, 0, 0 - walkable tiles
# 2, 0, 1, 0 - walkable tiles - special
# 4, 0, 0, 0 - obstacle tiles
# 5, 0, 0, 0 - obstacle overlay tiles

# 13, 0, 0, 0 - movable rocks
# 16, 0, 0, 0 - ???
# 17, 0, 0, 0 - overlayable scenery

# 32, 0, 2, 0 - map: spaceport
# 32, 0, 4, 0 - map: puzzle
# 32, 0, 8, 0 - map: puzzle filled
# 32, 0, 16, 0 - map: door
# 32, 0, 32, 0 - map: door filled
# 32, 0, 64, 0 - map: north wall
# 32, 0, 128, 0 - map: south wall
# 32, 0, 0, 1 - map: west wall
# 32, 0, 0, 2 - map: east wall
# 32, 0, 0, 4 - map: north wall open
# 32, 0, 0, 8 - map: south wall open
# 32, 0, 0, 16 - map: west wall open
# 32, 0, 0, 32 - map: east wall open
# 32, 0, 0, 64 - map: goal
# 32, 0, 0, 128 - map: location

# 65, 0, 1, 0 - blaster
# 65, 0, 2, 0 - rifle + detonator
# 65, 0, 4, 0 - lightsabers
# 65, 0, 8, 0 - force

# 129, 0, 1, 0 - keys
# 129, 0, 2, 0 - tools
# 129, 0, 4, 0 - macguffins
# 129, 0, 8, 0 - macguffins
# 129, 0, 16, 0 - locator
# 129, 0, 64. 0 - health


class TileData( mrc.Block ):
    unknown1 =  mrc.Bytes( 0x00, length=4 )
    data =      mrc.Bytes( 0x04, length=0x400 )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.image = img.IndexedImage(
                        self,
                        width=32,
                        height=32,
                        source=mrc.Ref( 'data' ),
                        palette=YODA_PALETTE,
                    )

# ENDF
# ACTN
# HTSP
# ZAX3
# ZAX2
# ZAUX
# VERS
# PUZ2
# CAUX
# CHWP
# CHAR
# TNAM
# STUP

class StupData( mrc.Block ):
    data =      mrc.Bytes( 0x00, length=0x120 )

class STUP( mrc.Block ):
    size =      mrc.UInt32_LE( 0x00 )   # should be 0x14000
    data =      mrc.BlockField( StupData, 0x04, length=0x120 )

# SNDS
class SNDS( mrc.Block ):
    size =      mrc.UInt32_LE( 0x00 )
    


# TILE
# ZONE

class TILE( mrc.Block ):
    tiles =     mrc.BlockField( TileData, 0x00, stream=True )


class ZONE( mrc.Block ):
    pass


class DAWFile( mrc.Block ):
    pass


class IndyLoader( mrc.Loader ):
    """Loader for the game Indiana Jones and His Desktop Adventures (Win16, 1996)."""
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
