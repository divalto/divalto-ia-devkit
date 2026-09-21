#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lance les suites de tests du skill reading-multichoix.

Les cas de contrat documentaire tournent partout. Les cas qui lisent un vrai
dictionnaire de multichoix exigent `DhxIsam64.dll` et un `.dhfi` : ils se declarent
**non applicables** (jamais "reussis") quand l'un des deux manque. Pour les activer :

    set MULTICHOIX_TEST_FILE=<chemin d'une COPIE d'un XXfdmc.dhfi>

Ne jamais pointer un fichier de production, meme si les scripts ne font que lire.

Lancer :
    py .claude/skills/reading-multichoix/tests/run_all.py

Exit 0 = toutes les suites passent ; exit 1 = au moins une suite en echec.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    "test_sortie_machine.py",
]


def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    if not os.environ.get("MULTICHOIX_TEST_FILE"):
        print("Note : MULTICHOIX_TEST_FILE non defini -- les cas sur fichier reel seront")
        print("       declares NON APPLICABLES (et non reussis).")
        print()

    failed = []
    for suite in SUITES:
        print("=" * 70)
        print("### " + suite)
        print("=" * 70)
        r = subprocess.run([sys.executable, os.path.join(HERE, suite)], capture_output=True)
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
        err = r.stderr.decode("utf-8", "replace").strip()
        if err:
            sys.stdout.write(err + "\n")
        if r.returncode != 0:
            failed.append(suite)
        print()

    print("=" * 70)
    if failed:
        print("BILAN : %d suite(s) en ECHEC -> %s" % (len(failed), ", ".join(failed)))
    else:
        print("BILAN : %d/%d suites OK" % (len(SUITES), len(SUITES)))
    print("=" * 70)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
