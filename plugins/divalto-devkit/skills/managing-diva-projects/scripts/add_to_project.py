#!/usr/bin/env python3
"""Ajoute un .dhps dans la section [sousprojets] d'un .dhpt existant.

Lit le .dhpt, verifie que le sous-projet n'est pas deja reference,
et produit le contenu mis a jour.

En-tetes .dhpt acceptes :
- `xwin-projet 2.0` (projet standard)
- `xwin-s-projet 2.0` (projet de surcharge)

Garde-fou surcharge : une .dhps de surcharge (suffixe `u.dhps`) ne doit
PAS etre listee dans [sousprojets] -- xwin7 leve "ne peut etre charge
directement". Le script refuse l'ajout dans ce cas.

Usage :
    py add_to_project.py --dhpt chemin.dhpt --dhps "gt_zoom article.dhps"
    py add_to_project.py --dhpt chemin.dhpt --dhps "gt_zoom article.dhps" --output updated.dhpt

Sortie JSON (stdout) :
    {
        "dhpt": "chemin.dhpt",
        "dhps_added": "gt_zoom article.dhps",
        "already_present": false,
        "total_subprojects": 42,
        "output": "updated.dhpt"
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


def is_surcharge_dhps(dhps_name):
    """Detecte une .dhps de surcharge via la convention de nommage.

    xwin7 fait une auto-detection : `<nom>u.dhps` dans le repertoire `projets/`
    surcharge automatiquement `<nom>.dhps` du standard via `cheminbases`.
    La .dhps de surcharge ne doit PAS etre listee dans [sousprojets] sinon
    xwin7 leve "ne peut etre charge directement" (cf. anti-pattern P17).

    `gt_zoom articleu.dhps` -> True
    `gt_zoom article.dhps`  -> False
    """
    stem = os.path.splitext(dhps_name)[0]
    return stem.endswith("u")


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

    # Garde-fou P17 : refuser une .dhps de surcharge (suffixe `u`).
    # Elle est auto-detectee par xwin7 via `cheminbases`, l'ajouter dans
    # [sousprojets] casse la compilation ("ne peut etre charge directement").
    if is_surcharge_dhps(dhps_name):
        return {
            "error": (
                f"{dhps_name} est une .dhps de surcharge (suffixe 'u'). "
                f"xwin7 la detecte automatiquement via cheminbases : elle ne "
                f"doit PAS etre listee dans [sousprojets] du .dhpt parent "
                f"(anti-pattern P17). Aucune modification appliquee."
            )
        }

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

    return {
        "dhpt": dhpt_path,
        "dhps_added": dhps_name,
        "already_present": False,
        "total_subprojects": len(existing) + 1,
        "output": target
    }


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
