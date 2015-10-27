from copy import deepcopy
from six import add_metaclass, iteritems, iterkeys

import os, re

from mrcrowbar.collections import OrderedDict

from mrcrowbar.fields import *


class Magic:
    pass


# how do we define a block?

# - we want to be able to scan through a stream of bollocks and identify a magic number
# - scanning will provide a start offset (in other words, a list sliced to the beginning)
# - further pounding 


# borrowed from schematic

class FieldDescriptor(object):

    """
    The FieldDescriptor serves as a wrapper for Types that converts them into
    fields.

    A field is then the merger of a Type and it's Model.
    """

    def __init__(self, name):
        """
        :param name:
            The field's name
        """
        self.name = name

    def __get__(self, instance, cls):
        """
        Checks the field name against the definition of the model and returns
        the corresponding data for valid fields or raises the appropriate error
        for fields missing from a class.
        """
        try:
            if instance is None:
                return cls._fields[self.name]
            return instance._data[self.name]
        except KeyError:
            raise AttributeError(self.name)

    def __set__(self, instance, value):
        """
        Checks the field name against a model and sets the value.
        """
        from .types.compound import ModelType
        field = instance._fields[self.name]
        if not isinstance(value, Model) and isinstance(field, ModelType):
            value = field.model_class(value)
        instance._data[self.name] = value

    def __delete__(self, instance):
        """
        Checks the field name against a model and deletes the field.
        """
        if self.name not in instance._fields:
            raise AttributeError('%r has no attribute %r' %
                                 (type(instance).__name__, self.name))
        del instance._fields[self.name]


class ModelMeta(type):

    """
    Meta class for Models.
    """

    def __new__(mcs, name, bases, attrs):
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
        serializables = {}
        #validator_functions = {}  # Model level

        # Accumulate metas info from parent classes
        for base in reversed(bases):
            if hasattr(base, '_fields'):
                fields.update(deepcopy(base._fields))

        # Parse this class's attributes into meta structures
        for key, value in iteritems(attrs):
            if isinstance(value, Field):
                fields[key] = value

        # Convert list of types into fields for new klass
        fields.sort(key=lambda i: i[1]._position_hint)
        for key, field in iteritems(fields):
            attrs[key] = FieldDescriptor(key)

        # Ready meta data to be klass attributes
        attrs['_fields'] = fields

        klass = type.__new__(mcs, name, bases, attrs)

        # Add reference to klass to each field instance
        def set_owner_model(field, klass):
            field.owner_model = klass
            if hasattr(field, 'field'):
                set_owner_model(field.field, klass)

        for field_name, field in fields.items():
            set_owner_model(field, klass)
            field.name = field_name

        # Register class on ancestor models
        klass._subclasses = []
        for base in klass.__mro__[1:]:
            if isinstance(base, ModelMeta):
                base._subclasses.append(klass)

        return klass

    @property
    def fields(cls):
        return cls._fields


@add_metaclass( ModelMeta )
class Block:
    _magic = Magic()
    _block_size = 0

    def __init__( self, raw_buffer=None ):
        self.import_data( raw_buffer )
        pass

    def __repr__( self ):
        return '<{}: {}>'.format( self.__class__.__name__, str( self ) )

    def __str__( self ):
        return hex( id( self ) )

    def import_data( self, raw_buffer, **kw ):
        self._data = _import_data( self.__class__, raw_buffer, **kw )

    def size( self ):
        return self._block_size

    def validate( self, **kw ):
        return _validate( self.__class__, self._data, **kw )
        


class Check( object ):
    def __init__( self, instance, value ):
        pass


def _import_data( klass, raw_buffer, **kw ):
    data = {}
    if raw_buffer:
        assert type( raw_buffer ) == bytes
        assert len( raw_buffer ) >= klass._block_size
        for name in klass._fields:
            data[name] = klass._fields[name].get_from_buffer( raw_buffer )
    else:
        for name in klass._fields:
            data[name] = klass._fields[name].default
    return data


def _export_data( klass, instance, **kw ):
    assert isinstance( instance, klass )


def _validate( klass, instance_data, **kw ):
    for name in klass._fields:
        klass._fields[name].validate( instance_data[name] )
    return
    

class Transform:
    def export_data( self, buffer ):
        return None
    
    def import_data( self, buffer ):
        return {
            'payload': b'',
            'end_offset': 0
        }



class Loader:
    def __init__( self, file_class_map, case_sensitive=False ):
        self.file_class_map = file_class_map
        self.re_flags = re.IGNORECASE if not case_sensitive else 0
        self.file_re_map = { key: re.compile( key, flags=self.re_flags ) for key, klass in file_class_map.items() if klass } 
        self._files = {}

    def load( self, target_path, verbose=False ):
        target_path = os.path.abspath( target_path )
        for root, subFolders, files in os.walk( target_path ):
            for f in files:
                full_path = os.path.join( root, f )

                for key, regex in self.file_re_map.items():
                    match = regex.search( full_path )
                    if match:
                        data = open( full_path, 'rb' ).read()
                        if verbose:
                            print( '{} => {}'.format( full_path, self.file_class_map[key] ) )
                        self._files[full_path] = {
                            'klass': self.file_class_map[key],
                            'match': match.groups(),
                            'obj': self.file_class_map[key]( data )
                        }

        self.post_load( verbose )
        return

    def post_load( self, verbose=False ):
        pass
        

    def keys( self ):
        return self._files.keys()

    def __len__( self ):
        return len( self._files )

    def __getitem__( self, key ):
        return self._files[key]['obj']

    def __contains__( self, key ):
        return key in self._files
