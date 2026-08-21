from pathlib import Path
import shutil

import pytest
from texcanvas.cli import main


def test_cli_builds_and_prints_summary(deck_files: tuple[Path, Path], tmp_path: Path, capsys):
    source, asset_root = deck_files
    output = tmp_path / "cli.pptx"
    status = main(["build", str(source), "--asset-root", str(asset_root), "-o", str(output)])
    captured = capsys.readouterr()
    assert status == 0
    assert "Slides: 6" in captured.out
    assert "Warnings: 0" in captured.out
    assert output.exists()


@pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("pdftocairo") is None,
    reason="TikZ toolchain is not installed",
)
def test_cli_graphics_builds_tikz(tmp_path: Path, capsys):
    source = tmp_path / "figure.tikz"
    source.write_text(
        r"""\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}""",
        encoding="utf-8",
    )
    spec = tmp_path / "figures.yml"
    spec.write_text(
        "figures:\n  - id: smoke\n    engine: tikz\n    source: figure.tikz\n    outputs: [svg]\n",
        encoding="utf-8",
    )
    status = main(["graphics", "build", str(spec), "-o", str(tmp_path / "output")])
    captured = capsys.readouterr()
    assert status == 0
    assert "Figures: 1" in captured.out
    assert (tmp_path / "output" / "smoke.svg").is_file()
