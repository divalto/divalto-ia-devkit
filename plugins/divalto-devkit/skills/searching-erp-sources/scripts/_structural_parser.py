"""
_structural_parser.py -- Extraction structurelle d'un fichier source DIVA (.dhsp / .dhsq).

Detecte les blocs Procedure/EndP et Function/EndF, localise le bloc englobant
d'une ligne donnee et extrait un snippet de contexte.

Pas de validation : extraction pure destinee aux skills d'analyse (searching-erp-sources
en premier consommateur). Les regex sont alignees sur celles de lint_diva.py pour
garantir la coherence de detection entre les deux outils.

Source canonique : .claude/skills/linting-diva-code/scripts/_structural_parser.py
Copies vendorees : .claude/skills/searching-erp-sources/scripts/_structural_parser.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Prefixes de visibilite optionnels precedent Procedure/Function en DIVA
_VIS_PREFIX = r'(?:Public\s+|Private\s+)?'
PROC_DECL_PAT = re.compile(rf'^\s*{_VIS_PREFIX}Procedure\s+(\w+)', re.IGNORECASE)
FUNC_DECL_PAT = re.compile(rf'^\s*{_VIS_PREFIX}Function\s+(\w+)', re.IGNORECASE)
BEGINP_PAT = re.compile(r'^\s*BeginP\b', re.IGNORECASE)
BEGINF_PAT = re.compile(r'^\s*BeginF\b', re.IGNORECASE)
ENDP_PAT = re.compile(r'^\s*EndP\b', re.IGNORECASE)
ENDF_PAT = re.compile(r'^\s*EndF\b', re.IGNORECASE)
# Commentaires DIVA : // (C-style) ou ; (semi-colon en debut de ligne)
COMMENT_LINE_PAT = re.compile(r'^\s*(//|;)')


@dataclass
class Block:
    """Bloc structurel -- procedure ou fonction."""
    kind: str  # "procedure" | "function"
    name: str
    decl_line: int  # ligne de Procedure X / Function X (1-indexed)
    begin_line: int | None  # ligne de BeginP / BeginF (None si pas trouve)
    end_line: int | None  # ligne de EndP / EndF (None si pas trouve)


def parse_blocks(lines: list[str]) -> list[Block]:
    """Parcourt les lignes et retourne la liste des blocs procedure/fonction.

    Blocs mal formes (Procedure sans EndP, etc.) sont retournes avec end_line=None
    pour signaler le probleme au consommateur sans planter.
    """
    blocks: list[Block] = []
    current: Block | None = None
    current_end_pat: re.Pattern | None = None
    current_begin_pat: re.Pattern | None = None

    for i, line in enumerate(lines, start=1):
        if COMMENT_LINE_PAT.match(line):
            continue

        if current is None:
            m = PROC_DECL_PAT.match(line)
            if m:
                current = Block(kind="procedure", name=m.group(1), decl_line=i,
                                begin_line=None, end_line=None)
                current_begin_pat = BEGINP_PAT
                current_end_pat = ENDP_PAT
                continue
            m = FUNC_DECL_PAT.match(line)
            if m:
                current = Block(kind="function", name=m.group(1), decl_line=i,
                                begin_line=None, end_line=None)
                current_begin_pat = BEGINF_PAT
                current_end_pat = ENDF_PAT
                continue
        else:
            # Dans un bloc actif : chercher BeginX puis EndX
            if current.begin_line is None and current_begin_pat.match(line):
                current.begin_line = i
                continue
            if current_end_pat.match(line):
                current.end_line = i
                blocks.append(current)
                current = None
                current_end_pat = None
                current_begin_pat = None
                continue
            # Si on rencontre un nouveau Procedure/Function avant la fin du bloc courant :
            # bloc malforme, on le ferme sans end_line et on ouvre le nouveau.
            m_proc = PROC_DECL_PAT.match(line)
            m_func = FUNC_DECL_PAT.match(line)
            if m_proc or m_func:
                blocks.append(current)
                if m_proc:
                    current = Block(kind="procedure", name=m_proc.group(1), decl_line=i,
                                    begin_line=None, end_line=None)
                    current_begin_pat = BEGINP_PAT
                    current_end_pat = ENDP_PAT
                else:
                    current = Block(kind="function", name=m_func.group(1), decl_line=i,
                                    begin_line=None, end_line=None)
                    current_begin_pat = BEGINF_PAT
                    current_end_pat = ENDF_PAT

    if current is not None:
        blocks.append(current)

    return blocks


def find_enclosing_block(blocks: list[Block], line_no: int) -> Block | None:
    """Retourne le bloc qui englobe line_no (1-indexed), ou None.

    Un bloc englobe line_no si decl_line <= line_no <= end_line (ou derniere ligne
    connue si end_line is None).
    """
    for b in blocks:
        start = b.decl_line
        end = b.end_line if b.end_line is not None else sys.maxsize
        if start <= line_no <= end:
            return b
    return None


def extract_snippet(lines: list[str], line_no: int, window: int = 30,
                    block: Block | None = None) -> tuple[int, int, str]:
    """Extrait un snippet autour de line_no.

    Si block est fourni et que sa taille est <= window, retourne le bloc entier.
    Sinon, retourne une fenetre centree sur line_no, bornee au fichier.

    Retourne (start_line_1_indexed, end_line_1_indexed, snippet_text).
    """
    total = len(lines)
    if block is not None and block.end_line is not None:
        block_size = block.end_line - block.decl_line + 1
        if block_size <= window:
            start = block.decl_line
            end = block.end_line
            snippet = "".join(lines[start - 1:end])
            return (start, end, snippet)

    half = window // 2
    start = max(1, line_no - half)
    end = min(total, line_no + half)
    snippet = "".join(lines[start - 1:end])
    return (start, end, snippet)


def read_diva_file(path: Path) -> list[str]:
    """Lit un fichier DIVA en ISO-8859-1 (encodage standard). Preserve les fins de ligne."""
    with open(path, "r", encoding="iso-8859-1", newline="") as f:
        return f.readlines()


def _cli() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Parse structurel d'un fichier DIVA (.dhsp/.dhsq). Sortie JSON.")
    parser.add_argument("--file", required=True, help="Chemin du fichier source")
    parser.add_argument("--line", type=int, default=None,
                        help="Si fourni, retourne le bloc englobant + snippet")
    parser.add_argument("--window", type=int, default=30,
                        help="Fenetre du snippet (defaut 30)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Fichier introuvable : {path}", file=sys.stderr)
        return 2

    lines = read_diva_file(path)
    blocks = parse_blocks(lines)

    output: dict = {
        "file": str(path),
        "total_lines": len(lines),
        "blocks": [asdict(b) for b in blocks],
    }

    if args.line is not None:
        block = find_enclosing_block(blocks, args.line)
        start, end, snippet = extract_snippet(lines, args.line, args.window, block)
        output["query"] = {
            "line": args.line,
            "enclosing_block": asdict(block) if block else None,
            "snippet_start": start,
            "snippet_end": end,
            "snippet": snippet,
        }

    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
