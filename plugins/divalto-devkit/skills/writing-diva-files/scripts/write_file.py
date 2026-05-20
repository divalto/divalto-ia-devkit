#!/usr/bin/env python3
"""Ecrit du contenu dans un fichier Divalto en ISO-8859-1 + CRLF.

Usage:
    py scripts/write_file.py --path "chemin/fichier.dhsp" --content "contenu"
    echo "contenu" | py scripts/write_file.py --path "chemin/fichier.dhsp" --stdin

Sortie JSON: {path, encoding, line_endings, bytes}
Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import sys


def normalize_line_endings(text):
    """Normalise les fins de ligne en CRLF."""
    # D'abord uniformiser en LF, puis convertir en CRLF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', '\r\n')
    return text


def write_diva_file(path, content):
    """Ecrit le contenu en ISO-8859-1 + CRLF."""
    # Normaliser les fins de ligne
    content = normalize_line_endings(content)

    # S'assurer que le fichier termine par CRLF
    if content and not content.endswith('\r\n'):
        content += '\r\n'

    # Encoder en ISO-8859-1
    try:
        encoded = content.encode('iso-8859-1')
    except UnicodeEncodeError as e:
        print(f"Erreur: caractere non encodable en ISO-8859-1: {e}", file=sys.stderr)
        return None

    # Creer le repertoire parent si necessaire
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    # Ecrire en mode binaire pour controler exactement les octets
    with open(path, 'wb') as f:
        f.write(encoded)

    return {
        "path": os.path.abspath(path),
        "encoding": "iso-8859-1",
        "line_endings": "CRLF",
        "bytes": len(encoded)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Ecrit du contenu dans un fichier Divalto en ISO-8859-1 + CRLF"
    )
    parser.add_argument("--path", required=True, help="Chemin du fichier a ecrire")
    parser.add_argument("--content", help="Contenu a ecrire (texte)")
    parser.add_argument("--stdin", action="store_true", help="Lire le contenu depuis stdin")

    args = parser.parse_args()

    if args.stdin:
        content = sys.stdin.read()
    elif args.content is not None:
        content = args.content
    else:
        print("Erreur: --content ou --stdin requis", file=sys.stderr)
        sys.exit(1)

    result = write_diva_file(args.path, content)
    if result is None:
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
