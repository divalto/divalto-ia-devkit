#!/usr/bin/env python3
"""Genere les 5 blocs INI a inserer dans un dictionnaire .dhsd pour ajouter une table.

Usage:
    py .claude/skills/managing-diva-dictionaries/scripts/generate_dhsd_block.py \
        --table MonEntite \
        --description "Description de la table" \
        --ce-value A \
        --base GtfMonEntite \
        --base-prefix Gtf \
        --dict-name gtfdd \
        --fields fields.json \
        --output output_blocks.json

    Ou avec --stdin pour lire les parametres JSON depuis stdin :
    echo '{ ... }' | py .../generate_dhsd_block.py --stdin --output output.json

Format JSON d'entree (fields.json ou stdin) :
{
    "table": "MonEntite",
    "description": "Description de la table",
    "ce_value": "A",
    "base": "GtfMonEntite",
    "base_prefix": "Gtf",
    "dict_name": "gtfdd",
    "u_field_size": 500,
    "filler_size": 0,
    "fields": [
        {"name": "ChampMetier1", "nature": "20", "description": "Description champ 1"},
        {"name": "ChampMetier2", "nature": "8", "description": "Description champ 2"},
        {"name": "Prix", "nature": "10,2", "description": "Prix unitaire"}
    ],
    "indexes": [
        {"name": "Index_A", "description": "Index primaire", "unique": false,
         "fields": ["Dos", "ChampMetier1"]}
    ]
}

Sortie JSON: {table, blocks: {champs[], table_block, base_block, indexes[], indexl_lines[]},
              positions: {field: {position, size}}, taille, summary}
Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time

# Ajouter le repertoire parent pour importer nature_to_size
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nature_to_size import nature_to_size


# Champs standard toujours presents (dans l'ordre)
STANDARD_FIELDS_BEFORE = [
    {"name": "Ce1", "nature": "1", "description": "Code enregistrement", "standard": True},
    {"name": "Dos", "nature": "8", "description": "Dossier", "standard": True},
]

STANDARD_FIELDS_AFTER = [
    {"name": "UserCr", "nature": "20", "description": "Utilisateur createur", "standard": True},
    {"name": "UserMo", "nature": "20", "description": "Utilisateur modificateur", "standard": True},
    {"name": "UserCrDh", "nature": "DH", "description": "Timestamp creation", "standard": True},
    {"name": "UserMoDh", "nature": "DH", "description": "Timestamp modification", "standard": True},
]


def generate_timestamp():
    """Genere un timestamp au format DIVA (AAAAMMJJHHMMSS)."""
    return time.strftime("%Y%m%d%H%M%S")


def generate_hash():
    """Genere un hash hexadecimal aleatoire pour DateM."""
    return hashlib.md5(os.urandom(16)).hexdigest()[:16]


def pad_name(name, width=20):
    """Padde un nom a la largeur donnee (convention Version= dans .dhsd)."""
    return name.ljust(width)[:width]


def generate_version_line(creator="Claude"):
    """Genere une ligne Version= standard."""
    ts = generate_timestamp()
    padded = pad_name(creator)
    return f"Version=1,{ts},{padded},{ts},{padded}"


def compute_positions(all_fields):
    """Calcule les positions de tous les champs (regle : pas de trou).

    Args:
        all_fields: liste de dicts avec 'name' et 'nature'

    Returns:
        list de dicts avec 'name', 'nature', 'position', 'size' ajoutes
    """
    position = 1
    result = []
    for field in all_fields:
        info = nature_to_size(str(field["nature"]))
        if info is None:
            raise ValueError(f"Nature invalide pour le champ '{field['name']}': {field['nature']}")
        size = info["size"]
        result.append({
            **field,
            "position": position,
            "size": size,
        })
        position += size
    return result


def generate_champ_blocks(fields, table_name, u_field_size):
    """Genere les blocs [CHAMP] pour les champs metier + U-field.

    Ne genere PAS de [CHAMP] pour les champs standard (Ce1, Dos, UserCr, etc.)
    ni pour Filler (mot-cle special).
    """
    blocks = []
    version = generate_version_line()

    # Champs metier
    for field in fields:
        block = (
            f"[CHAMP]\n"
            f"{version}\n"
            f"Nom={field['name']},{field.get('description', field['name'])},1\n"
            f"Gel=3\n"
            f"Nature={field['nature']}\n"
            f"NomOdbc={field['name']}\n"
            f"Flags=o,1,n,n,n,n,n,n,n"
        )
        blocks.append({"name": field["name"], "block": block})

    # U-field
    u_name = f"U{table_name}"
    block = (
        f"[CHAMP]\n"
        f"{version}\n"
        f"Nom={u_name},Reserve distributeur {table_name},1\n"
        f"Gel=3\n"
        f"Nature={u_field_size}\n"
        f"NomOdbc={u_name}\n"
        f"Flags=n,1,o,o,n,n,n,n,o"
    )
    blocks.append({"name": u_name, "block": block})

    return blocks


def generate_table_block(table_name, description, ce_value, positioned_fields, taille):
    """Genere le bloc [TABLE] complet."""
    version = generate_version_line()
    date_m = generate_hash()
    date_m2 = generate_hash()

    lines = [
        "[TABLE]",
        version,
        f"Nom={table_name},{description},1",
        f"DateM={date_m},{date_m2}",
        f"NomOdbc={table_name}",
        f"Taille={taille},{taille}",
        "Pack=0,0",
        f"CE=Ce1,{ce_value}",
        "[CHAMPS]",
    ]

    for pf in positioned_fields:
        is_filler = pf["name"] == "Filler"
        repetition = pf.get("filler_size", 0) if is_filler else 0
        gel = 1 if is_filler else 3
        lines.append(f"Nom={pf['name']},{pf['position']},2,N,0,{repetition},N,{gel}")

    lines.append("[/CHAMPS]")

    return "\n".join(lines)


def generate_base_block(base_name, table_name, base_prefix):
    """Genere le bloc [BASE]."""
    version = generate_version_line()
    date_m = generate_hash()
    date_m_idx = generate_hash()
    fichier_name = base_name.upper()

    return (
        f"[BASE]\n"
        f"{version}\n"
        f"Nom={base_name},{table_name},1\n"
        f"DateM={date_m}\n"
        f"Fichier=I,0,{fichier_name}.dhfi\n"
        f"Versionbase=223\n"
        f"DateMIndex={date_m_idx}\n"
        f"[TABLES]\n"
        f"Nom={table_name},0\n"
        f"[/TABLES]"
    )


CE_VALUE_RE = re.compile(r"^[A-Z0-9]$")
INDEX_LETTER_RE = re.compile(r"^[A-Z0-9]$")


def validate_ce_value(ce_value, discriminator="Ce1"):
    """Valide ce_value selon le discriminator.

    Avec discriminator=Ce1 (defaut, Nature=1 char), ce_value doit etre
    1 caractere alphanumerique majuscule (A-Z, 0-9). Un multi-chiffres
    type "200" passe le script mais fait echouer la compilation DIVA
    avec "La lettre cle doit etre un seul caractere".
    """
    if not isinstance(ce_value, str):
        raise ValueError(
            f"ce_value doit etre une chaine, recu : {type(ce_value).__name__}"
        )
    if discriminator == "Ce1":
        if not CE_VALUE_RE.match(ce_value):
            raise ValueError(
                f"ce_value invalide : '{ce_value}'. Avec discriminator Ce1, "
                f"la valeur doit etre 1 caractere alphanumerique majuscule "
                f"(A-Z, 0-9). Pour numerique multi-chiffres, utiliser "
                f"discriminator=CeBin (non implemente)."
            )


def derive_index_letter(idx_name, used_letters):
    """Derive une lettre cle (1 char A-Z ou 0-9) pour un index.

    Strategie :
    1. Si Index_<X> ou X est 1 char alphanumerique : reutiliser X (uppercase)
    2. Sinon (Index_Pay, Index_Code...) : prendre la 1re lettre du suffixe
    3. Si conflit : allouer la 1re lettre libre A-Z

    Levant ValueError si A-Z deja toutes prises.
    """
    suffix = idx_name.replace("Index_", "", 1) if idx_name.startswith("Index_") else idx_name
    # Cas 1 : suffixe deja une lettre/chiffre unique
    if len(suffix) == 1 and suffix.isalnum():
        candidate = suffix.upper()
        if candidate not in used_letters:
            return candidate
    # Cas 2 : 1re lettre du suffixe
    if suffix and suffix[0].isalpha():
        candidate = suffix[0].upper()
        if candidate not in used_letters:
            return candidate
    # Cas 3 : fallback alloc libre
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if c not in used_letters:
            return c
    raise ValueError(
        f"Impossible de deriver une lettre cle pour '{idx_name}' : "
        f"A-Z toutes utilisees ({sorted(used_letters)})."
    )


def generate_index_blocks(indexes, base_name, ce_value, positioned_fields):
    """Genere les blocs [INDEX]."""
    blocks = []
    version = generate_version_line()

    # Construire un mapping nom -> {position, size} pour calculer les positions dans l'index
    field_map = {pf["name"]: pf for pf in positioned_fields}

    used_letters = set()
    for idx in indexes:
        date_m = generate_hash()
        letter = derive_index_letter(idx["name"], used_letters)
        if not INDEX_LETTER_RE.match(letter):
            raise ValueError(
                f"Lettre cle invalide pour index '{idx['name']}' : '{letter}' "
                f"(doit matcher [A-Z0-9])"
            )
        used_letters.add(letter)
        unique = "o" if idx.get("unique", False) else "n"

        cle_line = f"CLE={base_name},{letter},Ce1,2,{ce_value},{unique},1,n"

        # Calculer les positions dans l'index (cumulees)
        idx_lines = []
        idx_pos = 1
        for field_name in idx["fields"]:
            if field_name not in field_map:
                raise ValueError(
                    f"Champ '{field_name}' de l'index '{idx['name']}' "
                    f"n'existe pas dans la table"
                )
            idx_lines.append(f"Nom={field_name},{idx_pos},0,")
            idx_pos += field_map[field_name]["size"]

        block = (
            f"[INDEX]\n"
            f"{version}\n"
            f"Nom={idx['name']},{idx.get('description', idx['name'])},1\n"
            f"DateM={date_m}\n"
            f"{cle_line}\n"
            f"[CHAMPS]\n"
            + "\n".join(idx_lines) + "\n"
            f"[/CHAMPS]\n"
            f"[/INDEX]"
        )
        blocks.append({"name": idx["name"], "block": block})

    return blocks


def generate_indexl_lines(indexes, base_name, table_name):
    """Genere les lignes [INDEXL]."""
    return [f"Nom={base_name},{table_name},{idx['name']},0" for idx in indexes]


def generate_all(params):
    """Genere tous les blocs a partir des parametres.

    Args:
        params: dict avec table, description, ce_value, base, base_prefix,
                dict_name, fields, indexes, u_field_size, filler_size

    Returns:
        dict: rapport complet
    """
    table_name = params["table"]
    description = params.get("description", table_name)
    ce_value = params["ce_value"]
    base_name = params["base"]
    base_prefix = params.get("base_prefix", "")
    u_field_size = params.get("u_field_size", 500)
    filler_size = params.get("filler_size", 0)
    user_fields = params["fields"]
    indexes = params.get("indexes", [])

    # Garde-fou : Ce1 = 1 char alphanumerique majuscule (A-Z, 0-9)
    validate_ce_value(ce_value, discriminator=params.get("discriminator", "Ce1"))

    # Construire la liste complete des champs dans l'ordre
    all_fields = []
    all_fields.extend(STANDARD_FIELDS_BEFORE)
    all_fields.extend(user_fields)
    all_fields.extend(STANDARD_FIELDS_AFTER)

    # Ajouter Filler si taille > 0
    if filler_size > 0:
        all_fields.append({
            "name": "Filler",
            "nature": str(filler_size),
            "description": "Bourrage",
            "filler_size": filler_size,
        })

    # Ajouter U-field
    u_name = f"U{table_name}"
    all_fields.append({
        "name": u_name,
        "nature": str(u_field_size),
        "description": f"Reserve distributeur {table_name}",
    })

    # Calculer les positions
    positioned = compute_positions(all_fields)

    # Calculer la taille totale
    last = positioned[-1]
    taille = last["position"] + last["size"] - 1

    # Generer les blocs
    champ_blocks = generate_champ_blocks(user_fields, table_name, u_field_size)
    table_block = generate_table_block(table_name, description, ce_value, positioned, taille)
    base_block = generate_base_block(base_name, table_name, base_prefix)
    index_blocks = generate_index_blocks(indexes, base_name, ce_value, positioned)
    indexl_lines = generate_indexl_lines(indexes, base_name, table_name)

    # Construire le mapping positions pour reference
    positions = {}
    for pf in positioned:
        positions[pf["name"]] = {"position": pf["position"], "size": pf["size"]}

    return {
        "table": table_name,
        "blocks": {
            "champs": champ_blocks,
            "table": table_block,
            "base": base_block,
            "indexes": index_blocks,
            "indexl": indexl_lines,
        },
        "positions": positions,
        "taille": taille,
        "summary": {
            "champs_declares": len(champ_blocks),
            "champs_dans_table": len(positioned),
            "indexes": len(index_blocks),
            "indexl_lines": len(indexl_lines),
            "taille_table": taille,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Genere les 5 blocs INI pour ajouter une table dans un .dhsd"
    )
    parser.add_argument("--stdin", action="store_true",
                        help="Lire les parametres JSON depuis stdin")
    parser.add_argument("--fields", default=None,
                        help="Chemin vers le fichier JSON des parametres")
    parser.add_argument("--table", default=None, help="Nom de la table")
    parser.add_argument("--description", default=None, help="Description de la table")
    parser.add_argument("--ce-value", default=None, help="Valeur CE (1-9, A-Z)")
    parser.add_argument("--base", default=None, help="Nom de la base physique")
    parser.add_argument("--base-prefix", default=None, help="Prefixe de la base (Gtf, Ccf...)")
    parser.add_argument("--dict-name", default=None, help="Nom du dictionnaire (gtfdd, ccfdd...)")
    parser.add_argument("--u-field-size", type=int, default=500,
                        help="Taille du U-field en octets (defaut: 500)")
    parser.add_argument("--filler-size", type=int, default=0,
                        help="Taille du Filler en octets (defaut: 0 = pas de filler)")
    parser.add_argument("--output", default=None,
                        help="Chemin du fichier JSON de sortie (defaut: stdout)")

    args = parser.parse_args()

    # Charger les parametres
    params = None

    if args.stdin:
        try:
            params = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Erreur JSON stdin : {e}", file=sys.stderr)
            sys.exit(1)

    elif args.fields:
        try:
            with open(args.fields, "r", encoding="utf-8") as f:
                params = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Erreur lecture fichier : {e}", file=sys.stderr)
            sys.exit(1)

    elif args.table:
        # Mode ligne de commande (sans champs metier - juste la structure)
        print("Erreur: en mode CLI, utiliser --fields ou --stdin pour fournir les champs",
              file=sys.stderr)
        sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)

    # Valider les parametres obligatoires
    required = ["table", "ce_value", "base", "fields"]
    for key in required:
        if key not in params or not params[key]:
            print(f"Parametre obligatoire manquant : '{key}'", file=sys.stderr)
            sys.exit(1)

    # Generer
    try:
        result = generate_all(params)
    except ValueError as e:
        print(f"Erreur de generation : {e}", file=sys.stderr)
        sys.exit(1)

    # Sortie
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Blocs generes dans {args.output}", file=sys.stderr)
    else:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()


if __name__ == "__main__":
    main()
