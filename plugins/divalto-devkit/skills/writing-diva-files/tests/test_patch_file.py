#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de patch_file.py -- garde-fous d'edition sure.

Chaque cas rejoue un defaut REELLEMENT survenu puis corrige (issues entre crochets).
Aucun poste Divalto requis : tout se joue sur des fichiers temporaires.

Lancer :
    py .claude/skills/writing-diva-files/tests/test_patch_file.py
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
SCRIPT = os.path.join(SCRIPTS, "patch_file.py")

BASE = b"L1\r\nL2\r\nL3\r\n"


def run(args):
    r = subprocess.run([sys.executable, SCRIPT] + args, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    js = None
    for blob in (out, err):
        try:
            js = json.loads(blob)
            break
        except Exception:
            continue
    return r.returncode, js, out + err


def main():
    tmp = tempfile.mkdtemp(prefix="patchfile_tests_")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    def cible(content=BASE, name="t.dhsp"):
        p = os.path.join(tmp, name)
        with open(p, "wb") as f:
            f.write(content)
        return p

    def octets(p):
        return open(p, "rb").read()

    def ecrire_utf8(name, texte):
        p = os.path.join(tmp, name)
        with open(p, "wb") as f:
            f.write(texte.encode("utf-8"))
        return p

    try:
        # ================= encodage (bugs racine du LOT A/B) =================
        # [#312] stdin doit etre decode en UTF-8 puis reencode en ISO-8859-1
        p = cible()
        src = ecrire_utf8("in.txt", "; café 30°\r\n")
        with open(src, "rb") as fh:
            r = subprocess.run([sys.executable, SCRIPT, "--path", p, "--op", "append",
                                "--stdin"], stdin=fh, capture_output=True)
        b = octets(p)
        check("[#312] stdin : accents en ISO-8859-1, pas de mojibake",
              b"\xe9" in b and b"\xb0" in b and b"\xc3\xa9" not in b)

        # [#262] un BOM pipe doit etre strippe
        p = cible()
        bom = os.path.join(tmp, "bom.txt")
        with open(bom, "wb") as f:
            f.write(b"\xef\xbb\xbf; ligne\r\n")
        rc, js, txt = run(["--path", p, "--op", "append", "--content-file", bom])
        check("[#262] BOM du --content-file strippe", b"\xef\xbb\xbf" not in octets(p))

        # [#314] --content-file evite le quoting PowerShell (guillemets preserves)
        p = cible()
        q = ecrire_utf8("q.txt", '  Module "GTTMCHKT140.dhop"\r\n')
        rc, js, txt = run(["--path", p, "--op", "append", "--content-file", q])
        check("[#314] guillemets preserves via --content-file",
              b'Module "GTTMCHKT140.dhop"' in octets(p))

        # [P1] contenu non encodable -> refus, cible INTACTE (jamais tronquee)
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "append", "--content", "tiret — cadratin"])
        check("[P1] contenu non-Latin-1 : refus et cible intacte",
              rc != 0 and octets(p) == BASE, "rc=%s" % rc)

        # anti-mojibake sur le CONTENU INJECTE (symetrie avec write_file)
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "append", "--content", "; commentaire Ã©"])
        check("mojibake dans le contenu injecte : refus, cible intacte",
              rc != 0 and octets(p) == BASE, "rc=%s" % rc)

        # ... mais patcher un fichier DEJA SALE ailleurs doit rester possible
        sale = cible(b"; d\xc3\xa9ja sale\r\nL2\r\n", "sale.dhsp")
        rc, js, txt = run(["--path", sale, "--op", "append", "--content", "; ajout propre"])
        check("fichier deja sale ailleurs : le patch propre reste possible",
              b"; ajout propre" in octets(sale), "rc=%s" % rc)

        # ================= garde-fou anti-numero-perime =================
        # [#303] ciblage par numero SANS --expect-content -> refus
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "replace", "--line-range", "2:3", "--content", "X"])
        check("[#303] numero sans --expect-content : refus, rien ecrit",
              rc != 0 and octets(p) == BASE, "rc=%s" % rc)

        # [#303/#263] --expect-content FAUX (numeros perimes) -> refus, cible intacte
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "replace", "--line-range", "2:3",
                           "--expect-content", "PERIME\nAUSSI", "--content", "X"])
        check("[#263] --expect-content faux : refus, cible intacte",
              rc != 0 and octets(p) == BASE, "rc=%s" % rc)

        # --expect-content JUSTE -> le patch passe
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "replace", "--line-range", "2:3",
                           "--expect-content", "L2\nL3", "--content", "X"])
        check("--expect-content juste : patch applique",
              js is not None and js.get("changed") is True and octets(p) == b"L1\r\nX\r\n",
              str(octets(p)))

        # [#313] delete accepte --line N (gate par le garde-fou)
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "delete", "--line", "3",
                           "--expect-content", "L3"])
        check("[#313] delete --line N accepte", octets(p) == b"L1\r\nL2\r\n", str(octets(p)))

        # portee du garde-fou : hors replace/delete-par-numero, l'option est REFUSEE
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "insert", "--line", "2", "--position", "after",
                           "--expect-content", "BIDON", "--content", "NEW"])
        check("insert + --expect-content : refus explicite (jamais ignore en silence)",
              rc != 0 and octets(p) == BASE, "rc=%s" % rc)
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "replace", "--anchor", "L2",
                           "--expect-content", "L2", "--content", "X"])
        check("--anchor + --expect-content : refus explicite", rc != 0, "rc=%s" % rc)

        # ================= ancre =================
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "replace", "--anchor", "L2", "--content", "X"])
        check("--anchor seule : patch applique", octets(p) == b"L1\r\nX\r\nL3\r\n", str(octets(p)))

        p = cible(b"L1\r\nL2\r\nL2\r\n", "dup.dhsp")
        rc, js, txt = run(["--path", p, "--op", "replace", "--anchor", "L2", "--content", "X"])
        check("[#288] ancre non unique : refus, cible intacte",
              rc != 0 and octets(p) == b"L1\r\nL2\r\nL2\r\n", "rc=%s" % rc)

        # ================= `verified` doit signifier `valid` =================
        p = cible()
        longue = ecrire_utf8("long.txt", "; " + "B" * 300 + "\r\n")
        rc, js, txt = run(["--path", p, "--op", "append", "--content-file", longue])
        check("[#277] ligne > 251 : plus de verified:true, ecriture rejetee",
              rc != 0 and js is not None and js.get("restored") is True, "rc=%s" % rc)
        check("[#277] cible restauree a l'identique", octets(p) == BASE, str(octets(p))[:60])

        # le fichier restaure doit rester VISIBLE et reinscriptible (bug d'attribut cache)
        if os.name == "nt":
            attrs = ctypes.windll.kernel32.GetFileAttributesW(p)
            check("fichier restaure : pas d'attribut cache", attrs != -1 and not (attrs & 0x2),
                  "attrs=0x%04x" % attrs)
        try:
            with open(p, "wb") as f:
                f.write(BASE)
            reinscriptible = True
        except Exception as e:
            reinscriptible = False
        check("fichier restaure : reinscriptible", reinscriptible)

        # --no-backup : le message ne doit PAS pretendre une restauration
        p = cible()
        rc, js, txt = run(["--path", p, "--op", "append", "--content-file", longue, "--no-backup"])
        check("--no-backup : restored=False annonce", js is not None and js.get("restored") is False)
        check("--no-backup : l'ecriture est bien conservee (dit honnetement)",
              len(octets(p)) > len(BASE))

        # ================= perimetre =================
        p = cible(b"[BASE]\r\n", "t.dhsd")
        rc, js, txt = run(["--path", p, "--op", "append", "--content", "; x"])
        check("fichier structure .dhsd : refuse et redirige",
              rc != 0 and "managing-diva-dictionaries" in txt, "rc=%s" % rc)

        p = cible()
        rc, js, txt = run(["--path", p, "--op", "replace", "--anchor", "L2", "--content", "X",
                           "--dry-run"])
        check("--dry-run n'ecrit rien", octets(p) == BASE)

        rc, js, txt = run(["--path", os.path.join(tmp, "absent.dhsp"), "--op", "append",
                           "--content", "x"])
        check("fichier introuvable : echec propre, oriente vers write_file",
              rc != 0 and "write_file" in txt)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
