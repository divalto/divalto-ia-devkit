#!/usr/bin/env python3
"""ingest_deliverable.py -- Lit un livrable UC-200 et produit un IR unifie.

Extrait pour chaque entite :
- Liste des affirmations narratives (texte + yaml_path + citations detectees + mark [A VERIFIER])
- Liste des structures declarees (fields, indexes, primary_key, relations)
- meta.a_verifier (items ouverts)

Sortie : JSON lisible par les detecteurs E1-E4.

Usage :
  py ingest_deliverable.py --deliverable out/doc-erp/DAV/ --out ir.json
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERREUR : pyyaml requis. Installer : py -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# Detection de citations. 2 formes acceptees :
#   1. `fichier.ext:N`        -- citation precise (source de verite X.13 avec ligne)
#   2. `[fichier.ext]` inline -- citation faible (fichier seul, sans ligne)
# Plus la source structuree via clé `source: fichier.ext[:N]` d'un dict {text, source}.
CITATION_WITH_LINE_REGEX = re.compile(
    r"([A-Za-z0-9_./\\-]+\.(?:dhsp|dhsq|dhsd|dhsf|dhop|sql|dll|md|py|js)):(\d+)",
    re.IGNORECASE,
)
CITATION_BRACKETED_REGEX = re.compile(
    r"\[([A-Za-z0-9_./\\-]+\.(?:dhsp|dhsq|dhsd|dhsf|dhop|sql|dll|md|py|js))\]",
    re.IGNORECASE,
)
A_VERIFIER_MARK_REGEX = re.compile(r"\[A\s+(?:VERIFIER|ENRICHIR)\]", re.IGNORECASE)
SOURCE_KEY_REGEX = re.compile(
    r"^[A-Za-z0-9_./\\-]+\.(?:dhsp|dhsq|dhsd|dhsf|dhop|sql|dll|md|py|js)(?::\d+)?$",
    re.IGNORECASE,
)

NARRATIVE_TOP_PREFIXES = ("business.", "schema.", "technical.")

# Champs structurels / enumerations / IDs : pas narratif metier, a ignorer.
STRUCTURAL_FIELDS = {
    "name", "nature", "sql_type", "nullable", "default", "layer",
    "primary_table", "primary_key", "satellite_tables", "zoom",
    "dictionary_source", "record_name", "field_count", "zoom_code",
    "base", "module", "code", "label", "status", "dict_file",
    "choix_id", "position", "repetition", "taille", "ce_field",
    "ce_value", "kind", "version", "criticality", "source",
    "main_screen_name", "main_screens", "diagram_mermaid",
}

MIN_NARRATIVE_LEN = 20


def detect_citations(text: str) -> list:
    """Extrait les citations inline du texte (formes fichier:N et [fichier])."""
    hits = []
    for m in CITATION_WITH_LINE_REGEX.finditer(text):
        hits.append(f"{m.group(1)}:{m.group(2)}")
    for m in CITATION_BRACKETED_REGEX.finditer(text):
        hits.append(m.group(1))
    return hits


def has_a_verifier_mark(text: str) -> bool:
    return bool(A_VERIFIER_MARK_REGEX.search(text))


def _last_segment(path: str) -> str:
    """Extrait le dernier segment du yaml_path, depouille des indices de liste."""
    tail = path.rsplit(".", 1)[-1]
    if "[" in tail:
        tail = tail.split("[", 1)[0]
    return tail


def _should_capture(path: str, value: str) -> bool:
    if not path.startswith(NARRATIVE_TOP_PREFIXES):
        return False
    if not value or len(value) < MIN_NARRATIVE_LEN:
        return False
    if _last_segment(path) in STRUCTURAL_FIELDS:
        return False
    return True


def _dict_implicit_source(data: dict) -> str | None:
    """Si un dict porte une clé 'source' valide (pattern fichier.ext[:N]),
    retourne cette source comme citation implicite applicable a ses strings."""
    src = data.get("source")
    if isinstance(src, str):
        s = src.strip()
        if s and SOURCE_KEY_REGEX.match(s):
            return s
    return None


def walk_affirmations(data, path_prefix: str, out: list, implicit_source: str | None = None):
    """Parcourt recursivement et collecte les strings narratives.

    Regle : si un dict porte `source: fichier.ext[:N]` valide, cette source
    devient citation implicite pour ses strings directes (convention
    documenting-erp pour `{text, source}` et listes de dicts avec `source:`).
    """
    if isinstance(data, dict):
        local_src = _dict_implicit_source(data) or implicit_source
        for key, value in data.items():
            if key == "source":
                continue
            current_path = f"{path_prefix}.{key}" if path_prefix else key
            if isinstance(value, str):
                if _should_capture(current_path, value):
                    out.append(_make_item(current_path, value, local_src))
            elif isinstance(value, (list, dict)):
                walk_affirmations(value, current_path, out, local_src)
    elif isinstance(data, list):
        for idx, v in enumerate(data):
            if isinstance(v, str):
                item_path = f"{path_prefix}[{idx}]"
                if _should_capture(item_path, v):
                    out.append(_make_item(item_path, v, implicit_source))
            else:
                walk_affirmations(v, f"{path_prefix}[{idx}]", out, implicit_source)


def _make_item(yaml_path: str, text: str, implicit_source: str | None = None) -> dict:
    citations = detect_citations(text)
    if implicit_source and implicit_source not in citations:
        citations.append(implicit_source)
    return {
        "yaml_path": yaml_path,
        "text": text,
        "citations": citations,
        "has_a_verifier_mark": has_a_verifier_mark(text),
    }


def extract_structures(entity_yaml: dict) -> dict:
    """Liste les structures declarees : fields, indexes, audit_fields, primary_key, relations."""
    tech = entity_yaml.get("technical") or {}
    sch = entity_yaml.get("schema") or {}
    return {
        "fields": [
            {"name": f.get("name"), "nature": f.get("nature", ""), "zoom": f.get("zoom", "")}
            for f in (tech.get("fields") or []) if isinstance(f, dict) and f.get("name")
        ],
        "indexes": [i.get("name") for i in (tech.get("indexes") or []) if isinstance(i, dict) and i.get("name")],
        "audit_fields": [a for a in (tech.get("audit_fields") or []) if isinstance(a, str)],
        "primary_key": sch.get("primary_key") or [],
        "primary_table": sch.get("primary_table") or "",
        "dictionary_source": tech.get("dictionary_source", ""),
        "relations": [r for r in (sch.get("relations") or []) if isinstance(r, dict)],
    }


def ingest_entity(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    code = data.get("code") or path.stem
    affirmations: list = []
    walk_affirmations(data, "", affirmations)
    meta = data.get("meta") or {}
    a_verifier = meta.get("a_verifier") or []
    if not isinstance(a_verifier, list):
        a_verifier = []
    return {
        "code": code,
        "label": data.get("label", ""),
        "module": data.get("module", ""),
        "source_file": str(path),
        "affirmations": affirmations,
        "structures": extract_structures(data),
        "a_verifier": [str(x) for x in a_verifier],
    }


def ingest_deliverable(root: Path, entities_filter: set | None) -> dict:
    entity_dir = root / "entity"
    if not entity_dir.is_dir():
        raise SystemExit(f"Repertoire 'entity/' absent sous {root}")
    entities = []
    for yml in sorted(entity_dir.glob("*.yaml")):
        # Ignorer les variantes *.partial.yaml / *.narrative.yaml (fragments intermediaires
        # de documenting-erp) : on ne garde que le livrable final <CODE>.yaml.
        if "." in yml.stem:
            continue
        entry = ingest_entity(yml)
        if entities_filter and entry["code"] not in entities_filter:
            continue
        entities.append(entry)
    module_yaml = root / "module.yaml"
    module_data = {}
    if module_yaml.is_file():
        with module_yaml.open(encoding="utf-8") as f:
            module_data = yaml.safe_load(f) or {}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deliverable_root": str(root),
        "module": {
            "code": module_data.get("code", ""),
            "label": module_data.get("label", ""),
            "domain": module_data.get("domain") or module_data.get("prefix", ""),
        },
        "entities": entities,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deliverable", required=True, help="Racine du livrable UC-200 (contient module.yaml + entity/*.yaml)")
    ap.add_argument("--entities", default="all", help="'all' ou liste separee par virgule")
    ap.add_argument("--out", required=True, help="Chemin du fichier IR JSON de sortie")
    args = ap.parse_args()

    entities_filter = None
    if args.entities and args.entities != "all":
        entities_filter = {e.strip() for e in args.entities.split(",") if e.strip()}

    root = Path(args.deliverable)
    ir = ingest_deliverable(root, entities_filter)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ir, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "entities": len(ir["entities"]),
        "affirmations_total": sum(len(e["affirmations"]) for e in ir["entities"]),
        "out": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
