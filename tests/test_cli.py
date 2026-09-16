import json

import pytest

from blocket_toolkit import cli
from blocket_toolkit.client import Page


class FakeClient:
    instances = []

    def __init__(self, *args, **kwargs):
        self.calls = []
        FakeClient.instances.append(self)

    def _page(self, items):
        return Page(items=items, page=1, last_page=1, total=len(items))

    def search(self, query, **kwargs):
        self.calls.append(("search", query, kwargs))
        return self._page([{"id": 1, "heading": "Kindle", "price": 500, "timestamp": 1}])

    def search_cars(self, query=None, **kwargs):
        self.calls.append(("cars", query, kwargs))
        return self._page([{"id": 2, "heading": "Volvo", "price": 100000}])

    def search_boats(self, query=None, **kwargs):
        self.calls.append(("boats", query, kwargs))
        return self._page([{"id": 3, "heading": "Bayliner"}])

    def search_mc(self, query=None, **kwargs):
        self.calls.append(("mc", query, kwargs))
        return self._page([{"id": 4, "heading": "MT-07"}])

    def get_ad(self, ad_id, ad_type="recommerce", raw=False):
        self.calls.append(("ad", ad_id, ad_type, raw))
        return {"id": ad_id, "title": "Nice thing", "specifications": {"År": "2020"}}


@pytest.fixture(autouse=True)
def _fake_client(monkeypatch):
    FakeClient.instances = []
    monkeypatch.setattr(cli, "BlocketClient", FakeClient)


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])
    assert excinfo.value.code == 0


def test_missing_command_is_an_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])
    assert excinfo.value.code == 2


def test_search_prints_json_with_paging(capsys):
    assert cli.main(["search", "kindle"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["heading"] == "Kindle"
    assert payload["count"] == 1


def test_search_passes_resolved_filters():
    cli.main(
        [
            "search",
            "ram",
            "-l",
            "stockholm,skane",
            "-c",
            "elektronik_och_vitvaror",
            "--sort",
            "price_asc",
        ]
    )
    _, query, kwargs = FakeClient.instances[-1].calls[-1]
    assert query == "ram"
    assert [loc.name for loc in kwargs["locations"]] == ["STOCKHOLM", "SKANE"]
    assert kwargs["category"].name == "ELEKTRONIK_OCH_VITVAROR"
    assert kwargs["sort_order"].name == "PRICE_ASC"


def test_search_rejects_category_and_subcategory_together(capsys):
    code = cli.main(["search", "ram", "-c", "elektronik_och_vitvaror", "--sub-category", "datorer"])
    assert code == 2
    assert "--category" in capsys.readouterr().err


def test_search_rejects_unknown_category(capsys):
    code = cli.main(["search", "ram", "-c", "bogus"])
    assert code == 2
    assert "Unknown Category" in capsys.readouterr().err


def test_cars_maps_flags_to_api_kwargs():
    cli.main(
        [
            "cars",
            "-m",
            "volvo",
            "--year-min",
            "2015",
            "--mileage-max",
            "15000",
            "--price-max",
            "250000",
            "--transmission",
            "automatic",
        ]
    )
    _, _, kwargs = FakeClient.instances[-1].calls[-1]
    assert [m.name for m in kwargs["models"]] == ["VOLVO"]
    assert kwargs["year_from"] == 2015
    assert kwargs["mileage_to"] == 15000
    assert kwargs["price_to"] == 250000
    assert [t.name for t in kwargs["transmissions"]] == ["AUTOMATIC"]


def test_table_output_has_header(capsys):
    assert cli.main(["search", "kindle", "-o", "table"]) == 0
    out = capsys.readouterr().out
    assert "HEADING" in out
    assert "Kindle" in out


def test_limit_slices_results(capsys):
    cli.main(["search", "kindle", "-n", "0"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"] == []


def test_categories_lists_all(capsys):
    assert cli.main(["categories"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert any(item["name"] == "ELEKTRONIK_OCH_VITVAROR" for item in payload)


def test_subcategories_filtered_by_category(capsys):
    cli.main(["subcategories", "-c", "elektronik_och_vitvaror"])
    payload = json.loads(capsys.readouterr().out)
    assert all(item["category"] == "ELEKTRONIK_OCH_VITVAROR" for item in payload)
    assert any(item["name"] == "DATORER" for item in payload)


def test_ad_table_renders_pairs(capsys):
    assert cli.main(["ad", "123", "-o", "table"]) == 0
    out = capsys.readouterr().out
    assert "title: Nice thing" in out
