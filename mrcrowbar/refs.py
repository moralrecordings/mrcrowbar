"""Definition classes for cross-references."""

from mrcrowbar import common


class Ref( object ):
    """Base class for defining cross-references."""

    def __init__( self, path, allow_write=True ):
        """Create a new Ref instance.

        path
            The path to traverse from the context object to reach the target.
            Child lookups should be in property dot syntax (e.g. obj1.obj2.target).
            For Blocks that are constructed by other Blocks, you can use the _parent property
            to traverse up the stack.

        allow_write
            Allow modification of the target with the set() method.
        """
        self._position_hint = next( common.next_position_hint )
        # very simple path syntax for now: walk down the chain of properties
        if not type( path ) == str:
            raise TypeError( 'path argument to Ref() should be a string' )
        self._path = tuple( path.split( '.' ) )
        self._allow_write = allow_write

    def cache( self, instance, name ):
        """Signal to the source to pre-load information.

        Called by the parent Block constructor."""
        pass

    def get( self, instance, **kwargs ):
        """Return an attribute from an object using the Ref path.

        instance
            The object instance to traverse.
        """
        target = instance
        for attr in self._path:
            target = getattr( target, attr )
        return target

    def set( self, instance, value, **kwargs ):
        """Set an attribute on an object using the Ref path.

        instance
            The object instance to traverse.

        value
            The value to set.

        Throws AttributeError if allow_write is False.
        """
        if not self._allow_write:
            raise AttributeError( "can't set Ref directly, allow_write is disabled" )
        target = instance
        for attr in self._path[:-1]:
            target = getattr( target, attr )
        setattr( target, self._path[-1], value )
        return

    def __repr__( self ):
        desc = '0x{:016x}'.format( id( self ) )
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return '<{}: {}>'.format( self.__class__.__name__, desc )

    @property
    def repr( self ):
        """Plaintext summary of the object."""
        return '{} ({})'.format( '.'.join( self._path ), 'rw' if self._allow_write else 'r' )

    @property
    def serialised( self ):
        """Tuple containing the contents of the object."""
        return common.serialise( self, ('_path', '_allow_write') )

    def __hash__( self ):
        return hash( self.serialised )

    def __eq__( self, other ):
        return self.serialised == other.serialised


class ConstRef( Ref ):
    """Shortcut for a read-only Ref."""

    def __init__( self, path ):
        """Create a new Ref instance.

        path
            The path to traverse from the context object to reach the target.
            Child lookups should be in property dot syntax (e.g. obj1.obj2.target).
            For Blocks that are constructed by other Blocks, you can use the _parent property
            to traverse up the stack.
        """
        super().__init__( path, allow_write=False )


def property_get( prop, instance, **kwargs ):
    """Wrapper for property reads which auto-dereferences Refs if required.

    prop
        A Ref (which gets dereferenced and returned) or any other value (which gets returned).

    instance
        The context object used to dereference the Ref.
    """
    if isinstance( prop, Ref ):
        return prop.get( instance, **kwargs )
    return prop


def property_set( prop, instance, value, **kwargs ):
    """Wrapper for property writes which auto-deferences Refs.

    prop
        A Ref (which gets dereferenced and the target value set).

    instance
        The context object used to dereference the Ref.

    value
        The value to set the property to.

    Throws AttributeError if prop is not a Ref.
    """

    if isinstance( prop, Ref ):
        return prop.set( instance, value, **kwargs )
    raise AttributeError( "can't change value of constant {} (context: {})".format( prop, instance ) )


def view_property( prop ):
    """Wrapper for attributes of a View class which auto-dereferences Refs.
    
    Equivalent to setting a property on the class with the getter wrapped
    with property_get(), and the setter wrapped with property_set().

    prop
        A string containing the name of the class attribute to wrap.
    """
    def getter( self ):
        return property_get( getattr( self, prop ), self.parent )

    def setter( self, value ):
        return property_set( getattr( self, prop ), self.parent, value )

    return property( getter, setter )


class EndOffset( Ref ):
    """Cross-reference for getting the offset of the end of a Field. Used for chaining variable length Fields."""
    def __init__( self, path, neg=False, align=1 ):
        """Create a new EndOffset instance.

        path
            The path to traverse from the context object to reach the target Field.
            Child lookups should be in property dot syntax (e.g. obj1.obj2.target).
            For Blocks that are constructed by other Blocks, you can use the _parent property
            to traverse up the stack.

        neg
            Whether to return the end offset as a negative value. Useful for
            e.g. globally offsetting Stores which use an index relative to the
            very start of the file, even if the first chunk contains headers.

        align
            Round up the result to the nearest multiple of this value.
        """
        super().__init__( path )
        self._neg = neg
        self._align = align

    def get( self, instance, **kwargs ):
        target = instance
        align = property_get( self._align, instance )
        for attr in self._path[:-1]:
            target = getattr( target, attr )
        target = target.get_field_end_offset( self._path[-1] )
        target -= (target % -align)
        if self._neg:
            target *= -1
        return target

    def set( self, instance, value, **kwargs ):
        raise AttributeError( "can't change the end offset of another field" )

    @property
    def serialised( self ):
        return common.serialise( self, ('_path', '_allow_write', '_neg', '_align') )


class Chain( Ref ):
    def __init__( self ):
        super().__init__( '_previous_attr' )

    def get( self, instance, caller=None, **kwargs ):
        if caller is None:
            return 0
        field_name = getattr( caller, self._path[0] )
        if field_name is None:
            return 0
        return instance.get_field_end_offset( field_name )

    def set( self, instance, value, **kwargs ):
        raise AttributeError( "can't change the end offset of another field" )

    def __repr__( self ):
        return '<Chain>'
