#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables -- `is_surcharge` est une PRESOMPTION, pas un fait.

`is_dhsf_filename.py` ne recoit qu'un **nom de fichier** : il n'ouvre rien. Et un
`.dhsf` ne porte **aucun marqueur interne** de surcharge -- verifie sur 2962 fichiers
reels (2438 du standard X.13 + 524 d'un specifique) : zero occurrence de
`overwrite` / `overwrittenby`. Le suffixe `u` du nom est donc le **seul** signal
disponible ici, contrairement aux `.dhps` (dont l'en-tete `xwin-s-sprojet` est
autoritaire).

La consequence est inevitable : tout nom finissant par la lettre `u` est flague, y
compris pour des raisons purement lexicales. Les **5 masques du standard X.13** dans
ce cas -- `a5eepersmenu`, `rceebordereau`, `rcembordereau`, `rceztreressimu`,
`speewebscru` -- ne sont **aucun** des surcharges.

On ne peut donc pas corriger la deduction ; ce qui se corrige, c'est de cesser de la
presenter comme un fait etabli. Ces tests gardent cet aveu : ils echouent si
quelqu'un retire l'avertissement ou la mention de la base de deduction.

Lancer :
    py .claude/skills/manipulating-dhsf-screens/tests/run_all.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "..", "scripts", "is_dhsf_filename.py"))

# Les 5 masques du standard X.13 finissant par 'u' -- aucun n'est une surcharge.
FAUX_POSITIFS_STANDARD = [
    "a5eepersmenu.dhsf",     # men-u
    "rceebordereau.dhsf",    # bordere-au
    "rcembordereau.dhsf",    # bordere-au
    "rceztreressimu.dhsf",   # ressi-mu
    "speewebscru.dhsf",      # websc-ru
]


def parse(nom):
    r = subprocess.run([sys.executable, SCRIPT, "--filename", nom], capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    i = out.find("{")
    return (json.loads(out[i:]) if i >= 0 else {}), r.returncode


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    # La base de la deduction doit TOUJOURS etre annoncee, surcharge ou non.
    js, _ = parse("gtez000_sql.dhsf")
    check("un masque ordinaire : is_surcharge = false",
          js.get("is_surcharge") is False, "js=%s" % js)
    check("la base de la deduction est annoncee meme quand la reponse est false",
          "PRESOMPTION" in (js.get("is_surcharge_base") or ""),
          "is_surcharge_base=%r" % js.get("is_surcharge_base"))
    check("pas d'avertissement quand rien n'est presume",
          "is_surcharge_avertissement" not in js, "js=%s" % sorted(js))

    # Les 5 faux positifs mesures du standard : la reponse reste `true` (on ne peut
    # pas faire mieux), mais elle doit etre accompagnee de son avertissement.
    for nom in FAUX_POSITIFS_STANDARD:
        js, _ = parse(nom)
        check("[faux positif mesure] %-24s is_surcharge reste true" % nom,
              js.get("is_surcharge") is True, "js=%s" % js)
        check("[faux positif mesure] %-24s avertissement present" % nom,
              "is_surcharge_avertissement" in js, "cles=%s" % sorted(js))

    # L'avertissement doit dire l'essentiel : la base, la mesure, et quoi faire.
    js, _ = parse("a5eepersmenu.dhsf")
    avert = js.get("is_surcharge_avertissement") or ""
    check("l'avertissement nomme la base (suffixe seul)",
          "suffixe" in avert.lower(), "avert=%r" % avert[:120])
    check("l'avertissement dit qu'aucun .dhsf ne porte de marqueur interne",
          "marqueur interne" in avert, "avert=%r" % avert[:200])
    check("l'avertissement cite les contre-exemples mesures du standard",
          "rceebordereau" in avert, "avert=%r" % avert[:250])
    check("l'avertissement dit COMMENT confirmer autrement",
          "Confirmer" in avert or "confirmer" in avert, "avert=%r" % avert[:250])

    # Un vrai nom de surcharge reste reconnu (la deduction garde son utilite).
    js, _ = parse("gtez000u.dhsf")
    check("un vrai nom de surcharge reste presume surcharge",
          js.get("is_surcharge") is True, "js=%s" % js)

    # Non-regression : la regle universelle (pos 3 = 'e') n'est pas touchee.
    js, code = parse("gtaz000.dhsf")
    check("non-regression : pos 3 != 'e' -> pas un masque, exit 1",
          js.get("is_mask") is False and code == 1, "js=%s exit=%s" % (js, code))

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
