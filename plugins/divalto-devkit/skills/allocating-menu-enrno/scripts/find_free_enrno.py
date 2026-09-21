#!/usr/bin/env python3
"""Trouve un EnrNo libre pour le menu, dans l'UNION du standard et de son overlay.

Plages :
  - `standard` : EnrNo < 100000 (zone reservee ERP standard -- allocation deconseillee)
  - `custom`   : EnrNo >= 100000 (zone reservee customisations utilisateur, defaut recommande)

**Le used-set est une UNION** : `g3f.dhfi` (standard) **+ `g3fu.dhfi` (overlay
specifique)**. Meme mecanisme que `a5f`/`a5fu` pour les zooms.

Ignorer l'overlay est le defaut que ce script avait : il ne scannait que `g3f`, et
pouvait donc rendre un EnrNo **deja pris dans l'overlay du partenaire** -- exactement la
collision qu'il existe pour prevenir (#228). Le script voisin
`allocating-zoom-numbers/scripts/find_free_zoom.py` faisait deja l'union ; le
menu ne l'avait pas.

Filtre `Ce=2` obligatoire sur chaque fichier -- sinon l'enreg M0 au Ce=0 est decode avec
des offsets errones et peut produire un EnrNo aberrant.

> **Doublons g3f / g3fu = normaux** : surcharger une entree de menu standard cree une
> entree de meme EnrNo dans `g3fu`, **prioritaire**. Le used-set etant une union, le
> doublon se fond en une seule valeur ; ce n'est pas une collision.

Usage :
    py find_free_enrno.py --file "<module>/fichier/g3f.dhfi" --range custom
    py find_free_enrno.py --file "<g3f.dhfi>" --g3fu "<specifs>/g3fu.dhfi" --range custom
    py find_free_enrno.py --file "<g3f.dhfi>" --range custom --count 3

Sortie JSON :
    {
      "free": [100001, 100002, 100003],
      "range": "custom",
      "range_bounds": [100000, 999999],
      "sources": {"g3f": {...}, "g3fu": {...}, "union_used_in_range": 12, ...},
      "avertissements": ["..."]
    }

Exit codes : 0 = au moins un libre, 1 = aucun libre / aucune M2 lue, 2 = erreur.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


# Plages de semantique EnrNo G3F (RETEX, `[A VERIFIER]` empiriquement)
RANGE_BOUNDS = {
    "standard": (1, 99999),       # Zone reservee ERP standard, deconseillee en allocation custom
    "custom":   (100000, 999999), # Zone customisations utilisateur (defaut recommande)
}

VENDORED_STRUCTURE = Path(__file__).resolve().parent / "structure_xmenuf_m2.json"


def scan_g3f_enrnos(dhfi_path, read_isam_script):
    """Scan complet de g3f.dhfi cle A avec structure M2 vendored.

    Returns (list_of_records_parsed, error_message_or_None).
    Utilise filter Ce=2 pour ignorer l'enreg M0 (Ce=0) -- cf piege RETEX.
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
        description="Trouve un EnrNo libre dans g3f.dhfi (plages standard / custom)",
    )
    parser.add_argument("--file", required=True,
                        help="Chemin du g3f.dhfi STANDARD du module ERP (lu, jamais ecrit)")
    parser.add_argument("--g3fu", default=None,
                        help="Chemin du g3fu.dhfi (overlay specifique du partenaire, meme "
                             "structure M2). **A fournir des qu'il existe** : sans lui le "
                             "used-set est incomplet et un EnrNo deja pris dans l'overlay "
                             "peut etre propose comme libre. Les doublons g3f/g3fu sont "
                             "normaux (surcharge) et se fondent dans l'union.")
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

    # Used-set = UNION du standard et de l'overlay. Le standard est obligatoire ;
    # l'overlay est optionnel MAIS son absence est signalee, car elle rend le
    # resultat incomplet sans que rien ne le dise (#228).
    sources = {}
    avertissements = []
    union = set()

    for etiquette, chemin, obligatoire in (("g3f", args.file, True),
                                           ("g3fu", args.g3fu, False)):
        if not chemin:
            avertissements.append(
                "overlay g3fu NON fourni : le used-set ne couvre que le standard. Si le "
                "partenaire a un g3fu.dhfi, un EnrNo deja pris dedans peut etre propose "
                "ici comme libre -- passer --g3fu <chemin>.")
            sources[etiquette] = None
            continue
        records, err = scan_g3f_enrnos(chemin, read_isam_script)
        if err:
            if obligatoire:
                print(f"Erreur : {err}", file=sys.stderr)
                sys.exit(2)
            # Un overlay illisible ne doit pas passer pour un overlay vide.
            avertissements.append(f"overlay g3fu illisible ({err}) : used-set incomplet.")
            sources[etiquette] = {"erreur": err}
            continue
        dans_plage = extract_enrnos(records or [], lo, hi)
        union |= dans_plage
        sources[etiquette] = {
            "fichier": chemin,
            "m2_records": len(records or []),
            "enrno_parsed": sum(1 for r in (records or [])
                                if (r.get("EnrNo") or "").strip().isdigit()),
            "used_in_range": len(dans_plage),
            "max_used_in_range": max(dans_plage) if dans_plage else None,
        }

    free = find_free(union, lo, hi, count=args.count)

    result = {
        "file": args.file,
        "range": args.range,
        "range_bounds": [lo, hi],
        "free": free,
        "sources": sources,
        "union_used_in_range": len(union),
        "max_used_in_range": max(union) if union else None,
        "avertissements": avertissements,
        "note": "Hypothese plages standard < 100000 / custom >= 100000 [A VERIFIER -- retour terrain non reproduit]. "
                "Le used-set est l'UNION g3f + g3fu ; les doublons entre les deux sont normaux "
                "(surcharge) et ne sont pas des collisions.",
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0 if free else 1)


if __name__ == "__main__":
    main()
