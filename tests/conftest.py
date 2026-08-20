from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def deck_files(tmp_path: Path) -> tuple[Path, Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    Image.new("RGB", (800, 400), "#244E70").save(assets / "figure.png")
    yaml_path = tmp_path / "deck.yml"
    yaml_path.write_text(
        """
metadata:
  title: Integration deck
  author: Ada
  institute: Example Lab
  short_title: Demo
sections:
  - id: background
    title: Background
    short_title: BG
    slides:
      - kind: section_divider
        title: Background
      - kind: content
        title: Question
        body: A short introduction.
        bullets: [One, Two]
  - id: methods
    title: Methods
    short_title: Methods
    slides:
      - kind: two_columns
        title: Design
        left: {heading: Group A, bullets: [Treatment]}
        right: {heading: Group B, bullets: [Control]}
      - kind: image
        title: Figure
        image: {path: assets/figure.png, fit: cover}
        caption: A generated figure
  - id: conclusion
    title: Conclusion
    short_title: End
    slides:
      - kind: conclusion
        title: Takeaway
        takeaway: The method works.
        bullets: [Repeatable, Editable]
      - kind: references
        title: References
        items: ["Doe. Paper. 2025.", "Smith. Study. 2024."]
""".strip(),
        encoding="utf-8",
    )
    return yaml_path, tmp_path

