#!/usr/bin/env python3
"""Valide un fichier de structure JSON pour l'ecriture ISAM.

Usage:
    py .claude/skills/writing-isam-files/scripts/validate_structure.py --path structure_m4.json

    # Verifier que la CLE declaree est bien la cle physique de l'index :
    py ... --path structure.json --probe-key A --file "chemin/fichier.dhfi"

Sortie JSON:
    {valid: bool, errors: [str], fields: int, record_size: int}
    + {key_probe: {...}} avec --probe-key

Exit codes:
    0 = structure valide (et sonde concluante si demandee)
    1 = structure invalide, ou cle declaree refutee par la sonde
    2 = fichier introuvable ou JSON illisible
"""

import argparse
import ctypes
import json
import os
import sys


REQUIRED_KEYS = {"Dictionnaire", "Table", "Base", "TailleEnreg", "Structure"}
REQUIRED_FIELD_KEYS = {"Nom", "Offset", "Taille"}


def validate(data):
    """Valide la structure et retourne une liste d'erreurs."""
    errors = []

    # Cles obligatoires
    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        errors.append(f"Cles manquantes : {', '.join(sorted(missing))}")
        return errors  # pas la peine de continuer

    # TailleEnreg
    taille = data["TailleEnreg"]
    if not isinstance(taille, int) or taille <= 0:
        errors.append(f"TailleEnreg doit etre un entier positif (recu : {taille!r})")
        return errors

    # Structure
    structure = data["Structure"]
    if not isinstance(structure, list) or len(structure) == 0:
        errors.append("Structure doit etre un tableau non vide")
        return errors

    # Champs individuels
    noms_vus = set()
    for i, field in enumerate(structure):
        prefix = f"Structure[{i}]"

        if not isinstance(field, dict):
            errors.append(f"{prefix} : doit etre un objet")
            continue

        field_missing = REQUIRED_FIELD_KEYS - set(field.keys())
        if field_missing:
            errors.append(f"{prefix} : cles manquantes {', '.join(sorted(field_missing))}")
            continue

        nom = field["Nom"]
        offset = field["Offset"]
        taille_champ = field["Taille"]

        # Types
        if not isinstance(nom, str) or not nom:
            errors.append(f"{prefix} : Nom doit etre une chaine non vide")
            continue

        if not isinstance(offset, int) or offset < 0:
            errors.append(f"{prefix} ({nom}) : Offset doit etre un entier >= 0 (recu : {offset!r})")

        if not isinstance(taille_champ, int) or taille_champ <= 0:
            errors.append(f"{prefix} ({nom}) : Taille doit etre un entier > 0 (recu : {taille_champ!r})")
            continue

        # Depassement
        if isinstance(offset, int) and offset >= 0:
            if offset + taille_champ > taille:
                errors.append(
                    f"{prefix} ({nom}) : depasse TailleEnreg "
                    f"(offset {offset} + taille {taille_champ} = {offset + taille_champ} > {taille})"
                )

        # Unicite
        if nom in noms_vus:
            errors.append(f"{prefix} ({nom}) : nom en double")
        noms_vus.add(nom)

    return errors


# ---------------------------------------------------------------------------
# Sonde de cle -- la cle DECLAREE est-elle la cle PHYSIQUE de l'index ?
# ---------------------------------------------------------------------------
#
# Les blocs `Keys` des structures JSON sont ecrits A LA MAIN et rien ne les
# validait. Or une cle declaree fausse ne se manifeste qu'au moment d'un
# `update`/`delete` qui echoue de facon incomprehensible : le positionnement
# n'a pas lieu, on atterrit sur le debut de l'index, et le garde-fou refuse
# l'operation ("match approximatif refuse"). Le developpeur cherche alors du
# cote de son enregistrement, pas de la declaration.
#
# Piege mesure : le champ CE (`Ce`, `Ce1`...) appartient a la cle physique de
# CERTAINS index seulement. Sur le dictionnaire standard, **822 index sur 959
# (86 %) n'ont AUCUN champ CE dans leurs champs de cle**, mais 137 en ont un.
# Deux structures livrees par ce skill illustrent les deux cas : la cle du menu
# M2 inclut bien `Ce`, celle du multichoix ne l'incluait qu'a tort.
#
# La sonde s'AUTO-VERIFIE : elle n'a pas besoin de connaitre la bonne reponse.
#   1. lire un enregistrement en parcours sequentiel ;
#   2. en extraire les valeurs de ses PROPRES champs de cle ;
#   3. tenter de se positionner sur ces valeurs-la ;
#   4. verifier qu'on retombe sur LE MEME enregistrement.
# Si non, la cle declaree est refutee.

TDF_SIZE, TDF_NAME_OFFSET, TDF_KEY_OFFSET = 1024, 4, 261
ENCODING = "windows-1252"
_SONDE_TACHE = 15


def _charger_dll(dll_path):
    dll = ctypes.WinDLL(dll_path)
    dll.xisam_begin.argtypes = [ctypes.c_ushort]
    dll.xisam_begin.restype = ctypes.c_short
    dll.xisam_end.argtypes = [ctypes.c_ushort]
    dll.xisam_end.restype = ctypes.c_ushort
    p = ctypes.POINTER(ctypes.c_ubyte)
    dll.xisam_topenlong.argtypes = [ctypes.c_ushort, p, p]
    dll.xisam_topenlong.restype = ctypes.c_ushort
    dll.xisam_tcloselong.argtypes = [ctypes.c_ushort, p]
    dll.xisam_tcloselong.restype = ctypes.c_ushort
    dll.xisam_treadlong.argtypes = [ctypes.c_ushort, p, p, ctypes.c_ushort, p]
    dll.xisam_treadlong.restype = ctypes.c_ushort
    return dll


def _tdf(fichier):
    tdf = (ctypes.c_ubyte * TDF_SIZE)()
    for i, b in enumerate(fichier.encode(ENCODING)[:256]):
        tdf[TDF_NAME_OFFSET + i] = b
    return tdf


def _poser_cle(tdf, lettre, valeur=None):
    for i in range(TDF_KEY_OFFSET, TDF_KEY_OFFSET + 256):
        tdf[i] = 0x20
    tdf[TDF_KEY_OFFSET] = ord(lettre)
    if valeur:
        for i, b in enumerate(valeur):
            tdf[TDF_KEY_OFFSET + 1 + i] = b


def _extraire(rec, champs, noms):
    """Octets bruts de chaque champ nomme, dans l'ordre."""
    fm = {f["Nom"]: f for f in champs}
    return [bytes(rec[fm[n]["Offset"]:fm[n]["Offset"] + fm[n]["Taille"]]) for n in noms]


def sonder_cle(data, fichier, nom_index, dll_path):
    """Confronte la cle declaree a la realite de l'index. Retourne un dict."""
    res = {"index": nom_index, "fichier": fichier, "concluant": False,
           "cle_declaree": None, "verdict": None, "detail": None}
    keys = data.get("Keys") or {}
    if nom_index not in keys:
        res["detail"] = ("index '%s' absent du bloc Keys (declares : %s)"
                         % (nom_index, ", ".join(sorted(keys)) or "aucun"))
        return res
    decl = keys[nom_index]
    lettre = (decl.get("Letter") or nom_index)[0]
    noms = list(decl.get("Fields") or [])
    res["cle_declaree"] = {"lettre": lettre, "champs": noms}
    if not noms:
        res["detail"] = "aucun champ de cle declare"
        return res

    champs = data["Structure"]
    manquants = [n for n in noms if n not in {f["Nom"] for f in champs}]
    if manquants:
        res["detail"] = "champ(s) de cle absent(s) de Structure : %s" % manquants
        return res

    if not os.path.isfile(fichier):
        res["detail"] = "fichier introuvable : %s" % fichier
        return res
    if not os.path.isfile(dll_path):
        res["detail"] = ("DLL introuvable (%s) -- sonde impossible sur ce poste"
                         % dll_path)
        return res

    taille = data["TailleEnreg"]
    dll = _charger_dll(dll_path)
    dll.xisam_begin(ctypes.c_ushort(_SONDE_TACHE))
    try:
        # 1-2. lire un enregistrement et relever ses valeurs de cle
        tdf = _tdf(fichier)
        mode_open = (ctypes.c_ubyte * 1)(0x50)
        if dll.xisam_topenlong(ctypes.c_ushort(_SONDE_TACHE), tdf, mode_open) != 0:
            res["detail"] = "ouverture du fichier impossible"
            return res
        rec = (ctypes.c_ubyte * taille)()
        mode = (ctypes.c_ubyte * 1)(ord("P"))
        _poser_cle(tdf, lettre)
        temoin = None
        for _ in range(3):     # on saute les premiers enregs (souvent un en-tete)
            if dll.xisam_treadlong(ctypes.c_ushort(_SONDE_TACHE), tdf, rec,
                                   ctypes.c_ushort(taille), mode) != 0:
                break
            temoin = bytes(rec)
        dll.xisam_tcloselong(ctypes.c_ushort(_SONDE_TACHE), tdf)
        if temoin is None:
            res["detail"] = "aucun enregistrement lisible : sonde impossible"
            return res
        attendu = _extraire(temoin, champs, noms)

        # 3. se positionner sur ces valeurs exactes
        tdf = _tdf(fichier)
        if dll.xisam_topenlong(ctypes.c_ushort(_SONDE_TACHE), tdf, mode_open) != 0:
            res["detail"] = "reouverture impossible"
            return res
        _poser_cle(tdf, lettre, b"".join(attendu))
        rec2 = (ctypes.c_ubyte * taille)()
        ret = dll.xisam_treadlong(ctypes.c_ushort(_SONDE_TACHE), tdf, rec2,
                                  ctypes.c_ushort(taille), mode)
        dll.xisam_tcloselong(ctypes.c_ushort(_SONDE_TACHE), tdf)
    finally:
        dll.xisam_end(ctypes.c_ushort(_SONDE_TACHE))

    lisible = lambda vals: [v.decode(ENCODING, "replace").strip() for v in vals]
    res["concluant"] = True
    if ret != 0:
        res["verdict"] = "REFUTEE"
        res["detail"] = (
            "positionnement en echec (ret=%d) sur les valeurs d'un enregistrement "
            "pourtant lu juste avant : %s. La cle declaree n'est pas la cle physique "
            "de l'index." % (ret, dict(zip(noms, lisible(attendu)))))
        return res

    # 4. est-ce le meme enregistrement ?
    obtenu = _extraire(bytes(rec2), champs, noms)
    if obtenu == attendu:
        res["verdict"] = "CONFIRMEE"
        res["detail"] = ("positionnement exact sur %s"
                         % dict(zip(noms, lisible(attendu))))
    else:
        res["verdict"] = "REFUTEE"
        res["detail"] = (
            "positionnement inefficace : demande %s, atterri sur %s. Le champ CE "
            "figure-t-il vraiment dans la cle de cet index ? Sur le standard, 86 %% "
            "des index n'en ont pas -- cela se lit dans le dictionnaire, index par "
            "index, et ne se suppose pas."
            % (dict(zip(noms, lisible(attendu))), dict(zip(noms, lisible(obtenu)))))
    return res


def main():
    parser = argparse.ArgumentParser(description="Valide un fichier de structure ISAM JSON")
    parser.add_argument("--path", required=True, help="Chemin vers le fichier structure JSON")
    parser.add_argument("--probe-key", default=None, metavar="INDEX",
                        help="Confronte la cle declaree de cet index (ex: A, Index_A_M2) "
                             "a la realite du fichier : lit un enregistrement, se "
                             "repositionne sur ses propres valeurs de cle et verifie "
                             "qu'on retombe dessus. Necessite --file.")
    parser.add_argument("--file", default=None,
                        help="Fichier .dhfi reel a sonder (avec --probe-key). Travailler "
                             "sur une COPIE si le fichier est en production.")
    parser.add_argument("--dll-path", default=os.path.join(r"C:\divalto\sys", "DhxIsam64.dll"),
                        help="Chemin de DhxIsam64.dll pour la sonde")
    args = parser.parse_args()

    # Charger le fichier
    try:
        with open(args.path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Fichier introuvable : {args.path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"JSON invalide : {e}", file=sys.stderr)
        sys.exit(2)

    # Valider
    errors = validate(data)
    fields = len(data.get("Structure", []))
    record_size = data.get("TailleEnreg", 0)

    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "fields": fields,
        "record_size": record_size,
    }

    if args.probe_key:
        if not args.file:
            print("--probe-key exige --file (le .dhfi a sonder)", file=sys.stderr)
            sys.exit(2)
        sonde = sonder_cle(data, args.file, args.probe_key, args.dll_path)
        result["key_probe"] = sonde
        # Une cle refutee invalide la structure : `update`/`delete` ne peuvent pas
        # fonctionner avec elle. Une sonde non concluante (DLL absente, fichier
        # illisible) ne change rien -- on ne conclut pas sur une absence de mesure.
        if sonde.get("verdict") == "REFUTEE":
            result["valid"] = False
            result["errors"].append(
                "cle '%s' REFUTEE par la sonde : %s" % (args.probe_key, sonde["detail"]))

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
