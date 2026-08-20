from __future__ import annotations

from ..geometry import Box
from ..model import Slide
from .common import RenderContext, add_rich_text
from .inline_image import render_inline_image


def render_content(ctx: RenderContext, slide: Slide) -> None:
    content_box = Box(0.82, 1.5, ctx.slide_width - 1.64, ctx.slide_height - 2.2)
    if slide.inline_image is not None:
        text_box = render_inline_image(ctx, slide, content_box)
    else:
        text_box = content_box

    paragraphs: list[tuple[str, float, bool, str, float]] = []
    if slide.body:
        paragraphs.append((slide.body, 18, False, ctx.theme.text, 14))
    paragraphs.extend((f"•  {bullet}", 17, False, ctx.theme.text, 9) for bullet in slide.bullets)
    if not paragraphs:
        paragraphs.append(("", 18, False, ctx.theme.text, 0))
    add_rich_text(ctx, "DSH_BODY", paragraphs, text_box.x, text_box.y, text_box.width, text_box.height)
