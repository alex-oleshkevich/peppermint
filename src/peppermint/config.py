import dataclasses
import random
import uuid

import faker as fakerlib


@dataclasses.dataclass
class Config:
    locale: str
    faker: fakerlib.Faker


global_config = Config(
    locale="en",
    faker=fakerlib.Faker("en"),
)


def configure(
    *,
    locale: str | None = None,
    faker: fakerlib.Faker | None = None,
    seed: int | None = None,
) -> None:
    if seed is None:
        seed = int(uuid.uuid4())
    random.seed(seed)
    global_config.faker.seed_instance(seed)

    if locale is not None:
        global_config.locale = locale

    if faker is not None:
        faker.seed_instance(seed)
        global_config.faker = faker
