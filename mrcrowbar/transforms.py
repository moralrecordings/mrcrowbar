
class Transform( object ):
    def export_data( self, buffer, parent=None ):
        return None
    
    def import_data( self, buffer, parent=None ):
        return {
            'payload': b'',
            'end_offset': 0
        }
