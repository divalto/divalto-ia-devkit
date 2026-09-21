#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de la chaine d'encodage : write_file / verify_encoding / convert_file.

Chaque cas rejoue un defaut REELLEMENT survenu puis corrige (issues entre crochets).
Aucun poste Divalto requis.

Lancer :
    py .claude/skills/writing-diva-files/tests/test_encoding_guards.py
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
WRITE = os.path.join(SCRIPTS, "write_file.py")
VERIFY = os.path.join(SCRIPTS, "verify_encoding.py")
CONVERT = os.path.join(SCRIPTS, "convert_file.py")


def run(script, args, stdin_path=None):
    fh = open(stdin_path, "rb") if stdin_path else None
    try:
        r = subprocess.run([sys.executable, script] + args, capture_output=True, stdin=fh)
    finally:
        if fh:
            fh.close()
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
    tmp = tempfile.mkdtemp(prefix="encguards_tests_")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    def w(name, data):
        p = os.path.join(tmp, name)
        with open(p, "wb") as f:
            f.write(data)
        return p

    try:
        # ================= write_file =================
        # [#287/#305/#309] stdin decode en UTF-8 -> ISO-8859-1, rapport HONNETE
        src = w("in.txt", "; génération n° 1\r\nProc Test()\r\n".encode("utf-8"))
        out = os.path.join(tmp, "a.dhsp")
        rc, js, txt = run(WRITE, ["--path", out, "--stdin"], stdin_path=src)
        raw = open(out, "rb").read()
        check("[#305] write_file --stdin : accents en ISO-8859-1 (0xE9)",
              b"\xe9" in raw and b"\xc3\xa9" not in raw)
        check("[#309] rapport conforme au fichier reellement ecrit",
              js is not None and js.get("encoding") == "iso-8859-1")
        check("CRLF preserve", raw.endswith(b"\r\n") and raw.count(b"\n") == raw.count(b"\r\n"))

        # write_file refuse un contenu deja mojibake (garde-fou LOT A)
        rc, js, txt = run(WRITE, ["--path", os.path.join(tmp, "m.dhsp"),
                                  "--content", "; commentaire Ã©"])
        check("write_file refuse le contenu mojibake", rc != 0, "rc=%s" % rc)
        check("write_file : cible non creee apres refus",
              not os.path.exists(os.path.join(tmp, "m.dhsp")))

        # [#262] BOM strippe
        bom = w("bom.txt", b"\xef\xbb\xbf; ligne\r\n")
        out2 = os.path.join(tmp, "b.dhsp")
        rc, js, txt = run(WRITE, ["--path", out2, "--content-file", bom])
        check("[#262] BOM du --content-file strippe",
              not open(out2, "rb").read().startswith(b"\xef\xbb\xbf"))

        # write_file REFUSE d'ecraser si le backup est impossible (avant : ecrasait)
        cible = w("ro.dhsp", b"ORIGINAL\r\n")
        bak = w("ro.dhsp.bak", b"vieux")
        os.chmod(bak, 0o444)
        if os.name == "nt":
            ctypes.windll.kernel32.SetFileAttributesW(bak, 0x1 | 0x2)   # readonly + hidden
        rc, js, txt = run(WRITE, ["--path", cible, "--content", "NOUVEAU"])
        check("backup impossible : write_file REFUSE d'ecraser", rc != 0, "rc=%s" % rc)
        check("backup impossible : le fichier existant est intact",
              open(cible, "rb").read() == b"ORIGINAL\r\n")
        rc, js, txt = run(WRITE, ["--path", cible, "--content", "NOUVEAU", "--no-backup"])
        check("--no-backup : le risque assume explicitement passe", rc == 0, "rc=%s" % rc)

        # ================= verify_encoding =================
        # [#285] .dhsi (et .dhse/.dhsj) sont des fichiers DIVA a part entiere
        for ext in ("dhsi", "dhse", "dhsj", "dhsp"):
            p = w("x." + ext, b"; test\r\n")
            rc, js, txt = run(VERIFY, ["--path", p])
            check("[#285] extension .%s reconnue" % ext,
                  js is not None and js.get("valid") is True, str(js)[:90])

        # [#277] ligne physique > 251 : XWin refuse d'OUVRIR le source
        p = w("long.dhsp", (b"; " + b"A" * 300 + b"\r\n"))
        rc, js, txt = run(VERIFY, ["--path", p])
        check("[#277] ligne > 251 : valid=false", js is not None and js.get("valid") is False)
        check("[#277] exit non nul", rc != 0, "rc=%s" % rc)

        # CRLF final manquant -> Erreur 135
        p = w("nocrlf.dhsp", b"; ligne sans fin")
        rc, js, txt = run(VERIFY, ["--path", p])
        check("CRLF final manquant : valid=false", js is not None and js.get("valid") is False)

        # mojibake residuel : decode en ISO sans erreur mais contenu corrompu
        p = w("moji.dhsp", b"; commentaire \xc3\xa9 double\r\n")
        rc, js, txt = run(VERIFY, ["--path", p])
        check("mojibake residuel : valid=false", js is not None and js.get("valid") is False)

        # ================= convert_file =================
        # mojibake FRANC : doit etre repare
        p = w("pur.dhsp", b"; commentaire \xc3\xa9 double\r\n")
        rc, js, txt = run(CONVERT, ["--path", p])
        check("mojibake franc : converti", rc == 0 and js is not None and js.get("converted") is True,
              "rc=%s" % rc)
        raw = open(p, "rb").read()
        check("mojibake franc : 0xE9 restitue", b"\xe9" in raw and b"\xc3\xa9" not in raw)
        rc2, js2, _ = run(VERIFY, ["--path", p])
        check("mojibake franc : verify_encoding valide ensuite",
              js2 is not None and js2.get("valid") is True)

        # mojibake MELE a du Latin-1 valide : conversion globale impossible -> le DIRE
        p = w("mix.dhsp", b"; caf\xe9 et commentaire \xc3\xa9 double\r\n")
        rc, js, txt = run(CONVERT, ["--path", p])
        check("mojibake mele : verified=false (plus de fausse certification)",
              js is not None and js.get("verified") is False, str(js)[:110])
        check("mojibake mele : exit non nul (le code suit le verdict)", rc != 0, "rc=%s" % rc)
        check("mojibake mele : hint oriente vers une reparation chirurgicale",
              js is not None and "patch_file" in str(js.get("hint", "")))
        rc2, js2, _ = run(VERIFY, ["--path", p])
        check("mojibake mele : convert et verify disent la MEME chose",
              js2 is not None and js2.get("valid") is False)

        # fichier deja propre : rien a faire, exit 0
        p = w("ok.dhsp", b"; caf\xe9\r\n")
        rc, js, txt = run(CONVERT, ["--path", p])
        check("fichier propre : converted=false, verified=true, exit 0",
              rc == 0 and js is not None and js.get("converted") is False
              and js.get("verified") is True, "rc=%s %s" % (rc, str(js)[:80]))

        # UTF-8 franc + LF : converti en ISO-8859-1 + CRLF
        p = w("u8.dhsp", "; café 30°\n".encode("utf-8"))
        rc, js, txt = run(CONVERT, ["--path", p])
        raw = open(p, "rb").read()
        check("UTF-8 + LF : converti en ISO-8859-1 + CRLF",
              rc == 0 and b"\xe9" in raw and raw.endswith(b"\r\n"), "rc=%s" % rc)
    finally:
        for root, _dirs, files in os.walk(tmp):
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), 0o666)
                except Exception:
                    pass
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
