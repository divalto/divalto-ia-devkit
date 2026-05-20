#!/usr/bin/env python3
"""Verifie qu'un fichier Divalto est bien en ISO-8859-1 + CRLF.

Usage:
    py scripts/verify_encoding.py --path "chemin/fichier.dhsp"

Sortie JSON: {path, valid, encoding, line_endings, issues[]}
Exit codes: 0 = valide, 1 = invalide, 2 = erreur interne
"""

import argparse
import json
import os
import sys


# Extensions binaires Divalto — ne pas verifier
BINARY_EXTENSIONS = {'.dhop', '.dhoq'}

# Extensions texte Divalto — doivent etre ISO-8859-1 + CRLF
DIVA_TEXT_EXTENSIONS = {'.dhsp', '.dhsq', '.dhsj', '.dhpt', '.dhps', '.dhsd', '.dhsf'}


def detect_encoding(data):
    """Detecte si les donnees sont UTF-8 ou ISO-8859-1.

    Retourne 'utf-8', 'iso-8859-1', ou 'us-ascii'.
    """
    # Verifier si c'est du pur ASCII
    if all(b < 0x80 for b in data):
        return 'us-ascii'

    # Verifier si c'est du UTF-8 valide avec des sequences multi-octets
    try:
        data.decode('utf-8')
        # Verifier s'il y a des sequences multi-octets UTF-8 (octets >= 0x80)
        has_multibyte = False
        i = 0
        while i < len(data):
            b = data[i]
            if b >= 0xC0:  # Debut de sequence multi-octets UTF-8
                has_multibyte = True
                break
            elif b >= 0x80:  # Octet de continuation sans debut — pas UTF-8 valide
                return 'iso-8859-1'
            i += 1
        if has_multibyte:
            return 'utf-8'
    except UnicodeDecodeError:
        pass

    # Par defaut, c'est ISO-8859-1 (tout octet 0x00-0xFF est valide)
    return 'iso-8859-1'


def detect_line_endings(data):
    """Detecte le type de fins de ligne.

    Retourne 'CRLF', 'LF', 'mixed', ou 'none'.
    """
    crlf_count = data.count(b'\r\n')
    # Compter les LF isoles (pas precedes de CR)
    lf_count = 0
    for i, b in enumerate(data):
        if b == 0x0A and (i == 0 or data[i - 1] != 0x0D):
            lf_count += 1

    if crlf_count == 0 and lf_count == 0:
        return 'none'
    elif crlf_count > 0 and lf_count == 0:
        return 'CRLF'
    elif crlf_count == 0 and lf_count > 0:
        return 'LF'
    else:
        return 'mixed'


def verify_file(path):
    """Verifie l'encodage et les fins de ligne d'un fichier Divalto."""
    issues = []

    if not os.path.exists(path):
        return {
            "path": os.path.abspath(path),
            "valid": False,
            "encoding": "unknown",
            "line_endings": "unknown",
            "issues": [f"Fichier non trouve: {path}"]
        }

    ext = os.path.splitext(path)[1].lower()

    if ext in BINARY_EXTENSIONS:
        return {
            "path": os.path.abspath(path),
            "valid": True,
            "encoding": "binary",
            "line_endings": "N/A",
            "issues": []
        }

    with open(path, 'rb') as f:
        data = f.read()

    if len(data) == 0:
        return {
            "path": os.path.abspath(path),
            "valid": True,
            "encoding": "empty",
            "line_endings": "none",
            "issues": []
        }

    encoding = detect_encoding(data)
    line_endings = detect_line_endings(data)

    # Verifier l'encodage
    if encoding == 'utf-8':
        issues.append("Encodage UTF-8 detecte — doit etre ISO-8859-1")
    elif encoding == 'us-ascii':
        pass  # ASCII est un sous-ensemble valide de ISO-8859-1

    # Verifier les fins de ligne
    if line_endings == 'LF':
        issues.append("Fins de ligne LF detectees — doit etre CRLF")
    elif line_endings == 'mixed':
        issues.append("Fins de ligne mixtes (CRLF + LF) — doit etre 100% CRLF")

    # Verifier BOM UTF-8
    if data[:3] == b'\xef\xbb\xbf':
        issues.append("BOM UTF-8 detecte en debut de fichier — a supprimer")

    # Avertissement si extension non-Divalto
    if ext and ext not in DIVA_TEXT_EXTENSIONS and ext not in BINARY_EXTENSIONS:
        issues.append(f"Extension {ext} non reconnue comme fichier Divalto")

    valid = len(issues) == 0

    return {
        "path": os.path.abspath(path),
        "valid": valid,
        "encoding": encoding,
        "line_endings": line_endings,
        "issues": issues
    }


def main():
    parser = argparse.ArgumentParser(
        description="Verifie l'encodage et les fins de ligne d'un fichier Divalto"
    )
    parser.add_argument("--path", required=True, help="Chemin du fichier a verifier")

    args = parser.parse_args()
    from pathlib import Path
    if not Path(args.path).exists():
        print(f"Erreur : path '{args.path}' introuvable.", file=sys.stderr)
        sys.exit(2)
    result = verify_file(args.path)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
