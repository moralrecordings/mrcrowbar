
class Ref( object ):
    # very simple path syntax for now: walk down the chain of properties
    def __init__( self, path, allow_write=False ):
        self.path = path.split( '.' )
        self.allow_write = allow_write 

    def __repr__( self ):
        return '<{}: {}>'.format( self.__class__.__name__, str( self ) )

    def __str__( self ):
        return '.'.join( self.path )

    def get( self, instance ):
        target = instance
        for attr in self.path:
            target = getattr( target, attr )
        return target

    def set( self, instance, value ):
        if not self.allow_write:
            raise AttributeError( "can't set Ref directly" )
        target = instance
        for attr in self.path[:-1]:
            target = getattr( target, attr )
        setattr( target, self.path[-1], value )
        return


def property_get( prop, parent ):
    if type( prop ) == Ref:
        return prop.get( parent )
    return prop


def property_set( prop, parent, value ):
    if type( prop ) == Ref:
        return prop.set( parent, value )
    raise AttributeError( "property was declared as a constant" )

