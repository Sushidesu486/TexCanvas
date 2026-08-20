import pytest

from beamer_pptx.geometry import Box, contain, cover, navigation_widths, page_label


def test_contain_centers_wide_image():
    result = contain(1600, 900, Box(0, 0, 10, 10))
    assert result.width == pytest.approx(10)
    assert result.height == pytest.approx(5.625)
    assert result.y == pytest.approx(2.1875)
    assert result.crop_left == 0


def test_cover_crops_wide_image_equally():
    result = cover(1600, 900, Box(1, 2, 10, 10))
    assert result.width == 10
    assert result.crop_left == pytest.approx(0.21875)
    assert result.crop_right == pytest.approx(0.21875)


def test_navigation_widths_fill_available_space():
    widths = navigation_widths(13.333, 4)
    assert sum(widths) + 0.04 * 3 + 0.35 * 2 == pytest.approx(13.333)


def test_page_label_zero_pads():
    assert page_label(3, 24) == "03 / 24"

