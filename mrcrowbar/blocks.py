"""Definition classes for data blocks."""

from collections import OrderedDict

from mrcrowbar.fields import *
from mrcrowbar.refs import *
from mrcrowbar.checks import *
from mrcrowbar import utils

class FieldDescriptor( object ):
    def __init__( self, name ):
        """Attribute wrapper class for Fields.

        name
            Name of the Field.
        """
        self.name = name

    def __get__( self, instance, cls ):
        try:
            if instance is None:
                return cls._fields[self.name]
            return instance._field_data[self.name]
        except KeyError:
            raise AttributeError( self.name )

    def __set__( self, instance, value ):
        if instance is None:
            return
        instance._field_data[self.name] = value
        return

    def __delete__( self, instance ):
        if self.name not in instance._fields:
            raise AttributeError( "{} has no attribute {}".format(
                type( instance ).__name__, self.name ) )
        del instance._fields[self.name]


class RefDescriptor( object ):
    def __init__( self, name ):
        """Attribute wrapper class for Refs.

        name
            Name of the Ref.
        """
        self.name = name

    def __get__( self, instance, cls ):
        try:
            if instance is None:
                return cls._refs[self.name]
            # FIXME: don't cache until we evaluate if the performance suffers
            if True: #self.name not in instance._ref_cache:
                instance._ref_cache[self.name] = instance._refs[self.name].get( instance )
            return instance._ref_cache[self.name]
        except KeyError:
            raise AttributeError( self.name )

    def __set__( self, instance, value ):
        if instance is None:
            return
        instance._refs[self.name].set( instance, value )
        return

    def __delete__( self, instance ):
        raise AttributeError( "can't delete Ref" )


class BlockMeta( type ):
    def __new__( mcs, name, bases, attrs ):
        """Metaclass for Block which detects and wraps attributes from the class definition."""

        # Structures used to accumulate meta info
        fields = OrderedDict()
        refs = OrderedDict()
        checks = OrderedDict()

        # Parse this class's attributes into meta structures
        for key, value in attrs.items():
            if isinstance( value, Field ):
                fields[key] = value
            elif isinstance( value, Ref ):
                refs[key] = value
            elif isinstance( value, Check ):
                checks[key] = value

        # Convert list of types into fields for new klass
        fields = OrderedDict( sorted( fields.items(), key=lambda i: i[1]._position_hint ) )
        for key, field in fields.items():
            attrs[key] = FieldDescriptor( key )
        for key, ref in refs.items():
            attrs[key] = RefDescriptor( key )

        # Ready meta data to be klass attributes
        attrs['_fields'] = fields
        attrs['_refs'] = refs
        attrs['_checks'] = checks

        klass = type.__new__( mcs, name, bases, attrs )

        for field_name, field in fields.items():
            field._name = field_name

        return klass

    @property
    def fields( cls ):
        return cls._fields

    @property
    def refs( cls ):
        return cls._refs
    
    @property
    def checks( cls ):
        return cls._checks


class Block( object, metaclass=BlockMeta ):
    _parent = None
    repr = None

    def __init__( self, source_data=None, parent=None, preload_attrs=None ):
        """Base class for Blocks.

        source_data
            Source data to construct Block with. Can be a byte string or 
            another Block object.

        parent
            Parent Block object where this Block is defined. Used for e.g. 
            evaluating Refs.

        preload_attrs
            Attributes on the Block to set before importing the data. Used
            for linking in dependencies before loading.
        """
        self._field_data = {}
        self._ref_cache = {}
        self._parent = parent

        if preload_attrs:
            for attr, value in preload_attrs.items():
                setattr( self, attr, value )

        # start the initial load of data
        if isinstance( source_data, Block ):
            self.clone_data( source_data )
        else:
            self.import_data( source_data )

    def __repr__( self ):
        desc = '0x{:016x}'.format( id( self ) )
        if hasattr( self, 'repr' ) and isinstance( self.repr, str ):
            desc = self.repr
        return '<{}: {}>'.format( self.__class__.__name__, desc )

    def clone_data( self, source ):
        """Clone data from another Block.

        source
            Block instance to copy from.
        """
        klass = self.__class__
        assert isinstance( source, klass )

        for name in klass._fields:
            self._field_data[name] = getattr( source, name )

    def import_data( self, raw_buffer ):
        """Import data from a byte array.

        raw_buffer
            Byte array to import from.
        """
        klass = self.__class__
        if raw_buffer:
            assert utils.is_bytes( raw_buffer )

        self._field_data = {}

        for name in klass._fields:
            if raw_buffer:
                self._field_data[name] = klass._fields[name].get_from_buffer(
                    raw_buffer, parent=self
                )
            else:
                self._field_data[name] = klass._fields[name].default
        
        if raw_buffer:
            for name, check in klass._checks.items():
                check.check_buffer( raw_buffer, parent=self )

            # debug stuff
            #test = self.export_data()
            #print( 'Stats for {}:'.format( self ) )
            #print( 'Length: {} => {}'.format( len( raw_buffer ), len( test ) ) )
            #if test == raw_buffer[:len( test )]:
            #    print( 'Content: exact match!' )
            #else:
            #    print( 'Content:' )
            #    print( utils.hexdump_diff( raw_buffer[:len( test )], test ) )
        return

    def export_data( self ):
        """Export data to a byte array."""
        klass = self.__class__

        output = bytearray( b'\x00'*self.get_size() )

        for name in klass._fields:
            scrubbed_data = klass._fields[name].scrub( 
                self._field_data[name], parent=self 
            )
            klass._fields[name].validate( 
                scrubbed_data, parent=self 
            )
            klass._fields[name].update_buffer_with_value(
                scrubbed_data, output, parent=self
            )

        for name, check in klass._checks.items():
            check.update_buffer( output, parent=self )
        return output

    def validate( self ):
        """Validate all the fields on this Block instance."""
        klass = self.__class__

        for name in klass._fields:
            scrubbed_data = klass._fields[name].scrub( 
                self._field_data[name], parent=self 
            )
            klass._fields[name].validate( 
                scrubbed_data, parent=self 
            )
        return

    def get_size( self ):
        """Get the projected size (in bytes) of the exported data from this Block instance."""
        klass = self.__class__
        size = 0
        for name in klass._fields:
            size = max( size, klass._fields[name].get_end_offset( self._field_data[name], parent=self ) )
        for check in klass._checks.values():
            size = max( size, check.get_end_offset( parent=self ) )
        return size

    def _prime( self ):
        klass = self.__class__
        for ref in klass._refs:
            pass


class Unknown( Block ):
    """Placeholder block for data of an unknown format."""

    #: Raw data.
    data =  Bytes( 0x0000 )
