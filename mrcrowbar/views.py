from collections import OrderedDict

from mrcrowbar.refs import *

class View( object ):
    def __init__( self, parent, *args, **kwargs ):
        self._parent = parent

    @property
    def parent( self ):
        return self._parent


class Store( View ):
    def __init__( self, parent, source, fill=b'\x00', **kwargs ):
        super().__init__( parent, **kwargs )
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
        # key is the combination of:
        # instance, offset ref, size ref, block_klass
        # this means even if 
        key = (instance, offset, size, block_klass)
        offset = property_get( offset, instance )
        size = property_get( size, instance )
        block_kwargs = block_kwargs if block_kwargs else {}

        if key not in self.refs:
            self.refs[key] = block_klass( source_data=self.source[offset:offset+size], parent=instance, **block_kwargs )
        return self.refs[key]


# Loading a Store is a tricky business.
# The old way was basically to load on demand; so if BlockA had the store and BlockB the StoreRef,
# then at load time the store would be wired up to the giant chunk of bytes.
# Maybe the solution is NOT to use dumb bytes (as they have to be kept legit in edit mode)
# Instead, make a new Field class that is basically like Bytes except it's assembled at export time and you
# can't access it like a normal byte array.
# That would mean that StoreRef would have to also dynamically update the offset and size Refs.

# all up the load process will be something like
# - loader loops through every file
# - every file is run through BlockKlass( buffer )
#  - the metaclass magic extracts the fields 
#  - the constructor creates the store view
# - afterwards, post_load() adds soft links between files

# problem is! because the store only exists after the constructor is called, the StoreRefs aren't going to resolve!
# and because we're relying on the constructors to recursively assemble everything, we can't load the StoreRefs during
# that pass.

# cleanest way I can think of is to have a seperate pass, run after post_load(), which walks the Block tree and hits
# every StoreRef.

# but what about saving?
# well... the store has to do a bunch of stuff
# - take all of the things saved in the StoreRefs
# - assemble them into one byte blob
# - push the bytes to the data ref
# - push the resulting offsets and sizes into the respective refs
# - 

class StoreRef( Ref ):
    def __init__( self, block_klass, store, offset, size, count=None, block_kwargs=None ):
        self.block_klass = block_klass
        self.store = store
        self.offset = offset
        self.size = size
        self.count = count 
        self.block_kwargs = block_kwargs
   
    def get( self, instance ):
        store = property_get( self.store, instance )
        
        return store.get_object( instance, self.offset, self.size, self.block_klass, self.block_kwargs )

    def set( self, instance ):
        raise AttributeError( "can't set StoreRef directly" )

