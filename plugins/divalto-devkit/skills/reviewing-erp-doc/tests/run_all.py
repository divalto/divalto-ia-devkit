#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lance les 2 suites de tests du skill reviewing-erp-doc.

Aucun ERP, aucune base SQL, aucune dependance externe : les detecteurs consomment un IR
en JSON, et la fixture en fournit un vrai (cf. tests/README.md). `ingest_deliverable.py`
n'est pas couvert -- il exige `pyyaml`.

Lancer :
    py .claude/skills/reviewing-erp-doc/tests/run_all.py

Exit 0 = toutes les suites passent ; exit 1 = au moins une suite en echec.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    "test_detecteurs.py",
    "test_e4_heuristiques.py",
]


def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    echecs = []
    for suite in SUITES:
        print("=" * 70)
        print("### " + suite)
        print("=" * 70)
        r = subprocess.run([sys.executable, os.path.join(HERE, suite)],
                           capture_output=True)
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
        err = r.stderr.decode("utf-8", "replace").strip()
        if err:
            sys.stdout.write(err + "\n")
        if r.returncode != 0:
            echecs.append(suite)
        print()

    print("=" * 70)
    if echecs:
        print("BILAN : %d suite(s) en ECHEC -> %s" % (len(echecs), ", ".join(echecs)))
    else:
        print("BILAN : %d/%d suites OK" % (len(SUITES), len(SUITES)))
    print("=" * 70)
    sys.exit(1 if echecs else 0)


if __name__ == "__main__":
    main()
