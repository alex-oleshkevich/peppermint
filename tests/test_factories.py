from __future__ import annotations

import datetime

from peppermint import call, gen, ignore, lazy, seq, sub, sub_list
from peppermint.factories import Factory


class _TagFactory(Factory):
    id = seq()
    name = gen().string(12)


class _AddressFactory(Factory):
    street = gen().string(20)
    city = gen().string(10)
    postal_code = gen().string(6, "0123456789")
    country_code = "CH"


class _ProfileFactory(Factory):
    bio = gen().string(50)
    avatar_url = lazy(lambda x: f"https://cdn.example.com/avatars/{x.registered_at}.jpg")
    birthdate = lazy(lambda _: datetime.date(1990, 1, 1))  # simplified for testing
    registered_at = call(datetime.datetime.now)


class _UserFactory(Factory):
    id = seq()
    username = gen().string(15)
    email = seq("{:d}@example.com")
    is_active = gen().choice([True, False])
    address = sub(_AddressFactory)
    profile = sub(_ProfileFactory)
    tags = sub_list(_TagFactory, count=3, attrs={"name": "name"})
    ignored_field = ignore()
    children = sub_list(lambda: _UserFactory, count=2, attrs={"children": []})


def test_dict_factory() -> None:
    data = _UserFactory.build()
    print(data)
    # assert data == {"id": 1, "name": "i0VpEBOWfbZA"}
