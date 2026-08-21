from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from .assets import validate_assets
from .errors import InputError, RenderError, TexCanvasError
from .loader import load_deck
from .mathml import normalize_math_namespaces_in_pptx
from .render import render_deck
from .scaffold import bundled_template_path
from .sync import apply_overrides
from .theme import DEFAULT_THEME
from .validate import content_warnings


@dataclass(frozen=True)
class BuildReport:
    output: Path
    slide_count: int
    section_count: int
    warnings: tuple[str, ...]


def _remove_all_slides(prs: Presentation) -> None:
    slide_ids = prs.slides._sldIdLst  # python-pptx currently has no public slide-delete API
    for slide_id in list(slide_ids):
        relationship_id = slide_id.rId
        prs.part.drop_rel(relationship_id)
        slide_ids.remove(slide_id)


def _presentation(template: Path | None) -> tuple[Presentation, bool]:
    if template is None:
        template = bundled_template_path()
    if not template.is_file():
        raise InputError(f"template: file not found: {template}")
    try:
        prs = Presentation(str(template))
    except Exception as exc:
        raise InputError(f"template: cannot open {template}: {exc}") from exc
    _remove_all_slides(prs)
    return prs, False


def build(
    input: str | Path,
    output: str | Path,
    template: str | Path | None = None,
    strict: bool = True,
    asset_root: str | Path | None = None,
    overrides: str | Path | None = None,
) -> BuildReport:
    input_path = Path(input).expanduser().resolve()
    output_path = Path(output).expanduser().resolve()
    template_path = Path(template).expanduser().resolve() if template is not None else None
    root = Path(asset_root).expanduser().resolve() if asset_root is not None else input_path.parent

    deck = load_deck(input_path)
    warnings = content_warnings(deck)
    warnings.extend(validate_assets(deck, root, strict))
    prs, draw_code_background = _presentation(template_path)
    render_deck(
        prs,
        deck,
        theme=DEFAULT_THEME,
        asset_root=root,
        strict=strict,
        warnings=warnings,
        draw_code_background=draw_code_background,
    )
    if overrides is not None:
        apply_overrides(prs, overrides)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        prs.save(str(temporary))
        # python-pptx serializes injected OMML with synthetic numeric prefixes
        # and omits the math namespace on the slide root, which WPS won't render.
        # Rewrite slide parts to use the canonical m: prefix (no-op when no math).
        normalize_math_namespaces_in_pptx(temporary)
        os.replace(temporary, output_path)
    except TexCanvasError:
        raise
    except Exception as exc:
        raise RenderError(f"output: cannot save {output_path}: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)

    return BuildReport(
        output=output_path,
        slide_count=deck.slide_count,
        section_count=len(deck.sections),
        warnings=tuple(warnings),
    )
