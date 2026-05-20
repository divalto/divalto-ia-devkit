#!/usr/bin/env python3
"""Ecrit/modifie/supprime des enregistrements dans des fichiers ISAM Divalto via DhxIsam64.dll.

Usage:
    py write_isam.py --params-file data.json                     # op par defaut = insert
    py write_isam.py --params-file data.json --op insert
    py write_isam.py --params-file data.json --op update
    py write_isam.py --params-file data.json --op delete
    py write_isam.py --params-file data.json --dry-run
    py write_isam.py --params-file data.json --structure-dir structures/

Operations :
    insert : ecriture d'un nouvel enregistrement (defaut, ne necessite pas de cle)
    update : modification d'un enregistrement existant (necessite Key + KeyFields dans la JSON data)
    delete : suppression d'un enregistrement existant (idem update)

Format JSON pour update/delete :
    {
        "Fichier": "...",
        "Structure": "structure_xmenuf_m2.json",
        "Key": "A2",
        "KeyFields": ["Ce", "Reg", "Ordre"],
        "Donnees": {"Ce": "2", "Reg": "ZZZTEST", "Ordre": "10", ...}
    }

Sortie JSON:
    {success: bool, total: int, written: int, skipped: int, errors: [{index, file, error_code, message}]}

Exit codes:
    0 = toutes les operations ok
    1 = erreurs partielles
    2 = erreur fatale (DLL absente, params illisible, xisam_begin echoue)
"""

import argparse
import ctypes
import json
import os
import sys


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DLL_PATH = r"C:\divalto\sys\DhxIsam64.dll"
TASK_ID = 15  # defaut ; acquire_task() essaie 15 puis fallback 2..16
TDF_SIZE = 1024
TDF_NAME_OFFSET = 4
OPEN_MODE_SHARED = 0x50
WRITE_MODE = 0x50
ENCODING = "windows-1252"

ERROR_MESSAGES = {
    0: "Succes",
    2: "Fin de fichier / enregistrement absent (E_EOF)",
    3: "Fichier plein (E_OVF)",
    9: "L'enregistrement existe deja (E_EXIST)",
    12: "Erreur d'acces (tache non initialisee ou TDF invalide)",
    20: "Fichier introuvable (E_ABSENT)",
    47: "Erreur de partage (E_SHARE)",
}


# ---------------------------------------------------------------------------
# Chargement DLL
# ---------------------------------------------------------------------------

def load_dll():
    """Charge DhxIsam64.dll et configure les signatures ctypes."""
    if not os.path.isfile(DLL_PATH):
        print(f"DLL introuvable : {DLL_PATH}", file=sys.stderr)
        return None

    dll = ctypes.WinDLL(DLL_PATH)

    # xisam_begin(ushort tache) -> short
    dll.xisam_begin.argtypes = [ctypes.c_ushort]
    dll.xisam_begin.restype = ctypes.c_short

    # xisam_end(ushort tache) -> ushort
    dll.xisam_end.argtypes = [ctypes.c_ushort]
    dll.xisam_end.restype = ctypes.c_ushort

    # xisam_topenlong(ushort tache, byte[] tdf, byte[] mode) -> ushort
    dll.xisam_topenlong.argtypes = [
        ctypes.c_ushort,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.POINTER(ctypes.c_ubyte),
    ]
    dll.xisam_topenlong.restype = ctypes.c_ushort

    # xisam_twritelong(ushort tache, byte[] tdf, byte[] enreg, ushort lg, byte[] mode) -> ushort
    dll.xisam_twritelong.argtypes = [
        ctypes.c_ushort,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_ushort,
        ctypes.POINTER(ctypes.c_ubyte),
    ]
    dll.xisam_twritelong.restype = ctypes.c_ushort

    # xisam_tpreadlong -- protected read (positionnement + lecture + reservation)
    dll.xisam_tpreadlong.argtypes = dll.xisam_twritelong.argtypes
    dll.xisam_tpreadlong.restype = ctypes.c_ushort

    # xisam_trewritelong(ushort tache, byte[] tdf, byte[] enreg, ushort lg) -> ushort  (UPDATE)
    dll.xisam_trewritelong.argtypes = [
        ctypes.c_ushort,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_ushort,
    ]
    dll.xisam_trewritelong.restype = ctypes.c_ushort

    # xisam_tdeletelong(ushort tache, byte[] tdf, byte[] enreg, ushort lg) -> ushort  (DELETE)
    dll.xisam_tdeletelong.argtypes = dll.xisam_trewritelong.argtypes
    dll.xisam_tdeletelong.restype = ctypes.c_ushort

    # xisam_tcloselong(ushort tache, byte[] tdf) -> ushort
    dll.xisam_tcloselong.argtypes = [
        ctypes.c_ushort,
        ctypes.POINTER(ctypes.c_ubyte),
    ]
    dll.xisam_tcloselong.restype = ctypes.c_ushort

    return dll


# ---------------------------------------------------------------------------
# Chargement JSON
# ---------------------------------------------------------------------------

def load_structure(path):
    """Charge et retourne un fichier de structure JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_params(path):
    """Charge le fichier data JSON et normalise en liste d'entrees.

    Chaque entree est un dict {Fichier, Structure, Donnees} ou Donnees est un dict unique.

    Formats supportes :
      1. Objet simple  : {Fichier, Structure, Donnees: {...}}
      2. Batch meme fic: {Fichier, Structure, Donnees: [{...}, ...]}
      3. Batch multi   : [{Fichier, Structure, Donnees}, ...]
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    entries = []

    if isinstance(raw, list):
        # Format 3 : tableau top-level
        for item in raw:
            entries.extend(_expand_entry(item))
    elif isinstance(raw, dict):
        entries.extend(_expand_entry(raw))
    else:
        raise ValueError(f"Format JSON inattendu : {type(raw).__name__}")

    return entries


def _expand_entry(item):
    """Expanse une entree qui peut avoir Donnees comme dict ou liste.

    Conserve les cles auxiliaires (Key, KeyFields) pour les ops update/delete.
    """
    donnees = item["Donnees"]
    base = {k: v for k, v in item.items() if k != "Donnees"}

    if isinstance(donnees, list):
        return [{**base, "Donnees": d} for d in donnees]
    else:
        return [{**base, "Donnees": donnees}]


# ---------------------------------------------------------------------------
# Construction d'enregistrement
# ---------------------------------------------------------------------------

def build_record(donnees, structure_fields, record_size):
    """Construit un buffer binaire a partir des donnees et de la structure.

    Args:
        donnees: dict {NomChamp: valeur_string}
        structure_fields: liste de {Nom, Offset, Taille}
        record_size: taille totale du buffer

    Returns:
        ctypes array (c_ubyte * record_size), liste de warnings
    """
    rec = (ctypes.c_ubyte * record_size)()
    # Initialiser avec des espaces (0x20)
    for i in range(record_size):
        rec[i] = 0x20

    # Index par nom de champ
    field_map = {f["Nom"]: f for f in structure_fields}

    warnings = []
    for nom, valeur in donnees.items():
        if nom not in field_map:
            warnings.append(f"Champ inconnu dans la structure : {nom}")
            continue

        field = field_map[nom]
        offset = field["Offset"]
        taille = field["Taille"]
        justify = field.get("Justify", "left")  # defaut : left-aligned (texte)

        # Encoder la valeur en Windows-1252
        val_str = str(valeur)
        if justify == "right":
            # Champs numeriques : strip + re-pad a gauche sur la taille du champ.
            # Idempotent : accepte "51" comme "      51" -- resultat identique.
            val_str = val_str.strip()
        try:
            val_bytes = val_str.encode(ENCODING)
        except UnicodeEncodeError:
            warnings.append(f"Champ {nom} : valeur non encodable en {ENCODING}")
            continue

        if justify == "right":
            # Cadrage a droite : padding espaces a gauche
            if len(val_bytes) > taille:
                val_bytes = val_bytes[-taille:]  # troncature cote gauche
            else:
                val_bytes = b" " * (taille - len(val_bytes)) + val_bytes
            for j in range(taille):
                rec[offset + j] = val_bytes[j]
        else:
            # Cadrage a gauche (defaut texte) : copier depuis offset, padding droit implicite (buffer init a 0x20)
            copy_len = min(len(val_bytes), taille)
            for j in range(copy_len):
                rec[offset + j] = val_bytes[j]

    return rec, warnings


# ---------------------------------------------------------------------------
# Ecriture ISAM
# ---------------------------------------------------------------------------

def make_tdf(fichier_path):
    """Cree un buffer TDF avec le chemin du fichier."""
    tdf = (ctypes.c_ubyte * TDF_SIZE)()
    name_bytes = fichier_path.encode(ENCODING)
    copy_len = min(len(name_bytes), 256)
    for i in range(copy_len):
        tdf[TDF_NAME_OFFSET + i] = name_bytes[i]
    return tdf


def record_matches_key_fields(record_buf, donnees, key_fields, structure_fields):
    """Verifie que l'enreg lu correspond exactement aux valeurs de cle attendues.

    tpreadlong mode F positionne sur l'enreg le plus proche, pas forcement l'exact.
    Sans cette verification, update/delete risquent d'operer sur le mauvais enreg.
    """
    field_map = {f["Nom"]: f for f in structure_fields}
    for field_name in key_fields:
        if field_name not in field_map:
            return False
        field = field_map[field_name]
        offset = field["Offset"]
        size = field["Taille"]
        actual = bytes(record_buf[offset:offset + size]).rstrip(b" ")
        expected = str(donnees.get(field_name, "")).encode(ENCODING).rstrip(b" ")
        if actual != expected:
            return False
    return True


def build_tdf_key(tdf, key, key_fields, donnees, structure_fields):
    """Ecrit dans TDF la lettre d'index + la valeur exacte de la cle pour positionnement.

    Convention pour update/delete :
      - `key`        : nom/lettre de l'index (seul le PREMIER caractere est envoye au DLL)
      - `key_fields` : liste ordonnee des champs composant la valeur de la cle

    TDF.KEY layout (offset 261) :
      - KEY[0]   = lettre d'index (premier char de `key`)
      - KEY[1..] = concatenation des `key_fields` encodes comme dans l'enreg

    Args:
        tdf: buffer TDF (c_ubyte * 1024)
        key: nom de cle (ex: "A", "A2", "B") -- seul key[0] est utilise
        key_fields: liste de noms de champs formant la cle, dans l'ordre
        donnees: dict {NomChamp: valeur}
        structure_fields: definition de la structure
    """
    # Reinitialiser la zone cle a espaces (KEY fait 256 octets, 261..516)
    for i in range(261, 517):
        tdf[i] = 0x20

    # Ecrire UNIQUEMENT la lettre d'index (KEY[0])
    tdf[261] = ord(key[0])

    # Ecrire la valeur de cle en concatenant les key_fields a partir de KEY[1]
    field_map = {f["Nom"]: f for f in structure_fields}
    value_offset = 262
    for field_name in key_fields:
        if field_name not in field_map:
            raise ValueError(f"Champ cle inconnu : {field_name}")
        field = field_map[field_name]
        taille = field["Taille"]
        val_str = str(donnees.get(field_name, ""))
        val_bytes = val_str.encode(ENCODING).ljust(taille, b" ")[:taille]
        for j in range(len(val_bytes)):
            tdf[value_offset + j] = val_bytes[j]
        value_offset += taille


def resolve_key(structure, key, key_fields):
    """Resout la cle logique contre structure.Keys (si declare).

    Trois cas :
      1. `key` = nom d'index declare dans structure.Keys : retourne (Letter, Fields) de la structure.
         `key_fields` fourni par l'appelant est ignore (priorite a la structure = source de verite).
      2. `key` = lettre (1 caractere) + `key_fields` fourni : retourne (key, key_fields).
      3. Aucun des cas : erreur.

    Retourne (letter, fields) ou leve ValueError.
    """
    keys_meta = structure.get("Keys") or {}
    if key in keys_meta:
        meta = keys_meta[key]
        return meta["Letter"], meta["Fields"]
    if key and key_fields:
        return key[0], list(key_fields)
    raise ValueError(
        f"Cle '{key}' non trouvee dans structure.Keys et 'KeyFields' manquant. "
        f"Options : passer un nom d'index declare ({list(keys_meta.keys())}) ou fournir 'Key' + 'KeyFields'."
    )


def update_single(dll, tache, entry, structure_dir, dry_run):
    """Modifie un enregistrement existant.

    Sequence : open -> tpreadlong R (reserve) -> verification exacte -> trewritelong -> close.
    Revision R-014 (2026-04-22) : unifie avec delete_single sur tpreadlong mode R.
    """
    fichier = entry["Fichier"]
    struct_ref = entry["Structure"]
    donnees = entry["Donnees"]
    key = entry.get("Key")

    if not key:
        return {"written": False, "skipped": False, "error_code": -1,
                "message": "update : 'Key' est requis (nom d'index logique ou lettre DLL + KeyFields)"}

    struct_path = os.path.join(structure_dir, struct_ref)
    if not os.path.isfile(struct_path):
        return {"written": False, "skipped": False, "error_code": -1,
                "message": f"Structure introuvable : {struct_path}"}

    structure = load_structure(struct_path)
    try:
        letter, key_fields = resolve_key(structure, key, entry.get("KeyFields"))
    except ValueError as e:
        return {"written": False, "skipped": False, "error_code": -1, "message": str(e)}
    key = letter
    record_size = structure["TailleEnreg"]
    fields = structure["Structure"]

    new_rec, warnings = build_record(donnees, fields, record_size)
    for w in warnings:
        print(f"  Warning: {w}", file=sys.stderr)

    if dry_run:
        return {"written": True, "skipped": False, "error_code": 0,
                "message": "Dry run : update valide (non applique)"}

    tdf = make_tdf(fichier)
    mode_open = (ctypes.c_ubyte * 1)(OPEN_MODE_SHARED)
    ret = dll.xisam_topenlong(ctypes.c_ushort(tache), tdf, mode_open)
    if ret != 0:
        msg = ERROR_MESSAGES.get(ret, f"Erreur inconnue ({ret})")
        return {"written": False, "skipped": False, "error_code": ret,
                "message": f"Ouverture echouee : {msg}"}

    # Positionner la cle
    try:
        build_tdf_key(tdf, key, key_fields, donnees, fields)
    except ValueError as e:
        dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)
        return {"written": False, "skipped": False, "error_code": -1, "message": str(e)}

    # Positionner + reserver via tpreadlong mode R (Reserve) : acquiert un lock
    # record-by-record. Le positionnement est porte par TDF.KEY (Greater-or-Equal implicite).
    # Revision R-014 (2026-04-22) : remplace l'usage historique de treadlong mode G
    # (G etait un code invalide interprete comme alias de R par effet de bord).
    current_rec = (ctypes.c_ubyte * record_size)()
    mode_read = (ctypes.c_ubyte * 1)(ord("R"))
    ret = dll.xisam_tpreadlong(
        ctypes.c_ushort(tache), tdf, current_rec,
        ctypes.c_ushort(record_size), mode_read,
    )
    if ret != 0:
        dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)
        msg = ERROR_MESSAGES.get(ret, f"Erreur inconnue ({ret})")
        return {"written": False, "skipped": False, "error_code": ret,
                "message": f"Enreg cible introuvable : {msg}"}

    # VERIFICATION CRITIQUE : positionnement GE implicite peut glisser sur un enreg voisin
    # si la cle cible n'existe pas. Toujours verifier champ par champ que la cle correspond
    # exactement. Sans cette verif, on risque d'ecraser un autre enreg (corruption silencieuse).
    if not record_matches_key_fields(current_rec, donnees, key_fields, fields):
        dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)
        return {"written": False, "skipped": False, "error_code": 2,
                "message": "Enreg cible introuvable (match approximatif refuse)"}

    # Reecrire avec les nouvelles valeurs
    ret = dll.xisam_trewritelong(
        ctypes.c_ushort(tache), tdf, new_rec,
        ctypes.c_ushort(record_size),
    )
    dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)

    if ret == 0:
        return {"written": True, "skipped": False, "error_code": 0, "message": "OK update"}
    msg = ERROR_MESSAGES.get(ret, f"Erreur inconnue ({ret})")
    return {"written": False, "skipped": False, "error_code": ret, "message": msg}


def delete_single(dll, tache, entry, structure_dir, dry_run):
    """Supprime un enregistrement existant.

    Sequence : open -> tpreadlong R (reserve) -> verification exacte -> tdeletelong -> close.
    Revision R-014 (2026-04-22) : unifie avec update_single sur tpreadlong mode R.
    Remplace l'usage historique de tpreadlong mode F (tolerant = risque corruption).
    """
    fichier = entry["Fichier"]
    struct_ref = entry["Structure"]
    donnees = entry["Donnees"]
    key = entry.get("Key")

    if not key:
        return {"written": False, "skipped": False, "error_code": -1,
                "message": "delete : 'Key' est requis (nom d'index logique ou lettre DLL + KeyFields)"}

    struct_path = os.path.join(structure_dir, struct_ref)
    if not os.path.isfile(struct_path):
        return {"written": False, "skipped": False, "error_code": -1,
                "message": f"Structure introuvable : {struct_path}"}

    structure = load_structure(struct_path)
    try:
        letter, key_fields = resolve_key(structure, key, entry.get("KeyFields"))
    except ValueError as e:
        return {"written": False, "skipped": False, "error_code": -1, "message": str(e)}
    key = letter
    record_size = structure["TailleEnreg"]
    fields = structure["Structure"]

    if dry_run:
        return {"written": True, "skipped": False, "error_code": 0,
                "message": "Dry run : delete valide (non applique)"}

    tdf = make_tdf(fichier)
    mode_open = (ctypes.c_ubyte * 1)(OPEN_MODE_SHARED)
    ret = dll.xisam_topenlong(ctypes.c_ushort(tache), tdf, mode_open)
    if ret != 0:
        msg = ERROR_MESSAGES.get(ret, f"Erreur inconnue ({ret})")
        return {"written": False, "skipped": False, "error_code": ret,
                "message": f"Ouverture echouee : {msg}"}

    try:
        build_tdf_key(tdf, key, key_fields, donnees, fields)
    except ValueError as e:
        dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)
        return {"written": False, "skipped": False, "error_code": -1, "message": str(e)}

    # Positionner + reserver via tpreadlong mode R (Reserve) : acquiert un lock
    # record-by-record. Le positionnement est porte par TDF.KEY (Greater-or-Equal implicite).
    # Revision R-014 (2026-04-22) : remplace l'usage historique de tpreadlong mode F
    # (F = "Forcee" = tolerant, positionne sur l'enreg le plus proche = risque corruption).
    current_rec = (ctypes.c_ubyte * record_size)()
    mode_read = (ctypes.c_ubyte * 1)(ord("R"))
    ret = dll.xisam_tpreadlong(
        ctypes.c_ushort(tache), tdf, current_rec,
        ctypes.c_ushort(record_size), mode_read,
    )
    if ret != 0:
        dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)
        msg = ERROR_MESSAGES.get(ret, f"Erreur inconnue ({ret})")
        return {"written": False, "skipped": False, "error_code": ret,
                "message": f"Enreg cible introuvable : {msg}"}

    # VERIFICATION CRITIQUE : positionnement GE implicite peut glisser sur un enreg voisin
    # si la cle cible n'existe pas. Toujours verifier champ par champ que la cle correspond
    # exactement. Sans cette verif, on risque de supprimer un autre enreg (corruption silencieuse).
    if not record_matches_key_fields(current_rec, donnees, key_fields, fields):
        dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)
        return {"written": False, "skipped": False, "error_code": 2,
                "message": "Enreg cible introuvable (match approximatif refuse)"}

    # Supprimer
    ret = dll.xisam_tdeletelong(
        ctypes.c_ushort(tache), tdf, current_rec,
        ctypes.c_ushort(record_size),
    )
    dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)

    if ret == 0:
        return {"written": True, "skipped": False, "error_code": 0, "message": "OK delete"}
    msg = ERROR_MESSAGES.get(ret, f"Erreur inconnue ({ret})")
    return {"written": False, "skipped": False, "error_code": ret, "message": msg}


def write_single(dll, tache, entry, structure_dir, dry_run):
    """Ecrit un enregistrement unique. Retourne un dict resultat."""
    fichier = entry["Fichier"]
    struct_ref = entry["Structure"]
    donnees = entry["Donnees"]

    # Resoudre le chemin de la structure
    struct_path = os.path.join(structure_dir, struct_ref)
    if not os.path.isfile(struct_path):
        return {"written": False, "skipped": False, "error_code": -1,
                "message": f"Structure introuvable : {struct_path}"}

    # Charger la structure
    structure = load_structure(struct_path)
    record_size = structure["TailleEnreg"]
    fields = structure["Structure"]

    # Construire l'enregistrement
    rec, warnings = build_record(donnees, fields, record_size)
    for w in warnings:
        print(f"  Warning: {w}", file=sys.stderr)

    if dry_run:
        return {"written": True, "skipped": False, "error_code": 0,
                "message": "Dry run : enregistrement valide (non ecrit)"}

    # Ouvrir le fichier ISAM
    tdf = make_tdf(fichier)
    mode_open = (ctypes.c_ubyte * 1)(OPEN_MODE_SHARED)
    ret = dll.xisam_topenlong(ctypes.c_ushort(tache), tdf, mode_open)
    if ret != 0:
        msg = ERROR_MESSAGES.get(ret, f"Erreur inconnue ({ret})")
        return {"written": False, "skipped": False, "error_code": ret,
                "message": f"Ouverture echouee : {msg}"}

    # Ecrire
    mode_write = (ctypes.c_ubyte * 1)(WRITE_MODE)
    ret = dll.xisam_twritelong(
        ctypes.c_ushort(tache), tdf, rec,
        ctypes.c_ushort(record_size), mode_write,
    )

    # Fermer
    dll.xisam_tcloselong(ctypes.c_ushort(tache), tdf)

    if ret == 0:
        return {"written": True, "skipped": False, "error_code": 0, "message": "OK"}
    elif ret == 9:
        return {"written": False, "skipped": True, "error_code": 9,
                "message": ERROR_MESSAGES[9]}
    else:
        msg = ERROR_MESSAGES.get(ret, f"Erreur inconnue ({ret})")
        return {"written": False, "skipped": False, "error_code": ret,
                "message": msg}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ecrit des enregistrements dans des fichiers ISAM Divalto"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--params-file",
        help="Fichier JSON data (unitaire ou batch)"
    )
    group.add_argument(
        "--stdin", action="store_true",
        help="Lire le JSON data depuis stdin"
    )
    parser.add_argument(
        "--structure-dir", default=None,
        help="Repertoire des structures JSON (defaut : repertoire du params-file)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Valide sans ecrire (fonctionne sans la DLL)"
    )
    parser.add_argument(
        "--op", choices=["insert", "update", "delete"], default="insert",
        help="Operation a effectuer (defaut : insert)"
    )
    args = parser.parse_args()

    # Resoudre structure-dir
    if args.structure_dir:
        structure_dir = args.structure_dir
    elif args.params_file:
        structure_dir = os.path.dirname(os.path.abspath(args.params_file))
    else:
        structure_dir = os.getcwd()

    # Charger les parametres
    try:
        if args.stdin:
            raw = json.loads(sys.stdin.read())
            entries = []
            if isinstance(raw, list):
                for item in raw:
                    entries.extend(_expand_entry(item))
            else:
                entries.extend(_expand_entry(raw))
        else:
            entries = load_params(args.params_file)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Erreur chargement params : {e}", file=sys.stderr)
        sys.exit(2)

    total = len(entries)
    written = 0
    skipped = 0
    errors = []

    # Charger la DLL (sauf dry-run)
    dll = None
    task_id = TASK_ID
    if not args.dry_run:
        dll = load_dll()
        if dll is None:
            sys.exit(2)

        # Acquerir un slot de tache (15 par defaut, sinon fallback 2..16)
        acquired = None
        for candidate in [TASK_ID] + [t for t in range(2, 17) if t != TASK_ID]:
            ret = dll.xisam_begin(ctypes.c_ushort(candidate))
            if ret == candidate:
                acquired = candidate
                break
        if acquired is None:
            print("xisam_begin : aucun slot libre (2..16)", file=sys.stderr)
            sys.exit(2)
        task_id = acquired

    # Dispatcher par operation
    op_funcs = {
        "insert": write_single,
        "update": update_single,
        "delete": delete_single,
    }
    op_fn = op_funcs[args.op]

    try:
        for i, entry in enumerate(entries):
            result = op_fn(dll, task_id, entry, structure_dir, args.dry_run)

            if result["written"]:
                written += 1
            elif result["skipped"]:
                skipped += 1

            if result["error_code"] != 0:
                errors.append({
                    "index": i,
                    "file": entry["Fichier"],
                    "error_code": result["error_code"],
                    "message": result["message"],
                })
    finally:
        if dll is not None:
            dll.xisam_end(ctypes.c_ushort(task_id))

    # Succes si tout ecrit ou seulement des doublons (code 9)
    all_only_exist = all(e["error_code"] == 9 for e in errors) if errors else True
    success = (written + skipped == total) and all_only_exist

    output = {
        "success": success,
        "total": total,
        "written": written,
        "skipped": skipped,
        "errors": errors,
    }

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    print()

    if not success and errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
