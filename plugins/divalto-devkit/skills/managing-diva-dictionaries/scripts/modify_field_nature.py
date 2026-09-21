#!/usr/bin/env python3
"""Modifie la Nature d'un champ existant dans un .dhsd et re-propage les positions.

Le skill couvre l'AJOUT de table (generate_dhsd_block) et la surcharge
(generate_surcharge_field) mais pas la MODIFICATION de la Nature d'un champ
deja declare. Or changer une Nature decale toutes les positions des champs
suivants dans chaque [TABLE]/[CHAMPS] et chaque [INDEX]/[CHAMPS] qui l'utilisent.

Cas reel : alignement d'un dictionnaire lors d'une migration de version ERP
(reprise du specifique d'une version a une autre).

Ce script :
  1. lit la Nature actuelle du champ dans son bloc [CHAMP] global ;
  2. calcule delta = taille(nouvelle Nature) - taille(ancienne) ;
  3. met a jour la ligne Nature= du [CHAMP] ;
  4. pour chaque [TABLE] contenant le champ : decale les champs en aval ;
  5. pour chaque [INDEX] contenant le champ : recalcule les offsets cumules ;
  6. politique Filler : shift (defaut) ou cannibalize ;
  7. reecrit en ISO-8859-1 + CRLF (+ .bak) et valide via validate_dhsd.

Usage :
    py modify_field_nature.py --path <dict.dhsd> --field <Nom> --new-nature <code>
       [--filler-policy shift|cannibalize] [--tables T1,T2|ALL]
       [--dry-run] [--no-backup]

Sortie JSON: {field, old_nature, new_nature, delta, tables[], indexes[],
              warnings[], validation[]}
Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne

Limites v1 (signalees, non traitees) :
  - couche relationnelle [CHAMPL] (records logiques RecordSQL) NON re-propagee
    -> warning si le champ y figure (: angle mort de l'arbitrage) ;
  - champs tableau (Nature avec '*', repetition != 0) et multi-table composite
    -> refuses (rediger a la main, cf reference/dhsd-surcharge-pattern.md).
"""

import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nature_to_size import nature_to_size
from validate_dhsd import validate_dhsd_file

ENCODING = "iso-8859-1"

_NOM_RE = re.compile(r'^(\s*)Nom=(.*)$')
_TAILLE_RE = re.compile(r'^(\s*)Taille=(.*)$')
_NATURE_RE = re.compile(r'^(\s*)Nature=(.*)$')


def read_lines(path):
    """Lit le .dhsd en binaire et renvoie (lignes, eol) en preservant CRLF."""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode(ENCODING)
    return text.split("\r\n")


def _size_of(nature):
    info = nature_to_size(nature)
    return info["size"] if info else None


def _nom_name(line):
    """Renvoie le nom d'une ligne Nom=NAME,... ou None."""
    m = _NOM_RE.match(line)
    if not m:
        return None
    return m.group(2).split(",")[0]


def _nom_pos(line):
    """Renvoie la position (int parts[1]) d'une ligne Nom=NAME,POS,... ou None."""
    m = _NOM_RE.match(line)
    if not m:
        return None
    parts = m.group(2).split(",")
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _set_nom_pos(line, new_pos):
    m = _NOM_RE.match(line)
    parts = m.group(2).split(",")
    parts[1] = str(new_pos)
    return f"{m.group(1)}Nom={','.join(parts)}"


def _nom_repetition(line):
    """parts[5] d'une ligne table [CHAMPS] (taille pour Filler, 0 sinon)."""
    m = _NOM_RE.match(line)
    parts = m.group(2).split(",")
    if len(parts) < 6:
        return None
    try:
        return int(parts[5])
    except ValueError:
        return None


def _set_nom_repetition(line, new_rep):
    m = _NOM_RE.match(line)
    parts = m.group(2).split(",")
    parts[5] = str(new_rep)
    return f"{m.group(1)}Nom={','.join(parts)}"


def find_field_nature(lines, field):
    """Trouve le bloc [CHAMP] global du champ : (index ligne Nature=, valeur)."""
    i, n = 0, len(lines)
    while i < n:
        if lines[i].strip() == "[CHAMP]":
            j = i + 1
            this_name = None
            nature_idx = None
            while j < n and lines[j].strip() != "[CHAMP]":
                s = lines[j].strip()
                if s.startswith("Nom=") and this_name is None:
                    this_name = s[4:].split(",")[0]
                elif s.startswith("Nature="):
                    nature_idx = j
                j += 1
            if this_name == field and nature_idx is not None:
                return nature_idx, lines[nature_idx].strip()[7:]
            i = j
        else:
            i += 1
    return None, None


def count_champl_usage(lines, field):
    """Compte les records relationnels [CHAMPL] referencant le champ."""
    count = 0
    in_champl = False
    for line in lines:
        s = line.strip()
        if s == "[CHAMPL]":
            in_champl = True
        elif s == "[/CHAMPL]":
            in_champl = False
        elif in_champl and _nom_name(line) == field:
            count += 1
    return count


def iter_blocks(lines, opener):
    """Genere (start, end, name) pour chaque bloc [opener] ... avec son [CHAMPS].

    name = valeur du 1er Nom= avant [CHAMPS]. start/end bornent le bloc complet
    (du [opener] jusqu'a la fin de son [/CHAMPS]).
    """
    i, n = 0, len(lines)
    tag = f"[{opener}]"
    while i < n:
        if lines[i].strip() == tag:
            name = None
            champs_start = champs_end = None
            j = i + 1
            in_champs = False
            while j < n:
                s = lines[j].strip()
                if s == tag:
                    break
                if not in_champs and s.startswith("Nom=") and name is None:
                    name = s[4:].split(",")[0]
                elif s == "[CHAMPS]":
                    in_champs = True
                    champs_start = j
                elif s == "[/CHAMPS]":
                    champs_end = j
                    break
                j += 1
            if name is not None and champs_start is not None and champs_end is not None:
                yield (i, champs_start, champs_end, name)
            i = j if j > i else i + 1
        else:
            i += 1


def apply_to_table(lines, champs_start, champs_end, field, delta, policy):
    """Decale les positions dans un bloc table [CHAMPS]. Retourne dict ou None.

    Renvoie {field_pos, shifted, taille_before, taille_after, filler:{...}} si le
    champ est present, sinon None. Leve ValueError si cannibalize impossible.
    """
    field_pos = None
    for k in range(champs_start + 1, champs_end):
        if _nom_name(lines[k]) == field:
            field_pos = _nom_pos(lines[k])
            break
    if field_pos is None:
        return None

    # localiser la ligne Taille= du bloc (avant [CHAMPS])
    taille_idx = None
    for k in range(champs_start - 1, max(champs_start - 40, -1), -1):
        if _TAILLE_RE.match(lines[k]):
            taille_idx = k
            break

    info = {"field_pos": field_pos, "shifted": 0, "filler": None}

    if policy == "shift":
        for k in range(champs_start + 1, champs_end):
            pos = _nom_pos(lines[k])
            if pos is not None and pos > field_pos:
                lines[k] = _set_nom_pos(lines[k], pos + delta)
                info["shifted"] += 1
        if taille_idx is not None:
            m = _TAILLE_RE.match(lines[taille_idx])
            parts = m.group(2).split(",")
            t0 = int(parts[0])
            parts[0] = str(t0 + delta)
            lines[taille_idx] = f"{m.group(1)}Taille={','.join(parts)}"
            info["taille_before"], info["taille_after"] = t0, t0 + delta
        return info

    # cannibalize : Filler apres le champ absorbe delta, Taille inchangee
    filler_k = filler_pos = None
    for k in range(champs_start + 1, champs_end):
        if _nom_name(lines[k]) == "Filler":
            p = _nom_pos(lines[k])
            if p is not None and p > field_pos:
                filler_k, filler_pos = k, p
                break
    if filler_k is None:
        raise ValueError(f"cannibalize impossible : aucun Filler apres '{field}'")
    rep = _nom_repetition(lines[filler_k])
    if rep is None or rep < delta:
        raise ValueError(
            f"cannibalize impossible : Filler={rep} < delta={delta} "
            f"(reserve insuffisante)")
    # champs entre le champ et le Filler : +delta ; apres le Filler : inchanges
    for k in range(champs_start + 1, champs_end):
        pos = _nom_pos(lines[k])
        if pos is not None and field_pos < pos < filler_pos:
            lines[k] = _set_nom_pos(lines[k], pos + delta)
            info["shifted"] += 1
    # Filler : decale de +delta et reduit de delta
    lines[filler_k] = _set_nom_pos(lines[filler_k], filler_pos + delta)
    lines[filler_k] = _set_nom_repetition(lines[filler_k], rep - delta)
    info["filler"] = {"size_before": rep, "size_after": rep - delta}
    info["taille_before"] = info["taille_after"] = None  # inchangee
    return info


def apply_to_index(lines, champs_start, champs_end, field, delta):
    """Decale les offsets cumules d'un index apres le champ. Retourne shifted/None."""
    field_pos = None
    for k in range(champs_start + 1, champs_end):
        if _nom_name(lines[k]) == field:
            field_pos = _nom_pos(lines[k])
            break
    if field_pos is None:
        return None
    shifted = 0
    for k in range(champs_start + 1, champs_end):
        pos = _nom_pos(lines[k])
        if pos is not None and pos > field_pos:
            lines[k] = _set_nom_pos(lines[k], pos + delta)
            shifted += 1
    return {"field_pos": field_pos, "shifted": shifted}


def main():
    parser = argparse.ArgumentParser(
        description="Modifie la Nature d'un champ dans un .dhsd et re-propage les positions")
    parser.add_argument("--path", required=True, help="Chemin du .dhsd a modifier")
    parser.add_argument("--field", required=True, help="Nom du champ a modifier")
    parser.add_argument("--new-nature", required=True, help="Nouvelle Nature (ex: 8, 50, 5,0)")
    parser.add_argument("--filler-policy", choices=["shift", "cannibalize"],
                        default="shift",
                        help="shift (defaut, record grandit) ou cannibalize (Filler absorbe, Taille constante)")
    parser.add_argument("--dry-run", action="store_true", help="Previsualiser sans ecrire")
    parser.add_argument("--no-backup", action="store_true", help="Ne pas creer de .bak")
    args = parser.parse_args()

    if not os.path.isfile(args.path):
        print(f"ERREUR : fichier introuvable : {args.path}", file=sys.stderr)
        sys.exit(1)

    lines = read_lines(args.path)

    # 1. Nature actuelle
    nat_idx, old_nature = find_field_nature(lines, args.field)
    if nat_idx is None:
        print(f"ERREUR : champ '{args.field}' sans bloc [CHAMP]/Nature= : "
              f"modification impossible", file=sys.stderr)
        sys.exit(1)

    # Refus v1 : tableau (Nature avec '*')
    if "*" in old_nature or "*" in args.new_nature:
        print(f"ERREUR : champ tableau (Nature='{old_nature}' -> '{args.new_nature}') "
              f"non supporte en v1 (rediger a la main)", file=sys.stderr)
        sys.exit(1)

    old_size = _size_of(old_nature)
    new_size = _size_of(args.new_nature)
    if old_size is None:
        print(f"ERREUR : ancienne Nature '{old_nature}' non resolue par nature_to_size",
              file=sys.stderr)
        sys.exit(1)
    if new_size is None:
        print(f"ERREUR : nouvelle Nature '{args.new_nature}' non resolue par nature_to_size",
              file=sys.stderr)
        sys.exit(1)

    delta = new_size - old_size
    warnings = []

    if delta == 0:
        warnings.append(f"delta=0 (taille inchangee {old_size}o) : seule la Nature est mise a jour")

    # 2. detecter usage [CHAMPL] (non re-propage)
    champl_n = count_champl_usage(lines, args.field)
    if champl_n:
        warnings.append(
            f"[CHAMPL] : champ present dans {champl_n} record(s) relationnel(s) -- "
            f"positions NON re-propagees (limite connue de cette version). Verifier manuellement.")

    # 3. mettre a jour la Nature du [CHAMP] global
    m = _NATURE_RE.match(lines[nat_idx])
    lines[nat_idx] = f"{m.group(1)}Nature={args.new_nature}"

    # 4-5. propager dans les tables puis les index
    tables_report = []
    cannibalize_errors = []
    for (_blk, cs, ce, tname) in list(iter_blocks(lines, "TABLE")):
        # refus tableau : repetition != 0 sur la ligne du champ
        for k in range(cs + 1, ce):
            if _nom_name(lines[k]) == args.field:
                rep = _nom_repetition(lines[k])
                if rep not in (0, None):
                    print(f"ERREUR : champ '{args.field}' avec repetition={rep} dans "
                          f"table '{tname}' (tableau/composite) non supporte en v1",
                          file=sys.stderr)
                    sys.exit(1)
                break
        try:
            info = apply_to_table(lines, cs, ce, args.field, delta, args.filler_policy)
        except ValueError as e:
            cannibalize_errors.append({"table": tname, "error": str(e)})
            continue
        if info is not None:
            info["table"] = tname
            tables_report.append(info)

    indexes_report = []
    for (_blk, cs, ce, iname) in list(iter_blocks(lines, "INDEX")):
        info = apply_to_index(lines, cs, ce, args.field, delta)
        if info is not None:
            info["index"] = iname
            indexes_report.append(info)

    if cannibalize_errors:
        print(json.dumps({
            "field": args.field, "error": "cannibalize impossible sur certaines tables",
            "details": cannibalize_errors,
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

    if not tables_report and not indexes_report:
        warnings.append(f"champ '{args.field}' absent des tables/index (selon --tables)")

    result = {
        "field": args.field,
        "old_nature": old_nature,
        "new_nature": args.new_nature,
        "old_size": old_size,
        "new_size": new_size,
        "delta": delta,
        "filler_policy": args.filler_policy,
        "tables": tables_report,
        "indexes": indexes_report,
        "warnings": warnings,
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        result["validation"] = "skipped (dry-run)"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # 7. ecriture ISO-8859-1 + CRLF (+ .bak)
    if not args.no_backup:
        shutil.copy2(args.path, args.path + ".bak")
        result["backup"] = args.path + ".bak"
    output = "\r\n".join(lines)
    with open(args.path, "wb") as f:
        f.write(output.encode(ENCODING))

    # validate_dhsd sur chaque table modifiee (filet de securite), en mode migration
    # : le DICT03 preexistant ne doit pas masquer le signal DICT01/DICT02.
    validation = []
    for t in tables_report:
        v = validate_dhsd_file(args.path, t["table"], migration=True)
        validation.append({
            "table": t["table"], "valid": v["valid"],
            "errors": v["errors"], "warnings": v["warnings"],
        })
    result["validation"] = validation
    result["valid"] = all(v["valid"] for v in validation) if validation else True

    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
