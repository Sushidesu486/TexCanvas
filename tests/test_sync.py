from __future__ import annotations

import posixpath
import zipfile
from copy import deepcopy
from pathlib import Path

import yaml
from lxml import etree

from texcanvas import build
from texcanvas.sync import pull

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _q(namespace: str, tag: str) -> str:
    return "{%s}%s" % (namespace, tag)


def _shape(root: etree._Element, name: str) -> etree._Element | None:
    for shape in list(root.iter(_q(P_NS, "sp"))) + list(root.iter(_q(P_NS, "pic"))):
        nv_tag = "nvSpPr" if shape.tag == _q(P_NS, "sp") else "nvPicPr"
        c_nv_pr = shape.find("./%s/%s" % (_q(P_NS, nv_tag), _q(P_NS, "cNvPr")))
        if c_nv_pr is not None and c_nv_pr.get("name") == name:
            return shape
    return None


def _mutate_pptx_for_human_edits(source: Path, target: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}

    slide2_path = "ppt/slides/slide2.xml"
    slide3_path = "ppt/slides/slide3.xml"
    slide4_path = "ppt/slides/slide4.xml"
    slide2 = etree.fromstring(entries[slide2_path])
    body = _shape(slide2, "DSH_BODY")
    body.find(".//{%s}t" % A_NS).text = "Human edited body"
    off = body.find(".//{%s}off" % A_NS)
    assert off is not None
    off.set("x", "2220000")

    slide3 = etree.fromstring(entries[slide3_path])
    block_panel = _shape(slide3, "DSH_LEFT_PANEL")
    block_off = block_panel.find(".//{%s}off" % A_NS)
    assert block_off is not None
    block_off.set("x", "3330000")

    slide4 = etree.fromstring(entries[slide4_path])
    picture = next(slide4.iter(_q(P_NS, "pic")))
    picture = deepcopy(picture)
    source_rels = etree.fromstring(entries["ppt/slides/_rels/slide4.xml.rels"])
    target_rels = etree.fromstring(entries["ppt/slides/_rels/slide2.xml.rels"])
    image_rel = next(
        rel for rel in source_rels if rel.get("Type", "").endswith("/image")
    )
    new_rid = "rIdHumanImage"
    etree.SubElement(
        target_rels,
        _q(PKG_REL_NS, "Relationship"),
        Id=new_rid,
        Type=image_rel.get("Type"),
        Target=image_rel.get("Target"),
    )
    blip = picture.find(".//{%s}blip" % A_NS)
    assert blip is not None
    blip.set(_q(R_NS, "embed"), new_rid)
    c_nv_pr = picture.find("./%s/%s" % (_q(P_NS, "nvPicPr"), _q(P_NS, "cNvPr")))
    assert c_nv_pr is not None
    c_nv_pr.set("id", "99")
    c_nv_pr.set("name", "HumanInsertedImage")
    sp_tree = slide2.find(".//{%s}spTree" % P_NS)
    assert sp_tree is not None
    sp_tree.append(picture)

    presentation = etree.fromstring(entries["ppt/presentation.xml"])
    sld_ids = presentation.find("./{%s}sldIdLst" % P_NS)
    assert sld_ids is not None and len(sld_ids) >= 2
    first, second = sld_ids[0], sld_ids[1]
    sld_ids.remove(first)
    sld_ids.insert(1, first)

    entries[slide2_path] = etree.tostring(slide2, xml_declaration=True, encoding="UTF-8", standalone=True)
    entries[slide3_path] = etree.tostring(slide3, xml_declaration=True, encoding="UTF-8", standalone=True)
    entries["ppt/slides/_rels/slide2.xml.rels"] = etree.tostring(
        target_rels, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    entries["ppt/presentation.xml"] = etree.tostring(
        presentation, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def test_sync_pull_round_trips_xml_edits_and_inserted_image(deck_files: tuple[Path, Path], tmp_path: Path):
    source, asset_root = deck_files
    original = tmp_path / "original.pptx"
    edited = tmp_path / "edited.pptx"
    overrides = tmp_path / "overrides.yml"
    rebuilt = tmp_path / "rebuilt.pptx"
    build(source, original, asset_root=asset_root)
    _mutate_pptx_for_human_edits(original, edited)

    report = pull(edited, overrides)
    assert report.slide_count == 6
    data = yaml.safe_load(overrides.read_text(encoding="utf-8"))
    slides = data["slides"]
    assert slides[0]["id"] == "background/slide-2"
    assert slides[1]["id"] == "background/slide-1"
    edited_slide = next(item for item in slides if item["id"] == "background/slide-2")
    assert edited_slide["shapes"]["DSH_BODY"]["text"].startswith("Human edited body")
    assert edited_slide["shapes"]["DSH_BODY"]["frame"]["x"] == 2.4278
    moved_slide = next(item for item in slides if item["id"] == "methods/slide-1")
    assert moved_slide["shapes"]["DSH_LEFT_PANEL"]["frame"]["x"] == 3.6417
    image = edited_slide["shapes"]["HumanInsertedImage"]
    assert image["kind"] == "picture"
    assert (overrides.parent / image["asset"]).is_file()

    build(source, rebuilt, asset_root=asset_root, overrides=overrides)
    with zipfile.ZipFile(rebuilt) as archive:
        rebuilt_entries = {name: archive.read(name) for name in archive.namelist()}
        slide_roots = [
            etree.fromstring(rebuilt_entries[name])
            for name in rebuilt_entries
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
        rebuilt_presentation = etree.fromstring(rebuilt_entries["ppt/presentation.xml"])
        presentation_rels = etree.fromstring(rebuilt_entries["ppt/_rels/presentation.xml.rels"])
    rebuilt_slide = next(root for root in slide_roots if "Human edited body" in "".join(root.itertext()))
    assert any(_shape(root, "HumanInsertedImage") is not None for root in slide_roots)
    moved_root = next(root for root in slide_roots if _shape(root, "DSH_LEFT_PANEL") is not None)
    moved_shape = _shape(moved_root, "DSH_LEFT_PANEL")
    assert moved_shape.find(".//{%s}off" % A_NS).get("x") == "3330000"
    rebuilt_ids = rebuilt_presentation.find("./{%s}sldIdLst" % P_NS)
    assert rebuilt_ids is not None
    rel_targets = {
        rel.get("Id"): posixpath.normpath(posixpath.join("ppt", rel.get("Target", "")))
        for rel in presentation_rels
        if rel.get("Type", "").endswith("/slide")
    }
    ordered_names = []
    for sld_id in rebuilt_ids:
        slide_path = rel_targets[sld_id.get(_q(R_NS, "id"))]
        slide_root = etree.fromstring(rebuilt_entries[slide_path])
        ordered_names.append(slide_root.find("./{%s}cSld" % P_NS).get("name").removeprefix("texcanvas:"))
    assert ordered_names[:2] == ["background/slide-2", "background/slide-1"]
