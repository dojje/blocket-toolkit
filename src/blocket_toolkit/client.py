"""Thin wrapper around ``blocket_api`` returning compact, JSON-friendly records."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from blocket_api import BlocketAPI, BoatAd, CarAd, McAd, RecommerceAd

from .enums import (
    BoatSortOrder,
    BoatType,
    CarColor,
    CarModel,
    CarSortOrder,
    CarTransmission,
    CarWheelDrive,
    Category,
    Location,
    McModel,
    McSortOrder,
    McType,
    SortOrder,
    SubCategory,
)

AD_CLASSES: dict[str, type] = {
    "recommerce": RecommerceAd,
    "car": CarAd,
    "boat": BoatAd,
    "mc": McAd,
}

AD_TYPES: tuple[str, ...] = tuple(AD_CLASSES)

_LISTING_KEYS = (
    "id",
    "ad_id",
    "heading",
    "subheading",
    "location",
    "trade_type",
    "flags",
    "labels",
    "dealer_segment",
    "seller_type",
    "org_id",
)

_VEHICLE_KEYS = (
    "make",
    "model",
    "model_specification",
    "series",
    "registration_class",
    "vehicle_type",
    "regno",
    "year",
    "model_year",
    "mileage",
    "milage",
    "mileage_unit",
    "transmission",
    "fuel",
    "horsepower",
    "engine_volume",
    "volume",
    "length",
    "width",
    "length_feet",
    "motor_type",
    "motor_fuel",
    "motor_size",
    "class",
    "engine_type",
    "seats",
    "old_price",
)

_PRICE_UNITS_TO_DROP = {"TOTAL", "kr", "KR", "SEK"}


@dataclass
class Page:
    """One page of search results."""

    items: list[dict[str, Any]]
    page: int = 1
    last_page: int | None = None
    total: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "last_page": self.last_page,
            "total": self.total,
            "count": len(self.items),
            "items": self.items,
        }


def _iso(timestamp_ms: float) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).isoformat()


def compact_listing(doc: dict[str, Any]) -> dict[str, Any]:
    """Reduce a raw Blocket search hit to a flat, predictable record."""
    out: dict[str, Any] = {}

    for key in _LISTING_KEYS + _VEHICLE_KEYS:
        value = doc.get(key)
        if value is not None:
            out[key] = value

    if isinstance(out.get("id"), str) and out["id"].isdigit():
        out["id"] = int(out["id"])

    url = doc.get("canonical_url") or doc.get("url")
    if not url and doc.get("id") is not None:
        url = f"https://www.blocket.se/recommerce/forsale/item/{doc['id']}"
    if url:
        out["url"] = url

    image = doc.get("image")
    if isinstance(image, dict) and image.get("url"):
        out["image_url"] = image["url"]
    elif doc.get("image_url"):
        out["image_url"] = doc["image_url"]
    elif doc.get("image_urls"):
        out["image_urls"] = doc["image_urls"]

    price = doc.get("price")
    if isinstance(price, dict):
        out["price"] = price.get("amount")
        unit = price.get("price_unit")
        if unit and unit not in _PRICE_UNITS_TO_DROP:
            out["price_unit"] = unit
    elif isinstance(price, (int, float)):
        out["price"] = int(price)

    timestamp = doc.get("timestamp")
    if isinstance(timestamp, (int, float)):
        out["timestamp"] = timestamp
        out["published_at"] = _iso(timestamp)

    return out


def _slim_recommerce(payload: dict[str, Any]) -> dict[str, Any]:
    section = (payload.get("loaderData") or {}).get("item-recommerce") or {}
    item = section.get("itemData")
    if not isinstance(item, dict):
        return payload

    out = dict(item)
    images = item.get("images")
    if isinstance(images, list):
        urls = [
            image.get("url") or image.get("uri")
            for image in images
            if isinstance(image, dict) and (image.get("url") or image.get("uri"))
        ]
        if urls:
            out["image_urls"] = urls
    if section.get("jsonLd"):
        out["jsonLd"] = section["jsonLd"]
    if section.get("meta"):
        out["meta"] = section["meta"]
    return out


def _paging(raw: dict[str, Any], page: int) -> tuple[int, int | None, int | None]:
    meta = raw.get("metadata") or {}
    paging = meta.get("paging") or {}

    current = paging.get("current") or paging.get("page") or page
    last = paging.get("last") or paging.get("last_page") or paging.get("total_pages")

    tracking = meta.get("tracking") or {}
    tracking_object = tracking.get("object") or {}
    total = (
        (meta.get("result_size") or {}).get("match_count")
        or tracking_object.get("numItems")
        or meta.get("total")
        or meta.get("total_count")
    )

    def as_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return as_int(current) or page, as_int(last), as_int(total)


class BlocketClient:
    """Search Blocket.se for items, cars, boats and motorcycles."""

    def __init__(self, api: BlocketAPI | None = None) -> None:
        self._api = api if api is not None else BlocketAPI()

    def _page(self, raw: dict[str, Any], page: int, compact: bool) -> Page:
        docs = raw.get("docs") or []
        items = [compact_listing(doc) for doc in docs] if compact else docs
        current, last, total = _paging(raw, page)
        return Page(items=items, page=current, last_page=last, total=total)

    def search(
        self,
        query: str,
        *,
        page: int = 1,
        sort_order: SortOrder = SortOrder.RELEVANCE,
        locations: list[Location] | None = None,
        category: Category | None = None,
        sub_category: SubCategory | None = None,
        compact: bool = True,
    ) -> Page:
        """Search general items (torget)."""
        raw = self._api.search(
            query,
            page=page,
            sort_order=sort_order,
            locations=list(locations or []),
            category=category,
            sub_category=sub_category,
        )
        return self._page(raw, page, compact)

    def search_cars(
        self,
        query: str | None = None,
        *,
        page: int = 1,
        sort_order: CarSortOrder = CarSortOrder.RELEVANCE,
        locations: list[Location] | None = None,
        models: list[CarModel] | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        mileage_from: int | None = None,
        mileage_to: int | None = None,
        horsepower_from: int | None = None,
        horsepower_to: int | None = None,
        colors: list[CarColor] | None = None,
        transmissions: list[CarTransmission] | None = None,
        wheel_drive: list[CarWheelDrive] | None = None,
        compact: bool = True,
    ) -> Page:
        """Search used cars."""
        raw = self._api.search_car(
            query or None,
            page=page,
            sort_order=sort_order,
            locations=list(locations or []),
            models=list(models or []),
            price_from=price_from,
            price_to=price_to,
            year_from=year_from,
            year_to=year_to,
            milage_from=mileage_from,
            milage_to=mileage_to,
            horsepower_from=horsepower_from,
            horsepower_to=horsepower_to,
            colors=list(colors or []),
            transmissions=list(transmissions or []),
            wheel_drive=list(wheel_drive or []),
        )
        return self._page(raw, page, compact)

    def search_boats(
        self,
        query: str | None = None,
        *,
        page: int = 1,
        sort_order: BoatSortOrder = BoatSortOrder.RELEVANCE,
        locations: list[Location] | None = None,
        types: list[BoatType] | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
        length_from: int | None = None,
        length_to: int | None = None,
        compact: bool = True,
    ) -> Page:
        """Search used boats."""
        raw = self._api.search_boat(
            query or None,
            page=page,
            sort_order=sort_order,
            types=list(types or []),
            locations=list(locations or []),
            price_from=price_from,
            price_to=price_to,
            length_from=length_from,
            length_to=length_to,
        )
        return self._page(raw, page, compact)

    def search_mc(
        self,
        query: str | None = None,
        *,
        page: int = 1,
        sort_order: McSortOrder = McSortOrder.RELEVANCE,
        locations: list[Location] | None = None,
        models: list[McModel] | None = None,
        types: list[McType] | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
        engine_volume_from: int | None = None,
        engine_volume_to: int | None = None,
        compact: bool = True,
    ) -> Page:
        """Search used motorcycles."""
        raw = self._api.search_mc(
            query or None,
            page=page,
            sort_order=sort_order,
            models=list(models or []),
            types=list(types or []),
            locations=list(locations or []),
            price_from=price_from,
            price_to=price_to,
            engine_volume_from=engine_volume_from,
            engine_volume_to=engine_volume_to,
        )
        return self._page(raw, page, compact)

    def get_ad(
        self, ad_id: int, ad_type: str = "recommerce", raw: bool = False
    ) -> dict[str, Any]:
        """Fetch the full listing for a single ad.

        For ``recommerce`` listings the React-router hydration blob is reduced to
        the useful ``itemData`` payload unless ``raw`` is set.
        """
        ad_class = AD_CLASSES.get(ad_type)
        if ad_class is None:
            raise ValueError(f"Unknown ad type: {ad_type!r}. Valid: {', '.join(AD_TYPES)}")

        payload = self._api.get_ad(ad_class(int(ad_id)))
        if raw or ad_type != "recommerce":
            return payload
        return _slim_recommerce(payload)

    def paginate(
        self,
        fetch: Callable[[int], Page],
        *,
        start_page: int = 1,
        max_pages: int = 20,
    ) -> Iterator[Page]:
        """Yield consecutive pages from a ``fetch(page_number) -> Page`` callable."""
        page_no = start_page
        for _ in range(max_pages):
            page = fetch(page_no)
            yield page
            if not page.items:
                return
            if page.last_page is not None and page_no >= page.last_page:
                return
            page_no += 1
