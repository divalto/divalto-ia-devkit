#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lance les suites de tests du skill coding-diva-advanced.

Toutes les suites tournent PARTOUT : elles ne lisent que des fichiers du skill, sans
DLL, sans ERP installe, sans acces reseau. Aucun cas ne peut donc se declarer "non
applicable" -- si un cas ne s'execute pas, c'est un echec.

En particulier, la suite de syntaxe n'appelle PAS le MCP : elle verifie la concordance
entre la page reference/syntaxe-de-base.md et le releve reference/keywords-verifies.json.
L'interrogation du graphe est le travail de l'orchestrateur LLM (convention du plugin) ;
le test, lui, garde la trace ecrite honnete.

Lancer :
    py .claude/skills/coding-diva-advanced/tests/run_all.py

Exit 0 = toutes les suites passent ; exit 1 = au moins une suite en echec.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    "test_syntaxe_verifiee.py",
    "test_surcharge_verifiee.py",
    "test_recordsql_verifiee.py",
    "test_appels_programmes_verifiee.py",
    "test_log_anomalies_verifiee.py",
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
