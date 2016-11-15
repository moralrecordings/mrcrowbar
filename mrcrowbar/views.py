from collections import OrderedDict

from mrcrowbar.refs import *

class View( object ):
    def __init__( self, parent, *args, **kwargs ):
        self._parent = parent


class Store( View ):
    def __init__( self, parent, source, fill=b'\x00', **kwargs ):
        super( Store, self ).__init__( parent )
        self._source = source
        self.fill = fill
        self.refs = OrderedDict()

    @property
    def source( self ):
        return property_get( self._source, self._parent )

    @source.setter
    def source( self, value ):
        return property_set( self._source, self._parent, value )

    def get_object( self, instance, offset, size, block_klass, block_kwargs=None ):
        key = (instance, offset, size, block_klass)
        offset = property_get( offset, instance )
        size = property_get( size, instance )
        block_kwargs = block_kwargs if block_kwargs else {}

        if key not in self.refs:
            self.refs[key] = block_klass( source_data=self.source[offset:offset+size], parent=instance, **block_kwargs )
        return self.refs[key]


class StoreRef( Ref ):
    def __init__( self, block_klass, store, offset, size, block_kwargs=None ):
        self.block_klass = block_klass
        self.store = store
        self.offset = offset
        self.size = size
        self.block_kwargs = block_kwargs
   
    def __str__( self ):
        return '0x{:016x}'.format( id( self ) )

    def get( self, instance ):
        store = property_get( self.store, instance )
        
        return store.get_object( instance, self.offset, self.size, self.block_klass, self.block_kwargs )

    def set( self, instance ):
        raise AttributeError( "can't set StoreRef directly" )
