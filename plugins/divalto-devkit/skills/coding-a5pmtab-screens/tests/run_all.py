#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lance les suites de tests du skill coding-a5pmtab-screens.

Aucun prerequis : pas de DLL, pas d'ERP installe, pas de reseau, pas de MCP. Les suites ne
lisent que les fichiers du skill. Un cas qui ne s'execute pas est un echec, jamais un
"non applicable".

Ce que les suites garantissent : les pages et le releve date concordent -- y compris sur les
CHIFFRES, et y compris sur ce que le skill declare **ne pas** savoir. Ce qu'elles ne
garantissent pas : que le releve soit a jour. Cela se refait a la main, en rejouant les
requetes contre le graphe et en relisant les sources livrees.

Lancer :
    py .claude/skills/coding-a5pmtab-screens/tests/run_all.py

Exit 0 = toutes les suites passent ; exit 1 = au moins une suite en echec.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    "test_a5pmtab_verifiee.py",
]


def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

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
