#!/usr/bin/env python3
"""detect_doc_contradictions.py -- Categorie E4 : contradictions avec le referentiel.

Deux heuristiques deterministes, dont les deux sources sont LIVREES avec le devkit.
Aucune n'exige un document que le partenaire n'aurait pas : E4 tourne toujours.

- H1 : Nature d'un champ coherente avec son suffixe type.
       Table ci-dessous. Elle ne garde que les suffixes dont la correlation est forte
       (>= 85 %) selon `managing-diva-dictionaries` --
       `reference/taxonomie-suffixes.md` et `scripts/suggest_nature.py`.
- H5 : Prefixe du fichier cite coherent avec le domaine declare.
       Table dans `reference/prefixes-domaine.md`, copie locale de la page
       `naming-diva-entities/reference/domain-prefixes.md` (regle de vendoring : un
       script ne lit pas la page d'un autre skill).

Severite : toujours `warning`. Une correlation statistique n'est pas une regle.

Usage :
  py detect_doc_contradictions.py --ir ir.json --out detect_e4.json
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# H1 : table suffixe -> Nature attendue. Seuls les suffixes de la bande « correlation
# forte » (>= 85 %) de `managing-diva-dictionaries/reference/taxonomie-suffixes.md`, qui
# concorde avec `SUFFIX_TAXONOMY` de son `scripts/suggest_nature.py`.
#
# `Mt` et `Qte` ont ete RETIRES. Cette table affirmait `8,N` pour les deux, alors que
# les deux sources donnent `Mt` -> `16,D0` a 65 % et `Qte` -> `12,D2` a 72 % : la bande
# « proposer + demander confirmation », pas celle qu'on affirme. E4 signalait donc comme
# contradiction un livrable declarant la bonne Nature.
SUFFIX_TO_NATURE = {
    "Dh":  {"nature": "DH", "note": "Timestamp 14 octets (98 %)"},
    "Fl":  {"nature_starts": "1,", "note": "Flag booleen, 1,0 (95 %)"},
    "Dt":  {"nature": "D8", "note": "Date AAAAMMJJ (93 %)"},
}


def parse_domain_prefixes(page: Path) -> dict:
    """{domaine: prefixe_module} depuis `reference/prefixes-domaine.md`.

    Lignes de tableau : `| DAV | \u0060GT_\u0060 | \u0060gtt\u0060 |`. On prend la
    TROISIEME colonne, « Prefixe module », parce que c'est elle qui prefixe les noms de
    fichiers (`gttcli.dhop`). L'ancienne version lisait `GT_` et le comparait a
    `gttcli` : ca ne concordait que par accident de troncature.
    """
    if not page.is_file():
        return {}
    content = page.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^\|\s*([A-Za-z][\w\- ]*?)\s*\|\s*`[^`]+`\s*\|\s*`([^`]+)`\s*\|",
        re.MULTILINE)
    return {m.group(1).strip(): m.group(2).strip()
            for m in pattern.finditer(content)}


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
        "source_ref": "taxonomie des suffixes -- skill `managing-diva-dictionaries`, page `reference/taxonomie-suffixes.md`",
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
            # On compare le prefixe module attendu, lu dans `reference/prefixes-domaine.md`.
            if not fname_basename.lower().startswith(expected_prefix.lower()):
                items.append({
                    "entity": code,
                    "severity": "warning",
                    "title": f"Citation {fname_basename} incoherente avec domaine {module}",
                    "yaml_path": aff.get("yaml_path", ""),
                    "excerpt_deliverable": f"citation : {citation}",
                    "excerpt_source": f"domaine {module} -> prefixe attendu {expected_prefix}",
                    "source_ref": "reference/prefixes-domaine.md",
                    "challenge": (
                        f"L'entite declare module={module} mais cite un fichier '{fname_basename}' "
                        f"dont le prefixe ne matche pas {expected_prefix} attendu pour ce domaine."
                    ),
                })
    return items


PAGE_PREFIXES = Path(__file__).resolve().parent.parent / "reference" / \
    "prefixes-domaine.md"


def detect(ir: dict) -> dict:
    all_items: list[dict] = []
    warnings_global: list[str] = []

    domain_prefixes = parse_domain_prefixes(PAGE_PREFIXES)
    if not domain_prefixes:
        warnings_global.append(
            "H5 inactive : %s illisible ou sans table. La page est livree avec le "
            "skill -- si elle manque, l'installation est incomplete."
            % PAGE_PREFIXES.name)

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
    ap.add_argument("--out", required=True)
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

    warnings = sum(1 for x in result["items"] if x["severity"] == "warning")
    summary = {
        "category": "E4",
        "warnings_items": warnings,
        "warnings_global": len(result["warnings_global"]),
        "domain_prefixes_loaded": len(parse_domain_prefixes(PAGE_PREFIXES)),
        "out": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
