"""
extract_context.py -- Wrapper de _structural_parser.py.

Entree : --file <path> [--line N] [--window W]
Sortie : JSON stdout avec enclosing_block + snippet.

Le parsing structurel est delegue a _structural_parser.py (vendore de linting-diva-code).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _structural_parser import (  # noqa: E402
    parse_blocks, find_enclosing_block, extract_snippet, read_diva_file,
)


def extract(file_path: Path, line: int | None = None, window: int = 30) -> dict:
    lines = read_diva_file(file_path)
    total = len(lines)
    target = line if line is not None else min(total, max(1, total // 2))
    blocks = parse_blocks(lines)
    block = find_enclosing_block(blocks, target)
    start, end, snippet = extract_snippet(lines, target, window=window, block=block)
    return {
        "file": str(file_path),
        "total_lines": total,
        "line": target,
        "enclosing_block": (
            {"kind": block.kind, "name": block.name,
             "decl_line": block.decl_line, "end_line": block.end_line}
            if block else None
        ),
        "snippet_start": start,
        "snippet_end": end,
        "snippet": snippet,
    }


def _cli() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Extrait le contexte autour d'une ligne dans un fichier DIVA.")
    ap.add_argument("--file", required=True)
    ap.add_argument("--line", type=int)
    ap.add_argument("--window", type=int, default=30)
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Fichier introuvable : {path}", file=sys.stderr)
        return 2

    out = extract(path, line=args.line, window=args.window)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
