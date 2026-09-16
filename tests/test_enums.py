import pytest

from blocket_toolkit.enums import (
    Category,
    Location,
    SubCategory,
    enum_items,
    resolve,
    resolve_many,
    subcategories_of,
)


def test_resolve_by_name_is_case_insensitive():
    assert resolve(Category, "elektronik_och_vitvaror") is Category.ELEKTRONIK_OCH_VITVAROR
    assert resolve(Category, "ELEKTRONIK_OCH_VITVAROR") is Category.ELEKTRONIK_OCH_VITVAROR


def test_resolve_accepts_spaces_and_dashes():
    assert resolve(Category, "Elektronik och vitvaror") is Category.ELEKTRONIK_OCH_VITVAROR
    assert resolve(Location, "vastra-gotaland") is Location.VASTRA_GOTALAND


def test_resolve_by_raw_id():
    assert resolve(Category, "0.93") is Category.ELEKTRONIK_OCH_VITVAROR
    assert resolve(Location, "0.300001") is Location.STOCKHOLM


def test_resolve_unknown_raises_with_hint():
    with pytest.raises(ValueError) as excinfo:
        resolve(Category, "nope")
    assert "ELEKTRONIK_OCH_VITVAROR" in str(excinfo.value)


def test_resolve_empty_raises():
    with pytest.raises(ValueError):
        resolve(Category, "")


def test_resolve_many_flattens_and_splits():
    result = resolve_many(Location, ["stockholm,skane", "UPPSALA"])
    assert result == [Location.STOCKHOLM, Location.SKANE, Location.UPPSALA]


def test_resolve_many_none_is_empty():
    assert resolve_many(Location, None) == []


def test_subcategories_of_groups_by_prefix():
    subs = subcategories_of(Category.ELEKTRONIK_OCH_VITVAROR)
    assert SubCategory.DATORER in subs
    assert SubCategory.HUNDAR not in subs
    assert all(str(sub.value).startswith("1.93.") for sub in subs)


def test_every_subcategory_belongs_to_exactly_one_category():
    seen = {sub for category in Category for sub in subcategories_of(category)}
    assert seen == set(SubCategory)


def test_enum_items_are_sorted_name_id_dicts():
    items = enum_items(Category)
    assert all(set(item) == {"name", "id"} for item in items)
    assert [item["name"] for item in items] == sorted(item["name"] for item in items)
