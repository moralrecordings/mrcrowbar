from mrcrowbar.blocks import Block
from mrcrowbar.fields import Bytes

class Unknown( Block ):
    """Placeholder block for data of an unknown format."""

    #: Raw data.
    data =  Bytes( 0x0000 )


