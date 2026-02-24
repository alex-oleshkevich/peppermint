from __future__ import annotations

import builtins
import decimal
import random
import typing
import uuid
from string import ascii_letters, digits

import faker

if typing.TYPE_CHECKING:
    from peppermint import Factory

T = typing.TypeVar("T", default=dict)


class ModelProxy:
    __slots__ = "_data"

    def __init__(self, data: object) -> None:
        self._data = data

    def __getattr__(self, name: str) -> object:
        if isinstance(self._data, typing.Mapping):
            mapping = typing.cast(typing.Mapping[str, object], self._data)
            try:
                return mapping[name]
            except KeyError:
                pass

        try:
            return getattr(self._data, name)
        except AttributeError:
            raise AttributeError(f'Field "{name}" not yet resolved or does not exist.') from None


class Descriptor[T]:
    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> T:
        raise NotImplementedError


class StaticValue(Descriptor[T]):
    __slots__ = ("value",)

    def __init__(self, value: T) -> None:
        self.value = value

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> T:
        return self.value


class LazyDescriptor(Descriptor[T]):
    __slots__ = ("_func",)

    def __init__(self, func: typing.Callable[[ModelProxy], T]) -> None:
        self._func = func

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> T:
        return self._func(model_proxy)


PS = typing.ParamSpec("PS")


class CallDescriptor(Descriptor[T]):
    __slots__ = ("_args", "_func", "_kwargs")

    def __init__(
        self,
        func: typing.Callable[PS, T],
        *args: PS.args,
        **kwargs: PS.kwargs,
    ) -> None:
        self._args = args
        self._kwargs = kwargs
        self._func = func

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> T:
        return self._func(*self._args, **self._kwargs)


class SequenceDescriptor(Descriptor[T | str | int]):
    __slots__ = ("_counter", "_format", "_func", "_start")

    def __init__(
        self,
        format: str | typing.Callable[[ModelProxy, int], T] | None = None,
        *,
        start: int = 1,
    ) -> None:
        self._func: typing.Callable[[ModelProxy, int], T] | None = None
        self._format: str | None = None

        if callable(format):
            self._func = typing.cast(typing.Callable[[ModelProxy, int], T], format)
        else:
            self._format = format

        self._start = start
        self._counter = start

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> T | str | int:
        n = self._counter
        self._counter += 1

        if self._func is not None:
            return self._func(model_proxy, n)

        if self._format is not None:
            return self._format.format(n)

        return n


class SubFactoryDescriptor(Descriptor[T]):
    __slots__ = ("_factory", "_kwargs")

    def __init__(
        self,
        factory: type[Factory[T]] | typing.Callable[[], type[Factory[T]]],
        attrs: dict[str, object] | None = None,
    ) -> None:
        self._factory = factory
        self._kwargs = attrs or {}

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> T:
        factory = self._factory
        if callable(factory):
            factory = factory()

        return factory.build(**self._kwargs)


class SubListFactoryDescriptor(Descriptor[list[T]]):
    __slots__ = ("_count", "_factory", "_kwargs")

    def __init__(
        self,
        factory: type[Factory[T]] | typing.Callable[[], type[Factory[T]]],
        *,
        count: int = 1,
        attrs: dict[str, object] | None = None,
    ) -> None:
        self._count = count
        self._factory = factory
        self._kwargs = attrs or {}

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> list[T]:
        factory = self._factory
        if callable(factory):
            factory = factory()

        return typing.cast(list[T], factory.build_batch(self._count, **self._kwargs))


class IgnoreDescriptor(Descriptor[typing.Never]):
    __slots__ = ()

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> typing.NoReturn:
        raise RuntimeError("IgnoreDescriptor should never be resolved.")


class _Gen:
    def decimal(
        self,
        min: builtins.float,
        max: builtins.float,
        places: builtins.int = 2,
    ) -> Descriptor:
        value = decimal.Decimal(str(random.uniform(min, max)))
        quantum = decimal.Decimal("1").scaleb(-places)
        return CallDescriptor(value.quantize, quantum, rounding=decimal.ROUND_HALF_UP)

    def normal(self, mean: builtins.float, stdev: builtins.float) -> Descriptor:
        if stdev < 0:
            raise ValueError("stdev must be >= 0.")
        return CallDescriptor(random.gauss, mean, stdev)

    def sample(self, sequence: typing.Sequence[T], k: builtins.int) -> Descriptor:
        return CallDescriptor(random.sample, sequence, k=k)

    def choices(
        self,
        sequence: typing.Sequence[T],
        k: builtins.int = 1,
        *,
        weights: typing.Sequence[builtins.float] | None = None,
    ) -> Descriptor:
        return CallDescriptor(random.choices, sequence, k=k, weights=weights)

    def uuid4(self) -> Descriptor:
        return CallDescriptor(uuid.uuid4)

    def string(self, length: builtins.int, alphabet: str = ascii_letters + digits) -> Descriptor:
        if length < 0:
            raise ValueError("length must be >= 0.")
        if not alphabet and length > 0:
            raise ValueError("alphabet cannot be empty when length > 0.")
        return CallDescriptor(lambda: "".join(random.choices(alphabet, k=length)))

    def bool(self) -> Descriptor:
        return CallDescriptor(random.choice, [True, False])

    def bytes(self, n: builtins.int) -> Descriptor:
        if n < 0:
            raise ValueError("n must be >= 0.")
        return CallDescriptor(random.randbytes, n)

    def int(self, min: builtins.int, max: builtins.int) -> Descriptor:
        return CallDescriptor(random.randint, min, max)

    def float(self, min: builtins.float, max: builtins.float) -> Descriptor:
        return CallDescriptor(random.uniform, min, max)

    def choice(self, sequence: typing.Sequence[T]) -> Descriptor:
        return CallDescriptor(random.choice, sequence)
