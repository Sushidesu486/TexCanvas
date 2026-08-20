"""`texcanvas init` scaffold generator.

Creates a self-contained deck project in the current directory (or a named
subdirectory) with:

    <name>/
      AGENTS.md        condensed usage guide for agents
      deck.yml         minimal build-green deck (title + content)
      assets/          drop image assets here (empty)
      build.sh         one-shot wrapper that calls the installed texcanvas
      output/          build artifact target (kept empty via .gitkeep)
      .gitignore       ignores output/*.pptx

The wrapper resolves the packaged template (``texcanvas init`` ships
``beamer-academic.pptx`` inside the wheel) and passes it as ``-t`` so the
generated deck immediately has the right master/background.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from .errors import InputError

_AGENTS_MD = """\
# AGENTS.md (texcanvas 脚手架)

本目录是一个 texcanvas deck 项目。完整文档见 https://github.com/Sushidesu486/TexCanvas 。

## 快速命令

```bash
bash build.sh                 # 生成 output/deck.pptx
texcanvas deck.yml -o output/deck.pptx -t <template> --asset-root . --verbose
```

## YAML 结构

```yaml
metadata: {title, subtitle?, author?, institute?, date?, short_title?}
aspect: "16:9"
sections:
  - id: <slug>
    title: ...
    short_title: ...
    slides: [{kind: ...}]
```

## 11 种 slide kind

title / section_divider / content / two_columns / image / code / table /
equation / block / conclusion / references

每个 kind 的必填字段见仓库根 AGENTS.md 第 3 节。最易踩坑：

- two_columns 必须同时提供非空 left 和 right
- image 仅支持 PNG/JPEG，路径相对 --asset-root（默认 deck.yml 所在目录）
- code.lang 支持 python/c/cpp/java/javascript/rust/go
- equation 是最小化 LaTeX（\\frac、^{}、_{}、符号命令），不调用 LaTeX 引擎

## 常见错误

| 错误 | 处理 |
|------|------|
| `kind: unsupported value 'x'` | kind 写错，用 11 种之一 |
| `image.path: image not found` | 修路径，或加 --no-strict 放占位框 |
| `image.path: unsupported image format .svg` | 转 PNG/JPEG |
| `Warnings: N` + verbose 明细 | 超 bullets>8 / code>18 行 / table>10 行阈值，拆 slide |
"""

_DECK_YML = """\
metadata:
  title: 我的演示文稿
  subtitle: A Beamer-style editable presentation
  author: 作者
  institute: 单位
  date: ""

aspect: "16:9"

sections:
  - id: intro
    title: 引言
    short_title: Intro
    slides:
      - kind: title
        title: 我的演示文稿
        subtitle: A Beamer-style editable presentation

      - kind: section_divider
        title: 引言
        subtitle: Background and goal

      - kind: content
        title: 概述
        body: 在这里写正文。
        bullets:
          - 第一个要点
          - 第二个要点
"""

_BUILD_SH = """\
#!/usr/bin/env bash
# Build the deck into output/deck.pptx using the packaged template.
set -euo pipefail
cd "$(dirname "$0")"

# Locate the texcanvas that owns the `texcanvas` command on PATH, then resolve
# the template shipped inside that package. This works whether texcanvas was
# installed via pipx, pip, or an activated venv.
TEXCANVAS_BIN="$(command -v texcanvas || true)"
if [ -z "$TEXCANVAS_BIN" ]; then
  echo "Error: 'texcanvas' command not found on PATH." >&2
  exit 127
fi
# Follow symlinks to the real console script, whose sibling python can import texcanvas.
REAL="$(readlink -f "$TEXCANVAS_BIN" 2>/dev/null || python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$TEXCANVAS_BIN")"
PYTHON_BIN="$(dirname "$REAL")/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN=python3
TEMPLATE=$("$PYTHON_BIN" -c 'import texcanvas, pathlib; print(pathlib.Path(texcanvas.__file__).parent / "templates" / "beamer-academic.pptx")')

texcanvas build deck.yml \\
  -t "$TEMPLATE" \\
  -o output/deck.pptx \\
  --asset-root . \\
  --verbose
"""

_GITIGNORE = """\
output/*.pptx
!output/.gitkeep
.DS_Store
__pycache__/
"""

_GITKEEP = ""


def _bundled_template_path() -> Path:
    try:
        with resources.as_file(resources.files("texcanvas").joinpath("templates/beamer-academic.pptx")) as resolved:
            return Path(resolved)
    except (ModuleNotFoundError, FileNotFoundError, AttributeError) as exc:
        raise InputError(f"bundled template not found; is texcanvas installed correctly? {exc}") from exc


def init_project(target: Path, name: str) -> Path:
    project = (target / name).resolve()
    if project.exists():
        raise InputError(f"init: destination already exists: {project}")
    project.mkdir(parents=True)
    (project / "assets").mkdir()
    (project / "output").mkdir()
    (project / "AGENTS.md").write_text(_AGENTS_MD, encoding="utf-8")
    (project / "deck.yml").write_text(_DECK_YML, encoding="utf-8")
    build_sh = project / "build.sh"
    build_sh.write_text(_BUILD_SH, encoding="utf-8")
    build_sh.chmod(0o755)
    (project / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")
    (project / "output" / ".gitkeep").write_text(_GITKEEP, encoding="utf-8")
    return project


def bundled_template_path() -> Path:
    """Public accessor: where the packaged template lives on disk."""
    return _bundled_template_path()
