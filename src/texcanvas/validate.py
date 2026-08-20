from __future__ import annotations

from .errors import ValidationError
from .model import BlockStyle, Deck, SlideKind


def _column_has_content(column: object) -> bool:
    return bool(getattr(column, "heading", "") or getattr(column, "body", "") or getattr(column, "bullets", ()))


def validate_deck(deck: Deck) -> None:
    if deck.aspect != "16:9":
        raise ValidationError("aspect: only '16:9' is currently supported")
    if not deck.sections:
        raise ValidationError("sections: at least one section is required")

    seen: dict[str, int] = {}
    for section_index, section in enumerate(deck.sections):
        location = f"sections[{section_index}]"
        if section.id in seen:
            raise ValidationError(f"{location}.id: duplicate section id {section.id!r} (first used at sections[{seen[section.id]}])")
        seen[section.id] = section_index
        if not section.slides:
            raise ValidationError(f"{location}.slides: at least one slide is required")
        for slide_index, slide in enumerate(section.slides):
            slide_location = f"{location}.slides[{slide_index}]"
            if slide.kind is SlideKind.TITLE:
                # The cover slide draws from deck metadata, so it needs no slide-level fields.
                continue
            if slide.kind is SlideKind.TWO_COLUMNS:
                if slide.columns is None:
                    raise ValidationError(f"{slide_location}: two_columns requires left and right columns")
                if not all(_column_has_content(column) for column in slide.columns):
                    raise ValidationError(f"{slide_location}: left and right columns must not be empty")
            elif slide.kind is SlideKind.IMAGE:
                if slide.image is None or not slide.image.path:
                    raise ValidationError(f"{slide_location}: image.path is required")
                if slide.image.fit not in {"contain", "cover"}:
                    raise ValidationError(f"{slide_location}.image.fit: expected 'contain' or 'cover'")
            elif slide.kind is SlideKind.CODE:
                if slide.code is None or not slide.code.source.strip():
                    raise ValidationError(f"{slide_location}.code.source: is required")
            elif slide.kind is SlideKind.TABLE:
                if slide.table is None or (not slide.table.header and not slide.table.rows):
                    raise ValidationError(f"{slide_location}.table: header or rows are required")
            elif slide.kind is SlideKind.EQUATION:
                if not slide.equation.strip():
                    raise ValidationError(f"{slide_location}.equation: is required")
            elif slide.kind is SlideKind.BLOCK:
                if slide.block is None:
                    raise ValidationError(f"{slide_location}.block: is required")
                if slide.block.style not in {style.value for style in BlockStyle}:
                    raise ValidationError(
                        f"{slide_location}.block.style: unsupported value {slide.block.style!r}; "
                        f"expected one of {', '.join(style.value for style in BlockStyle)}"
                    )
                if not slide.block.body and not slide.block.bullets:
                    raise ValidationError(f"{slide_location}.block: body or bullets are required")
            elif slide.kind is SlideKind.CONCLUSION:
                if not slide.takeaway and not slide.bullets:
                    raise ValidationError(f"{slide_location}: conclusion requires takeaway or bullets")
            elif slide.kind is SlideKind.REFERENCES and not slide.items:
                raise ValidationError(f"{slide_location}.items: at least one reference is required")
            if slide.inline_image is not None:
                if not slide.inline_image.path:
                    raise ValidationError(f"{slide_location}.inline_image.path: is required")
                if slide.inline_image.align not in {"left", "right"}:
                    raise ValidationError(
                        f"{slide_location}.inline_image.align: unsupported value {slide.inline_image.align!r}; "
                        f"expected 'left' or 'right'"
                    )
                if slide.inline_image.width <= 0:
                    raise ValidationError(f"{slide_location}.inline_image.width: must be positive")


def content_warnings(deck: Deck) -> list[str]:
    warnings: list[str] = []
    if len(deck.sections) > 8:
        warnings.append(f"sections: {len(deck.sections)} sections may make the top navigation crowded")
    for section_index, section in enumerate(deck.sections):
        for slide_index, slide in enumerate(section.slides):
            location = f"sections[{section_index}].slides[{slide_index}]"
            if len(slide.bullets) > 8:
                warnings.append(f"{location}.bullets: {len(slide.bullets)} bullets may overflow the safe area")
            if slide.kind is SlideKind.CODE and slide.code is not None:
                line_count = slide.code.source.strip("\n").count("\n") + 1
                if line_count > 18:
                    warnings.append(f"{location}.code.source: {line_count} lines may overflow the slide")
            if slide.kind is SlideKind.TABLE and slide.table is not None:
                row_count = len(slide.table.rows)
                if row_count > 10:
                    warnings.append(f"{location}.table.rows: {row_count} rows may overflow the slide")
                for row_index, row in enumerate(slide.table.rows):
                    if len(row) > 6:
                        warnings.append(f"{location}.table.rows[{row_index}]: {len(row)} cells may overflow the slide width")
            if slide.kind is SlideKind.REFERENCES and len(slide.items) > 12:
                warnings.append(f"{location}.items: {len(slide.items)} references may overflow the slide")
    return warnings

