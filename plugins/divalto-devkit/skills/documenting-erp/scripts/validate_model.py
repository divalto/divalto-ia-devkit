#!/usr/bin/env python3
"""validate_model.py -- Valide les YAML du modele contre les schemas.

Verifications :
- Parsing YAML sans erreur
- Presence des champs obligatoires (code, label, module, base, status pour entity, etc.)
- Coherence inter-fichiers : les references entre types pointent vers des codes existants
- Taux de completion des sections couche-par-couche

Usage :
  py validate_model.py --model out/doc-erp/DAV/ --schemas schemas/
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERREUR : pyyaml requis. Installer : py -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REQUIRED_BY_KIND = {
    "module":   ["code", "label", "prefix", "status"],
    "entity":   ["code", "label", "module", "base", "status"],
    "relation": ["source_entity", "target_entity", "type", "cardinality"],
    "process":  ["code", "label", "module"],
    "program":  ["code", "kind", "module"],
    "glossary": ["term", "technical_code"],
}


def validate_file(path: Path) -> list:
    """Renvoie une liste d'erreurs (chaines) pour un fichier donne."""
    errors = []
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [f"{path}: parsing YAML impossible : {e}"]
    if not isinstance(data, dict):
        return [f"{path}: contenu non-dict (type {type(data).__name__})"]

    kind = data.get("kind")
    if not kind:
        # heuristique : regarder le nom de repertoire
        parent = path.parent.name
        kind_by_folder = {"entity": "entity", "relation": "relation",
                          "process": "process", "program": "program"}
        kind = kind_by_folder.get(parent)
    if not kind:
        errors.append(f"{path}: kind absent et indeterminable")
        return errors

    required = REQUIRED_BY_KIND.get(kind, [])
    for key in required:
        if key not in data and not _get_nested(data, key):
            errors.append(f"{path}: champ obligatoire absent : {key}")
    return errors


def _get_nested(data, key_path):
    parts = key_path.split(".")
    cur = data
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def check_cross_references(model_dir: Path) -> list:
    """Verifie que les references inter-fichiers pointent vers des codes existants."""
    errors = []
    entities = set()
    processes = set()

    for path in (model_dir / "entity").glob("*.yaml") if (model_dir / "entity").exists() else []:
        with path.open(encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        if d.get("code"):
            entities.add(d["code"])

    for path in (model_dir / "process").glob("*.yaml") if (model_dir / "process").exists() else []:
        with path.open(encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        if d.get("code"):
            processes.add(d["code"])

    # verifier les refs dans entities
    for path in (model_dir / "entity").glob("*.yaml") if (model_dir / "entity").exists() else []:
        with path.open(encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        code = d.get("code", path.stem)
        # refs vers processes
        for pr in (d.get("business") or {}).get("processes", []) or []:
            if pr not in processes:
                errors.append(f"{path}: entity {code} reference process inconnu: {pr}")
        # refs relations
        for rel in (d.get("schema") or {}).get("relations", []) or []:
            target = rel.get("target_entity")
            # cible peut etre une entite externe au module : warning, pas error
            if target and target not in entities:
                errors.append(f"WARN {path}: relation vers entite {target} non documentee dans ce module")

    return errors


_CITATION_PATTERN = re.compile(r'[A-Za-z0-9_]+\.(?:dhsp|dhsd|dhsf|dhsq|dhop):\d+')


def check_ce_citations(entity: dict, path: Path) -> list:
    """Verifie la regle de citation stricte (CA4) sur les descriptions metier CE.

    Pour chaque entree dans technical.ce_analysis.fields[] :
    - status=="actif" + description_metier non vide :
        description_metier_source doit contenir au moins une citation
        fichier:ligne (format `<fichier>.(dhsp|dhsd|dhsf|dhsq):<n>`).
    - status=="actif" + description_metier vide/null :
        meta.a_verifier doit contenir un item qui mentionne le nom du CE.
    - status=="reserve" : description_metier fixe (ecrite par le script),
        aucune verification requise.
    """
    errors = []
    tech = entity.get("technical") or {}
    ce = tech.get("ce_analysis") or {}
    fields = ce.get("fields") or []
    if not fields:
        return errors
    entity_code = entity.get("code", path.stem)
    a_verifier = [str(x) for x in (entity.get("meta") or {}).get("a_verifier", []) or []]

    for f in fields:
        name = (f.get("name") or "").upper()
        status = f.get("status")
        desc = f.get("description_metier")
        src = f.get("description_metier_source") or ""
        if status == "actif":
            if desc:
                if not _CITATION_PATTERN.search(src):
                    errors.append(
                        f"{path}: entity {entity_code} CE {name} : "
                        f"description_metier sans citation fichier:ligne "
                        f"(description_metier_source='{src[:60]}')"
                    )
            else:
                # Description absente : exige un item a_verifier citant le CE
                mentioned = any(name in item.upper() for item in a_verifier)
                if not mentioned:
                    errors.append(
                        f"{path}: entity {entity_code} CE {name} actif sans "
                        f"description_metier et non reference dans meta.a_verifier"
                    )
    return errors


def compute_layer_completion(entity: dict) -> dict:
    """Mesure le taux de completion des 3 couches pour une entite."""
    def non_empty(section):
        if not section:
            return 0, 0
        filled = sum(1 for v in section.values() if v not in (None, "", [], {}, "[A ENRICHIR]", "[A VERIFIER]"))
        return filled, len(section)
    b_f, b_t = non_empty(entity.get("business"))
    s_f, s_t = non_empty(entity.get("schema"))
    t_f, t_t = non_empty(entity.get("technical"))
    return {
        "business":  f"{b_f}/{b_t}" if b_t else "0/0",
        "schema":    f"{s_f}/{s_t}" if s_t else "0/0",
        "technical": f"{t_f}/{t_t}" if t_t else "0/0",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="Repertoire du modele (ex: out/doc-erp/DAV/)")
    ap.add_argument("--schemas", help="Repertoire des schemas (reserve, non utilise en MVP)")
    args = ap.parse_args()

    model_dir = Path(args.model)
    if not model_dir.exists():
        print(json.dumps({"error": f"model_dir introuvable : {model_dir}"}), file=sys.stderr)
        sys.exit(2)

    all_errors = []
    file_count = 0
    layer_stats = {}
    for path in sorted(model_dir.rglob("*.yaml")):
        if ".partial." in path.name or ".narrative." in path.name:
            continue
        file_count += 1
        errs = validate_file(path)
        all_errors.extend(errs)
        if path.parent.name == "entity":
            with path.open(encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            layer_stats[d.get("code", path.stem)] = compute_layer_completion(d)
            # Regle de citation stricte CA4 sur les CE actifs
            all_errors.extend(check_ce_citations(d, path))

    all_errors.extend(check_cross_references(model_dir))

    # split warnings vs errors
    warnings = [e for e in all_errors if e.startswith("WARN ")]
    errors = [e for e in all_errors if not e.startswith("WARN ")]

    result = {
        "model_dir": str(model_dir),
        "files_checked": file_count,
        "errors": errors,
        "warnings": warnings,
        "layer_completion_by_entity": layer_stats,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
