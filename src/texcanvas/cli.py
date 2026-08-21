from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build
from .errors import TexCanvasError
from .scaffold import init_project
from .sync import pull


def _build_parser() -> tuple[argparse.ArgumentParser, argparse._SubParsersAction]:
    root = argparse.ArgumentParser(
        prog="texcanvas",
        description="将 YAML 描述文件生成为可编辑的 Beamer 风格 PPTX（可在 WPS/PowerPoint 中继续微调）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  texcanvas init my-talk                 # 在 ./my-talk 创建脚手架\n"
            "  texcanvas build deck.yml -o out.pptx    # 生成 pptx\n"
            "  python -m texcanvas build deck.yml -o out.pptx\n"
            "\n"
            "更多版式与字段说明见 AGENTS.md / README.md。"
        ),
    )
    sub = root.add_subparsers(dest="command", required=True, metavar="<command>")
    return root, sub


def _add_build_parser(sub: argparse._SubParsersAction) -> None:
    build_p = sub.add_parser(
        "build",
        help="从 YAML 生成 PPTX",
        description="从 YAML deck 描述文件生成可编辑的 .pptx。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    build_p.add_argument("input", type=Path, help="YAML deck 描述文件路径")
    build_p.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="输出 .pptx 文件路径（父目录不存在时会自动创建）",
    )
    build_p.add_argument(
        "-t",
        "--template",
        type=Path,
        help="可选的可编辑 PPTX 模板路径；保留母版/主题，模板中的示例页会被清空",
    )
    build_p.add_argument(
        "--asset-root",
        type=Path,
        help="相对图片路径的基准目录；默认为 YAML 文件所在目录",
    )
    strict_group = build_p.add_mutually_exclusive_group()
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
    build_p.add_argument(
        "--verbose",
        action="store_true",
        help="打印每条 warning 的详细信息",
    )
    build_p.add_argument(
        "--overrides",
        type=Path,
        help="可选的人类 PPTX 微调覆盖文件（由 sync pull 生成）",
    )


def _add_init_parser(sub: argparse._SubParsersAction) -> None:
    init_p = sub.add_parser(
        "init",
        help="在当前目录创建一个 deck 脚手架目录",
        description="在当前目录创建一个 deck 脚手架目录，包含 AGENTS.md、deck.yml、assets/、build.sh 和 output/。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    init_p.add_argument("name", help="脚手架目录名（在当前目录下创建）")
    init_p.add_argument(
        "-d",
        "--dir",
        type=Path,
        default=Path.cwd(),
        help="父目录（默认为当前工作目录）",
    )


def _add_sync_parser(sub: argparse._SubParsersAction) -> None:
    sync_p = sub.add_parser("sync", help="在 YAML 与人工编辑后的 PPTX 之间同步覆盖层")
    sync_sub = sync_p.add_subparsers(dest="sync_command", required=True, metavar="<sync-command>")
    pull_p = sync_sub.add_parser("pull", help="从人工编辑后的 PPTX 提取 overrides.yml")
    pull_p.add_argument("input", type=Path, help="人工编辑后的 PPTX 文件")
    pull_p.add_argument("-o", "--output", type=Path, required=True, help="覆盖层 YAML 输出路径")
    pull_p.add_argument(
        "--asset-dir",
        type=Path,
        help="提取新增图片的目录；默认为 <overrides-name>-assets",
    )


def parser() -> argparse.ArgumentParser:
    root, sub = _build_parser()
    _add_build_parser(sub)
    _add_init_parser(sub)
    _add_sync_parser(sub)
    return root


def _run_build(args: argparse.Namespace) -> int:
    try:
        report = build(
            input=args.input,
            output=args.output,
            template=args.template,
            strict=args.strict,
            asset_root=args.asset_root,
            overrides=args.overrides,
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


def _run_init(args: argparse.Namespace) -> int:
    try:
        project = init_project(args.dir, args.name)
    except TexCanvasError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Created {project}")
    print("Next steps:")
    print(f"  cd {project.name}")
    print("  bash build.sh        # 生成 output/deck.pptx")
    return 0


def _run_sync_pull(args: argparse.Namespace) -> int:
    try:
        report = pull(args.input, args.output, asset_dir=args.asset_dir)
    except TexCanvasError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {report.output}")
    print(f"Slides: {report.slide_count}")
    print(f"Shapes: {report.shape_count}")
    print(f"Extracted images: {report.extracted_image_count}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "build":
        return _run_build(args)
    if args.command == "init":
        return _run_init(args)
    if args.command == "sync" and args.sync_command == "pull":
        return _run_sync_pull(args)
    # argparse enforces required subcommand; unreachable.
    return 2
