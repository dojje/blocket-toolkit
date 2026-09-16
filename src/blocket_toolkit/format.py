"""Output rendering: JSON, JSON-lines and plain text tables."""

from __future__ import annotations

import json
from typing import Any

LISTING_COLUMNS = ("id", "price", "heading", "location", "url")
CAR_COLUMNS = ("id", "price", "heading", "year", "mileage", "location", "url")
BOAT_COLUMNS = ("id", "price", "heading", "year", "length", "location", "url")
MC_COLUMNS = ("id", "price", "heading", "year", "volume", "location", "url")
OPTION_COLUMNS = ("name", "id")

MAX_CELL = 60


def render_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def render_jsonl(items: list[Any]) -> str:
    return "\n".join(
        json.dumps(item, ensure_ascii=False, default=str) for item in items
    )


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    text = str(value).replace("\n", " ").strip()
    if len(text) > MAX_CELL:
        text = text[: MAX_CELL - 1] + "…"
    return text


def render_table(rows: list[dict[str, Any]], columns: tuple[str, ...]) -> str:
    if not rows:
        return "(no results)"

    header = [column.upper() for column in columns]
    cells = [[_cell(row.get(column)) for column in columns] for row in rows]

    widths = [
        max(len(header[i]), *(len(row[i]) for row in cells)) for i in range(len(columns))
    ]

    lines = ["  ".join(header[i].ljust(widths[i]) for i in range(len(columns)))]
    lines.append("  ".join("-" * widths[i] for i in range(len(columns))))
    for row in cells:
        lines.append("  ".join(row[i].ljust(widths[i]) for i in range(len(columns))))
    return "\n".join(lines)


def render_pairs(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, (dict, list, tuple)):
            rendered = render_json(value)
        elif value is None or value == "":
            rendered = "-"
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    return "\n".join(lines)


def render(items: Any, output: str, columns: tuple[str, ...] = LISTING_COLUMNS) -> str:
    """Render ``items`` in the requested format.

    ``items`` may be a ``Page`` (or its ``as_dict``), a list of records, or a
    plain dict.
    """
    if output == "jsonl":
        rows = items["items"] if isinstance(items, dict) and "items" in items else items
        if isinstance(rows, dict):
            rows = [rows]
        return render_jsonl(rows)
    if output == "table":
        if isinstance(items, dict) and "items" in items:
            return render_table(items["items"], columns)
        if isinstance(items, list):
            return render_table(items, columns)
        if isinstance(items, dict):
            sections = [
                f"# {key}\n" + render_table(value, tuple(value[0].keys()))
                for key, value in items.items()
                if isinstance(value, list) and value and isinstance(value[0], dict)
            ]
            if sections:
                return "\n\n".join(sections)
            if all(not isinstance(v, (dict, list)) for v in items.values()):
                return render_pairs(items)
            return render_table([items], columns)
    return render_json(items)
