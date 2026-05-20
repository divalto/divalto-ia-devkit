#!/usr/bin/env python3
"""Genere un fichier .dhps (sous-projet Divalto) au format INI.

Le fichier genere est en texte brut (UTF-8) -- le skill writing-diva-files
se charge de la conversion finale en ISO-8859-1 + CRLF.

Usage :
    py create_subproject.py --stdin < params.json
    py create_subproject.py --stdin --output mon_sous_projet.dhps < params.json

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


def generate_dhps(params):
    """Genere le contenu d'un fichier .dhps.

    Args:
        params: dict avec name, util, communs, fichiers, includes, autres

    Returns:
        str: contenu complet du .dhps
    """
    lines = []

    # En-tete
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

    content = generate_dhps(params)

    if args.output:
        # Ecriture en mode binaire : ISO-8859-1 + CRLF (format natif Divalto)
        content_crlf = content.replace("\r\n", "\n").replace("\n", "\r\n")
        with open(args.output, "wb") as f:
            f.write(content_crlf.encode("iso-8859-1"))
        result = {
            "file": args.output,
            "name": params["name"],
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
