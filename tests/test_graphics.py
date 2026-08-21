from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from texcanvas.errors import RenderError, ValidationError
from texcanvas.graphics import build_figures


# SVG export needs a DVI-capable compiler (xelatex/lualatex) + dvisvgm; PNG
# rasterization needs pdftocairo.  When any of these is missing we skip the
# compilation tests rather than fail.
TOOLS = ("xelatex", "dvisvgm", "pdftocairo")
skip_without_tex = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in TOOLS),
    reason="TikZ toolchain (xelatex + dvisvgm + pdftocairo) is not installed",
)


@skip_without_tex
def test_build_figures_generates_svg_and_png(tmp_path: Path):
    source = tmp_path / "model.tikz"
    source.write_text(
        r"""
\begin{tikzpicture}
  \draw[->, thick] (0,0) -- (2,0) node[right] {Input};
  \node[draw, rounded corners] at (1,1) {Model};
\end{tikzpicture}
""".strip(),
        encoding="utf-8",
    )
    spec = tmp_path / "figures.yml"
    spec.write_text(
        """
figures:
  - id: model
    engine: tikz
    source: model.tikz
    outputs: [svg, png]
""".strip(),
        encoding="utf-8",
    )
    output = tmp_path / "output" / "figures"

    report = build_figures(spec, output)

    assert report.figure_count == 1
    assert report.outputs == (output / "model.svg", output / "model.png")
    svg = output / "model.svg"
    png = output / "model.png"
    svg_text = svg.read_text(encoding="utf-8")
    assert svg_text.lstrip().startswith("<?xml")
    # dvisvgm preserves selectable text rather than flattening glyphs to paths.
    assert svg_text.count("<text") > 0
    assert "Input" in svg_text
    with Image.open(png) as image:
        assert image.format == "PNG"
        assert image.width > 0 and image.height > 0


@skip_without_tex
def test_build_figures_svg_preserves_math_labels(tmp_path: Path):
    """LaTeX math inside TikZ stays as selectable text in the SVG.

    Regression guard: the previous pdftocairo -svg pipeline flattened every
    glyph to a <path>, so labels like ``$h=f(x)$`` were neither selectable nor
    searchable.  The dvisvgm path keeps them as <text> with an embedded font.
    """
    source = tmp_path / "math.tikz"
    source.write_text(
        r"\begin{tikzpicture}\node[draw] {$h=f(x)$};\end{tikzpicture}",
        encoding="utf-8",
    )
    spec = tmp_path / "figures.yml"
    spec.write_text(
        "figures:\n  - id: math\n    engine: tikz\n    source: math.tikz\n    outputs: [svg]\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"

    report = build_figures(spec, output)

    assert report.figure_count == 1
    svg = (output / "math.svg").read_text(encoding="utf-8")
    assert svg.count("<text") >= 2  # at least the variable letters render as text
    assert "font-face" in svg  # embedded font subset keeps the SVG self-contained


@skip_without_tex
def test_build_figures_respects_custom_dpi(tmp_path: Path):
    source = tmp_path / "dot.tikz"
    source.write_text(
        r"\begin{tikzpicture}\draw (0,0) rectangle (2,1);\end{tikzpicture}",
        encoding="utf-8",
    )
    spec = tmp_path / "figures.yml"
    spec.write_text(
        "figures:\n  - id: dot\n    engine: tikz\n    source: dot.tikz\n    outputs: [png]\n    dpi: 150\n",
        encoding="utf-8",
    )
    output = tmp_path / "out"

    report = build_figures(spec, output)
    assert report.outputs == (output / "dot.png",)

    baseline_spec = tmp_path / "baseline.yml"
    baseline_spec.write_text(
        "figures:\n  - id: dot\n    engine: tikz\n    source: dot.tikz\n    outputs: [png]\n    dpi: 600\n",
        encoding="utf-8",
    )
    baseline_output = tmp_path / "baseline-out"
    build_figures(baseline_spec, baseline_output)

    with Image.open(output / "dot.png") as low, Image.open(baseline_output / "dot.png") as high:
        assert high.width > low.width  # higher dpi yields a larger raster


@skip_without_tex
def test_build_figures_rejects_pdflatex_for_svg(tmp_path: Path):
    """pdflatex cannot emit DVI/XDV, so svg output must be refused early."""
    source = tmp_path / "m.tikz"
    source.write_text(
        r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}",
        encoding="utf-8",
    )
    spec = tmp_path / "figures.yml"
    spec.write_text(
        "figures:\n  - id: m\n    engine: tikz\n    source: m.tikz\n    outputs: [svg]\n    compiler: pdflatex\n",
        encoding="utf-8",
    )

    with pytest.raises(RenderError, match="cannot emit DVI/XDV"):
        build_figures(spec, tmp_path / "output")


def test_build_figures_rejects_unsupported_engine(tmp_path: Path):
    spec = tmp_path / "figures.yml"
    spec.write_text(
        """
figures:
  - id: graph
    engine: unknown
    source: graph.dot
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="unsupported figure engine"):
        build_figures(spec, tmp_path / "output")
