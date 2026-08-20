from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build
from .errors import TexCanvasError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="texcanvas",
        description="将 YAML 描述文件生成为可编辑的 Beamer 风格 PPTX（可在 WPS/PowerPoint 中继续微调）。",
        epilog=(
            "示例:\n"
            "  texcanvas examples/demo.yml -o output/demo.pptx --asset-root examples\n"
            "  texcanvas deck.yml -t templates/beamer-academic.pptx -o out.pptx --no-strict --verbose\n"
            "  python -m texcanvas deck.yml -o out.pptx\n"
            "\n"
            "更多版式与字段说明见 README.md 的「支持的版式」章节。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    result.add_argument("input", type=Path, help="YAML deck 描述文件路径")
    result.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="输出 .pptx 文件路径（父目录不存在时会自动创建）",
    )
    result.add_argument(
        "-t",
        "--template",
        type=Path,
        help="可选的可编辑 PPTX 模板路径；保留母版/主题，模板中的示例页会被清空",
    )
    result.add_argument(
        "--asset-root",
        type=Path,
        help="相对图片路径的基准目录；默认为 YAML 文件所在目录",
    )
    strict_group = result.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        default=True,
        help="严格模式（默认）：图片缺失、损坏或格式不支持时立即失败",
    )
    strict_group.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="宽松模式：记录 warning 并在页面放入可编辑占位框后继续生成",
    )
    result.add_argument(
        "--verbose",
        action="store_true",
        help="打印每条 warning 的详细信息",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = build(
            input=args.input,
            output=args.output,
            template=args.template,
            strict=args.strict,
            asset_root=args.asset_root,
        )
    except TexCanvasError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Built {report.output}")
    print(f"Slides: {report.slide_count}")
    print(f"Sections: {report.section_count}")
    print(f"Warnings: {len(report.warnings)}")
    if args.verbose:
        for warning in report.warnings:
            print(f"- {warning}")
    return 0

