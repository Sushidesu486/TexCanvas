#!/usr/bin/env python3
"""Create the distributable zero-slide 16:9 starter template."""

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "templates" / "beamer-academic.pptx"
    output.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Beamer Academic Editable Template"
    prs.core_properties.subject = "16:9 starter template for texcanvas"
    prs.core_properties.author = "texcanvas"
    prs.save(output)
    print(f"Created {output}")


if __name__ == "__main__":
    main()

