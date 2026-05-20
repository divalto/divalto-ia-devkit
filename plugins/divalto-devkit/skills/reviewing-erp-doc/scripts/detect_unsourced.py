#!/usr/bin/env python3
"""detect_unsourced.py -- Categorie E1 : affirmations narratives non sourcees.

Lit l'IR produit par ingest_deliverable.py et remonte les affirmations qui ne sont :
- ni tracees par une citation `fichier:ligne`,
- ni marquees litteralement `[A VERIFIER]` / `[A ENRICHIR]`,
- ni couvertes par un item de `meta.a_verifier` (matching sur yaml_path ou dernier segment).

Severite : erreur. Viole CA4 de UC-200.

Usage :
  py detect_unsourced.py --ir ir.json --out detect_e1.json
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def is_covered_by_a_verifier(yaml_path: str, a_verifier_items: list) -> bool:
    """Un item de meta.a_verifier couvre le champ si son texte mentionne :
    - le yaml_path complet (ex: 'business.role')
    - ou le dernier segment du path (ex: 'role'), en matching insensible a la casse.
    """
    if not a_verifier_items:
        return False
    last_segment = re.sub(r"\[\d+\]$", "", yaml_path.rsplit(".", 1)[-1])
    last_segment_lower = last_segment.lower()
    path_lower = yaml_path.lower()
    for item in a_verifier_items:
        item_lower = str(item).lower()
        if path_lower in item_lower:
            return True
        # Eviter de matcher un segment trop court ou generique (< 4 chars)
        if len(last_segment) >= 4 and re.search(rf"\b{re.escape(last_segment_lower)}\b", item_lower):
            return True
    return False


def detect(ir: dict) -> dict:
    items = []
    for entity in ir.get("entities", []):
        a_verifier = entity.get("a_verifier", [])
        code = entity.get("code", "?")
        for aff in entity.get("affirmations", []):
            if aff.get("citations"):
                continue
            if aff.get("has_a_verifier_mark"):
                continue
            if is_covered_by_a_verifier(aff.get("yaml_path", ""), a_verifier):
                continue
            items.append({
                "entity": code,
                "severity": "erreur",
                "title": "Affirmation narrative non sourcee",
                "yaml_path": aff.get("yaml_path", ""),
                "excerpt_deliverable": _truncate(aff.get("text", ""), 300),
                "excerpt_source": "",
                "source_ref": "<aucune>",
                "challenge": (
                    "Aucune citation fichier:ligne dans l'affirmation, aucun marquage "
                    "[A VERIFIER] inline, aucun item meta.a_verifier couvrant le champ. "
                    "Viole CA4 de UC-200 (regle de citation stricte)."
                ),
            })
    items.sort(key=lambda x: (x["entity"], x["yaml_path"]))
    return {
        "category": "E1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir", required=True, help="IR JSON produit par ingest_deliverable.py")
    ap.add_argument("--out", required=True, help="Chemin de sortie .detect_e1.json")
    args = ap.parse_args()

    ir_path = Path(args.ir)
    if not ir_path.is_file():
        print(f"ERREUR : IR introuvable : {ir_path}", file=sys.stderr)
        sys.exit(2)
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    result = detect(ir)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "category": "E1",
        "erreurs": len(result["items"]),
        "out": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
