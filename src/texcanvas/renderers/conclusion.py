from __future__ import annotations

from ..model import Slide
from .common import RenderContext, add_box, add_rich_text, add_text


def render_conclusion(ctx: RenderContext, slide: Slide) -> None:
    add_box(
        ctx,
        "DSH_TAKEAWAY_PANEL",
        0.85,
        1.58,
        ctx.slide_width - 1.7,
        1.25,
        fill="FFF3E8",
        line=ctx.theme.accent,
        radius=False,
    )
    add_text(
        ctx,
        "DSH_TAKEAWAY",
        slide.takeaway or "Key conclusions",
        1.15,
        1.84,
        ctx.slide_width - 2.3,
        0.7,
        size=23,
        text_color=ctx.theme.primary,
        bold=True,
        margin=0,
    )
    paragraphs = [(f"•  {bullet}", 17, False, ctx.theme.text, 10) for bullet in slide.bullets]
    if paragraphs:
        add_rich_text(ctx, "DSH_BODY", paragraphs, 1.02, 3.18, ctx.slide_width - 2.04, ctx.slide_height - 4.0)

