#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lance les 3 suites de tests du skill compiling-diva-projects.

Aucun xwin7 ni poste Divalto requis (cf. tests/README.md).

Lancer :
    py .claude/skills/compiling-diva-projects/tests/run_all.py

Exit 0 = toutes les suites passent ; exit 1 = au moins une suite en echec.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    "test_parse_compilation.py",
    "test_generate_harness.py",
    "test_compile_project.py",
]


def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    failed = []
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
