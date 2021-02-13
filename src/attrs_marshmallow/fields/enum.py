from enum import Enum
from typing import Type, Any, Optional, Mapping

from marshmallow.fields import Field


class EnumField(Field):
    default_error_messages = {
        "unknown_variant": "Unknown enum variant {value}",
        "not_enum": "{value} is not an instance of {enum_cls}",
        "not_str": "Value must be string, got {value_type}"
    }

    def __init__(self, enum_cls: Type[Enum], **kwargs):
        super().__init__(**kwargs)
        self.enum_cls = enum_cls

    def _serialize(self, value: Enum, attr: str, obj: Any, **kwargs):
        if type(value) != self.enum_cls:
            raise self.make_error("not_enum", value=value, enum_cls=self.enum_cls)

        return value.name

    def _deserialize(self, value: Any, attr: Optional[str], data: Optional[Mapping[str, Any]], **kwargs):
        if value and not isinstance(value, str):
            raise self.make_error("not_str", value_type=type(value))

        try:
            return self.enum_cls[value]
        except KeyError:
            raise self.make_error("unknown_variant", value=value) from None
