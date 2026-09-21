#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de `write_isam.py` -- cadrage de cle, champs binaires, sauvegarde.

, RETEX #334 et #290.

**Aucune DLL, aucun fichier ISAM reel requis.** Les trois defauts corriges vivent dans
des fonctions pures (`encoder_champ`, `build_tdf_key`, `record_matches_key_fields`) ou
dans une copie de fichier -- tous testables sans `DhxIsam64.dll` et sans toucher a un
`.dhfi` de production.

Les trois defauts rejoues :

1. **#334 -- le cadrage s'arretait a mi-chemin.** `build_record` lisait `Justify`,
   `build_tdf_key` faisait un `ljust` inconditionnel : un champ numerique cadre a
   DROITE (`"     131"`) partait dans la cle cadre a GAUCHE (`"131     "`), une cle
   totalement differente en tri octet par octet. Declenche par la structure que le
   skill livre lui-meme (`Index_A_M2` = `Ce`+`Reg`+`Ordre`, `Ordre` etant
   `Justify=right`) -- donc sur le chemin nominal, pas dans un cas limite.

2. **Le defaut JUMEAU, que l'issue ne nommait pas.** `record_matches_key_fields`
   comparait avec un simple `rstrip` : les espaces de TETE d'un champ cadre a droite
   restaient, et la verification echouait meme apres un positionnement correct. Meme
   message d'erreur, cause distincte -- corriger seul `build_tdf_key` aurait laisse
   `update`/`delete` casses.

3. **#290 -- champ binaire inexprimable, et aucun filet.** La lecture rend un champ
   `Type=B` en hexadecimal ; l'ecriture n'avait aucun equivalent (`str().encode(cp1252)`
   ne permet pas d'exprimer un octet arbitraire). Et `write_isam.py` n'a jamais cree de
   sauvegarde, alors que son voisin d'ecriture texte le fait par defaut.

Lancer :
    py .claude/skills/writing-isam-files/tests/run_all.py
"""
import ctypes
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "..", "scripts", "write_isam.py"))

_spec = importlib.util.spec_from_file_location("_write_isam", SCRIPT)
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


# --- champs calques sur la structure livree par le skill (structure_xmenuf_m2) ---
CE = {"Nom": "Ce", "Offset": 0, "Taille": 1}
REG = {"Nom": "Reg", "Offset": 1, "Taille": 8}
ORDRE = {"Nom": "Ordre", "Offset": 9, "Taille": 8, "Justify": "right"}
DATEMC = {"Nom": "datemc", "Offset": 17, "Taille": 8, "Type": "B"}
CHAMPS = [CE, REG, ORDRE, DATEMC]
KEY_FIELDS = ["Ce", "Reg", "Ordre"]
TAILLE_ENREG = 25


def cadrage_fautif(valeur, field):
    """La v1 de `build_tdf_key` : `ljust` inconditionnel, sans regarder Justify."""
    return str(valeur).encode(W.ENCODING).ljust(field["Taille"], b" ")[:field["Taille"]]


def cle_du_tdf(tdf, key_fields, champs):
    """Relit la valeur de cle ecrite dans le TDF (lettre en 261, valeur des 262)."""
    field_map = {f["Nom"]: f for f in champs}
    out, off = [], 262
    for n in key_fields:
        t = field_map[n]["Taille"]
        out.append(bytes(tdf[off:off + t]))
        off += t
    return out


# --------------------------------------------------------------------------
# #334 -- cadrage de la cle
# --------------------------------------------------------------------------

@cas("1. #334 : un champ Justify=right est cadre a DROITE dans la cle")
def cas1():
    tdf = (ctypes.c_ubyte * W.TDF_SIZE)()
    donnees = {"Ce": "2", "Reg": "MENU", "Ordre": "131"}
    W.build_tdf_key(tdf, "A", KEY_FIELDS, donnees, CHAMPS)
    ce, reg, ordre = cle_du_tdf(tdf, KEY_FIELDS, CHAMPS)
    assert chr(tdf[261]) == "A", "la lettre d'index doit rester en KEY[0]"
    assert ce == b"2", ce
    assert reg == b"MENU    ", reg
    assert ordre == b"     131", "attendu cadre a droite, obtenu %r" % ordre
    return "Ordre -> %r (et non %r)" % (ordre, cadrage_fautif("131", ORDRE))


@cas("2. TEMOIN : le cadrage fautif produit une cle DIFFERENTE")
def cas2():
    bon = W.encoder_champ("131", ORDRE)
    fautif = cadrage_fautif("131", ORDRE)
    assert bon != fautif, "sans difference, le cas 1 ne prouverait rien"
    assert fautif == b"131     ", fautif
    assert bon < fautif, ("en tri octet par octet les deux cles ne se positionnent pas "
                          "au meme endroit : %r vs %r" % (bon, fautif))
    return "%r vs %r -- deux positions differentes dans l'index" % (bon, fautif)


@cas("3. Le cadrage de la CLE est identique a celui de l'ENREGISTREMENT")
def cas3():
    """L'invariant qui manquait : les deux representations doivent coincider."""
    donnees = {"Ce": "2", "Reg": "MENU", "Ordre": "131"}
    rec, _w = W.build_record(donnees, CHAMPS, TAILLE_ENREG)
    tdf = (ctypes.c_ubyte * W.TDF_SIZE)()
    W.build_tdf_key(tdf, "A", KEY_FIELDS, donnees, CHAMPS)
    for nom, lu in zip(KEY_FIELDS, cle_du_tdf(tdf, KEY_FIELDS, CHAMPS)):
        f = {x["Nom"]: x for x in CHAMPS}[nom]
        dans_enreg = bytes(rec[f["Offset"]:f["Offset"] + f["Taille"]])
        assert lu == dans_enreg, ("%s : cle=%r mais enregistrement=%r" % (nom, lu, dans_enreg))
    return "les 3 champs de cle coincident octet pour octet"


@cas("4. Champ Justify=right : la valeur deja cadree est acceptee a l'identique")
def cas4():
    assert W.encoder_champ("     131", ORDRE) == W.encoder_champ("131", ORDRE)
    return "idempotent : '131' et '     131' donnent le meme resultat"


# --------------------------------------------------------------------------
# Le defaut jumeau -- verification post-lecture
# --------------------------------------------------------------------------

@cas("5. JUMEAU : la verification accepte un enreg dont la cle est cadree a droite")
def cas5():
    donnees = {"Ce": "2", "Reg": "MENU", "Ordre": "131"}
    rec, _ = W.build_record(donnees, CHAMPS, TAILLE_ENREG)
    assert W.record_matches_key_fields(rec, donnees, KEY_FIELDS, CHAMPS), (
        "un enregistrement construit par le skill lui-meme doit se reconnaitre")
    return "sans ce correctif : rstrip laissait les espaces de tete -> refus systematique"


@cas("6. TEMOIN du jumeau : l'ancienne comparaison (rstrip) aurait refuse")
def cas6():
    rec, _ = W.build_record({"Ce": "2", "Reg": "MENU", "Ordre": "131"}, CHAMPS, TAILLE_ENREG)
    lu = bytes(rec[ORDRE["Offset"]:ORDRE["Offset"] + ORDRE["Taille"]]).rstrip(b" ")
    attendu_ancien = "131".encode(W.ENCODING).rstrip(b" ")
    assert lu != attendu_ancien, "sans difference, le cas 5 ne prouverait rien"
    return "ancienne comparaison : %r != %r -> 'match approximatif refuse'" % (lu, attendu_ancien)


@cas("7. NON-REGRESSION : un enreg voisin reste REFUSE (garde anti-corruption)")
def cas7():
    rec, _ = W.build_record({"Ce": "2", "Reg": "MENU", "Ordre": "132"}, CHAMPS, TAILLE_ENREG)
    vise = {"Ce": "2", "Reg": "MENU", "Ordre": "131"}
    assert not W.record_matches_key_fields(rec, vise, KEY_FIELDS, CHAMPS), (
        "assouplir la comparaison ne doit PAS ouvrir la porte a l'ecrasement d'un voisin")
    return "l'assouplissement porte sur le cadrage, pas sur l'identite de la cle"


# --------------------------------------------------------------------------
# #290 -- champs binaires
# --------------------------------------------------------------------------

@cas("8. #290 : un champ Type=B accepte de l'hexadecimal et ecrit les octets exacts")
def cas8():
    rec, warns = W.build_record({"datemc": "01D9EF910F1F5C9D"}, CHAMPS, TAILLE_ENREG)
    lu = bytes(rec[DATEMC["Offset"]:DATEMC["Offset"] + DATEMC["Taille"]])
    assert lu == bytes.fromhex("01D9EF910F1F5C9D"), lu
    assert not any("datemc" in w and "non fourni" in w for w in warns), warns
    return "8 octets bruts places a l'offset du champ"


@cas("9. #290 : hexadecimal invalide -> REFUS, pas d'ecriture silencieuse")
def cas9():
    for mauvais in ("ZZZZZZZZZZZZZZZZ", "pas de l'hex"):
        try:
            W.encoder_champ(mauvais, DATEMC)
            raise AssertionError("valeur acceptee a tort : %r" % mauvais)
        except ValueError as e:
            assert "hexadecimal" in str(e), str(e)


@cas("10. #290 : mauvaise longueur -> REFUS, jamais de troncature")
def cas10():
    for mauvais in ("01D9EF91", "01D9EF910F1F5C9DAA"):
        try:
            W.encoder_champ(mauvais, DATEMC)
            raise AssertionError("longueur acceptee a tort : %r" % mauvais)
        except ValueError as e:
            assert "refuse plutot que tronque" in str(e), str(e)
    return "une troncature muette produirait une valeur binaire plausible mais fausse"


@cas("11. #290 : champ binaire NON fourni -> reste a 0x20 mais est SIGNALE")
def cas11():
    rec, warns = W.build_record({"Ce": "2"}, CHAMPS, TAILLE_ENREG)
    lu = bytes(rec[DATEMC["Offset"]:DATEMC["Offset"] + DATEMC["Taille"]])
    assert lu == b" " * 8, lu
    signale = [w for w in warns if "datemc" in w and "non fourni" in w]
    assert signale, "l'absence doit etre signalee : %s" % warns
    assert "hexadecimal" in signale[0], signale[0]
    return "aucune valeur inventee, mais l'utilisateur est averti"


@cas("12. #290 : aller-retour lecture -> ecriture (symetrie du Type=B)")
def cas12():
    """La lecture rend `raw.hex().upper()` ; l'ecriture doit le reaccepter tel quel."""
    original = bytes.fromhex("01D7328FC9A13577")
    comme_lu = original.hex().upper()
    assert W.encoder_champ(comme_lu, DATEMC) == original
    return "ce que read_isam rend, write_isam le reprend"


# --------------------------------------------------------------------------
# #290 -- sauvegarde
# --------------------------------------------------------------------------

def _paire(tmp, nom="gtfdmc"):
    dhfi = os.path.join(tmp, nom + ".dhfi")
    dhfd = os.path.join(tmp, nom + ".dhfd")
    open(dhfi, "wb").write(b"DONNEES" * 100)
    open(dhfd, "wb").write(b"INDEX" * 100)
    return dhfi, dhfd


def _empreinte(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


@cas("13. #290 : la sauvegarde couvre les DEUX fichiers de la paire ISAM")
def cas13(tmp):
    dhfi, dhfd = _paire(tmp)
    W._DEJA_SAUVEGARDES.clear()
    crees = W.sauvegarder_isam(dhfi)
    assert os.path.isfile(dhfi + ".bak"), "sauvegarde du .dhfi manquante"
    assert os.path.isfile(dhfd + ".bak"), (
        "sauvegarde du .dhfd manquante -- un .dhfi seul ne permet PAS de restaurer")
    assert len(crees) == 2, crees
    return "le RETEX ne demandait que le .dhfi : sa suggestion etait incomplete"


@cas("14. #290 : le .bak est fidele a l'original")
def cas14(tmp):
    dhfi, dhfd = _paire(tmp)
    W._DEJA_SAUVEGARDES.clear()
    W.sauvegarder_isam(dhfi)
    for p in (dhfi, dhfd):
        assert _empreinte(p) == _empreinte(p + ".bak"), "copie non fidele : " + p


@cas("15. #290 : UN SEUL .bak par fichier, meme sur un lot de N enregistrements")
def cas15(tmp):
    dhfi, _dhfd = _paire(tmp)
    W._DEJA_SAUVEGARDES.clear()
    W.sauvegarder_isam(dhfi)
    avant = _empreinte(dhfi + ".bak")
    open(dhfi, "wb").write(b"MODIFIE")          # simule la 1re ecriture
    crees = W.sauvegarder_isam(dhfi)            # 2e enregistrement du meme lot
    assert crees == [], "une 2e sauvegarde a eu lieu : %s" % crees
    assert _empreinte(dhfi + ".bak") == avant, (
        "le .bak a ete ecrase par un etat DEJA modifie -- le filet ne sert plus a rien")
    return "sinon le 2e enregistrement detruirait la seule copie saine"


@cas("16. #290 : .dhfd absent -> pas de plantage, on sauvegarde ce qui existe")
def cas16(tmp):
    dhfi = os.path.join(tmp, "seul.dhfi")
    open(dhfi, "wb").write(b"DONNEES")
    W._DEJA_SAUVEGARDES.clear()
    crees = W.sauvegarder_isam(dhfi)
    assert crees == [dhfi + ".bak"], crees
    assert not os.path.isfile(os.path.join(tmp, "seul.dhfd.bak"))


# --------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    echecs = []
    for titre, fn in CAS:
        tmp = tempfile.mkdtemp(prefix="isam_")
        try:
            note = fn(tmp) if fn.__code__.co_argcount else fn()
            print("  OK   %s" % titre)
            if note:
                print("         -> %s" % note)
        except AssertionError as e:
            echecs.append(titre)
            print("  ECHEC %s" % titre)
            print("         %s" % str(e)[:400])
        except Exception as e:
            echecs.append(titre)
            print("  ERREUR %s : %s: %s" % (titre, type(e).__name__, str(e)[:300]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("")
    if echecs:
        print("BILAN : %d/%d cas en ECHEC" % (len(echecs), len(CAS)))
        for t in echecs:
            print("  - " + t)
        return 1
    print("BILAN : %d/%d cas OK" % (len(CAS), len(CAS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
