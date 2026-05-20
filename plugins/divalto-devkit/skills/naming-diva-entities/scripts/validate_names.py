#!/usr/bin/env python3
"""Valide la coherence des tokens de nommage produits par compute_names.py.

Usage:
    py .claude/skills/naming-diva-entities/scripts/compute_names.py ... | \
        py .claude/skills/naming-diva-entities/scripts/validate_names.py --stdin

    py .claude/skills/naming-diva-entities/scripts/validate_names.py --file tokens.json

Sortie JSON: {valid, errors[], warnings[]}
Exit codes: 0 = succes (meme s'il y a des warnings), 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import sys


# ── Exceptions par domaine ─────────────────────────────────────────────────
# Prefixes SQL alternatifs historiques (en plus du prefix_db standard)
SQL_PREFIX_EXCEPTIONS = {
    "DAV": ["g3", "g3t"],
}

# ── Regles de validation ───────────────────────────────────────────────────

def validate_collision(tokens):
    """V01: Non-collision RecordSql / Record (ERREUR)."""
    if tokens.get("collision_detected"):
        return {
            "rule": "V01",
            "severity": "error",
            "message": (
                f"Collision NomVue/TableSQL : '{tokens['NomVue']}' est identique "
                f"(case-insensitive) a '{tokens['TableSQL']}'. "
                f"Utiliser --nom-vue pour fournir un nom alternatif."
            ),
        }
    return None


def validate_pascal_case(tokens):
    """V02: NomVue doit etre en PascalCase (ERREUR)."""
    nom_vue = tokens.get("NomVue", "")
    if not nom_vue or not nom_vue[0].isupper():
        return {
            "rule": "V02",
            "severity": "error",
            "message": f"NomVue '{nom_vue}' doit commencer par une majuscule (PascalCase).",
        }
    if "_" in nom_vue or " " in nom_vue:
        return {
            "rule": "V02",
            "severity": "error",
            "message": f"NomVue '{nom_vue}' ne doit pas contenir d'underscores ni d'espaces.",
        }
    return None


def validate_entite_pascal_case(tokens):
    """V03: entity doit etre en PascalCase (ERREUR)."""
    entite = tokens.get("entity", "")
    if not entite or not entite[0].isupper():
        return {
            "rule": "V03",
            "severity": "error",
            "message": f"Entite '{entite}' doit commencer par une majuscule (PascalCase).",
        }
    return None


def validate_champ_cle_pascal_case(tokens):
    """V04: ChampCle doit etre en PascalCase (ERREUR)."""
    champ = tokens.get("ChampCle", "")
    if not champ or not champ[0].isupper():
        return {
            "rule": "V04",
            "severity": "error",
            "message": f"ChampCle '{champ}' doit commencer par une majuscule (PascalCase).",
        }
    return None


def validate_prefix_db_in_table(tokens):
    """V05: La table SQL devrait commencer par le prefixe DB (WARNING).

    Accepte les prefixes SQL alternatifs historiques par domaine
    (ex: DAV utilise 'G3' en SQL au lieu de 'gtf').
    """
    table = tokens.get("TableSQL", "").lower()
    prefix_db = tokens.get("prefix_db", "").lower()
    domaine = tokens.get("domaine", "").upper()

    if prefix_db and not table.startswith(prefix_db):
        # Verifier les exceptions par domaine
        exceptions = SQL_PREFIX_EXCEPTIONS.get(domaine, [])
        for exc_prefix in exceptions:
            if table.startswith(exc_prefix.lower()):
                return None  # Prefixe alternatif accepte

        return {
            "rule": "V05",
            "severity": "warning",
            "message": (
                f"La table '{tokens['TableSQL']}' ne commence pas par le prefixe DB "
                f"'{tokens['prefix_db']}' du domaine {tokens['domaine']}. "
                f"Verifier que la table appartient bien a ce domaine."
            ),
        }
    return None


def validate_fichier_lengths(tokens):
    """V06: Les noms de fichiers ne devraient pas depasser 40 caracteres (WARNING)."""
    issues = []
    for key in ("fichier_rsql", "fichier_zoom", "fichier_mchk"):
        val = tokens.get(key, "")
        if len(val) > 40:
            issues.append({
                "rule": "V06",
                "severity": "warning",
                "message": (
                    f"Nom de fichier '{val}' ({key}) fait {len(val)} caracteres "
                    f"(max recommande: 40)."
                ),
            })
    return issues


def validate_base_not_empty(tokens):
    """V07: base ne doit pas etre vide (ERREUR)."""
    base = tokens.get("base", "")
    if not base:
        return {
            "rule": "V07",
            "severity": "error",
            "message": "Le nom de base derive est vide. Verifier le nom de table et le prefixe DB.",
        }
    return None


def validate_description_not_empty(tokens):
    """V08: description ne doit pas etre vide (ERREUR)."""
    desc = tokens.get("Description", "")
    if not desc or not desc.strip():
        return {
            "rule": "V08",
            "severity": "error",
            "message": "La description est vide. Fournir une description metier.",
        }
    return None


def validate_consistency(tokens):
    """V09: Coherence interne des tokens derives (ERREUR)."""
    issues = []

    # TABLE_MAJUSCULE == TableSQL.upper()
    if tokens.get("TABLE_MAJUSCULE") != tokens.get("TableSQL", "").upper():
        issues.append({
            "rule": "V09",
            "severity": "error",
            "message": "Incoherence : TABLE_MAJUSCULE != TableSQL.upper()",
        })

    # table_minuscule == TableSQL.lower()
    if tokens.get("table_minuscule") != tokens.get("TableSQL", "").lower():
        issues.append({
            "rule": "V09",
            "severity": "error",
            "message": "Incoherence : table_minuscule != TableSQL.lower()",
        })

    # ENTITY == entity.upper()
    if tokens.get("ENTITY") != tokens.get("entity", "").upper():
        issues.append({
            "rule": "V09",
            "severity": "error",
            "message": "Incoherence : ENTITY != entity.upper()",
        })

    # CHAMPCLE == ChampCle.upper()
    if tokens.get("CHAMPCLE") != tokens.get("ChampCle", "").upper():
        issues.append({
            "rule": "V09",
            "severity": "error",
            "message": "Incoherence : CHAMPCLE != ChampCle.upper()",
        })

    return issues


def validate_tokens(tokens):
    """Execute toutes les regles de validation et retourne le rapport."""
    errors = []
    warnings = []

    # Regles simples (retournent un seul resultat ou None)
    single_rules = [
        validate_collision,
        validate_pascal_case,
        validate_entite_pascal_case,
        validate_champ_cle_pascal_case,
        # V05 supprimee : --table est un nom de table dictionnaire (pas de prefixe requis)
        validate_base_not_empty,
        validate_description_not_empty,
    ]

    for rule_fn in single_rules:
        result = rule_fn(tokens)
        if result:
            if result["severity"] == "error":
                errors.append(result)
            else:
                warnings.append(result)

    # Regles multiples (retournent une liste)
    for result in validate_fichier_lengths(tokens):
        if result["severity"] == "error":
            errors.append(result)
        else:
            warnings.append(result)

    for result in validate_consistency(tokens):
        if result["severity"] == "error":
            errors.append(result)
        else:
            warnings.append(result)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total": len(errors) + len(warnings),
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Valide les tokens de nommage d'une entite DIVA"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stdin", action="store_true",
                       help="Lire les tokens JSON depuis stdin")
    group.add_argument("--file", help="Chemin vers un fichier JSON de tokens")

    args = parser.parse_args()

    try:
        if args.stdin:
            tokens = json.load(sys.stdin)
        else:
            with open(args.file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Erreur JSON : {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Fichier non trouve : {args.file}", file=sys.stderr)
        sys.exit(1)

    report = validate_tokens(tokens)
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
