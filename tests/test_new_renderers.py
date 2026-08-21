from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree
import pytest
from PIL import Image
from pptx import Presentation

from texcanvas import build
from texcanvas.mathml import normalize_math_namespaces_in_pptx


def _shape(slide, name):
    return next(shape for shape in slide.shapes if shape.name == name)


@pytest.fixture
def primitives_deck(tmp_path: Path) -> tuple[Path, Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    yaml_path = tmp_path / "deck.yml"
    yaml_path.write_text(
        r"""
metadata: {title: Primitives, short_title: Prim}
aspect: "16:9"
sections:
  - id: code
    title: Code
    short_title: Code
    slides:
      - kind: code
        title: Python
        code: {lang: python, source: "def f(x):\n    return x + 1\n"}
  - id: table
    title: Table
    short_title: Table
    slides:
      - kind: table
        title: Results
        table:
          header: [Method, Score]
          rows: [[Baseline, "0.8"], [Ours, "0.9"]]
          caption: Table 1
  - id: equation
    title: Equation
    short_title: Eq
    slides:
      - kind: equation
        title: Loss
        equation: |
          L = -\frac{1}{N}\sum_{i=1}^{N} y_i
  - id: block
    title: Blocks
    short_title: Blocks
    slides:
      - kind: block
        title: Note
        block: {style: default, title: Note, body: A note, bullets: [one, two]}
      - kind: block
        title: Alert
        block: {style: alert, title: Warning, body: Be careful}
      - kind: block
        title: Example
        block: {style: example, title: Demo, body: An example}
""".strip(),
        encoding="utf-8",
    )
    return yaml_path, tmp_path


def test_build_with_new_kinds_and_reopens(primitives_deck, tmp_path: Path):
    source, asset_root = primitives_deck
    output = tmp_path / "out.pptx"
    report = build(source, output, asset_root=asset_root)
    assert report.slide_count == 6
    assert report.section_count == 4
    assert report.warnings == ()
    assert output.is_file() and output.stat().st_size > 0
    assert len(Presentation(output).slides) == 6


def test_code_renders_with_panel_and_header_runs(primitives_deck, tmp_path: Path):
    source, asset_root = primitives_deck
    output = tmp_path / "code.pptx"
    build(source, output, asset_root=asset_root)
    prs = Presentation(output)
    code_slide = prs.slides[0]
    panel = _shape(code_slide, "DSH_CODE_PANEL")
    assert panel is not None
    body = _shape(code_slide, "DSH_CODE_BODY")
    # Line 1: "def f(x):" -> def keyword; Line 2: "    return x + 1" -> return keyword.
    first_line_runs = body.text_frame.paragraphs[0].runs
    second_line_runs = body.text_frame.paragraphs[1].runs
    assert any(run.text == "def" for run in first_line_runs)
    assert any(run.text == "return" for run in second_line_runs)
    # keyword run should be colored with the theme's keyword color
    def_run = next(run for run in first_line_runs if run.text == "def")
    assert str(def_run.font.color.rgb) == "0B3D91"


def test_table_renders_grid_and_header(primitives_deck, tmp_path: Path):
    source, asset_root = primitives_deck
    output = tmp_path / "table.pptx"
    build(source, output, asset_root=asset_root)
    prs = Presentation(output)
    slide = prs.slides[1]
    table_shape = _shape(slide, "DSH_TABLE")
    assert table_shape.has_table
    table = table_shape.table
    assert len(table.rows) == 3  # 1 header + 2 body
    assert len(table.columns) == 2
    assert table.cell(0, 0).text == "Method"
    assert table.cell(1, 0).text == "Baseline"
    assert table.cell(2, 1).text == "0.9"
    assert _shape(slide, "DSH_CAPTION").text == "Table 1"


def test_equation_renders_omml_when_pandoc_available(primitives_deck, tmp_path: Path):
    source, asset_root = primitives_deck
    output = tmp_path / "eq.pptx"
    build(source, output, asset_root=asset_root)
    prs = Presentation(output)
    slide = prs.slides[2]
    body = _shape(slide, "DSH_EQUATION")
    # With pandoc installed, the equation renders as a native <m:oMath> element.
    MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    omaths = list(body.text_frame._txBody.iter("{%s}oMath" % MATH_NS))
    assert len(omaths) == 1
    # Structure: a fraction (m:f) and an n-ary sum (m:nary) with a subscript (m:sSub).
    tags = {__import__("lxml").etree.QName(node).localname for node in omaths[0].iter() if __import__("lxml").etree.QName(node).namespace == MATH_NS}
    assert "f" in tags       # \frac{1}{N}
    assert "nary" in tags    # \sum
    assert "sSub" in tags    # y_i


@pytest.mark.skipif(__import__("shutil").which("pandoc") is None, reason="pandoc not installed")
def test_equation_math_fonts_use_wordprocessing_run_properties(primitives_deck, tmp_path: Path):
    source, asset_root = primitives_deck
    output = tmp_path / "eq-fonts.pptx"
    build(source, output, asset_root=asset_root)
    body = _shape(Presentation(output).slides[2], "DSH_EQUATION")
    math_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    drawing_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
    omath = next(body.text_frame._txBody.iter("{%s}oMath" % math_ns))
    runs = list(omath.iter("{%s}r" % math_ns))
    assert runs
    for run in runs:
        math_rpr = run.find("{%s}rPr" % math_ns)
        assert math_rpr is None or not any(child.tag.startswith("{%s}" % drawing_ns) for child in math_rpr)
        word_rpr = run.find("{%s}rPr" % word_ns)
        assert word_rpr is not None
        fonts = word_rpr.find("{%s}rFonts" % word_ns)
        assert fonts is not None
        assert fonts.get("{%s}ascii" % word_ns) == "Helvetica"
        assert fonts.get("{%s}hAnsi" % word_ns) == "Helvetica"
        assert fonts.get("{%s}eastAsia" % word_ns) == "苹方-简"
        assert fonts.get("{%s}cs" % word_ns) == "苹方-简"


@pytest.mark.skipif(__import__("shutil").which("pandoc") is None, reason="pandoc not installed")
def test_equation_zip_xml_is_renderable_and_namespace_normalization_is_idempotent(primitives_deck, tmp_path: Path):
    source, asset_root = primitives_deck
    output = tmp_path / "eq-xml.pptx"
    build(source, output, asset_root=asset_root)

    with zipfile.ZipFile(output) as archive:
        slide_xml = archive.read("ppt/slides/slide3.xml")
    root = etree.fromstring(slide_xml)
    math_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    drawing_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
    assert root.nsmap["m"] == math_ns
    assert root.nsmap["w"] == word_ns
    omath = root.find(".//{%s}oMath" % math_ns)
    assert omath is not None
    for math_rpr in omath.iter("{%s}rPr" % math_ns):
        assert not any(etree.QName(child).namespace == drawing_ns for child in math_rpr)
    assert normalize_math_namespaces_in_pptx(output) is False


@pytest.mark.skipif(__import__("shutil").which("pandoc") is None, reason="pandoc not installed")
def test_equation_matrix_renders_as_omml(tmp_path: Path):
    source = tmp_path / "matrix.yml"
    source.write_text(
        r"""
metadata: {title: Matrix}
sections:
  - id: m
    title: M
    short_title: M
    slides:
      - kind: equation
        title: Matrix
        equation: |
          \begin{pmatrix} a & b \\ c & d \end{pmatrix}
""".strip(),
        encoding="utf-8",
    )
    output = tmp_path / "matrix.pptx"
    build(source, output, asset_root=tmp_path)
    prs = Presentation(output)
    body = _shape(prs.slides[0], "DSH_EQUATION")
    MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    omaths = list(body.text_frame._txBody.iter("{%s}oMath" % MATH_NS))
    assert len(omaths) == 1
    tags = {__import__("lxml").etree.QName(node).localname for node in omaths[0].iter() if __import__("lxml").etree.QName(node).namespace == MATH_NS}
    assert "d" in tags and "m" in tags  # delimiter (pmatrix) + matrix


def test_blocks_render_panel_and_title_for_each_style(primitives_deck, tmp_path: Path):
    source, asset_root = primitives_deck
    output = tmp_path / "blocks.pptx"
    build(source, output, asset_root=asset_root)
    prs = Presentation(output)
    for index, expected_title in enumerate(["Note", "Warning", "Demo"]):
        slide = prs.slides[3 + index]
        _shape(slide, "DSH_BLOCK_PANEL")
        title = _shape(slide, "DSH_BLOCK_TITLE")
        assert title.text == expected_title


def test_pptx_zip_valid_for_new_kinds(primitives_deck, tmp_path: Path):
    source, asset_root = primitives_deck
    output = tmp_path / "zip.pptx"
    build(source, output, asset_root=asset_root)
    assert zipfile.is_zipfile(output)
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert "[Content_Types].xml" in names
    assert "ppt/slides/slide1.xml" in names
