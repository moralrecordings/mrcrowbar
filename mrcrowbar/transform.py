
def import_binary( klass, instance, raw_buffer, **kw ):
    data = import_binary_loop( klass, instance, raw_buffer, **kw )
    return data


def import_binary_loop( klass, instance, raw_buffer, **kw ):
    assert isinstance( instance, klass )
    

class Transform:
    def export_data( self, buffer ):
        return b''

    def import_data( self, buffer ):
        return None
