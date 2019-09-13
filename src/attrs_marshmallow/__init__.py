import attr
import marshmallow
from functools import partial
from marshmallow import Schema, post_load
from marshmallow.fields import Field, Raw
from typing import Type, Callable, Mapping, Any, Optional
from typing_inspect import get_origin, get_args, is_optional_type

MARSHMALLOW_FIELD = "marshmallow_field"
MARSHMALLOW_KWARGS = "marshmallow_kwargs"

class MissingType:
    def __bool__(self):
        return False

Missing = MissingType()

def schema(**fields):
    return type("Schema", (Schema,), fields)

SIMPLE_TYPES = {
    str: marshmallow.fields.String
}

_FIELD_FOR_TYPE = Callable[[Type, Mapping[str, Any]], Field]
_TYPE_HOOK = Callable[[Type, Mapping[str, Any], _FIELD_FOR_TYPE], Field]

class TypedDictField(Field):
    def __init__(self, *args, value_field: Field, **kwargs):
        super().__init__(*args, **kwargs)
        self.value_field = value_field

    def _serialize(self, value, attr, obj):
        return {key: self.value_field.serialize(key, value) for key in value}

    def _deserialize(self, value, attr, data):
        return {key: self.value_field.deserialize(value, key, data) for key, value in value.items()}

def _field_for_type(tp: Type, field_kwargs: Mapping[str, Any], field_for_type: _FIELD_FOR_TYPE) -> Field:
    origin = get_origin(tp)
    args = get_args(tp)

    field_kwargs = {"allow_none": True, **field_kwargs}

    if origin == list:
        return marshmallow.fields.List(field_for_type(args[0], {}), **field_kwargs)
    elif origin == dict:
        value_field = field_for_type(args[1], {})
        return TypedDictField(value_field=value_field, **field_kwargs)
    elif is_optional_type(tp):
        return field_for_type(args[0], field_kwargs)
    elif hasattr(tp, "Schema"):
        return marshmallow.fields.Nested(tp.Schema, **field_kwargs)
    else:
        return SIMPLE_TYPES.get(tp, Raw)(**field_kwargs)

def _field_for_attribute(attribute: attr.Attribute, type_hook: Optional[_TYPE_HOOK]) -> Field:
    field_kwargs = attribute.metadata.get(MARSHMALLOW_KWARGS, {})
    if type_hook:
        field_for_type = partial(type_hook)
        field_for_type.keywords["default"] = partial(_field_for_type, field_for_type=field_for_type)
    else:
        field_for_type = partial(_field_for_type)
        field_for_type.keywords["field_for_type"] = field_for_type

    field = field_for_type(attribute.type, field_kwargs)
    return attribute.metadata.get(MARSHMALLOW_FIELD, field)

def attrs_schema(cls: Type, type_hook: Optional[_TYPE_HOOK] = None):
    fields = {name: _field_for_attribute(attribute, type_hook) for name, attribute in attr.fields_dict(cls).items()}

    @post_load
    def make_object_func(self, data, **kwargs):
        return cls(**data)

    fields["make_object"] = make_object_func

    return type("Schema", (marshmallow.Schema,), fields)

def add_schema(cls: Type = None, type_hook: _TYPE_HOOK = None):
    def wrapper(cls: Type):
        if "__attrs_attrs__" not in cls.__dict__:
            cls = attr.s(cls, auto_attribs=True, kw_only=True)

        cls.Schema = attrs_schema(cls, type_hook=type_hook)
        return cls

    if cls:
        return wrapper(cls)

    return wrapper
