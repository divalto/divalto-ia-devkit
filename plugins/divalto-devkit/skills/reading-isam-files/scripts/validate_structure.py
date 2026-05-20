#!/usr/bin/env python3
"""Valide un fichier de structure JSON pour l'ecriture ISAM.

Usage:
    py .claude/skills/writing-isam-files/scripts/validate_structure.py --path structure_m4.json

Sortie JSON:
    {valid: bool, errors: [str], fields: int, record_size: int}

Exit codes:
    0 = structure valide
    1 = structure invalide (erreurs de validation)
    2 = fichier introuvable ou JSON illisible
"""

import argparse
import json
import sys


REQUIRED_KEYS = {"Dictionnaire", "Table", "Base", "TailleEnreg", "Structure"}
REQUIRED_FIELD_KEYS = {"Nom", "Offset", "Taille"}


def validate(data):
    """Valide la structure et retourne une liste d'erreurs."""
    errors = []

    # Cles obligatoires
    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        errors.append(f"Cles manquantes : {', '.join(sorted(missing))}")
        return errors  # pas la peine de continuer

    # TailleEnreg
    taille = data["TailleEnreg"]
    if not isinstance(taille, int) or taille <= 0:
        errors.append(f"TailleEnreg doit etre un entier positif (recu : {taille!r})")
        return errors

    # Structure
    structure = data["Structure"]
    if not isinstance(structure, list) or len(structure) == 0:
        errors.append("Structure doit etre un tableau non vide")
        return errors

    # Champs individuels
    noms_vus = set()
    for i, field in enumerate(structure):
        prefix = f"Structure[{i}]"

        if not isinstance(field, dict):
            errors.append(f"{prefix} : doit etre un objet")
            continue

        field_missing = REQUIRED_FIELD_KEYS - set(field.keys())
        if field_missing:
            errors.append(f"{prefix} : cles manquantes {', '.join(sorted(field_missing))}")
            continue

        nom = field["Nom"]
        offset = field["Offset"]
        taille_champ = field["Taille"]

        # Types
        if not isinstance(nom, str) or not nom:
            errors.append(f"{prefix} : Nom doit etre une chaine non vide")
            continue

        if not isinstance(offset, int) or offset < 0:
            errors.append(f"{prefix} ({nom}) : Offset doit etre un entier >= 0 (recu : {offset!r})")

        if not isinstance(taille_champ, int) or taille_champ <= 0:
            errors.append(f"{prefix} ({nom}) : Taille doit etre un entier > 0 (recu : {taille_champ!r})")
            continue

        # Depassement
        if isinstance(offset, int) and offset >= 0:
            if offset + taille_champ > taille:
                errors.append(
                    f"{prefix} ({nom}) : depasse TailleEnreg "
                    f"(offset {offset} + taille {taille_champ} = {offset + taille_champ} > {taille})"
                )

        # Unicite
        if nom in noms_vus:
            errors.append(f"{prefix} ({nom}) : nom en double")
        noms_vus.add(nom)

    return errors


def main():
    parser = argparse.ArgumentParser(description="Valide un fichier de structure ISAM JSON")
    parser.add_argument("--path", required=True, help="Chemin vers le fichier structure JSON")
    args = parser.parse_args()

    # Charger le fichier
    try:
        with open(args.path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Fichier introuvable : {args.path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"JSON invalide : {e}", file=sys.stderr)
        sys.exit(2)

    # Valider
    errors = validate(data)
    fields = len(data.get("Structure", []))
    record_size = data.get("TailleEnreg", 0)

    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "fields": fields,
        "record_size": record_size,
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
