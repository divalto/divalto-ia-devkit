#!/usr/bin/env python3
"""Modifie les tables d'un dictionnaire DIVA (.dhsd).

Actions:
    list-fields   Liste les champs d'une table avec natures et positions
    add-field     Ajoute un champ dans une table
    modify-field  Modifie la nature d'un champ existant
    remove-field  Supprime un champ d'une table

Usage:
    py modify_dhsd_table.py --action list-fields --dhsd PATH --table TABLE
    py modify_dhsd_table.py --action add-field --dhsd PATH --table TABLE --name FIELD --nature NATURE [--after FIELD] [--dry-run] [--backup]
    py modify_dhsd_table.py --action modify-field --dhsd PATH --table TABLE --name FIELD --new-nature NATURE [--dry-run] [--backup]
    py modify_dhsd_table.py --action remove-field --dhsd PATH --table TABLE --name FIELD [--dry-run] [--backup]

Sortie JSON sur stdout, erreurs sur stderr.
Exit codes:
    0 = succes
    1 = erreur utilisateur (argument invalide, Nature invalide, champ deja existant, champ standard protege)
    2 = ressource introuvable (fichier .dhsd absent, table ou champ non trouve)
    3 = erreur interne (exception non previsible)
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _nature_to_size import nature_to_size

ENCODING = "iso-8859-1"

STANDARD_SIZES = {
    "Ce1": 1, "Ce2": 1, "Ce3": 1, "Ce4": 1, "Ce5": 1,
    "Ce6": 1, "Ce7": 1, "Ce8": 1, "Ce9": 1, "CeA": 1,
    "CeB": 1, "CeC": 1, "Ce": 10,
    "Dos": 3, "UserCr": 30, "UserMo": 30, "UserTrace": 50,
}
STANDARD_FIELDS = set(STANDARD_SIZES.keys())


def is_u_field(name, table_name):
    """Detecte si un champ est le U-field (zone libre utilisateur) de la table.

    Le nom du U-field est "U" + nom_table. La casse peut varier selon
    les versions historiques du dictionnaire (UArt / UAdriso / UArtGarantie),
    on compare donc en minuscules.
    """
    if table_name is None:
        return False
    return name.lower() == f"u{table_name}".lower()


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def read_dhsd(path):
    """Lit un .dhsd et renvoie la liste de lignes (sans fin de ligne)."""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode(ENCODING)
    return text.replace("\r\n", "\n").split("\n")


def write_dhsd(path, lines, backup=False):
    """Ecrit un .dhsd en ISO-8859-1 + CRLF."""
    if backup:
        shutil.copy2(path, path + ".bak")
    data = "\r\n".join(lines)
    with open(path, "wb") as f:
        f.write(data.encode(ENCODING))


def get_field_size(name, champ_natures, table_name=None):
    """Renvoie la taille d'un champ a partir de son nom et des natures declarees.

    Pour le U-field (zone libre utilisateur) : renvoie 0. Sa taille reelle est
    implicite (absorbee par la Taille totale de la table) et ne contribue pas au
    cumul des positions car c'est toujours le dernier champ.
    """
    if name in STANDARD_SIZES:
        return STANDARD_SIZES[name]
    if is_u_field(name, table_name):
        return 0
    if name in champ_natures:
        info = nature_to_size(champ_natures[name])
        return info["size"] if info else None
    return None


def parse_champ_declarations(lines):
    """Parse toutes les declarations [CHAMP] et renvoie {nom: nature}.

    Supporte deux formats :
    - Format multiligne (reel ERP) :
        [CHAMP]
        Version=...
        Nom=FieldName,description,1
        Gel=3
        Nature=X
        Flags=...
    - Format inline (historique de ce script) :
        [CHAMP]
        Nom=FieldName,"Nature",Description

    Si les deux conventions coexistent dans un bloc, Nature= (multiligne) prime.
    """
    natures = {}
    i = 0
    while i < len(lines):
        if lines[i].strip() == "[CHAMP]":
            name = None
            nature = None
            j = i + 1
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith("["):
                    break
                if s.startswith("Nom="):
                    rest = s[4:]
                    parts = rest.split(",", 1)
                    name = parts[0]
                    if len(parts) > 1 and parts[1].startswith('"'):
                        try:
                            end_quote = parts[1].index('"', 1)
                            nature = parts[1][1:end_quote]
                        except ValueError:
                            pass
                elif s.startswith("Nature="):
                    nature = s[7:].strip()
                j += 1
            if name and nature is not None:
                natures[name] = nature
            i = j
        else:
            i += 1
    return natures


def find_table_range(lines, table_name):
    """Trouve la plage de lignes d'un bloc [TABLE] pour la table donnee.

    Returns:
        (table_start, champs_start, champs_end, table_end) ou None
        champs_start = ligne apres [CHAMPS], champs_end = ligne de [/CHAMPS]
    """
    i = 0
    while i < len(lines):
        if lines[i].strip() == "[TABLE]":
            table_start = i
            j = i + 1
            # Chercher Nom=
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith("Nom="):
                    parts = s[4:].split(",")
                    if parts[0] == table_name:
                        # Table trouvee, chercher [CHAMPS] et [/CHAMPS]
                        champs_start = None
                        champs_end = None
                        k = j + 1
                        while k < len(lines):
                            sk = lines[k].strip()
                            if sk == "[CHAMPS]":
                                champs_start = k + 1
                            elif sk == "[/CHAMPS]":
                                champs_end = k
                                return (table_start, champs_start, champs_end, k)
                            k += 1
                    break
                if s.startswith("[") and s != "[TABLE]":
                    break
                j += 1
            i = j
        else:
            i += 1
    return None


def parse_table_fields(lines, champs_start, champs_end):
    """Parse les lignes Nom= de [CHAMPS] et renvoie la liste de champs."""
    fields = []
    for i in range(champs_start, champs_end):
        s = lines[i].strip()
        if s.startswith("Nom="):
            parts = s[4:].split(",")
            if len(parts) >= 8:
                fields.append({
                    "name": parts[0],
                    "position": int(parts[1]),
                    "col2": parts[2],
                    "col3": parts[3],
                    "col4": parts[4],
                    "repetition": int(parts[5]),
                    "col6": parts[6],
                    "gel": int(parts[7]),
                    "line_index": i,
                })
    return fields


def get_taille(lines, table_start, champs_start):
    """Extrait la Taille de la table."""
    for i in range(table_start, champs_start):
        s = lines[i].strip()
        if s.startswith("Taille="):
            parts = s[7:].split(",")
            return int(parts[0]), i
    return None, None


def find_indexes_for_table(lines, table_name, champ_natures):
    """Trouve les blocs [INDEX] lies a la table et renvoie leurs infos.

    Returns:
        list of {name, start, champs_start, champs_end, fields: [{name, line_index}]}
    """
    indexes = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "[INDEX]":
            idx_start = i
            idx_name = None
            linked_table = None
            j = i + 1
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith("Nom="):
                    parts = s[4:].split(",")
                    idx_name = parts[0]
                elif s.startswith("Table="):
                    linked_table = s[6:].strip()
                elif s == "[CHAMPS]":
                    if linked_table == table_name:
                        champs_start = j + 1
                        champs_end = j
                        idx_fields = []
                        k = j + 1
                        while k < len(lines):
                            sk = lines[k].strip()
                            if sk == "[/CHAMPS]":
                                champs_end = k
                                break
                            if sk.startswith("Nom="):
                                pf = sk[4:].split(",")
                                idx_fields.append({
                                    "name": pf[0],
                                    "line_index": k,
                                })
                            k += 1
                        indexes.append({
                            "name": idx_name,
                            "start": idx_start,
                            "champs_start": champs_start,
                            "champs_end": champs_end,
                            "fields": idx_fields,
                        })
                    break
                elif s.startswith("[") and s not in ("[INDEX]", "[CHAMPS]"):
                    break
                j += 1
            i = j + 1
        else:
            i += 1
    return indexes


def recalc_positions(fields, champ_natures, table_name=None):
    """Recalcule les positions de tous les champs sequentiellement.

    Le U-field (s'il existe) a size=0 : il ne decale pas la position du champ
    suivant. En pratique c'est toujours le dernier champ, donc sans effet.
    Sa position sera egale a la somme des tailles des champs precedents + 1.
    Pour preserver la position d'origine du U-field, appeler recalc_filler.
    """
    pos = 1
    for f in fields:
        f["position"] = pos
        if f["name"] == "Filler":
            pos += f["repetition"]
        elif f["name"] in STANDARD_SIZES:
            pos += STANDARD_SIZES[f["name"]]
        elif is_u_field(f["name"], table_name):
            pass
        else:
            size = get_field_size(f["name"], champ_natures, table_name)
            if size is None:
                fail(f"Impossible de calculer la taille du champ '{f['name']}'")
            pos += size


def recalc_filler(fields, champ_natures, original_taille, table_name=None):
    """Recalcule le Filler pour preserver l'invariant de la table.

    - Si un U-field est present : le Filler est ajuste pour preserver la position
      d'origine du U-field (zone libre utilisateur). La Taille totale reste
      inchangee (l'espace absorbe/libere est pris sur le Filler).
    - Sinon : le Filler est ajuste pour preserver la Taille totale.

    Returns:
        (new_taille, filler_adjusted)
    """
    u_original_pos = None
    u_idx = None
    if table_name:
        for i, f in enumerate(fields):
            if is_u_field(f["name"], table_name):
                u_original_pos = f["position"]
                u_idx = i
                break

    # Si U-field present : choisir le DERNIER Filler avant lui (celui qui absorbe).
    # Sinon : choisir le premier Filler (comportement par defaut).
    filler_idx = None
    if u_idx is not None:
        for i in range(u_idx - 1, -1, -1):
            if fields[i]["name"] == "Filler":
                filler_idx = i
                break
    else:
        for i, f in enumerate(fields):
            if f["name"] == "Filler":
                filler_idx = i
                break

    # Calcule la taille effective d'un champ. Pour Filler : sa repetition.
    def _field_size(f):
        if f["name"] == "Filler":
            return f["repetition"]
        if f["name"] in STANDARD_SIZES:
            return STANDARD_SIZES[f["name"]]
        if is_u_field(f["name"], table_name):
            return 0
        size = get_field_size(f["name"], champ_natures, table_name)
        if size is None:
            fail(f"Impossible de calculer la taille du champ '{f['name']}'")
        return size

    total_without_filler = sum(
        _field_size(f) for f in fields if f["name"] != "Filler"
    )

    if u_original_pos is not None and filler_idx is not None:
        # Tailles avant Filler (pour deduire sa repetition requise)
        sum_before_filler = sum(_field_size(f) for f in fields[:filler_idx])
        needed_filler = u_original_pos - sum_before_filler - 1
        if needed_filler < 0:
            fail(
                f"Trop de champs : somme avant Filler = {sum_before_filler}, "
                f"position U-field = {u_original_pos}. Filler serait negatif."
            )
        fields[filler_idx]["repetition"] = needed_filler
        recalc_positions(fields, champ_natures, table_name)
        return original_taille, True

    if filler_idx is not None:
        needed_filler = original_taille - total_without_filler
        if needed_filler > 0:
            fields[filler_idx]["repetition"] = needed_filler
            recalc_positions(fields, champ_natures, table_name)
            return original_taille, True
        fields.pop(filler_idx)
        recalc_positions(fields, champ_natures, table_name)
        new_taille = sum(_field_size(f) for f in fields)
        return new_taille, True

    # Pas de Filler
    new_taille = total_without_filler
    return new_taille, False


def rebuild_champs_lines(fields):
    """Reconstruit les lignes Nom= a partir de la liste de champs."""
    result = []
    for f in fields:
        result.append(
            f"Nom={f['name']},{f['position']},{f['col2']},"
            f"{f['col3']},{f['col4']},{f['repetition']},{f['col6']},{f['gel']}"
        )
    return result


def update_taille_line(lines, taille_line_idx, new_taille):
    """Met a jour la ligne Taille= avec la nouvelle valeur."""
    old = lines[taille_line_idx].strip()
    parts = old[7:].split(",")
    parts[0] = str(new_taille)
    if len(parts) >= 2:
        parts[1] = str(new_taille)
    lines[taille_line_idx] = "Taille=" + ",".join(parts)


def recalc_index_positions(lines, index_info, champ_natures, table_name=None):
    """Recalcule les positions cumulees dans un bloc [INDEX]."""
    cum_pos = 1
    for f in index_info["fields"]:
        size = get_field_size(f["name"], champ_natures, table_name)
        if size is None:
            fail(f"Impossible de calculer la taille du champ index '{f['name']}'")
        old_line = lines[f["line_index"]].strip()
        parts = old_line[4:].split(",")
        parts[1] = str(cum_pos)
        lines[f["line_index"]] = "Nom=" + ",".join(parts)
        cum_pos += size


def validate_positions(fields, champ_natures, table_name=None):
    """Valide D01/D02 : positions contigues sans trou ni chevauchement.

    Le U-field est considere comme le dernier champ et occupe l'espace restant
    jusqu'a la Taille totale ; il ne doit pas casser la sequence des positions.
    """
    errors = []
    expected = 1
    for f in fields:
        if f["position"] != expected:
            errors.append(f"Position du champ '{f['name']}' = {f['position']}, attendu {expected}")
        if f["name"] == "Filler":
            expected = f["position"] + f["repetition"]
        elif f["name"] in STANDARD_SIZES:
            expected = f["position"] + STANDARD_SIZES[f["name"]]
        elif is_u_field(f["name"], table_name):
            pass
        else:
            size = get_field_size(f["name"], champ_natures, table_name)
            if size:
                expected = f["position"] + size
    return errors


def insert_champ_declaration(lines, field_name, nature_str, description=None):
    """Insere un bloc [CHAMP] alphabetiquement parmi les existants.

    Genere le format multiligne utilise par les .dhsd ERP reels :
        [CHAMP]
        Version=1,{date},{user},{date},{user}
        Nom={field_name},{description},1
        Gel=3
        Nature={nature_str}
        Flags=n,1,n,n,n,n,n,n,n

    Returns:
        L'index d'insertion utilise.
    """
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    user_padded = "CLAUDE".ljust(20)
    desc = description if description else field_name
    block = [
        "[CHAMP]",
        f"Version=1,{now},{user_padded},{now},{user_padded}",
        f"Nom={field_name},{desc},1",
        "Gel=3",
        f"Nature={nature_str}",
        "Flags=n,1,n,n,n,n,n,n,n",
    ]

    # Scanner tous les blocs [CHAMP] : pour chaque bloc, capturer
    # (name, start_line, end_line_exclusive). end_line_exclusive pointe sur
    # la ligne du bloc suivant (premier [...] rencontre apres [CHAMP]).
    champ_blocks = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].strip() == "[CHAMP]":
            start = i
            name = None
            j = i + 1
            while j < n:
                s = lines[j].strip()
                if s.startswith("["):
                    break
                if name is None and s.startswith("Nom="):
                    rest = s[4:]
                    name = rest.split(",", 1)[0]
                j += 1
            if name:
                champ_blocks.append((name, start, j))
            i = j
        else:
            i += 1

    if not champ_blocks:
        for idx, l in enumerate(block):
            lines.insert(idx, l)
        return 0

    # Recherche de la position d'insertion alphabetique (case-insensitive)
    insert_at = None
    for name, start, _end in champ_blocks:
        if name.lower() > field_name.lower():
            insert_at = start
            break

    if insert_at is None:
        # Inserer apres la fin du dernier bloc
        insert_at = champ_blocks[-1][2]

    for idx, l in enumerate(block):
        lines.insert(insert_at + idx, l)
    return insert_at


# -- Actions ----------------------------------------------------------------

def action_list_fields(args):
    lines = read_dhsd(args.dhsd)
    champ_natures = parse_champ_declarations(lines)
    rng = find_table_range(lines, args.table)
    if rng is None:
        fail(f"Table '{args.table}' non trouvee dans {args.dhsd}", code=2)
    table_start, champs_start, champs_end, table_end = rng
    fields = parse_table_fields(lines, champs_start, champs_end)
    taille, _ = get_taille(lines, table_start, champs_start)
    indexes = find_indexes_for_table(lines, args.table, champ_natures)

    result_fields = []
    for f in fields:
        name = f["name"]
        entry = {"name": name, "position": f["position"]}
        if name == "Filler":
            entry["size"] = f["repetition"]
            entry["nature"] = None
            entry["is_filler"] = True
        elif name in STANDARD_SIZES:
            entry["size"] = STANDARD_SIZES[name]
            entry["nature"] = str(STANDARD_SIZES[name])
            entry["is_standard"] = True
        elif is_u_field(name, args.table):
            # Taille implicite = Taille totale - position + 1
            implicit_size = (taille - f["position"] + 1) if taille else None
            entry["size"] = implicit_size
            entry["nature"] = champ_natures.get(name)
            entry["is_u_field"] = True
        else:
            nature = champ_natures.get(name)
            size = get_field_size(name, champ_natures, args.table)
            entry["size"] = size
            entry["nature"] = nature
            entry["is_standard"] = False
        result_fields.append(entry)

    result_indexes = []
    for idx in indexes:
        result_indexes.append({
            "name": idx["name"],
            "fields": [f["name"] for f in idx["fields"]],
        })

    output = {
        "success": True,
        "table": args.table,
        "taille": taille,
        "fields": result_fields,
        "indexes": result_indexes,
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    print()


def action_add_field(args):
    lines = read_dhsd(args.dhsd)
    champ_natures = parse_champ_declarations(lines)
    rng = find_table_range(lines, args.table)
    if rng is None:
        fail(f"Table '{args.table}' non trouvee dans {args.dhsd}", code=2)
    table_start, champs_start, champs_end, table_end = rng
    fields = parse_table_fields(lines, champs_start, champs_end)
    taille_before, taille_line_idx = get_taille(lines, table_start, champs_start)

    # Validation : champ pas deja present
    existing_names = [f["name"] for f in fields]
    if args.name in existing_names:
        fail(f"Le champ '{args.name}' existe deja dans la table '{args.table}'")

    # Resoudre nature -> taille
    info = nature_to_size(args.nature)
    if info is None:
        fail(f"Nature invalide : '{args.nature}'")
    new_size = info["size"]

    # Point d'insertion
    u_field_name = f"U{args.table}"
    if args.after:
        after_idx = None
        for i, f in enumerate(fields):
            if f["name"] == args.after:
                after_idx = i
                break
        if after_idx is None:
            fail(f"Champ --after '{args.after}' non trouve dans la table")
        if fields[after_idx]["name"] == u_field_name:
            fail(f"Impossible d'inserer apres le U-field '{u_field_name}'")
        insert_idx = after_idx + 1
    else:
        # Avant UserCr par defaut
        insert_idx = None
        for i, f in enumerate(fields):
            if f["name"] == "UserCr":
                insert_idx = i
                break
        if insert_idx is None:
            # Avant Filler si pas de UserCr
            for i, f in enumerate(fields):
                if f["name"] == "Filler":
                    insert_idx = i
                    break
        if insert_idx is None:
            # Avant U-field
            for i, f in enumerate(fields):
                if f["name"] == u_field_name:
                    insert_idx = i
                    break
        if insert_idx is None:
            insert_idx = len(fields)

    # Creer l'entree du nouveau champ
    new_field = {
        "name": args.name,
        "position": 0,
        "col2": "2",
        "col3": "N",
        "col4": "0",
        "repetition": 0,
        "col6": "N",
        "gel": 3,
    }
    fields.insert(insert_idx, new_field)

    # Mettre a jour les natures connues
    champ_natures[args.name] = args.nature

    # Recalculer positions et Filler (U-field ancre si present)
    recalc_positions(fields, champ_natures, args.table)
    new_taille, filler_adjusted = recalc_filler(fields, champ_natures, taille_before, args.table)
    recalc_positions(fields, champ_natures, args.table)

    # Verifier [CHAMP]
    champ_created = False
    if args.name not in STANDARD_FIELDS and not is_u_field(args.name, args.table):
        existing_natures = parse_champ_declarations(lines)
        if args.name not in existing_natures:
            insert_champ_declaration(lines, args.name, args.nature)
            champ_created = True
            # Re-parser car les indices ont change
            rng = find_table_range(lines, args.table)
            table_start, champs_start, champs_end, table_end = rng
            taille_before_val, taille_line_idx = get_taille(lines, table_start, champs_start)

    # Reconstruire les lignes [CHAMPS]
    new_champs_lines = rebuild_champs_lines(fields)
    lines[champs_start:champs_end] = new_champs_lines
    champs_end = champs_start + len(new_champs_lines)

    # Mettre a jour Taille
    if taille_line_idx is not None:
        update_taille_line(lines, taille_line_idx, new_taille)

    # Validation D01/D02
    errs = validate_positions(fields, champ_natures, args.table)
    if errs:
        fail("Erreur de validation post-modification :\n" + "\n".join(errs))

    # Calculer champs decales
    fields_shifted = sum(1 for f in fields if f["position"] > fields[insert_idx]["position"])

    if not args.dry_run:
        write_dhsd(args.dhsd, lines, backup=args.backup)

    output = {
        "success": True,
        "action": "add-field",
        "field": args.name,
        "nature": args.nature,
        "size": new_size,
        "position": fields[insert_idx]["position"],
        "taille_before": taille_before,
        "taille_after": new_taille,
        "filler_adjusted": filler_adjusted,
        "champ_created": champ_created,
        "fields_shifted": fields_shifted,
        "dry_run": args.dry_run,
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    print()


def action_modify_field(args):
    lines = read_dhsd(args.dhsd)
    champ_natures = parse_champ_declarations(lines)
    rng = find_table_range(lines, args.table)
    if rng is None:
        fail(f"Table '{args.table}' non trouvee dans {args.dhsd}", code=2)
    table_start, champs_start, champs_end, table_end = rng
    fields = parse_table_fields(lines, champs_start, champs_end)
    taille_before, taille_line_idx = get_taille(lines, table_start, champs_start)

    # Trouver le champ
    target_idx = None
    for i, f in enumerate(fields):
        if f["name"] == args.name:
            target_idx = i
            break
    if target_idx is None:
        fail(f"Champ '{args.name}' non trouve dans la table '{args.table}'", code=2)

    # Validation : pas standard, pas Filler, pas U-field
    if args.name in STANDARD_FIELDS:
        fail(f"Le champ standard '{args.name}' ne peut pas etre modifie")
    if args.name == "Filler":
        fail("Le champ Filler ne peut pas etre modifie directement")
    if is_u_field(args.name, args.table):
        fail(f"Le U-field '{args.name}' ne peut pas etre modifie")

    # Resoudre ancienne et nouvelle nature
    old_nature = champ_natures.get(args.name)
    info_new = nature_to_size(args.new_nature)
    if info_new is None:
        fail(f"Nature invalide : '{args.new_nature}'")
    new_size = info_new["size"]

    # Mettre a jour la declaration [CHAMP] (format multiligne ERP ou inline)
    i = 0
    champ_updated = False
    n = len(lines)
    while i < n:
        if lines[i].strip() == "[CHAMP]":
            j = i + 1
            block_name = None
            nom_line_idx = None
            nature_line_idx = None
            while j < n:
                s = lines[j].strip()
                if s.startswith("["):
                    break
                if s.startswith("Nom=") and nom_line_idx is None:
                    nom_line_idx = j
                    block_name = s[4:].split(",", 1)[0]
                elif s.startswith("Nature="):
                    nature_line_idx = j
                j += 1
            if block_name == args.name:
                if nature_line_idx is not None:
                    lines[nature_line_idx] = f"Nature={args.new_nature}"
                    champ_updated = True
                elif nom_line_idx is not None:
                    line = lines[nom_line_idx]
                    rest = line[4:]
                    parts = rest.split(",", 1)
                    if len(parts) > 1 and parts[1].startswith('"'):
                        try:
                            end_quote = parts[1].index('"', 1)
                            new_remainder = f'"{args.new_nature}"' + parts[1][end_quote + 1:]
                            lines[nom_line_idx] = f"Nom={parts[0]},{new_remainder}"
                            champ_updated = True
                        except ValueError:
                            pass
                break
            i = j
        else:
            i += 1

    if not champ_updated:
        fail(f"Declaration [CHAMP] pour '{args.name}' non trouvee", code=2)

    # Mettre a jour les natures
    champ_natures[args.name] = args.new_nature

    # Re-parser (les indices n'ont pas change pour [TABLE])
    rng = find_table_range(lines, args.table)
    table_start, champs_start, champs_end, table_end = rng
    fields = parse_table_fields(lines, champs_start, champs_end)
    taille_before, taille_line_idx = get_taille(lines, table_start, champs_start)

    # Recalculer (U-field ancre si present)
    recalc_positions(fields, champ_natures, args.table)
    new_taille, filler_adjusted = recalc_filler(fields, champ_natures, taille_before, args.table)
    recalc_positions(fields, champ_natures, args.table)

    # Reconstruire [CHAMPS]
    new_champs_lines = rebuild_champs_lines(fields)
    lines[champs_start:champs_end] = new_champs_lines

    # Mettre a jour Taille
    if taille_line_idx is not None:
        update_taille_line(lines, taille_line_idx, new_taille)

    # Recalculer les index concernes
    indexes = find_indexes_for_table(lines, args.table, champ_natures)
    indexes_updated = []
    for idx in indexes:
        if any(f["name"] == args.name for f in idx["fields"]):
            recalc_index_positions(lines, idx, champ_natures, args.table)
            indexes_updated.append(idx["name"])

    # Validation
    errs = validate_positions(fields, champ_natures, args.table)
    if errs:
        fail("Erreur de validation post-modification :\n" + "\n".join(errs))

    if not args.dry_run:
        write_dhsd(args.dhsd, lines, backup=args.backup)

    output = {
        "success": True,
        "action": "modify-field",
        "field": args.name,
        "old_nature": old_nature,
        "new_nature": args.new_nature,
        "old_size": get_field_size(args.name, {args.name: old_nature}, args.table) if old_nature else None,
        "new_size": new_size,
        "taille_before": taille_before,
        "taille_after": new_taille,
        "filler_adjusted": filler_adjusted,
        "indexes_updated": indexes_updated,
        "dry_run": args.dry_run,
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    print()


def action_remove_field(args):
    lines = read_dhsd(args.dhsd)
    champ_natures = parse_champ_declarations(lines)
    rng = find_table_range(lines, args.table)
    if rng is None:
        fail(f"Table '{args.table}' non trouvee dans {args.dhsd}", code=2)
    table_start, champs_start, champs_end, table_end = rng
    fields = parse_table_fields(lines, champs_start, champs_end)
    taille_before, taille_line_idx = get_taille(lines, table_start, champs_start)

    # Trouver le champ
    target_idx = None
    for i, f in enumerate(fields):
        if f["name"] == args.name:
            target_idx = i
            break
    if target_idx is None:
        fail(f"Champ '{args.name}' non trouve dans la table '{args.table}'", code=2)

    # Validation : pas standard, pas U-field, pas Filler
    if args.name in STANDARD_FIELDS:
        fail(f"Le champ standard '{args.name}' ne peut pas etre supprime")
    if is_u_field(args.name, args.table):
        fail(f"Le U-field '{args.name}' ne peut pas etre supprime")
    if args.name == "Filler":
        fail("Le champ Filler ne peut pas etre supprime directement")

    # Supprimer le champ
    removed = fields.pop(target_idx)

    # Recalculer (U-field ancre si present)
    recalc_positions(fields, champ_natures, args.table)
    new_taille, filler_adjusted = recalc_filler(fields, champ_natures, taille_before, args.table)
    recalc_positions(fields, champ_natures, args.table)

    # Reconstruire [CHAMPS]
    new_champs_lines = rebuild_champs_lines(fields)
    lines[champs_start:champs_end] = new_champs_lines

    # Mettre a jour Taille
    if taille_line_idx is not None:
        update_taille_line(lines, taille_line_idx, new_taille)

    # Traiter les index : retirer le champ et recalculer
    indexes = find_indexes_for_table(lines, args.table, champ_natures)
    indexes_updated = []
    for idx in indexes:
        removed_from_idx = False
        new_idx_fields = []
        for f in idx["fields"]:
            if f["name"] == args.name:
                lines[f["line_index"]] = ""
                removed_from_idx = True
            else:
                new_idx_fields.append(f)
        if removed_from_idx:
            idx["fields"] = new_idx_fields
            lines = [l for l in lines if l != "" or l.strip() != ""]
            indexes = find_indexes_for_table(lines, args.table, champ_natures)
            for idx2 in indexes:
                recalc_index_positions(lines, idx2, champ_natures, args.table)
                indexes_updated.append(idx2["name"])
            break

    # Validation
    errs = validate_positions(fields, champ_natures, args.table)
    if errs:
        fail("Erreur de validation post-modification :\n" + "\n".join(errs))

    if not args.dry_run:
        write_dhsd(args.dhsd, lines, backup=args.backup)

    output = {
        "success": True,
        "action": "remove-field",
        "field": args.name,
        "taille_before": taille_before,
        "taille_after": new_taille,
        "filler_adjusted": filler_adjusted,
        "indexes_updated": indexes_updated,
        "dry_run": args.dry_run,
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    print()


# -- Main -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Modifie les tables d'un dictionnaire DIVA (.dhsd)"
    )
    parser.add_argument("--action", required=True,
                        choices=["list-fields", "add-field", "modify-field", "remove-field"],
                        help="Action a effectuer")
    parser.add_argument("--dhsd", required=True,
                        help="Chemin vers le fichier .dhsd")
    parser.add_argument("--table", required=True,
                        help="Nom de la table cible")
    parser.add_argument("--name", default=None,
                        help="Nom du champ (requis pour add/modify/remove)")
    parser.add_argument("--nature", default=None,
                        help="Nature du champ (requis pour add-field)")
    parser.add_argument("--new-nature", default=None,
                        help="Nouvelle nature (requis pour modify-field)")
    parser.add_argument("--after", default=None,
                        help="Inserer apres ce champ (add-field)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simuler sans ecrire")
    parser.add_argument("--backup", action="store_true",
                        help="Creer une copie .bak avant modification")

    args = parser.parse_args()

    if not os.path.exists(args.dhsd):
        fail(f"Fichier non trouve : {args.dhsd}", code=2)

    try:
        if args.action == "list-fields":
            action_list_fields(args)
        elif args.action == "add-field":
            if not args.name or not args.nature:
                fail("--name et --nature sont requis pour add-field")
            action_add_field(args)
        elif args.action == "modify-field":
            if not args.name or not args.new_nature:
                fail("--name et --new-nature sont requis pour modify-field")
            action_modify_field(args)
        elif args.action == "remove-field":
            if not args.name:
                fail("--name est requis pour remove-field")
            action_remove_field(args)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Erreur interne : {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
