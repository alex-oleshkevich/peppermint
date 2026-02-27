import dataclasses
import datetime
import decimal
import enum
import time
import typing
import uuid

import faker

from peppermint import descriptors
from peppermint.config import Config, global_config
from peppermint.descriptors import (
    AutoDescriptor,
    Descriptor,
    LazyDescriptor,
    ModelProxy,
)
from peppermint.traits import Trait

T = typing.TypeVar("T")


def iter_items[T = typing.Any](obj: typing.Mapping[str, T]) -> typing.Iterator[tuple[str, T]]:
    for attr_name, attr_value in obj.items():
        if attr_name.startswith("__"):
            continue
        if attr_name in ["_declarations", "_traits"]:
            continue

        if isinstance(attr_value, (classmethod, property, staticmethod)):
            continue

        yield attr_name, attr_value


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


def _collect_definitions_from_dataclass(model_class: typing.Any, manual_descriptors: set[str]) -> dict[str, Descriptor]:
    descriptors: dict[str, Descriptor] = {}
    hints = typing.get_type_hints(model_class)

    for attr_name, attr_type in iter_items(hints):
        if attr_name in manual_descriptors:
            continue

        field_type = attr_type
        descriptors[attr_name] = AutoDescriptor(attr_name, field_type)

    return descriptors


class DescriptorExtractor(typing.Protocol):
    def __call__(self, model_class: object, manual_descriptors: set[str]) -> dict[str, Descriptor]: ...


def smart_extractor(model_class: object, manual_descriptors: set[str]) -> dict[str, Descriptor]:
    if dataclasses.is_dataclass(model_class):
        return _collect_definitions_from_dataclass(model_class, manual_descriptors)

    if hasattr(model_class, "__annotations__"):
        return _collect_definitions_from_dataclass(model_class, manual_descriptors)

    raise RuntimeError(f"Unsupported model class: {model_class!r}")


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

        try:
            orig_bases = attrs.get("__orig_bases__")
            base_args = getattr(orig_bases[0], "__args__", None)  # type: ignore
            args_tuple = typing.cast(tuple[object, ...], base_args)
            model_class = args_tuple[0]
        except (KeyError, TypeError):
            model_class = dict
        else:
            extractor = typing.cast(DescriptorExtractor, attrs.get("__descriptor_extractor__", smart_extractor))
            declarations.update(extractor(model_class, set(declarations.keys())))

        locale = typing.cast(str, attrs.get("__locale__", global_config.locale))
        seed = typing.cast(int, attrs.get("__seed__", global_config.seed))
        faker_ = faker.Faker(locale)
        faker_.seed_instance(seed)

        attrs.update(
            {
                "_declarations": declarations,
                "_traits": traits,
                "__model_class__": model_class,
                "__faker__": faker_,
            }
        )
        return super().__new__(cls, name, bases, attrs)


class BuildStrategy(typing.Protocol[T]):
    def __call__(self, model_class: object, attrs: dict[str, typing.Any]) -> T: ...


class Factory[T](metaclass=FactoryMeta):
    __model_class__: type[T]
    __locale__: str
    __faker__: faker.Faker
    __seed__: int
    __build_strategy__: typing.Literal["setattr", "init"] | BuildStrategy[T] = "init"
    __descriptor_extractor__ = smart_extractor

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
        faker = cls.__faker__

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
    def to_dict(cls, overrides: dict[str, object] | None = None) -> dict[str, object]:
        attrs = cls._resolve()
        attrs.update(overrides or {})
        return attrs

    @classmethod
    def to_json_dict(cls, overrides: dict[str, object] | None = None) -> dict[str, object]:
        attrs = cls.to_dict(overrides)
        return typing.cast(dict[str, object], _jsonify(attrs))

    @classmethod
    def build(cls, **overrides: object) -> T:
        attrs = cls._resolve(overrides=overrides)
        if callable(cls.__build_strategy__):
            return cls.__build_strategy__(cls.__model_class__, attrs)

        if cls.__build_strategy__ == "init":
            return cls.__model_class__(**attrs)

        instance = cls.__model_class__()
        for attr_name, attr_value in attrs.items():
            setattr(instance, attr_name, attr_value)

        return instance

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
