#!/usr/bin/env python3
"""Calcule l'ensemble complet des tokens de nommage pour une entite DIVA.

Usage:
    py .claude/skills/naming-diva-entities/scripts/compute_names.py \
        --domaine DAV --entite Livre --nomrecordsql LivreRS \
        --champ-cle CodeLivre --description "Livre"

Parametres:
    --entite    : nom de l'entite = nom de la table dictionnaire = nom de la table SQL
    --nomrecordsql : nom du RecordSQL (ex: LivreRS, Article, RtlFamRglt)

Sortie JSON: tous les tokens de SQUELETTES.md
Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import sys

from _naming import compute_names


def main():
    parser = argparse.ArgumentParser(
        description="Calcule les tokens de nommage pour une entite DIVA"
    )
    parser.add_argument("--domaine", required=True,
                        help="Nom du domaine (ex: DAV, Retail, Production)")
    parser.add_argument("--entite", required=True,
                        help="Nom de l'entite/table dictionnaire/table SQL en PascalCase (ex: Livre, FamRglt)")
    parser.add_argument("--nomrecordsql", required=True,
                        help="Nom du RecordSQL (ex: LivreRS, Article, RtlFamRglt)")
    parser.add_argument("--champ-cle", required=True,
                        help="Champ cle primaire (ex: CodeLivre, RgltFam)")
    parser.add_argument("--description", required=True,
                        help="Description metier (ex: Livre, Famille de reglement)")
    parser.add_argument("--no-libelle", action="store_true",
                        help="La table n'a pas de champ Libelle")
    parser.add_argument("--champ-libelle", default="Libelle",
                        help="Nom du champ libelle (defaut: Libelle ; "
                             "utiliser Lib si Nature=40)")

    args = parser.parse_args()

    tokens, error = compute_names(
        domaine=args.domaine,
        entite=args.entite,
        table_sql=args.entite,
        champ_cle=args.champ_cle,
        description=args.description,
        nom_vue_override=args.nomrecordsql,
        has_libelle=not args.no_libelle,
        champ_libelle=args.champ_libelle,
    )

    if error:
        print(error, file=sys.stderr)
        sys.exit(1)

    json.dump(tokens, sys.stdout, indent=2, ensure_ascii=False)
    print()  # newline finale


if __name__ == "__main__":
    main()
