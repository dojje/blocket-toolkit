"""Command-line interface for blocket-toolkit."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from typing import Any

from httpx import HTTPStatusError, RequestError

from . import __version__
from .client import AD_TYPES, BlocketClient, Page
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
    enum_items,
    resolve,
    resolve_many,
    subcategories_of,
)
from .format import (
    BOAT_COLUMNS,
    CAR_COLUMNS,
    LISTING_COLUMNS,
    MC_COLUMNS,
    OPTION_COLUMNS,
    render,
    render_json,
    render_pairs,
)

Fetch = Callable[[int], Page]


def _sort_choices(enum_cls: type) -> list[str]:
    return [member.name for member in enum_cls]


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-o",
        "--output",
        choices=("json", "jsonl", "table"),
        default="json",
        help="Output format (default: json)",
    )
    common.add_argument(
        "--raw",
        action="store_true",
        help="Return Blocket's raw API objects instead of compacted records",
    )

    paging = argparse.ArgumentParser(add_help=False)
    paging.add_argument("--page", type=int, default=1, help="Page number, 1-based (default: 1)")
    paging.add_argument(
        "-n", "--limit", type=int, default=None, help="Maximum number of results to return"
    )
    paging.add_argument(
        "--all", action="store_true", dest="all_pages", help="Fetch all pages (see --max-pages)"
    )
    paging.add_argument(
        "--max-pages", type=int, default=20, help="Safety cap for --all (default: 20)"
    )

    locations = argparse.ArgumentParser(add_help=False)
    locations.add_argument(
        "-l",
        "--location",
        action="append",
        metavar="REGION",
        help="Region name or id (repeatable or comma-separated), e.g. STOCKHOLM,SKANE",
    )

    parser = argparse.ArgumentParser(
        prog="blocket-toolkit",
        description="Search all of Blocket.se — general items, cars, boats and motorcycles.",
    )
    parser.add_argument(
        "--version", action="version", version=f"blocket-toolkit {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p = sub.add_parser(
        "search",
        parents=[common, paging, locations],
        help="Search general items (torget)",
        description="Search general items on Blocket torget.",
    )
    p.add_argument("query", help="Search term")
    p.add_argument(
        "-c",
        "--category",
        help="Category name or id, e.g. ELEKTRONIK_OCH_VITVAROR or 0.93",
    )
    p.add_argument(
        "--sub-category", help="Subcategory name or id, e.g. DATORER or 1.93.3215"
    )
    p.add_argument(
        "--sort",
        type=str.upper,
        choices=_sort_choices(SortOrder),
        default="RELEVANCE",
    )
    p.add_argument("--price-min", type=int, default=None, help="Minimum price, SEK (client-side)")
    p.add_argument("--price-max", type=int, default=None, help="Maximum price, SEK (client-side)")
    p.add_argument(
        "--newer-than",
        type=float,
        default=None,
        metavar="HOURS",
        help="Only ads newer than N hours",
    )
    p.set_defaults(handler=_cmd_search)

    p = sub.add_parser(
        "cars",
        parents=[common, paging, locations],
        help="Search used cars",
        description="Search used cars on Blocket mobility.",
    )
    p.add_argument("query", nargs="?", default=None, help="Optional free-text search term")
    p.add_argument("-m", "--model", action="append", metavar="BRAND", help="Car brand, e.g. VOLVO")
    p.add_argument("--color", action="append", metavar="COLOR", help="Exterior colour, e.g. SVART")
    p.add_argument("--transmission", action="append", metavar="GEARBOX", help="AUTOMATIC or MANUAL")
    p.add_argument(
        "--wheel-drive", action="append", metavar="DRIVE", help="FWD, RWD, FOUR or TWO"
    )
    p.add_argument("--price-min", type=int, default=None, help="Minimum price, SEK")
    p.add_argument("--price-max", type=int, default=None, help="Maximum price, SEK")
    p.add_argument(
        "--year-min", type=int, default=None, dest="year_from", help="Earliest model year"
    )
    p.add_argument(
        "--year-max", type=int, default=None, dest="year_to", help="Latest model year"
    )
    p.add_argument(
        "--mileage-min",
        type=int,
        default=None,
        dest="mileage_from",
        help="Minimum milage, km",
    )
    p.add_argument(
        "--mileage-max",
        type=int,
        default=None,
        dest="mileage_to",
        help="Maximum milage, km",
    )
    p.add_argument(
        "--hp-min", type=int, default=None, dest="horsepower_from", help="Minimum horsepower"
    )
    p.add_argument(
        "--hp-max", type=int, default=None, dest="horsepower_to", help="Maximum horsepower"
    )
    p.add_argument(
        "--sort", type=str.upper, choices=_sort_choices(CarSortOrder), default="RELEVANCE"
    )
    p.set_defaults(handler=_cmd_cars)

    p = sub.add_parser(
        "boats",
        parents=[common, paging, locations],
        help="Search used boats",
        description="Search used boats on Blocket mobility.",
    )
    p.add_argument("query", nargs="?", default=None, help="Optional free-text search term")
    p.add_argument(
        "-t",
        "--type",
        action="append",
        metavar="TYPE",
        help="Boat type, e.g. SEGELBAT_MOTORSEGLARE",
    )
    p.add_argument("--price-min", type=int, default=None, help="Minimum price, SEK")
    p.add_argument("--price-max", type=int, default=None, help="Maximum price, SEK")
    p.add_argument(
        "--length-min", type=int, default=None, dest="length_from", help="Minimum length, feet"
    )
    p.add_argument(
        "--length-max", type=int, default=None, dest="length_to", help="Maximum length, feet"
    )
    p.add_argument(
        "--sort", type=str.upper, choices=_sort_choices(BoatSortOrder), default="RELEVANCE"
    )
    p.set_defaults(handler=_cmd_boats)

    p = sub.add_parser(
        "mc",
        parents=[common, paging, locations],
        help="Search used motorcycles",
        description="Search used motorcycles on Blocket mobility.",
    )
    p.add_argument("query", nargs="?", default=None, help="Optional free-text search term")
    p.add_argument("-m", "--model", action="append", metavar="BRAND", help="MC brand, e.g. YAMAHA")
    p.add_argument("-t", "--type", action="append", metavar="TYPE", help="MC type, e.g. SPORT")
    p.add_argument("--price-min", type=int, default=None, help="Minimum price, SEK")
    p.add_argument("--price-max", type=int, default=None, help="Maximum price, SEK")
    p.add_argument(
        "--engine-min",
        type=int,
        default=None,
        dest="engine_volume_from",
        help="Minimum engine volume, cc",
    )
    p.add_argument(
        "--engine-max",
        type=int,
        default=None,
        dest="engine_volume_to",
        help="Maximum engine volume, cc",
    )
    p.add_argument(
        "--sort", type=str.upper, choices=_sort_choices(McSortOrder), default="RELEVANCE"
    )
    p.set_defaults(handler=_cmd_mc)

    p = sub.add_parser(
        "ad",
        parents=[common],
        help="Fetch one listing",
        description="Fetch the full listing for an ad id.",
    )
    p.add_argument("ad_id", type=int, help="The ad id from a search result")
    p.add_argument(
        "--type", choices=AD_TYPES, default="recommerce", help="Listing kind (default: recommerce)"
    )
    p.set_defaults(handler=_cmd_ad)

    p = sub.add_parser(
        "categories",
        parents=[common],
        help="List categories",
        description="List all general item categories.",
    )
    p.set_defaults(handler=_cmd_categories)

    p = sub.add_parser(
        "subcategories",
        parents=[common],
        help="List subcategories",
        description="List subcategories, optionally for a single category.",
    )
    p.add_argument("-c", "--category", help="Restrict to one category")
    p.set_defaults(handler=_cmd_subcategories)

    p = sub.add_parser(
        "locations",
        parents=[common],
        help="List regions",
        description="List all Swedish regions.",
    )
    p.set_defaults(handler=_cmd_locations)

    p = sub.add_parser(
        "car-options",
        parents=[common],
        help="List car filter options",
        description="List car brands, colours, gearboxes and sort orders.",
    )
    p.set_defaults(handler=_cmd_car_options)

    p = sub.add_parser(
        "boat-options",
        parents=[common],
        help="List boat filter options",
        description="List boat types and sort orders.",
    )
    p.set_defaults(handler=_cmd_boat_options)

    p = sub.add_parser(
        "mc-options",
        parents=[common],
        help="List motorcycle filter options",
        description="List MC brands, types and sort orders.",
    )
    p.set_defaults(handler=_cmd_mc_options)

    return parser


def _gather(fetch: Fetch, args: argparse.Namespace) -> tuple[list[dict], dict[str, Any]]:
    limit = args.limit
    items: list[dict[str, Any]] = []
    last_page: int | None = None
    total: int | None = None
    start = args.page

    if args.all_pages:
        page_no = start
        for _ in range(args.max_pages):
            page = fetch(page_no)
            items.extend(page.items)
            last_page = page.last_page
            total = page.total if total is None else total
            if not page.items:
                break
            if limit is not None and len(items) >= limit:
                break
            if page.last_page is not None and page_no >= page.last_page:
                break
            page_no += 1
    else:
        page = fetch(start)
        items = list(page.items)
        last_page = page.last_page
        total = page.total

    if limit is not None:
        items = items[:limit]

    meta = {"page": start, "last_page": last_page, "total": total, "count": len(items)}
    return items, meta


def _price_of(item: dict[str, Any]) -> int | None:
    price = item.get("price")
    if isinstance(price, dict):
        price = price.get("amount")
    if isinstance(price, (int, float)):
        return int(price)
    return None


def _filter_local(
    items: list[dict[str, Any]],
    *,
    price_min: int | None,
    price_max: int | None,
    newer_than: float | None,
) -> list[dict[str, Any]]:
    cutoff = (time.time() - newer_than * 3600) * 1000 if newer_than else None
    out = []
    for item in items:
        if price_min is not None or price_max is not None:
            price = _price_of(item)
            if price is None:
                continue
            if price_min is not None and price < price_min:
                continue
            if price_max is not None and price > price_max:
                continue
        if cutoff is not None:
            timestamp = item.get("timestamp")
            if not isinstance(timestamp, (int, float)) or timestamp < cutoff:
                continue
        out.append(item)
    return out


def _print(items: list[dict], args: argparse.Namespace, meta: dict[str, Any], columns) -> None:
    if args.output == "json":
        print(render_json({**meta, "items": items}))
    else:
        print(render(items, args.output, columns))


def _print_options(items: Any, args: argparse.Namespace, columns=OPTION_COLUMNS) -> None:
    print(render(items, args.output, columns))


def _cmd_search(args: argparse.Namespace) -> None:
    if args.category and args.sub_category:
        raise ValueError("Cannot combine --category and --sub-category")

    client = BlocketClient()
    locations = resolve_many(Location, args.location)
    sort_order = resolve(SortOrder, args.sort)
    category = resolve(Category, args.category) if args.category else None
    sub_category = resolve(SubCategory, args.sub_category) if args.sub_category else None
    compact = not args.raw

    def fetch(page: int) -> Page:
        return client.search(
            args.query,
            page=page,
            sort_order=sort_order,
            locations=locations,
            category=category,
            sub_category=sub_category,
            compact=compact,
        )

    items, meta = _gather(fetch, args)
    items = _filter_local(
        items, price_min=args.price_min, price_max=args.price_max, newer_than=args.newer_than
    )
    meta["count"] = len(items)
    _print(items, args, meta, LISTING_COLUMNS)


def _cmd_cars(args: argparse.Namespace) -> None:
    client = BlocketClient()
    fetch_ = lambda page: client.search_cars(  # noqa: E731
        args.query,
        page=page,
        sort_order=resolve(CarSortOrder, args.sort),
        locations=resolve_many(Location, args.location),
        models=resolve_many(CarModel, args.model),
        price_from=args.price_min,
        price_to=args.price_max,
        year_from=args.year_from,
        year_to=args.year_to,
        mileage_from=args.mileage_from,
        mileage_to=args.mileage_to,
        horsepower_from=args.horsepower_from,
        horsepower_to=args.horsepower_to,
        colors=resolve_many(CarColor, args.color),
        transmissions=resolve_many(CarTransmission, args.transmission),
        wheel_drive=resolve_many(CarWheelDrive, args.wheel_drive),
        compact=not args.raw,
    )
    items, meta = _gather(fetch_, args)
    _print(items, args, meta, CAR_COLUMNS)


def _cmd_boats(args: argparse.Namespace) -> None:
    client = BlocketClient()
    fetch_: Fetch = lambda page: client.search_boats(  # noqa: E731
        args.query,
        page=page,
        sort_order=resolve(BoatSortOrder, args.sort),
        locations=resolve_many(Location, args.location),
        types=resolve_many(BoatType, args.type),
        price_from=args.price_min,
        price_to=args.price_max,
        length_from=args.length_from,
        length_to=args.length_to,
        compact=not args.raw,
    )
    items, meta = _gather(fetch_, args)
    _print(items, args, meta, BOAT_COLUMNS)


def _cmd_mc(args: argparse.Namespace) -> None:
    client = BlocketClient()
    fetch_: Fetch = lambda page: client.search_mc(  # noqa: E731
        args.query,
        page=page,
        sort_order=resolve(McSortOrder, args.sort),
        locations=resolve_many(Location, args.location),
        models=resolve_many(McModel, args.model),
        types=resolve_many(McType, args.type),
        price_from=args.price_min,
        price_to=args.price_max,
        engine_volume_from=args.engine_volume_from,
        engine_volume_to=args.engine_volume_to,
        compact=not args.raw,
    )
    items, meta = _gather(fetch_, args)
    _print(items, args, meta, MC_COLUMNS)


def _cmd_ad(args: argparse.Namespace) -> None:
    client = BlocketClient()
    details = client.get_ad(args.ad_id, ad_type=args.type, raw=args.raw)
    if args.output == "jsonl":
        print(render([details], "jsonl"))
    elif args.output == "table":
        print(render_pairs(details))
    else:
        print(render_json(details))


def _cmd_categories(args: argparse.Namespace) -> None:
    _print_options(enum_items(Category), args)


def _cmd_subcategories(args: argparse.Namespace) -> None:
    items: list[dict[str, Any]] = []
    if args.category:
        category = resolve(Category, args.category)
        items = [
            {"category": category.name, "name": sub.name, "id": str(sub.value)}
            for sub in subcategories_of(category)
        ]
    else:
        for category in Category:
            items.extend(
                {"category": category.name, "name": sub.name, "id": str(sub.value)}
                for sub in subcategories_of(category)
            )
        items.sort(key=lambda item: (item["category"], item["name"]))
    _print_options(items, args, ("category", "name", "id"))


def _cmd_locations(args: argparse.Namespace) -> None:
    _print_options(enum_items(Location), args)


def _cmd_car_options(args: argparse.Namespace) -> None:
    _print_options(
        {
            "models": enum_items(CarModel),
            "colors": enum_items(CarColor),
            "transmissions": enum_items(CarTransmission),
            "wheel_drives": enum_items(CarWheelDrive),
            "sort_orders": enum_items(CarSortOrder),
        },
        args,
    )


def _cmd_boat_options(args: argparse.Namespace) -> None:
    _print_options(
        {"types": enum_items(BoatType), "sort_orders": enum_items(BoatSortOrder)}, args
    )


def _cmd_mc_options(args: argparse.Namespace) -> None:
    _print_options(
        {
            "models": enum_items(McModel),
            "types": enum_items(McType),
            "sort_orders": enum_items(McSortOrder),
        },
        args,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        args.handler(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except HTTPStatusError as exc:
        print(
            f"error: Blocket returned HTTP {exc.response.status_code} for {exc.request.url}",
            file=sys.stderr,
        )
        return 1
    except RequestError as exc:
        print(f"error: network problem talking to Blocket: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
