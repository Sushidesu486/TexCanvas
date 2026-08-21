"""Reproducible figure generation for papers and presentations."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import InputError, RenderError, ValidationError


SUPPORTED_ENGINES = {"tikz", "pgfplots"}
SUPPORTED_OUTPUTS = {"svg", "png"}
# xelatex/lualatex emit DVI/XDV via ``-no-pdf``, letting dvisvgm produce vector
# SVG with selectable text.  pdflatex only emits PDF, so its SVG export degrades
# to flattened outlines via pdftocairo.
COMPILERS = {"xelatex", "lualatex", "pdflatex"}
DEFAULT_COMPILER = "xelatex"
# Compilers that can emit DVI/XDV (vector-SVG capable).
DVI_CAPABLE_COMPILERS = {"xelatex", "lualatex"}
DEFAULT_DPI = 300
# Per-engine LaTeX document assembly.  tikz draws structural diagrams; pgfplots
# draws data plots (bars, lines, heatmaps) and needs its package + compat flag.
ENGINE_PACKAGES: dict[str, tuple[str, ...]] = {
    "tikz": (r"\usepackage{tikz}",),
    "pgfplots": (r"\usepackage{tikz}", r"\usepackage{pgfplots}", r"\pgfplotsset{compat=1.18}"),
}


@dataclass(frozen=True)
class FigureSpec:
    id: str
    engine: str
    source: Path
    outputs: tuple[str, ...]
    preamble: tuple[str, ...] = ()
    compiler: str = DEFAULT_COMPILER
    dpi: int = DEFAULT_DPI


@dataclass(frozen=True)
class FigureBuildReport:
    figure_count: int
    outputs: tuple[Path, ...]


def build_figures(
    input: str | Path,
    output: str | Path,
    *,
    asset_root: str | Path | None = None,
) -> FigureBuildReport:
    """Build all figure specs in a figures YAML file."""
    input_path = Path(input).expanduser().resolve()
    output_path = Path(output).expanduser().resolve()
    root = Path(asset_root).expanduser().resolve() if asset_root is not None else input_path.parent
    specs = load_figures(input_path, root)
    output_path.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for spec in specs:
        generated.extend(_build_figure(spec, output_path))
    return FigureBuildReport(figure_count=len(specs), outputs=tuple(generated))


def load_figures(path: str | Path, asset_root: Path | None = None) -> tuple[FigureSpec, ...]:
    """Load and validate a figures YAML file without running a backend."""
    source = Path(path).expanduser().resolve()
    root = asset_root or source.parent
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError(f"figures: cannot read {source}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise InputError(f"figures: invalid YAML in {source}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValidationError("figures: expected a mapping")
    entries = raw.get("figures")
    if not isinstance(entries, list) or not entries:
        raise ValidationError("figures: expected a non-empty list")

    specs: list[FigureSpec] = []
    seen: set[str] = set()
    for index, value in enumerate(entries):
        location = f"figures[{index}]"
        if not isinstance(value, dict):
            raise ValidationError(f"{location}: expected a mapping")
        figure_id = _required_text(value.get("id"), f"{location}.id")
        if figure_id in seen:
            raise ValidationError(f"{location}.id: duplicate value {figure_id!r}")
        seen.add(figure_id)
        engine = _required_text(value.get("engine"), f"{location}.engine")
        if engine not in SUPPORTED_ENGINES:
            supported = ", ".join(sorted(SUPPORTED_ENGINES))
            raise ValidationError(f"{location}.engine: unsupported figure engine {engine!r}; expected {supported}")
        source_text = _required_text(value.get("source"), f"{location}.source")
        source_path = (root / source_text).resolve()
        if not source_path.is_file():
            raise InputError(f"{location}.source: file not found: {source_path}")
        outputs = _outputs(value.get("outputs", ("svg", "png")), location)
        preamble = _preamble(value.get("preamble", ()), location)
        compiler = str(value.get("compiler", DEFAULT_COMPILER))
        if compiler not in COMPILERS:
            raise ValidationError(f"{location}.compiler: unsupported compiler {compiler!r}")
        dpi = _dpi(value.get("dpi", DEFAULT_DPI), location)
        specs.append(FigureSpec(figure_id, engine, source_path, outputs, preamble, compiler, dpi))
    return tuple(specs)


def _build_figure(spec: FigureSpec, output_dir: Path) -> list[Path]:
    needs_svg = "svg" in spec.outputs
    needs_png = "png" in spec.outputs
    # SVG needs a DVI/XDV so dvisvgm can emit selectable text.  PDF-only
    # compilers (pdflatex) would force a flattened-outline fallback.
    if needs_svg and spec.compiler not in DVI_CAPABLE_COMPILERS:
        capable = ", ".join(sorted(DVI_CAPABLE_COMPILERS))
        raise RenderError(
            f"figure {spec.id}: compiler {spec.compiler!r} cannot emit DVI/XDV; "
            f"use one of {capable} for svg output"
        )

    dvisvgm_path = shutil.which("dvisvgm") if needs_svg else None
    pdftocairo_path = shutil.which("pdftocairo") if needs_png else None
    if needs_svg and dvisvgm_path is None:
        raise RenderError(f"figure {spec.id}: dvisvgm is required for svg output")
    if needs_png and pdftocairo_path is None:
        raise RenderError(f"figure {spec.id}: pdftocairo is required for png output")

    source = spec.source.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix=f"texcanvas-{spec.id}-") as temp_dir:
        temp = Path(temp_dir)
        tex_path = temp / f"{spec.id}.tex"
        tex_path.write_text(_tikz_document(source, spec.preamble, spec.engine), encoding="utf-8")

        vector_path, pdf_path = _compile(spec, tex_path, temp, needs_svg, needs_png)

        generated: list[Path] = []
        if needs_svg:
            target = output_dir / f"{spec.id}.svg"
            _run_export(
                [dvisvgm_path, "--exact-bbox", "--font-format=woff2", str(vector_path), "-o", str(target)],
                target,
                spec.id,
                "SVG",
            )
            generated.append(target)
        if needs_png:
            target = output_dir / f"{spec.id}.png"
            prefix = target.with_suffix("")
            _run_export(
                [pdftocairo_path, "-png", "-singlefile", "-r", str(spec.dpi), str(pdf_path), str(prefix)],
                target,
                spec.id,
                "PNG",
            )
            generated.append(target)
        return generated


def _compile(spec: FigureSpec, tex_path: Path, temp: Path, needs_vector: bool, needs_pdf: bool) -> tuple[Path | None, Path | None]:
    """Compile ``tex_path`` into the DVI/XDV and PDF artifacts required.

    DVI-capable compilers (xelatex/lualatex) are run with ``-no-pdf`` to emit a
    vector file, then ``xdvipdfmx`` produces the PDF for PNG rasterization.
    pdflatex emits a PDF directly (no selectable-text SVG available).
    """
    if spec.compiler in DVI_CAPABLE_COMPILERS:
        vector_path = temp / f"{spec.id}.xdv"
        command = [
            spec.compiler,
            "-no-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            "-output-directory",
            str(temp),
            str(tex_path),
        ]
        completed = _run_compiler(command, spec.source.parent)
        if completed.returncode != 0 or not vector_path.is_file():
            raise RenderError(f"figure {spec.id}: {spec.compiler} failed\n{_tail(completed.stdout)}")
        pdf_path = None
        if needs_pdf:
            pdf_path = temp / f"{spec.id}.pdf"
            _produce_pdf_from_xdv(vector_path, pdf_path, spec.id)
        return vector_path, pdf_path

    # pdflatex: PDF only.
    pdf_path = temp / f"{spec.id}.pdf"
    command = [
        spec.compiler,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-output-directory",
        str(temp),
        str(tex_path),
    ]
    completed = _run_compiler(command, spec.source.parent)
    if completed.returncode != 0 or not pdf_path.is_file():
        raise RenderError(f"figure {spec.id}: {spec.compiler} failed\n{_tail(completed.stdout)}")
    return None, pdf_path


def _produce_pdf_from_xdv(xdv_path: Path, pdf_path: Path, figure_id: str) -> None:
    xdvipdfmx_path = shutil.which("xdvipdfmx")
    if xdvipdfmx_path is None:
        raise RenderError(f"figure {figure_id}: xdvipdfmx is required to produce pdf from xdv")
    command = [xdvipdfmx_path, "-o", str(pdf_path), str(xdv_path)]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0 or not pdf_path.is_file():
        raise RenderError(f"figure {figure_id}: xdvipdfmx failed\n{_tail(completed.stdout)}")


def _run_compiler(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _tikz_document(source: str, preamble: tuple[str, ...], engine: str = "tikz") -> str:
    # ``standalone`` is loaded WITHOUT its ``tikz`` option so that the PGF
    # system-layer driver below takes effect.  Passing ``tikz`` to the class
    # makes standalone \RequirePackage{tikz} during \documentclass, before our
    # \pgfsysdriver override is seen — PGF then picks the platform default
    # driver (xetex/pdftex) and dvisvgm loses every drawn shape, keeping only
    # text.  pgfsys-dvisvgm.def emits the dvisvgm-native specials dvisvgm reads.
    lines = [
        r"\documentclass[border=2pt]{standalone}",
        r"\def\pgfsysdriver{pgfsys-dvisvgm.def}",
        *ENGINE_PACKAGES.get(engine, ENGINE_PACKAGES["tikz"]),
        *preamble,
        r"\begin{document}",
        source,
        r"\end{document}",
        "",
    ]
    return "\n".join(lines)


def _run_export(command: list[str | None], target: Path, figure_id: str, format_name: str) -> None:
    completed = subprocess.run(
        [argument for argument in command if argument is not None],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0 or not target.is_file():
        detail = _tail(completed.stdout)
        raise RenderError(f"figure {figure_id}: {format_name} export failed\n{detail}")


def _tail(output: str, lines: int = 20) -> str:
    values = output.strip().splitlines()
    return "\n".join(values[-lines:])


def _required_text(value: Any, location: str) -> str:
    if value is None or not str(value).strip():
        raise ValidationError(f"{location}: is required")
    return str(value).strip()


def _outputs(value: Any, location: str) -> tuple[str, ...]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)) or not value:
        raise ValidationError(f"{location}.outputs: expected a non-empty list")
    outputs = tuple(str(item).lower() for item in value)
    unsupported = [item for item in outputs if item not in SUPPORTED_OUTPUTS]
    if unsupported:
        raise ValidationError(f"{location}.outputs: unsupported format {unsupported[0]!r}; expected svg or png")
    if len(set(outputs)) != len(outputs):
        raise ValidationError(f"{location}.outputs: duplicate format")
    return outputs


def _preamble(value: Any, location: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{location}.preamble: expected text or list")
    return tuple(str(item) for item in value)


def _dpi(value: Any, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{location}.dpi: expected a positive integer")
    if value <= 0:
        raise ValidationError(f"{location}.dpi: must be positive")
    return value
