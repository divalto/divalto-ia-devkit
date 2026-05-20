#!/usr/bin/env python3
"""build_review.py -- Assemble le rapport de relecture final.

Agrege les JSON `.detect_eN.json` des 4 detecteurs, calcule les statistiques
et le verdict, puis produit :
- review.md (rapport lisible via template Jinja2)
- review.json (machine-readable)
- review.stats.json (stats seules)

Tri deterministe des items : entite alpha -> categorie (E1, E3, E4, E2)
-> severite (erreur, warning, info) -> yaml_path. Timestamps exclus du diff
d'idempotence (CA13 UC-201).

Si un fichier `.detect_eN.json` est absent, il est simplement ignore
(0 items pour cette categorie).

Usage :
  py build_review.py --ir ir.json \\
      --detections detect_e1.json,detect_e3.json,detect_e4.json \\
      --template templates/review.md.j2 \\
      --out-md review.md --out-json review.json --out-stats review.stats.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("ERREUR : jinja2 requis. Installer : py -m pip install jinja2", file=sys.stderr)
    sys.exit(2)


CATEGORY_ORDER = {"E1": 0, "E3": 1, "E4": 2, "E2": 3}
SEVERITY_ORDER = {"erreur": 0, "warning": 1, "info": 2}


def collect_detections(paths: list[Path]) -> tuple[list[dict], list[str]]:
    all_items: list[dict] = []
    warnings_global: list[str] = []
    for p in paths:
        if not p.is_file():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        category = data.get("category") or "?"
        for item in (data.get("items") or []):
            item = dict(item)
            item["category"] = item.get("category") or category
            all_items.append(item)
        if data.get("warnings_global"):
            warnings_global.extend(data["warnings_global"])
    return all_items, warnings_global


def sort_key(item: dict) -> tuple:
    return (
        item.get("entity", ""),
        CATEGORY_ORDER.get(item.get("category", ""), 99),
        SEVERITY_ORDER.get(item.get("severity", ""), 99),
        item.get("yaml_path", ""),
    )


def compute_stats(items: list[dict], ir: dict) -> dict:
    stats: dict = {
        c: {"erreur": 0, "warning": 0, "info": 0, "total": 0}
        for c in ["E1", "E2", "E3", "E4"]
    }
    stats["total"] = {"erreur": 0, "warning": 0, "info": 0, "total": 0}
    errors_by_entity: dict[str, int] = {}

    for item in items:
        cat = item.get("category", "?")
        sev = item.get("severity", "?")
        entity = item.get("entity", "?")
        if cat in stats and sev in stats[cat]:
            stats[cat][sev] += 1
            stats[cat]["total"] += 1
        if sev in stats["total"]:
            stats["total"][sev] += 1
            stats["total"]["total"] += 1
        if sev == "erreur":
            errors_by_entity[entity] = errors_by_entity.get(entity, 0) + 1

    a_verifier_count = sum(len(e.get("a_verifier") or []) for e in (ir.get("entities") or []))
    items_count = len(items)
    denom = a_verifier_count + items_count
    coverage_ratio = round(100 * a_verifier_count / denom, 1) if denom else 100.0

    top_critical = sorted(errors_by_entity.items(), key=lambda x: (-x[1], x[0]))[:3]

    stats["a_verifier_count"] = a_verifier_count
    stats["items_count"] = items_count
    stats["coverage_ratio"] = coverage_ratio
    stats["top_critical"] = [(e, n) for e, n in top_critical if n > 0]
    return stats


def verdict(stats: dict) -> str:
    e1_errors = stats.get("E1", {}).get("erreur", 0)
    total_errors = stats.get("total", {}).get("erreur", 0)
    items_count = stats.get("items_count", 0)
    if items_count and e1_errors >= items_count * 0.5:
        return "regression CA4 UC-200"
    if total_errors == 0:
        return "publiable en l'etat"
    return "corrections necessaires avant publication"


def build_entity_list(ir: dict, items_by_entity: dict) -> list[dict]:
    result = []
    for e in sorted(ir.get("entities") or [], key=lambda x: x.get("code", "")):
        code = e.get("code", "?")
        result.append({
            "code": code,
            "label": e.get("label", ""),
            "detected": items_by_entity.get(code, []),
            "a_verifier": e.get("a_verifier") or [],
        })
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir", required=True)
    ap.add_argument("--detections", required=True,
                    help="Liste separee par virgule des chemins .detect_eN.json")
    ap.add_argument("--template", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-stats", required=True)
    ap.add_argument("--editorial", default=None,
                    help="Chemin optionnel vers un .md de synthese editoriale a injecter en tete du rapport")
    args = ap.parse_args()

    ir_path = Path(args.ir)
    if not ir_path.is_file():
        print(f"ERREUR : IR introuvable : {ir_path}", file=sys.stderr)
        sys.exit(2)
    ir = json.loads(ir_path.read_text(encoding="utf-8"))

    detection_paths = [Path(p.strip()) for p in args.detections.split(",") if p.strip()]
    items, warnings_global = collect_detections(detection_paths)
    items.sort(key=sort_key)

    items_by_entity: dict[str, list[dict]] = {}
    for item in items:
        items_by_entity.setdefault(item.get("entity", "?"), []).append(item)

    stats = compute_stats(items, ir)
    v = verdict(stats)
    entities = build_entity_list(ir, items_by_entity)
    module = ir.get("module") or {}

    review_json = {
        "deliverable_root": ir.get("deliverable_root", ""),
        "module": module,
        "verdict": v,
        "entities": entities,
        "warnings_global": warnings_global,
        "stats": stats,
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(
        json.dumps(review_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    Path(args.out_stats).write_text(
        json.dumps({
            "module": module.get("code", ""),
            "verdict": v,
            "stats": stats,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    template_path = Path(args.template)
    if not template_path.is_file():
        print(f"ERREUR : template introuvable : {template_path}", file=sys.stderr)
        sys.exit(2)
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_path.name)
    editorial_text = ""
    if args.editorial:
        ep = Path(args.editorial)
        if ep.is_file():
            editorial_text = ep.read_text(encoding="utf-8").strip()

    rendered = template.render(
        module=module,
        deliverable_root=ir.get("deliverable_root", ""),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        verdict=v,
        stats=stats,
        warnings_global=warnings_global,
        entities=entities,
        editorial=editorial_text,
    )
    Path(args.out_md).write_text(rendered, encoding="utf-8")

    summary = {
        "verdict": v,
        "items_total": len(items),
        "out_md": str(args.out_md),
        "out_json": str(args.out_json),
        "out_stats": str(args.out_stats),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
