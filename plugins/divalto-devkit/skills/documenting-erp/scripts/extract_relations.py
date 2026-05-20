#!/usr/bin/env python3
"""extract_relations.py -- Extrait les relations inter-entites d'une entite.

Strategies disponibles :
- heuristic : scan du nom des champs (DOS -> SOC, ETB -> ETS, CPT -> C3, ...)
- neo4j    : requete diva-mcp (non implemente MVP, renvoie liste vide)
- code     : scan du code X.13 pour Zoom/OverWrittenBy (non implemente MVP)

Pour le MVP : strategie heuristic uniquement, a completer au CP3 par le collaborateur
en consultant les f8= et table_associee des masques .dhsf X.13.

Usage :
  py extract_relations.py --entity CLI --sql-schema {CHEMIN_SCHEMA_SQL}/columns/CLI.json \\
     --output {REPERTOIRE_SORTIE}/doc-erp/DAV/relation/CLI.partial.yaml
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERREUR : pyyaml requis. Installer : py -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# Heuristiques deterministes : nom de champ -> entite cible probable.
# A confirmer/corriger manuellement via les f8= des masques .dhsf X.13 et
# les declarations Record dans les modules .dhsp.
FIELD_TO_ENTITY_HINT = {
    "DOS": "SOC",
    "ETB": "ETS",
    "CPT": "C3",
    "TIERS": None,         # cle metier, pas une FK vers une autre entite
    "ART": "ART",
    "FOU": "FOU",
    "CLI": "CLI",
    "REGL": None,          # table de codes, pas une entite
    "DEV": "DEVISE",       # [A VERIFIER]
    "PAY": "PAYS",         # [A VERIFIER]
    "VRP": "VRP",
    "LANG": "LANGUE",      # [A VERIFIER]
    "TVA": "TVA",
}


def infer_relations(entity_code: str, columns: list) -> list:
    """Genere des relations heuristiques depuis le nom des champs."""
    relations = []
    seen = set()
    for col in columns:
        name = col.get("name", "")
        target = FIELD_TO_ENTITY_HINT.get(name)
        if target and target != entity_code and target not in seen:
            seen.add(target)
            relations.append({
                "source_entity": entity_code,
                "target_entity": target,
                "type": "fk",
                "cardinality": "N-1",
                "source_field": name,
                "business_note": f"[A VERIFIER] FK heuristique basee sur le nom de champ '{name}'",
            })
    return relations


def build_relations_file(args) -> dict:
    columns = []
    if args.sql_schema:
        p = Path(args.sql_schema)
        if p.exists():
            with p.open(encoding="utf-8") as f:
                columns = json.load(f).get("columns", [])
        else:
            print(f"WARN : sql-schema introuvable : {p}", file=sys.stderr)

    relations = []
    if args.source == "heuristic":
        relations = infer_relations(args.entity, columns)
    elif args.source == "neo4j":
        print("INFO : source=neo4j non implementee en MVP, renvoie liste vide", file=sys.stderr)
    elif args.source == "code":
        print("INFO : source=code non implementee en MVP, renvoie liste vide", file=sys.stderr)

    return {
        "kind": "relations",
        "entity": args.entity,
        "source": args.source,
        "relations": relations,
        "a_verifier": [
            "Chaque relation heuristique doit etre confirmee via graphe Neo4j ou code source",
            "Preciser cardinality exacte (N-1 par defaut, 1-N a verifier)",
            "Ajouter les zooms reels depuis les .dhsf et les Module Check",
        ] if relations else [],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entity", required=True, help="Code entite source")
    ap.add_argument("--sql-schema", help="Chemin JSON columns pour heuristique (recommande)")
    ap.add_argument("--source", choices=["heuristic", "neo4j", "code"], default="heuristic",
                    help="Source de detection (defaut : heuristic)")
    ap.add_argument("--output", required=True, help="Chemin YAML de sortie")
    args = ap.parse_args()

    data = build_relations_file(args)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=120)

    summary = {
        "entity": args.entity,
        "source": args.source,
        "output": str(out),
        "relations_count": len(data["relations"]),
        "targets": [r["target_entity"] for r in data["relations"]],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
