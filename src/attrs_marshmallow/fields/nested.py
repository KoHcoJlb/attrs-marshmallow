import marshmallow
from marshmallow import Schema
from marshmallow.fields import Nested


class NestedField(Nested):
    @property
    def schema(self):
        schema = super().schema
        if not self.unknown:
            if isinstance(self.parent, Schema):
                schema.unknown = self.parent.unknown
            elif isinstance(self.parent, marshmallow.fields.List) or isinstance(self.parent, marshmallow.fields.Dict):
                schema.unknown = self.parent.parent.unknown
        return schema
