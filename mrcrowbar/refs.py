"""Definition classes for cross-references."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from mrcrowbar import common

if TYPE_CHECKING:
    from mrcrowbar.blocks import Block
    from mrcrowbar.fields import Field

T = TypeVar( "T" )


class Ref( Generic[T] ):
    """Base class for defining cross-references."""

    def __init__( self, path: str, allow_write: bool = True ):
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
            raise TypeError( "path argument to Ref() should be a string" )
        self._path = tuple( path.split( "." ) )
        self._allow_write = allow_write

    def cache( self, instance: Block, name: str ) -> None:
        """Signal to the source to pre-load information.

        Called by the parent Block constructor."""
        pass

    def get( self, instance: Block, caller: Field | None = None ) -> T:
        """Return an attribute from an object using the Ref path.

        instance
            The object instance to traverse.
        """
        target = instance
        for attr in self._path:
            target = getattr( target, attr )
        return target  # type: ignore

    def set( self, instance: Block, value: T, caller: Field | None = None ) -> None:
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

    def __repr__( self ) -> str:
        desc = f"0x{id( self ):016x}"
        if hasattr( self, "repr" ) and isinstance( self.repr, str ):
            desc = self.repr
        return f"<{self.__class__.__name__}: {desc}>"

    @property
    def repr( self ) -> str:
        """Plaintext summary of the object."""
        perms = "rw" if self._allow_write else "r"
        return f'{".".join( self._path )} ({perms})'

    @property
    def serialised( self ):
        """Tuple containing the contents of the object."""
        return common.serialise( self, ["_path", "_allow_write"] )

    def __hash__( self ) -> int:
        return hash( self.serialised )

    def __eq__( self, other: Any ) -> bool:
        return self.serialised == other.serialised


class ConstRef( Ref[T] ):
    """Shortcut for a read-only Ref."""

    def __init__( self, path: str ):
        """Create a new Ref instance.

        path
            The path to traverse from the context object to reach the target.
            Child lookups should be in property dot syntax (e.g. obj1.obj2.target).
            For Blocks that are constructed by other Blocks, you can use the _parent property
            to traverse up the stack.
        """
        super().__init__( path, allow_write=False )


def property_get(
    prop: None | T | Ref[T],
    instance: Block | None,
    caller: Field | None = None,
) -> T | None:
    """Wrapper for property reads which auto-dereferences Refs if required.

    prop
        A Ref (which gets dereferenced and returned) or any other value (which gets returned).

    instance
        The context object used to dereference the Ref.
    """
    if isinstance( prop, Ref ):
        return prop.get( instance, caller )
    return prop


def property_set(
    prop: Ref[T], instance: Block | None, value: T, caller: Field | None = None
) -> None:
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
        prop.set( instance, value, caller )
        return
    raise AttributeError(
        f"can't change value of constant {prop} (context: {instance})"
    )


def view_property( prop: str ) -> property:
    """Wrapper for attributes of a View class which auto-dereferences Refs.

    Equivalent to setting a property on the class with the getter wrapped
    with property_get(), and the setter wrapped with property_set().

    prop
        A string containing the name of the class attribute to wrap.
    """

    def getter( self: Any ) -> Any:
        return property_get( getattr( self, prop ), self.parent )

    def setter( self: Any, value: Any ) -> None:
        return property_set( getattr( self, prop ), self.parent, value )

    return property( getter, setter )


class EndOffset( Ref[int] ):
    """Cross-reference for getting the offset of the end of a Field. Used for chaining variable length Fields."""

    def __init__( self, path: str, neg: bool = False, align: int = 1 ):
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

    def get( self, instance: Block | None, caller: Field | None = None ) -> int:
        target = instance
        align = property_get( self._align, instance )
        for attr in self._path[:-1]:
            target = getattr( target, attr )
        target = target.get_field_end_offset( self._path[-1] )
        target -= target % -align
        if self._neg:
            target *= -1
        return target

    def set(
        self, instance: Block | None, value: int, caller: Field | None = None
    ) -> None:
        raise AttributeError( "can't change the end offset of another field" )

    @property
    def serialised( self ):
        return common.serialise( self, ["_path", "_allow_write", "_neg", "_align"] )


class Chain( Ref[int] ):
    def __init__( self ) -> None:
        super().__init__( "_previous_attr" )

    def get( self, instance: Block, caller: Field | None = None ) -> int:
        if caller is None:
            return 0
        field_name = getattr( caller, self._path[0] )
        if field_name is None:
            return 0
        return instance.get_field_end_offset( field_name )

    def set( self, instance: Block, value: int, caller: Field | None = None ) -> None:
        raise AttributeError( "can't change the end offset of another field" )

    def __repr__( self ) -> str:
        return "<Chain>"


class Coda( Ref[int] ):
    def __init__( self ) -> None:
        super().__init__( "_coda_offset" )

    def set( self, instance: Block, value: int, caller: Field | None = None ) -> None:
        raise AttributeError( "can't change the start offset of a Coda" )

    def __repr__( self ) -> str:
        return "<Coda>"
