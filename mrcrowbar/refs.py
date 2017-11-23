"""Definition classes for cross-references."""

class Ref( object ):
    """Base class for defining cross-references."""

    def __init__( self, path, allow_write=False ):
        """Create a new Ref instance.

        path
            The path to traverse from the context object to reach the target.
            Child lookups should be in property dot syntax (e.g. obj1.obj2.target).
            For Blocks that are constructed by other Blocks, you can use the _parent property
            to traverse up the stack.

        allow_write
            Allow modification of the target with the set() method.
        """
        # very simple path syntax for now: walk down the chain of properties
        self.path = path.split( '.' )
        self.allow_write = allow_write

    def get( self, instance ):
        """Return an attribute from an object using the Ref path.

        instance
            The object instance to traverse.
        """
        target = instance
        for attr in self.path:
            target = getattr( target, attr )
        return target

    def set( self, instance, value ):
        """Set an attribute on an object using the Ref path.

        instance
            The object instance to traverse.

        value
            The value to set.

        Throws AttributeError if allow_write is False.
        """
        if not self.allow_write:
            raise AttributeError( "can't set Ref directly" )
        target = instance
        for attr in self.path[:-1]:
            target = getattr( target, attr )
        setattr( target, self.path[-1], value )
        return

    def __repr__( self ):
        desc = '0x{:016x}'.format( id( self ) )
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return '<{}: {}>'.format( self.__class__.__name__, desc )

    repr = None


def property_get( prop, instance ):
    """Wrapper for property reads which auto-dereferences Refs if required.

    prop
        A Ref (which gets dereferenced and returned) or any other value (which gets returned).

    instance
        The context object used to dereference the Ref.
    """
    if isinstance( prop, Ref ):
        return prop.get( instance )
    return prop


def property_set( prop, instance, value ):
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
        return prop.set( instance, value )
    raise AttributeError( "property was declared as a constant" )


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
