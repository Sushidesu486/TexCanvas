from __future__ import annotations

from pathlib import Path

import pytest

from texcanvas.errors import ValidationError
from texcanvas.loader import deck_from_mapping


def minimal(slides=None):
    return {
        "metadata": {"title": "Demo"},
        "sections": [{"title": "Background", "slides": slides or [{"kind": "content"}]}],
    }


def test_code_requires_source():
    with pytest.raises(ValidationError, match=r"code\.source: is required"):
        deck_from_mapping(minimal([{"kind": "code", "code": {"lang": "python"}}]))


def test_code_with_source_loads():
    deck = deck_from_mapping(minimal([{
        "kind": "code",
        "code": {"source": "print('hi')\n", "lang": "python", "caption": "L1"},
    }]))
    code = deck.sections[0].slides[0].code
    assert code is not None
    assert "print" in code.source
    assert code.lang == "python"
    assert code.caption == "L1"


def test_table_requires_header_or_rows():
    with pytest.raises(ValidationError, match=r"table: header or rows are required"):
        deck_from_mapping(minimal([{"kind": "table", "table": {}}]))


def test_table_with_only_header_loads():
    deck = deck_from_mapping(minimal([{"kind": "table", "table": {"header": ["A"]}}]))
    assert deck.sections[0].slides[0].table.header == ("A",)
    assert deck.sections[0].slides[0].table.rows == ()


def test_table_with_only_rows_loads():
    deck = deck_from_mapping(minimal([{"kind": "table", "table": {"rows": [["x"]]}}]))
    assert deck.sections[0].slides[0].table.rows == (("x",),)


def test_table_with_header_and_rows_loads():
    deck = deck_from_mapping(minimal([{
        "kind": "table",
        "table": {
            "header": ["A", "B"],
            "rows": [["1", "2"], ["3", "4"]],
            "caption": "T1",
        },
    }]))
    table = deck.sections[0].slides[0].table
    assert table is not None
    assert table.header == ("A", "B")
    assert table.rows[1] == ("3", "4")


def test_table_jagged_rows_keep_tupling():
    deck = deck_from_mapping(minimal([{
        "kind": "table",
        "table": {"header": ["A", "B", "C"], "rows": [["x"]]},
    }]))
    assert deck.sections[0].slides[0].table.rows == (("x",),)


def test_equation_required():
    with pytest.raises(ValidationError, match=r"equation: is required"):
        deck_from_mapping(minimal([{"kind": "equation"}]))


def test_equation_loads():
    deck = deck_from_mapping(minimal([{
        "kind": "equation", "equation": "L = -\\frac{1}{N}",
    }]))
    assert deck.sections[0].slides[0].equation.startswith("L = ")


def test_block_requires_body_or_bullets():
    with pytest.raises(ValidationError, match=r"block: body or bullets are required"):
        deck_from_mapping(minimal([{"kind": "block", "block": {"title": "T"}}]))


def test_block_invalid_style_rejected():
    with pytest.raises(ValidationError, match=r"block\.style: unsupported value"):
        deck_from_mapping(minimal([{
            "kind": "block", "block": {"style": "weird", "body": "x"},
        }]))


def test_block_styles_load():
    for style, expected in [("default", "default"), ("alert", "alert"), ("example", "example")]:
        deck = deck_from_mapping(minimal([{
            "kind": "block", "block": {"style": style, "body": "x"},
        }]))
        assert deck.sections[0].slides[0].block.style == expected
