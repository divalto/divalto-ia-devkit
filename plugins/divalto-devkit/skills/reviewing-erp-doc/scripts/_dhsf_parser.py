#!/usr/bin/env python3
"""_dhsf_parser.py -- Mini-parseur de masque ecran Divalto (.dhsf).

**Parseur dedie relecture** : n'extrait que les liens zooms `f8=<code>` par champ,
ce qui suffit aux heuristiques E3 (zooms declares cote source) et E4 (anti-pattern Z16).

Le vrai dhsf_parser complet (manipulating-dhsf-screens/scripts/dhsf_parser.py) produit
un arbre structurel, overkill pour ce besoin. Implementation 50 lignes, deterministe.
"""
from __future__ import annotations

import re
from pathlib import Path


SEC_PAT = re.compile(r"^\[(/?\w+)\]")
KEY_VAL_PAT = re.compile(r"^(\w+)\s*=\s*(.*)")


def parse_dhsf_zooms(path: Path) -> list[dict]:
    """Parcourt un .dhsf et retourne la liste des zooms f8 declares par champ.

    Format cible : blocs `[champ]` avec lignes `nom=<nom>` et `f8=<code>` dans `[touches]`.
    Retourne : [{champ: "Pays", zoom: "9053", line: 42}, ...]
    """
    if not path.is_file():
        return []
    content = path.read_text(encoding="iso-8859-1", errors="replace")
    lines = content.splitlines()
    zooms: list[dict] = []
    current_champ: str | None = None
    current_line: int | None = None
    in_touches = False

    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        sec = SEC_PAT.match(line)
        if sec:
            tag = sec.group(1).lower()
            if tag == "champ":
                current_champ = None
                current_line = idx
                in_touches = False
            elif tag == "/champ":
                current_champ = None
                in_touches = False
            elif tag == "touches":
                in_touches = True
            elif tag == "/touches":
                in_touches = False
            continue
        kv = KEY_VAL_PAT.match(line)
        if not kv:
            continue
        key, value = kv.group(1).lower(), kv.group(2).strip()
        if key == "nom" and current_champ is None:
            current_champ = value
        elif key == "f8" and in_touches and current_champ:
            zooms.append({
                "champ": current_champ,
                "zoom": value,
                "line": current_line or idx,
            })
    return zooms
