#!/usr/bin/env python3
"""Create the distributable zero-slide 16:9 starter template.

Output path: src/texcanvas/templates/beamer-academic.pptx (shipped inside the package).

The master slide is given a solid fill in the deck background color (F7F9FC) so
that ``texcanvas build`` produces a correctly-backgrounded deck without needing
to paint a full-slide rectangle shape per slide. When a custom template is
supplied via ``-t``, users keep full control over their own master background.
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "src" / "texcanvas" / "templates" / "beamer-academic.pptx"
    output.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Beamer Academic Editable Template"
    prs.core_properties.subject = "16:9 starter template for texcanvas"
    prs.core_properties.author = "texcanvas"
    prs.slide_master.background.fill.solid()
    prs.slide_master.background.fill.fore_color.rgb = RGBColor.from_string("F7F9FC")
    prs.save(output)
    print(f"Created {output}")


if __name__ == "__main__":
    main()
