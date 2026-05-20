#!/usr/bin/env python3
"""Convertit un fichier vers ISO-8859-1 + CRLF.

Detecte l'encodage actuel (UTF-8 ou ISO-8859-1) et les fins de ligne,
puis convertit si necessaire. Cree un backup .bak avant modification.

Usage:
    py scripts/convert_file.py --path "chemin/fichier.dhsp"
    py scripts/convert_file.py --path "chemin/fichier.dhsp" --no-backup

Sortie JSON: {path, backup, original_encoding, original_line_endings, converted, verified}
Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import shutil
import sys

# Reutiliser les fonctions de detection de verify_encoding
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from verify_encoding import detect_encoding, detect_line_endings


def convert_file(path, create_backup=True):
    """Convertit un fichier vers ISO-8859-1 + CRLF."""
    if not os.path.exists(path):
        print(f"Erreur: fichier non trouve: {path}", file=sys.stderr)
        return None

    # Lire les donnees brutes
    with open(path, 'rb') as f:
        data = f.read()

    original_encoding = detect_encoding(data)
    original_line_endings = detect_line_endings(data)

    # Verifier si conversion necessaire
    needs_encoding_fix = original_encoding == 'utf-8'
    needs_line_ending_fix = original_line_endings in ('LF', 'mixed')
    has_bom = data[:3] == b'\xef\xbb\xbf'

    if not needs_encoding_fix and not needs_line_ending_fix and not has_bom:
        return {
            "path": os.path.abspath(path),
            "backup": None,
            "original_encoding": original_encoding,
            "original_line_endings": original_line_endings,
            "converted": False,
            "verified": True
        }

    # Creer backup
    backup_path = None
    if create_backup:
        backup_path = path + '.bak'
        shutil.copy2(path, backup_path)

    # Decoder le contenu
    try:
        if has_bom:
            text = data[3:].decode('utf-8' if needs_encoding_fix else 'iso-8859-1')
        elif needs_encoding_fix:
            text = data.decode('utf-8')
        else:
            text = data.decode('iso-8859-1')
    except (UnicodeDecodeError, UnicodeEncodeError) as e:
        print(f"Erreur de decodage: {e}", file=sys.stderr)
        # Restaurer le backup si la conversion echoue
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, path)
        return None

    # Normaliser les fins de ligne en CRLF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', '\r\n')

    # Encoder en ISO-8859-1
    try:
        encoded = text.encode('iso-8859-1')
    except UnicodeEncodeError as e:
        print(f"Erreur: caractere non encodable en ISO-8859-1: {e}", file=sys.stderr)
        print("Le fichier contient des caracteres Unicode hors ISO-8859-1.", file=sys.stderr)
        # Restaurer le backup
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, path)
        return None

    # Ecrire le fichier converti
    with open(path, 'wb') as f:
        f.write(encoded)

    # Verifier le resultat
    with open(path, 'rb') as f:
        result_data = f.read()

    result_encoding = detect_encoding(result_data)
    result_line_endings = detect_line_endings(result_data)
    verified = result_encoding in ('iso-8859-1', 'us-ascii') and result_line_endings in ('CRLF', 'none')

    return {
        "path": os.path.abspath(path),
        "backup": os.path.abspath(backup_path) if backup_path else None,
        "original_encoding": original_encoding,
        "original_line_endings": original_line_endings,
        "converted": True,
        "verified": verified
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convertit un fichier vers ISO-8859-1 + CRLF"
    )
    parser.add_argument("--path", required=True, help="Chemin du fichier a convertir")
    parser.add_argument("--no-backup", action="store_true", help="Ne pas creer de backup .bak")

    args = parser.parse_args()
    result = convert_file(args.path, create_backup=not args.no_backup)

    if result is None:
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
