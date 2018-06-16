from collections import OrderedDict
import logging
logger = logging.getLogger( __name__ )

from mrcrowbar.refs import Ref, property_get, property_set, view_property

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
        self.items = OrderedDict()

    source = view_property( '_source' )
    base_offset = view_property( '_base_offset' )

    def cache_object( self, instance, offset, size, block_klass, block_kwargs=None ):
        # key is the combination of:
        # instance, offset ref, size ref
        key = (instance, offset, size)
        self.refs[key] = {
            'instance': instance,
            'offset': offset,
            'size': size,
            'block_klass': block_klass,
            'block_kwargs': block_kwargs if block_kwargs else {}
        }

    def get_object( self, instance, offset, size ):
        if self.refs and not self.items:
            self.cache()
        key = (instance, offset, size)

        return self.items[key]
        offset = property_get( offset, instance )
        size = property_get( size, instance )
        block_kwargs = self.refs[key]['block_klass']

        if key not in self.refs:
            source_data = self.source[self.base_offset+offset:]
            if size is not None:
                source_data = source_data[:size]
            else:
                logger.warning( '{}: loading from StoreRef without a size!'.format( self ) )
            self.items[key] = block_klass( source_data=source_data, parent=instance, **block_kwargs )
        return self.refs[key]

    def set_object( self, instance, offset, size, value ):
        key = (instance, offset, size)
        self.items[key] = value

    def cache( self ):
        for key, data in self.refs.items():
            if key not in self.items:
                instance = data['instance']
                block_klass = data['block_klass']
                block_kwargs = data['block_kwargs']
                offset = property_get( data['offset'], instance )
                size = property_get( data['size'], instance )
                self.items[key] = block_klass( source_data=self.source[self.base_offset+offset:][:size], parent=instance, **block_kwargs )

    def save( self ):
        pointer = 0
        result = bytearray()
        for key, block in self.items.items():
            instance, offset, size = key
            data = block.export_data()
            property_set( offset, instance, pointer-self.base_offset )
            property_set( size, instance, len( data ) )
            pointer += len( data )
            result += data
        self.source = bytes( result )

class LinearStore( View ):
    def __init__( self, parent, source, block_klass, offsets=None, sizes=None, base_offset=0, fill=b'\x00', **kwargs ):
        super().__init__( parent, **kwargs )
        self._source = source
        self._offsets = offsets
        self._sizes = sizes
        self._base_offset = base_offset
        self.block_klass = block_klass
        self._items = None

    source = view_property( '_source' )
    offsets = view_property( '_offsets' )
    sizes = view_property( '_sizes' )
    base_offset = view_property( '_base_offset' )

    @property
    def items( self ):
        if self._items is None:
            self.cache()
        return self._items

    @items.setter
    def items( self, value ):
        self._items = value

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
        self._items = [self.block_klass( self.source[self.base_offset+offsets[i]:][:sizes[i]], parent=self.parent ) for i in range( len( sizes ) )]

    def save( self ):
        self.validate()
        if self._items is None:
            self.cache()

        result = bytearray()
        pointer = 0

        offsets = []
        sizes = []

        for item in self.items:
            entry = item.export_data()
            offsets.append( pointer - self.base_offset )
            sizes.append( len( entry ) )
            result += entry
            pointer += len( entry )
        self.source = bytes(result)
        if self.offsets and self.offsets != offsets:
            self.offsets = offsets
        if self.sizes and self.sizes != sizes:
            self.sizes = sizes


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

    def cache( self, instance ):
        store = property_get( self.store, instance )
        store.cache_object( instance, self.offset, self.size, self.block_klass, self.block_kwargs )

    def get( self, instance ):
        store = property_get( self.store, instance )
        return store.get_object( instance, self.offset, self.size )

    def set( self, instance, value ):
        store = property_get( self.store, instance )
        assert isinstance( value, self.block_klass )
        return store.set_object( instance, self.offset, self.size, value )
