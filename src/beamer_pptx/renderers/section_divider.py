from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR

from ..model import Slide
from .common import RenderContext, add_box, add_text


def render_section_divider(ctx: RenderContext, slide: Slide) -> None:
    number = f"{ctx.section_index + 1:02d}"
    add_text(
        ctx,
        "DSH_SECTION_NUMBER",
        number,
        0.78,
        1.55,
        2.2,
        1.2,
        size=58,
        text_color=ctx.theme.accent,
        bold=True,
        margin=0,
    )
    add_box(ctx, "DSH_SECTION_BAR", 0.82, 2.75, 1.0, 0.08, fill=ctx.theme.primary)
    add_text(
        ctx,
        "DSH_SECTION_TITLE",
        slide.title or ctx.section.title,
        2.55,
        1.68,
        ctx.slide_width - 3.35,
        1.35,
        size=34,
        text_color=ctx.theme.primary,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
        margin=0,
    )
    subtitle = slide.subtitle
    if subtitle:
        add_text(
            ctx,
            "DSH_SECTION_SUBTITLE",
            subtitle,
            2.58,
            3.16,
            ctx.slide_width - 3.4,
            0.75,
            size=18,
            text_color=ctx.theme.muted,
            margin=0,
        )

