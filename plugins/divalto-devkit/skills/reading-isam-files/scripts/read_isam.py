#!/usr/bin/env python3
"""Lit des enregistrements dans un fichier ISAM Divalto (.dhfi) via DhxIsam64.dll.

Usage :
    py read_isam.py --file "chemin/a5f.dhfi" --structure "structure_a5f_m4.json" --key "A4"
    py read_isam.py --file "chemin/g3f.dhfi" --structure "structure_xmenuf_m2.json" --key "A2" --key-value "FIC"
    py read_isam.py --file "chemin/a5f.dhfi" --structure "structure_a5f_m4.json" --key "A4" --max 5
    py read_isam.py --file "chemin/a5f.dhfi" --structure "structure_a5f_m4.json" --key "A4" --filter "ZoomNum=9490"
    py read_isam.py --file "chemin/g3f.dhfi" --structure "structure_xmenuf_m2.json" --key "A2" --reverse --max 3

Sortie JSON :
    {
        "success": true,
        "file": "chemin/a5f.dhfi",
        "records": [ { "Ce": "4", "ZoomNum": "9490", ... }, ... ],
        "count": 1
    }

Typage optionnel : chaque champ de la Structure peut declarer un Type :
    - "C" (caractere)  : rstrip -- preserve les espaces de tete
    - "N" (numerique)  : strip  -- supprime les espaces des 2 cotes
    - "D" (date)       : strip  -- supprime les espaces des 2 cotes (formatage a faire par l'appelant)
    - "B" (binaire)    : retour hex uppercase -- aucun decode texte (utile pour FILETIME, UID, etc.)
    - absent           : strip  -- comportement historique (back-compat)

Si un champ de type texte contient des bytes non decodables en cp1252, un warning
est emis sur stderr et les bytes invalides sont remplaces par "?".

Exit codes : 0 = succes, 1 = aucun enregistrement, 2 = erreur
"""

import argparse
import ctypes
import json
import os
import sys

DLL_PATH = r"C:\divalto\sys\DhxIsam64.dll"
ENCODING = "windows-1252"


def load_dll():
    """Charge DhxIsam64.dll."""
    try:
        return ctypes.WinDLL(DLL_PATH)
    except OSError:
        return None


def load_structure(path):
    """Charge le fichier de structure JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def decode_record(raw_bytes, structure):
    """Decode un enregistrement binaire en dict selon la structure.

    Si un champ declare un Type, applique la semantique :
        - "B" (binaire)   : raw_bytes.hex().upper() -- aucun decode texte
        - "C" (caractere) : rstrip (preserve leading spaces)
        - "N" (numerique) : strip (both sides)
        - "D" (date)      : strip (both sides)
        - absent / autre  : strip (both sides) -- comportement historique

    Decodage defensif : si le decode cp1252 echoue (bytes invalides), remplace par "?"
    et warning stderr, au lieu de planter tout le parcours.
    """
    result = {}
    for field in structure["Structure"]:
        offset = field["Offset"]
        size = field["Taille"]
        segment = raw_bytes[offset:offset + size]
        field_type = field.get("Type")
        if field_type == "B":
            result[field["Nom"]] = segment.hex().upper()
            continue
        try:
            raw = segment.decode(ENCODING)
        except UnicodeDecodeError as e:
            raw = segment.decode(ENCODING, errors="replace")
            print(
                f"Warning: decode cp1252 echoue sur {field['Nom']} "
                f"(offset {offset}, {size} octets) : {e}. Bytes invalides remplaces par '?'.",
                file=sys.stderr,
            )
        if field_type == "C":
            value = raw.rstrip()
        else:
            value = raw.strip()
        result[field["Nom"]] = value
    return result


def matches_filter(record, filters):
    """Verifie si un enregistrement correspond aux filtres."""
    for f in filters:
        key, val = f.split("=", 1)
        record_val = record.get(key, "").strip()
        filter_val = val.strip()
        if record_val != filter_val:
            return False
    return True


def read_records(dll, file_path, structure, key, key_value=None, max_records=100, filters=None, reverse=False, reservation=b"P"):
    """Lit les enregistrements d'un fichier ISAM.

    Args:
        dll: DLL chargee
        file_path: chemin du fichier .dhfi
        structure: dict de structure (depuis JSON)
        key: cle d'index (ex: "A4", "A2")
        key_value: valeur de cle optionnelle pour positionner (ex: "FIC")
        max_records: nombre max d'enregistrements a lire
        filters: liste de filtres "Champ=Valeur"
        reverse: parcours en sens inverse (positionne en fin via 0xFF en fin de cle)
        reservation: code de reservation passe a la DLL (defaut b"P" = Partage, pas de lock).
                     Autres valeurs officielles : b"F" (Forcee), b"R" (Reserve -- consomme la
                     table a ~1003 slots, a n'utiliser qu'en read-then-update).

    Revision 2026-04-22 (R-014) : suppression des concepts `initial_mode` / `next_mode`.
    Le parametre `mode` de la DLL est un code de reservation uniquement (pas de direction).
    Le positionnement est entierement porte par la cle dans TDF (Greater-or-Equal implicite).
    La direction inverse est encodee par 0xFF en fin de cle, pas par le mode.

    Returns:
        (list of dict, error_message)
    """
    # Acquerir un slot (15 par defaut, fallback 2..16)
    acquired = None
    for candidate in [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 16]:
        r = dll.xisam_begin(ctypes.c_ushort(candidate))
        if r == candidate:
            acquired = candidate
            break
    if acquired is None:
        return None, "xisam_begin : aucun slot libre (2..16)"
    TACHE = ctypes.c_ushort(acquired)

    # Creer TDF et ouvrir le fichier
    tdf = (ctypes.c_byte * 1024)(*([0x20] * 1024))
    path_bytes = file_path.encode(ENCODING)
    for i, b in enumerate(path_bytes[:256]):
        tdf[4 + i] = b

    ret = dll.xisam_topenlong(TACHE, tdf, b"P")
    if ret != 0:
        dll.xisam_end(TACHE)
        return None, f"Erreur ouverture fichier: code {ret}"

    # Positionner la cle (KEY[0] = lettre index, KEY[1..] = valeur)
    for i, c in enumerate(key[:32]):
        tdf[261 + i] = ord(c)

    key_end = 261 + len(key)
    if key_value:
        padded = key_value.ljust(8)
        for i, c in enumerate(padded[:8]):
            tdf[key_end + i] = ord(c)
        key_end += len(padded)

    # Pour reverse sans key_value : positionner en fin de cle (un seul octet 0xFF apres la cle logique suffit)
    if reverse and not key_value:
        if key_end < 517:
            tdf[key_end] = 0xFF

    record_size = structure["TailleEnreg"]
    record = (ctypes.c_byte * record_size)(*([0x20] * record_size))

    # Choix de la fonction de lecture :
    #   - treadlong pour parcours forward standard (positionnement + lecture)
    #   - tpreadlong pour parcours reverse (supporte positionnement par cle artificielle haute 0xFF)
    # Le `mode` passe n'est PAS un code de direction : c'est un code de reservation (voir docstring).
    read_fn = dll.xisam_tpreadlong if reverse else dll.xisam_treadlong

    # Premier read et iterations suivantes : meme code de reservation.
    # Positionnement et direction sont portes par TDF.KEY (lettre + valeur + eventuel 0xFF pour reverse).
    ret = read_fn(TACHE, tdf, record, record_size, reservation)

    records = []
    count = 0
    saturation_warned = False
    while ret == 0 and count < max_records:
        raw = bytes(record)
        decoded = decode_record(raw, structure)

        # Si key_value, verifier que le 2e champ (typiquement Reg) correspond encore.
        # C'est la detection applicative de rupture de cle (Ce change, Reg change, etc.).
        if key_value:
            if len(structure["Structure"]) > 1:
                check_field = structure["Structure"][1]["Nom"]
                if decoded.get(check_field, "").strip() != key_value.strip():
                    break

        # Appliquer les filtres
        if filters:
            if matches_filter(decoded, filters):
                records.append(decoded)
        else:
            records.append(decoded)

        count += 1
        ret = read_fn(TACHE, tdf, record, record_size, reservation)

    # Avertissement si saturation de la table de reservations (mode R ou alias invalide)
    if ret == 46 and not saturation_warned:
        print(
            f"Warning: ret=46 detecte (table de reservations ISAM saturee). "
            f"Utilisez reservation='P' (par defaut) pour un parcours lecture seule, "
            f"ou liberez les reservations via close entre deux lectures 'R'.",
            file=sys.stderr,
        )

    dll.xisam_tcloselong(TACHE, tdf)
    dll.xisam_end(TACHE)

    return records, None


def main():
    # R-004 (2026-04-23) : force stdout en utf-8 pour que la sortie JSON soit lisible
    # par json.load(encoding="utf-8"). Sans ca, stdout est cp1252 sur Windows et les
    # accents du standard ERP (ex : "Creation", "Modele") deviennent des bytes 0xE9
    # non decodables en utf-8.
    if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Lit des enregistrements dans un fichier ISAM Divalto"
    )
    parser.add_argument("--file", required=True, help="Chemin du fichier .dhfi")
    parser.add_argument("--structure", required=True, help="Chemin du fichier structure JSON")
    parser.add_argument("--structure-dir", default=None, help="Repertoire des structures")
    parser.add_argument("--key", required=True, help="Cle d'index (ex: A4, A2)")
    parser.add_argument("--key-value", default=None, help="Valeur de cle pour filtrer (ex: FIC)")
    parser.add_argument("--max", type=int, default=100, help="Nombre max d'enregistrements (defaut: 100)")
    parser.add_argument("--filter", action="append", default=[], help="Filtre Champ=Valeur (cumulable)")
    parser.add_argument("--fields", default=None, help="Champs a afficher (separes par virgule)")
    parser.add_argument("--reverse", action="store_true", help="Parcours en sens inverse (positionne via 0xFF en fin de cle TDF)")
    parser.add_argument("--reservation", default="P", choices=["F", "P", "R"],
                        help="Code de reservation DLL (defaut P=Partage, pas de lock). F=Forcee, R=Reserve (consomme la table a ~1003 slots)")
    args = parser.parse_args()

    # Charger DLL
    dll = load_dll()
    if dll is None:
        print(f"Erreur : DLL introuvable : {DLL_PATH}", file=sys.stderr)
        sys.exit(2)

    # Resoudre chemin structure
    struct_path = args.structure
    if args.structure_dir:
        struct_path = os.path.join(args.structure_dir, args.structure)
    if not os.path.isfile(struct_path):
        print(f"Erreur : structure introuvable : {struct_path}", file=sys.stderr)
        sys.exit(2)

    # Charger structure
    try:
        structure = load_structure(struct_path)
    except Exception as e:
        print(f"Erreur chargement structure : {e}", file=sys.stderr)
        sys.exit(2)

    # Verifier fichier
    if not os.path.isfile(args.file):
        print(f"Erreur : fichier introuvable : {args.file}", file=sys.stderr)
        sys.exit(2)

    # Lire
    records, error = read_records(
        dll, args.file, structure,
        key=args.key,
        key_value=args.key_value,
        max_records=args.max,
        filters=args.filter,
        reverse=args.reverse,
        reservation=args.reservation.encode("ascii"),
    )

    if error:
        print(f"Erreur : {error}", file=sys.stderr)
        sys.exit(2)

    # Filtrer les champs si --fields
    if args.fields and records:
        field_list = [f.strip() for f in args.fields.split(",")]
        records = [{k: r[k] for k in field_list if k in r} for r in records]

    result = {
        "success": len(records) > 0,
        "file": args.file,
        "records": records,
        "count": len(records),
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    sys.exit(0 if records else 1)


if __name__ == "__main__":
    main()
