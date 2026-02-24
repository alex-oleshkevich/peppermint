import dataclasses
import datetime


@dataclasses.dataclass
class Profile:
    id: int
    bio: str
    website: str


@dataclasses.dataclass
class User:
    id: int
    name: str
    birthdate: datetime.date
    active: bool
    country: str
    address: str
    profile: Profile
