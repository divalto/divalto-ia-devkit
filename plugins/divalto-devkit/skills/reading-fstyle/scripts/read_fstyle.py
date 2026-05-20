#!/usr/bin/env python3
"""Lit les feuilles de style Divalto (fstyle*.dhfi) via DhxIsam64.dll.

Usage :
    py read_fstyle.py --variant wpf --list
    py read_fstyle.py --variant wpf --detail TBLART
    py read_fstyle.py --variant legacy --stats
    py read_fstyle.py --variant wpf --all-details
    py read_fstyle.py --resolve TBLART
    py read_fstyle.py --file "C:/chemin/custom/fstyle.dhfi" --list

Les 7 Types geres :
    - Type 1 Police        : taille + poids Windows (400000/700000) + famille
    - Type 2 Couleur RGB   : R G B A packes (3 chars par canal)
    - Type 3 Reference i18n : <NOM> #<cle> <flags>  (cle fondamentale pour les tbl*)
    - Type 5 Style global  : STD regroupe styles contextuels (1 record unique)
    - Type 6 Cadre         : 6 cadres canoniques (SANS, SIMPLE, RELIEF_*, CADRE_*)
    - Type 7 Style compose : assemblage police + cadre + couleur
    - Type 9 Contexte      : scopes .BOUTON/.MENU/.TOOLBAR et entrees associees

Exit codes : 0 = succes, 1 = resultat vide ou orphelin, 2 = erreur.
"""

import argparse
import ctypes
import json
import os
import sys
from collections import OrderedDict, Counter

DLL_PATH = r"C:\divalto\sys\DhxIsam64.dll"
ENCODING = "windows-1252"
RECORD_SIZE = 1024

# Layout observe empiriquement (byte 0 = Type, byte 2+ = Nom sur 32 chars,
# puis champs de 32 chars selon Type).
OFF_TYPE = 0
OFF_NOM = 2
NOM_LEN = 32
FIELD_LEN = 32

# Variantes connues sous C:\divalto\sys\
VARIANTS = {
    "wpf":    r"C:\divalto\sys\fstylewpf.dhfi",
    "legacy": r"C:\divalto\sys\fstyle.dhfi",
    "imp":    r"C:\divalto\sys\fstyleimp.dhfi",
    "web":    r"C:\divalto\sys\fstyleweb.dhfi",
}

# Ordre de resolution par defaut (wpf d'abord car le plus riche en TBL*)
DEFAULT_RESOLVE_ORDER = ["wpf", "legacy", "imp"]


def load_dll():
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
    """Parcours complet du fichier, retourne un OrderedDict {nom_upper: raw_bytes}.

    Filtre les records magic `*$version` (Type = '*'). Les doublons de nom
    sont geres par premier-gagne (l'index A de fstyle est en principe unique).
    """
    acquired = None
    for candidate in range(15, 1, -1):
        if dll.xisam_begin(ctypes.c_ushort(candidate)) == candidate:
            acquired = candidate
            break
    if acquired is None:
        return None, "xisam_begin : aucun slot libre"
    tache = ctypes.c_ushort(acquired)

    tdf = (ctypes.c_byte * 1024)(*([0x20] * 1024))
    path_bytes = file_path.encode(ENCODING)
    for i, b in enumerate(path_bytes[:256]):
        tdf[4 + i] = b

    ret = dll.xisam_topenlong(tache, tdf, b"P")
    if ret != 0:
        dll.xisam_end(tache)
        return None, f"xisam_topenlong : code {ret}"

    for i in range(256):
        tdf[261 + i] = 0x20
    tdf[261] = ord("A")

    rec = (ctypes.c_byte * RECORD_SIZE)()
    by_nom = OrderedDict()

    while True:
        ret = dll.xisam_treadlong(tache, tdf, rec, ctypes.c_ushort(RECORD_SIZE), b"P")
        if ret != 0:
            break
        raw = bytes(bytearray((b & 0xFF) for b in rec[:RECORD_SIZE]))
        if raw[OFF_TYPE] == ord("*"):
            continue  # magic header *$version
        nom = raw[OFF_NOM:OFF_NOM + NOM_LEN].decode(ENCODING, errors="replace").rstrip()
        if not nom:
            continue
        by_nom.setdefault(nom.upper(), raw)

    dll.xisam_tcloselong(tache, tdf)
    dll.xisam_end(tache)
    return by_nom, None


def text(raw, offset, size):
    return raw[offset:offset + size].decode(ENCODING, errors="replace").rstrip()


def tokens_after_nom(raw):
    """Tokens apres le nom, nettoyes des nulls et espaces."""
    tail = raw[OFF_NOM + NOM_LEN:].decode(ENCODING, errors="replace").replace("\x00", " ")
    return tail.split()


def _decode_type1(raw):
    """Police : <taille> 0 0 0 <poids> ... <famille>."""
    t = tokens_after_nom(raw)
    d = {}
    if t:
        d["taille"] = t[0]
    if len(t) >= 5:
        d["poids"] = t[4]
    # Famille : dernier token non numerique long (les tokens numeriques sont flags).
    # Empirique : famille peut etre prefixee par un code numerique court (ex: "34Tahoma")
    # -> on prend le dernier token contenant au moins un caractere alphabetique.
    alpha_tokens = [tok for tok in t if any(c.isalpha() for c in tok)]
    if alpha_tokens:
        fam = alpha_tokens[-1]
        # Strip prefixe numerique eventuel
        while fam and fam[0].isdigit():
            fam = fam[1:]
        d["famille"] = fam
    return d


def _decode_type2(raw):
    """Couleur RGBA : concatenation de 4 valeurs sur 3 chars chacune."""
    t = tokens_after_nom(raw)
    d = {}
    if t:
        packed = t[0]
        # Reconstituer R/G/B/A : 3 chars chacun, padding espaces dans les valeurs brutes.
        # Empirique : le token peut mesurer 9 a 12 chars. On decoupe par la fin.
        # Ex: '255  0  00' -> [255, 0, 0, 0]
        if len(packed) in (9, 10):
            try:
                # Decoupage 3+3+3+reste
                r = int(packed[0:3].strip())
                g = int(packed[3:6].strip())
                b = int(packed[6:9].strip())
                d["r"] = r
                d["g"] = g
                d["b"] = b
                if len(packed) > 9:
                    rest = packed[9:].strip()
                    if rest.isdigit():
                        d["a"] = int(rest)
                d["rgb_brut"] = packed
            except ValueError:
                d["rgb_brut"] = packed
        else:
            d["rgb_brut"] = packed
    return d


def _decode_type3(raw):
    """Reference i18n : <#cle> [<flags>] [<couleur>]."""
    t = tokens_after_nom(raw)
    d = {}
    if t:
        # 1er token = cle i18n (typiquement #xxx) ou flags
        if t[0].startswith("#"):
            d["cle_i18n"] = t[0]
            if len(t) > 1:
                d["flags"] = t[1]
            if len(t) > 2:
                d["couleur"] = t[2]
        else:
            # Rare : pas de cle #, c'est un flag direct
            d["flags"] = t[0]
    return d


def _decode_type5(raw):
    """Style global STD : tokens = refs successives (saisie, aff, bloc, tableau...)."""
    t = tokens_after_nom(raw)
    return {"styles_contextuels": t}


def _decode_type6(raw):
    """Cadre : <index> <flag>."""
    t = tokens_after_nom(raw)
    d = {}
    if t:
        d["index"] = t[0]
    if len(t) > 1:
        d["flag"] = t[1]
    return d


def _decode_type7(raw):
    """Style compose : <police_ref> <cadre_ref> <couleur_ref>."""
    t = tokens_after_nom(raw)
    d = {}
    if len(t) >= 1:
        d["police_ref"] = t[0]
    if len(t) >= 2:
        d["cadre_ref"] = t[1]
    if len(t) >= 3:
        d["couleur_ref"] = t[2]
    return d


def _decode_type9(raw):
    """Contexte : optionnellement suivi d'une ref i18n."""
    t = tokens_after_nom(raw)
    d = {}
    if t:
        if t[0].startswith("#"):
            d["cle_i18n"] = t[0]
        else:
            d["token"] = t[0]
    return d


DECODERS = {
    "1": _decode_type1,
    "2": _decode_type2,
    "3": _decode_type3,
    "5": _decode_type5,
    "6": _decode_type6,
    "7": _decode_type7,
    "9": _decode_type9,
}


def decode_record(raw):
    """Decode un record selon son Type. Retourne {type, nom, **champs_typed}."""
    t = chr(raw[OFF_TYPE]) if 32 <= raw[OFF_TYPE] < 127 else ""
    nom = text(raw, OFF_NOM, NOM_LEN)
    result = {"type": t, "nom": nom}
    decoder = DECODERS.get(t)
    if decoder:
        result.update(decoder(raw))
    return result


def _resolve_file(args):
    """Determine le chemin du fichier fstyle a ouvrir a partir de --variant ou --file."""
    if args.file:
        return args.file
    if args.variant:
        path = VARIANTS.get(args.variant)
        if not path:
            print(f"Erreur : variant inconnue '{args.variant}'. Valeurs : {', '.join(VARIANTS)}",
                  file=sys.stderr)
            sys.exit(2)
        return path
    print("Erreur : specifier --variant OU --file", file=sys.stderr)
    sys.exit(2)


def cmd_list(by_nom):
    items = []
    for nom, raw in by_nom.items():
        items.append({
            "nom": text(raw, OFF_NOM, NOM_LEN),
            "type": chr(raw[OFF_TYPE]) if 32 <= raw[OFF_TYPE] < 127 else "",
        })
    return {"total": len(items), "styles": items}


def cmd_stats(by_nom):
    counter = Counter()
    for raw in by_nom.values():
        t = chr(raw[OFF_TYPE]) if 32 <= raw[OFF_TYPE] < 127 else "?"
        counter[t] += 1
    total = sum(counter.values())
    by_type = {
        t: {"count": c, "pct": round(c * 100.0 / total, 1) if total else 0.0}
        for t, c in sorted(counter.items())
    }
    return {"total_nc": total, "by_type": by_type}


def cmd_detail(by_nom, nom_target):
    key = nom_target.upper()
    if key not in by_nom:
        return {"nom": nom_target, "found": False}
    decoded = decode_record(by_nom[key])
    decoded["found"] = True
    return decoded


def cmd_all_details(by_nom):
    out = {}
    for nom, raw in by_nom.items():
        out[nom] = decode_record(raw)
    return {"total": len(out), "styles": out}


def cmd_resolve(dll, nom_target, variant_order):
    """Cherche un style dans les variantes dans l'ordre, retourne la premiere correspondance."""
    key = nom_target.upper()
    tried = []
    for variant in variant_order:
        path = VARIANTS.get(variant)
        if not path or not os.path.isfile(path):
            continue
        tried.append(variant)
        by_nom, err = read_all_records(dll, path)
        if err:
            continue
        if key in by_nom:
            decoded = decode_record(by_nom[key])
            return {
                "nom": nom_target,
                "resolved": True,
                "variant_source": variant,
                "type": decoded.get("type"),
                "cle_i18n": decoded.get("cle_i18n"),
                "decoded": decoded,
                "variants_tried": tried,
            }
    return {
        "nom": nom_target,
        "resolved": False,
        "orphan": True,
        "variants_tried": tried,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Lit les feuilles de style ISAM Divalto (fstyle*.dhfi).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", help="Chemin complet d'un fichier fstyle*.dhfi (alternative a --variant)")
    parser.add_argument("--variant", choices=list(VARIANTS.keys()),
                        help=f"Variante par defaut : wpf / legacy / imp / web -> C:\\divalto\\sys\\fstyle*.dhfi")
    parser.add_argument("--variant-order", dest="variant_order", default=",".join(DEFAULT_RESOLVE_ORDER),
                        help="Ordre de resolution pour --resolve (defaut : wpf,legacy,imp)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="Liste tous les styles (nom, type)")
    group.add_argument("--stats", action="store_true", help="Distribution par Type")
    group.add_argument("--detail", metavar="NOM", help="Detail d'un style par son nom")
    group.add_argument("--all-details", dest="all_details", action="store_true",
                       help="Detail de tous les styles (consommation machine)")
    group.add_argument("--resolve", metavar="NOM",
                       help="Resout un style dans les variantes (wpf -> legacy -> imp)")
    args = parser.parse_args()

    dll = load_dll()
    if dll is None:
        print(f"Erreur : DLL introuvable : {DLL_PATH}", file=sys.stderr)
        sys.exit(2)

    # Mode resolve : gere son propre fichier, pas de --file/--variant requis
    if args.resolve:
        order = [v.strip() for v in args.variant_order.split(",") if v.strip()]
        payload = cmd_resolve(dll, args.resolve, order)
        success = payload.get("resolved", False)
        result = {"success": success, **payload}
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.exit(0 if success else 1)

    file_path = _resolve_file(args)
    if not os.path.isfile(file_path):
        print(f"Erreur : fichier introuvable : {file_path}", file=sys.stderr)
        sys.exit(2)

    by_nom, err = read_all_records(dll, file_path)
    if err:
        print(f"Erreur : {err}", file=sys.stderr)
        sys.exit(2)

    if args.list:
        payload = cmd_list(by_nom)
        success = payload["total"] > 0
    elif args.stats:
        payload = cmd_stats(by_nom)
        success = payload["total_nc"] > 0
    elif args.detail:
        payload = cmd_detail(by_nom, args.detail)
        success = payload.get("found", False)
    elif args.all_details:
        payload = cmd_all_details(by_nom)
        success = payload["total"] > 0
    else:
        parser.error("Aucun mode selectionne")
        return

    result = {"success": success, "file": file_path, **payload}
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
