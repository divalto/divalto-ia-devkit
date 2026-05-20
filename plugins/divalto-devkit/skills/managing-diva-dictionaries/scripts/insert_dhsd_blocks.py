#!/usr/bin/env python3
"""Insere les blocs generes par generate_dhsd_block.py dans un dictionnaire .dhsd.

Respecte la structure du fichier :
  [CHAMP] (tries alpha) → [CHAMPR]/[CHAMPL] → [TABLE] (tries alpha)
  → [BASE] (tries alpha) → [INDEX] (groupes par base) → [INDEXL]

Usage :
    py insert_dhsd_blocks.py --dhsd "chemin/gtfdd.dhsd" --blocks "blocs.json"
    py insert_dhsd_blocks.py --dhsd "chemin/gtfdd.dhsd" --blocks "blocs.json" --dry-run

Sortie JSON :
    {
        "success": true,
        "file": "chemin/gtfdd.dhsd",
        "backup": "chemin/gtfdd.dhsd.bak",
        "insertions": { ... },
        "validation": { ... }
    }

Exit codes : 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

ENCODING = "iso-8859-1"


# ---------------------------------------------------------------------------
# Detection des zones
# ---------------------------------------------------------------------------

def detect_zones(lines):
    """Detecte les bornes des 6 zones dans le fichier .dhsd.

    Returns:
        dict: {zone_name: {"start": int, "end": int}} (indices 0-based)
    """
    zones = {
        "champ": {"start": None, "end": None},
        "champr": {"start": None, "end": None},
        "table": {"start": None, "end": None},
        "base": {"start": None, "end": None},
        "index": {"start": None, "end": None},
        "indexl": {"start": None, "end": None},
    }

    first_champ = None
    last_champ_before_champr = None
    first_champr = None
    last_champr = None
    first_table = None
    last_table_end = None
    first_base = None
    last_base_end = None
    first_index = None
    last_index_end = None
    indexl_start = None
    indexl_end = None

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped == "[CHAMP]":
            if first_champ is None:
                first_champ = i
            # Chercher la fin de ce bloc CHAMP (prochaine ligne [CHAMP], [CHAMPR], [TABLE], [BASE], [INDEX])
            last_champ_before_champr = i

        elif stripped == "[CHAMPR]":
            if first_champr is None:
                first_champr = i
            last_champr = i

        elif stripped == "[/CHAMPR]":
            last_champr = i

        elif stripped == "[TABLE]":
            if first_table is None:
                first_table = i

        elif stripped == "[/CHAMPS]":
            # Peut etre dans TABLE ou INDEX -- on prend le contexte
            pass

        elif stripped == "[BASE]":
            if first_base is None:
                first_base = i

        elif stripped == "[/TABLES]":
            last_base_end = i

        elif stripped == "[INDEX]":
            if first_index is None:
                first_index = i

        elif stripped == "[/INDEX]":
            last_index_end = i

        elif stripped == "[INDEXL]":
            indexl_start = i

        elif stripped == "[/INDEXL]":
            indexl_end = i

        i += 1

    # Calculer les bornes
    if first_champ is not None:
        zones["champ"]["start"] = first_champ
        # La zone CHAMP s'arrete juste avant [CHAMPR] ou [TABLE]
        if first_champr is not None:
            zones["champ"]["end"] = first_champr - 1
        elif first_table is not None:
            zones["champ"]["end"] = first_table - 1

    if first_champr is not None:
        zones["champr"]["start"] = first_champr
        zones["champr"]["end"] = last_champr

    if first_table is not None:
        zones["table"]["start"] = first_table
        # La zone TABLE s'arrete juste avant [BASE]
        if first_base is not None:
            zones["table"]["end"] = first_base - 1

    if first_base is not None:
        zones["base"]["start"] = first_base
        zones["base"]["end"] = last_base_end

    if first_index is not None:
        zones["index"]["start"] = first_index
        zones["index"]["end"] = last_index_end

    if indexl_start is not None:
        zones["indexl"]["start"] = indexl_start
        zones["indexl"]["end"] = indexl_end

    return zones


# ---------------------------------------------------------------------------
# Recherche de position d'insertion alphabetique
# ---------------------------------------------------------------------------

def find_champ_insert_pos(lines, zone, champ_name):
    """Trouve la position d'insertion pour un [CHAMP] dans la zone CHAMP (tri alpha).

    Returns:
        (int, bool, str|None): (ligne d'insertion, doublon_detecte, nature_existante)
        nature_existante est renseigne uniquement si doublon_detecte=True.
    """
    champ_lower = champ_name.lower()
    last_champ_start = None
    last_champ_end = zone["end"]

    i = zone["start"]
    while i <= zone["end"]:
        stripped = lines[i].strip()
        if stripped == "[CHAMP]":
            # Chercher le Nom= dans les 10 lignes suivantes
            for j in range(i + 1, min(i + 10, zone["end"] + 1)):
                nom_line = lines[j].strip()
                nom_match = re.match(r"Nom=([^,]+),", nom_line)
                if nom_match:
                    existing_name = nom_match.group(1)
                    if existing_name.lower() == champ_lower:
                        # Extraire la Nature existante (2e champ apres Nom=)
                        parts = nom_line.split(",")
                        existing_nature = parts[1].strip('"') if len(parts) > 1 else None
                        return (i, True, existing_nature)  # Doublon
                    if existing_name.lower() > champ_lower:
                        return (i, False, None)  # Inserer avant ce [CHAMP]
                    last_champ_start = i
                    break
        i += 1

    # Si on n'a pas trouve de position, inserer apres le dernier CHAMP
    # Trouver la fin du dernier bloc CHAMP (chercher le Flags= ou la prochaine section)
    if last_champ_start is not None:
        for j in range(last_champ_start + 1, zone["end"] + 2):
            if j > zone["end"] or lines[j].strip().startswith("["):
                return (j, False, None)
    return (zone["end"] + 1, False, None)


def find_table_insert_pos(lines, zone, table_name):
    """Trouve la position d'insertion pour un [TABLE] dans la zone TABLE (tri alpha).

    Returns:
        (int, bool): (ligne d'insertion, doublon_detecte)
    """
    table_lower = table_name.lower()

    i = zone["start"]
    while i <= zone["end"]:
        stripped = lines[i].strip()
        if stripped == "[TABLE]":
            for j in range(i + 1, min(i + 10, zone["end"] + 1)):
                nom_match = re.match(r"Nom=([^,]+),", lines[j].strip())
                if nom_match:
                    existing_name = nom_match.group(1)
                    if existing_name.lower() == table_lower:
                        return (i, True)
                    if existing_name.lower() > table_lower:
                        return (i, False)
                    break
        i += 1

    return (zone["end"] + 1, False)


def find_base_insert_pos(lines, zone, base_name):
    """Trouve la position d'insertion pour un [BASE] dans la zone BASE (tri alpha).

    Returns:
        (int, bool): (ligne d'insertion, doublon_detecte)
    """
    base_lower = base_name.lower()

    i = zone["start"]
    while i <= zone["end"]:
        stripped = lines[i].strip()
        if stripped == "[BASE]":
            for j in range(i + 1, min(i + 10, zone["end"] + 1)):
                nom_match = re.match(r"Nom=([^,]+),", lines[j].strip())
                if nom_match:
                    existing_name = nom_match.group(1)
                    if existing_name.lower() == base_lower:
                        return (i, True)
                    if existing_name.lower() > base_lower:
                        return (i, False)
                    break
        i += 1

    return (zone["end"] + 1, False)


def find_index_insert_pos(lines, zone, base_name):
    """Trouve la position d'insertion pour les [INDEX] d'une nouvelle base.

    Insere apres le dernier index de la base precedente alphabetiquement.

    Returns:
        int: ligne d'insertion
    """
    base_lower = base_name.lower()
    last_index_end_before = zone["start"]

    i = zone["start"]
    while i <= zone["end"]:
        stripped = lines[i].strip()
        cle_match = re.match(r"CLE=([^,]+),", stripped)
        if cle_match:
            idx_base = cle_match.group(1)
            if idx_base.lower() >= base_lower:
                return last_index_end_before
        if stripped == "[/INDEX]":
            last_index_end_before = i + 1
        i += 1

    return last_index_end_before


# ---------------------------------------------------------------------------
# Insertion
# ---------------------------------------------------------------------------

def insert_blocks(lines, zones, blocks):
    """Insere les blocs dans les lignes.

    Args:
        lines: liste de lignes du .dhsd
        zones: dict des zones detectees
        blocks: dict des blocs (depuis le JSON genere)

    Returns:
        (lines_modified, insertions_report, errors)
    """
    insertions = {"champs": [], "table": None, "base": None, "indexes": [], "indexl": []}
    errors = []
    pending = []  # (position, block_lines, info_dict)

    # 1. INDEXL -- inserer avant [/INDEXL]
    if zones["indexl"]["end"] is not None:
        for il_line in blocks.get("indexl", []):
            pending.append((zones["indexl"]["end"], [il_line], {"type": "indexl"}))

    # 2. INDEX
    if zones["index"]["start"] is not None and "indexes" in blocks:
        # Extraire le nom de base depuis le CLE du premier index
        if blocks["indexes"]:
            first_idx = blocks["indexes"][0]["block"]
            cle_match = re.search(r"CLE=([^,]+),", first_idx)
            if cle_match:
                idx_base = cle_match.group(1)
                pos = find_index_insert_pos(lines, zones["index"], idx_base)
                for idx_block in blocks["indexes"]:
                    idx_lines = idx_block["block"].split("\n")
                    pending.append((pos, idx_lines, {"type": "index", "name": idx_block["name"]}))

    # 3. BASE
    if zones["base"]["start"] is not None and "base" in blocks:
        base_text = blocks["base"]
        base_name_match = re.search(r"Nom=([^,]+),", base_text)
        if base_name_match:
            base_name = base_name_match.group(1)
            pos, is_dup = find_base_insert_pos(lines, zones["base"], base_name)
            if is_dup:
                errors.append(f"Base '{base_name}' existe deja dans le dictionnaire")
            else:
                base_lines = base_text.split("\n")
                pending.append((pos, base_lines, {"type": "base", "name": base_name}))

    # 4. TABLE
    if zones["table"]["start"] is not None and "table" in blocks:
        table_text = blocks["table"]
        table_name_match = re.search(r"Nom=([^,]+),", table_text)
        if table_name_match:
            table_name = table_name_match.group(1)
            pos, is_dup = find_table_insert_pos(lines, zones["table"], table_name)
            if is_dup:
                errors.append(f"Table '{table_name}' existe deja dans le dictionnaire")
            else:
                table_lines = table_text.split("\n")
                pending.append((pos, table_lines, {"type": "table", "name": table_name}))

    # 5. CHAMPS (les champs sont globaux : skip si deja present, pas d'erreur)
    skipped_champs = []
    nature_warnings = []
    if zones["champ"]["start"] is not None and "champs" in blocks:
        for champ in blocks["champs"]:
            champ_text = champ["block"]
            champ_name = champ["name"]
            pos, is_dup, existing_nature = find_champ_insert_pos(lines, zones["champ"], champ_name)
            if is_dup:
                skipped_champs.append(champ_name)
                # Comparer la Nature existante avec celle demandee
                if existing_nature is not None:
                    nom_match = re.search(r"Nom=[^,]+,([^,]+)", champ_text)
                    if nom_match:
                        requested_nature = nom_match.group(1).strip('"')
                        if requested_nature != existing_nature:
                            nature_warnings.append(
                                f"Champ '{champ_name}' : Nature existante '{existing_nature}' "
                                f"!= Nature demandee '{requested_nature}' -- le champ global sera utilise tel quel"
                            )
            else:
                champ_lines = champ_text.split("\n")
                pending.append((pos, champ_lines, {"type": "champ", "name": champ_name}))
    insertions["skipped_champs"] = skipped_champs
    insertions["nature_warnings"] = nature_warnings

    if errors:
        return lines, insertions, errors

    # Trier par position decroissante pour inserer de bas en haut
    pending.sort(key=lambda x: -x[0])

    for pos, block_lines, info in pending:
        for j, bl in enumerate(block_lines):
            lines.insert(pos + j, bl)

        actual_line = pos + 1  # 1-indexed pour le rapport
        if info["type"] == "champ":
            insertions["champs"].append({"name": info["name"], "line": actual_line})
        elif info["type"] == "table":
            insertions["table"] = {"name": info["name"], "line": actual_line}
        elif info["type"] == "base":
            insertions["base"] = {"name": info["name"], "line": actual_line}
        elif info["type"] == "index":
            insertions["indexes"].append({"name": info["name"], "line": actual_line})
        elif info["type"] == "indexl":
            insertions["indexl"].append({"line": actual_line})

    return lines, insertions, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Insere des blocs dans un dictionnaire .dhsd"
    )
    parser.add_argument("--dhsd", required=True, help="Chemin du dictionnaire .dhsd")
    parser.add_argument("--blocks", required=True, help="Chemin du JSON de blocs (generate_dhsd_block.py)")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les positions sans modifier")
    parser.add_argument("--no-backup", action="store_true", help="Ne pas creer de backup .bak")
    args = parser.parse_args()

    result = {
        "success": False,
        "file": args.dhsd,
        "backup": None,
        "insertions": None,
        "validation": None,
        "errors": [],
    }

    # Charger le fichier .dhsd
    if not os.path.isfile(args.dhsd):
        result["errors"].append(f"Fichier introuvable: {args.dhsd}")
        print(f"Erreur : fichier .dhsd introuvable : {args.dhsd}", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        with open(args.dhsd, "r", encoding=ENCODING) as f:
            content = f.read()
    except Exception as e:
        result["errors"].append(f"Erreur lecture: {e}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    lines = content.split("\n")
    lines = [line.rstrip("\r") for line in lines]

    # Charger les blocs
    try:
        with open(args.blocks, "r", encoding="utf-8") as f:
            blocks_data = json.load(f)
    except Exception as e:
        result["errors"].append(f"Erreur lecture blocs: {e}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    blocks = blocks_data.get("blocks", {})
    table_name = blocks_data.get("table", "")

    # Detecter les zones
    zones = detect_zones(lines)

    # Verifier que les zones sont detectees
    missing = [z for z, v in zones.items() if v["start"] is None and z != "champr"]
    if missing:
        result["errors"].append(f"Zones non detectees dans le dictionnaire: {missing}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Inserer les blocs
    lines, insertions, errors = insert_blocks(lines, zones, blocks)

    if errors:
        result["errors"] = errors
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    result["insertions"] = insertions

    if args.dry_run:
        result["success"] = True
        result["errors"].append("dry-run: fichier non modifie")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    # Backup
    if not args.no_backup:
        backup_path = args.dhsd + ".bak"
        shutil.copy2(args.dhsd, backup_path)
        result["backup"] = backup_path

    # Ecrire le fichier
    try:
        output = "\r\n".join(lines)
        with open(args.dhsd, "w", encoding=ENCODING, newline="") as f:
            f.write(output)
    except Exception as e:
        result["errors"].append(f"Erreur ecriture: {e}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    # Validation post-insertion
    validate_script = os.path.join(os.path.dirname(__file__), "validate_dhsd.py")
    if os.path.isfile(validate_script):
        try:
            proc = subprocess.run(
                [sys.executable, validate_script, "--path", args.dhsd, "--table", table_name],
                capture_output=True, text=True, timeout=30
            )
            result["validation"] = json.loads(proc.stdout) if proc.stdout.strip() else None
        except Exception:
            result["validation"] = None

    result["success"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
