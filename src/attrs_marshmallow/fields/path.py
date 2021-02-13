from pathlib import Path, PurePath
from typing import Type, Any, Optional, Mapping

from marshmallow.fields import Field


class PathField(Field):
    def __init__(self, path_cls: Type[PurePath] = Path, **kwargs):
        super().__init__(**kwargs)
        self.path_cls = path_cls

    def _serialize(self, value: Any, attr: str, obj: Any, **kwargs):
        return str(value)

    def _deserialize(self, value: Any, attr: Optional[str], data: Optional[Mapping[str, Any]], **kwargs):
        return self.path_cls(value)
