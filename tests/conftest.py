import pytest

from tfs.world.shops import world


@pytest.fixture(scope="session")
def shops():
    return world(6101)
