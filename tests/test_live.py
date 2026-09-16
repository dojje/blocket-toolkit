"""Smoke tests that hit the real Blocket API. Run with: pytest -m live"""

import pytest

from blocket_toolkit.client import BlocketClient
from blocket_toolkit.enums import CarModel, Location

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    return BlocketClient()


def test_live_search(client):
    page = client.search("iphone", locations=[Location.STOCKHOLM])
    assert page.items, "expected at least one hit for 'iphone'"
    first = page.items[0]
    assert first["id"]
    assert first["url"].startswith("http")


def test_live_cars(client):
    page = client.search_cars(models=[CarModel.VOLVO], price_to=300_000)
    assert page.items, "expected at least one Volvo"


def test_live_boats(client):
    page = client.search_boats(price_to=500_000)
    assert page.items, "expected at least one boat"


def test_live_mc(client):
    page = client.search_mc(price_to=200_000)
    assert page.items, "expected at least one motorcycle"


def test_live_ad_detail(client):
    page = client.search("cykel", locations=[Location.STOCKHOLM])
    ad_id = page.items[0]["id"]
    details = client.get_ad(ad_id)
    assert isinstance(details, dict)
    assert details, "ad detail payload should not be empty"
