from __future__ import annotations

from ..model import Slide
from .common import RenderContext, add_rich_text


def render_references(ctx: RenderContext, slide: Slide) -> None:
    size = 14 if len(slide.items) <= 8 else 12 if len(slide.items) <= 12 else 10
    paragraphs = [(f"[{index}]  {item}", size, False, ctx.theme.text, 7) for index, item in enumerate(slide.items, 1)]
    add_rich_text(ctx, "DSH_REFERENCES", paragraphs, 0.78, 1.48, ctx.slide_width - 1.56, ctx.slide_height - 2.18, margin=0.05)

