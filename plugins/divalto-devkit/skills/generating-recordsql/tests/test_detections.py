#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ce que le validateur DETECTE vraiment, sur des fichiers reels.

Premiere suite de comportement de ce skill : l autre ne verifie que les CODES -- prefixe,
table, restes. Un code bien nomme peut tres bien ne rien detecter.

Le cas 1 vient d un defaut mesure. RSQ03 annonce Nom du RecordSql vide, et son motif
exigeait au moins un caractere non blanc. Un Name= reellement vide ne matchait donc pas
du tout : la boucle ne tournait pas et la regle restait muette sur le cas exact qu elle
promet. Seule la forme avec deux guillemets declenchait. Une regle peut etre juste dans
son libelle et aveugle dans son motif.

Lancer :
    py plugin/skills/generating-recordsql/tests/test_detections.py
"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
GEN = os.path.join(SKILL, "scripts", "generate_rsql.py")
VAL = os.path.join(SKILL, "scripts", "validate_rsql.py")
GUILLEMETS = chr(34) + chr(34)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def genere():
    """Un .dhsq produit par le generateur du skill -- jamais fabrique a la main."""
    d = tempfile.mkdtemp(prefix="rsql_")
    p = os.path.join(d, "rtlrsfamrglt.dhsq")
    r = subprocess.run([sys.executable, GEN, "--params", "--domaine", "Retail",
                        "--entite", "FamRglt", "--table", "RtlFamRglt",
                        "--champ-cle", "RgltFam", "--description", "Famille",
                        "--output", p], capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:300]
    return io.open(p, encoding="iso-8859-1", newline="").read()


def valider(texte):
    p = os.path.join(tempfile.mkdtemp(prefix="rsql_"), "rtlrsfamrglt.dhsq")
    io.open(p, "w", encoding="iso-8859-1", newline="").write(texte)
    r = subprocess.run([sys.executable, VAL, "--path", p], capture_output=True)
    rap = json.loads(r.stdout.decode("utf-8", "replace"))
    return set(v["rule"] for cle in ("errors", "warnings")
               for v in (rap.get(cle) or []) if isinstance(v, dict) and v.get("rule"))


@cas("1. RSQ03 voit les DEUX formes de nom vide : sans valeur, et avec deux guillemets")
def cas1():
    base = genere()
    assert not valider(base), "le fichier genere doit sortir vierge"
    formes = {
        "Name= sans aucune valeur": "<RecordSql Name= ",
        "Name= avec deux guillemets": "<RecordSql Name=" + GUILLEMETS + " ",
    }
    manques = []
    for libelle, remplacant in formes.items():
        mute = base.replace("<RecordSql Name=FamRgltRtl ", remplacant, 1)
        assert mute != base, "mutation sans effet : %s" % libelle
        if "RSQ03" not in valider(mute):
            manques.append(libelle)
    assert not manques, (
        "RSQ03 annonce un nom vide mais ne voit pas : %s" % manques)
    return "%d formes de nom vide, toutes detectees" % len(formes)


@cas("2. TEMOIN : un nom valide ne declenche pas RSQ03")
def cas2():
    """Sans ce temoin, le cas 1 passerait avec un motif qui signalerait TOUT."""
    obtenus = valider(genere())
    assert "RSQ03" not in obtenus, (
        "faux positif : un RecordSql correctement nomme ne doit rien declencher (%s)"
        % sorted(obtenus))
    return "nom valide, aucun verdict"


def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    echecs = []
    for titre, fn in CAS:
        try:
            note = fn()
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
