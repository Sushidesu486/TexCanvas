from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from .errors import InputError, ValidationError
from .model import (
    BlockSpec,
    BlockStyle,
    CodeSpec,
    Column,
    Deck,
    ImageSpec,
    Metadata,
    Section,
    Slide,
    SlideKind,
    TableSpec,
)
from .validate import validate_deck


def _mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{location}: expected a mapping")
    return value


def _list(value: Any, location: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValidationError(f"{location}: expected a list")
    return value


def _text(value: Any, location: str, *, required: bool = False) -> str:
    if value is None:
        value = ""
    if isinstance(value, (Mapping, Sequence)) and not isinstance(value, str):
        raise ValidationError(f"{location}: expected text")
    result = str(value).strip()
    if required and not result:
        raise ValidationError(f"{location}: is required")
    return result


def _text_tuple(value: Any, location: str) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(_text(item, f"{location}[{index}]", required=True) for index, item in enumerate(_list(value, location)))


def _slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or fallback


def _column(value: Any, location: str) -> Column:
    raw = _mapping(value, location)
    return Column(
        heading=_text(raw.get("heading"), f"{location}.heading"),
        body=_text(raw.get("body"), f"{location}.body"),
        bullets=_text_tuple(raw.get("bullets"), f"{location}.bullets"),
    )


def _slide(value: Any, location: str) -> Slide:
    raw = _mapping(value, location)
    kind_text = _text(raw.get("kind"), f"{location}.kind", required=True)
    try:
        kind = SlideKind(kind_text)
    except ValueError as exc:
        supported = ", ".join(item.value for item in SlideKind)
        raise ValidationError(f"{location}.kind: unsupported value {kind_text!r}; expected one of {supported}") from exc

    columns = None
    if kind is SlideKind.TWO_COLUMNS and ("left" in raw or "right" in raw):
        if "left" not in raw:
            raise ValidationError(f"{location}.left: is required")
        if "right" not in raw:
            raise ValidationError(f"{location}.right: is required")
        columns = (_column(raw["left"], f"{location}.left"), _column(raw["right"], f"{location}.right"))

    image = None
    if "image" in raw and raw["image"] is not None:
        image_raw = _mapping(raw["image"], f"{location}.image")
        image = ImageSpec(
            path=_text(image_raw.get("path"), f"{location}.image.path"),
            fit=_text(image_raw.get("fit", "contain"), f"{location}.image.fit", required=True),
        )

    code = None
    if "code" in raw and raw["code"] is not None:
        code_raw = _mapping(raw["code"], f"{location}.code")
        code = CodeSpec(
            source=_text(code_raw.get("source"), f"{location}.code.source", required=True),
            lang=_text(code_raw.get("lang"), f"{location}.code.lang"),
            caption=_text(code_raw.get("caption"), f"{location}.code.caption"),
        )

    table = None
    if "table" in raw and raw["table"] is not None:
        table_raw = _mapping(raw["table"], f"{location}.table")
        header = _text_tuple(table_raw.get("header"), f"{location}.table.header")
        rows_value = table_raw.get("rows")
        if rows_value is None:
            rows: tuple[tuple[str, ...], ...] = ()
        else:
            rows_raw = _list(rows_value, f"{location}.table.rows")
            rows = tuple(
                _text_tuple(row, f"{location}.table.rows[{row_index}]")
                for row_index, row in enumerate(rows_raw)
            )
        table = TableSpec(
            header=header,
            rows=rows,
            caption=_text(table_raw.get("caption"), f"{location}.table.caption"),
        )

    block = None
    if "block" in raw and raw["block"] is not None:
        block_raw = _mapping(raw["block"], f"{location}.block")
        block = BlockSpec(
            style=_text(block_raw.get("style", BlockStyle.DEFAULT), f"{location}.block.style"),
            title=_text(block_raw.get("title"), f"{location}.block.title"),
            body=_text(block_raw.get("body"), f"{location}.block.body"),
            bullets=_text_tuple(block_raw.get("bullets"), f"{location}.block.bullets"),
        )

    equation = ""
    if "equation" in raw and raw["equation"] is not None:
        equation = _text(raw["equation"], f"{location}.equation")

    return Slide(
        kind=kind,
        title=_text(raw.get("title"), f"{location}.title"),
        subtitle=_text(raw.get("subtitle"), f"{location}.subtitle"),
        body=_text(raw.get("body"), f"{location}.body"),
        bullets=_text_tuple(raw.get("bullets"), f"{location}.bullets"),
        columns=columns,
        image=image,
        code=code,
        table=table,
        block=block,
        caption=_text(raw.get("caption"), f"{location}.caption"),
        takeaway=_text(raw.get("takeaway"), f"{location}.takeaway"),
        items=_text_tuple(raw.get("items"), f"{location}.items"),
        notes=_text(raw.get("notes"), f"{location}.notes"),
        equation=equation,
    )


def deck_from_mapping(value: Any) -> Deck:
    root = _mapping(value, "root")
    metadata_raw = _mapping(root.get("metadata"), "metadata")
    metadata = Metadata(
        title=_text(metadata_raw.get("title"), "metadata.title", required=True),
        subtitle=_text(metadata_raw.get("subtitle"), "metadata.subtitle"),
        author=_text(metadata_raw.get("author"), "metadata.author"),
        institute=_text(metadata_raw.get("institute"), "metadata.institute"),
        date=_text(metadata_raw.get("date"), "metadata.date"),
        short_title=_text(metadata_raw.get("short_title"), "metadata.short_title"),
    )

    sections_raw = _list(root.get("sections"), "sections")
    sections: list[Section] = []
    for section_index, section_value in enumerate(sections_raw):
        location = f"sections[{section_index}]"
        raw = _mapping(section_value, location)
        title = _text(raw.get("title"), f"{location}.title", required=True)
        short_title = _text(raw.get("short_title"), f"{location}.short_title") or title
        section_id = _text(raw.get("id"), f"{location}.id") or _slugify(short_title, f"section-{section_index + 1}")
        slides = tuple(
            _slide(slide_value, f"{location}.slides[{slide_index}]")
            for slide_index, slide_value in enumerate(_list(raw.get("slides"), f"{location}.slides"))
        )
        sections.append(Section(id=section_id, title=title, short_title=short_title, slides=slides))

    deck = Deck(
        metadata=metadata,
        sections=tuple(sections),
        aspect=_text(root.get("aspect", "16:9"), "aspect", required=True),
    )
    validate_deck(deck)
    return deck


def load_deck(path: str | Path) -> Deck:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{source}: cannot read input: {exc}") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise InputError(f"{source}: invalid YAML: {exc}") from exc
    return deck_from_mapping(raw)

