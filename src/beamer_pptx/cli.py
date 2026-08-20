from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build
from .errors import BeamerPptxError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="beamer-pptx", description="Generate an editable Beamer-style PPTX from YAML.")
    result.add_argument("input", type=Path, help="YAML deck description")
    result.add_argument("-t", "--template", type=Path, help="optional editable PPTX template")
    result.add_argument("-o", "--output", type=Path, required=True, help="output PPTX path")
    result.add_argument("--asset-root", type=Path, help="base directory for relative image paths")
    strict_group = result.add_mutually_exclusive_group()
    strict_group.add_argument("--strict", dest="strict", action="store_true", default=True, help="fail on invalid assets (default)")
    strict_group.add_argument("--no-strict", dest="strict", action="store_false", help="warn and insert placeholders for invalid assets")
    result.add_argument("--verbose", action="store_true", help="print warning details")
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
    except BeamerPptxError as exc:
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

