#!/usr/bin/env python3
"""Lit le dictionnaire des multichoix Divalto (gtfdmc.dhfi) via DhxIsam64.dll.

Usage :
    py read_multichoix.py --file "<path>\\gtfdmc.dhfi" --list
    py read_multichoix.py --file "<path>\\gtfdmc.dhfi" --detail NONOUI
    py read_multichoix.py --file "<path>\\gtfdmc.dhfi" --all-details
    py read_multichoix.py --file "<path>\\gtfdmc.dhfi" --stats
    py read_multichoix.py --file "<path>\\gtfdmc.dhfi" --resolve AXENO   # [MC-03, pas encore implemente]

Les 3 Types geres :
    - Type 1 (liste fixe)        : `choix` 104 bytes texte + `valeur` code retourne
    - Type 3 (lookup dynamique)  : sous-champs enreg/donnee/prefixe/ideb/ifin
    - Type 4 (identifiant externe) : `valeur` contient un IdXxx

Exit codes : 0 = succes avec resultat, 1 = resultat vide, 2 = erreur.
"""

import argparse
import ctypes
import json
import os
import sys
from collections import OrderedDict, Counter

DLL_PATH = r"C:\divalto\sys\DhxIsam64.dll"
ENCODING = "windows-1252"
RECORD_SIZE = 420

# Offsets dans la vue ch60 de rnfdd.dhsd (cf structure_gtfdmc_ch60.json)
OFF_CE = 0
OFF_NC = 1            # 16 bytes
OFF_TYPE = 17         # 1 byte
OFF_CHOIX = 18        # 104 bytes (texte Type=1 OU sous-structure Type=3)
OFF_ENREG = 18        # 32 bytes (Type=3)
OFF_DONNEE = 50       # 32 bytes (Type=3)
OFF_PREFIXE = 82      # 32 bytes (Type=3)
OFF_IDEB = 114        # 4 bytes numeric (Type=3)
OFF_IFIN = 118        # 4 bytes numeric (Type=3)
OFF_MODBITMAP = 122   # 1 byte
OFF_DATEMC = 123      # 8 bytes binaire
OFF_VALEUR = 131      # 80 bytes
OFF_NOMS = 211        # 80 bytes


def load_dll():
    """Charge DhxIsam64.dll et configure les signatures ctypes."""
    try:
        dll = ctypes.WinDLL(DLL_PATH)
    except OSError:
        return None
    dll.xisam_begin.argtypes = [ctypes.c_ushort]
    dll.xisam_begin.restype = ctypes.c_short
    dll.xisam_end.argtypes = [ctypes.c_ushort]
    dll.xisam_end.restype = ctypes.c_ushort
    dll.xisam_topenlong.argtypes = [ctypes.c_ushort, ctypes.POINTER(ctypes.c_byte), ctypes.c_char_p]
    dll.xisam_topenlong.restype = ctypes.c_ushort
    dll.xisam_tcloselong.argtypes = [ctypes.c_ushort, ctypes.POINTER(ctypes.c_byte)]
    dll.xisam_tcloselong.restype = ctypes.c_ushort
    dll.xisam_treadlong.argtypes = [
        ctypes.c_ushort, ctypes.POINTER(ctypes.c_byte),
        ctypes.POINTER(ctypes.c_byte), ctypes.c_ushort, ctypes.c_char_p,
    ]
    dll.xisam_treadlong.restype = ctypes.c_ushort
    return dll


def read_all_records(dll, file_path):
    """Parcours complet de gtfdmc.dhfi, retourne un OrderedDict {nc: [raw_bytes...]}.

    Filtre les enregistrements dont Ce n'est pas '1' ou '2' (header a skipper).
    """
    # Acquerir un slot (2..16)
    acquired = None
    for candidate in range(15, 1, -1):
        if dll.xisam_begin(ctypes.c_ushort(candidate)) == candidate:
            acquired = candidate
            break
    if acquired is None:
        return None, "xisam_begin : aucun slot libre"
    tache = ctypes.c_ushort(acquired)

    # TDF + open
    tdf = (ctypes.c_byte * 1024)(*([0x20] * 1024))
    path_bytes = file_path.encode(ENCODING)
    for i, b in enumerate(path_bytes[:256]):
        tdf[4 + i] = b

    ret = dll.xisam_topenlong(tache, tdf, b"P")
    if ret != 0:
        dll.xisam_end(tache)
        return None, f"xisam_topenlong : code {ret}"

    # Positionner sur la cle A (pad espaces sur 256 octets)
    for i in range(256):
        tdf[261 + i] = 0x20
    tdf[261] = ord("A")

    rec = (ctypes.c_byte * RECORD_SIZE)()
    by_nc = OrderedDict()

    while True:
        ret = dll.xisam_treadlong(tache, tdf, rec, ctypes.c_ushort(RECORD_SIZE), b"P")
        if ret != 0:
            break
        raw = bytes(bytearray((b & 0xFF) for b in rec[:RECORD_SIZE]))
        if raw[OFF_CE] not in (ord("1"), ord("2")):
            continue
        nc = raw[OFF_NC:OFF_NC + 16].decode(ENCODING, errors="replace").rstrip()
        by_nc.setdefault(nc, []).append(raw)

    dll.xisam_tcloselong(tache, tdf)
    dll.xisam_end(tache)
    return by_nc, None


def text(raw, offset, size):
    """Decode une tranche de bytes en texte cp1252 rstrip-e."""
    return raw[offset:offset + size].decode(ENCODING, errors="replace").rstrip()


def dominant_type(records):
    """Retourne le Type dominant (premier non-vide) des entrees d'un Nc."""
    types = [chr(r[OFF_TYPE]) for r in records if r[OFF_TYPE] >= 32]
    non_space = [t for t in types if t != " "]
    return (non_space[0] if non_space else (types[0] if types else "")).strip()


def decode_entry(raw, mc_type):
    """Decode un enregistrement selon le Type dominant du multichoix."""
    ce = text(raw, OFF_CE, 1)
    if mc_type == "3":
        return {
            "ce": ce,
            "enreg": text(raw, OFF_ENREG, 32),
            "donnee": text(raw, OFF_DONNEE, 32),
            "prefixe": text(raw, OFF_PREFIXE, 32),
            "ideb": text(raw, OFF_IDEB, 4),
            "ifin": text(raw, OFF_IFIN, 4),
        }
    # Type 1 ou 4 : `choix` est un texte libre 104 octets + `valeur` code retourne
    return {
        "ce": ce,
        "choix": text(raw, OFF_CHOIX, 104),
        "valeur": text(raw, OFF_VALEUR, 80),
    }


def cmd_list(by_nc):
    """Mode --list : dump la liste des Nc avec leur Type et nb entrees."""
    items = []
    total_records = 0
    for nc, records in by_nc.items():
        items.append({
            "nc": nc,
            "type": dominant_type(records),
            "entries": len(records),
        })
        total_records += len(records)
    return {
        "total_nc": len(items),
        "total_records": total_records,
        "multichoix": items,
    }


def cmd_stats(by_nc):
    """Mode --stats : distribution des Types rencontres."""
    total = len(by_nc)
    counter = Counter(dominant_type(records) for records in by_nc.values())
    by_type = {
        t: {"count": c, "pct": round(c * 100.0 / total, 1) if total else 0.0}
        for t, c in sorted(counter.items())
    }
    return {"total_nc": total, "by_type": by_type}


def _build_detail(nc, records):
    """Construit la structure detail d'un multichoix (factorise pour --detail et --all-details)."""
    mc_type = dominant_type(records)
    result = {
        "nc": nc,
        "type": mc_type,
        "entries": [decode_entry(r, mc_type) for r in records],
    }
    if mc_type == "3" and records:
        first = records[0]
        ideb_str = text(first, OFF_IDEB, 4)
        ifin_str = text(first, OFF_IFIN, 4)
        result["lookup"] = {
            "enreg": text(first, OFF_ENREG, 32),
            "donnee": text(first, OFF_DONNEE, 32),
            "prefixe": text(first, OFF_PREFIXE, 32),
            "ideb": int(ideb_str) if ideb_str.isdigit() else ideb_str,
            "ifin": int(ifin_str) if ifin_str.isdigit() else ifin_str,
        }
    return result


def cmd_detail(by_nc, nc_target):
    """Mode --detail <NC> : dump les entrees d'un Nc precis."""
    if nc_target not in by_nc:
        return {"nc": nc_target, "found": False}
    result = _build_detail(nc_target, by_nc[nc_target])
    result["found"] = True
    return result


def cmd_all_details(by_nc):
    """Mode --all-details : dump le detail complet de tous les multichoix en une passe.

    Format : {"total_nc": N, "multichoix": {<nc>: {type, entries, lookup?}}}.
    Destine aux consommateurs machine (ex: pipeline documenting-erp) qui
    n'appelleraient sinon que --detail une fois par Nc.
    """
    result = {}
    for nc, records in by_nc.items():
        result[nc] = _build_detail(nc, records)
    return {"total_nc": len(result), "multichoix": result}


def main():
    parser = argparse.ArgumentParser(description="Lit le dictionnaire multichoix Divalto")
    parser.add_argument("--file", required=True, help="Chemin complet du fichier gtfdmc.dhfi")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="Liste tous les multichoix")
    group.add_argument("--stats", action="store_true", help="Distribution des Types")
    group.add_argument("--detail", metavar="NC", help="Detaille un multichoix par son nom")
    group.add_argument("--all-details", dest="all_details", action="store_true",
                       help="Dump le detail complet de tous les multichoix (consommation machine)")
    group.add_argument("--resolve", metavar="NC", help="[MC-03 pas encore implemente] Resout un Type=3 en lisant la table cible")
    args = parser.parse_args()

    dll = load_dll()
    if dll is None:
        print(f"Erreur : DLL introuvable : {DLL_PATH}", file=sys.stderr)
        sys.exit(2)

    if not os.path.isfile(args.file):
        print(f"Erreur : fichier introuvable : {args.file}", file=sys.stderr)
        sys.exit(2)

    by_nc, err = read_all_records(dll, args.file)
    if err:
        print(f"Erreur : {err}", file=sys.stderr)
        sys.exit(2)

    if args.list:
        payload = cmd_list(by_nc)
        success = payload["total_nc"] > 0
    elif args.stats:
        payload = cmd_stats(by_nc)
        success = payload["total_nc"] > 0
    elif args.detail:
        payload = cmd_detail(by_nc, args.detail)
        success = payload.get("found", False)
    elif args.all_details:
        payload = cmd_all_details(by_nc)
        success = payload["total_nc"] > 0
    elif args.resolve:
        payload = {
            "nc": args.resolve,
            "resolved": False,
            "error": "Mode --resolve pas encore implemente (BACKLOG MC-03). "
                     "Utiliser --detail pour obtenir l'enreg/donnee/prefixe/ideb/ifin "
                     "puis lire la table cible avec reading-isam-files.",
        }
        success = False
    else:
        parser.error("Aucun mode selectionne")
        return

    result = {"success": success, "file": args.file, **payload}
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
