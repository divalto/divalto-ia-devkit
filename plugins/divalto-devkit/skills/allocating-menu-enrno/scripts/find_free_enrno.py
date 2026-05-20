#!/usr/bin/env python3
"""Trouve un EnrNo libre dans g3f.dhfi pour une plage donnee (standard ou custom).

Plages :
  - `standard` : EnrNo < 100000 (zone reservee ERP standard -- allocation deconseillee)
  - `custom`   : EnrNo >= 100000 (zone reservee customisations utilisateur, defaut recommande)

La logique est simple : scan complet de la cle A de g3f.dhfi avec structure M2 (filter Ce=2
obligatoire -- sinon l'enreg M0 au Ce=0 est decode avec des offsets errones et peut produire
un EnrNo aberrant, cf RETEX R-006), collecte des EnrNo presents dans la plage, retour max+1.

Usage :
    py find_free_enrno.py --file "<module>/fichier/g3f.dhfi" --range custom
    py find_free_enrno.py --file "<g3f.dhfi>" --range standard
    py find_free_enrno.py --file "<g3f.dhfi>" --range custom --count 3

Sortie JSON :
    {
      "free": [100001, 100002, 100003],
      "range": "custom",
      "range_bounds": [100000, 999999],
      "sources": {"total_records": 1368, "m2_records": 1367, "m0_records": 1, "max_used_in_range": 100000},
      "collisions": []
    }

Exit codes : 0 = au moins un libre, 1 = aucun libre / aucune M2 lue, 2 = erreur.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


# Plages de semantique EnrNo G3F (RETEX R-005, `[A VERIFIER]` empiriquement)
RANGE_BOUNDS = {
    "standard": (1, 99999),       # Zone reservee ERP standard, deconseillee en allocation custom
    "custom":   (100000, 999999), # Zone customisations utilisateur (defaut recommande)
}

VENDORED_STRUCTURE = Path(__file__).resolve().parent / "structure_xmenuf_m2.json"


def scan_g3f_enrnos(dhfi_path, read_isam_script):
    """Scan complet de g3f.dhfi cle A avec structure M2 vendored.

    Returns (list_of_records_parsed, error_message_or_None).
    Utilise filter Ce=2 pour ignorer l'enreg M0 (Ce=0) -- cf piege RETEX R-006.
    """
    if not os.path.isfile(dhfi_path):
        return None, f"Fichier introuvable : {dhfi_path}"
    if not os.path.isfile(read_isam_script):
        return None, f"read_isam.py introuvable : {read_isam_script}"
    if not VENDORED_STRUCTURE.is_file():
        return None, f"Structure vendored introuvable : {VENDORED_STRUCTURE}"

    try:
        r = subprocess.run(
            ["py", read_isam_script,
             "--file", dhfi_path,
             "--structure", str(VENDORED_STRUCTURE),
             "--key", "A",
             "--filter", "Ce=2",
             "--max", "500000",
             "--fields", "Ce,EnrNo,Lib,Reg,Ordre"],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
    except Exception as exc:  # noqa: BLE001
        return None, f"Echec subprocess read_isam.py : {exc}"

    if r.returncode not in (0, 1):
        stderr_preview = (r.stderr or "")[:500]
        return None, f"read_isam.py exit={r.returncode}, stderr={stderr_preview}"

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as exc:
        return None, f"JSON invalide en sortie read_isam.py : {exc}"

    return data.get("records", []), None


def extract_enrnos(records, lo, hi):
    """Pour une liste de records M2, retourne set des EnrNo entiers dans [lo, hi]."""
    used = set()
    for rec in records:
        val = (rec.get("EnrNo") or "").strip()
        if not val.isdigit():
            continue
        num = int(val)
        if lo <= num <= hi:
            used.add(num)
    return used


def find_free(used_set, lo, hi, count=1):
    """Trouve les `count` premiers numeros libres dans [lo, hi], ordre croissant.

    Scan lineaire depuis lo (permet de remplir les trous en tete de plage). Sur
    plage custom (100000..999999) typiquement vide en X.13 standard, retourne
    directement 100000+ sans saut vers max_used+1.
    """
    free = []
    candidate = lo
    while candidate <= hi and len(free) < count:
        if candidate not in used_set:
            free.append(candidate)
        candidate += 1
    return free


def main():
    parser = argparse.ArgumentParser(
        description="Trouve un EnrNo libre dans g3f.dhfi (plages standard / custom, RETEX R-005)",
    )
    parser.add_argument("--file", required=True, help="Chemin du g3f.dhfi cible (module ERP)")
    parser.add_argument("--range", required=True, choices=list(RANGE_BOUNDS.keys()),
                        help="Plage d'allocation : 'standard' (<100000) ou 'custom' (>=100000)")
    parser.add_argument("--count", type=int, default=1,
                        help="Nombre d'EnrNo libres a retourner (defaut 1)")
    parser.add_argument("--read-isam-script", default=None,
                        help="Chemin de reading-isam-files/scripts/read_isam.py "
                             "(defaut : ../../reading-isam-files/scripts/read_isam.py)")
    args = parser.parse_args()

    # Resoudre chemin read_isam.py (defaut relatif)
    if args.read_isam_script:
        read_isam_script = args.read_isam_script
    else:
        read_isam_script = str(
            Path(__file__).resolve().parent.parent.parent
            / "reading-isam-files" / "scripts" / "read_isam.py"
        )

    lo, hi = RANGE_BOUNDS[args.range]

    records, err = scan_g3f_enrnos(args.file, read_isam_script)
    if err:
        print(f"Erreur : {err}", file=sys.stderr)
        sys.exit(2)

    used_in_range = extract_enrnos(records or [], lo, hi)
    free = find_free(used_in_range, lo, hi, count=args.count)

    # Diagnostics : tous les EnrNo (toutes plages) pour le rapport
    all_enrnos_parsed = 0
    for rec in records or []:
        val = (rec.get("EnrNo") or "").strip()
        if val.isdigit():
            all_enrnos_parsed += 1

    result = {
        "file": args.file,
        "range": args.range,
        "range_bounds": [lo, hi],
        "free": free,
        "sources": {
            "m2_records": len(records or []),
            "enrno_parsed": all_enrnos_parsed,
            "used_in_range": len(used_in_range),
            "max_used_in_range": max(used_in_range) if used_in_range else None,
        },
        "note": "Hypothese plages standard < 100000 / custom >= 100000 [A VERIFIER] RETEX R-005 2026-04-23",
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0 if free else 1)


if __name__ == "__main__":
    main()
