from __future__ import annotations

from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from ..model import Slide
from .common import RenderContext, add_box, add_text, set_run_font

# Keywords reserved in several common languages; a small, self-contained set.
_KEYWORDS: dict[str, set[str]] = {
    "python": {
        "False", "None", "True", "and", "as", "assert", "async", "await", "break",
        "class", "continue", "def", "del", "elif", "else", "except", "finally",
        "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
        "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
    },
    "c": {
        "auto", "break", "case", "char", "const", "continue", "default", "do",
        "double", "else", "enum", "extern", "float", "for", "goto", "if", "inline",
        "int", "long", "register", "return", "short", "signed", "sizeof", "static",
        "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
    },
    "cpp": {
        "alignas", "alignof", "auto", "bool", "break", "case", "catch", "char",
        "class", "const", "constexpr", "continue", "decltype", "default", "delete",
        "do", "double", "else", "enum", "explicit", "extern", "false", "float", "for",
        "friend", "goto", "if", "inline", "int", "long", "namespace", "new",
        "noexcept", "nullptr", "operator", "private", "protected", "public",
        "register", "return", "short", "signed", "sizeof", "static", "struct",
        "switch", "template", "this", "throw", "true", "try", "typedef", "typename",
        "union", "unsigned", "using", "virtual", "void", "volatile", "while",
    },
    "java": {
        "abstract", "assert", "boolean", "break", "byte", "case", "catch",
        "char", "class", "const", "continue", "default", "do", "double", "else",
        "enum", "extends", "final", "finally", "float", "for", "goto", "if",
        "implements", "import", "instanceof", "int", "interface", "long",
        "native", "new", "package", "private", "protected", "public", "return",
        "short", "static", "strictfp", "super", "switch", "synchronized",
        "this", "throw", "throws", "transient", "try", "void", "volatile", "while",
        "true", "false", "null",
    },
    "javascript": {
        "break", "case", "catch", "class", "const", "continue", "debugger",
        "default", "delete", "do", "else", "export", "extends", "finally",
        "for", "function", "if", "import", "in", "instanceof", "new", "return",
        "super", "switch", "this", "throw", "try", "typeof", "var", "void",
        "while", "with", "yield", "let", "async", "await", "true", "false",
        "null", "undefined",
    },
    "rust": {
        "as", "async", "await", "break", "const", "continue", "crate", "dyn",
        "else", "enum", "extern", "false", "fn", "for", "if", "impl", "in",
        "let", "loop", "match", "mod", "move", "mut", "pub", "ref", "return",
        "self", "Self", "static", "struct", "super", "trait", "true", "type",
        "unsafe", "use", "where", "while",
    },
    "go": {
        "break", "case", "chan", "const", "continue", "default", "defer",
        "else", "fallthrough", "for", "func", "go", "goto", "if", "import",
        "interface", "map", "package", "range", "return", "select", "struct",
        "switch", "type", "var", "true", "false", "nil",
    },
}

# Fallback keyword set: union of the common C-family languages.
BUILTIN_KEYWORDS = _KEYWORDS["python"] | _KEYWORDS["c"] | _KEYWORDS["cpp"]

_TOKEN_TEXT = "text"
_TOKEN_COMMENT = "comment"
_TOKEN_STRING = "string"
_TOKEN_KEYWORD = "keyword"
_TOKEN_NUMBER = "number"


def _normalize_lang(lang: str) -> str:
    normalized = lang.strip().casefold().replace("+", "p")
    aliases = {
        "py": "python",
        "csharp": "c#",
        "cs": "c#",
        "js": "javascript",
        "ts": "typescript",
    }
    return aliases.get(normalized, normalized)


def _tokenize_line(line: str, keywords: set[str]) -> list[tuple[str, str]]:
    """Split a source line into (text, token_type) pairs for coloring."""
    stripped = line.lstrip()
    if stripped.startswith(("#", "//")):
        return [(line, _TOKEN_COMMENT)]
    tokens: list[tuple[str, str]] = []
    index, n = 0, len(line)
    while index < n:
        char = line[index]
        if char == "#":
            tokens.append((line[index:], _TOKEN_COMMENT))
            break
        if char == "/" and index + 1 < n and line[index + 1] == "/":
            tokens.append((line[index:], _TOKEN_COMMENT))
            break
        if char == '"':
            end = line.find('"', index + 1)
            end = n if end == -1 else end + 1
            tokens.append((line[index:end], _TOKEN_STRING))
            index = end
            continue
        if char == "'":
            end = line.find("'", index + 1)
            end = n if end == -1 else end + 1
            tokens.append((line[index:end], _TOKEN_STRING))
            index = end
            continue
        if char.isdigit():
            end = index
            while end < n and (line[end].isdigit() or line[end] == "."):
                end += 1
            tokens.append((line[index:end], _TOKEN_NUMBER))
            index = end
            continue
        if char.isalpha() or char == "_":
            end = index
            while end < n and (line[end].isalnum() or line[end] == "_"):
                end += 1
            word = line[index:end]
            tokens.append((word, _TOKEN_KEYWORD if word in keywords else _TOKEN_TEXT))
            index = end
            continue
        end = index
        while end < n and not (line[end].isalnum() or line[end] == "_" or line[end] in "\"'#"):
            end += 1
        if end == index:
            end = index + 1
        tokens.append((line[index:end], _TOKEN_TEXT))
        index = end
    return tokens


def render_code(ctx: RenderContext, slide: Slide) -> None:
    assert slide.code is not None
    code = slide.code
    source = code.source.replace("\r\n", "\n").strip("\n")
    lines = source.split("\n") if source else [""]
    lang = _normalize_lang(code.lang)
    keywords = _KEYWORDS.get(lang, BUILTIN_KEYWORDS)

    panel_left = 0.82
    panel_width = ctx.slide_width - 1.64
    panel_top = 1.5
    header_height = 0.34 if (code.lang or code.caption) else 0.0
    available_height = ctx.slide_height - 1.48 - 0.6 - panel_top
    body_height = 0.26 * len(lines) + 0.2
    panel_height = min(available_height, max(1.6, body_height + header_height + 0.2))

    add_box(
        ctx,
        "DSH_CODE_PANEL",
        panel_left,
        panel_top,
        panel_width,
        panel_height,
        fill=ctx.theme.code_background,
        line=ctx.theme.code_border,
        radius=False,
    )

    body_top = panel_top + header_height + 0.1 if header_height else panel_top + 0.1
    if header_height:
        add_text(
            ctx,
            "DSH_CODE_HEADER",
            "  ".join(part for part in (code.lang, code.caption) if part),
            panel_left + 0.13,
            panel_top + 0.05,
            panel_width - 0.26,
            header_height,
            size=10,
            text_color=ctx.theme.muted,
            font_name=ctx.theme.code_font,
            valign=MSO_ANCHOR.MIDDLE,
            margin=0,
        )
        add_box(
            ctx,
            "DSH_CODE_HEADER_RULE",
            panel_left + 0.13,
            panel_top + header_height,
            panel_width - 0.26,
            0.012,
            fill=ctx.theme.code_border,
        )

    body_panel_height = panel_height - (header_height + 0.2 if header_height else 0.2)
    shape = ctx.slide.shapes.add_textbox(
        Inches(panel_left + 0.13),
        Inches(body_top),
        Inches(panel_width - 0.26),
        Inches(max(0.4, body_panel_height)),
    )
    shape.name = "DSH_CODE_BODY"
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.auto_size = None
    frame.margin_left = frame.margin_right = Inches(0.12)
    frame.margin_top = frame.margin_bottom = Inches(0.08)

    color_map = {
        _TOKEN_TEXT: ctx.theme.code_text,
        _TOKEN_COMMENT: ctx.theme.code_comment,
        _TOKEN_STRING: ctx.theme.code_string,
        _TOKEN_KEYWORD: ctx.theme.code_keyword,
        _TOKEN_NUMBER: ctx.theme.code_number,
    }
    size = 13 if len(lines) <= 14 else 12 if len(lines) <= 18 else 11

    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.line_spacing = 1.12
        paragraph.space_after = Pt(0)
        paragraph.alignment = PP_ALIGN.LEFT
        if not line:
            run = paragraph.add_run()
            run.text = " "
            set_run_font(run, latin=ctx.theme.code_font, ea=ctx.theme.chinese_font)
            run.font.size = Pt(size)
            run.font.color.rgb = RGBColor.from_string(ctx.theme.code_text)
            continue
        for text, token_type in _tokenize_line(line, keywords):
            run = paragraph.add_run()
            run.text = text
            set_run_font(run, latin=ctx.theme.code_font, ea=ctx.theme.chinese_font)
            run.font.size = Pt(size)
            run.font.color.rgb = RGBColor.from_string(color_map[token_type])
