#!/usr/bin/env python3
"""extract_codified_values.py -- Extrait les valeurs des choix codifies d'un module DIVA.

S'appuie sur le script vendore `_read_multichoix.py` (copie canonique du skill
`reading-multichoix`) pour lire le fichier ISAM `.dhfi` multichoix et decoder
les 3 Types de multichoix Divalto :

- Type 1 (liste fixe)          : `choix` (libelle) + `valeur` (code retourne)
- Type 3 (lookup dynamique)    : sous-structure enreg/donnee/prefixe/ideb/ifin
                                 qui designe une table cible a resoudre au runtime
- Type 4 (identifiant externe) : `valeur` = IdFic / LstPolice / LstStyleWpf / ...

Enrichit chaque value avec des drapeaux :
- `LabelReference: true`     si le libelle est un nom de bitmap `tbl*`
- `LabelTranslationRef: true` si le libelle est une reference i18n `#<nom>`

Usage :
  py extract_codified_values.py \\
     --dhfi {CHEMIN_FICHIERS}/gtfdmc.dhfi \\
     --partial-json {CHEMIN_FICHIERS}/gtfdmc.json \\
     --output {REPERTOIRE_SORTIE}/doc-erp/DAV/_codified_values.json

Multi-`.dhfi` (resolution cross-modules, ex: DAV->Retail->WM) : passer plusieurs
`--dhfi` (et `--partial-json`). Ordre : premier gagne sur les doublons.

Format de sortie :
  {"Columns": {
     "<nc>": {
       "Type": "1"|"3"|"4",
       "FieldType": "String",
       "AvailableValues": [
         {"Id": "1", "Label": "...", "Value": "...",
          "LabelReference": true?, "LabelTranslationRef": true?, "Color": "..."?}
       ],
       "Lookup": {...}      # Type 3 uniquement
       "ExternId": "IdFic"  # Type 4 uniquement
     }
  }}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
READ_MULTICHOIX = SCRIPT_DIR / "_read_multichoix.py"
READ_FSTYLE = SCRIPT_DIR / "_read_fstyle.py"

TBL_REFERENCE_RE = re.compile(r"^tbl[a-z0-9_]+$", re.IGNORECASE)
TRANSLATION_REF_RE = re.compile(r"^#\S+$")

# Variantes fstyle consultees pour resoudre les libelles `tbl*` en nom canonique.
# Ordre : wpf (moderne, 223 TBL*) puis legacy (73) puis imp (13). Web exclu (0).
FSTYLE_VARIANTS = ["wpf", "legacy", "imp"]


def run_all_details(dhfi_path: Path) -> dict:
    """Appelle `_read_multichoix.py --all-details` et retourne {nc: detail}.

    Force PYTHONIOENCODING=utf-8 pour garantir une sortie UTF-8 stable sur
    Windows (par defaut stdout utilise cp1252 et casse sur les accents).
    """
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        ["py", str(READ_MULTICHOIX), "--file", str(dhfi_path), "--all-details"],
        capture_output=True, env=env,
    )
    if result.returncode not in (0, 1):
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"read_multichoix a echoue sur {dhfi_path} (rc={result.returncode}) :\n{stderr}"
        )
    stdout = result.stdout.decode("utf-8", errors="replace")
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Sortie _read_multichoix invalide : {exc}\n{stdout[:200]}")
    return data.get("multichoix", {})


def build_fstyle_lookup(variants: list[str] = None) -> dict:
    """Construit un lookup {nom_upper: {variant, type, cle_i18n}} depuis les
    variantes fstyle indiquees (defaut wpf -> legacy -> imp, premier gagne).

    Si la DLL ISAM ou les fichiers fstyle*.dhfi sont absents, retourne un dict
    vide : la pipeline fonctionne en degrade, les `tbl*` restent en `_(icone)_`.
    """
    if variants is None:
        variants = FSTYLE_VARIANTS
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    lookup: dict[str, dict] = {}
    for variant in variants:
        result = subprocess.run(
            ["py", str(READ_FSTYLE), "--variant", variant, "--all-details"],
            capture_output=True, env=env,
        )
        if result.returncode not in (0, 1):
            # Fichier absent ou DLL non chargee : on skippe silencieusement,
            # le pipeline est resilient.
            continue
        try:
            data = json.loads(result.stdout.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        for nom, info in (data.get("styles") or {}).items():
            key = (nom or "").upper()
            if not key or key in lookup:
                continue
            lookup[key] = {
                "variant": variant,
                "type": info.get("type", ""),
                "cle_i18n": info.get("cle_i18n", ""),
            }
    return lookup


def convert_to_columns(multichoix: dict, fstyle_lookup: dict = None) -> dict:
    """Convertit le format --all-details vers le format Columns consomme
    en aval par `_sources_parser.parse_choix_values_json`.

    Les drapeaux LabelReference / LabelTranslationRef sont poses sur chaque
    value Type 1 dont le libelle ressemble a un nom de bitmap `tbl*` ou
    a une reference i18n `#<nom>`. Le renderer les remplacera par un
    fallback lisible (voir `render_markdown.render_entity_business`).

    Quand `fstyle_lookup` est fourni et qu'un libelle `tbl*` y trouve une
    correspondance, le champ `FstyleName` est injecte dans la value (ex:
    `TBLART`). Le renderer externe s'en sert pour afficher `_(icone TBLART)_`
    au lieu de `_(icone)_` generique (FS-03 UC-200).
    """
    if fstyle_lookup is None:
        fstyle_lookup = {}
    columns: dict[str, dict] = {}
    for nc, info in multichoix.items():
        mc_type = info.get("type", "") or ""
        col: dict = {"Type": mc_type, "FieldType": "String"}

        if mc_type == "3":
            col["Lookup"] = info.get("lookup") or {}
            col["AvailableValues"] = []  # valeurs resolues au runtime depuis la table cible
        elif mc_type == "4":
            extern_ids = [
                (e.get("valeur") or "").strip()
                for e in info.get("entries", [])
                if (e.get("valeur") or "").strip()
            ]
            if extern_ids:
                col["ExternId"] = extern_ids[0]
            col["AvailableValues"] = []
        else:
            # Type 1 (liste fixe) ou type vide (traite comme liste fixe).
            values = []
            for rank, entry in enumerate(info.get("entries", []), start=1):
                label = (entry.get("choix") or "").strip()
                value = (entry.get("valeur") or "").strip()
                av = {"Id": str(rank), "Label": label, "Value": value}
                if label and TBL_REFERENCE_RE.match(label):
                    av["LabelReference"] = True
                    # FS-03 : enrichissement fstyle. Si le nom est catalogue
                    # dans une variante fstyle, on propage le nom canonique
                    # (normalement = label.upper()) pour le rendu externe.
                    fstyle_match = fstyle_lookup.get(label.upper())
                    if fstyle_match:
                        av["FstyleName"] = label.upper()
                        av["FstyleVariant"] = fstyle_match.get("variant", "")
                elif label and TRANSLATION_REF_RE.match(label):
                    av["LabelTranslationRef"] = True
                values.append(av)
            col["AvailableValues"] = values

        columns[nc] = col
    return columns


def merge_columns_list(columns_list: list[tuple[dict, str]]) -> tuple[dict, dict]:
    """Fusionne plusieurs dict Columns ; premier gagne sur les doublons.

    Retourne (merged, source_by_id). `source_by_id[nc]` = nom du `.dhfi`
    qui a fourni le choix (utile pour l'audit).
    """
    merged: dict = {}
    source: dict[str, str] = {}
    for cols, source_name in columns_list:
        for nc, col in cols.items():
            if nc in merged:
                continue
            merged[nc] = col
            source[nc] = source_name
    return merged, source


def load_partial_json(json_path: Path) -> dict:
    """Charge un `.json` partiel (ISO-8859-1) a cote d'un `.dhfi`.

    Le `.json` partiel existe pour une poignee de choix (~8 sur gtfdmc DAV)
    et apporte la `Color` par value. Il n'est plus la source de verite
    (le `.dhfi` l'est depuis le refactor 2026-04-24).
    """
    if not json_path.exists():
        return {}
    try:
        data = json.loads(json_path.read_text(encoding="iso-8859-1"))
    except json.JSONDecodeError as exc:
        print(f"WARN : {json_path} illisible ({exc}), ignore", file=sys.stderr)
        return {}
    return data.get("Columns", {})


def merge_json_list(json_paths: list[Path]) -> dict:
    """Fusionne plusieurs `.json` partiels ; premier gagne sur les doublons."""
    merged: dict = {}
    for path in json_paths:
        cols = load_partial_json(path)
        for nc, col in cols.items():
            merged.setdefault(nc, col)
    return merged


def merge_partial_json_colors(merged: dict, partial_cols: dict) -> dict:
    """Injecte la `Color` des values presentes dans le `.json` partiel.

    Matching par `Id`. Les autres champs du merged (Type, Lookup, ExternId,
    flags tbl/#) sont preserves inchanges.
    """
    for nc, partial in partial_cols.items():
        if nc not in merged:
            continue
        partial_by_id = {
            av.get("Id"): av for av in partial.get("AvailableValues") or []
        }
        for av in merged[nc].get("AvailableValues", []):
            partial_av = partial_by_id.get(av.get("Id"))
            if partial_av and partial_av.get("Color"):
                av["Color"] = partial_av["Color"]
    return merged


def compute_stats(merged: dict) -> dict:
    total_values = sum(len(v.get("AvailableValues", [])) for v in merged.values())
    by_type: dict[str, int] = {}
    tbl_refs = translation_refs = extern_ids = with_color = empty_labels = 0
    fstyle_resolved = 0
    for col in merged.values():
        t = col.get("Type", "") or "(vide)"
        by_type[t] = by_type.get(t, 0) + 1
        if col.get("ExternId"):
            extern_ids += 1
        for av in col.get("AvailableValues", []):
            if av.get("LabelReference"):
                tbl_refs += 1
                if av.get("FstyleName"):
                    fstyle_resolved += 1
            if av.get("LabelTranslationRef"):
                translation_refs += 1
            if av.get("Color"):
                with_color += 1
            if not (av.get("Label") or "").strip():
                empty_labels += 1
    return {
        "choix_ids": len(merged),
        "total_values": total_values,
        "by_type": by_type,
        "tbl_references": tbl_refs,
        "tbl_references_resolved_fstyle": fstyle_resolved,
        "translation_references": translation_refs,
        "extern_ids": extern_ids,
        "choix_with_color": with_color,
        "empty_labels": empty_labels,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--dhfi",
        required=True,
        action="append",
        help=(
            "Chemin d'un .dhfi multichoix (ex: gtfdmc.dhfi). Repetable : passer "
            "plusieurs --dhfi pour resoudre les choix cross-modules (ex: NATURE defini "
            "dans rtfdmc.dhfi mais utilise par DAV.CLI). Ordre : le premier .dhfi prime "
            "sur les suivants pour un meme nc."
        ),
    )
    ap.add_argument(
        "--partial-json",
        action="append",
        default=[],
        help=(
            "Chemin d'un .json partiel a cote d'un .dhfi (optionnel, apporte la Color). "
            "Repetable pour plusieurs modules. Ordre : le premier .json prime."
        ),
    )
    ap.add_argument("--output", required=True, help="JSON de sortie (Columns format enrichi)")
    args = ap.parse_args()

    dhfi_paths = [Path(p) for p in args.dhfi]
    for p in dhfi_paths:
        if not p.exists():
            print(json.dumps({"error": f"dhfi introuvable : {p}"}), file=sys.stderr)
            return 1

    # FS-03 : batir le lookup fstyle une fois en amont pour enrichir les tbl*
    fstyle_lookup = build_fstyle_lookup()

    columns_list: list[tuple[dict, str]] = []
    for p in dhfi_paths:
        multichoix = run_all_details(p)
        columns_list.append((convert_to_columns(multichoix, fstyle_lookup), p.name))

    merged, source_by_id = merge_columns_list(columns_list)

    json_paths = [Path(p) for p in args.partial_json]
    partial_cols = merge_json_list(json_paths)
    merged = merge_partial_json_colors(merged, partial_cols)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"Columns": merged}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    source_counts = Counter(source_by_id.values())
    summary = {
        "dhfi": [str(p) for p in dhfi_paths],
        "partial_json": [str(p) for p in json_paths] or ["(absent)"],
        "output": str(out_path),
        **compute_stats(merged),
        "choix_by_dhfi_source": dict(source_counts),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
