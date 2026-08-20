from pathlib import Path

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
