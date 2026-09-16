import time

import pytest

from blocket_toolkit.cli import _filter_local, _price_of
from blocket_toolkit.client import (
    BlocketClient,
    Page,
    _slim_recommerce,
    compact_listing,
)


class FakeAPI:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return self.pages[min(kwargs.get("page", 1), len(self.pages)) - 1]

    def search_car(self, query=None, **kwargs):
        self.calls.append((query, kwargs))
        return self.pages[min(kwargs.get("page", 1), len(self.pages)) - 1]


def _raw_page(docs, current=1, last=1, total=None):
    return {
        "docs": docs,
        "metadata": {
            "paging": {"current": current, "last": last},
            "result_size": {"match_count": total if total is not None else len(docs)},
            "num_results": len(docs),
        },
    }


def test_compact_listing_flattens_price_and_adds_url_and_timestamp():
    doc = {
        "id": 123,
        "heading": "Kindle Paperwhite",
        "canonical_url": "https://www.blocket.se/annons/123",
        "price": {"amount": 750, "currency_code": "SEK", "price_unit": "TOTAL"},
        "image": {"url": "https://img/1.jpg"},
        "location": "Stockholm",
        "timestamp": 1_700_000_000_000,
        "irrelevant": "drop me",
    }
    out = compact_listing(doc)
    assert out["price"] == 750
    assert "price_unit" not in out
    assert out["url"] == "https://www.blocket.se/annons/123"
    assert out["image_url"] == "https://img/1.jpg"
    assert out["published_at"].startswith("2023-11-14")
    assert "irrelevant" not in out


def test_compact_listing_falls_back_to_constructed_url():
    out = compact_listing({"id": 7})
    assert out["url"].endswith("/item/7")


def test_compact_listing_keeps_price_unit_when_not_total():
    out = compact_listing({"id": 1, "price": {"amount": 100, "price_unit": "PER_MONTH"}})
    assert out["price_unit"] == "PER_MONTH"


def test_compact_listing_drops_noisy_price_units():
    out = compact_listing({"id": 1, "price": {"amount": 100, "price_unit": "kr"}})
    assert "price_unit" not in out


def test_compact_listing_normalizes_string_id():
    out = compact_listing({"id": "26586567"})
    assert out["id"] == 26586567


def test_compact_listing_keeps_non_numeric_id():
    out = compact_listing({"id": "abc"})
    assert out["id"] == "abc"


def test_search_returns_page_with_paging_metadata():
    api = FakeAPI([_raw_page([{"id": 1}, {"id": 2}], current=2, last=5, total=100)])
    client = BlocketClient(api=api)
    page = client.search("iphone", page=2)
    assert isinstance(page, Page)
    assert [item["id"] for item in page.items] == [1, 2]
    assert page.page == 2
    assert page.last_page == 5
    assert page.total == 100
    assert api.calls[0][1]["page"] == 2


def test_total_falls_back_to_tracking_num_items():
    api = FakeAPI(
        [
            {
                "docs": [{"id": 1}],
                "metadata": {
                    "paging": {"current": 1, "last": 1},
                    "num_results": 1,
                    "tracking": {"object": {"numItems": 4321}},
                },
            }
        ]
    )
    page = BlocketClient(api=api).search("x")
    assert page.total == 4321


def test_search_raw_is_not_compacted():
    api = FakeAPI([_raw_page([{"id": 1, "price": {"amount": 5}}])])
    client = BlocketClient(api=api)
    page = client.search("x", compact=False)
    assert page.items[0]["price"] == {"amount": 5}


def test_paginate_stops_at_last_page():
    api = FakeAPI(
        [
            _raw_page([{"id": 1}], current=1, last=2),
            _raw_page([{"id": 2}], current=2, last=2),
        ]
    )
    client = BlocketClient(api=api)
    pages = list(client.paginate(lambda p: client.search("x", page=p)))
    assert len(pages) == 2


def test_paginate_respects_max_pages():
    api = FakeAPI([_raw_page([{"id": 1}], current=1, last=99) for _ in range(10)])
    client = BlocketClient(api=api)
    pages = list(client.paginate(lambda p: client.search("x", page=p), max_pages=3))
    assert len(pages) == 3


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"price": {"amount": 500}}, 500),
        ({"price": 500}, 500),
        ({"price": "500"}, None),
        ({}, None),
    ],
)
def test_price_of(item, expected):
    assert _price_of(item) == expected


def test_slim_recommerce_extracts_item_data():
    payload = {
        "loaderData": {
            "item-recommerce": {
                "itemData": {
                    "title": "Kindle",
                    "price": 500,
                    "images": [{"url": "u1"}, {"url": "u2"}],
                },
                "jsonLd": {"@type": "Product"},
            }
        }
    }
    out = _slim_recommerce(payload)
    assert out["title"] == "Kindle"
    assert out["image_urls"] == ["u1", "u2"]
    assert out["jsonLd"] == {"@type": "Product"}


def test_slim_recommerce_passthrough_without_item_data():
    payload = {"loaderData": {"root": {}}}
    assert _slim_recommerce(payload) == payload


def test_filter_local_price_and_recency():
    now_ms = time.time() * 1000
    items = [
        {"id": 1, "price": {"amount": 100}, "timestamp": now_ms},
        {"id": 2, "price": {"amount": 9000}, "timestamp": now_ms},
        {"id": 3, "price": {"amount": 100}, "timestamp": now_ms - 10 * 3600 * 1000},
        {"id": 4},
    ]
    kept = _filter_local(items, price_min=50, price_max=1000, newer_than=1)
    assert [item["id"] for item in kept] == [1]
