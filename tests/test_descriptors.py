import datetime
import decimal
import uuid

import faker
import pytest

from peppermint import descriptors
from peppermint.descriptors import AutoDescriptor, ModelProxy
from peppermint.factories import Factory


class TestStaticValue:
    def test_returns_same_value(self) -> None:
        value = "test"
        descriptor = descriptors.StaticValue(value)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == "test"


class TestLazyDescriptor:
    def test_returns_callback_result(self) -> None:
        descriptor = descriptors.LazyDescriptor(lambda ns: "ok")
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == "ok"


class TestCallDescriptor:
    def test_calls_callback_without_args(self) -> None:
        descriptor = descriptors.CallDescriptor(lambda: "done")
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == "done"

    def test_passes_positional_args(self) -> None:
        descriptor = descriptors.CallDescriptor(lambda a, b: a + b, 2, 3)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 5

    def test_passes_keyword_args(self) -> None:
        descriptor = descriptors.CallDescriptor(
            lambda *, first, last: f"{first} {last}",
            first="Ada",
            last="Lovelace",
        )
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == "Ada Lovelace"

    def test_passes_positional_and_keyword_args(self) -> None:
        descriptor = descriptors.CallDescriptor(
            lambda greeting, *, name: f"{greeting}, {name}",
            "Hello",
            name="Alex",
        )
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == "Hello, Alex"


class TestSequenceDescriptor:
    def test_default_sequence_starts_at_one(self) -> None:
        descriptor = descriptors.SequenceDescriptor()
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 1

    def test_default_sequence_increments_each_call(self) -> None:
        descriptor = descriptors.SequenceDescriptor()
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 1
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 2
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 3

    def test_custom_start_value(self) -> None:
        descriptor = descriptors.SequenceDescriptor(start=10)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 10
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 11

    def test_string_format_applied(self) -> None:
        descriptor = descriptors.SequenceDescriptor(format="user-{:03d}")
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == "user-001"
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == "user-002"

    def test_callable_format_applied(self) -> None:
        descriptor = descriptors.SequenceDescriptor(format=lambda model_proxy, n: f"id-{n}")
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == "id-1"

    def test_callable_format_increments(self) -> None:
        descriptor = descriptors.SequenceDescriptor(format=lambda model_proxy, n: n * 10)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 10
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 20

    def test_instances_are_independent(self) -> None:
        first = descriptors.SequenceDescriptor()
        second = descriptors.SequenceDescriptor()
        assert first.resolve(faker.Faker(), ModelProxy({})) == 1
        assert first.resolve(faker.Faker(), ModelProxy({})) == 2
        assert second.resolve(faker.Faker(), ModelProxy({})) == 1


class TestIgnoreDescriptor:
    def test_resolve_raises_runtime_error(self) -> None:
        descriptor = descriptors.IgnoreDescriptor()
        with pytest.raises(RuntimeError, match="should never be resolved"):
            descriptor.resolve(faker.Faker(), ModelProxy({}))


class TestGen:
    def test_decimal_quantizes_places(self) -> None:
        descriptor = descriptors._Gen().decimal(1.0, 2.0, places=3)
        value = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert isinstance(value, decimal.Decimal)
        assert value.as_tuple().exponent == -3

    def test_normal_returns_float(self) -> None:
        value = descriptors._Gen().normal(10.0, 2.0).resolve(faker.Faker(), ModelProxy({}))
        assert isinstance(value, float)

    def test_normal_rejects_negative_stdev(self) -> None:
        with pytest.raises(ValueError, match="stdev must be >= 0"):
            descriptors._Gen().normal(10.0, -1.0)

    def test_sample_returns_k_items(self) -> None:
        value = descriptors._Gen().sample([1, 2, 3, 4], 2).resolve(faker.Faker(), ModelProxy({}))
        assert len(value) == 2
        assert set(value).issubset({1, 2, 3, 4})

    def test_choices_returns_list_of_length_k(self) -> None:
        value = descriptors._Gen().choices(["a", "b"], k=3).resolve(faker.Faker(), ModelProxy({}))
        assert len(value) == 3
        assert set(value).issubset({"a", "b"})

    def test_uuid4_returns_uuid(self) -> None:
        value = descriptors._Gen().uuid4().resolve(faker.Faker(), ModelProxy({}))
        assert isinstance(value, uuid.UUID)

    def test_string_returns_requested_length(self) -> None:
        value = descriptors._Gen().string(12, "abc").resolve(faker.Faker(), ModelProxy({}))
        assert len(value) == 12
        assert set(value).issubset({"a", "b", "c"})

    def test_string_rejects_negative_length(self) -> None:
        with pytest.raises(ValueError, match="length must be >= 0"):
            descriptors._Gen().string(-1)

    def test_string_rejects_empty_alphabet_with_positive_length(self) -> None:
        with pytest.raises(ValueError, match="alphabet cannot be empty"):
            descriptors._Gen().string(1, "")

    def test_bool_returns_bool(self) -> None:
        value = descriptors._Gen().bool().resolve(faker.Faker(), ModelProxy({}))
        assert isinstance(value, bool)

    def test_bytes_returns_requested_length(self) -> None:
        value = descriptors._Gen().bytes(8).resolve(faker.Faker(), ModelProxy({}))
        assert isinstance(value, bytes)
        assert len(value) == 8

    def test_bytes_rejects_negative_n(self) -> None:
        with pytest.raises(ValueError, match="n must be >= 0"):
            descriptors._Gen().bytes(-1)

    def test_int_within_bounds(self) -> None:
        value = descriptors._Gen().int(5, 10).resolve(faker.Faker(), ModelProxy({}))
        assert 5 <= value <= 10

    def test_float_within_bounds(self) -> None:
        value = descriptors._Gen().float(1.5, 2.5).resolve(faker.Faker(), ModelProxy({}))
        assert 1.5 <= value <= 2.5

    def test_choice_returns_member_from_sequence(self) -> None:
        value = descriptors._Gen().choice(["x", "y", "z"]).resolve(faker.Faker(), ModelProxy({}))
        assert value in {"x", "y", "z"}


class TestSubFactoryDescriptor:
    def test_builds_from_factory_class(self) -> None:
        class ChildFactory(Factory):
            id = 1

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == {"id": 1}

    def test_builds_from_factory_callable(self) -> None:
        class ChildFactory(Factory):
            id = 1

        descriptor = descriptors.SubFactoryDescriptor(lambda: ChildFactory)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == {"id": 1}

    def test_passes_attrs_to_factory_build(self) -> None:
        class ChildFactory(Factory):
            id = 1
            name = "default"

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory, attrs={"name": "Ada"})
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == {"id": 1, "name": "Ada"}

    def test_uses_empty_attrs_by_default(self) -> None:
        class ChildFactory(Factory):
            id = 1
            name = "default"

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == {"id": 1, "name": "default"}

    def test_callable_factory_invoked_at_resolve_time(self) -> None:
        class ChildFactory(Factory):
            id = 1

        calls = {"count": 0}

        def provider() -> type[Factory]:
            calls["count"] += 1
            return ChildFactory

        descriptor = descriptors.SubFactoryDescriptor(provider)
        descriptor.resolve(faker.Faker(), ModelProxy({}))
        descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert calls["count"] == 2

    def test_sub_factory_with_sequence_descriptor(self) -> None:
        class ChildFactory(Factory):
            id = descriptors.SequenceDescriptor(start=10)

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"id": 10}

    def test_sub_factory_with_static_value_descriptor(self) -> None:
        class ChildFactory(Factory):
            first_name = descriptors.StaticValue("Ada")

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"first_name": "Ada"}

    def test_sub_factory_with_call_descriptor(self) -> None:
        class ChildFactory(Factory):
            last_name = descriptors.CallDescriptor(lambda: "Byron")

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"last_name": "Byron"}

    def test_sub_factory_with_lazy_descriptor(self) -> None:
        class ChildFactory(Factory):
            first_name = descriptors.StaticValue("Ada")
            last_name = descriptors.StaticValue("Byron")
            full_name = descriptors.LazyDescriptor(lambda model: f"{model.first_name} {model.last_name}")

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {
            "first_name": "Ada",
            "last_name": "Byron",
            "full_name": "Ada Byron",
        }

    def test_sub_factory_with_gen_descriptor(self) -> None:
        class ChildFactory(Factory):
            lucky_number = descriptors._Gen().int(7, 7)

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"lucky_number": 7}

    def test_sub_factory_applies_multiple_overrides(self) -> None:
        class ChildFactory(Factory):
            id = descriptors.SequenceDescriptor(start=10)
            first_name = descriptors.StaticValue("Ada")
            last_name = descriptors.StaticValue("Byron")

        descriptor = descriptors.SubFactoryDescriptor(
            ChildFactory,
            attrs={"id": 99, "last_name": "Lovelace"},
        )
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"id": 99, "first_name": "Ada", "last_name": "Lovelace"}

    def test_sub_factory_with_sub_descriptor(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubFactoryDescriptor(NestedFactory)

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"nested": {"hello": "world"}}

    def test_sub_factory_with_sub_descriptor_with_override(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubFactoryDescriptor(NestedFactory, {"hello": "override"})

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"nested": {"hello": "override"}}

    def test_sub_factory_with_nested_list_descriptor(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubListFactoryDescriptor(NestedFactory)

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"nested": [{"hello": "world"}]}

    def test_sub_factory_with_nested_list_descriptor_with_override(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubListFactoryDescriptor(
                NestedFactory,
                attrs={"hello": "override"},
            )

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"nested": [{"hello": "override"}]}

    def test_sub_factory_with_nested_list_descriptor_with_count(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubListFactoryDescriptor(NestedFactory, count=2)

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"nested": [{"hello": "world"}, {"hello": "world"}]}

    def test_sub_factory_with_nested_list_descriptor_with_count_and_override(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubListFactoryDescriptor(
                NestedFactory,
                count=2,
                attrs={"hello": "override"},
            )

        descriptor = descriptors.SubFactoryDescriptor(ChildFactory)
        resolved = descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert resolved == {"nested": [{"hello": "override"}, {"hello": "override"}]}


class TestSubListFactoryDescriptor:
    def test_builds_from_factory_class(self) -> None:
        class ChildFactory(Factory):
            id = 1

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [{"id": 1}, {"id": 1}]

    def test_builds_from_factory_callable(self) -> None:
        class ChildFactory(Factory):
            id = 1

        descriptor = descriptors.SubListFactoryDescriptor(lambda: ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [{"id": 1}, {"id": 1}]

    def test_uses_default_count(self) -> None:
        class ChildFactory(Factory):
            id = 1

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [{"id": 1}]

    def test_uses_custom_count(self) -> None:
        class ChildFactory(Factory):
            id = 1

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=3)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"id": 1},
            {"id": 1},
            {"id": 1},
        ]

    def test_passes_attrs_to_factory_build(self) -> None:
        class ChildFactory(Factory):
            id = 1
            name = "default"

        descriptor = descriptors.SubListFactoryDescriptor(
            ChildFactory,
            count=2,
            attrs={"name": "Ada"},
        )
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"id": 1, "name": "Ada"},
            {"id": 1, "name": "Ada"},
        ]

    def test_applies_count_and_override(self) -> None:
        class ChildFactory(Factory):
            id = 1
            role = "user"

        descriptor = descriptors.SubListFactoryDescriptor(
            ChildFactory,
            count=3,
            attrs={"role": "admin"},
        )
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"id": 1, "role": "admin"},
            {"id": 1, "role": "admin"},
            {"id": 1, "role": "admin"},
        ]

    def test_callable_factory_invoked_at_resolve_time(self) -> None:
        class ChildFactory(Factory):
            id = 1

        calls = {"count": 0}

        def provider() -> type[Factory]:
            calls["count"] += 1
            return ChildFactory

        descriptor = descriptors.SubListFactoryDescriptor(provider, count=2)
        descriptor.resolve(faker.Faker(), ModelProxy({}))
        descriptor.resolve(faker.Faker(), ModelProxy({}))
        assert calls["count"] == 2

    def test_with_sequence_descriptor(self) -> None:
        class ChildFactory(Factory):
            id = descriptors.SequenceDescriptor(start=10)

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [{"id": 10}, {"id": 11}]

    def test_with_static_value_descriptor(self) -> None:
        class ChildFactory(Factory):
            first_name = descriptors.StaticValue("Ada")

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"first_name": "Ada"},
            {"first_name": "Ada"},
        ]

    def test_with_call_descriptor(self) -> None:
        class ChildFactory(Factory):
            last_name = descriptors.CallDescriptor(lambda: "Byron")

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"last_name": "Byron"},
            {"last_name": "Byron"},
        ]

    def test_with_lazy_descriptor(self) -> None:
        class ChildFactory(Factory):
            first_name = descriptors.StaticValue("Ada")
            last_name = descriptors.StaticValue("Byron")
            full_name = descriptors.LazyDescriptor(lambda model: f"{model.first_name} {model.last_name}")

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {
                "first_name": "Ada",
                "last_name": "Byron",
                "full_name": "Ada Byron",
            },
            {
                "first_name": "Ada",
                "last_name": "Byron",
                "full_name": "Ada Byron",
            },
        ]

    def test_with_gen_descriptor(self) -> None:
        class ChildFactory(Factory):
            lucky_number = descriptors._Gen().int(7, 7)

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"lucky_number": 7},
            {"lucky_number": 7},
        ]

    def test_with_sub_descriptor(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubFactoryDescriptor(NestedFactory)

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"nested": {"hello": "world"}},
            {"nested": {"hello": "world"}},
        ]

    def test_with_sub_descriptor_with_override(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubFactoryDescriptor(NestedFactory, {"hello": "override"})

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"nested": {"hello": "override"}},
            {"nested": {"hello": "override"}},
        ]

    def test_with_nested_list_descriptor(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubListFactoryDescriptor(NestedFactory)

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"nested": [{"hello": "world"}]},
            {"nested": [{"hello": "world"}]},
        ]

    def test_with_nested_list_descriptor_with_override(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubListFactoryDescriptor(
                NestedFactory,
                attrs={"hello": "override"},
            )

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"nested": [{"hello": "override"}]},
            {"nested": [{"hello": "override"}]},
        ]

    def test_with_nested_list_descriptor_with_count(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubListFactoryDescriptor(NestedFactory, count=2)

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"nested": [{"hello": "world"}, {"hello": "world"}]},
            {"nested": [{"hello": "world"}, {"hello": "world"}]},
        ]

    def test_with_nested_list_descriptor_with_count_and_override(self) -> None:
        class NestedFactory(Factory):
            hello = "world"

        class ChildFactory(Factory):
            nested = descriptors.SubListFactoryDescriptor(
                NestedFactory,
                count=2,
                attrs={"hello": "override"},
            )

        descriptor = descriptors.SubListFactoryDescriptor(ChildFactory, count=2)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == [
            {"nested": [{"hello": "override"}, {"hello": "override"}]},
            {"nested": [{"hello": "override"}, {"hello": "override"}]},
        ]


class TestAutoDescriptor:
    def _faker(self) -> faker.Faker:
        f = faker.Faker()
        f.seed_instance(1)
        return f

    def test_name_based_str_fields(self) -> None:
        f = self._faker()
        proxy = ModelProxy({})
        assert AutoDescriptor("first_name", str).resolve(f, proxy) == "Dennis"
        assert AutoDescriptor("last_name", str).resolve(f, proxy) == "Boone"
        assert AutoDescriptor("name", str).resolve(f, proxy) == "Dawn Simpson"
        assert AutoDescriptor("username", str).resolve(f, proxy) == "ykennedy"
        assert AutoDescriptor("job_title", str).resolve(f, proxy) == "Engineer, manufacturing systems"
        assert AutoDescriptor("email", str).resolve(f, proxy) == "freemanpatricia@example.com"
        assert AutoDescriptor("phone", str).resolve(f, proxy) == "(890)574-3915x00080"
        assert AutoDescriptor("street", str).resolve(f, proxy) == "083 Crosby Plaza Apt. 533"
        assert AutoDescriptor("city", str).resolve(f, proxy) == "Farleytown"
        assert AutoDescriptor("state", str).resolve(f, proxy) == "Nebraska"
        assert AutoDescriptor("country", str).resolve(f, proxy) == "Taiwan"
        assert AutoDescriptor("country_code", str).resolve(f, proxy) == "TH"
        assert AutoDescriptor("zipcode", str).resolve(f, proxy) == "84687"
        assert AutoDescriptor("company", str).resolve(f, proxy) == "Lopez Ltd"
        assert AutoDescriptor("description", str).resolve(f, proxy) == "Building four return represent view."
        assert AutoDescriptor("title", str).resolve(f, proxy) == "Medical travel couple exist."
        assert AutoDescriptor("slug", str).resolve(f, proxy) == "us-money-throughout"
        assert AutoDescriptor("url", str).resolve(f, proxy) == "https://www.sanchez-salinas.biz/"
        assert AutoDescriptor("ip", str).resolve(f, proxy) == "151.126.244.244"
        assert AutoDescriptor("ipv6", str).resolve(f, proxy) == "c69d:4bd8:b3fa:7aa7:e1fa:b9d8:8c7e:134f"
        assert AutoDescriptor("mac_address", str).resolve(f, proxy) == "84:bf:2c:e0:37:53"
        assert (
            AutoDescriptor("user_agent", str).resolve(f, proxy)
            == "Opera/9.92.(Windows NT 5.1; as-IN) Presto/2.9.161 Version/11.00"
        )
        assert AutoDescriptor("password", str).resolve(f, proxy) == "QjRp5QhU#2"
        assert (
            AutoDescriptor("token", str).resolve(f, proxy)
            == "110d035449c31eae1331fae4f496410806b40f0189d0f9270bb54be4673161e6"
        )
        assert AutoDescriptor("filename", str).resolve(f, proxy) == "natural.avi"
        assert AutoDescriptor("filepath", str).resolve(f, proxy) == "/arrive/last.avi"
        assert AutoDescriptor("mime_type", str).resolve(f, proxy) == "video/x-matroska"
        assert AutoDescriptor("timezone", str).resolve(f, proxy) == "Africa/Tunis"
        assert AutoDescriptor("locale", str).resolve(f, proxy) == "raj_IN"
        assert AutoDescriptor("color", str).resolve(f, proxy) == "#7c240e"

    def test_name_based_date_fields(self) -> None:
        f = self._faker()
        proxy = ModelProxy({})
        assert AutoDescriptor("birth_date", datetime.date).resolve(f, proxy) == datetime.date(1925, 9, 28)
        assert AutoDescriptor("start_date", datetime.date).resolve(f, proxy) == datetime.date(2017, 8, 4)
        assert AutoDescriptor("end_date", datetime.date).resolve(f, proxy) == datetime.date(2012, 11, 22)
        assert isinstance(AutoDescriptor("created_at", datetime.datetime).resolve(f, proxy), datetime.datetime)
        assert isinstance(AutoDescriptor("published_at", datetime.datetime).resolve(f, proxy), datetime.datetime)

    def test_name_based_int_fields(self) -> None:
        f = self._faker()
        proxy = ModelProxy({})
        assert AutoDescriptor("age", int).resolve(f, proxy) == 17
        assert AutoDescriptor("count", int).resolve(f, proxy) == 582
        assert AutoDescriptor("port", int).resolve(f, proxy) == 8271

    def test_int_id_is_positive(self) -> None:
        f = self._faker()
        proxy = ModelProxy({})
        assert AutoDescriptor("id", int).resolve(f, proxy) >= 1
        assert AutoDescriptor("pk", int).resolve(f, proxy) >= 1

    def test_type_based_fallbacks(self) -> None:
        f = self._faker()
        proxy = ModelProxy({})
        assert AutoDescriptor("score", float).resolve(f, proxy) == 129944532028.507
        assert AutoDescriptor("is_active", bool).resolve(f, proxy) is False
        assert isinstance(AutoDescriptor("happened_at", datetime.datetime).resolve(f, proxy), datetime.datetime)
        assert AutoDescriptor("on_date", datetime.date).resolve(f, proxy) == datetime.date(2006, 8, 5)
        assert isinstance(AutoDescriptor("at_time", datetime.time).resolve(f, proxy), datetime.time)
        assert isinstance(AutoDescriptor("amount", decimal.Decimal).resolve(f, proxy), decimal.Decimal)
        assert isinstance(AutoDescriptor("uid", uuid.UUID).resolve(f, proxy), uuid.UUID)

    def test_optional_str_unwrapped(self) -> None:
        f = self._faker()
        f.seed_instance(1)
        result = AutoDescriptor("first_name", str | None).resolve(f, ModelProxy({}))
        assert result == "Dennis"

    def test_unknown_type_returns_none(self) -> None:
        f = self._faker()
        result = AutoDescriptor("something", object).resolve(f, ModelProxy({}))
        assert result is None


class TestFakeDescriptor:
    def test_calls_named_faker_method(self) -> None:
        f = faker.Faker()
        f.seed_instance(1)
        descriptor = descriptors.FakeDescriptor("first_name")
        assert descriptor.resolve(f, ModelProxy({})) == "Dennis"

    def test_forwards_positional_args(self) -> None:
        f = faker.Faker()
        f.seed_instance(1)
        descriptor = descriptors.FakeDescriptor("pystr", min_chars=5, max_chars=5)
        result = descriptor.resolve(f, ModelProxy({}))
        assert isinstance(result, str)
        assert len(result) == 5

    def test_forwards_keyword_args(self) -> None:
        f = faker.Faker()
        descriptor = descriptors.FakeDescriptor("random_int", min=42, max=42)
        assert descriptor.resolve(f, ModelProxy({})) == 42

    def test_called_at_resolve_time_not_construction(self) -> None:
        f1 = faker.Faker()
        f1.seed_instance(1)
        f2 = faker.Faker()
        f2.seed_instance(2)
        descriptor = descriptors.FakeDescriptor("first_name")
        assert descriptor.resolve(f1, ModelProxy({})) == "Dennis"
        assert descriptor.resolve(f2, ModelProxy({})) == "Stephanie"

    def test_unknown_method_raises_attribute_error(self) -> None:
        descriptor = descriptors.FakeDescriptor("nonexistent_method_xyz")
        with pytest.raises(AttributeError):
            descriptor.resolve(faker.Faker(), ModelProxy({}))


class TestFakerProxy:
    def test_attribute_access_returns_callable(self) -> None:
        proxy = descriptors.FakerProxy()
        result = proxy.first_name
        assert callable(result)

    def test_call_produces_fake_descriptor(self) -> None:
        proxy = descriptors.FakerProxy()
        result = proxy.first_name()
        assert isinstance(result, descriptors.FakeDescriptor)

    def test_kwargs_forwarded_to_descriptor(self) -> None:
        proxy = descriptors.FakerProxy()
        descriptor = proxy.random_int(min=7, max=7)
        assert descriptor.resolve(faker.Faker(), ModelProxy({})) == 7

    def test_different_attributes_produce_different_methods(self) -> None:
        proxy = descriptors.FakerProxy()
        f = faker.Faker()
        f.seed_instance(1)
        first = proxy.first_name().resolve(f, ModelProxy({}))
        assert isinstance(first, str)
        last = proxy.last_name().resolve(f, ModelProxy({}))
        assert isinstance(last, str)
        assert first != last

    def test_used_in_factory(self) -> None:
        class _F(Factory):
            name = descriptors.FakerProxy().first_name()

        result = _F.build()
        assert isinstance(result["name"], str)
        assert len(result["name"]) > 0
