"""Definition classes for transformations."""

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
        return {
            'payload': b'',
        }

    def import_data( self, buffer, parent=None ):
        """Perform a reverse-transform on a byte string.

        buffer
            Source byte string.

        parent
            Parent object of the source (to provide context for Refs).
        """
        return {
            'payload': b'',
            'end_offset': 0
        }
