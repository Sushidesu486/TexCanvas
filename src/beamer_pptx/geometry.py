from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    def within(self, outer: "Box") -> bool:
        return (
            self.x >= outer.x
            and self.y >= outer.y
            and self.x + self.width <= outer.x + outer.width
            and self.y + self.height <= outer.y + outer.height
        )


@dataclass(frozen=True)
class ImagePlacement:
    x: float
    y: float
    width: float
    height: float
    crop_left: float = 0.0
    crop_right: float = 0.0
    crop_top: float = 0.0
    crop_bottom: float = 0.0


def contain(image_width: int, image_height: int, box: Box) -> ImagePlacement:
    if image_width <= 0 or image_height <= 0 or box.width <= 0 or box.height <= 0:
        raise ValueError("image and box dimensions must be positive")
    scale = min(box.width / image_width, box.height / image_height)
    width = image_width * scale
    height = image_height * scale
    return ImagePlacement(
        x=box.x + (box.width - width) / 2,
        y=box.y + (box.height - height) / 2,
        width=width,
        height=height,
    )


def cover(image_width: int, image_height: int, box: Box) -> ImagePlacement:
    if image_width <= 0 or image_height <= 0 or box.width <= 0 or box.height <= 0:
        raise ValueError("image and box dimensions must be positive")
    image_ratio = image_width / image_height
    box_ratio = box.width / box.height
    crop_left = crop_right = crop_top = crop_bottom = 0.0
    if image_ratio > box_ratio:
        visible_fraction = box_ratio / image_ratio
        crop_left = crop_right = (1.0 - visible_fraction) / 2.0
    elif image_ratio < box_ratio:
        visible_fraction = image_ratio / box_ratio
        crop_top = crop_bottom = (1.0 - visible_fraction) / 2.0
    return ImagePlacement(
        x=box.x,
        y=box.y,
        width=box.width,
        height=box.height,
        crop_left=crop_left,
        crop_right=crop_right,
        crop_top=crop_top,
        crop_bottom=crop_bottom,
    )


def navigation_widths(slide_width: float, section_count: int, margin: float = 0.35, gap: float = 0.04) -> tuple[float, ...]:
    if section_count <= 0:
        raise ValueError("section_count must be positive")
    usable = slide_width - 2 * margin - gap * (section_count - 1)
    if usable <= 0:
        raise ValueError("sections do not fit within slide width")
    width = usable / section_count
    return tuple(width for _ in range(section_count))


def page_label(current: int, total: int) -> str:
    if current <= 0 or total <= 0 or current > total:
        raise ValueError("page numbers must satisfy 1 <= current <= total")
    digits = max(2, len(str(total)))
    return f"{current:0{digits}d} / {total:0{digits}d}"

