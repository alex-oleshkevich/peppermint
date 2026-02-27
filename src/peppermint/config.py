import dataclasses
import random
import time
import uuid

import faker as fakerlib


@dataclasses.dataclass
class Config:
    locale: str
    seed: int


global_config = Config(
    locale="en",
    seed=time.time_ns(),
)


def configure(
    *,
    locale: str | None = None,
    faker: fakerlib.Faker | None = None,
    seed: int | None = None,
) -> None:
    if seed is None:
        seed = int(uuid.uuid4())

    if locale is not None:
        global_config.locale = locale

    global_config.seed = seed
    random.seed(seed)
