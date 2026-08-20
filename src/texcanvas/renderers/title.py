from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from ..model import Slide
from .common import RenderContext, add_box, add_text


def render_title(ctx: RenderContext, slide: Slide) -> None:
    """Deck cover slide (beamer ``\\titlepage``), drawn from deck metadata.

    A full-bleed primary band carries the title and subtitle; the author,
    institute, and date sit beneath it. Navigation, the slide title rule, and
    the footer are suppressed for cover slides (see ``render_chrome``), so the
    band is the only chrome on the page.
    """
    meta = ctx.deck.metadata
    band_top = 2.5
    band_height = 2.3

    add_box(
        ctx,
        "DSH_TITLE_BAND",
        -0.1,
        band_top,
        ctx.slide_width + 0.2,
        band_height,
        fill=ctx.theme.primary,
    )
    # Accent bar capping the band, centered (a metropolis-style highlight).
    add_box(
        ctx,
        "DSH_TITLE_ACCENT",
        (ctx.slide_width - 2.0) / 2,
        band_top - 0.06,
        2.0,
        0.08,
        fill=ctx.theme.accent,
    )

    title = slide.title or meta.title
    if title:
        add_text(
            ctx,
            "DSH_TITLE_COVER",
            title,
            1.2,
            band_top + 0.25,
            ctx.slide_width - 2.4,
            1.25,
            size=44,
            text_color=ctx.theme.white,
            bold=True,
            align=PP_ALIGN.CENTER,
            valign=MSO_ANCHOR.MIDDLE,
            margin=0,
        )

    subtitle = slide.subtitle or meta.subtitle
    if subtitle:
        add_text(
            ctx,
            "DSH_TITLE_SUBTITLE",
            subtitle,
            1.2,
            band_top + 1.55,
            ctx.slide_width - 2.4,
            0.6,
            size=22,
            text_color=ctx.theme.pale,
            align=PP_ALIGN.CENTER,
            margin=0,
        )

    byline_parts = [part for part in (meta.author, meta.institute, meta.date) if part]
    if byline_parts:
        add_text(
            ctx,
            "DSH_TITLE_BYLINE",
            "  ·  ".join(byline_parts),
            1.2,
            band_top + band_height + 0.35,
            ctx.slide_width - 2.4,
            0.45,
            size=16,
            text_color=ctx.theme.muted,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
