#!/usr/bin/env python3
"""Genere un fichier .dhps (sous-projet Divalto) au format INI.

Le fichier genere est ecrit en ISO-8859-1 + CRLF (format natif Divalto).

Deux modes :
- **Standard** (par defaut) : en-tete `xwin-sprojet 2.0`
- **Surcharge** : en-tete `xwin-s-sprojet 2.0` (xwin7 exige cette variante
  pour une .dhps qui surcharge un sous-projet du standard livre).

Mode surcharge declenche par :
- Flag explicite `--surcharge` (prioritaire)
- Auto-detection via `--parent-dhpt` : si le .dhpt parent a l'en-tete
  `xwin-s-projet`, on bascule en mode surcharge

Usage :
    py create_subproject.py --stdin < params.json
    py create_subproject.py --stdin --output mon_sous_projet.dhps < params.json
    py create_subproject.py --stdin --surcharge --output gt_zoom_articleu.dhps < params.json
    py create_subproject.py --stdin --parent-dhpt projet_surcharge.dhpt --output gt_zoom_articleu.dhps < params.json

Entree JSON :
    {
        "name": "gt_zoom article",
        "util": "SC",
        "communs": ["gt_base", "gt_dictionnaires", "gt_sql"],
        "fichiers": ["gtez099_sql.dhsf", "gtpp099.dhsp", "gtpz099.dhsp"],
        "includes": ["a5pcbaslic.dhsp", "a5tcchk000.dhsp", "gtpc000.dhsp"],
        "autres": []
    }

Sortie : contenu .dhps complet (texte ou fichier).

Exit codes :
    0 = succes
    1 = erreur utilisateur
    2 = erreur interne
"""

import argparse
import json
import sys
from datetime import datetime


def generate_timestamp():
    """Genere un horodatage au format Divalto : YYYYMMDDHHMMSSmmm099."""
    now = datetime.now()
    # Format : 14 chiffres datetime + 3 chiffres ms + "099"
    return now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}" + "099"


def validate_params(params):
    """Valide les parametres d'entree. Retourne une liste d'erreurs."""
    errors = []

    if not params.get("name"):
        errors.append("'name' est obligatoire")

    if not params.get("util"):
        errors.append("'util' est obligatoire")

    fichiers = params.get("fichiers", [])
    if not isinstance(fichiers, list):
        errors.append("'fichiers' doit etre une liste")

    includes = params.get("includes", [])
    if not isinstance(includes, list):
        errors.append("'includes' doit etre une liste")

    communs = params.get("communs", [])
    if not isinstance(communs, list):
        errors.append("'communs' doit etre une liste")

    autres = params.get("autres", [])
    if not isinstance(autres, list):
        errors.append("'autres' doit etre une liste")

    return errors


def detect_surcharge_from_parent(parent_dhpt_path):
    """Detecte si le .dhpt parent est un projet de surcharge.

    Renvoie True si l'en-tete commence par `xwin-s-projet`, False sinon
    (y compris si le fichier est introuvable -- on retombe en mode standard).
    """
    try:
        with open(parent_dhpt_path, "rb") as f:
            first_line = f.readline().decode("iso-8859-1", errors="replace").strip()
    except Exception:
        return False
    return first_line.startswith("xwin-s-projet")


def generate_dhps(params, surcharge=False):
    """Genere le contenu d'un fichier .dhps.

    Args:
        params: dict avec name, util, communs, fichiers, includes, autres
        surcharge: True pour generer une .dhps de surcharge (en-tete
                   `xwin-s-sprojet 2.0` requis par xwin7 pour les surcharges
                   de sous-projets standards)

    Returns:
        str: contenu complet du .dhps
    """
    lines = []

    # En-tete : variante surcharge si demandee (xwin7 distingue les deux)
    if surcharge:
        lines.append("xwin-s-sprojet     2.0")
    else:
        lines.append("xwin-sprojet       2.0")

    # [general]
    lines.append("[general]")
    date = params.get("date", generate_timestamp())
    lines.append(f'date="{date}"')
    lines.append(f'util="{params["util"]}"')

    # [communs]
    communs = params.get("communs", [])
    lines.append("[communs]")
    for group in communs:
        lines.append(f'incl="{group}"," "')

    # [fichiers]
    fichiers = params.get("fichiers", [])
    lines.append("[fichiers]")
    for fic in fichiers:
        lines.append(f'fic="{fic}"," "')

    # [includes] -- zdiva.dhsp toujours en premier
    includes = params.get("includes", [])
    lines.append("[includes]")
    # Assurer zdiva.dhsp est present et en premier
    all_includes = []
    has_zdiva = any(inc.lower() == "zdiva.dhsp" for inc in includes)
    if not has_zdiva:
        all_includes.append("zdiva.dhsp")
    for inc in includes:
        if inc.lower() == "zdiva.dhsp":
            all_includes.insert(0, inc)
        else:
            all_includes.append(inc)
    for inc in all_includes:
        lines.append(f'fic="{inc}"')

    # [autres]
    autres = params.get("autres", [])
    lines.append("[autres]")
    for fic in autres:
        lines.append(f'fic="{fic}"," "')

    # Ligne vide finale
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Genere un fichier .dhps (sous-projet Divalto)"
    )
    parser.add_argument(
        "--stdin", action="store_true",
        help="Lire les parametres JSON depuis stdin"
    )
    parser.add_argument(
        "--output", default=None,
        help="Fichier de sortie (stdout si omis)"
    )
    parser.add_argument(
        "--surcharge", action="store_true",
        help="Genere une .dhps de surcharge (en-tete xwin-s-sprojet)"
    )
    parser.add_argument(
        "--parent-dhpt", default=None,
        help="Chemin du .dhpt parent : si son en-tete est xwin-s-projet, "
             "mode surcharge active automatiquement (sauf si --surcharge "
             "explicite est deja fourni)"
    )
    args = parser.parse_args()

    if not args.stdin:
        print("Erreur : --stdin est requis", file=sys.stderr)
        sys.exit(1)

    try:
        params = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Erreur JSON : {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_params(params)
    if errors:
        for err in errors:
            print(f"Erreur : {err}", file=sys.stderr)
        sys.exit(1)

    # Mode surcharge : flag explicite prioritaire, sinon auto-detection
    # depuis le .dhpt parent si fourni
    surcharge = args.surcharge
    if not surcharge and args.parent_dhpt:
        surcharge = detect_surcharge_from_parent(args.parent_dhpt)

    content = generate_dhps(params, surcharge=surcharge)

    if args.output:
        # Ecriture en mode binaire : ISO-8859-1 + CRLF (format natif Divalto)
        content_crlf = content.replace("\r\n", "\n").replace("\n", "\r\n")
        with open(args.output, "wb") as f:
            f.write(content_crlf.encode("iso-8859-1"))
        result = {
            "file": args.output,
            "name": params["name"],
            "surcharge": surcharge,
            "sections": {
                "communs": len(params.get("communs", [])),
                "fichiers": len(params.get("fichiers", [])),
                "includes": len([i for i in content.split("\n")
                                if i.startswith("fic=") and
                                "[includes]" in content[:content.index(i)]
                                ]) if "[includes]" in content else 0,
                "autres": len(params.get("autres", []))
            },
            "zdiva_included": True
        }
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print(content)


if __name__ == "__main__":
    main()
