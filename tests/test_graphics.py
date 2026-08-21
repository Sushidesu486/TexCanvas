from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from texcanvas.errors import ValidationError
from texcanvas.graphics import build_figures


TOOLS = ("pdflatex", "pdftocairo")
skip_without_tex = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in TOOLS),
    reason="TikZ toolchain is not installed",
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
    assert svg.read_text(encoding="utf-8").lstrip().startswith("<?xml")
    with Image.open(png) as image:
        assert image.format == "PNG"
        assert image.width > 0 and image.height > 0


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
