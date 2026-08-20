from pathlib import Path

import pytest
from PIL import Image

from texcanvas.assets import inspect_image
from texcanvas.errors import AssetError


def test_png_image_is_inspected(tmp_path: Path):
    path = tmp_path / "image.png"
    Image.new("RGB", (20, 10)).save(path)
    info = inspect_image(path, "slide.image")
    assert (info.width, info.height) == (20, 10)


def test_svg_is_rejected_explicitly(tmp_path: Path):
    path = tmp_path / "image.svg"
    path.write_text("<svg/>", encoding="utf-8")
    with pytest.raises(AssetError, match="use PNG or JPEG"):
        inspect_image(path, "slide.image")

