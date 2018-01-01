from collections import OrderedDict

from mrcrowbar.refs import *

class View( object ):
    def __init__( self, parent, *args, **kwargs ):
        self._parent = parent

    @property
    def parent( self ):
        return self._parent


class Store( View ):
    def __init__( self, parent, source, fill=b'\x00', base_offset=0, **kwargs ):
        super().__init__( parent, **kwargs )
        self._source = source
        self._base_offset = base_offset
        self.fill = fill
        self.refs = OrderedDict()

    source = view_property( '_source' )
    base_offset = view_property( '_base_offset' )

    def get_object( self, instance, offset, size, block_klass, block_kwargs=None ):
        # key is the combination of:
        # instance, offset ref, size ref, block_klass
        # this means even if 
        key = (instance, offset, size, block_klass)
        offset = property_get( offset, instance )
        size = property_get( size, instance )
        block_kwargs = block_kwargs if block_kwargs else {}

        if key not in self.refs:
            self.refs[key] = block_klass( source_data=self.source[self.base_offset+offset:][:size], parent=instance, **block_kwargs )
        return self.refs[key]


class LinearStore( View ):
    def __init__( self, parent, source, block_klass, offsets=None, sizes=None, base_offset=0, fill=b'\x00', **kwargs ):
        super().__init__( parent, **kwargs )
        self._source = source
        self._offsets = offsets
        self._sizes = sizes
        self._base_offset = base_offset
        self.block_klass = block_klass
        self.refs = None

    source = view_property( '_source' )
    offsets = view_property( '_offsets' )
    sizes = view_property( '_sizes' )
    base_offset = view_property( '_base_offset' )

    def validate( self ):
        offsets = self.offsets
        sizes = self.sizes
        if offsets and not isinstance( offsets, list ):
            raise TypeError( 'offsets must be a list of values' )
        if sizes and not isinstance( sizes, list ):
            raise TypeError( 'sizes must be a list of values' )
        if not offsets and not sizes:
            raise ValueError( 'either offsets or sizes must be defined' )
        if offsets and sizes and not (len( offsets ) == len( sizes )):
            raise ValueError( 'array length of offsets and sizes must match' )

    def cache( self ):
        self.validate()
        offsets = self.offsets
        sizes = self.sizes
        if not sizes:
            sizes = [offsets[i+1]-offsets[i] for i in range( len( offsets )-1)]
            sizes.append( len( self.source ) - offsets[-1] )
        elif not offsets:
            offsets = [sum( sizes[:i] ) for i in range( len( sizes ) )]
        self.refs = [self.block_klass( self.source[self.base_offset+offsets[i]:][:sizes[i]] ) for i in range( len( sizes ) )]

    def __getitem__( self, key ):
        if self.refs is None:
            self.cache()
        return self.refs[key]

    def __setitem__( self, key, value ):
        if self.refs is None:
            self.cache()
        self.refs[key] = value

    def __len__( self ):
        return len( self.refs )


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

