#!/usr/bin/env python3
"""detect_omissions.py -- Categorie E3 : omissions structurelles.

Re-parse les sources X.13 (.dhsd, .dhsf, schema SQL) pour reconstruire la liste
de reference des structures (fields, indexes, zooms, FK). Diffe avec les
structures declarees dans l'IR du livrable. Tout element present en source mais
absent du livrable, non justifie par un item meta.a_verifier, est remonte en erreur.

Le socle audit canonique (Ce1..CeC, Dos, UserCr, UserMo, UserCrDh, UserMoDh,
UserCrDt, UserMoDt, Filler) est exclu si l'entite declare `technical.audit_fields`
non vide -- on considere alors que les champs audit sont resumes par ce flag
plutot qu'enumere en `technical.fields[]`.

Usage :
  py detect_omissions.py --ir ir.json --erp-root <path> --out detect_e3.json
    [--schema-sql <path>]
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _dhsd_parser import parse_dhsd_file  # noqa: E402


AUDIT_CANONICAL = {
    "Ce1", "Ce2", "Ce3", "Ce4", "Ce5", "Ce6", "Ce7", "Ce8", "Ce9",
    "CeA", "CeB", "CeC", "Ce",
    "Dos", "UserCr", "UserMo", "UserCrDh", "UserMoDh",
    "UserCrDt", "UserMoDt", "UserTrace", "Filler",
}


def resolve_source(erp_root: Path, name: str) -> Path | None:
    direct = erp_root / name
    if direct.is_file():
        return direct
    for candidate in erp_root.rglob(name):
        if candidate.is_file():
            return candidate
    return None


def is_justified(element_name: str, a_verifier_items: list) -> bool:
    """Un item meta.a_verifier couvre une omission si son texte mentionne
    litteralement le nom de l'element (insensible a la casse, word boundary)."""
    low = element_name.lower()
    for item in a_verifier_items:
        if low in str(item).lower():
            return True
    return False


def detect_for_entity(entity: dict, erp_root: Path, schema_sql: Path | None) -> list[dict]:
    items: list[dict] = []
    code = entity.get("code", "?")
    structures = entity.get("structures") or {}
    a_verifier = entity.get("a_verifier") or []

    declared_fields = {
        f["name"] if isinstance(f, dict) else f
        for f in (structures.get("fields") or []) if f
    }
    declared_indexes = {i for i in (structures.get("indexes") or []) if i}
    primary_table = structures.get("primary_table") or code

    # 1. Dictionnaire .dhsd -- priorite au `technical.dictionary_source` declare
    # dans le livrable (convention documenting-erp), sinon heuristique sur le nom
    # de la table (`Gtt<code>.dhsd` ou `<code>dd.dhsd`).
    declared_dict = (structures.get("dictionary_source") or "").strip()
    candidate_names: list[str] = []
    if declared_dict:
        candidate_names.append(declared_dict)
    candidate_names.extend([f"Gtt{code.lower()}.dhsd", f"{code.lower()}dd.dhsd"])
    dhsd_path = None
    for candidate in candidate_names:
        dhsd_path = resolve_source(erp_root, candidate)
        if dhsd_path:
            break

    if dhsd_path is None:
        items.append({
            "entity": code,
            "severity": "info",
            "title": "Source .dhsd introuvable",
            "yaml_path": "technical.dictionary_source",
            "excerpt_deliverable": "",
            "excerpt_source": "",
            "source_ref": f"<aucun fichier .dhsd trouve sous erp-root pour table {primary_table}>",
            "challenge": (
                "Le relecteur n'a pas pu localiser le dictionnaire source pour cette entite "
                f"(essaye : {', '.join(candidate_names)}). Detection E3 partielle."
            ),
        })
    else:
        parsed = parse_dhsd_file(dhsd_path, primary_table)
        source_fields = {f["name"]: f for f in parsed.get("fields", []) if f.get("name")}
        source_indexes = {i["name"]: i for i in parsed.get("indexes", []) if i.get("name")}

        audit_flag = entity.get("audit_flag", False)
        audit_list = structures.get("audit_fields") or []
        has_audit_summary = bool(audit_list) or audit_flag

        for name in sorted(source_fields):
            if name in declared_fields:
                continue
            if has_audit_summary and name in AUDIT_CANONICAL:
                continue
            if is_justified(name, a_verifier):
                continue
            items.append({
                "entity": code,
                "severity": "erreur",
                "title": f"Champ {name} absent du livrable",
                "yaml_path": "technical.fields",
                "excerpt_deliverable": f"technical.fields ne contient pas '{name}'",
                "excerpt_source": f"[CHAMPS] Nom={name}...",
                "source_ref": f"{dhsd_path.name}",
                "challenge": (
                    f"Champ '{name}' declare dans le dictionnaire source mais absent de "
                    "technical.fields du livrable, sans justification dans meta.a_verifier."
                ),
            })

        for name in sorted(source_indexes):
            if name in declared_indexes:
                continue
            if is_justified(name, a_verifier):
                continue
            items.append({
                "entity": code,
                "severity": "erreur",
                "title": f"Index {name} absent du livrable",
                "yaml_path": "technical.indexes",
                "excerpt_deliverable": f"technical.indexes ne contient pas '{name}'",
                "excerpt_source": f"[INDEX] Nom={name}...",
                "source_ref": f"{dhsd_path.name}",
                "challenge": (
                    f"Index '{name}' declare dans le dictionnaire source mais absent de "
                    "technical.indexes du livrable, sans justification dans meta.a_verifier."
                ),
            })

    # 2. Schema SQL : hors scope du MVP (demande un parseur du JSON schema specifique
    #    a l'export de documenting-erp). A cabler en A4bis si besoin.
    if schema_sql and schema_sql.is_file():
        pass  # placeholder -- couverture SQL reportee

    return items


def detect(ir: dict, erp_root: Path, schema_sql: Path | None) -> dict:
    all_items: list[dict] = []
    for entity in ir.get("entities", []):
        all_items.extend(detect_for_entity(entity, erp_root, schema_sql))
    all_items.sort(key=lambda x: (x["entity"], x["yaml_path"], x["title"]))
    return {
        "category": "E3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": all_items,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir", required=True)
    ap.add_argument("--erp-root", required=True)
    ap.add_argument("--schema-sql", default=None, help="Optionnel : chemin vers l'export JSON SQL")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ir_path = Path(args.ir)
    if not ir_path.is_file():
        print(f"ERREUR : IR introuvable : {ir_path}", file=sys.stderr)
        sys.exit(2)
    erp_root = Path(args.erp_root)
    if not erp_root.is_dir():
        print(f"ERREUR : erp-root introuvable : {erp_root}", file=sys.stderr)
        sys.exit(2)
    schema_sql = Path(args.schema_sql) if args.schema_sql else None

    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    result = detect(ir, erp_root, schema_sql)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    erreurs = sum(1 for x in result["items"] if x["severity"] == "erreur")
    infos = sum(1 for x in result["items"] if x["severity"] == "info")
    summary = {
        "category": "E3",
        "erreurs": erreurs,
        "infos": infos,
        "total_items": len(result["items"]),
        "out": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
