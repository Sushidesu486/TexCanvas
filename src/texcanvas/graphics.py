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


SUPPORTED_ENGINES = {"tikz"}
SUPPORTED_OUTPUTS = {"svg", "png"}
COMPILERS = {"pdflatex", "lualatex", "xelatex"}


@dataclass(frozen=True)
class FigureSpec:
    id: str
    engine: str
    source: Path
    outputs: tuple[str, ...]
    preamble: tuple[str, ...] = ()
    compiler: str = "pdflatex"


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
        compiler = str(value.get("compiler", "pdflatex"))
        if compiler not in COMPILERS:
            raise ValidationError(f"{location}.compiler: unsupported compiler {compiler!r}")
        specs.append(FigureSpec(figure_id, engine, source_path, outputs, preamble, compiler))
    return tuple(specs)


def _build_figure(spec: FigureSpec, output_dir: Path) -> list[Path]:
    compiler_path = shutil.which(spec.compiler)
    pdftocairo_path = shutil.which("pdftocairo") if ("svg" in spec.outputs or "png" in spec.outputs) else None
    if compiler_path is None:
        raise RenderError(f"figure {spec.id}: {spec.compiler} is not installed")
    if ("svg" in spec.outputs or "png" in spec.outputs) and pdftocairo_path is None:
        raise RenderError(f"figure {spec.id}: pdftocairo is required for SVG/PNG output")

    source = spec.source.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix=f"texcanvas-{spec.id}-") as temp_dir:
        temp = Path(temp_dir)
        tex_path = temp / f"{spec.id}.tex"
        pdf_path = temp / f"{spec.id}.pdf"
        tex_path.write_text(_tikz_document(source, spec.preamble), encoding="utf-8")
        command = [
            compiler_path,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            "-output-directory",
            str(temp),
            str(tex_path),
        ]
        completed = subprocess.run(
            command,
            cwd=spec.source.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode != 0 or not pdf_path.is_file():
            detail = _tail(completed.stdout)
            raise RenderError(f"figure {spec.id}: {spec.compiler} failed\n{detail}")

        generated: list[Path] = []
        for output_kind in spec.outputs:
            target = output_dir / f"{spec.id}.{output_kind}"
            if output_kind == "svg":
                _run_export(
                    [pdftocairo_path, "-svg", str(pdf_path), str(target)],
                    target,
                    spec.id,
                    "SVG",
                )
            else:
                prefix = target.with_suffix("")
                _run_export(
                    [pdftocairo_path, "-png", "-singlefile", "-r", "300", str(pdf_path), str(prefix)],
                    target,
                    spec.id,
                    "PNG",
                )
            generated.append(target)
        return generated


def _tikz_document(source: str, preamble: tuple[str, ...]) -> str:
    lines = [
        r"\documentclass[tikz,border=2pt]{standalone}",
        r"\usepackage{tikz}",
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
