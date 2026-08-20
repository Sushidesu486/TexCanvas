from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR

from ..model import BlockStyle, Slide
from .common import RenderContext, add_box, add_rich_text, add_text


def _palette(ctx: RenderContext, style: str) -> tuple[str, str]:
    if style == BlockStyle.ALERT.value:
        return ctx.theme.block_alert_title, ctx.theme.block_alert_body
    if style == BlockStyle.EXAMPLE.value:
        return ctx.theme.block_example_title, ctx.theme.block_example_body
    return ctx.theme.block_default_title, ctx.theme.block_default_body


def render_block(ctx: RenderContext, slide: Slide) -> None:
    assert slide.block is not None
    block = slide.block
    title_color, body_fill = _palette(ctx, block.style)

    panel_left = 0.9
    panel_width = ctx.slide_width - 1.8
    panel_top = 1.6
    available_height = ctx.slide_height - 1.48 - 0.6 - panel_top
    has_bullets = bool(block.bullets)
    estimated_height = 0.5 + (0.3 * len(block.bullets) if has_bullets else 0) + (0.5 if block.body else 0)
    panel_height = min(available_height, max(1.4, estimated_height + 0.5))

    add_box(
        ctx,
        "DSH_BLOCK_PANEL",
        panel_left,
        panel_top,
        panel_width,
        panel_height,
        fill=body_fill,
        line=title_color,
        radius=False,
    )

    # Title bar on the left edge (beamer-style colored block title).
    title_text = block.title or {
        BlockStyle.ALERT.value: "Alert",
        BlockStyle.EXAMPLE.value: "Example",
        BlockStyle.DEFAULT.value: "Block",
    }.get(block.style, "Block")
    title_width = 1.6
    add_box(
        ctx,
        "DSH_BLOCK_TITLE_PANEL",
        panel_left,
        panel_top,
        title_width,
        0.5,
        fill=title_color,
        radius=False,
    )
    add_text(
        ctx,
        "DSH_BLOCK_TITLE",
        title_text,
        panel_left + 0.12,
        panel_top,
        title_width - 0.18,
        0.5,
        size=16,
        text_color=ctx.theme.white,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
        margin=0,
    )

    body_top = panel_top + 0.7
    body_height = panel_height - 0.85
    paragraphs: list[tuple[str, float, bool, str, float]] = []
    if block.body:
        paragraphs.append((block.body, 16, False, ctx.theme.text, 12))
    paragraphs.extend((f"•  {bullet}", 15, False, ctx.theme.text, 8) for bullet in block.bullets)
    if paragraphs:
        add_rich_text(ctx, "DSH_BLOCK_BODY", paragraphs, panel_left + 0.22, body_top, panel_width - 0.44, body_height)
