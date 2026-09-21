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


def set_hidden_windows(path):
    """Pose l'attribut 'cache' Windows sur le backup (no-op hors Windows ; jamais bloquant)."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)  # FILE_ATTRIBUTE_HIDDEN
    except Exception:
        pass


def _utf8_residue_count(data):
    """Compte les sequences UTF-8 residuelles dans des octets censes etre ISO-8859-1
    (signature d'un mojibake : Latin-1 double-encode). Copie autonome de la meme
    heuristique que verify_encoding.find_utf8_residue (vendoring intra-skill)."""
    n = 0
    i = 0
    total = len(data)
    while i < total:
        b = data[i]
        if b in (0xC2, 0xC3) and i + 1 < total and 0x80 <= data[i + 1] <= 0xBF:
            n += 1
            i += 2
            continue
        if b == 0xEF and i + 2 < total and data[i + 1] == 0xBF and data[i + 2] == 0xBD:
            n += 1
            i += 3
            continue
        i += 1
    return n


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
    needs_final_crlf = len(data) > 0 and not data.endswith(b'\r\n')

    if not needs_encoding_fix and not needs_line_ending_fix and not has_bom and not needs_final_crlf:
        # Rien a convertir selon les 4 criteres ci-dessus... mais le fichier peut tout de
        # meme etre CORROMPU : un mojibake MELANGE a du vrai Latin-1 (ex. 0xE9 reel + 0xC3 0xA9
        # double-encode) n'est ni de l'UTF-8 valide (donc `needs_encoding_fix` est faux) ni un
        # probleme de fins de ligne. On rendait alors `verified: true` sur un fichier que
        # verify_encoding declare invalide -- et le workflow "verify detecte -> convert corrige"
        # bouclait sans fin. On le DIT, au lieu de certifier a tort.
        residue = _utf8_residue_count(data)
        if residue:
            return {
                "path": os.path.abspath(path),
                "backup": None,
                "original_encoding": original_encoding,
                "original_line_endings": original_line_endings,
                "converted": False,
                "verified": False,
                "issues": [
                    "%d sequence(s) UTF-8 residuelle(s) melangee(s) a du Latin-1 valide "
                    "(mojibake partiel)" % residue
                ],
                "hint": "Conversion globale IMPOSSIBLE sans risque : le fichier n'est pas de "
                        "l'UTF-8 valide (une conversion echouerait) et reecrire les seules "
                        "sequences suspectes serait une supposition sur du contenu legitime. "
                        "Localiser les sequences avec verify_encoding.py, puis corriger "
                        "chirurgicalement avec patch_file.py (ancre unique).",
            }
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
        if os.path.exists(backup_path):
            os.remove(backup_path)
        shutil.copy2(path, backup_path)
        set_hidden_windows(backup_path)

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

    # Garantir un CRLF final (son absence provoque l'Erreur 135)
    if text and not text.endswith('\r\n'):
        text += '\r\n'

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
    final_crlf_ok = (len(result_data) == 0) or result_data.endswith(b'\r\n')
    # Le residu mojibake entre dans le verdict : sinon `verified` ne signifie pas la meme
    # chose que le `valid` de verify_encoding, et le skill se contredit lui-meme.
    result_residue = _utf8_residue_count(result_data)
    verified = (result_encoding in ('iso-8859-1', 'us-ascii')
                and result_line_endings in ('CRLF', 'none')
                and final_crlf_ok
                and result_residue == 0)

    return {
        "path": os.path.abspath(path),
        "backup": os.path.abspath(backup_path) if backup_path else None,
        "original_encoding": original_encoding,
        "original_line_endings": original_line_endings,
        "converted": True,
        "verified": verified
    }


def main():
    # Sortie en UTF-8 (stdout + stderr) : sinon print() encode avec la console (cp1252 sur
    # Windows) et les caracteres non-ASCII cassent un json.loads(utf-8) cote appelant.
    # Meme garde-fou que read_isam.py.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
            _stream.reconfigure(encoding="utf-8")

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

    # Le code de sortie doit refleter le verdict : sortir 0 sur un fichier encore invalide
    # laissait l'appelant croire la reparation faite (workflow "verify -> convert" en boucle).
    if not result.get("verified", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
