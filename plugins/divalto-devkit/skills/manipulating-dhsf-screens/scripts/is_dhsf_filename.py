#!/usr/bin/env python3
"""Verifie qu'un nom de fichier respecte la convention masque Divalto.

Regle universelle observee dans le standard : un masque `.dhsf` a
**toujours `e` en position 3**.

Decomposition du nom :
- pos 1-2 = code domaine (gt, cc, a5, gg, co, rt, wm, pp, cv, ga, gr, ...)
- pos 3 = 'e' (invariant) -- "ecran"
- pos 4+ = type + identifiant (z<num>, m<X>, q<num>, e<X>, ...)

Usage :
    py is_dhsf_filename.py --filename gtez000_sql.dhsf
    py is_dhsf_filename.py --filename cceq701.dhsf

Sortie JSON :
    {
        "filename": "gtez000_sql.dhsf",
        "is_mask": true,
        "domain": "gt",
        "type": "z",
        "id": "000_sql",
        "is_surcharge": false
    }

Si le suffixe `u` est present avant `.dhsf` (ex: `gtez000_sqlu.dhsf`),
`is_surcharge` est `true`.

Exit codes :
    0 = nom valide
    1 = nom invalide (mais pas une erreur d'usage)
    2 = erreur d'usage
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def parse_mask_filename(filename: str) -> dict:
    """Decompose un nom de fichier masque selon la convention DIVA.

    Retourne un dict :
    - is_mask : True si pos 3 = 'e' et extension .dhsf
    - domain : code domaine (pos 1-2)
    - type : 1er caractere apres 'e' (z, m, q, e, ...)
    - id : reste du nom apres le type
    - is_surcharge : True si le stem se termine par 'u' (avant .dhsf)
    """
    base = os.path.basename(filename)
    stem, ext = os.path.splitext(base)

    result = {
        "filename": base,
        "is_mask": False,
        "domain": None,
        "type": None,
        "id": None,
        "is_surcharge": False,
        "reason": None,
    }

    if ext.lower() != ".dhsf":
        result["reason"] = f"extension '{ext}' attendue '.dhsf'"
        return result

    if len(stem) < 4:
        result["reason"] = f"nom trop court (< 4 chars hors extension) : '{stem}'"
        return result

    if stem[2].lower() != "e":
        result["reason"] = (
            f"position 3 = '{stem[2]}' (attendu 'e' invariant -- regle universelle masque)"
        )
        return result

    result["is_mask"] = True
    result["domain"] = stem[:2].lower()
    result["type"] = stem[3].lower()
    result["id"] = stem[4:]
    result["is_surcharge"] = stem.endswith("u")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verifie qu'un nom de fichier est un masque Divalto valide (regle: pos 3 = 'e' invariant)"
    )
    parser.add_argument("--filename", required=True, help="Nom de fichier a verifier (ex: gtez000_sql.dhsf)")
    args = parser.parse_args()

    result = parse_mask_filename(args.filename)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0 if result["is_mask"] else 1)


if __name__ == "__main__":
    main()
