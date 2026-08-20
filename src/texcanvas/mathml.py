"""LaTeX → OMML conversion via pandoc, with graceful fallback.

PowerPoint/WPS store equations as OMML (Office Math Markup Language) under the
``m:`` namespace. ``python-pptx`` does not expose any math API, but it round-
trips unknown namespace elements verbatim, so we can:

1. ask ``pandoc`` to convert LaTeX → a throwaway ``.docx`` (pandoc emits OMML),
2. open that docx with ``zipfile``/``lxml`` and lift the ``<m:oMath>`` element,
3. ``deepcopy``-append it into a textbox paragraph on the real slide.

If pandoc is not installed or fails, callers fall back to the legacy Unicode
renderer in ``equation.py``, so decks still build (with degraded math).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_OMATH_TAG = "{%s}oMath" % MATH_NS


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
