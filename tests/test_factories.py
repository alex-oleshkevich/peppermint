from __future__ import annotations

import dataclasses
import datetime

from peppermint import fake, lazy, seq
from peppermint.factories import Factory


class TestDictFactory:
    def test_infers_model_class(self) -> None:
        class _SomeFactory(Factory):
            id = seq()
            name = lazy(lambda _: "John Doe")

        assert _SomeFactory.__model_class__ is dict

    def test_to_dict(self) -> None:
        class _SomeFactory(Factory):
            id = seq()
            name = lazy(lambda _: "John Doe")

        assert _SomeFactory.to_dict() == {"id": 1, "name": "John Doe"}

    def test_to_dict_with_override(self) -> None:
        class _SomeFactory(Factory):
            id = seq()
            name = lazy(lambda _: "John Doe")

        assert _SomeFactory.to_dict({"name": "Jane Doe"}) == {"id": 1, "name": "Jane Doe"}

    def test_to_json_dict(self) -> None:

        class _SomeFactory(Factory):
            today = lazy(lambda _: datetime.date(2026, 1, 1))

        assert _SomeFactory.to_json_dict() == {"today": "2026-01-01"}

    def test_to_json_dict_with_override(self) -> None:

        class _SomeFactory(Factory):
            today = lazy(lambda _: datetime.date(2026, 1, 1))

        assert _SomeFactory.to_json_dict({"today": datetime.date(2025, 1, 1)}) == {"today": "2025-01-01"}

    def test_build(self) -> None:
        class _SomeFactory(Factory):
            id = seq()
            name = lazy(lambda _: "John Doe")

        result = _SomeFactory.build()
        assert result == {"id": 1, "name": "John Doe"}

    def test_build_with_overrides(self) -> None:
        class _SomeFactory(Factory):
            id = seq()
            name = lazy(lambda _: "John Doe")

        result = _SomeFactory.build(name="Jane Doe")
        assert result["name"] == "Jane Doe"

    def test_build_batch(self) -> None:
        class _SomeFactory(Factory):
            id = seq()

        results = _SomeFactory.build_batch(3)
        assert len(results) == 3
        assert [r["id"] for r in results] == [1, 2, 3]

    def test_build_batch_with_overrides(self) -> None:
        class _SomeFactory(Factory):
            id = seq()
            name = lazy(lambda _: "John Doe")

        results = _SomeFactory.build_batch(3, name="Jane Doe")
        assert all(r["name"] == "Jane Doe" for r in results)


class TestObjectFactory:
    def test_infers_model_class(self) -> None:
        class _SomeObject: ...

        class _SomeFactory(Factory[_SomeObject]):
            id = seq()
            name = lazy(lambda _: "John Doe")

        assert _SomeFactory.__model_class__ is _SomeObject

    def test_build(self) -> None:
        class _SomeObject:
            id: int
            name: str

        class _SomeFactory(Factory[_SomeObject]):
            id = seq()
            name = lazy(lambda _: "John Doe")

        result = _SomeFactory.build()
        assert result.id == 1
        assert result.name == "John Doe"

    def test_auto_detected_fields(self) -> None:
        class _SomeUser:
            id: int
            first_name: str
            last_name: str | None
            age: int
            city: str | None = "Warsaw"

        class _SomeFactory(Factory[_SomeUser]):
            id = seq()

        result = _SomeFactory.build()
        assert result.id == 1
        assert result.first_name == "Dennis"
        assert result.last_name == "Boone"
        assert result.age == 97
        assert result.city == "West Davidmouth"

    def test_auto_detected_fields_with_locale(self) -> None:
        class _SomeUser:
            id: int
            first_name: str
            last_name: str | None
            age: int
            city: str | None = "Warsaw"

        class _SomeFactory(Factory[_SomeUser]):
            __locale__ = "de"
            id = seq()

        result = _SomeFactory.build()
        assert result.id == 1
        assert result.first_name == "Franz"
        assert result.last_name == "Roskoth"
        assert result.age == 108
        assert result.city == "Greiz"


@dataclasses.dataclass
class _SomeObject:
    id: int
    name: str


class TestDataclassFactory:
    def test_infers_model_class(self) -> None:

        class _SomeFactory(Factory[_SomeObject]):
            id = seq()
            name = lazy(lambda _: "John Doe")

        assert _SomeFactory.__model_class__ is _SomeObject

    def test_build(self) -> None:
        class _SomeFactory(Factory[_SomeObject]):
            id = seq()
            name = lazy(lambda _: "John Doe")

        result = _SomeFactory.build()
        assert result.id == 1
        assert result.name == "John Doe"

    def test_auto_detected_fields(self) -> None:
        @dataclasses.dataclass
        class _SomeUser:
            id: int
            first_name: str
            last_name: str | None
            age: int
            city: str | None = "Warsaw"

        class _SomeFactory(Factory[_SomeUser]):
            id = seq()

        result = _SomeFactory.build()
        assert result.id == 1
        assert result.first_name == "Dennis"
        assert result.last_name == "Boone"
        assert result.age == 97
        assert result.city == "West Davidmouth"

    def test_auto_detected_fields_with_locale(self) -> None:
        @dataclasses.dataclass
        class _SomeUser:
            id: int
            first_name: str
            last_name: str | None
            age: int
            city: str | None = "Warsaw"

        class _SomeFactory(Factory[_SomeUser]):
            __locale__ = "de"
            id = seq()

        result = _SomeFactory.build()
        assert result.id == 1
        assert result.first_name == "Franz"
        assert result.last_name == "Roskoth"
        assert result.age == 108
        assert result.city == "Greiz"
