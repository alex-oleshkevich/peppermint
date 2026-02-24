import pytest

from peppermint import configure


@pytest.fixture(autouse=True, scope="session")
def _seed() -> None:
    configure(seed=1)
