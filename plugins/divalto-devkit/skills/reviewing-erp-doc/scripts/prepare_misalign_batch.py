#!/usr/bin/env python3
"""prepare_misalign_batch.py -- Prepare le batch d'evaluation E2 (desalignement narratif vs citation).

Pour chaque affirmation sourcee (citation fichier:ligne dans l'IR), extrait un contexte
de N lignes autour de la ligne citee via _x13_context. Produit un batch JSON destine
a Claude (etape 6 du SKILL.md) qui evaluera chaque paire {narratif, context_source}.

Citations dont la source est introuvable sont conservees avec `context_error = "source_not_found"` :
Claude remontera ces items en severite `info` plutot que de les ignorer silencieusement.

Usage :
  py prepare_misalign_batch.py --ir ir.json --erp-root {CHEMIN_ERP_STANDARD} --out batch_e2.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _x13_context import extract  # noqa: E402


def resolve_source(erp_root: Path, citation_path: str) -> Path | None:
    """Resout une citation 'Gttokk.dhsq' en chemin absolu sous erp_root.

    Recherche recursive si le fichier n'est pas directement a la racine. Renvoie None
    si le fichier n'existe pas.
    """
    direct = erp_root / citation_path
    if direct.is_file():
        return direct
    name = Path(citation_path).name
    for candidate in erp_root.rglob(name):
        if candidate.is_file():
            return candidate
    return None


def build_batch(ir: dict, erp_root: Path, context_lines: int) -> dict:
    entries = []
    for entity in ir.get("entities", []):
        code = entity.get("code", "?")
        for aff in entity.get("affirmations", []):
            citations = aff.get("citations") or []
            if not citations:
                continue
            for citation in citations:
                try:
                    fname, lineno = citation.rsplit(":", 1)
                    line_int = int(lineno)
                except (ValueError, AttributeError):
                    continue
                src_path = resolve_source(erp_root, fname)
                if src_path is None:
                    entries.append({
                        "entity": code,
                        "yaml_path": aff.get("yaml_path", ""),
                        "narratif": aff.get("text", ""),
                        "citation": citation,
                        "context_source": "",
                        "context_lines_range": None,
                        "context_error": "source_not_found",
                    })
                    continue
                try:
                    ctx = extract(src_path, line=line_int, window=context_lines)
                    raw = ctx.get("snippet", "")
                    snippet = "".join(raw) if isinstance(raw, list) else (raw or "")
                    entries.append({
                        "entity": code,
                        "yaml_path": aff.get("yaml_path", ""),
                        "narratif": aff.get("text", ""),
                        "citation": citation,
                        "context_source": snippet,
                        "context_lines_range": [ctx.get("snippet_start"), ctx.get("snippet_end")],
                        "context_error": None,
                    })
                except Exception as e:
                    entries.append({
                        "entity": code,
                        "yaml_path": aff.get("yaml_path", ""),
                        "narratif": aff.get("text", ""),
                        "citation": citation,
                        "context_source": "",
                        "context_lines_range": None,
                        "context_error": f"extract_error: {e}",
                    })
    entries.sort(key=lambda x: (x["entity"], x["yaml_path"], x["citation"]))
    return {
        "erp_root": str(erp_root),
        "context_lines": context_lines,
        "entries": entries,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir", required=True, help="IR JSON produit par ingest_deliverable.py")
    ap.add_argument("--erp-root", required=True, help="Racine des sources X.13")
    ap.add_argument("--context-lines", type=int, default=20, help="Nb de lignes autour de chaque citation (defaut 20)")
    ap.add_argument("--out", required=True, help="Chemin du batch E2 JSON de sortie")
    args = ap.parse_args()

    ir_path = Path(args.ir)
    if not ir_path.is_file():
        print(f"ERREUR : IR introuvable : {ir_path}", file=sys.stderr)
        sys.exit(2)
    erp_root = Path(args.erp_root)
    if not erp_root.is_dir():
        print(f"ERREUR : erp-root introuvable : {erp_root}", file=sys.stderr)
        sys.exit(2)

    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    batch = build_batch(ir, erp_root, args.context_lines)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")

    total = len(batch["entries"])
    resolved = sum(1 for e in batch["entries"] if e["context_error"] is None)
    not_found = sum(1 for e in batch["entries"] if e["context_error"] == "source_not_found")
    summary = {
        "entries_total": total,
        "resolved": resolved,
        "source_not_found": not_found,
        "extract_error": total - resolved - not_found,
        "out": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
