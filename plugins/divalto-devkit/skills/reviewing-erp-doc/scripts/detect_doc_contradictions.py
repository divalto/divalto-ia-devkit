#!/usr/bin/env python3
"""detect_doc_contradictions.py -- Categorie E4 : contradictions avec le referentiel DIVA.

MVP v1 : 2 heuristiques deterministes sur le corpus `docs/` du workspace.

- H1 : Nature d'un champ coherente avec son suffixe typee
       Source : taxonomie consolidee dans managing-diva-dictionaries/scripts/suggest_nature.py,
       documentee dans docs/DICTIONNAIRE-DHSD.md section 2.
- H5 : Domaine coherent avec prefixe de fichier source
       Source : docs/MODULES-ERP.md section 4 "Prefixes domaine complets".

Modes :
- `--docs-root <path>` : charge les heuristiques dependantes de docs/
- `--docs-root skip` : skip H5 + marque H1 comme "taxonomie hardcodee" (H1 reste actif)

Severite : toujours `warning` (le referentiel peut etre en retard).

Usage :
  py detect_doc_contradictions.py --ir ir.json --docs-root docs/ --out detect_e4.json
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# H1 : table suffixe -> Nature attendue (extract de SUFFIX_TAXONOMY,
# managing-diva-dictionaries/scripts/suggest_nature.py, confidence >= 0.9).
# Subset MVP : les suffixes les plus fiables et les plus frequents.
SUFFIX_TO_NATURE = {
    "Dh":  {"nature": "DH", "note": "Datetime 14 octets"},
    "Dt":  {"nature": "D8", "note": "Date 8 octets"},
    "Fl":  {"nature_starts": "1,", "note": "Flottant (1,0 ou 1,N)"},
    "Mt":  {"nature_starts": "8,", "note": "Montant financier (8,N)"},
    "Qte": {"nature_starts": "8,", "note": "Quantite (8,N)"},
}


def parse_domain_prefixes(modules_erp_md: Path) -> dict:
    """Extrait le mapping code_domaine -> prefixe_fichier depuis MODULES-ERP.md section 4.

    Regex sur les lignes de tableau Markdown :
        | Achat-Vente (DAV) | `GT_` | ...
    """
    if not modules_erp_md.is_file():
        return {}
    content = modules_erp_md.read_text(encoding="utf-8")
    pattern = re.compile(r"\|[^|]*\(([A-Z]+)\)\s*\|\s*`([A-Za-z_]+)`", re.MULTILINE)
    out: dict[str, str] = {}
    for match in pattern.finditer(content):
        domain = match.group(1)
        prefix = match.group(2).rstrip("_").rstrip("t").rstrip("T")  # "GT_" -> "G" ou "Gt"
        # Preserver le vrai prefixe DIVA standard (Gtt/Gfc/...) -- garder les 3 premieres lettres
        out[domain] = match.group(2).rstrip("_")
    return out


def check_h1_suffix_nature(entity: dict) -> list[dict]:
    """Pour chaque champ, verifier la coherence suffixe (nom) vs Nature declaree."""
    items: list[dict] = []
    code = entity.get("code", "?")
    fields = (entity.get("structures") or {}).get("fields") or []
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get("name", "")
        nature = (field.get("nature") or "").strip()
        if not name or not nature:
            continue
        # Extraire le suffixe PascalCase : dernier groupe majuscule+minuscule en fin de nom
        # Ex : UserCrDh -> Dh, DateCre -> Cre, AnnulFl -> Fl
        suffix_match = re.search(r"([A-Z][a-z]+)$", name)
        if not suffix_match:
            continue
        suffix = suffix_match.group(1)
        expected = SUFFIX_TO_NATURE.get(suffix)
        if not expected:
            continue
        if "nature" in expected:
            if nature != expected["nature"]:
                items.append(_build_h1_item(code, name, nature, suffix, expected))
        elif "nature_starts" in expected:
            if not nature.startswith(expected["nature_starts"]):
                items.append(_build_h1_item(code, name, nature, suffix, expected))
    return items


def _build_h1_item(code: str, name: str, nature: str, suffix: str, expected: dict) -> dict:
    expected_str = expected.get("nature") or (expected.get("nature_starts", "") + "...")
    return {
        "entity": code,
        "severity": "warning",
        "title": f"Nature de {name} incoherente avec suffixe {suffix}",
        "yaml_path": f"technical.fields[{name}].nature",
        "excerpt_deliverable": f"{name} = {nature}",
        "excerpt_source": f"suffixe {suffix} attendu en Nature {expected_str} ({expected['note']})",
        "source_ref": "DICTIONNAIRE-DHSD.md:section 2 (+ managing-diva-dictionaries/scripts/suggest_nature.py)",
        "challenge": (
            f"Le champ '{name}' porte le suffixe typee '{suffix}' (Nature attendue : {expected_str}, "
            f"{expected['note']}), mais le livrable declare Nature '{nature}'. "
            "Soit le nom du champ derive de la convention, soit la Nature a ete mal extraite."
        ),
    }


def check_h5_domain_prefix(entity: dict, domain_prefixes: dict, ir_module_code: str) -> list[dict]:
    """Verifier que le prefixe des citations d'une entite matche le prefixe du domaine declare."""
    items: list[dict] = []
    code = entity.get("code", "?")
    module = entity.get("module") or ir_module_code
    if not module or module not in domain_prefixes:
        return items
    expected_prefix = domain_prefixes[module]
    for aff in entity.get("affirmations") or []:
        for citation in aff.get("citations") or []:
            fname = citation.split(":", 1)[0]
            fname_basename = fname.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            # Les fichiers DIVA utilisent souvent 2-3 lettres de prefixe (Gtt, Gfc, Gab...).
            # On compare le prefixe attendu (de MODULES-ERP.md) avec le debut du fichier.
            if not fname_basename.lower().startswith(expected_prefix.lower()):
                items.append({
                    "entity": code,
                    "severity": "warning",
                    "title": f"Citation {fname_basename} incoherente avec domaine {module}",
                    "yaml_path": aff.get("yaml_path", ""),
                    "excerpt_deliverable": f"citation : {citation}",
                    "excerpt_source": f"domaine {module} -> prefixe attendu {expected_prefix}",
                    "source_ref": "MODULES-ERP.md:section 4",
                    "challenge": (
                        f"L'entite declare module={module} mais cite un fichier '{fname_basename}' "
                        f"dont le prefixe ne matche pas {expected_prefix} attendu pour ce domaine."
                    ),
                })
    return items


def detect(ir: dict, docs_root: Path | None) -> dict:
    all_items: list[dict] = []
    warnings_global: list[str] = []

    domain_prefixes: dict[str, str] = {}
    if docs_root is None:
        warnings_global.append("E4 partielle : --docs-root skip, seule H1 (taxonomie hardcodee) est active.")
    else:
        modules_md = docs_root / "MODULES-ERP.md"
        if modules_md.is_file():
            domain_prefixes = parse_domain_prefixes(modules_md)
        else:
            warnings_global.append(f"MODULES-ERP.md introuvable sous {docs_root} -- H5 skippee.")

    ir_module_code = (ir.get("module") or {}).get("code", "")

    for entity in ir.get("entities") or []:
        all_items.extend(check_h1_suffix_nature(entity))
        if domain_prefixes:
            all_items.extend(check_h5_domain_prefix(entity, domain_prefixes, ir_module_code))

    all_items.sort(key=lambda x: (x["entity"], x["yaml_path"], x["title"]))
    return {
        "category": "E4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warnings_global": warnings_global,
        "items": all_items,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir", required=True)
    ap.add_argument("--docs-root", required=True, help="Racine docs/ du workspace OU 'skip'")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ir_path = Path(args.ir)
    if not ir_path.is_file():
        print(f"ERREUR : IR introuvable : {ir_path}", file=sys.stderr)
        sys.exit(2)

    if args.docs_root.strip().lower() == "skip":
        docs_root = None
    else:
        docs_root = Path(args.docs_root)
        if not docs_root.is_dir():
            print(f"ERREUR : docs-root introuvable : {docs_root} (utiliser 'skip' si pas dispo)", file=sys.stderr)
            sys.exit(2)

    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    result = detect(ir, docs_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    warnings = sum(1 for x in result["items"] if x["severity"] == "warning")
    summary = {
        "category": "E4",
        "warnings_items": warnings,
        "warnings_global": len(result["warnings_global"]),
        "domain_prefixes_loaded": len(docs_root and (docs_root / "MODULES-ERP.md").is_file() and [1] or []),
        "out": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
