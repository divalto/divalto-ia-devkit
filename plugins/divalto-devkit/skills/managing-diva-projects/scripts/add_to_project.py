#!/usr/bin/env python3
"""Ajoute un .dhps dans la section [sousprojets] d'un .dhpt existant.

Lit le .dhpt, verifie que le sous-projet n'est pas deja reference,
et produit le contenu mis a jour.

En-tetes .dhpt acceptes :
- `xwin-projet 2.0` (projet standard)
- `xwin-s-projet 2.0` (projet de surcharge)

Garde-fou surcharge : une .dhps de surcharge ne doit PAS etre listee dans
[sousprojets] -- xwin7 leve "ne peut etre charge directement". Le script
refuse l'ajout dans ce cas. La surcharge est identifiee par son EN-TETE
(`xwin-s-sprojet`), JAMAIS par le suffixe `u` du nom de fichier : sur un
corpus reel de 2513 entrees, ce suffixe donnait 31 faux positifs et zero
vrai positif (`gt_menu.dhps`, `...bordereau.dhps`, `...individu.dhps`...),
dont 30 noms figurant dans des .dhpt du standard livre.

Usage :
    py add_to_project.py --dhpt chemin.dhpt --dhps "gt_zoom article.dhps"
    py add_to_project.py --dhpt chemin.dhpt --dhps "gt_zoom article.dhps" --output updated.dhpt

Sortie JSON (stdout) :
    {
        "dhpt": "chemin.dhpt",
        "dhps_added": "gt_zoom article.dhps",
        "already_present": false,
        "total_subprojects": 42,
        "output": "updated.dhpt",
        "warning": "... (present UNIQUEMENT si le statut de surcharge n'a pas pu etre verifie)"
    }

Exit codes :
    0 = succes
    1 = erreur utilisateur (fichier introuvable, deja present, surcharge refusee)
    2 = erreur interne
"""

import argparse
import json
import os
import re
import sys


def find_sousprojets_section(lines):
    """Trouve les indices de debut et fin de la section [sousprojets].

    Returns:
        tuple: (start_index, end_index) ou end_index est la ligne
               apres la derniere entree fic= de la section.
               None si section introuvable.
    """
    start = None
    end = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[sousprojets]":
            start = i
            continue
        if start is not None and stripped.startswith("[") and stripped.endswith("]"):
            end = i
            break

    if start is not None and end is None:
        end = len(lines)

    if start is None:
        return None

    return (start, end)


def get_existing_subprojects(lines, start, end):
    """Extrait les noms de .dhps deja references dans [sousprojets]."""
    subprojects = []
    for i in range(start + 1, end):
        line = lines[i].strip()
        match = re.match(r'^fic="([^"]+)"', line)
        if match:
            subprojects.append(match.group(1))
    return subprojects


# NB : fonction volontairement DUPLIQUEE dans validate_project.py. Les deux scripts
# sont des CLI autonomes -- un import croise casserait celui qu'on copie seul.
def surcharge_dhps(dhps_name, dhpt_path):
    """Statut de surcharge de la .dhps, d'apres son EN-TETE. Jamais d'apres son nom.

    Retourne "surcharge" (en-tete `xwin-s-sprojet`), "standard" (tout autre en-tete
    reconnu), ou "inconnu" quand le fichier est introuvable.

    xwin7 auto-detecte une .dhps de surcharge via `cheminbases` : la lister dans
    [sousprojets] casse la compilation ("ne peut etre charge directement",
    anti-pattern PROJ17). Mais le suffixe `u` du nom de fichier est une CONVENTION DE
    NOMMAGE, pas un marqueur : sur un corpus reel de 2513 entrees [sousprojets], le
    test `stem.endswith("u")` produisait **31 faux positifs et zero vrai positif** --
    il refusait `gt_menu.dhps`, `a5_menu.dhps`, `rc_cpt_bordereau.dhps`,
    `pp_zoom individu.dhps`, `...lieu.dhps`, `...fou.dhps`, soit tout mot finissant
    par `u`. Dont **30 noms figurant dans des .dhpt du standard livre** : le script
    refusait donc d'ajouter des sous-projets parfaitement legitimes.

    `inconnu` n'est pas un refus : voir add_subproject. Bloquer une operation
    legitime coute plus cher que laisser passer une surcharge, que xwin7 signalera
    au compile de facon recuperable.
    """
    cible = os.path.join(os.path.dirname(os.path.abspath(dhpt_path)),
                         os.path.basename(dhps_name))
    if not os.path.isfile(cible):
        return "inconnu"
    try:
        with open(cible, "r", encoding="iso-8859-1") as fh:
            entete = fh.readline().strip().lower()
    except OSError:
        return "inconnu"
    return "surcharge" if entete.startswith("xwin-s-sprojet") else "standard"


def add_subproject(dhpt_path, dhps_name, output_path=None):
    """Ajoute un .dhps dans [sousprojets] d'un .dhpt.

    Args:
        dhpt_path: chemin vers le .dhpt
        dhps_name: nom du .dhps a ajouter. Si un chemin relatif ou absolu
                   est fourni, seul le basename est conserve (les entrees
                   fic= dans [sousprojets] referencent le nom simple).
        output_path: chemin de sortie (None = modifier en place)

    Returns:
        dict: resultat JSON
    """
    # Extraire le nom simple : xwin7 -sousproject attend le basename
    dhps_name = os.path.basename(dhps_name)

    # Garde-fou PROJ17 : refuser une .dhps de surcharge, identifiee par son EN-TETE.
    # Elle est auto-detectee par xwin7 via `cheminbases`, l'ajouter dans
    # [sousprojets] casse la compilation ("ne peut etre charge directement").
    statut = surcharge_dhps(dhps_name, dhpt_path)
    if statut == "surcharge":
        return {
            "error": (
                f"{dhps_name} est une .dhps de surcharge (en-tete "
                f"'xwin-s-sprojet'). xwin7 la detecte automatiquement via "
                f"cheminbases : elle ne doit PAS etre listee dans [sousprojets] "
                f"du .dhpt parent (anti-pattern PROJ17). Aucune modification "
                f"appliquee."
            )
        }
    # `inconnu` = fichier introuvable a cote du .dhpt (sous-projet pas encore cree).
    # On n'a AUCUN moyen de savoir : on ajoute, et on le dit. Refuser a tort bloque
    # une operation legitime ; une surcharge reellement declaree sera signalee par
    # xwin7 au compile, ce qui est recuperable.
    avertissement = None
    if statut == "inconnu":
        avertissement = (
            f"{dhps_name} introuvable a cote du .dhpt : statut de surcharge "
            f"NON verifie (l'en-tete n'a pas pu etre lu). Si ce fichier est une "
            f"surcharge, il ne doit pas figurer dans [sousprojets] -- cf. PROJ17."
        )

    # Lire le fichier en mode binaire pour preserver CRLF + ISO-8859-1
    try:
        with open(dhpt_path, "rb") as f:
            raw = f.read()
        content = raw.decode("iso-8859-1")
    except FileNotFoundError:
        return {"error": f"Fichier introuvable : {dhpt_path}"}
    except Exception as e:
        return {"error": f"Erreur lecture : {e}"}

    lines = content.split("\r\n")

    # Verifier l'en-tete : accepter standard (xwin-projet) et surcharge (xwin-s-projet)
    header = lines[0].strip() if lines else ""
    if not (header.startswith("xwin-projet") or header.startswith("xwin-s-projet")):
        return {
            "error": (
                f"Ce fichier n'est pas un .dhpt valide : en-tete attendu "
                f"'xwin-projet' (standard) ou 'xwin-s-projet' (surcharge), "
                f"obtenu : {header!r}"
            )
        }

    # Trouver [sousprojets]
    section = find_sousprojets_section(lines)
    if section is None:
        return {"error": "Section [sousprojets] introuvable dans le .dhpt"}

    start, end = section

    # Verifier si deja present
    existing = get_existing_subprojects(lines, start, end)
    if dhps_name in existing:
        return {
            "dhpt": dhpt_path,
            "dhps_added": dhps_name,
            "already_present": True,
            "total_subprojects": len(existing),
            "output": None
        }

    # Inserer avant la section suivante, trie alphabetiquement
    # Trouver la position d'insertion (ordre alphabetique)
    insert_pos = end
    for i in range(start + 1, end):
        line = lines[i].strip()
        match = re.match(r'^fic="([^"]+)"', line)
        if match:
            existing_name = match.group(1)
            if dhps_name.lower() < existing_name.lower():
                insert_pos = i
                break
        elif line == "":
            continue
        else:
            insert_pos = i
            break

    # Si on n'a pas trouve de position, inserer a la fin de la section
    if insert_pos == end:
        # Inserer juste avant la section suivante
        insert_pos = end

    new_line = f'fic="{dhps_name}"," "'
    lines.insert(insert_pos, new_line)

    # Ecrire le resultat en mode binaire pour preserver CRLF + ISO-8859-1
    new_content = "\r\n".join(lines)
    target = output_path or dhpt_path

    try:
        with open(target, "wb") as f:
            f.write(new_content.encode("iso-8859-1"))
    except Exception as e:
        return {"error": f"Erreur ecriture : {e}"}

    resultat = {
        "dhpt": dhpt_path,
        "dhps_added": dhps_name,
        "already_present": False,
        "total_subprojects": len(existing) + 1,
        "output": target
    }
    if avertissement:
        resultat["warning"] = avertissement
    return resultat


def main():
    parser = argparse.ArgumentParser(
        description="Ajoute un .dhps dans [sousprojets] d'un .dhpt"
    )
    parser.add_argument(
        "--dhpt", required=True,
        help="Chemin du fichier .dhpt"
    )
    parser.add_argument(
        "--dhps", required=True,
        help="Nom du fichier .dhps a ajouter (ex: 'gt_zoom article.dhps')"
    )
    parser.add_argument(
        "--output", default=None,
        help="Fichier de sortie (modifie en place si omis)"
    )
    args = parser.parse_args()

    result = add_subproject(args.dhpt, args.dhps, args.output)

    if "error" in result:
        print(f"Erreur : {result['error']}", file=sys.stderr)
        sys.exit(1)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    if result.get("already_present"):
        sys.exit(1)


if __name__ == "__main__":
    main()
