#!/usr/bin/env python3
"""Convertit un code Nature DIVA en taille en octets.

Usage:
    py .claude/skills/managing-diva-dictionaries/scripts/nature_to_size.py --nature "20"
    py .claude/skills/managing-diva-dictionaries/scripts/nature_to_size.py --nature "D8"
    py .claude/skills/managing-diva-dictionaries/scripts/nature_to_size.py --nature "6,2"
    py .claude/skills/managing-diva-dictionaries/scripts/nature_to_size.py --nature "13,D0"

    Batch (JSON sur stdin) :
    echo '["20","D8","6,2","13,D0"]' | py .../nature_to_size.py --stdin

Sortie JSON: {nature, size, type, description} ou [{nature, size, type, description}, ...]
Exit codes: 0 = succes, 1 = erreur utilisateur
"""

import argparse
import json
import re
import sys


# Natures speciales avec taille fixe
SPECIAL_NATURES = {
    "D8": {"size": 8, "type": "date", "description": "Date (AAAAMMJJ)"},
    "H6": {"size": 6, "type": "heure", "description": "Heure (HHMMSS)"},
    "DH": {"size": 14, "type": "dateheure", "description": "Date+Heure"},
}


def nature_to_size(nature_str):
    """Convertit un code Nature en taille en octets.

    Args:
        nature_str: Code Nature (ex: "20", "D8", "6,2", "13,D0")

    Returns:
        dict: {nature, size, type, description} ou None si invalide
    """
    nature_str = nature_str.strip()

    # Natures speciales
    upper = nature_str.upper()
    if upper in SPECIAL_NATURES:
        info = SPECIAL_NATURES[upper]
        return {
            "nature": nature_str,
            "size": info["size"],
            "type": info["type"],
            "description": info["description"],
        }

    # Nature numerique : N,M ou N,D0
    if "," in nature_str:
        parts = nature_str.split(",", 1)
        try:
            n = int(parts[0])
        except ValueError:
            return None

        suffix = parts[1].strip()
        if suffix.upper() == "D0":
            return {
                "nature": nature_str,
                "size": n,
                "type": "numerique_signe",
                "description": f"Numerique signe ({n} octets)",
            }
        else:
            try:
                m = int(suffix)
            except ValueError:
                return None
            return {
                "nature": nature_str,
                "size": n,
                "type": "numerique",
                "description": f"Numerique ({n} octets, {m} decimales)",
            }

    # Nature simple : entier = taille
    try:
        n = int(nature_str)
        if n <= 0:
            return None
        return {
            "nature": nature_str,
            "size": n,
            "type": "simple",
            "description": f"Alphanumerique ({n} octets)",
        }
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Convertit un code Nature DIVA en taille en octets"
    )
    parser.add_argument("--nature", default=None,
                        help="Code Nature a convertir (ex: 20, D8, 6,2)")
    parser.add_argument("--stdin", action="store_true",
                        help="Lire une liste JSON de natures sur stdin")

    args = parser.parse_args()

    if args.stdin:
        try:
            natures = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Erreur JSON stdin : {e}", file=sys.stderr)
            sys.exit(1)

        results = []
        for nat in natures:
            info = nature_to_size(str(nat))
            if info is None:
                print(f"Nature invalide : '{nat}'", file=sys.stderr)
                sys.exit(1)
            results.append(info)

        json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
        print()

    elif args.nature:
        info = nature_to_size(args.nature)
        if info is None:
            print(f"Nature invalide : '{args.nature}'", file=sys.stderr)
            sys.exit(1)
        json.dump(info, sys.stdout, indent=2, ensure_ascii=False)
        print()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
