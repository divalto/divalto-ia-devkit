#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de parse_compilation.py contre des logs de compilation xwin7.

Les fixtures (tests/fixtures/*.txt) reproduisent le FORMAT REEL de xwin7 (capture sur
un vrai projet puis anonymisee : noms/chemins generiques, marqueurs de format reels).
1 fixture (#236 abandon) est reconstruite a partir des chaines verbatim de l'issue.

Lancer :
    py .claude/skills/compiling-diva-projects/tests/test_parse_compilation.py

Exit 0 = tous les verdicts attendus ; exit 1 = au moins un ecart.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARSER = os.path.join(HERE, "..", "scripts", "parse_compilation.py")
FIXTURES = os.path.join(HERE, "fixtures")

# Un fichier "compile" de plus de 2048 octets, stable et toujours present : sert de faux
# output valide pour les cas --check-outputs (le seuil est 2048B, 1024B = stub d'echec).
BIG_OUTPUT = os.path.abspath(PARSER)

# (fixture, args CLI supplementaires, exit attendu, assertions sur le JSON de sortie)
CASES = [
    ("build_ajour_success.txt", [], 0, {"success": True, "up_to_date": True}),
    ("buildall_success.txt", [], 0, {"success": True, "errors": 0}),
    ("echec_syntaxe.txt", [], 1, {"success": False, "min_errors": 1}),
    ("echec_mauvais_implicite_310.txt", [], 1, {"success": False, "other_errors": True}),
    ("echec_include_absent.txt", [], 1, {"success": False}),
    ("interrompu_ide.txt", [], 1, {"success": False, "build_incomplet": True}),
    ("interrompu_abandon_236.txt", [], 1, {"success": False, "build_incomplet": True}),

    # --- Regression : --check-outputs NE DOIT PAS surcharger le verdict ---
    # Le rattrapage est reserve au log REELLEMENT vide. Il rendait auparavant success:true
    # sur un build interrompu / un cas #310 sans ligne de resume (faux positif).
    ("interrompu_ide.txt", ["--check-outputs", BIG_OUTPUT], 1,
     {"success": False, "build_incomplet": True}),
    ("echec_mauvais_implicite_310.txt", ["--check-outputs", BIG_OUTPUT], 1,
     {"success": False, "other_errors": True}),
    ("echec_syntaxe.txt", ["--check-outputs", BIG_OUTPUT], 1, {"success": False}),
    # Cas legitime conserve : log vide + tous les outputs presents et valides = succes.
    ("log_vide.txt", ["--check-outputs", BIG_OUTPUT], 0, {"success": True}),
    # Log vide + output absent : diagnostic propre (jamais un traceback KeyError).
    ("log_vide.txt", ["--check-outputs", os.path.join(FIXTURES, "_absent.dhop")], 1,
     {"success": False}),

    # --- Regression : attribution du fichier source sur erreurs consecutives ---
    # Avant le fix, la 2e erreur heritait du fichier de la 1re (ligne precedente).
    ("deux_erreurs_fichiers.txt", [], 1,
     {"success": False, "source_files": ["premier.dhsp", "second.dhsp"]}),
    # Un nom DIVA peut contenir des ESPACES : il doit etre capture ENTIER.
    ("noms_avec_espaces.txt", [], 1,
     {"success": False, "source_files": ["gt_piece nouvellepiece.dhps"]}),
    # Une ligne de continuation " Fichier:... Erreur numero N" DECRIT l'erreur precedente :
    # elle ne doit PAS etre comptee comme une erreur de plus (compteur gonfle).
    ("erreur_avec_continuation.txt", [], 1,
     {"success": False, "exact_errors": 1, "source_files": ["monprojet.dhpt"]}),
]


def run(fixture, extra_args=()):
    r = subprocess.run(
        [sys.executable, PARSER, "--path", os.path.join(FIXTURES, fixture)] + list(extra_args),
        capture_output=True,
    )
    try:
        out = json.loads(r.stdout.decode("utf-8"))
    except Exception as e:
        out = {"_parse_error": str(e), "_stdout": r.stdout.decode("utf-8", "replace")[:200]}
    return r.returncode, out


def main():
    failures = 0
    for fixture, extra, want_exit, want in CASES:
        rc, o = run(fixture, extra)
        why = []
        if rc != want_exit:
            why.append(f"exit={rc} (attendu {want_exit})")
        if "success" in want and o.get("success") is not want["success"]:
            why.append(f"success={o.get('success')} (attendu {want['success']})")
        if want.get("up_to_date") and not o.get("up_to_date"):
            why.append("up_to_date manquant")
        if want.get("build_incomplet") and not o.get("build_incomplet"):
            why.append("build_incomplet manquant")
        if want.get("other_errors") and not o.get("other_errors"):
            why.append("other_errors manquant")
        if "errors" in want and o.get("summary", {}).get("errors") != want["errors"]:
            why.append(f"summary.errors={o.get('summary', {}).get('errors')} (attendu {want['errors']})")
        if "exact_errors" in want and len(o.get("errors", [])) != want["exact_errors"]:
            why.append(f"nb errors={len(o.get('errors', []))} (attendu exactement {want['exact_errors']})")
        if "min_errors" in want and len(o.get("errors", [])) < want["min_errors"]:
            why.append(f"nb errors={len(o.get('errors', []))} (attendu >= {want['min_errors']})")
        if "source_files" in want:
            got = [e.get("source_file") for e in o.get("errors", [])]
            if got != want["source_files"]:
                why.append(f"source_files={got} (attendu {want['source_files']})")
        ok = not why
        label = fixture + (" " + " ".join(
            os.path.basename(a) if os.sep in a else a for a in extra) if extra else "")
        print(("OK   " if ok else "FAIL ") + label + ("" if ok else "  -> " + " ; ".join(why)))
        failures += not ok
    print()
    print("=== " + ("TOUS OK" if failures == 0 else f"{failures} ECHEC(S)") + " ===")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
