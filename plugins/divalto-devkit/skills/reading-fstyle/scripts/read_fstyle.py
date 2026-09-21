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

DLL_NAME = "DhxIsam64.dll"
DEFAULT_SYS_DIR = r"C:\divalto\sys"

# --- Resolution du repertoire sys/ de Divalto (emplacement de DhxIsam64.dll + fstyle*.dhfi)
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


ENCODING = "windows-1252"
RECORD_SIZE = 1024

# Layout observe empiriquement (byte 0 = Type, byte 2+ = Nom sur 32 chars,
# puis champs de 32 chars selon Type).
OFF_TYPE = 0
OFF_NOM = 2
NOM_LEN = 32
FIELD_LEN = 32

# Variantes connues (noms de fichiers sous le repertoire sys/ resolu de Divalto)
VARIANTS = {
    "wpf":    "fstylewpf.dhfi",
    "legacy": "fstyle.dhfi",
    "imp":    "fstyleimp.dhfi",
    "web":    "fstyleweb.dhfi",
}

# Ordre de resolution par defaut (wpf d'abord car le plus riche en TBL*)
DEFAULT_RESOLVE_ORDER = ["wpf", "legacy", "imp"]


def load_dll(dll_path):
    try:
        dll = ctypes.WinDLL(dll_path)
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


# Couleur du texte d'un Type 1 : 4 composantes de 3 caracteres, cadrees a droite,
# a offset fixe. MESURE le 2026-08-30 sur fstylewpf.dhfi : 142 Type 1 sur 142 y portent
# 4 valeurs numeriques dans 0-255. Corroboree par les noms -- DATA_8_FONCE vaut
# 128/128/128 (gris), DATA_16 vaut 255/255/255 (blanc), DATA_10 vaut 255/0/0 (rouge).
# Meme decoupage 3+3+3+3 que le Type 2, dont c'est la grammaire documentee.
OFF_COULEUR_T1 = 109
LEN_COMPOSANTE = 3
NB_COMPOSANTES_T1 = 4


def _decode_couleur_type1(raw):
    """Les 4 composantes de couleur d'un Type 1, ou None si la zone n'a pas le format."""
    zone = raw[OFF_COULEUR_T1:
               OFF_COULEUR_T1 + LEN_COMPOSANTE * NB_COMPOSANTES_T1].decode(ENCODING,
                                                                          errors="replace")
    brut = [zone[i * LEN_COMPOSANTE:(i + 1) * LEN_COMPOSANTE]
            for i in range(NB_COMPOSANTES_T1)]
    valeurs = []
    for champ in brut:
        s = champ.strip().replace("\x00", "")
        if s == "":
            valeurs.append(0)
        elif s.isdigit() and 0 <= int(s) <= 255:
            valeurs.append(int(s))
        else:
            return None, zone
    return valeurs, zone


def _decode_type1(raw):
    """Police : <taille> 0 0 0 <poids> ... <famille>, plus la couleur du texte."""
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

    # Couleur du texte : SANS elle, les styles d'une meme famille sont indistinguables.
    # Mesure : 64 des 142 Type 1 de fstylewpf (45 %) decodaient a l'identique -- dont
    # 24 sur le seul {8, 400000, Tahoma}. C'est ce qui rendait impossible de repondre a
    # « de quelle couleur est ce marquage ? ».
    valeurs, zone = _decode_couleur_type1(raw)
    if valeurs is None:
        d["couleur_texte_brut"] = zone
        d["attributs_non_decodes"] = ["couleur_texte"]
    else:
        r, g, b, quatrieme = valeurs
        d["couleur_texte"] = {"r": r, "g": g, "b": b}
        # La 4e composante vaut 0 sur les 142 Type 1 mesures : sa semantique n'est PAS
        # etablie. On l'expose sans la nommer « alpha », ce qui serait une supposition.
        d["couleur_texte_composante_4"] = quatrieme
        d["couleur_texte_brut"] = zone

    # Le reste de l'enregistrement n'est PAS interprete : le dire plutot que de laisser
    # croire a un decodage complet (c'est la demande du retour terrain a l'origine).
    d.setdefault("attributs_non_decodes", [])
    d["attributs_non_decodes"] = d["attributs_non_decodes"] + [
        "semantique_composante_4", "drapeaux_apres_famille"]
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


def _resolve_file(args, sys_dir):
    """Determine le chemin du fichier fstyle a ouvrir a partir de --variant ou --file."""
    if args.file:
        return args.file
    if args.variant:
        name = VARIANTS.get(args.variant)
        if not name:
            print(f"Erreur : variant inconnue '{args.variant}'. Valeurs : {', '.join(VARIANTS)}",
                  file=sys.stderr)
            sys.exit(2)
        return os.path.join(sys_dir, name)
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


# Type 7 : les trois slots sont POSITIONNELS. Le premier vise une police dans 235 cas
# sur 235 (mesure du 2026-08-30 sur fstylewpf), mais les deux autres ne tiennent pas leur
# nom : le 2e vise un cadre 165 fois sur 235 (une couleur 59 fois, une police 11 fois) et
# le 3e une couleur 222 fois sur 235 (une police 13 fois). Nommer les slots « cadre » et
# « couleur » affirme donc une semantique que la donnee ne porte pas dans ~25 % des cas.
# Aucune reference n'est PENDANTE : les 705 pointent sur un nom present dans le fichier.
TYPE_ATTENDU_PAR_SLOT = {"police_ref": "1", "cadre_ref": "6", "couleur_ref": "2"}


def annoter_refs_type7(decoded, by_nom):
    """Ajoute a un Type 7 le type REEL de chaque reference, et signale les ecarts."""
    if decoded.get("type") != "7":
        return decoded
    reels, ecarts = {}, []
    for slot, attendu in TYPE_ATTENDU_PAR_SLOT.items():
        nom = decoded.get(slot)
        if not nom:
            continue
        cible = by_nom.get(nom.upper())
        if cible is None:
            reels[slot] = None
            ecarts.append("%s -> %s : nom ABSENT du fichier" % (slot, nom))
            continue
        reel = decode_record(cible).get("type")
        reels[slot] = reel
        if reel != attendu:
            ecarts.append("%s -> %s est un Type %s, pas un Type %s"
                          % (slot, nom, reel, attendu))
    decoded["refs_types_reels"] = reels
    if ecarts:
        # Le slot ne vise pas ce que son nom annonce : le dire, plutot que de laisser
        # le consommateur deduire une semantique fausse du nom de la cle.
        decoded["refs_hors_type_attendu"] = ecarts
    return decoded


def cmd_detail(by_nom, nom_target):
    key = nom_target.upper()
    if key not in by_nom:
        return {"nom": nom_target, "found": False}
    decoded = annoter_refs_type7(decode_record(by_nom[key]), by_nom)
    decoded["found"] = True
    return decoded


def cmd_all_details(by_nom):
    out = {}
    for nom, raw in by_nom.items():
        out[nom] = annoter_refs_type7(decode_record(raw), by_nom)
    return {"total": len(out), "styles": out}


def cmd_resolve(dll, nom_target, variant_order, sys_dir):
    """Cherche un style dans les variantes dans l'ordre, retourne la premiere correspondance."""
    key = nom_target.upper()
    tried = []
    for variant in variant_order:
        name = VARIANTS.get(variant)
        if not name:
            continue
        path = os.path.join(sys_dir, name)
        if not os.path.isfile(path):
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
                        help="Variante fstyle : wpf / legacy / imp / web (cherchee sous le repertoire sys/ resolu)")
    parser.add_argument("--variant-order", dest="variant_order", default=",".join(DEFAULT_RESOLVE_ORDER),
                        help="Ordre de resolution pour --resolve (defaut : wpf,legacy,imp)")
    parser.add_argument("--dll-path", default=None,
                        help="Chemin explicite de DhxIsam64.dll (sinon : --sys-dir, env DIVALTO_SYS_DIR, registre Divalto, puis C:\\divalto\\sys)")
    parser.add_argument("--sys-dir", default=None,
                        help="Repertoire sys/ de Divalto (DhxIsam64.dll + fstyle*.dhfi ; override du registre)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="Liste tous les styles (nom, type)")
    group.add_argument("--stats", action="store_true", help="Distribution par Type")
    group.add_argument("--detail", metavar="NOM", help="Detail d'un style par son nom")
    group.add_argument("--all-details", dest="all_details", action="store_true",
                       help="Detail de tous les styles (consommation machine)")
    group.add_argument("--resolve", metavar="NOM",
                       help="Resout un style dans les variantes (wpf -> legacy -> imp)")
    args = parser.parse_args()

    sys_dir = resolve_sys_dir(args.sys_dir)
    dll_path = resolve_dll_path(args.dll_path, args.sys_dir)
    dll = load_dll(dll_path)
    if dll is None:
        print(f"Erreur : DLL introuvable : {dll_path}", file=sys.stderr)
        sys.exit(2)

    # Mode resolve : gere son propre fichier, pas de --file/--variant requis
    if args.resolve:
        order = [v.strip() for v in args.variant_order.split(",") if v.strip()]
        payload = cmd_resolve(dll, args.resolve, order, sys_dir)
        success = payload.get("resolved", False)
        result = {"success": success, **payload}
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.exit(0 if success else 1)

    file_path = _resolve_file(args, sys_dir)
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
