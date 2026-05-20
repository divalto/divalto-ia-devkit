"""
query_neo4j.py -- Produit des requetes Cypher parametrees (mode generate) ou consolide
les resultats bruts du MCP diva-mcp (mode consolidate).

N'invoque jamais le MCP directement : c'est la responsabilite de l'orchestrateur LLM
(principe "scripts pour determinisme, LLM pour appels MCP").

Le graphe Neo4j est un snapshot X.12 -- tous les resultats portent un disclaimer
"source: diva-mcp-x12, status: X.12" jusqu'a verification par searching-erp-sources.

Couche "query" du pipeline d'analyse pre-action (parse / query / verify).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates" / "queries"

# --- Chargement des templates --------------------------------------------


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / f"{name}.cypher"
    if not path.exists():
        raise FileNotFoundError(f"Template Cypher introuvable : {path}")
    return path.read_text(encoding="utf-8")


def render_template(name: str, **params) -> str:
    """Remplace $var par les valeurs fournies. Echappement simple des quotes."""
    tpl = load_template(name)
    for key, value in params.items():
        safe = str(value).replace("'", "\\'") if isinstance(value, str) else value
        tpl = tpl.replace(f"${key}", str(safe))
    return tpl


# --- Mode generate -------------------------------------------------------


def _is_upper_table_name(token: str) -> bool:
    return token.isupper() and len(token) >= 3 and token.isalpha()


def _is_pascal_case(token: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][a-z]+(?:[A-Z][a-z]+)+", token))


def generate_queries(request: dict) -> list[dict]:
    """Selectionne les templates pertinents et produit les requetes Cypher."""
    queries: list[dict] = []

    # 1. by_keyword : un appel par keyword technique (max 5 pour borner le volume)
    for kw in request.get("keywords_techniques", [])[:5]:
        queries.append({
            "template": "by_keyword",
            "parameter": kw,
            "cypher": render_template("by_keyword", keyword=kw),
        })

    # 2. by_module : si domaine_pressenti identifie
    domaine = request.get("domaine_pressenti")
    if domaine:
        queries.append({
            "template": "by_module",
            "parameter": domaine,
            "cypher": render_template("by_module", module_prefix=domaine),
        })

    # 3. accesses_table : pour chaque nom en MAJUSCULE dans donnees (likely table name)
    for d in request.get("donnees", []):
        if _is_upper_table_name(d):
            queries.append({
                "template": "accesses_table",
                "parameter": d,
                "cypher": render_template("accesses_table", table_name=d),
            })

    # 4. callers_of + dynamic_callers_of + xmt_callers_of : pour chaque PascalCase
    #    dans keywords_techniques (likely function). Les trois relations (CALLS, DYNAMIC_CALL,
    #    XMT_CALL) couvrent les invocations statiques, dynamiques et transactionnelles.
    for kw in request.get("keywords_techniques", [])[:3]:
        if _is_pascal_case(kw):
            for tpl in ("callers_of", "dynamic_callers_of", "xmt_callers_of"):
                queries.append({
                    "template": tpl,
                    "parameter": kw,
                    "cypher": render_template(tpl, function_name=kw),
                })

    # 5. similar_entity : pour chaque PascalCase dans donnees (likely entity/table name)
    for d in request.get("donnees", [])[:3]:
        if _is_pascal_case(d) or _is_upper_table_name(d):
            queries.append({
                "template": "similar_entity",
                "parameter": d,
                "cypher": render_template("similar_entity", entity_pattern=d),
            })

    return queries


# --- Mode consolidate ----------------------------------------------------


def _base_disclaimers() -> list[str]:
    return [
        "Snapshot X.12 du standard ERP -- ne reflete pas X.13",
        "Toute recommandation d'action doit etre verifiee par searching-erp-sources",
    ]


def consolidate(results_by_key: dict, neo4j_status: str = "ok") -> dict:
    """Fusionne les resultats bruts en candidates_x12.json.

    results_by_key : cles de forme `<template>:<parameter>`, valeurs = liste de rows Neo4j.
    """
    candidates = {
        "neo4j_status": neo4j_status,
        "disclaimers": _base_disclaimers(),
        "programs": [],
        "functions": [],
        "tables": [],
        "entities": [],
        "relations": {"callers_of": [], "accesses": []},
        "query_trace": [],
    }

    if neo4j_status != "ok":
        candidates["disclaimers"].append(
            f"Neo4j status = {neo4j_status}. La phase de verification X.13 devient "
            "source principale (searching-erp-sources en mode direct).")
        return candidates

    # Index pour deduplication / scoring
    programs: dict[str, dict] = {}
    functions: dict[str, dict] = {}
    tables: dict[str, dict] = {}
    entities: dict[str, dict] = {}
    callers: list[dict] = []
    accesses: list[dict] = []

    for key, rows in results_by_key.items():
        template, _, parameter = key.partition(":")
        candidates["query_trace"].append({
            "template": template, "parameter": parameter, "row_count": len(rows)
        })

        for row in rows:
            # Convention : les rows Neo4j exposent des proprietes selon la requete.
            # On tente plusieurs noms de champ communs pour chaque categorie.
            name = row.get("name") or row.get("program_name") or row.get("p_name")
            domain = row.get("domain") or row.get("module") or row.get("m_name")

            if template in ("by_keyword", "by_module") and name:
                if name not in programs:
                    programs[name] = {
                        "name": name, "domain": domain, "score": 0,
                        "source": "diva-mcp-x12", "status": "X.12",
                    }
                programs[name]["score"] += 1

            if template in ("callers_of", "dynamic_callers_of", "xmt_callers_of"):
                # Tolerant aux variations de cle : caller_name / caller_function / caller / c_name
                caller = (row.get("caller_name") or row.get("caller_function")
                          or row.get("caller") or row.get("c_name"))
                callee = (row.get("callee_name") or row.get("callee_function")
                          or row.get("callee") or parameter)
                caller_prog = (row.get("program_name") or row.get("caller_program")
                               or row.get("p_name"))
                call_kind = {
                    "callers_of": "static",
                    "dynamic_callers_of": "dynamic",
                    "xmt_callers_of": "xmt",
                }[template]
                if caller:
                    if caller not in functions:
                        functions[caller] = {
                            "name": caller, "program": caller_prog,
                            "score": 0, "source": "diva-mcp-x12", "status": "X.12",
                        }
                    functions[caller]["score"] += 1
                    # Aussi ajouter le callee comme function candidate (c'est souvent
                    # le plus pertinent -- ex : select_sumpcentsituation pour un controle
                    # de somme, devis_travaux_controle_existence_situation pour un controle
                    # d'existence).
                    if callee and callee not in functions:
                        functions[callee] = {
                            "name": callee, "program": None,
                            "score": 0, "source": "diva-mcp-x12-callee", "status": "X.12",
                        }
                    if callee in functions:
                        functions[callee]["score"] += 1
                    entry = {
                        "caller": caller, "callee": callee,
                        "caller_program": caller_prog, "status": "X.12",
                        "call_kind": call_kind,
                    }
                    if call_kind == "xmt" and row.get("xmt_function"):
                        entry["xmt_function"] = row.get("xmt_function")
                    callers.append(entry)

            if template == "accesses_table":
                table = parameter
                if table not in tables:
                    tables[table] = {
                        "name": table, "accessed_by_count": 0,
                        "source": "diva-mcp-x12", "status": "X.12",
                    }
                tables[table]["accessed_by_count"] += 1
                if name:
                    accesses.append({"program": name, "table": table, "status": "X.12"})

            if template == "similar_entity":
                ename = row.get("entity_name") or parameter
                if ename not in entities:
                    entities[ename] = {
                        "name": ename,
                        "similar_fields": row.get("fields", []),
                        "source": "diva-mcp-x12", "status": "X.12",
                    }

    candidates["programs"] = sorted(programs.values(), key=lambda p: -p["score"])[:25]
    candidates["functions"] = sorted(functions.values(), key=lambda f: -f["score"])[:25]
    candidates["tables"] = list(tables.values())
    candidates["entities"] = list(entities.values())
    candidates["relations"]["callers_of"] = callers[:50]
    candidates["relations"]["accesses"] = accesses[:50]

    return candidates


# --- CLI -----------------------------------------------------------------


def _cli() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Generate Cypher queries or consolidate Neo4j results (diva-mcp).")
    ap.add_argument("--mode", required=True, choices=["generate", "consolidate"])
    ap.add_argument("--request", required=True, help="Chemin request.json (parsing-diva-request).")
    ap.add_argument("--results", help="Chemin raw_results.json (mode consolidate).")
    ap.add_argument("--neo4j-status", default="ok",
                    choices=["ok", "unavailable", "partial"],
                    help="Etat du MCP diva-mcp (mode consolidate).")
    args = ap.parse_args()

    request_path = Path(args.request)
    if not request_path.exists():
        print(f"Fichier request introuvable : {request_path}", file=sys.stderr)
        return 2
    request = json.loads(request_path.read_text(encoding="utf-8"))

    if args.mode == "generate":
        queries = generate_queries(request)
        out = {
            "neo4j_status": "pending",
            "queries": queries,
            "disclaimers": _base_disclaimers(),
        }
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    # consolidate
    if args.neo4j_status == "unavailable":
        results: dict = {}
    else:
        if not args.results:
            print("--results requis pour --mode consolidate (sauf si --neo4j-status unavailable)",
                  file=sys.stderr)
            return 2
        results = json.loads(Path(args.results).read_text(encoding="utf-8"))

    out = consolidate(results, neo4j_status=args.neo4j_status)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
