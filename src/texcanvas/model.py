from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SlideKind(StrEnum):
    TITLE = "title"
    SECTION_DIVIDER = "section_divider"
    CONTENT = "content"
    TWO_COLUMNS = "two_columns"
    IMAGE = "image"
    CODE = "code"
    TABLE = "table"
    EQUATION = "equation"
    BLOCK = "block"
    CONCLUSION = "conclusion"
    REFERENCES = "references"


@dataclass(frozen=True)
class CodeSpec:
    source: str
    lang: str = ""
    caption: str = ""


@dataclass(frozen=True)
class TableSpec:
    header: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    caption: str = ""


class BlockStyle(StrEnum):
    DEFAULT = "default"
    ALERT = "alert"
    EXAMPLE = "example"


@dataclass(frozen=True)
class BlockSpec:
    style: str = BlockStyle.DEFAULT
    title: str = ""
    body: str = ""
    bullets: tuple[str, ...] = ()


@dataclass(frozen=True)
class Metadata:
    title: str
    subtitle: str = ""
    author: str = ""
    institute: str = ""
    date: str = ""
    short_title: str = ""


@dataclass(frozen=True)
class Column:
    heading: str = ""
    body: str = ""
    bullets: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImageSpec:
    path: str
    fit: str = "contain"


@dataclass(frozen=True)
class Slide:
    kind: SlideKind
    title: str = ""
    subtitle: str = ""
    body: str = ""
    bullets: tuple[str, ...] = ()
    columns: tuple[Column, Column] | None = None
    image: ImageSpec | None = None
    code: CodeSpec | None = None
    table: TableSpec | None = None
    block: BlockSpec | None = None
    equation: str = ""
    caption: str = ""
    takeaway: str = ""
    items: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    short_title: str
    slides: tuple[Slide, ...]


@dataclass(frozen=True)
class Deck:
    metadata: Metadata
    sections: tuple[Section, ...]
    aspect: str = "16:9"

    @property
    def slide_count(self) -> int:
        return sum(len(section.slides) for section in self.sections)

