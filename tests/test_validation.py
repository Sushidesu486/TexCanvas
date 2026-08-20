import pytest

from texcanvas.errors import ValidationError
from texcanvas.loader import deck_from_mapping


def minimal(slides=None):
    return {
        "metadata": {"title": "Demo"},
        "sections": [{"title": "Background", "slides": slides or [{"kind": "content"}]}],
    }


def test_normal_yaml_mapping_and_default_section_id():
    deck = deck_from_mapping(minimal())
    assert deck.sections[0].id == "background"
    assert deck.aspect == "16:9"


def test_non_latin_default_section_id_is_stable():
    data = minimal()
    data["sections"][0]["title"] = "研究背景"
    assert deck_from_mapping(data).sections[0].id == "section-1"


def test_duplicate_section_id_reports_location():
    data = minimal()
    data["sections"].append({"id": "background", "title": "Again", "slides": [{"kind": "content"}]})
    data["sections"][0]["id"] = "background"
    with pytest.raises(ValidationError, match=r"sections\[1\]\.id: duplicate"):
        deck_from_mapping(data)


def test_unsupported_slide_kind():
    with pytest.raises(ValidationError, match="unsupported value"):
        deck_from_mapping(minimal([{"kind": "magic"}]))


def test_two_columns_requires_both_columns():
    with pytest.raises(ValidationError, match="two_columns requires"):
        deck_from_mapping(minimal([{"kind": "two_columns"}]))


def test_two_columns_cannot_be_empty():
    with pytest.raises(ValidationError, match="must not be empty"):
        deck_from_mapping(minimal([{"kind": "two_columns", "left": {}, "right": {}}]))


def test_image_requires_path():
    with pytest.raises(ValidationError, match="image.path is required"):
        deck_from_mapping(minimal([{"kind": "image", "image": {}}]))


def test_conclusion_requires_content():
    with pytest.raises(ValidationError, match="conclusion requires"):
        deck_from_mapping(minimal([{"kind": "conclusion"}]))


def test_references_require_items():
    with pytest.raises(ValidationError, match="at least one reference"):
        deck_from_mapping(minimal([{"kind": "references"}]))

