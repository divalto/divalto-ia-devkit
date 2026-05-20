#!/usr/bin/env python3
"""Retire des entrees temporaires de [fichiers] d'un .dhps.

Cas d'usage : apres compilation reussie d'un sous-projet, nettoyer les fichiers
de [communs] qui avaient ete pousses temporairement dans [fichiers] pour
contourner le piege "xwin7 -sousproject ne recompile pas les .dhsd en
[communs] du .dhpt parent".

Usage :
    py cleanup_communs_from_subproject.py --path "gt_zoom race chien.dhps" \\
        --remove gtfdd.dhsd --remove gtpmficsql.dhsp

Comportement :
- Lit le .dhps en ISO-8859-1
- Localise la section [fichiers]
- Supprime les lignes `fic="<X>"," "` dont X match une valeur de --remove
  (match case-insensitive, sur le basename)
- Cree un backup .bak avant ecriture
- Reecrit en ISO-8859-1 + CRLF

Sortie JSON : {path, removed[], kept[], lines_before, lines_after}
Exit codes : 0 = succes (au moins 1 ligne retiree ou rien a retirer),
             1 = erreur utilisateur, 2 = erreur interne
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FIC_LINE_RE = re.compile(r'^\s*fic\s*=\s*"([^"]+)"', re.IGNORECASE)
SECTION_RE = re.compile(r'^\s*\[([a-zA-Z_]+)\]\s*$')


def cleanup_subproject(path: Path, to_remove: list[str]) -> dict:
    raw = path.read_bytes()
    try:
        text = raw.decode("iso-8859-1")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"Decodage ISO-8859-1 echoue : {exc}")

    lines = text.splitlines()
    to_remove_lower = {x.lower() for x in to_remove}

    in_fichiers = False
    new_lines: list[str] = []
    removed: list[str] = []
    kept: list[str] = []

    for line in lines:
        section_match = SECTION_RE.match(line)
        if section_match:
            in_fichiers = section_match.group(1).lower() == "fichiers"
            new_lines.append(line)
            continue

        if in_fichiers:
            fic_match = FIC_LINE_RE.match(line)
            if fic_match:
                fic_value = fic_match.group(1)
                basename = fic_value.split("\\")[-1].split("/")[-1].lower()
                if basename in to_remove_lower:
                    removed.append(fic_value)
                    continue
                kept.append(fic_value)

        new_lines.append(line)

    if removed:
        # Backup avant ecriture
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_bytes(raw)
        # Reecrire en ISO-8859-1 + CRLF
        new_text = "\r\n".join(new_lines) + "\r\n"
        path.write_bytes(new_text.encode("iso-8859-1"))

    return {
        "path": str(path),
        "removed": removed,
        "kept": kept,
        "lines_before": len(lines),
        "lines_after": len(new_lines),
        "backup": str(backup) if removed else None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--path", required=True, help="Chemin du .dhps a nettoyer")
    ap.add_argument(
        "--remove",
        action="append",
        default=[],
        required=True,
        metavar="FICHIER",
        help="Fichier (basename) a retirer de [fichiers], repetable. "
             "Ex : --remove gtfdd.dhsd --remove gtpmficsql.dhsp",
    )
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Fichier introuvable : {path}", file=sys.stderr)
        sys.exit(1)
    if not path.suffix.lower() == ".dhps":
        print(f"Avertissement : le fichier n'a pas l'extension .dhps : {path}",
              file=sys.stderr)

    try:
        report = cleanup_subproject(path, args.remove)
    except RuntimeError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(2)

    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
