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
    chinese_font: str = "Noto Sans CJK SC"
    latin_font: str = "Arial"
    code_font: str = "Menlo"


DEFAULT_THEME = Theme()

