#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le generateur produit-il un fichier que son propre validateur accepte ?

Cette suite est nee d un defaut que rien ne pouvait voir : le gabarit livre posait
Zoom.ok = C puis continuait -- Where.Exists, reservation, titre -- alors qu il venait de
declarer la cle refusee. TOUT zoom genere par le skill naissait donc avec un
avertissement ZSQL02, emis par le validateur du meme skill.

Personne ne le voyait parce que personne ne faisait tourner les deux outils l un apres
l autre. C est pourtant l invariant le plus simple d un skill qui GENERE et VALIDE : ce
qu il produit doit passer ce qu il controle. Le cas 1 en fait un test.

Le cas 2 est son temoin : sans lui, le cas 1 passerait aussi si le validateur devenait
muet.

Lancer :
    py plugin/skills/generating-zoom-sql/tests/test_detections.py
"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
GEN = os.path.join(SKILL, "scripts", "generate_zoom.py")
VAL = os.path.join(SKILL, "scripts", "validate_zoom.py")
CRLF = chr(13) + chr(10)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def genere():
    """Un .dhsp produit par le generateur du skill. Le nom respecte la convention de
    la 4e lettre, sinon ZSQL10 ne s applique pas et le test mesurerait moins."""
    d = tempfile.mkdtemp(prefix="zsql_")
    p = os.path.join(d, "rtez01_sql.dhsp")
    r = subprocess.run([sys.executable, GEN, "--params", "--domaine", "Retail",
                        "--entite", "FamRglt", "--table", "RtlFamRglt",
                        "--champ-cle", "RgltFam", "--description", "Famille",
                        "--output", p], capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:300]
    return p


def valider(chemin):
    r = subprocess.run([sys.executable, VAL, "--path", chemin], capture_output=True)
    rap = json.loads(r.stdout.decode("utf-8", "replace"))
    return [(c.get("rule"), c.get("message", "")) for c in (rap.get("checks") or [])]


@cas("1. INVARIANT : ce que le generateur produit passe ce que le validateur controle")
def cas1():
    verdicts = valider(genere())
    assert not verdicts, (
        "le zoom genere par ce skill est signale par le validateur du MEME skill : %s"
        % [(r, m[:70]) for r, m in verdicts])
    return "zoom genere, aucun verdict"


@cas("2. TEMOIN : le validateur n est pas muet -- un zoom casse est bien signale")
def cas2():
    """Sans ce temoin, le cas 1 passerait aussi si le validateur cessait de detecter."""
    p = genere()
    texte = io.open(p, encoding="iso-8859-1", newline="").read()
    mute = texte.replace(CRLF + chr(9) + chr(9) + "preturn", "", 1)
    assert mute != texte, "mutation sans effet : le preturn attendu est introuvable"
    q = os.path.join(tempfile.mkdtemp(prefix="zsql_"), "rtez01_sql.dhsp")
    io.open(q, "w", encoding="iso-8859-1", newline="").write(mute)
    codes = [r for r, _ in valider(q)]
    assert "ZSQL02" in codes, (
        "un preturn retire doit lever ZSQL02 ; obtenu : %s" % codes)
    return "un preturn retire leve bien ZSQL02"


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
