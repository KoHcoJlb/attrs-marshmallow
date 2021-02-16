from enum import Enum
from pathlib import PurePath
from typing import Type, Callable, Mapping, Any, Optional, ForwardRef, List, Dict

import attr
import marshmallow
from marshmallow import Schema, post_load
from marshmallow.fields import Raw, Field
from marshmallow.schema import SchemaMeta
from typing_inspect import get_origin, get_args, is_union_type

from .fields.enum import EnumField
from .fields.nested import NestedField
from .fields.path import PathField
from .fields.polymorphic import PolymorphicField

ATTRIBUTE = "attrs_attribute"
MARSHMALLOW_OPTS = "marshmallow_opts"

MARSHMALLOW_DATA_KEY_OPT = "data_key"
MARSHMALLOW_KWARGS_OPT = "kwargs"
MARSHMALLOW_SKIP_OPT = "skip"
MARSHMALLOW_FIELD_OPT = "field"


def schema(**fields):
    return type("Schema", (Schema,), fields)


def get_marshmallow_opt(field: attr.Attribute, key: str, default=None) -> Any:
    return field.metadata.get(MARSHMALLOW_OPTS, {}).get(key, default)


FIELD_FOR_ATTR = Callable[[type, attr.Attribute, type, Mapping[str, Any]], Field]
FIELD_FOR_ATTR_HOOK = Callable[[type, attr.Attribute, type, Mapping[str, Any], FIELD_FOR_ATTR], Optional[Field]]

_SIMPLE_TYPES: Dict[Type, Type[Field]] = {
    str: marshmallow.fields.String,
    bool: marshmallow.fields.Boolean,
    int: marshmallow.fields.Int
}

_FIELD_FOR_ATTR_HOOKS: List[FIELD_FOR_ATTR_HOOK] = []


def _default_field_for_attribute(cls: type, attribute: attr.Attribute, tp: type, field_kwargs: Mapping[str, Any],
                                 field_for_attr: FIELD_FOR_ATTR) -> Field:
    origin = get_origin(tp)
    args = get_args(tp)

    if origin == list:
        return marshmallow.fields.List(field_for_attr(cls, attribute, args[0], {}), **field_kwargs)
    elif origin == dict:
        return marshmallow.fields.Dict(keys=field_for_attr(cls, attribute, args[0], {}),
                                       values=field_for_attr(cls, attribute, args[1], {}),
                                       **field_kwargs)
    elif is_union_type(tp):
        return field_for_attr(cls, attribute, args[0], field_kwargs)
    elif hasattr(tp, "Schema"):
        return NestedField(tp.Schema, **field_kwargs)
    # Self reference
    elif tp == cls or isinstance(tp, str) and tp == cls.__name__ \
            or isinstance(tp, ForwardRef) and tp.__forward_arg__ == cls.__name__:
        return NestedField("self", **field_kwargs)
    elif issubclass(tp, Enum):
        return EnumField(tp, **field_kwargs)
    elif issubclass(tp, PurePath):
        return PathField(tp, **field_kwargs)
    else:
        return _SIMPLE_TYPES.get(tp, Raw)(**field_kwargs)


def attrs_schema(cls: Type, field_for_attr_hook: Optional[FIELD_FOR_ATTR_HOOK] = None,
                 make_object: bool = True):
    """
    This function takes class and returns generated Schema for it.

    :param cls:
    :param field_for_attr_hook: Function that creates fields for attributes
    :param make_object: Function that creates class from dict
    :return:
    """

    def field_for_attr(cls: type, attribute: attr.Attribute, tp: type, field_kwargs: Mapping[str, Any]):
        field = get_marshmallow_opt(attribute, MARSHMALLOW_FIELD_OPT)
        if field:
            return field

        field_kwargs = {"required": attribute.default is attr.NOTHING, "allow_none": True, **field_kwargs,
                        **get_marshmallow_opt(attribute, MARSHMALLOW_KWARGS_OPT, {}), ATTRIBUTE: attribute}

        for hook in _FIELD_FOR_ATTR_HOOKS + [field_for_attr_hook]:
            if hook:
                res = hook(cls, attribute, tp, field_kwargs, field_for_attr)
                if res:
                    return res

        return _default_field_for_attribute(cls, attribute, tp, field_kwargs, field_for_attr)

    fields = {name: field_for_attr(cls, attribute, attribute.type, {})
              for name, attribute
              in attr.fields_dict(cls).items()
              if attribute.init and not get_marshmallow_opt(attribute, MARSHMALLOW_SKIP_OPT)}

    @post_load
    def make_object_func(self, data, **kwargs):
        return cls(**data)

    if make_object:
        fields["make_object"] = make_object_func
    fields.update({name: getattr(cls, name) for l in SchemaMeta.resolve_hooks(cls).values() for name in l})

    meta = getattr(cls, "Meta", None)
    if meta:
        fields["Meta"] = meta

    return type("Schema", (marshmallow.Schema,), fields)


def add_schema(cls: Type = None, field_for_attr: FIELD_FOR_ATTR_HOOK = _default_field_for_attribute):
    """
    Decorator that adds schema to the class. Schema is then accessible as `Schema` attribute.
    If class isn't attrs class, it will be wrapped automatically with auto_attribs=True, kw_only=True.
    :param cls:
    :param field_for_attr:
    :return:
    """

    def wrapper(cls: Type):
        if "__attrs_attrs__" not in cls.__dict__:
            cls = attr.s(cls, auto_attribs=True, kw_only=True)

        cls.Schema = attrs_schema(cls, field_for_attr)
        return cls

    if cls:
        return wrapper(cls)

    return wrapper


def marshmallow_opts(attribute: Optional[attr.Attribute] = None, *,
                     skip: Optional[bool] = False,
                     field: Optional[Field] = None,
                     kwargs: Optional[Mapping] = None,
                     data_key: Optional[str] = None):
    """
    Configures marshmallow field creation for an attribute.
    This function acts as a wrapper for attr.ib

    :param attribute: Existing attrs attribute to extend
    :param skip: Do not include this field in schema
    :param field: Manually pass field instance
    :param kwargs: Kwargs to pass to field constructor
    :param data_key: Shortcut to specify data_key in kwargs
    :return: attr.Attribute
    """
    attribute = attribute or attr.ib()
    opts = attribute.metadata.setdefault(MARSHMALLOW_OPTS, {})

    kwargs = {**opts.get(MARSHMALLOW_KWARGS_OPT, {}), **(kwargs or {})}
    if data_key is not None:
        kwargs[MARSHMALLOW_DATA_KEY_OPT] = data_key
    opts[MARSHMALLOW_KWARGS_OPT] = kwargs

    if skip is not None:
        opts[MARSHMALLOW_SKIP_OPT] = skip
    if field is not None:
        opts[MARSHMALLOW_FIELD_OPT] = field

    return attribute


def register_simple_field(cls: Type, field: Type[Field]):
    """
    Registers marshmallow field for type
    :param cls:
    :param field: marshmallow Field
    """
    _SIMPLE_TYPES[cls] = field


def register_field_hook(field_for_attr_hook: FIELD_FOR_ATTR_HOOK):
    """
    Registers function for field generation.
    :param field_for_attr_hook: Function
    """
    _FIELD_FOR_ATTR_HOOKS.append(field_for_attr_hook)
