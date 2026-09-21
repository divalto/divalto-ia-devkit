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
import shutil
import sys


def _utf8_residue_count(data):
    """Compte les sequences UTF-8 residuelles dans des octets censes etre ISO-8859-1
    (signature d'un mojibake : Latin-1 double-encode). Copie autonome de la meme
    heuristique que verify_encoding.find_utf8_residue (vendoring intra-skill : le
    script doit rester executable seul, sans import de son voisin)."""
    n = 0
    i = 0
    L = len(data)
    while i < L:
        b = data[i]
        if b in (0xC2, 0xC3) and i + 1 < L and 0x80 <= data[i + 1] <= 0xBF:
            n += 1
            i += 2
            continue
        if b == 0xEF and i + 2 < L and data[i + 1] == 0xBF and data[i + 2] == 0xBD:
            n += 1
            i += 3
            continue
        i += 1
    return n


def set_hidden_windows(path):
    """Pose l'attribut 'cache' Windows sur le backup (no-op hors Windows ; jamais bloquant)."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)  # FILE_ATTRIBUTE_HIDDEN
    except Exception:
        pass


def normalize_line_endings(text):
    """Normalise les fins de ligne en CRLF."""
    # D'abord uniformiser en LF, puis convertir en CRLF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', '\r\n')
    return text


def write_diva_file(path, content, create_backup=True):
    """Ecrit le contenu en ISO-8859-1 + CRLF.

    write_file CREE ou REECRIT le fichier en entier. S'il ecrase un fichier existant,
    il fait d'abord un backup `.bak` (cache sous Windows, glissant) et signale un
    avertissement : pour une modification CIBLEE, utiliser patch_file.py.
    """
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

    # Garde-fou anti-mojibake : des sequences UTF-8 residuelles dans les octets ISO-8859-1
    # signifient que le contenu etait deja corrompu en amont (double-encodage) -> refuser
    # d'ecrire la corruption plutot que de la propager silencieusement.
    residue = _utf8_residue_count(encoded)
    if residue:
        print(f"Erreur: {residue} sequence(s) UTF-8 residuelle(s) detectee(s) dans le contenu "
              f"(mojibake / double-encodage) -- ecriture annulee. Verifier la source du contenu "
              f"(le pipe transporte-t-il bien de l'UTF-8 propre ?).", file=sys.stderr)
        return None

    # Creer le repertoire parent si necessaire
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    # Si on ecrase un fichier existant : backup + avertissement (pas de blocage)
    backup = None
    warning = None
    if os.path.exists(path):
        warning = ("Fichier existant reecrit en entier. Pour une modification ciblee "
                   "(preserver le reste du fichier), utiliser patch_file.py.")
        if create_backup:
            backup = path + '.bak'
            try:
                if os.path.exists(backup):
                    os.remove(backup)
                shutil.copy2(path, backup)
                set_hidden_windows(backup)
            except Exception as e:
                # REFUS, pas un simple avertissement : ecraser un fichier existant apres
                # avoir PERDU le filet de securite est precisement le scenario destructeur
                # que le backup existe pour couvrir. patch_file.py refuse dans la meme
                # situation -- write_file ecrasait quand meme et rapportait exit 0.
                print(f"Erreur: backup impossible ({e}) -- ecriture ANNULEE, le fichier "
                      f"existant est intact. Liberer/reparer le dossier, ou assumer le "
                      f"risque explicitement avec --no-backup.", file=sys.stderr)
                sys.exit(1)

    # Ecrire en mode binaire pour controler exactement les octets
    with open(path, 'wb') as f:
        f.write(encoded)

    return {
        "path": os.path.abspath(path),
        "encoding": "iso-8859-1",
        "line_endings": "CRLF",
        "bytes": len(encoded),
        "backup": (os.path.abspath(backup) if backup else None),
        "warning": warning
    }


def main():
    # Sortie en UTF-8 (stdout + stderr) : sinon print() encode avec la console (cp1252 sur
    # Windows) et les caracteres non-ASCII (chemin accentue, warning...) cassent un
    # json.loads(utf-8) cote appelant. Meme garde-fou que read_isam.py.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
            _stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Ecrit du contenu dans un fichier Divalto en ISO-8859-1 + CRLF"
    )
    parser.add_argument("--path", required=True, help="Chemin du fichier a ecrire")
    parser.add_argument("--content", help="Contenu a ecrire (texte)")
    parser.add_argument("--content-file", help="Lire le contenu depuis un fichier UTF-8 (evite le quoting PowerShell et le BOM ; voie privilegiee sous PowerShell)")
    parser.add_argument("--stdin", action="store_true", help="Lire le contenu depuis stdin (UTF-8)")
    parser.add_argument("--no-backup", action="store_true", help="Ne pas creer de .bak si le fichier existe")

    args = parser.parse_args()

    if args.content_file is not None:
        # Lire depuis un fichier UTF-8 (utf-8-sig -> BOM eventuel supprime). Evite le
        # quoting PowerShell (guillemets absorbes) et le decodage console -- voie privilegiee.
        try:
            with open(args.content_file, 'r', encoding='utf-8-sig') as _cf:
                content = _cf.read()
        except OSError as e:
            print(f"Erreur: --content-file illisible : {e}", file=sys.stderr)
            sys.exit(1)
        except UnicodeDecodeError as e:
            print(f"Erreur: --content-file n'est pas de l'UTF-8 valide : {e}", file=sys.stderr)
            sys.exit(1)
    elif args.stdin:
        # Lire les octets bruts et decoder explicitement en UTF-8. sys.stdin.read()
        # decoderait avec l'encodage console (cp1252 sur poste Windows) -> mojibake
        # silencieux sur un contenu UTF-8 pipe (heredoc bash, contenu genere, Get-Content).
        # Un contenu non-UTF-8 leve UnicodeDecodeError -> echec BRUYANT, pas de corruption.
        try:
            content = sys.stdin.buffer.read().decode('utf-8-sig')  # -sig : strippe un BOM de tete pipe (cf. #262)
        except UnicodeDecodeError as e:
            print(f"Erreur: stdin n'est pas de l'UTF-8 valide (offset {e.start}) : {e}. "
                  f"Piper de l'UTF-8, ou passer le contenu via --content-file.", file=sys.stderr)
            sys.exit(1)
    elif args.content is not None:
        content = args.content
    else:
        print("Erreur: --content, --content-file ou --stdin requis", file=sys.stderr)
        sys.exit(1)

    result = write_diva_file(args.path, content, create_backup=not args.no_backup)
    if result is None:
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
