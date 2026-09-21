#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables -- l'EN-TETE fait foi, le suffixe `u` n'est qu'un indice.

`check_workspace_coherence.py` compare le nom d'un `.dhpt` a son en-tete. Il avait
les deux signaux sous la main et faisait confiance au mauvais : un nom finissant par
la lettre `u` declenchait une **`error`** conseillant de passer l'en-tete en
`xwin-s-projet 2.0`.

Or le suffixe `u` est une **convention de nommage**, pas un marqueur. Mesure sur un
workspace reel : `addon mercure ieu.dhpt` (ie-**u**) porte l'en-tete `xwin-projet`,
qui est **parfaitement correct**. Suivre le conseil du script transformait un projet
standard en surcharge declaree -- un conseil activement nuisible.

Le constat subsiste (une divergence nom/en-tete vaut d'etre signalee) mais en
`warning`, et sans plus rien prescrire.

Lancer :
    py .claude/skills/understanding-integrator-workspace/tests/run_all.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "..", "scripts",
                                      "check_workspace_coherence.py"))

DHPT = ('[general]\nnom="p"\n[profildefaut]\n[profil]\nnom="x"\n'
        '[sousprojets]\n[projetsfusion]\n[fabricationmere]\n[autres]\n')


def workspace(tmp, nom_dhpt, entete):
    """Fabrique un workspace minimal contenant un seul .dhpt."""
    racine = os.path.join(tmp, "ws")
    os.makedirs(os.path.join(racine, "projets"), exist_ok=True)
    with open(os.path.join(racine, "projets", nom_dhpt), "wb") as fh:
        fh.write((entete + "\n" + DHPT).replace("\r\n", "\n")
                 .replace("\n", "\r\n").encode("iso-8859-1"))
    impl = os.path.join(racine, "implicite.txt")
    io.open(impl, "wb").write(b"")
    return racine, impl


def audit(racine, impl):
    r = subprocess.run([sys.executable, SCRIPT, "--workspace", racine,
                        "--implicit", impl, "--confirmed-by-user"],
                       capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    i = out.find("{")
    return (json.loads(out[i:]) if i >= 0 else {}), r.returncode


def constats(js, regle):
    return [f for f in js.get("findings") or [] if f.get("rule") == regle]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    tmp = tempfile.mkdtemp(prefix="uiw_tests_")
    try:
        # Cas mesure sur workspace reel : nom finissant par 'u' pour raison lexicale,
        # en-tete standard CORRECT.
        racine, impl = workspace(tmp, "addon mercure ieu.dhpt", "xwin-projet        2.0")
        js, _ = audit(racine, impl)
        cn = constats(js, "convention-naming")
        check("nom en 'u' + en-tete standard : le constat existe toujours",
              len(cn) == 1, "constats=%s" % cn)
        check("... mais en `warning`, plus en `error`",
              cn and cn[0]["severity"] == "warning",
              "severite=%s" % (cn[0]["severity"] if cn else None))
        check("... et il ne compte PAS comme une erreur de l'audit",
              js.get("summary", {}).get("errors") == 0,
              "summary=%s" % js.get("summary"))

        msg = cn[0]["message"] if cn else ""
        check("le message dit que l'en-tete fait foi",
              "fait foi" in msg, "message=%r" % msg[:160])
        check("le message NE prescrit PLUS de changer l'en-tete",
              "Devrait etre" not in msg, "message=%r" % msg[:200])
        check("le message dit qu'un nom peut finir par 'u' sans etre une surcharge",
              "sans etre une surcharge" in msg, "message=%r" % msg[:220])

        # Non-regression : un vrai .dhpt de surcharge coherent ne declenche rien.
        shutil.rmtree(os.path.join(tmp, "ws"), ignore_errors=True)
        racine, impl = workspace(tmp, "divalto achat-venteu.dhpt",
                                 "xwin-s-projet      2.0")
        js, _ = audit(racine, impl)
        check("non-regression : nom en 'u' + en-tete de surcharge -> aucun constat",
              not constats(js, "convention-naming"),
              "constats=%s" % constats(js, "convention-naming"))

        # Non-regression : un .dhpt standard au nom ordinaire ne declenche rien.
        shutil.rmtree(os.path.join(tmp, "ws"), ignore_errors=True)
        racine, impl = workspace(tmp, "divalto achat-vente.dhpt", "xwin-projet        2.0")
        js, _ = audit(racine, impl)
        check("non-regression : nom ordinaire + en-tete standard -> aucun constat",
              not constats(js, "convention-naming"),
              "constats=%s" % constats(js, "convention-naming"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
