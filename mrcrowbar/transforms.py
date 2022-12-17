"""Definition classes for transformations."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NamedTuple, Optional

if TYPE_CHECKING:
    from mrcrowbar.blocks import Block

from mrcrowbar.common import BytesReadType

logger = logging.getLogger( __name__ )


class TransformResult( NamedTuple ):
    payload: bytes = b""
    end_offset: int = 0


class Transform( object ):
    """Base class for defining transformations."""

    # pylint: disable=unused-argument,no-self-use

    def export_data(
        self, buffer: BytesReadType, parent: Optional["Block"] = None
    ) -> TransformResult:
        """Perform a transform on a byte string.

        buffer
            Source byte string.

        parent
            Parent object of the source (to provide context for Refs).
        """
        logger.warning( f"{self}: export_data not implemented!" )
        return TransformResult()

    def import_data(
        self, buffer: BytesReadType, parent: Optional["Block"] = None
    ) -> TransformResult:
        """Perform a reverse-transform on a byte string.

        buffer
            Source byte string.

        parent
            Parent object of the source (to provide context for Refs).
        """
        logger.warning( f"{self}: import_data not implemented!" )
        return TransformResult()
