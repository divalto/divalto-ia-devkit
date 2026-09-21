#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de add_zoom_constant.py -- garde-fous anti-perte-de-donnees.

Ce script etait le seul ecrivain du skill a tronquer la cible AVANT d'encoder : un simple
caractere hors Latin-1 dans --comment (apostrophe typographique, tiret cadratin) vidait
a5tczoom.dhsp a 0 octet, sans backup. Ces tests gardent la correction.

Lancer :
    py .claude/skills/writing-diva-files/tests/test_add_zoom_constant.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
SCRIPT = os.path.join(SCRIPTS, "add_zoom_constant.py")
VERIFY = os.path.join(SCRIPTS, "verify_encoding.py")

BASE = ("; Constantes de zoom\r\n"
        ";REGLE ECRITURE: une ligne par zoom\r\n"
        "ZOOM_ART          =  1000\t; Zoom article\r\n")


def run(script, args):
    r = subprocess.run([sys.executable, script] + args, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    try:
        js = json.loads(out)
    except Exception:
        js = None
    return r.returncode, js, out + r.stderr.decode("utf-8", "replace")


def main():
    tmp = tempfile.mkdtemp(prefix="azc_tests_")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    def cible():
        p = os.path.join(tmp, "a5tczoom.dhsp")
        with open(p, "wb") as f:
            f.write(BASE.encode("iso-8859-1"))
        return p

    try:
        # --- 1. LE BUG : caractere hors Latin-1 -> la cible doit rester INTACTE ---
        p = cible()
        avant = os.path.getsize(p)
        rc, js, txt = run(SCRIPT, ["--file", p, "--instance", "MonEntite", "--num", "9400",
                                   "--comment", "Zoom de l’entite"])   # apostrophe typographique
        check("caractere hors Latin-1 : cible INTACTE (pas tronquee a 0)",
              os.path.getsize(p) == avant, "taille=%s (avant %s)" % (os.path.getsize(p), avant))
        check("caractere hors Latin-1 : exit non nul", rc != 0, "rc=%s" % rc)
        check("caractere hors Latin-1 : message nomme la cause",
              js is not None and "encodable" in str(js.get("error", "")).lower())

        # --- 2. --dry-run doit refuser AVANT l'ecriture reelle (plus de fausse confiance) ---
        p = cible()
        rc, js, txt = run(SCRIPT, ["--file", p, "--instance", "E", "--num", "9401",
                                   "--comment", "l’apostrophe", "--dry-run"])
        check("--dry-run refuse un contenu non encodable", rc != 0, "rc=%s" % rc)
        check("--dry-run ne modifie pas la cible", os.path.getsize(p) == len(BASE.encode("iso-8859-1")))

        # --- 3. cas nominal : ecriture + backup + CRLF final + resultat valide ---
        p = cible()
        rc, js, txt = run(SCRIPT, ["--file", p, "--instance", "MonEntite", "--num", "9400",
                                   "--comment", "Zoom entite"])
        check("cas nominal : exit 0", rc == 0, "rc=%s : %s" % (rc, txt[:120]))
        check("cas nominal : success", js is not None and js.get("success") is True)
        check("cas nominal : backup .bak cree", os.path.isfile(p + ".bak"))
        raw = open(p, "rb").read()
        check("cas nominal : CRLF final present", raw.endswith(b"\r\n"))
        check("cas nominal : constante ecrite", b"MONENTITE" in raw.upper())
        rc2, js2, _ = run(VERIFY, ["--path", p])
        check("cas nominal : verify_encoding valide le resultat",
              js2 is not None and js2.get("valid") is True)

        # --- 4. CRLF final garanti meme sans le marqueur d'insertion (Erreur 135) ---
        p2 = os.path.join(tmp, "sansmarqueur.dhsp")
        with open(p2, "wb") as f:
            f.write("ZOOM_A = 1".encode("iso-8859-1"))     # ni marqueur, ni CRLF final
        rc, js, txt = run(SCRIPT, ["--file", p2, "--instance", "E", "--num", "9402",
                                   "--comment", "test"])
        check("sans marqueur : CRLF final ajoute (Erreur 135 evitee)",
              open(p2, "rb").read().endswith(b"\r\n"))

        # --- 5. doublon : la constante existante est detectee ---
        p = cible()
        run(SCRIPT, ["--file", p, "--instance", "MonEntite", "--num", "9400", "--comment", "x"])
        rc, js, txt = run(SCRIPT, ["--file", p, "--instance", "MonEntite", "--num", "9400",
                                   "--comment", "x"])
        check("doublon detecte (already_exists)",
              js is not None and js.get("already_exists") is True, str(js)[:110])

        # --- 6. fichier introuvable : echec propre, sans traceback ---
        rc, js, txt = run(SCRIPT, ["--file", os.path.join(tmp, "absent.dhsp"),
                                   "--instance", "E", "--num", "9403", "--comment", "x"])
        check("fichier introuvable : echec propre", rc != 0 and "Traceback" not in txt)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
