"""Definition classes for transformations."""

from typing import NamedTuple

import logging
logger = logging.getLogger( __name__ )


class TransformResult( NamedTuple ):
    payload: bytes = b''
    end_offset: int = 0


class Transform( object ):
    """Base class for defining transformations."""
    # pylint: disable=unused-argument,no-self-use

    def export_data( self, buffer, parent=None ):
        """Perform a transform on a byte string.

        buffer
            Source byte string.

        parent
            Parent object of the source (to provide context for Refs).
        """
        logger.warning( '{}: export_data not implemented!'.format( self ) )
        return TransformResult()

    def import_data( self, buffer, parent=None ):
        """Perform a reverse-transform on a byte string.

        buffer
            Source byte string.

        parent
            Parent object of the source (to provide context for Refs).
        """
        logger.warning( '{}: import_data not implemented!'.format( self ) )
        return TransformResult()
