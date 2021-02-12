from typing import Dict, Any, Union, Optional, Mapping

from marshmallow import Schema, ValidationError
from marshmallow.fields import Field

from .nested import NestedField


class PolymorphicField(Field):
    def __init__(self, key: str, subtypes: Dict[Any, Union[Field, Schema, type]], **kwargs):
        super().__init__(**kwargs)
        self.key = key

        def map_subtype(subtype):
            if isinstance(subtype, Field):
                return subtype
            if isinstance(subtype, Schema):
                return NestedField(subtype)
            if isinstance(subtype, type):
                if issubclass(subtype, Schema):
                    return NestedField(subtype)
                else:
                    return NestedField(subtype.Schema)
            raise TypeError("invalid subtype '{}'".format(subtype))

        self.subtypes = {key: map_subtype(subtype) for key, subtype in subtypes.items()}

    def _deserialize(self, value: Any, attr: Optional[str],
                     data: Optional[Mapping[str, Any]], **kwargs):
        if not isinstance(value, dict):
            raise ValidationError("value must be dict")

        subtype_name = value.pop(self.key, None)
        subtype = self.subtypes.get(subtype_name)
        if not subtype:
            raise ValidationError("unknown subtype '{}'".format(subtype_name))

        return subtype._deserialize(value, attr, data, **kwargs)

    def _serialize(self, value: Any, attr: str, obj: Any, **kwargs):
        subtype_name = self.get_value(value, self.key)
        subtype = self.subtypes.get(subtype_name)
        if not subtype:
            raise ValueError("unknown subtype '{}'".format(value))
        return subtype._serialize(value, attr, obj, **kwargs)
