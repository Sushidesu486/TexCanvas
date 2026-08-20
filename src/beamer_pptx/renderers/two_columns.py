from __future__ import annotations

from ..model import Column, Slide
from .common import RenderContext, add_box, add_rich_text


def _render_column(ctx: RenderContext, column: Column, side: str, x: float, width: float) -> None:
    add_box(ctx, f"DSH_{side}_PANEL", x, 1.55, width, ctx.slide_height - 2.32, fill=ctx.theme.white, line=ctx.theme.pale, radius=True)
    paragraphs: list[tuple[str, float, bool, str, float]] = []
    if column.heading:
        paragraphs.append((column.heading, 19, True, ctx.theme.primary, 13))
    if column.body:
        paragraphs.append((column.body, 16, False, ctx.theme.text, 11))
    paragraphs.extend((f"•  {bullet}", 16, False, ctx.theme.text, 8) for bullet in column.bullets)
    add_rich_text(ctx, f"DSH_{side}_BODY", paragraphs, x + 0.2, 1.75, width - 0.4, ctx.slide_height - 2.72)


def render_two_columns(ctx: RenderContext, slide: Slide) -> None:
    assert slide.columns is not None
    gutter = 0.42
    total_width = ctx.slide_width - 1.64
    column_width = (total_width - gutter) / 2
    left_x = 0.82
    right_x = left_x + column_width + gutter
    _render_column(ctx, slide.columns[0], "LEFT", left_x, column_width)
    _render_column(ctx, slide.columns[1], "RIGHT", right_x, column_width)

