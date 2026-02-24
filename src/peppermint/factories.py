import dataclasses
import datetime
import decimal
import enum
import typing
import uuid

from peppermint import descriptors
from peppermint.config import Config, global_config
from peppermint.descriptors import (
    LazyDescriptor,
    ModelProxy,
)
from peppermint.traits import Trait

T = typing.TypeVar("T")


def _collect_definitions(
    attrs: typing.Mapping[str, object],
) -> tuple[dict[str, object], dict[str, Trait]]:
    declarations: dict[str, object] = {}
    traits: dict[str, Trait] = {}

    for attr_name, attr_value in attrs.items():
        if attr_name.startswith("__"):
            continue

        if attr_name in ["_declarations", "_traits"]:
            continue

        if isinstance(attr_value, (classmethod, property, staticmethod)):
            continue

        if isinstance(attr_value, descriptors.Descriptor):
            declarations[attr_name] = attr_value
            continue

        if isinstance(attr_value, Trait):
            traits[attr_name] = attr_value
            continue

        declarations[attr_name] = descriptors.StaticValue(attr_value)
    return declarations, traits


class FactoryMeta(type):
    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        attrs: dict[str, object],
    ) -> type:
        if name == "Factory":
            return super().__new__(cls, name, bases, attrs)

        declarations: dict[str, object] = {}
        traits: dict[str, Trait] = {}

        for base in reversed(bases):
            base_declarations, base_traits = _collect_definitions(base.__dict__)
            declarations.update(base_declarations)
            traits.update(base_traits)

        instance_declarations, instance_traits = _collect_definitions(attrs)
        declarations.update(instance_declarations)
        traits.update(instance_traits)

        model_class: type[object] = dict
        orig_bases = attrs.get("__orig_bases__")
        if isinstance(orig_bases, tuple) and orig_bases:
            base_args = getattr(orig_bases[0], "__args__", None)
            if isinstance(base_args, tuple) and base_args:
                args_tuple = typing.cast(tuple[object, ...], base_args)
                if isinstance(args_tuple[0], type):
                    model_class = args_tuple[0]

        attrs.update(
            {
                "_declarations": declarations,
                "_traits": traits,
                "__model_class__": model_class,
                "__config__": attrs.get("__config__", global_config),
            }
        )
        return super().__new__(cls, name, bases, attrs)


class Factory[T](metaclass=FactoryMeta):
    __model_class__: type[T]
    __config__: Config

    _declarations: typing.ClassVar[dict[str, object]]
    _traits: typing.ClassVar[dict[str, Trait]]

    @classmethod
    def _get_declarations(cls) -> dict[str, object]:
        return cls._declarations

    @classmethod
    def _resolve(cls, *, overrides: dict[str, object] | None = None) -> dict[str, object]:
        resolved: dict[str, object] = {}
        ignored: set[str] = set()
        lazy_fields: list[tuple[str, LazyDescriptor]] = []
        resolved_overrides = overrides or {}
        faker = cls.__config__.faker

        for field_name, descriptor in cls._get_declarations().items():
            if field_name in resolved_overrides:
                continue

            if isinstance(descriptor, descriptors.IgnoreDescriptor):
                ignored.add(field_name)
                continue

            if isinstance(descriptor, descriptors.LazyDescriptor):
                lazy_fields.append((field_name, descriptor))
                continue

            if isinstance(descriptor, descriptors.Descriptor):
                resolved[field_name] = descriptor.resolve(faker, ModelProxy(resolved))

        for field_name, override_value in resolved_overrides.items():
            if field_name in ignored:
                continue

            resolved[field_name] = override_value

        for field_name, lazy_descriptor in lazy_fields:
            if field_name not in resolved_overrides:
                resolved[field_name] = lazy_descriptor.resolve(faker, ModelProxy(resolved))

        return resolved

    @classmethod
    def to_dict(cls, overrides: dict[str, object]) -> dict[str, object]:
        attrs = cls._resolve()
        attrs.update(overrides)
        return attrs

    @classmethod
    def to_jsonable(cls, overrides: dict[str, object]) -> dict[str, object]:
        attrs = cls.to_dict(overrides)
        return typing.cast(dict[str, object], _jsonify(attrs))

    @classmethod
    def build(cls, **overrides: object) -> T:
        attrs = cls._resolve(overrides=overrides)
        return cls.__model_class__(**attrs)

    @classmethod
    def build_batch(cls, count: int, **overrides: object) -> list[T]:
        return [cls.build(**overrides) for _ in range(count)]


def _jsonify(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, enum.Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonify(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonify(v) for v in value]
    return value
