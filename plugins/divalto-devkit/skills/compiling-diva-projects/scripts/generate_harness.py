#!/usr/bin/env python3
"""Genere un harness standalone (DERNIER RECOURS) pour compiler des sources DIVA isoles.

Le harness EMPRUNTE sa configuration de compilation a un `.dhpt` REEL du workspace
(`--from-dhpt`) : profil, implicite (search path), util, progexec, cheminbases. Il ne
code AUCUNE valeur "poste" en dur -- un harness a la config inventee compile contre un
environnement fantome (RETEX : implicite hardcode inexistant sur le poste -> resolution
des includes cassee, faux verdicts).

QUAND l'utiliser : uniquement en DERNIER RECOURS -- source flambant neuf n'appartenant a
aucun sous-projet, en mode autonome ou l'on ne peut pas demander a l'utilisateur ou le
cabler. Dans tous les autres cas, compiler via le VRAI `.dhpt` du projet :
    py compile_project.py --project "<projet.dhpt>" --sousproject "<sousprojet.dhps>"
Cf. SKILL.md "Arbre de decision -- ou compiler un source".

Le `.dhpt` modele (`--from-dhpt`) est celui deja identifie et valide par le skill
`understanding-integrator-workspace` (qui enumere les `.dhpt` du workspace et controle la
coherence implicite <-> `.dhpt`). On ne le devine pas : on reprend celui de la decouverte.

Config empruntee (valide empiriquement) :
  - `[profil]` nom + implicites  -> LE champ critique : resout includes + dictionnaires.
  - `[general]` util, progexec, cheminbases -> contexte. NB : cheminbases est un chemin
    *runtime*, inoffensif a la compilation (teste : buildall OK meme avec cheminbases bidon).
  - `[profil]` repobjet/repobjetsurcharge -> FORCES sur le dossier objet JETABLE du harness
    (isole les objets produits, ne pollue pas le pack reel du poste).
  - `[communs]` -> OMIS entierement (une section `[communs]` presente mais VIDE est refusee
    par xwin7 : "Parametre manquant / Mot: nom"). Un source qui a besoin d'un module commun
    (a5pm000...) n'est PAS isolable dans un harness : signal qu'il faut le VRAI `.dhpt`.

Usage :
    py generate_harness.py --from-dhpt "<projet_reel.dhpt>" --source "fichier.dhsp" \\
        --output-dir "<sortie>"
    py generate_harness.py --from-dhpt "<projet_reel.dhpt>" --profile "<nom_profil>" \\
        --sources a.dhsp b.dhsp --output-dir "<sortie>"

Etape suivante -- compiler via le profil EMPRUNTE retourne (borrowed_profile) :
    py compile_project.py --project "<sortie>/projet/harness.dhpt" \\
        --profile "<borrowed_profile>" --log-path "<sortie>/log/harness_*.txt" --action buildall

Sortie JSON :
    {
      "dhpt": "...", "dhps": "...", "source_copies": [...], "objet_dir": "...",
      "borrowed_profile": "<nom>", "borrowed_from": "<.dhpt modele>",
      "next": "py compile_project.py --project ... --profile ... --log-path ..."
    }

Exit codes :
    0 = succes
    1 = erreur utilisateur (source/`.dhpt` introuvable, extension, profil ambigu/absent,
        implicite manquant dans le profil emprunte)
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
SUB_LOG = "log"

VALID_EXTENSIONS = ('.dhsp', '.dhsq')


def fail(msg, code=1):
    """Message d'erreur sur stderr + exit."""
    print(f"Erreur : {msg}", file=sys.stderr)
    sys.exit(code)


def write_iso(path, content):
    """Ecrit un fichier en ISO-8859-1 + CRLF (encodage DIVA)."""
    content = content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    if content and not content.endswith('\r\n'):
        content += '\r\n'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(content.encode('iso-8859-1'))


def _strip_val(rest):
    """'"valeur"," "' (partie apres la cle=) -> 'valeur' (1er champ, sans guillemets)."""
    return rest.split(",", 1)[0].strip().strip('"')


def parse_dhpt(dhpt_path):
    """Parse un `.dhpt` : `[general]` + liste ordonnee des `[profil]`.

    Retourne {general: {util, progexec, cheminbases},
              profils: [{nom, implicites, versioncible}, ...]}.
    Lecture ISO-8859-1 (encodage DIVA). Seules les cles utiles a l'emprunt sont retenues ;
    repobjet/repobjetsurcharge du modele sont volontairement IGNORES (forces en jetable).
    """
    with open(dhpt_path, 'rb') as f:
        text = f.read().decode('iso-8859-1', errors='replace')

    general = {}
    profils = []
    section = None
    cur = None
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith('['):
            sec = s.lower()
            if sec == '[profil]':
                cur = {}
                profils.append(cur)
                section = 'profil'
            elif sec == '[general]':
                section = 'general'
            else:
                section = sec  # toute autre section : on ne collecte rien
            continue
        if '=' not in s:
            continue
        key = s.split('=', 1)[0].strip().lower()
        rest = s[len(key):].lstrip()
        if rest.startswith('='):
            rest = rest[1:]
        if section == 'general':
            if key in ('util', 'progexec', 'cheminbases'):
                general[key] = _strip_val(rest)
        elif section == 'profil' and cur is not None:
            if key in ('nom', 'implicites', 'versioncible'):
                cur[key] = _strip_val(rest)
    return {'general': general, 'profils': profils}


def select_profil(parsed, profile_name):
    """Choisit LE profil a emprunter. Erreur explicite si ambigu/absent (aucun choix silencieux)."""
    profils = parsed['profils']
    if not profils:
        fail("Le .dhpt modele ne contient aucun [profil] -- impossible d'emprunter une config.")
    if profile_name:
        for p in profils:
            if p.get('nom', '').strip().lower() == profile_name.strip().lower():
                return p
        noms = [p.get('nom', '?') for p in profils]
        fail(f"Profil '{profile_name}' absent du .dhpt modele. Profils disponibles : {noms}")
    if len(profils) == 1:
        return profils[0]
    noms = [p.get('nom', '?') for p in profils]
    fail(f"Le .dhpt modele contient {len(profils)} profils : {noms}. "
         f'Preciser lequel emprunter avec --profile "<nom>".')


def generate_dhpt(objet_dir, borrowed):
    """Genere le `.dhpt` du harness a partir de la config EMPRUNTEE.

    borrowed = {util, progexec, cheminbases, profil_nom, implicites, versioncible}.
    repobjet/repobjetsurcharge -> objet_dir (JETABLE). [communs] laisse VIDE.
    """
    now = datetime.now().strftime("%Y%m%d%H%M%S") + "000099"
    g = borrowed
    lines = ['xwin-projet        2.0', '[general]', 'nom="harness"']
    if g.get('progexec'):
        lines.append(f'progexec="{g["progexec"]}"')
    lines.append(f'date="{now}"')
    if g.get('util'):
        lines.append(f'util="{g["util"]}"')
    if g.get('cheminbases'):
        lines.append(f'cheminbases="{g["cheminbases"]}"')
    lines += [
        '[profildefaut]',
        '[profil]',
        f'nom="{g["profil_nom"]}"',
        f'repobjet="{objet_dir}"',
        f'repobjetsurcharge="{objet_dir}"',
        f'implicites="{g["implicites"]}"',
    ]
    if g.get('versioncible'):
        lines.append(f'versioncible="{g["versioncible"]}"')
    # PAS de section [communs] : un harness isole n'a pas de module commun. NB : une
    # section `[communs]` presente mais VIDE est REFUSEE par xwin7 ("Parametre manquant /
    # Mot: nom" -- il exige `nom=` juste apres l'en-tete) ; on l'OMET donc entierement.
    # Un source qui aurait besoin d'un commun n'est pas isolable -> compiler via le vrai .dhpt.
    lines += [
        '[sousprojets]',
        'fic="harness.dhps"," "',
        '[projetsfusion]',
        '[fabricationmere]',
        '[autres]',
    ]
    return '\n'.join(lines)


def generate_dhps(source_basenames, with_zdiva, util):
    """Genere le `.dhps` du harness (liste des sources a compiler)."""
    now = datetime.now().strftime("%Y%m%d%H%M%S") + "000099"
    lines = ['xwin-sprojet       2.0', '[general]', f'date="{now}"']
    if util:
        lines.append(f'util="{util}"')
    lines += ['[communs]', '[fichiers]']
    for basename in source_basenames:
        lines.append(f'fic="{basename}"," "')
    lines.append('[includes]')
    if with_zdiva:
        lines.append('fic="zdiva.dhsp"')
    lines.append('[autres]')
    return '\n'.join(lines)


def main():
    # Sortie UTF-8 : les valeurs empruntees (profil "developpement" avec accent, implicite...)
    # casseraient un json.loads(utf-8) cote appelant sous cp1252. Meme garde-fou que compile_project.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
            _stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Genere un harness standalone (dernier recours) qui EMPRUNTE sa config a un .dhpt reel."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--source",
        help="Chemin d'un fichier .dhsp/.dhsq a compiler"
    )
    source_group.add_argument(
        "--sources", nargs='+',
        help="Chemins de plusieurs fichiers .dhsp/.dhsq a compiler ensemble"
    )
    parser.add_argument(
        "--from-dhpt", required=True,
        help=("Chemin d'un .dhpt REEL du workspace dont on emprunte la config (profil, "
              "implicite, util, progexec, cheminbases). Typiquement celui identifie par "
              "understanding-integrator-workspace. OBLIGATOIRE : pas de config poste en dur.")
    )
    parser.add_argument(
        "--profile",
        help="Nom du profil a emprunter dans --from-dhpt (obligatoire si le .dhpt en declare plusieurs)."
    )
    parser.add_argument(
        "--with-zdiva", action="store_true",
        help="Inclure zdiva.dhsp dans les includes du .dhps"
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Repertoire de sortie (3 sous-dossiers crees : objet, projet, log)"
    )
    args = parser.parse_args()

    # 1. Emprunter la config au .dhpt modele
    from_dhpt = os.path.abspath(args.from_dhpt)
    if not os.path.isfile(from_dhpt):
        fail(f"--from-dhpt introuvable : {from_dhpt}")
    if not from_dhpt.lower().endswith('.dhpt'):
        fail(f"--from-dhpt doit etre un .dhpt (recu : {os.path.splitext(from_dhpt)[1]})")

    parsed = parse_dhpt(from_dhpt)
    profil = select_profil(parsed, args.profile)
    if not profil.get('nom'):
        fail("Le [profil] emprunte du .dhpt modele ne declare pas de nom= -- "
             "impossible d'emprunter un profil sans nom (modele malforme ?).")
    if not profil.get('implicites'):
        fail(f"Le profil '{profil.get('nom', '?')}' du .dhpt modele ne declare pas d'implicites= -- "
             f"c'est le champ CRITIQUE pour resoudre includes et dictionnaires. "
             f"Emprunter un profil qui en declare un.")

    borrowed = {
        'util': parsed['general'].get('util'),
        'progexec': parsed['general'].get('progexec'),
        'cheminbases': parsed['general'].get('cheminbases'),
        'profil_nom': profil['nom'],
        'implicites': profil['implicites'],
        'versioncible': profil.get('versioncible'),
    }

    # 2. Resoudre les chemins de sortie
    output_dir = os.path.abspath(args.output_dir)
    objet_dir = os.path.join(output_dir, SUB_OBJET)
    projet_dir = os.path.join(output_dir, SUB_PROJET)
    log_dir = os.path.join(output_dir, SUB_LOG)

    # 3. Verifier les sources
    source_paths = args.sources if args.sources else [args.source]
    sources = []
    for src in source_paths:
        src = os.path.abspath(src)
        if not os.path.exists(src):
            fail(f"fichier source introuvable : {src}")
        if not src.lower().endswith(VALID_EXTENSIONS):
            fail(f"extension attendue .dhsp/.dhsq, recu : {os.path.splitext(src)[1]}")
        sources.append(src)
    source_basenames = [os.path.basename(s) for s in sources]

    # 4. Creer les repertoires + copier les sources dans le repobjet jetable
    for d in (objet_dir, projet_dir, log_dir):
        os.makedirs(d, exist_ok=True)
    source_copies = []
    for src in sources:
        dest = os.path.join(objet_dir, os.path.basename(src))
        shutil.copy2(src, dest)
        source_copies.append(dest)

    # 5. Generer les fichiers du harness (ISO-8859-1)
    dhpt_path = os.path.join(projet_dir, "harness.dhpt")
    dhps_path = os.path.join(objet_dir, "harness.dhps")
    write_iso(dhpt_path, generate_dhpt(objet_dir, borrowed))
    write_iso(dhps_path, generate_dhps(source_basenames, args.with_zdiva, borrowed['util']))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"harness_{ts}.txt")

    # Le harness ne compile PAS lui-meme : il delegue a compile_project.py (voie unique,
    # verdict-aware, gere le profil accentue + cwd + resolution user). On retourne le profil emprunte.
    next_cmd = (
        f'py compile_project.py --project "{dhpt_path}" '
        f'--profile "{borrowed["profil_nom"]}" --log-path "{log_path}" --action buildall'
    )

    result = {
        "dhpt": dhpt_path,
        "dhps": dhps_path,
        "source_copies": source_copies,
        "objet_dir": objet_dir,
        "borrowed_profile": borrowed['profil_nom'],
        "borrowed_from": from_dhpt,
        "next": next_cmd,
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
