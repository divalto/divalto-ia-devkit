#!/usr/bin/env python3
"""Ajoute des bindings "FK par zoom standard" a un .dhsf existant (FK-03).

Pour chaque FK declaree :
- Localise le bloc [champ] dont `donnee=<vue>,<champ>,<vue>` match (case-insensitive)
- Injecte ou enrichit les sous-sections :
    [param_saisie] : `table_associee=oui`
    [touches]      : `f8=<zoom>`
    [traitements]  : `diva_apres="Champ_<C>_<id>_Ap"`
    [boutons]      : entry `"zoom"` si absente
- Ajoute la procedure callback `Champ_<C>_<id>_Ap` dans la section [diva]
  juste avant `[/diva]`, appelant `Check_<SRC>_Field_<C>_Lib` du Module Check

Le `<id>` dans les noms de procedures est un compteur sequentiel global
alloue au fichier (pas l'id widget DOM).

Usage :
    py dhsf_add_fk.py --path <fichier.dhsf> --rsql RaceChienSQL \\
        --src-table RaceChien \\
        --fk Pay:T013:9053 --fk Dev:T007:9047

Parametres :
    --path       : chemin du .dhsf a modifier (en place)
    --rsql       : nom du RecordSql (ex RaceChienSQL) -- utilise dans
                   l'appel callback `<rsql>.<src_table>` et `<rsql>.<champ>_Lib`
    --src-table  : nom de la table source case mixte (ex RaceChien)
                   utilise dans `<rsql>.<src_table>` ; sa version uppercase
                   sert au nom de fonction `Check_<SRC_UPPER>_Field_<C>_Lib`
    --fk         : repetable, format `CHAMP:TARGET[:ZOOM]`

Pattern callback genere (conforme pattern DAV vu sur gtez027_sql.dhsf:2675,
gtez067_sql.dhsf:1349, gteedtr000.dhsf:42611) :
    Check_<SRC_UPPER>_Field_<CHAMP>_Lib(<rsql>.<src_table>, <rsql>.<CHAMP>_Lib)
La procedure Check_*_Field_*_Lib est generee par `generating-objet-metier --fk`
dans le Module Check de la source (ne pas dedoubler ici).

Sortie JSON : {path, modifications, proc_ids_generes, warnings}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing FK args
# ---------------------------------------------------------------------------

def parse_fk_args(fk_args):
    """['RacPays:T013:9053'] -> [{champ, target, zoom_num, ...}]."""
    fks = []
    for raw in fk_args:
        parts = raw.split(":")
        if len(parts) < 2:
            print(f"Erreur: --fk '{raw}' invalide (format CHAMP:TARGET[:ZOOM]).", file=sys.stderr)
            sys.exit(1)
        champ = parts[0].strip()
        target = parts[1].strip()
        zoom_num = None
        if len(parts) >= 3 and parts[2].strip():
            try:
                zoom_num = int(parts[2].strip())
            except ValueError:
                print(f"Erreur: --fk '{raw}' zoom doit etre entier.", file=sys.stderr)
                sys.exit(1)
        fks.append({
            "champ": champ,
            "target": target,
            "zoom_num": zoom_num,
        })
    return fks


# ---------------------------------------------------------------------------
# Scan des procedures Champ_*_Ap existantes (pour compteur sequentiel global)
# ---------------------------------------------------------------------------

CHAMP_AP_PROC = re.compile(
    r"public\s+procedure\s+(Champ_\w+_(\d+)_Ap)\b",
    re.IGNORECASE,
)


def next_proc_id(text):
    """Retourne le plus grand id + 1 parmi les procedures Champ_*_<id>_Ap."""
    max_id = 0
    for m in CHAMP_AP_PROC.finditer(text):
        try:
            n = int(m.group(2))
            if n > max_id:
                max_id = n
        except ValueError:
            continue
    return max_id + 1


# ---------------------------------------------------------------------------
# Localisation d'un bloc [champ] dans un .dhsf
# ---------------------------------------------------------------------------

CHAMP_BLOCK_START = re.compile(r"^(\s*)\[champ\]\s*$", re.MULTILINE)
DONNEE_LINE = re.compile(
    r"^\s*donnee\s*=\s*[^,]*,\s*(\S+?)\s*(?:,.*)?$",
    re.MULTILINE | re.IGNORECASE,
)


def find_champ_blocks(text):
    """Liste des (start_pos, end_pos, indent, donnee_champ_name) pour chaque bloc [champ].

    Un bloc [champ] se termine a la prochaine ligne dont l'indentation est <= celle
    du [champ] et qui contient un [xxx] (prochain element ou prochaine section).
    """
    lines = text.splitlines(keepends=True)
    # Positions cumulees
    positions = [0]
    for l in lines:
        positions.append(positions[-1] + len(l))

    blocks = []
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)\[champ\]\s*$", line)
        if not m:
            continue
        indent = m.group(1)
        indent_len = len(indent)
        start = positions[i]
        end = len(text)
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if not nxt.strip():
                continue
            nm = re.match(r"^(\s*)\[[a-z_/]+\]", nxt, re.IGNORECASE)
            if nm and len(nm.group(1)) <= indent_len:
                end = positions[j]
                break
        segment = text[start:end]
        dm = DONNEE_LINE.search(segment)
        if not dm:
            continue
        donnee_champ = dm.group(1).strip().lower()
        blocks.append({
            "start": start,
            "end": end,
            "indent": indent,
            "donnee_champ": donnee_champ,
        })
    return blocks


def find_block_for_fk(blocks, champ_name):
    """Retourne le premier bloc qui correspond au champ FK (match sur donnee)."""
    target = champ_name.lower()
    for b in blocks:
        if b["donnee_champ"] == target:
            return b
    return None


# ---------------------------------------------------------------------------
# Enrichissement d'un bloc [champ] existant
# ---------------------------------------------------------------------------

SUB_SECTION = re.compile(
    r"^(\s+)\[(param_saisie|touches|traitements|boutons)\]\s*$",
    re.MULTILINE,
)


def enrich_champ_block(block_text, fk, proc_id, indent_elt):
    """Retourne block_text enrichi avec f8, table_associee, diva_apres, bouton zoom.

    Strategie : pour chaque sous-section voulue, si elle existe deja, on y ajoute
    l'attribut (sans ecraser les valeurs existantes). Sinon on cree la sous-section.
    """
    # Indent sub-section : indent_elt + 1 space (INDENT_2 = indent_elt + " ")
    # Indent attribut : indent_elt + 2 spaces (INDENT_3 = indent_elt + "  ")
    indent_sub = indent_elt + " "
    indent_attr = indent_elt + "  "
    lines = block_text.splitlines(keepends=True)

    # Collect existing sub-section boundaries (start_line_idx for each)
    subs = {}  # name -> (start_idx, end_idx) inclusive of the header line
    cur_name = None
    cur_start = None
    for i, line in enumerate(lines):
        ms = re.match(r"^\s+\[(\w+)\]\s*$", line)
        if ms:
            # End previous sub-section
            if cur_name is not None:
                subs[cur_name] = (cur_start, i - 1)
            name = ms.group(1).lower()
            if name in ("presentation", "description", "param_saisie",
                       "touches", "traitements", "boutons"):
                cur_name = name
                cur_start = i
            else:
                cur_name = None
                cur_start = None
    if cur_name is not None:
        subs[cur_name] = (cur_start, len(lines) - 1)

    champ = fk["champ"]
    target = fk["target"]
    zoom_num = fk["zoom_num"]

    # Operations : liste (sub_section, attribute_line)
    ops = []
    ops.append(("param_saisie", f"{indent_attr}table_associee=oui\r\n"))
    if zoom_num:
        ops.append(("touches", f"{indent_attr}f8={zoom_num}\r\n"))
    ops.append(("traitements", f'{indent_attr}diva_apres="Champ_{champ}_{proc_id}_Ap"\r\n'))
    ops.append(("boutons", f'{indent_attr}"zoom"\r\n'))

    # Appliquer les ops (inserts from end to start to preserve indices)
    # Grouper par sub-section, chacune appliquee une fois
    by_section = {}
    for sec, line in ops:
        by_section.setdefault(sec, []).append(line)

    # Process in reverse order of existing sub-sections to preserve indices
    existing_sorted = sorted(subs.items(), key=lambda x: -x[1][0])
    result = list(lines)
    handled = set()
    for sec_name, (s_idx, e_idx) in existing_sorted:
        if sec_name in by_section:
            # Insert new attribute(s) right after the header line
            insert_point = s_idx + 1
            new_attrs = by_section[sec_name]
            # Skip if already present (idempotence basique : exact match)
            existing_block = "".join(result[s_idx:e_idx + 1])
            attrs_to_add = [a for a in new_attrs if a.strip() not in existing_block]
            if attrs_to_add:
                for j, attr in enumerate(attrs_to_add):
                    result.insert(insert_point + j, attr)
            handled.add(sec_name)

    # Pour les sections manquantes : les creer a la fin du bloc
    missing = [s for s in by_section if s not in handled]
    if missing:
        # Append at end of the block (before trailing newlines)
        # Find last non-empty line index
        tail = []
        for sec in missing:
            tail.append(f"{indent_sub}[{sec}]\r\n")
            for attr in by_section[sec]:
                tail.append(attr)
        result.extend(tail)

    return "".join(result)


# ---------------------------------------------------------------------------
# Injection procedure dans [diva]
# ---------------------------------------------------------------------------

DIVA_END = re.compile(r"^\[/diva\]\s*$", re.MULTILINE)


def inject_diva_procedures(text, fks_with_ids, src_table_upper, src_table_mixed, rsql):
    """Injecte les procedures Champ_<C>_<id>_Ap avant [/diva].

    Pattern callback :
        Check_<SRC_UPPER>_Field_<CHAMP>_Lib(<rsql>.<src_table_mixed>, <rsql>.<CHAMP>_Lib)
    """
    procs_code = []
    procs_code.append("\r\n;-- Procedures callback FK (auto-generees via --fk)\r\n")
    for fk, proc_id in fks_with_ids:
        champ = fk["champ"]
        procs_code.append("\r\n")
        procs_code.append(f";*\r\n")
        procs_code.append(f"public procedure Champ_{champ}_{proc_id}_Ap\r\n")
        procs_code.append(f";controle champ {champ} (FK vers {fk['target']})\r\n")
        procs_code.append(f"beginp\r\n")
        procs_code.append(
            f"\tCheck_{src_table_upper}_Field_{champ}_Lib"
            f"({rsql}.{src_table_mixed}, {rsql}.{champ}_Lib)\r\n"
        )
        procs_code.append(f"endp\r\n")

    injection = "".join(procs_code)

    # Trouver le PREMIER [/diva] (le template a parfois 2 [/diva])
    m = DIVA_END.search(text)
    if not m:
        return text, "Section [/diva] non trouvee"
    insert_pos = m.start()
    new_text = text[:insert_pos] + injection + text[insert_pos:]
    return new_text, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--path", required=True, help="Fichier .dhsf a modifier en place")
    ap.add_argument(
        "--rsql",
        required=True,
        help="Nom du RecordSql case mixte (ex RaceChienSQL). "
             "Utilise dans <rsql>.<src_table> et <rsql>.<champ>_Lib.",
    )
    ap.add_argument(
        "--src-table",
        required=True,
        help="Nom de la table source en case mixte (ex RaceChien). "
             "Sa version uppercase sert pour Check_<SRC>_Field_<C>_Lib.",
    )
    ap.add_argument(
        "--fk",
        action="append",
        default=[],
        required=True,
        metavar="CHAMP:TARGET[:ZOOM]",
        help="FK a ajouter, repetable. Ex --fk Pay:T013:9053",
    )
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Fichier introuvable : {path}", file=sys.stderr)
        sys.exit(1)

    raw = path.read_bytes()
    try:
        text = raw.decode("iso-8859-1")
    except Exception as exc:
        print(f"Erreur decodage : {exc}", file=sys.stderr)
        sys.exit(2)

    fks = parse_fk_args(args.fk)
    src_table_mixed = args.src_table
    src_table_upper = args.src_table.upper()
    rsql = args.rsql

    # Compteur sequentiel demarre apres le max existant
    proc_id = next_proc_id(text)

    warnings = []
    modifications = []

    # Localiser tous les blocs [champ]
    blocks = find_champ_blocks(text)

    # Pour chaque FK : enrichir le bloc si trouve, sinon warning
    fks_with_ids = []
    # Traitement from end to start pour preserver les indices
    fk_order = []
    for fk in fks:
        fks_with_ids.append((fk, proc_id))
        fk_order.append((fk, proc_id))
        proc_id += 1

    # Enrichissement des blocs (reverse order pour preserver les positions dans text)
    # Re-parse blocks a chaque iteration pour eviter les desynchros d'offsets
    for fk, pid in reversed(fk_order):
        blocks = find_champ_blocks(text)
        blk = find_block_for_fk(blocks, fk["champ"])
        if not blk:
            warnings.append(f"Bloc [champ] pour '{fk['champ']}' non trouve -- callback genere mais bloc [champ] a completer manuellement.")
            continue
        block_text = text[blk["start"]:blk["end"]]
        enriched = enrich_champ_block(block_text, fk, pid, blk["indent"])
        if enriched != block_text:
            text = text[:blk["start"]] + enriched + text[blk["end"]:]
            modifications.append(f"[champ] '{fk['champ']}' enrichi (f8={fk['zoom_num']}, diva_apres, bouton)")

    # Injecter les procedures dans [diva]
    text, err = inject_diva_procedures(
        text, fks_with_ids, src_table_upper, src_table_mixed, rsql
    )
    if err:
        warnings.append(err)
    else:
        modifications.append(f"{len(fks_with_ids)} procedures Champ_*_Ap ajoutees dans [diva]")

    # Normaliser CRLF
    text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_bytes(text.encode("iso-8859-1"))

    # Post-modification : valider le layout groupbox / bornes grille (R-007 2026-04-23).
    # Import tardif pour ne pas introduire de dep si le parser est indisponible.
    post_validation = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from dhsf_parser import parse_dhsf
        from dhsf_modify import validate_groupbox_layout
        post_validation = validate_groupbox_layout(parse_dhsf(str(path)))
    except Exception as exc:  # noqa: BLE001
        post_validation = {"valid": None, "error": f"post-validation skipped: {exc}"}

    report = {
        "path": str(path),
        "rsql": rsql,
        "src_table": src_table_mixed,
        "src_table_upper": src_table_upper,
        "fks_count": len(fks),
        "modifications": modifications,
        "proc_ids_generes": [f"Champ_{fk['champ']}_{pid}_Ap" for fk, pid in fks_with_ids],
        "warnings": warnings,
        "post_validation": post_validation,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not warnings else 0


if __name__ == "__main__":
    sys.exit(main())
