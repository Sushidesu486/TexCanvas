from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .errors import AssetError
from .model import Deck, SlideKind


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_FORMATS = {"PNG", "JPEG"}


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    width: int
    height: int


def resolve_asset(path: str, asset_root: Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else asset_root / candidate


def inspect_image(path: Path, location: str) -> ImageInfo:
    if path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
        raise AssetError(f"{location}: unsupported image format {path.suffix or '<none>'}; use PNG or JPEG")
    if not path.is_file():
        raise AssetError(f"{location}: image not found: {path}")
    try:
        with Image.open(path) as image:
            image.load()
            if image.format not in SUPPORTED_FORMATS:
                raise AssetError(f"{location}: unsupported image format {image.format}; use PNG or JPEG")
            return ImageInfo(path=path, width=image.width, height=image.height)
    except (OSError, UnidentifiedImageError) as exc:
        raise AssetError(f"{location}: cannot open image {path}: {exc}") from exc


def validate_assets(deck: Deck, asset_root: Path, strict: bool) -> list[str]:
    warnings: list[str] = []
    for section_index, section in enumerate(deck.sections):
        for slide_index, slide in enumerate(section.slides):
            if slide.kind is not SlideKind.IMAGE or slide.image is None:
                if slide.inline_image is not None:
                    location = f"sections[{section_index}].slides[{slide_index}].inline_image.path"
                    try:
                        inspect_image(resolve_asset(slide.inline_image.path, asset_root), location)
                    except AssetError as exc:
                        if strict:
                            raise
                        warnings.append(str(exc))
                continue
            location = f"sections[{section_index}].slides[{slide_index}].image.path"
            try:
                inspect_image(resolve_asset(slide.image.path, asset_root), location)
            except AssetError as exc:
                if strict:
                    raise
                warnings.append(str(exc))
    return warnings

