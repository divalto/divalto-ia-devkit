#!/usr/bin/env python3
"""Ajoute des bindings FK a un Module Check (.dhsp) existant (FK-05).

Pour chaque FK :
- Injecte `Module "Gttmchk<target>.dhop"` dans la section des imports Module
  (apres le dernier Module existant, si pas deja present)
- Ajoute les procedures `Check_<SRC>_Field_<CHAMP>` + `_Lib` a la fin du fichier
  (si pas deja presentes)

Exemptions : pour les cibles comptables (C3, C4, C5, C6, C7, C8, C9), pas de
Module unique dedie (framework CC indirect) -- seules les procedures sont
generees, sans nouveau Module import.

Usage :
    py dhsp_add_fk.py --path <fichier.dhsp> --src-table RACECHIEN \\
        --fk RacPays:T013:9053 --fk RacDev:T007

Parametres :
    --path       : chemin du .dhsp a modifier en place (ISO-8859-1 + CRLF)
    --src-table  : table source en MAJUSCULES (ex RACECHIEN)
    --fk         : repetable, format CHAMP:TARGET[:ZOOM]

Sortie JSON : {path, src_table, modifications, added_modules, added_procs, skipped}

Idempotent : re-executer avec les memes FK ne duplique pas les sections.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


CC_EXEMPT = {"C3", "C4", "C5", "C6", "C7", "C8", "C9"}

MODULE_LINE = re.compile(
    r'^\s*Module\s+"([^"]+\.dhop)"\s*$',
    re.MULTILINE | re.IGNORECASE,
)


def parse_fk_args(fk_args):
    fks = []
    for raw in fk_args:
        parts = raw.split(":")
        if len(parts) < 2:
            print(f"Erreur: --fk '{raw}' invalide.", file=sys.stderr)
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
        if target in CC_EXEMPT:
            module_dhop = None
        else:
            module_dhop = f"Gttmchk{target.lower()}.dhop"
        fks.append({
            "champ": champ,
            "target": target,
            "module_dhop": module_dhop,
            "find_fn": f"Find_{target}",
            "get_lib_fn": f"Get_{target}_Lib",
            "zoom_num": zoom_num,
        })
    return fks


def has_module(text, module_dhop):
    """True si le Module est deja importe (case-insensitive)."""
    if not module_dhop:
        return True  # exempt -> considere 'deja present'
    want = module_dhop.lower()
    for m in MODULE_LINE.finditer(text):
        if m.group(1).lower() == want:
            return True
    return False


def has_proc(text, proc_name):
    """True si la procedure Public function int <proc_name> est deja definie."""
    pat = re.compile(
        rf"Public\s+function\s+int\s+{re.escape(proc_name)}\s*\(",
        re.IGNORECASE,
    )
    return bool(pat.search(text))


def insert_module_imports(text, new_modules):
    """Insere les Modules apres le dernier Module existant.

    Retourne (new_text, liste_inseres).
    """
    inserted = []
    matches = list(MODULE_LINE.finditer(text))
    if not matches:
        return text, inserted
    last_match = matches[-1]
    end_line_pos = text.find("\n", last_match.end())
    if end_line_pos < 0:
        end_line_pos = len(text)
    insert_pos = end_line_pos + 1  # juste apres le \n du dernier Module
    # Formatter les nouvelles lignes (indent "   " comme les entrees T-tables)
    new_lines = []
    for mod in new_modules:
        if not mod:
            continue
        if has_module(text, mod):
            continue
        new_lines.append(f'Module   "{mod}"\r\n')
        inserted.append(mod)
    if not new_lines:
        return text, inserted
    injection = "".join(new_lines)
    new_text = text[:insert_pos] + injection + text[insert_pos:]
    return new_text, inserted


def build_check_procedures(fk, src_table, dict_name, nomvue, prefix_):
    """Genere le code DIVA des 2 procedures Check_*_Field_*(+_Lib) pour une FK."""
    champ = fk["champ"]
    target = fk["target"]
    find_fn = fk["find_fn"]
    get_lib_fn = fk["get_lib_fn"]

    code = []
    code.append("\r\n;*\r\n")
    code.append(
        f";*\t\tProcedure Check_{src_table}_Field_{champ} (FK-05 : auto-generee)\r\n"
    )
    code.append(";*\r\n")
    code.append(f"Public function int Check_{src_table}_Field_{champ}(&{src_table})\r\n")
    code.append(f";controle du champ {champ} (FK vers {target})\r\n")
    code.append(f"Record {dict_name}.dhsd {src_table}\t{src_table}\r\n")
    code.append("1\tret\t\t3,0\r\n")
    code.append("beginf\r\n")
    code.append(
        f'\tif (ret := {prefix_}CheckField(RS_{nomvue}, {src_table}, "{champ}")) <> 0\r\n'
    )
    code.append("\t\tfreturn(ret)\r\n")
    code.append("\tendif\r\n")
    code.append(f"\tfreturn({find_fn}({src_table}.{champ}, context=true))\r\n")
    code.append("endf\r\n")
    code.append("\r\n;*\r\n")
    code.append(
        f"Public function int Check_{src_table}_Field_{champ}_Lib(&{src_table}, &Lib)\r\n"
    )
    code.append(f";controle du champ {champ} + libelle ({get_lib_fn})\r\n")
    code.append(f"Record {dict_name}.dhsd {src_table}\t{src_table}\r\n")
    code.append("1\tLib\t\tA\r\n")
    code.append("1\tret\t\t3,0\r\n")
    code.append("beginf\r\n")
    code.append(f"\tret = Check_{src_table}_Field_{champ}({src_table})\r\n")
    code.append("\tif ret = 0\r\n")
    code.append(f"\t\tLib = {get_lib_fn}\r\n")
    code.append("\telse\r\n")
    code.append("\t\tLib = ' '\r\n")
    code.append("\tendif\r\n")
    code.append("\tfreturn(ret)\r\n")
    code.append("endf\r\n")
    return "".join(code)


def guess_dict_and_vue(text, src_table):
    """Extrait le nom du dictionnaire et du NomVue depuis le .dhsp existant.

    - dict : depuis un `Record '<DICT>.dhsd' <TABLE>` ou `Shared Record '<DICT>.dhsd'`
    - nomvue : depuis `Declaration_<NomVue>` ou `RS_<NomVue>`
    """
    # Dict
    m = re.search(
        rf"Record\s+['\"]?(\w+)\.dhsd['\"]?\s+{re.escape(src_table)}\b",
        text, re.IGNORECASE,
    )
    if m:
        dict_name = m.group(1).upper()
    else:
        # fallback generic
        dict_name = "GTFDD"
    # NomVue : chercher Declaration_<NomVue> ou RS_<NomVue>
    m = re.search(r"Declaration_(\w+)\b", text)
    if m:
        nomvue = m.group(1)
    else:
        m = re.search(r"RS_(\w+)\b", text)
        nomvue = m.group(1) if m else src_table.capitalize()
    return dict_name, nomvue


def guess_prefix(text):
    """Extrait le PREFIX_ (GT_/RT_/CC_...) depuis les appels framework du fichier."""
    m = re.search(
        r"\b(GT_|RT_|GG_|CC_|RC_|PV_|A5_)CheckField\b",
        text,
    )
    return m.group(1) if m else "GT_"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--path", required=True, help="Fichier .dhsp (Module Check) a modifier")
    ap.add_argument(
        "--src-table",
        required=True,
        help="Table source en MAJUSCULES (ex RACECHIEN)",
    )
    ap.add_argument(
        "--fk",
        action="append",
        required=True,
        default=[],
        metavar="CHAMP:TARGET[:ZOOM]",
        help="FK a ajouter, repetable",
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
    src_table = args.src_table.upper()

    dict_name, nomvue = guess_dict_and_vue(text, src_table)
    prefix_ = guess_prefix(text)

    # 1. Insert Module imports (skip duplicates and exempts)
    modules_to_add = [fk["module_dhop"] for fk in fks]
    text, added_modules = insert_module_imports(text, modules_to_add)

    # 2. Append Check_*_Field_* procedures (skip duplicates)
    added_procs = []
    skipped = []
    code_blocks = []
    for fk in fks:
        proc_name = f"Check_{src_table}_Field_{fk['champ']}"
        if has_proc(text, proc_name):
            skipped.append(proc_name)
            continue
        code_blocks.append(
            build_check_procedures(fk, src_table, dict_name, nomvue, prefix_)
        )
        added_procs.append(proc_name)

    if code_blocks:
        # Append at the end
        if not text.endswith("\r\n"):
            text += "\r\n"
        text += "".join(code_blocks)

    # Normaliser CRLF
    text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_bytes(text.encode("iso-8859-1"))

    report = {
        "path": str(path),
        "src_table": src_table,
        "dict_detected": dict_name,
        "nomvue_detected": nomvue,
        "prefix_detected": prefix_,
        "added_modules": added_modules,
        "added_procs": added_procs,
        "skipped_already_present": skipped,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
