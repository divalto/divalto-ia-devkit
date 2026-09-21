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

DLL_NAME = "DhxIsam64.dll"
DEFAULT_SYS_DIR = r"C:\divalto\sys"

# --- Resolution du repertoire sys/ de Divalto (emplacement de DhxIsam64.dll) ---------
# Vendoring (copie autonome identique dans chaque skill ISAM) : ne PAS importer le
# resolveur d'un autre skill. Ordre : --dll-path / --sys-dir (CLI, strict) > env
# DIVALTO_SYS_DIR > registre Divalto (HKLM\SOFTWARE\[WOW6432Node\]Divalto\divalto.ini\System
# -> CheminUl1, puis \sys) > fallback C:\divalto\sys. Le chemin en dur sur C: cassait
# toute operation ISAM sur un poste ou Divalto est installe ailleurs (ex. K:\).
# Discipline registre P-C : on lit UNIQUEMENT la valeur CheminUl1 sous les cles documentees.
_DIVA_REG_SUBKEYS = [
    r"SOFTWARE\WOW6432Node\Divalto\divalto.ini\System",
    r"SOFTWARE\Divalto\divalto.ini\System",
]


def _sys_dir_from_registry():
    """Renvoie <CheminUl1>\\sys via le registre Windows, ou None si indisponible."""
    try:
        import winreg
    except ImportError:
        return None
    for subkey in _DIVA_REG_SUBKEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as key:
                root, _ = winreg.QueryValueEx(key, "CheminUl1")
        except (FileNotFoundError, OSError):
            continue
        if root:
            return os.path.join(root, "sys")
    return None


def resolve_sys_dir(explicit_sys_dir=None):
    """Repertoire sys/ de Divalto. Override CLI (--sys-dir) honore STRICTEMENT ; sinon
    auto-resolution best-effort : env DIVALTO_SYS_DIR > registre > fallback, en prenant
    le 1er repertoire ou DhxIsam64.dll existe reellement."""
    if explicit_sys_dir:
        return explicit_sys_dir
    dirs = []
    env_dir = os.environ.get("DIVALTO_SYS_DIR")
    if env_dir:
        dirs.append(env_dir)
    reg_dir = _sys_dir_from_registry()
    if reg_dir:
        dirs.append(reg_dir)
    dirs.append(DEFAULT_SYS_DIR)
    for d in dirs:
        if os.path.isfile(os.path.join(d, DLL_NAME)):
            return d
    return dirs[-1]  # aucun existant : fallback (message d'erreur clair a l'appelant)


def resolve_dll_path(explicit_dll=None, explicit_sys_dir=None):
    """Chemin complet de DhxIsam64.dll. --dll-path est honore strictement."""
    if explicit_dll:
        return explicit_dll
    return os.path.join(resolve_sys_dir(explicit_sys_dir), DLL_NAME)


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

def load_dll(dll_path):
    """Charge DhxIsam64.dll et configure les signatures ctypes."""
    if not os.path.isfile(dll_path):
        print(f"DLL introuvable : {dll_path}", file=sys.stderr)
        return None

    dll = ctypes.WinDLL(dll_path)

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
# Garde-fou structure <-> dictionnaire (anti-corruption taille d'enregistrement)
#
# Un .dhfi peut contenir PLUSIEURS tables, chacune avec sa propre taille
# d'enregistrement (ex. base A5f : M1=50, M4=1000, M7=508). Ecrire un buffer
# dont la taille ne correspond a AUCUNE table reelle du fichier corrompt le
# fichier en silence. Ce garde-fou verifie que la structure declaree
# (Dictionnaire/Base/Table/TailleEnreg/Ce) correspond a une table reelle du
# dictionnaire avant toute ecriture. Source de verite = la structure JSON
# elle-meme (elle declare son dico/base/table) ; pas besoin de l'en-tete .dhfi
# (dont le format n'est pas universel -- ex. gtfdmc.dhfi ne porte pas ce lien).
#
# Parseur .dhsd VENDORE (copie locale, aucune dependance cross-skill).
# ---------------------------------------------------------------------------

def _parse_dhsd_lines(path):
    """Lit un .dhsd (ISO-8859-1 + CRLF) et retourne ses lignes strippees."""
    with open(path, "rb") as f:
        raw = f.read().decode("iso-8859-1", "replace")
    sep = "\r\n" if "\r\n" in raw else "\n"
    return [x.strip() for x in raw.split(sep)]


def _base_tables(lines, base):
    """Retourne la liste des tables du bloc [BASE] Nom=<base> via sa sous-section [TABLES].

    Retourne None si la base est absente du dictionnaire.
    """
    i = 0
    while i < len(lines):
        if lines[i] == "[BASE]":
            j = i + 1
            nom = None
            in_tables = False
            tables = []
            while j < len(lines) and lines[j] != "[BASE]":
                s = lines[j]
                if s.startswith("Nom=") and nom is None and not in_tables:
                    nom = s[4:].split(",")[0]
                elif s == "[TABLES]":
                    in_tables = True
                elif s == "[/TABLES]":
                    in_tables = False
                elif in_tables and s.startswith("Nom="):
                    tables.append(s[4:].split(",")[0])
                j += 1
            if nom and nom.lower() == base.lower():
                return tables
            i = j
            continue
        i += 1
    return None


def _table_size_ce(lines, table):
    """Retourne (ce, taille) en str du bloc [TABLE] Nom=<table>, ou None.

    `ce` peut etre None (tables mono-table sans discriminant, ex. XErr/206, XQ).
    """
    k = 0
    while k < len(lines):
        if lines[k] == "[TABLE]":
            m = k + 1
            nom = ce = taille = None
            while m < len(lines) and lines[m] != "[TABLE]":
                s = lines[m]
                if s.startswith("Nom=") and nom is None:
                    nom = s[4:].split(",")[0]
                elif s.startswith("CE="):
                    rest = s[3:]
                    ce = rest.split(",")[1] if "," in rest else None
                elif s.startswith("Taille="):
                    taille = s[7:].split(",")[0]
                m += 1
            if nom and nom.lower() == table.lower():
                return ce, taille
            k = m
            continue
        k += 1
    return None


def _locate_dico(dico_name, search_dirs):
    """Cherche le fichier dico .dhsd dans les repertoires donnes (ordre prioritaire)."""
    if not dico_name or not dico_name.lower().endswith(".dhsd"):
        return None
    for d in search_dirs:
        if not d:
            continue
        candidate = os.path.join(d, dico_name)
        if os.path.isfile(candidate):
            return candidate
    return None


def verify_structure_vs_dico(structure, fichier, dico_paths):
    """Verifie la coherence (Base, Table, TailleEnreg, Ce) de la structure vs le dictionnaire reel.

    Retourne (verdict, message) avec verdict dans {"ok", "warn", "refuse"} :
      - "refuse" : incoherence prouvee (table absente, taille != taille reelle, Ce != Ce reel)
                   -> l'ecriture DOIT etre bloquee (corruption evitee).
      - "warn"   : verification impossible (metadata manquante, dico introuvable/base absente)
                   -> degradation gracieuse, l'ecriture est autorisee mais signalee.
      - "ok"     : structure coherente avec une table reelle du fichier.

    Le CE n'est verifie que s'il est present des deux cotes (tables mono-table sans CE).
    """
    dico_name = structure.get("Dictionnaire")
    base = structure.get("Base")
    table = structure.get("Table")
    ce = structure.get("Ce")
    size = structure.get("TailleEnreg")

    if not dico_name or not base or not table:
        return "warn", "structure sans Dictionnaire/Base/Table : verification dico impossible"

    search = list(dico_paths or [])
    if fichier:
        search.append(os.path.dirname(os.path.abspath(fichier)))
    dico_file = _locate_dico(dico_name, search)
    if not dico_file:
        dirs = [d for d in search if d]
        return "warn", f"dictionnaire {dico_name!r} introuvable (cherche : {dirs}) : structure non verifiee (--dico-path pour preciser)"

    lines = _parse_dhsd_lines(dico_file)
    tables = _base_tables(lines, base)
    if tables is None:
        return "warn", f"base {base!r} absente de {dico_name} : structure non verifiee"
    if not any(t.lower() == table.lower() for t in tables):
        return "refuse", f"table {table!r} absente de la base {base!r} (tables reelles : {tables}) -- structure incompatible avec le fichier"

    det = _table_size_ce(lines, table)
    if not det or det[1] is None:
        return "warn", f"taille reelle de {base}.{table} introuvable dans {dico_name} : structure non verifiee"
    real_ce, real_ta = det
    if str(size) != str(real_ta):
        return "refuse", f"TailleEnreg={size} != taille reelle {real_ta} de {base}.{table} -- ecriture refusee (corruption evitee)"
    if ce is not None and real_ce is not None and str(ce) != str(real_ce):
        return "refuse", f"Ce={ce} != Ce reel {real_ce} de {base}.{table} -- structure incoherente avec le dictionnaire"
    return "ok", f"{base}.{table} Taille={real_ta} Ce={real_ce} : coherent"


def _guardrail_or_none(structure, fichier, dico_paths, skip_dict_check):
    """Applique le garde-fou dico. Retourne un dict-resultat d'erreur si REFUS, sinon None.

    Emet un warning stderr en cas de "warn" (degradation gracieuse) ; ne bloque jamais sur warn.
    """
    if skip_dict_check:
        return None
    verdict, msg = verify_structure_vs_dico(structure, fichier, dico_paths)
    if verdict == "refuse":
        return {"written": False, "skipped": False, "error_code": -2,
                "message": f"Garde-fou dico : {msg}"}
    if verdict == "warn":
        print(f"  Warning garde-fou dico : {msg}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Construction d'enregistrement
# ---------------------------------------------------------------------------

def encoder_champ(valeur, field):
    """Encode une valeur a la representation binaire EXACTE du champ.

    **Source unique du cadrage.** Trois endroits ont besoin de cette representation :
    le contenu de l'enregistrement (`build_record`), la valeur de cle de
    positionnement (`build_tdf_key`) et la verification post-lecture
    (`record_matches_key_fields`). Ils divergeaient : seul `build_record` lisait
    `Justify`, si bien qu'un champ numerique cadre a DROITE (`"     131"`) partait
    dans la cle cadre a GAUCHE (`"131     "`) -- une cle totalement differente en tri
    octet par octet, qui positionnait sur un enregistrement voisin (#334).

    Deux types :
      - `"B"` (binaire) : la valeur fournie est de l'**hexadecimal** (symetrique de
        la lecture, qui rend `raw.hex().upper()` -- cf. reading-isam-files). Seul
        moyen d'exprimer un octet arbitraire : le pipeline texte passe par cp1252,
        qui n'est pas bijectif sur 0x80-0x9F (#290).
      - tout le reste : texte cp1252, cadre selon `Justify` (`right` = padding
        espaces a gauche, defaut `left`).

    Returns:
        bytes de longueur EXACTEMENT field["Taille"].

    Raises:
        ValueError: hexadecimal invalide ou de longueur incompatible -- on refuse
            plutot que de tronquer en silence, une troncature muette produisant une
            valeur binaire plausible mais fausse.
    """
    taille = field["Taille"]
    nom = field.get("Nom", "?")

    if field.get("Type") == "B":
        brut = str(valeur).strip().replace(" ", "")
        try:
            octets = bytes.fromhex(brut)
        except ValueError:
            raise ValueError(
                f"Champ binaire '{nom}' : '{valeur}' n'est pas de l'hexadecimal valide. "
                f"Attendu {taille * 2} caracteres hex (ex: '01D9EF910F1F5C9D').")
        if len(octets) != taille:
            raise ValueError(
                f"Champ binaire '{nom}' : {len(octets)} octet(s) fournis pour un champ "
                f"de {taille}. Attendu exactement {taille * 2} caracteres hex -- refuse "
                f"plutot que tronque.")
        return octets

    val_str = str(valeur)
    justify = field.get("Justify", "left")
    if justify == "right":
        # Idempotent : accepte "131" comme "      131", meme resultat.
        val_str = val_str.strip()
    val_bytes = val_str.encode(ENCODING)
    if justify == "right":
        if len(val_bytes) > taille:
            val_bytes = val_bytes[-taille:]          # troncature cote gauche
        return b" " * (taille - len(val_bytes)) + val_bytes
    return val_bytes[:taille].ljust(taille, b" ")


def valeur_canonique(octets, field):
    """Forme comparable d'une valeur, insensible au cadrage.

    Sert a comparer ce qu'on a LU dans le fichier avec ce qu'on ATTEND, sans que le
    cadrage n'entre en jeu : `b"     131"` et `b"131     "` donnent tous deux `b"131"`.
    La version precedente ne faisait qu'un `rstrip`, ce qui laissait les espaces de
    TETE d'un champ cadre a droite -- la comparaison echouait donc systematiquement
    sur ces champs, avec le meme symptome que #334 mais une cause distincte.
    """
    if field.get("Type") == "B":
        return octets.hex().upper()
    return octets.strip(b" \x00")


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
        try:
            val_bytes = encoder_champ(valeur, field)
        except UnicodeEncodeError:
            warnings.append(f"Champ {nom} : valeur non encodable en {ENCODING}")
            continue
        except ValueError as e:
            warnings.append(str(e))
            continue

        for j in range(len(val_bytes)):
            rec[offset + j] = val_bytes[j]

    # Champs binaires NON fournis : le buffer les laisse a 0x20 (espaces), ce qui
    # n'est jamais une valeur binaire legitime. On ne devine PAS de valeur -- la
    # mesure montre que le standard lui-meme livre des champs binaires a espaces
    # (cf. reference/champs-binaires.md) -- mais on ne se tait pas non plus.
    for nom, field in field_map.items():
        if field.get("Type") == "B" and nom not in donnees:
            warnings.append(
                f"Champ binaire '{nom}' non fourni : reste rempli d'espaces (0x20), "
                f"ce qui n'est pas une valeur binaire legitime. Fournir sa valeur en "
                f"hexadecimal ({field['Taille'] * 2} caracteres) si l'outil qui relira "
                f"cet enregistrement en depend.")

    return rec, warnings


# ---------------------------------------------------------------------------
# Ecriture ISAM
# ---------------------------------------------------------------------------

# Fichiers deja sauvegardes dans CETTE execution : un seul .bak par fichier, meme
# pour un batch de 200 enregistrements (sinon le 2e enregistrement ecraserait la
# sauvegarde par un etat deja modifie -- le filet ne servirait plus a rien).
_DEJA_SAUVEGARDES = set()


# Fichiers standard qui possedent un OVERLAY de surcharge `<nom>u.dhfi` (#228).
# Liste volontairement COURTE et explicite : ne pas deduire l'existence d'un overlay
# du seul nom d'un fichier. Les deux mecanismes connus et confirmes :
#   a5f  -> a5fu  (zooms, visibilite F7)   -- confirme par mesure et par #250
#   g3f  -> g3fu  (choix de menu)          -- confirme par le distributeur
# Pour les AUTRES fichiers standard il n'y a PAS d'overlay : le partenaire gere son
# PROPRE fichier (ex. un XXfdmc de multichoix). Ce sont deux regles differentes, et les
# confondre produirait un mauvais conseil.
FICHIERS_AVEC_OVERLAY = {"a5f": "a5fu", "g3f": "g3fu"}


def avertissement_overlay(fichier_dhfi):
    """Message si la cible est un fichier standard qui possede un overlay, sinon None."""
    base = os.path.splitext(os.path.basename(fichier_dhfi))[0].lower()
    overlay = FICHIERS_AVEC_OVERLAY.get(base)
    if not overlay:
        return None
    return (
        "CIBLE STANDARD : '%s.dhfi' est le fichier livre par Divalto. Une ecriture custom "
        "doit viser son overlay '%s.dhfi' dans l'arborescence SPECIFIQUE -- une entree "
        "dans l'overlay est prioritaire sur celle du standard, et le standard n'est jamais "
        "modifie. Ecrire ici expose la modification a etre ECRASEE a la prochaine montee "
        "de version ou au prochain patch ERP. Si l'ecriture dans le standard est "
        "intentionnelle, ignorer cet avertissement." % (base, overlay))


def sauvegarder_isam(fichier_dhfi):
    """Copie de securite avant ecriture. Retourne la liste des `.bak` crees.

    **Les DEUX fichiers de la paire.** Un ISAM Divalto est un couple : `.dhfi`
    (donnees) et `.dhfd` (index). Sauvegarder le seul `.dhfi` ne permet PAS de
    revenir en arriere -- le skill de LECTURE le documente deja (« toute copie ou
    backup doit embarquer les deux fichiers »), l'ecriture l'ignorait. Le RETEX
    #290 ne demandait que le `.dhfi` : sa suggestion etait incomplete.

    Convention alignee sur `writing-diva-files/scripts/patch_file.py` : un seul
    `.bak` par fichier, **glissant** (chaque execution ecrase le precedent).
    """
    import shutil
    cle = os.path.abspath(fichier_dhfi).lower()
    if cle in _DEJA_SAUVEGARDES:
        return []
    crees = []
    base, _ext = os.path.splitext(fichier_dhfi)
    for chemin in (fichier_dhfi, base + ".dhfd"):
        if os.path.isfile(chemin):
            cible = chemin + ".bak"
            shutil.copy2(chemin, cible)
            crees.append(cible)
    _DEJA_SAUVEGARDES.add(cle)
    return crees


def make_tdf(fichier_path):
    """Cree un buffer TDF avec le chemin du fichier."""
    tdf = (ctypes.c_ubyte * TDF_SIZE)()
    name_bytes = fichier_path.encode(ENCODING)
    copy_len = min(len(name_bytes), 256)
    for i in range(copy_len):
        tdf[TDF_NAME_OFFSET + i] = name_bytes[i]
    return tdf


# Message d'echec du positionnement. Il DOIT nommer la cause la plus probable :
# une cle declaree qui n'est pas la cle physique de l'index. Le message precedent
# ("match approximatif refuse") envoyait chercher du cote de l'enregistrement, alors
# que le probleme est dans la declaration -- cas reel : un `Ce` en tete des champs de
# cle rendait le positionnement inefficace (#291).
MSG_CLE_REFUSEE = (
    "Enreg cible introuvable : le positionnement a atterri sur un AUTRE enregistrement, "
    "l'operation est refusee (aucune ecriture). Cause la plus frequente : la cle declaree "
    "dans le bloc Keys de la structure n'est pas la cle PHYSIQUE de l'index -- typiquement "
    "un champ CE inclus a tort (86 % des index du standard n'en ont aucun dans leur cle). "
    "Verifier avec : validate_structure.py --path <structure> --probe-key <index> "
    "--file <copie.dhfi>"
)


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
        lu = bytes(record_buf[offset:offset + size])
        try:
            attendu = encoder_champ(donnees.get(field_name, ""), field)
        except ValueError:
            return False
        # Comparaison sur la forme CANONIQUE : insensible au cadrage des deux cotes.
        if valeur_canonique(lu, field) != valeur_canonique(attendu, field):
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
        # Meme cadrage que dans l'enregistrement (#334) : un `ljust`
        # inconditionnel envoyait un champ `Justify=right` cadre a gauche.
        val_bytes = encoder_champ(donnees.get(field_name, ""), field)
        for j in range(len(val_bytes)):
            tdf[value_offset + j] = val_bytes[j]
        value_offset += field["Taille"]


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


def update_single(dll, tache, entry, structure_dir, dry_run, dico_paths=None, skip_dict_check=False):
    """Modifie un enregistrement existant.

    Sequence : open -> tpreadlong R (reserve) -> verification exacte -> trewritelong -> close.
    Revision 2026-04-22 : unifie avec delete_single sur tpreadlong mode R.
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

    # Garde-fou anti-corruption : la taille declaree doit correspondre a une table reelle du fichier
    refus = _guardrail_or_none(structure, fichier, dico_paths, skip_dict_check)
    if refus is not None:
        return refus

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
    # Revision 2026-04-22 : remplace l'usage historique de treadlong mode G
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
                "message": MSG_CLE_REFUSEE}

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


def delete_single(dll, tache, entry, structure_dir, dry_run, dico_paths=None, skip_dict_check=False):
    """Supprime un enregistrement existant.

    Sequence : open -> tpreadlong R (reserve) -> verification exacte -> tdeletelong -> close.
    Revision 2026-04-22 : unifie avec update_single sur tpreadlong mode R.
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

    # Garde-fou anti-corruption : la taille declaree doit correspondre a une table reelle du fichier
    refus = _guardrail_or_none(structure, fichier, dico_paths, skip_dict_check)
    if refus is not None:
        return refus

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
    # Revision 2026-04-22 : remplace l'usage historique de tpreadlong mode F
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
                "message": MSG_CLE_REFUSEE}

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


def write_single(dll, tache, entry, structure_dir, dry_run, dico_paths=None, skip_dict_check=False):
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

    # Garde-fou anti-corruption : la taille declaree doit correspondre a une table reelle du fichier
    refus = _guardrail_or_none(structure, fichier, dico_paths, skip_dict_check)
    if refus is not None:
        return refus

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
    parser.add_argument(
        "--dico-path", action="append", default=None, metavar="DIR",
        help="Repertoire ou chercher le dictionnaire .dhsd declare par la structure "
             "(cumulable). Defaut : repertoire du fichier .dhfi cible. Utile quand le dico "
             "est deporte (ex. fichiers d'erreur dans objets/, dico dans fichiers/)."
    )
    parser.add_argument(
        "--no-backup", action="store_true",
        help="Ne PAS creer de copie .bak avant ecriture. Par defaut le script sauvegarde "
             "les DEUX fichiers de la paire ISAM (.dhfi ET .dhfd) avant la premiere "
             "ecriture -- un .dhfi seul ne permet pas de revenir en arriere. Un seul .bak "
             "par fichier et par execution, glissant."
    )
    parser.add_argument(
        "--skip-dict-check", action="store_true",
        help="Desactive le garde-fou structure<->dictionnaire (verification de la taille "
             "d'enregistrement). A n'utiliser qu'en connaissance de cause."
    )
    parser.add_argument("--dll-path", default=None,
                        help="Chemin explicite de DhxIsam64.dll (sinon : --sys-dir, env DIVALTO_SYS_DIR, registre Divalto, puis C:\\divalto\\sys)")
    parser.add_argument("--sys-dir", default=None,
                        help="Repertoire sys/ de Divalto contenant DhxIsam64.dll (override du registre)")
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
    avertissements = []
    written = 0
    skipped = 0
    errors = []

    # Charger la DLL (sauf dry-run)
    dll = None
    task_id = TASK_ID
    if not args.dry_run:
        dll = load_dll(resolve_dll_path(args.dll_path, args.sys_dir))
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

    backups = []
    overlay_avertis = set()
    try:
        for i, entry in enumerate(entries):
            # Cible standard alors qu'un overlay existe : le dire AVANT d'ecrire, et
            # une seule fois par fichier (un lot de 200 entrees ne doit pas produire
            # 200 fois le meme avertissement). Emis aussi en --dry-run : c'est
            # precisement le moment ou l'on veut l'entendre.
            msg_overlay = avertissement_overlay(entry["Fichier"])
            if msg_overlay and entry["Fichier"] not in overlay_avertis:
                overlay_avertis.add(entry["Fichier"])
                avertissements.append({"file": entry["Fichier"], "message": msg_overlay})
                print("  AVERTISSEMENT: %s" % msg_overlay, file=sys.stderr)

            # Filet de securite AVANT toute ecriture reelle : une fois l'ecriture
            # faite dans un .dhfi il n'existe aucun retour arriere integre.
            if not args.dry_run and not args.no_backup:
                try:
                    backups.extend(sauvegarder_isam(entry["Fichier"]))
                except OSError as e:
                    errors.append({"index": i, "file": entry["Fichier"],
                                   "error_code": -1,
                                   "message": f"Sauvegarde impossible, ecriture annulee : {e}"})
                    continue

            result = op_fn(dll, task_id, entry, structure_dir, args.dry_run,
                           args.dico_path, args.skip_dict_check)

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
        "backups": backups,
        "avertissements": avertissements,
        "errors": errors,
    }

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    print()

    if not success and errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
