#!/usr/bin/env python3
"""extract_entity.py -- Extrait les structures techniques d'une entite ERP.

Sources (toutes passees en CLI, aucune ref en dur) :
- `--sql-schema` : JSON columns issu d'un export du schema SQL Server
  Format : {table, database, refreshed, column_count, columns[{name,type,length,nullable,ordinal}]}
- `--sql-indexes` : JSON indexes (optionnel)
  Format : {table, indexes[{name,columns[],unique,primary}]}
- `--dict` : chemin .dhsd (optionnel, pour reference dans meta)

Produit un YAML partiel conforme a schemas/entity.yaml, couche technical renseignee,
couche business laissee pour enrichissement humain au CP3.

Usage :
  py extract_entity.py --entity CLI --module DAV --base GTFPCF \\
     --sql-schema {CHEMIN_SCHEMA_SQL}/columns/CLI.json \\
     --sql-indexes {CHEMIN_SCHEMA_SQL}/indexes/CLI.json \\
     --output {REPERTOIRE_SORTIE}/doc-erp/DAV/entity/CLI.partial.yaml
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERREUR : pyyaml requis. Installer avec : py -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# Audit canonique DIVA (cf. docs/DICTIONNAIRE-DHSD.md) -- detecte dans la liste des champs
AUDIT_FIELD_NAMES = {
    "Ce1", "Dos", "UserCr", "UserMo", "UserCrDh", "UserMoDh", "Filler",
    # variantes en majuscules utilisees en SQL
    "CE1", "DOS", "USERCR", "USERMO", "USERCRDH", "USERMODH", "FILLER",
}


def sql_to_nature(sql_type: str, length) -> str:
    """Devine une Nature DIVA approximative depuis un type SQL.

    Imparfait : le .dhsd est la source de verite pour les Natures.
    Cette heuristique fournit un point de depart a corriger au CP3.
    """
    if not sql_type:
        return "?"
    t = sql_type.lower().strip()
    if t in ("int", "integer", "bigint"):
        return "N4"
    if t in ("smallint", "tinyint"):
        return "N2"
    if t in ("char", "varchar", "nchar", "nvarchar") and length:
        return f"C{length}"
    if t in ("char", "varchar", "nchar", "nvarchar"):
        return "C?"
    if t in ("decimal", "numeric", "float", "real"):
        return "F?"
    if t in ("datetime", "datetime2", "smalldatetime"):
        return "DH"
    if t == "date":
        return "D8"
    if t == "bit":
        return "L"
    if t in ("text", "ntext"):
        return "TX"
    return f"?{sql_type}"


def infer_layer(field_name: str) -> str:
    """Couche par defaut pour un champ, a affiner manuellement."""
    name = field_name.lower()
    if field_name in AUDIT_FIELD_NAMES or name in ("filler",):
        return "technical-only"
    if name.startswith("u-") or name.startswith("u_") or name == "filler":
        return "technical-only"
    if name.endswith("_id"):
        return "technical-only"  # ID technique, pas pertinent en couche schema
    return "all"


def build_fields(columns: list) -> list:
    """Transforme la liste des colonnes SQL en entries `field` YAML."""
    fields = []
    for col in columns:
        name = col.get("name", "")
        sql_type = col.get("type", "")
        length = col.get("length")
        nullable = col.get("nullable", True)
        # formatage SQL lisible
        if length and sql_type.lower() in ("char", "varchar", "nchar", "nvarchar"):
            sql_display = f"{sql_type}({length})"
        else:
            sql_display = sql_type
        fields.append({
            "name": name,
            "nature": sql_to_nature(sql_type, length),
            "sql_type": sql_display,
            "nullable": bool(nullable),
            "layer": infer_layer(name),
        })
    return fields


def build_indexes(indexes_data: dict) -> list:
    """Transforme la liste des indexes SQL en entries `index` YAML."""
    if not indexes_data:
        return []
    out = []
    for idx in indexes_data.get("indexes", []):
        out.append({
            "name": idx.get("name", ""),
            "fields": list(idx.get("columns", [])),
            "unique": bool(idx.get("unique", False)),
            "purpose": "Cle primaire" if idx.get("primary") else "",
        })
    return out


def detect_audit_fields(columns: list) -> list:
    names = {c.get("name") for c in columns}
    return sorted(n for n in AUDIT_FIELD_NAMES if n in names)


def build_entity(args) -> dict:
    sql_schema_path = Path(args.sql_schema)
    if not sql_schema_path.exists():
        print(f"ERREUR : sql-schema introuvable : {sql_schema_path}", file=sys.stderr)
        sys.exit(1)
    with sql_schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)

    indexes_data = None
    if args.sql_indexes:
        idx_path = Path(args.sql_indexes)
        if idx_path.exists():
            with idx_path.open(encoding="utf-8") as f:
                indexes_data = json.load(f)
        else:
            print(f"WARN : sql-indexes introuvable, ignore : {idx_path}", file=sys.stderr)

    columns = schema.get("columns", [])
    entity = {
        "kind": "entity",
        "code": args.entity,
        "label": args.label or args.entity,
        "module": args.module,
        "base": args.base,
        "status": "draft",
        "business": {
            "role": "[A ENRICHIR] Decrire le role metier de l'entite en 2-3 phrases",
            "criticality": "[A ENRICHIR] core | standard | peripheral",
        },
        "schema": {
            "primary_table": schema.get("table", args.entity),
            "primary_key": [],  # rempli ci-dessous si detecte
            "relations": [],     # rempli par extract_relations.py
        },
        "technical": {
            "dictionary_source": args.dict if args.dict else "[A VERIFIER]",
            "record_name": args.entity,
            "field_count": len(columns),
            "fields": build_fields(columns),
            "indexes": build_indexes(indexes_data),
            "audit_fields": detect_audit_fields(columns),
        },
        "meta": {
            "last_reviewed": date.today().isoformat(),
            "reviewed_by": "extract_entity.py (auto)",
            "a_verifier": [
                "Enrichir section business (role, criticality, processes, rules, examples)",
                "Corriger les Natures marquees '?' ou 'C?' depuis le .dhsd",
                "Valider primary_key (vide par defaut, a deduire des indexes unique)",
                "Definir layer par champ (actuellement heuristique sur audit/ID)",
            ],
            "source_sql_schema": str(sql_schema_path),
        },
    }

    # deduire primary_key depuis l'index primary si present
    if indexes_data:
        for idx in indexes_data.get("indexes", []):
            if idx.get("primary"):
                entity["schema"]["primary_key"] = list(idx.get("columns", []))
                break

    return entity


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entity", required=True, help="Code entite, ex: CLI")
    ap.add_argument("--module", required=True, help="Code module parent, ex: DAV")
    ap.add_argument("--base", required=True, help="Code base parente, ex: GTFPCF")
    ap.add_argument("--sql-schema", required=True, help="Chemin JSON columns de l'entite")
    ap.add_argument("--sql-indexes", help="Chemin JSON indexes de l'entite (optionnel)")
    ap.add_argument("--dict", help="Chemin .dhsd (optionnel, pour reference dans meta)")
    ap.add_argument("--label", help="Label lisible (defaut : code entite)")
    ap.add_argument("--output", required=True, help="Chemin YAML de sortie")
    args = ap.parse_args()

    entity = build_entity(args)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(entity, f, allow_unicode=True, sort_keys=False, width=120)

    summary = {
        "entity": args.entity,
        "output": str(out),
        "field_count": entity["technical"]["field_count"],
        "index_count": len(entity["technical"]["indexes"]),
        "audit_fields_detected": entity["technical"]["audit_fields"],
        "primary_key": entity["schema"]["primary_key"],
        "a_verifier_count": len(entity["meta"]["a_verifier"]),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
