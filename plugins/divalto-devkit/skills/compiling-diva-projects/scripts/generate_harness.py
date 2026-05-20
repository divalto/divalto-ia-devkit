#!/usr/bin/env python3
"""Genere un harness standalone pour valider un fichier .dhsp.

Cree un mini-projet (.dhpt + .dhps) + script de compilation dans le repertoire de sortie.
Le fichier source est copie dans le repobjet pour compilation.

Usage :
    py generate_harness.py --source "chemin/fichier.dhsp" --output-dir "chemin/sortie"
    py generate_harness.py --source "chemin/fichier.dhsp" --output-dir "chemin/sortie" --with-zdiva --with-communs

Sortie JSON :
    {
        "dhpt": "chemin/sortie/projet/harness.dhpt",
        "dhps": "chemin/sortie/objet/harness.dhps",
        "source_copy": "chemin/sortie/objet/fichier.dhsp",
        "compile_script": "chemin/sortie/scripts/harness_compile.ps1",
        "log_file": "chemin/sortie/log/harness_YYYYMMDD_HHMMSS.txt"
    }

Exit codes :
    0 = succes
    1 = erreur utilisateur (fichier introuvable, extension invalide)
    2 = erreur interne
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime


# Sous-repertoires crees dans le repertoire de sortie
SUB_OBJET = "objet"
SUB_PROJET = "projet"
SUB_SCRIPTS = "scripts"
SUB_LOG = "log"

PS1_NAME = "harness_compile.ps1"


def write_iso(path, content):
    """Ecrit un fichier en ISO-8859-1 + CRLF."""
    content = content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    if content and not content.endswith('\r\n'):
        content += '\r\n'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(content.encode('iso-8859-1'))


def generate_dhpt(source_basename, with_communs, objet_dir):
    """Genere le contenu du fichier .dhpt."""
    now = datetime.now().strftime("%Y%m%d%H%M%S") + "000099"

    lines = [
        'xwin-projet        2.0',
        '[general]',
        'nom="harness"',
        'progexec="ia.dhop"',
        f'date="{now}"',
        'util="SC"',
        '[profildefaut]',
        '[profil]',
        'nom="d\xe9veloppement"',
        f'repobjet="{objet_dir}"',
        'implicites="d\xe9veloppement_x13.txt"',
        'versioncible="X.38"',
    ]

    if with_communs:
        lines += [
            '[communs]',
            'nom="communs"',
            'fic="a5pm000.dhsp"," "',
            'fic="a5pmtab.dhsp"," "',
            'fic="gtpm000.dhsp"," "',
        ]

    lines += [
        '[sousprojets]',
        'fic="harness.dhps"," "',
        '[projetsfusion]',
        '[fabricationmere]',
        '[autres]',
    ]

    return '\n'.join(lines)


def generate_dhps(source_basenames, with_zdiva):
    """Genere le contenu du fichier .dhps.

    Args:
        source_basenames: liste de noms de fichiers source (basenames)
        with_zdiva: inclure zdiva.dhsp dans les includes
    """
    now = datetime.now().strftime("%Y%m%d%H%M%S") + "000099"

    lines = [
        'xwin-sprojet       2.0',
        '[general]',
        f'date="{now}"',
        'util="SC"',
        '[communs]',
        '[fichiers]',
    ]

    for basename in source_basenames:
        lines.append(f'fic="{basename}"," "')

    lines.append('[includes]')

    if with_zdiva:
        lines.append('fic="zdiva.dhsp"')

    lines.append('[autres]')

    return '\n'.join(lines)


def generate_ps1(log_name, projet_dir, log_dir, user=None):
    """Genere le script de compilation PowerShell.

    Args:
        log_name: nom du fichier de log
        projet_dir: repertoire projet
        log_dir: repertoire logs
        user: utilisateur xwin7 (None = omis de la ligne de commande)
    """
    dhpt_path = os.path.join(projet_dir, "harness.dhpt")
    log_path = os.path.join(log_dir, log_name)
    stdout_path = os.path.join(log_dir, log_name.replace(".txt", "_stdout.txt"))
    stderr_path = os.path.join(log_dir, log_name.replace(".txt", "_stderr.txt"))

    user_arg = f"-user {user} " if user else ""

    lines = [
        '$ErrorActionPreference = "Continue"',
        '$proc = Start-Process -FilePath "C:\\divalto\\sys\\xwin7.exe" '
        + f"-ArgumentList '-action buildall {user_arg}"
        + f'-project "{dhpt_path}" '
        + '-profile "d\xe9veloppement" '
        + f'-output "{log_path}" '
        + "-outputall' "
        + '-Wait -PassThru -NoNewWindow '
        + f'-RedirectStandardOutput "{stdout_path}" '
        + f'-RedirectStandardError "{stderr_path}"',
        'Write-Host "ExitCode: $($proc.ExitCode)"',
    ]

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Genere un harness standalone pour valider des fichiers DIVA"
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--source",
        help="Chemin d'un fichier .dhsp a valider (retro-compatible)"
    )
    source_group.add_argument(
        "--sources", nargs='+',
        help="Chemins de plusieurs fichiers .dhsp a valider ensemble"
    )
    parser.add_argument(
        "--with-zdiva", action="store_true",
        help="Inclure zdiva.dhsp dans les includes"
    )
    parser.add_argument(
        "--with-communs", action="store_true",
        help="Inclure les communs framework (a5pm000, a5pmtab, gtpm000)"
    )
    parser.add_argument(
        "--user",
        help="Utilisateur xwin7 (defaut: X_USER env, sinon omis)"
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Repertoire de sortie (4 sous-dossiers crees : objet, projet, scripts, log)"
    )
    args = parser.parse_args()

    # Resoudre les chemins a partir de --output-dir
    output_dir = os.path.abspath(args.output_dir)
    objet_dir = os.path.join(output_dir, SUB_OBJET)
    projet_dir = os.path.join(output_dir, SUB_PROJET)
    scripts_dir = os.path.join(output_dir, SUB_SCRIPTS)
    log_dir = os.path.join(output_dir, SUB_LOG)

    # Normaliser les sources (--source unique ou --sources multiples)
    source_paths = args.sources if args.sources else [args.source]

    # Verifier chaque fichier source
    sources = []
    for src in source_paths:
        src = os.path.abspath(src)
        if not os.path.exists(src):
            print(f"Erreur : fichier introuvable : {src}", file=sys.stderr)
            sys.exit(1)
        VALID_EXTENSIONS = ('.dhsp', '.dhsq')
        if not src.lower().endswith(VALID_EXTENSIONS):
            print(f"Erreur : extension attendue .dhsp ou .dhsq, recu : {os.path.splitext(src)[1]}",
                  file=sys.stderr)
            sys.exit(1)
        sources.append(src)

    source_basenames = [os.path.basename(s) for s in sources]

    # Creer les repertoires
    for d in [objet_dir, projet_dir, scripts_dir, log_dir]:
        os.makedirs(d, exist_ok=True)

    # Copier les fichiers source dans repobjet
    source_copies = []
    for src in sources:
        dest = os.path.join(objet_dir, os.path.basename(src))
        shutil.copy2(src, dest)
        source_copies.append(dest)

    # Generer un nom de log unique (timestamp) pour eviter les ecrasements
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_name = f"harness_{ts}.txt"

    # Generer les fichiers
    dhpt_path = os.path.join(projet_dir, "harness.dhpt")
    dhps_path = os.path.join(objet_dir, "harness.dhps")
    ps1_path = os.path.join(scripts_dir, PS1_NAME)
    log_path = os.path.join(log_dir, log_name)

    # Utilisateur xwin7 :
    #   - `--user XX` explicite : prioritaire, passe `-user XX`
    #   - `X_USER` env non-vide (stripe != '') : xwin7 la lit, pas de `-user`
    #   - sinon : FORCE un fallback sur l'utilisateur Windows courant pour eviter
    #     le crash xwin7 ExitCode -805306369 (confirme 2026-04-15 : corruption des
    #     objets compiles + buildall force si X_USER absente/vide et `-user` omis).
    user = args.user
    if not user:
        env_user = os.environ.get("X_USER", "").strip()
        if env_user:
            user = None  # xwin7 lira X_USER
        else:
            # Fallback securisant : utilisateur Windows courant
            user = os.environ.get("USERNAME", "").strip() or None
            if user:
                print(f"  INFO: X_USER vide/absente, fallback sur USERNAME={user}", file=sys.stderr)
            else:
                print("  WARN: ni --user, ni X_USER, ni USERNAME -- xwin7 risque de crasher", file=sys.stderr)

    write_iso(dhpt_path, generate_dhpt(source_basenames[0], args.with_communs, objet_dir))
    write_iso(dhps_path, generate_dhps(source_basenames, args.with_zdiva))
    write_iso(ps1_path, generate_ps1(log_name, projet_dir, log_dir, user=user))

    result = {
        "dhpt": dhpt_path,
        "dhps": dhps_path,
        "source_copies": source_copies,
        "compile_script": ps1_path,
        "log_file": log_path,
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
