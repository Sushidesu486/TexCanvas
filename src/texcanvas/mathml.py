"""LaTeX → OMML conversion via pandoc, with graceful fallback.

PowerPoint/WPS store equations as OMML (Office Math Markup Language) under the
``m:`` namespace. ``python-pptx`` does not expose any math API, but it round-
trips unknown namespace elements verbatim, so we can:

1. ask ``pandoc`` to convert LaTeX → a throwaway ``.docx`` (pandoc emits OMML),
2. open that docx with ``zipfile``/``lxml`` and lift the ``<m:oMath>`` element,
3. ``deepcopy``-append it into a textbox paragraph on the real slide.

If pandoc is not installed or fails, callers fall back to the legacy Unicode
renderer in ``equation.py``, so decks still build (with degraded math).

After python-pptx saves, the injected math elements are serialized with
synthetic numeric prefixes (``ns0:``, ``ns18:`` ...) and the ``m`` namespace is
not declared on the slide root — WPS in particular refuses to render math in
that state. ``normalize_math_namespaces_in_pptx`` rewrites each slide part so
the ``m`` namespace is declared on the ``p:sld`` root and all math elements use
the canonical ``m:`` prefix; call it on the saved pptx path.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_OMATH_TAG = "{%s}oMath" % MATH_NS
_PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def pandoc_available() -> bool:
    """Return True iff a usable ``pandoc`` is on PATH."""
    return shutil.which("pandoc") is not None


def latex_to_omml(latex: str) -> etree._Element | None:
    """Convert a LaTeX equation string to a single ``<m:oMath>`` element.

    Returns ``None`` when pandoc is unavailable or produced no math element
    (parse error / unsupported input), so callers can fall back.
    """
    if not pandoc_available():
        return None
    markdown = "$$" + latex.strip() + "$$\n"
    try:
        completed = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "docx", "-o", "-"],
            input=markdown.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return _extract_first_omath(completed.stdout)


def _extract_first_omath(docx_bytes: bytes) -> etree._Element | None:
    """Pull the first ``<m:oMath>`` out of a docx byte stream."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(docx_bytes)
        tmp_path = Path(tmp.name)
    try:
        if not zipfile.is_zipfile(tmp_path):
            return None
        with zipfile.ZipFile(tmp_path) as archive:
            try:
                document = archive.read("word/document.xml")
            except KeyError:
                return None
        root = etree.fromstring(document)
        omath = root.find(".//" + _OMATH_TAG)
        return omath
    except (etree.XMLSyntaxError, zipfile.BadZipFile):
        return None
    finally:
        tmp_path.unlink(missing_ok=True)


def normalize_math_namespaces_in_pptx(path: str | Path) -> bool:
    """Rewrite slide parts so math uses the canonical ``m:`` prefix.

    python-pptx serializes injected ``m:``-namespace elements with synthetic
    numeric prefixes and does not declare the math namespace on the ``p:sld``
    root. WPS does not render math in that state. This rebuilds each slide
    XML root with an ``m`` binding added to its namespace map so lxml emits the
    canonical ``m:`` prefix everywhere.

    Returns True if any slide part was rewritten. Safe to call on decks with
    no math: parts without ``m:`` elements are left untouched.
    """
    target = Path(path)
    if not target.is_file():
        return False
    changed = False
    tmp_zip = target.with_suffix(target.suffix + ".tmp")
    with zipfile.ZipFile(target, "r") as source:
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as dest:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename.startswith("ppt/slides/slide") and item.filename.endswith(".xml"):
                    if b"oMath" in data:
                        rewritten = _rewrite_slide_xml(data)
                        if rewritten is not None:
                            data = rewritten
                            changed = True
                dest.writestr(item, data)
    if changed:
        tmp_zip.replace(target)
    else:
        tmp_zip.unlink(missing_ok=True)
    return changed


def _rewrite_slide_xml(data: bytes) -> bytes | None:
    """Rebuild a slide XML root with the ``m`` namespace declared."""
    root = etree.fromstring(data)
    if root.tag != "{%s}sld" % _PRESENTATION_NS:
        return None
    if MATH_NS in root.nsmap.values():
        # Already declares a binding for the math namespace; nothing to do.
        return None
    new_root = etree.Element(root.tag, nsmap={**dict(root.nsmap), "m": MATH_NS})
    for key, value in root.attrib.items():
        new_root.set(key, value)
    new_root.text = root.text
    new_root.tail = root.tail
    for child in root:
        new_root.append(child)
    return etree.tostring(new_root, xml_declaration=True, encoding="UTF-8", standalone=True)


def strip_math_namespace_prefixes(element: etree._Element) -> None:
    """Normalize math element tags to use the ``m:`` prefix consistently.

    lxml may serialize math nodes with an arbitrary prefix (or none) depending
    on the source namespace map. PowerPoint/WPS accept any prefix bound to the
    math namespace, but a consistent ``m:`` keeps the output readable and
    matches what WPS itself writes.
    """
    for node in element.iter():
        if node.tag.startswith("{%s}" % MATH_NS):
            local = etree.QName(node).localname
            node.tag = "m:" + local

