"""Name and value resolution for the blocket_api enumerations."""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from blocket_api import (
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

E = TypeVar("E", bound=Enum)

__all__ = [
    "BoatSortOrder",
    "BoatType",
    "CarColor",
    "CarModel",
    "CarSortOrder",
    "CarTransmission",
    "CarWheelDrive",
    "Category",
    "Location",
    "McModel",
    "McSortOrder",
    "McType",
    "SortOrder",
    "SubCategory",
    "enum_items",
    "resolve",
    "resolve_many",
    "subcategories_of",
]


def _slug(token: str) -> str:
    return token.strip().upper().replace(" ", "_").replace("-", "_")


def resolve(enum_cls: type[E], token: str) -> E:
    """Resolve a user token to an enum member.

    Accepts the member name case-insensitively (spaces and dashes are treated as
    underscores) or the raw Blocket value, e.g. ``"elektronik_och_vitvaror"``,
    ``"Elektronik och vitvaror"`` or ``"0.93"``.
    """
    if not isinstance(token, str) or not token.strip():
        raise ValueError(f"Empty value for {enum_cls.__name__}")

    key = _slug(token)
    if key in enum_cls.__members__:
        return enum_cls[key]

    raw = token.strip()
    for member in enum_cls:
        if str(member.value) == raw:
            return member

    names = ", ".join(_names(enum_cls))
    raise ValueError(
        f"Unknown {enum_cls.__name__}: {token!r}. Valid names or ids: {names}"
    )


def resolve_many(enum_cls: type[E], tokens: list[str] | None) -> list[E]:
    """Resolve a list of tokens, flattening comma-separated values."""
    if not tokens:
        return []
    out: list[E] = []
    for token in tokens:
        for part in str(token).split(","):
            part = part.strip()
            if part:
                out.append(resolve(enum_cls, part))
    return out


def _names(enum_cls: type[Enum]) -> list[str]:
    return [m.name for m in enum_cls]


def enum_items(enum_cls: type[E]) -> list[dict[str, object]]:
    """Return an enum as a sorted list of ``{"name", "id"}`` dicts."""
    return sorted(
        ({"name": m.name, "id": str(m.value)} for m in enum_cls),
        key=lambda item: str(item["name"]),
    )


def subcategories_of(category: Category) -> list[SubCategory]:
    """Return the subcategories that belong to a category.

    Blocket encodes the hierarchy in the ids: a category ``0.93`` has
    subcategories ``1.93.<n>``.
    """
    prefix = f"0.{str(category.value).split('.')[-1]}"
    return [
        sub
        for sub in SubCategory
        if f"0.{str(sub.value).split('.')[1]}" == prefix
    ]
