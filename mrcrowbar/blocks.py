"""Definition classes for data blocks."""

from collections import OrderedDict

from mrcrowbar.fields import *
from mrcrowbar.refs import *
from mrcrowbar.validate import *
from mrcrowbar import utils

class FieldDescriptor( object ):

    """
    The FieldDescriptor serves as a wrapper for Types that converts them into
    fields.

    A field is then the merger of a Type and it's Model.
    """

    def __init__( self, name ):
        """
        :param name:
            The field's name
        """
        self.name = name

    def __get__( self, instance, cls ):
        """
        Checks the field name against the definition of the model and returns
        the corresponding data for valid fields or raises the appropriate error
        for fields missing from a class.
        """
        try:
            if instance is None:
                return cls._fields[self.name]
            return instance._field_data[self.name]
        except KeyError:
            raise AttributeError( self.name )

    def __set__( self, instance, value ):
        """
        Checks the field name against a model and sets the value.
        """
        #from .types.compound import ModelType
        #field = instance._fields[self.name]
        #if not isinstance( value, Model ) and isinstance( field, ModelType ):
        #    value = field.model_class( value )
        if instance is None:
            return
        instance._field_data[self.name] = value
        return

    def __delete__( self, instance ):
        """
        Checks the field name against a model and deletes the field.
        """
        if self.name not in instance._fields:
            raise AttributeError( "{} has no attribute {}".format(
                type( instance ).__name__, self.name ) )
        del instance._fields[self.name]


class RefDescriptor( object ):
    def __init__( self, name ):
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


class ModelMeta( type ):

    """
    Meta class for Models.
    """

    def __new__( mcs, name, bases, attrs ):
        """
        This metaclass adds four attributes to host classes: mcs._fields,
        mcs._serializables, mcs._validator_functions, and mcs._options.

        This function creates those attributes like this:

        ``mcs._fields`` is list of fields that are schematics types
        ``mcs._serializables`` is a list of functions that are used to generate
        values during serialization
        ``mcs._validator_functions`` are class level validation functions
        ``mcs._options`` is the end result of parsing the ``Options`` class
        """

        # Structures used to accumulate meta info
        fields = OrderedDict()
        refs = OrderedDict()
        checks = OrderedDict()

        serializables = {}
        #validator_functions = {}  # Model level

        # Parse this class's attributes into meta structures
        for key, value in attrs.items():
            if isinstance( value, Field ):
                fields[key] = value
            elif isinstance( value, Ref ):
                refs[key] = value
            elif isinstance( value, Check ):
                checks[key] = value
        #    elif isinstance( value, View ):
        #        views[key] = value

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

        # Add reference to klass to each field instance
        #def set_owner_model( field, klass ):
        #    field.owner_model = klass
        #    if hasattr( field, 'field' ):
        #        set_owner_model( field.field, klass )

        for field_name, field in fields.items():
        #    set_owner_model(field, klass)
            field._name = field_name

        # Register class on ancestor models
        #klass._subclasses = []
        #for base in klass.__mro__[1:]:
        #    if isinstance(base, ModelMeta):
        #        base._subclasses.append(klass)

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


class Block( object, metaclass=ModelMeta ):
    _block_size = 0
    _parent = None

    def __init__( self, source_data=None, parent=None ):
        self._field_data = {}
        self._ref_cache = {}
        self._parent = parent

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

    repr = None

    def clone_data( self, source, **kw ):
        klass = self.__class__
        assert isinstance( source, klass )

        for name in klass._fields:
            self._field_data[name] = getattr( source, name )

    def import_data( self, raw_buffer, **kw ):
        klass = self.__class__
        if raw_buffer:
            assert utils.is_bytes( raw_buffer )
            assert len( raw_buffer ) >= klass._block_size

        self._field_data = {}

        for name in klass._fields:
            if raw_buffer:
                self._field_data[name] = klass._fields[name].get_from_buffer(
                    raw_buffer, parent=self
                )
            else:
                self._field_data[name] = klass._fields[name].default

        for name in klass._checks:
            pass
        return

    def export_data( self, **kw ):
        klass = self.__class__

        output = bytearray( b'\x00'*klass._block_size )

        for name in klass._fields:
            klass._fields[name].update_buffer_with_value(
                self._field_data[name], output, parent=self
            )
        return output

    def validate( self, **kw ):
        klass = self.__class__
        for name in klass._fields:
            klass._fields[name].validate( self._field_data[name], parent=self )
        return
