#!/usr/bin/env python3
"""assemble_model.py -- Assemble les .partial.yaml en modele final.

Strategie de fusion :
- Pour chaque type (module, entity, relation, process, program, glossary), scanne
  les fichiers *.yaml et *.partial.yaml du repertoire d'entree.
- Si deux fichiers coexistent (ex: CLI.partial.yaml + CLI.yaml), le non-partial ecrase
  les sections qu'il renseigne (narratif metier manuel) et garde les sections techniques
  du partial (fields, indexes).
- Les relations partielles sont injectees dans entity.schema.relations de l'entite source.

Usage :
  py assemble_model.py --module DAV --input out/doc-erp/DAV/ --output out/doc-erp/DAV/
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


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict, overlay: dict) -> dict:
    """Fusion recursive : overlay ecrase base sur les cles qu'il renseigne."""
    if not isinstance(base, dict) or not isinstance(overlay, dict):
        return overlay if overlay is not None else base
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def collect_files(input_dir: Path, subfolder: str) -> dict:
    """Collecte les fichiers d'un sous-repertoire, fusionne partial + final par code."""
    folder = input_dir / subfolder
    if not folder.exists():
        return {}
    by_code = {}
    for path in sorted(folder.glob("*.yaml")):
        data = load_yaml(path)
        if not data:
            continue
        code = data.get("code") or data.get("entity") or path.stem.replace(".partial", "")
        is_partial = path.name.endswith(".partial.yaml")
        if code not in by_code:
            by_code[code] = {"partial": None, "final": None}
        if is_partial:
            by_code[code]["partial"] = data
        else:
            by_code[code]["final"] = data
    merged = {}
    for code, bits in by_code.items():
        if bits["final"] and bits["partial"]:
            # fusion : partial (technique) + final (narratif manuel)
            merged[code] = deep_merge(bits["partial"], bits["final"])
        elif bits["final"]:
            merged[code] = bits["final"]
        else:
            merged[code] = bits["partial"]
    return merged


PARTITION_FIELDS = {"DOS", "ETB"}


def resolve_heuristic_relations(entity_data: dict) -> None:
    """Resout les relations heuristiques [A VERIFIER] en les confrontant a :
    - la liste des Check_<Entity>_Field_<Field> procs (FK confirmee par objet metier)
    - la liste des champs de partitionnement connus (DOS, ETB)

    Modifie en place entity_data.schema.relations :
    - Promotion : heuristique + Check_Field existe -> FK confirmee
    - Reclassement : DOS/ETB -> type=partitioning
    - Suppression : aucune source ne confirme -> retirer (plus propre)
    """
    schema = entity_data.get("schema") or {}
    relations = schema.get("relations") or []
    tech = entity_data.get("technical") or {}
    field_checks = (tech.get("field_check_procedures") or {}).get("by_field") or {}

    resolved = []
    dropped = []
    for rel in relations:
        note = rel.get("business_note") or ""
        if "[A VERIFIER]" not in note:
            resolved.append(rel)
            continue
        sf = (rel.get("source_field") or "").upper()
        if sf in PARTITION_FIELDS:
            r = {k: v for k, v in rel.items() if k not in ("business_note", "type")}
            r["type"] = "partitioning"
            r["business_note"] = (
                f"Champ de partitionnement {sf} (multi-tenant). "
                f"Pas une FK metier : toute table DAV porte ce champ pour isolation par dossier/etablissement."
            )
            resolved.append(r)
        elif sf in field_checks:
            procs = field_checks[sf]
            r = dict(rel)
            r["business_note"] = (
                f"FK confirmee via {len(procs)} procedure(s) du Module Check : "
                f"{', '.join(procs[:3])}"
            )
            r["checks"] = procs
            resolved.append(r)
        else:
            dropped.append({
                "source_field": sf,
                "target_was": rel.get("target_entity"),
                "reason": "Aucune confirmation dans masque ni Module Check",
            })
    schema["relations"] = resolved
    if dropped:
        meta = entity_data.setdefault("meta", {})
        meta["_dropped_heuristic_relations"] = dropped


def inject_relations(entities: dict, relations_by_entity: dict) -> None:
    """Injecte les relations extraites dans la section schema.relations de chaque entite.

    Applique aussi `resolve_heuristic_relations` apres injection pour promouvoir/
    reclasser/supprimer les heuristiques [A VERIFIER].
    """
    for entity_code, data in entities.items():
        rel_data = relations_by_entity.get(entity_code)
        if rel_data:
            relations = rel_data.get("relations", [])
            if relations:
                schema_section = data.setdefault("schema", {})
                existing = schema_section.get("relations") or []
                seen = {(r.get("target_entity"), r.get("type")) for r in existing}
                for rel in relations:
                    key = (rel.get("target_entity"), rel.get("type"))
                    if key not in seen:
                        existing.append(rel)
                        seen.add(key)
                schema_section["relations"] = existing
        # Resoudre les heuristiques (inchange si rien a faire)
        resolve_heuristic_relations(data)


def write_final(item: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(item, f, allow_unicode=True, sort_keys=False, width=120)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", required=True, help="Code module, ex: DAV")
    ap.add_argument("--input", required=True, help="Repertoire contenant les .partial.yaml par sous-dossier")
    ap.add_argument("--output", required=True, help="Repertoire de sortie (peut etre le meme que --input)")
    args = ap.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)

    # 1. module
    module_file = in_dir / "module.yaml"
    module_partial = in_dir / "module.partial.yaml"
    if module_partial.exists() and module_file.exists():
        module = deep_merge(load_yaml(module_partial), load_yaml(module_file))
    elif module_partial.exists():
        module = load_yaml(module_partial)
    elif module_file.exists():
        module = load_yaml(module_file)
    else:
        module = None

    # 2. entities, relations, processes, programs, glossary
    entities = collect_files(in_dir, "entity")
    relations = collect_files(in_dir, "relation")
    processes = collect_files(in_dir, "process")
    programs = collect_files(in_dir, "program")

    # 3. injecter les relations dans les entites correspondantes
    inject_relations(entities, relations)

    # 4. ecrire les finaux (sans suffixe .partial)
    stats = {"module": 0, "entity": 0, "relation": 0, "process": 0, "program": 0}
    if module:
        write_final(module, out_dir / "module.yaml")
        stats["module"] = 1
    for code, data in entities.items():
        write_final(data, out_dir / "entity" / f"{code}.yaml")
        stats["entity"] += 1
    for code, data in relations.items():
        write_final(data, out_dir / "relation" / f"{code}.yaml")
        stats["relation"] += 1
    for code, data in processes.items():
        write_final(data, out_dir / "process" / f"{code}.yaml")
        stats["process"] += 1
    for code, data in programs.items():
        write_final(data, out_dir / "program" / f"{code}.yaml")
        stats["program"] += 1

    summary = {
        "module": args.module,
        "output": str(out_dir),
        "counts": stats,
        "entities": list(entities.keys()),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
