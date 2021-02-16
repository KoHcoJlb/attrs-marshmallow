# attrs-marshmallow

attrs-marshmallow is a Python library that generates [marshmallow](https://github.com/marshmallow-code/marshmallow)
schema for [attrs](https://github.com/python-attrs/attrs) decorated classes.

## Example

```python
from attrs_marshmallow import add_schema, marshmallow_opts


@add_schema
class Example:
    hello: str = marshmallow_opts()
    world: int


if __name__ == "__main__":
    e = Example(hello="value", world=3)
    data = e.Schema().dump(e)
    print(data)
```

## Usage remarks

To alter marshmallow field creation you can use `marshmallow_opts` function.

If you need further customization you can pass custom attr-to-field to `add_schema`/`attrs_schema` or register it
globally using `register_field_hook`.
