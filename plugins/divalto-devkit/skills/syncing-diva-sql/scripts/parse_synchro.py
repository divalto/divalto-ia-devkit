#!/usr/bin/env python3
"""Parse un rapport de synchronisation SQL xwin7 synchroauto.

Extrait le marqueur [TOTAL_ERRORS]N et les erreurs du rapport.

Usage :
    py parse_synchro.py --path rapport.txt

Sortie JSON :
    {
        "file": "rapport.txt",
        "success": true,
        "total_errors": 0,
        "errors": []
    }

Exit codes :
    0 = synchronisation reussie (0 erreur)
    1 = synchronisation echouee (erreurs trouvees)
    2 = erreur interne (rapport illisible)
"""

import argparse
import json
import os
import re
import sys


def parse_total_errors(lines):
    """Cherche le marqueur [TOTAL_ERRORS]N dans le rapport.

    Format attendu :
        [TOTAL_ERRORS]0
        [TOTAL_ERRORS]3

    Returns:
        int ou None si marqueur non trouve
    """
    pattern = re.compile(r'\[TOTAL_ERRORS\](\d+)')

    for line in reversed(lines):
        match = pattern.search(line)
        if match:
            return int(match.group(1))

    return None


def extract_errors(lines):
    """Extrait les lignes d'erreur du rapport avec contexte.

    Les erreurs de synchronisation contiennent typiquement :
    - Des messages d'erreur SQL (CREATE TABLE, ALTER TABLE echoue)
    - Des erreurs de connexion
    - Des erreurs de droits

    Returns:
        list of dict: [{line: N, message: "...", context: "..."}]
    """
    errors = []
    error_pattern = re.compile(r'(erreur|error|echec|failed|impossible)', re.IGNORECASE)

    # Exclure la ligne [TOTAL_ERRORS] elle-meme
    total_errors_pattern = re.compile(r'\[TOTAL_ERRORS\]')

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if total_errors_pattern.search(stripped):
            continue
        if error_pattern.search(stripped):
            context = lines[i - 1].strip() if i > 0 else ""
            errors.append({
                "line": i + 1,
                "message": stripped,
                "context": context
            })

    return errors


def parse_report(file_path):
    """Parse un rapport de synchronisation complet.

    Args:
        file_path: chemin du fichier rapport

    Returns:
        dict: resultat structure
    """
    try:
        with open(file_path, "r", encoding="iso-8859-1") as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"Fichier introuvable : {file_path}"}
    except Exception as e:
        return {"error": f"Erreur lecture : {e}"}

    lines = content.split("\n")

    # Chercher le marqueur [TOTAL_ERRORS]
    total_errors = parse_total_errors(lines)

    if total_errors is None:
        return {
            "error": "Marqueur [TOTAL_ERRORS] introuvable dans le rapport. "
                     "Verifier que le rapport est un fichier synchroauto xwin7."
        }

    # Extraire les erreurs
    errors = extract_errors(lines) if total_errors > 0 else []

    return {
        "file": file_path,
        "success": total_errors == 0,
        "total_errors": total_errors,
        "errors": errors
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parse un rapport de synchronisation SQL xwin7 synchroauto"
    )
    parser.add_argument(
        "--path", required=True,
        help="Chemin du fichier rapport de synchronisation"
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Erreur : fichier introuvable : {args.path}", file=sys.stderr)
        sys.exit(2)

    result = parse_report(args.path)

    if "error" in result:
        print(f"Erreur : {result['error']}", file=sys.stderr)
        sys.exit(2)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
