from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    primary: str = "16324F"
    secondary: str = "244E70"
    pale: str = "D9E3EC"
    background: str = "F7F9FC"
    text: str = "263238"
    muted: str = "65727E"
    accent: str = "F4A261"
    white: str = "FFFFFF"
    chinese_font: str = "苹方-简"
    latin_font: str = "Helvetica"
    code_font: str = "Menlo"
    # code block
    code_background: str = "F2F4F7"
    code_text: str = "24292E"
    code_comment: str = "6A737D"
    code_keyword: str = "0B3D91"
    code_string: str = "0A7B5C"
    code_number: str = "9C27B0"
    code_border: str = "D0D7DE"
    # table
    table_header_fill: str = "16324F"
    table_header_text: str = "FFFFFF"
    table_row_alt: str = "EEF3F8"
    table_grid: str = "C7D2DC"
    # beamer blocks
    block_default_title: str = "16324F"
    block_default_body: str = "E8EEF3"
    block_alert_title: str = "B23A48"
    block_alert_body: str = "FBE9EB"
    block_example_title: str = "2A6E3F"
    block_example_body: str = "E8F3EC"
    # equation
    equation_fill: str = "F2F4F7"
    equation_border: str = "D0D7DE"


DEFAULT_THEME = Theme()

