from __future__ import annotations

import builtins
import datetime
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


class FakeDescriptor(Descriptor[T]):
    __slots__ = ("_args", "_kwargs", "_method_name")

    def __init__(self, method_name: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        self._method_name = method_name
        self._args = args
        self._kwargs = kwargs

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> T:
        method = getattr(faker, self._method_name)
        return method(*self._args, **self._kwargs)


class FakerProxy:
    def __getattr__(self, name: str) -> typing.Callable[..., FakeDescriptor]:
        def descriptor_factory(*args: typing.Any, **kwargs: typing.Any) -> FakeDescriptor:
            return FakeDescriptor(name, *args, **kwargs)

        return descriptor_factory


def _unwrap_optional(field_type: type) -> type:
    args = typing.get_args(field_type)
    if args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return field_type


class AutoDescriptor(Descriptor[typing.Any]):
    def __init__(self, field_name: str, field_type: type) -> None:
        self.field_name = field_name
        self.field_type = field_type

    def resolve(self, faker: faker.Faker, model_proxy: ModelProxy) -> typing.Any:
        ft = _unwrap_optional(self.field_type)
        name = self.field_name.lower().replace("_", "")

        match name:
            # identity
            case "id" | "uuid" | "pk" | "uid" if ft is uuid.UUID:
                return uuid.uuid4()
            case "id" | "pk" if ft is builtins.int:
                return faker.random_int(min=1)
            # person
            case "firstname" | "fname" if ft is str:
                return faker.first_name()
            case "lastname" | "lname" | "surname" | "familyname" if ft is str:
                return faker.last_name()
            case "fullname" | "name" | "displayname" if ft is str:
                return faker.name()
            case "username" | "login" if ft is str:
                return faker.user_name()
            case "jobtitle" | "position" | "role" | "occupation" if ft is str:
                return faker.job()
            # contact
            case "email" | "emailaddress" if ft is str:
                return faker.email()
            case "phone" | "phonenumber" | "mobile" if ft is str:
                return faker.phone_number()
            # address
            case "street" | "streetaddress" | "address" if ft is str:
                return faker.street_address()
            case "city" | "town" if ft is str:
                return faker.city()
            case "state" | "region" | "province" if ft is str:
                return faker.state()
            case "country" | "countryname" if ft is str:
                return faker.country()
            case "countrycode" if ft is str:
                return faker.country_code()
            case "zipcode" | "postalcode" | "postcode" if ft is str:
                return faker.postcode()
            # company
            case "companyname" | "company" | "organization" | "org" if ft is str:
                return faker.company()
            # text
            case "description" | "desc" | "bio" | "summary" | "note" | "notes" if ft is str:
                return faker.sentence()
            case "title" | "heading" if ft is str:
                return faker.sentence(nb_words=4)
            case "slug" if ft is str:
                return faker.slug()
            # web / network
            case "url" | "website" | "homepage" if ft is str:
                return faker.url()
            case "ipaddress" | "ip" | "ipv4" if ft is str:
                return faker.ipv4()
            case "ipv6" if ft is str:
                return faker.ipv6()
            case "macaddress" | "mac" if ft is str:
                return faker.mac_address()
            case "useragent" | "ua" if ft is str:
                return faker.user_agent()
            # security
            case "password" | "passwd" | "secret" if ft is str:
                return faker.password()
            case "token" | "accesstoken" | "apikey" if ft is str:
                return faker.sha256()
            # file / media
            case "filename" if ft is str:
                return faker.file_name()
            case "filepath" | "path" if ft is str:
                return faker.file_path()
            case "mimetype" | "contenttype" if ft is str:
                return faker.mime_type()
            # locale / display
            case "timezone" | "tz" if ft is str:
                return faker.timezone()
            case "locale" | "lang" | "language" if ft is str:
                return faker.locale()
            case "color" | "colour" | "hexcolor" if ft is str:
                return faker.hex_color()
            # temporal (date)
            case "birthdate" | "dob" | "dateofbirth" if ft is datetime.date:
                return faker.date_of_birth()
            case "startdate" | "fromdate" if ft is datetime.date:
                return faker.date_object()
            case "enddate" | "todate" | "expirydate" | "expiresat" if ft is datetime.date:
                return faker.date_object()
            # temporal (datetime)
            case "createdat" | "updatedat" | "deletedat" | "timestamp" if ft is datetime.datetime:
                return faker.date_time()
            case "publishedat" | "postedat" | "sentat" if ft is datetime.datetime:
                return faker.date_time()
            # numeric
            case "age" if ft is builtins.int:
                return faker.random_int(min=0, max=120)
            case "count" | "quantity" | "qty" | "total" if ft is builtins.int:
                return faker.random_int(min=0, max=1000)
            case "port" if ft is builtins.int:
                return faker.port_number()

        if ft is str:
            return faker.pystr()
        if ft is int:
            return faker.random_int()
        if ft is float:
            return faker.pyfloat()
        if ft is bool:
            return faker.boolean()
        if ft is datetime.datetime:
            return faker.date_time()
        if ft is datetime.date:
            return faker.date_object()
        if ft is datetime.time:
            return faker.time_object()
        if ft is decimal.Decimal:
            return faker.pydecimal()
        if ft is uuid.UUID:
            return uuid.uuid4()
        if ft is bytes:
            return faker.binary(length=16)
        if typing.get_origin(ft) is list:
            return []
        if typing.get_origin(ft) is dict:
            return {}
        return None
