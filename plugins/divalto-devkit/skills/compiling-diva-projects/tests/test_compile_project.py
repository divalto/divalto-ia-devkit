#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de compile_project.py (aucun xwin7 requis).

Deux niveaux, tous deux hors poste Divalto :
  - fonctions pures importees (parse_util, resolve_user, parse_profiles, generate_ps1) ;
  - CLI en `--no-execute` / `--list-profiles`, qui s'arrete AVANT de lancer xwin7.

Les `.dhpt` sont fabriques dans un dossier temporaire (ISO-8859-1 + CRLF) : rien n'est
ecrit dans le depot, et aucun binaire Divalto n'est requis.

Lancer :
    py .claude/skills/compiling-diva-projects/tests/test_compile_project.py

Exit 0 = tous les comportements attendus ; exit 1 = au moins un ecart.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
SCRIPT = os.path.join(SCRIPTS, "compile_project.py")
sys.path.insert(0, SCRIPTS)

import compile_project as cp          # noqa: E402
import parse_compilation              # noqa: E402

PROFIL_ACCENT = "d\xe9veloppement"     # 'developpement' avec e accent aigu


def write_iso(path, text):
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("iso-8859-1")
    with open(path, "wb") as f:
        f.write(data)


def dhpt(profils, util=None):
    out = ["xwin-projet        2.0", "[general]", 'nom="projet test"']
    if util:
        out.append('util="' + util + '"')
    out.append("[profildefaut]")
    for p in profils:
        out += ["[profil]", 'nom="' + p + '"', 'implicites="impl.txt"']
    out += ["[sousprojets]", "[autres]", ""]
    return "\n".join(out)


def run(args):
    r = subprocess.run([sys.executable, SCRIPT] + args, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    try:
        js = json.loads(out)
    except Exception:
        js = None
    return r.returncode, js, out + err


def main():
    tmp = tempfile.mkdtemp(prefix="compileproj_tests_")
    failures = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            failures.append(label)

    try:
        p_accent = os.path.join(tmp, "projet.dhpt")
        write_iso(p_accent, dhpt([PROFIL_ACCENT], util="UTILDHPT"))
        p_multi = os.path.join(tmp, "multi.dhpt")
        write_iso(p_multi, dhpt(["profA", "profB"]))
        p_nouti = os.path.join(tmp, "sansutil.dhpt")
        write_iso(p_nouti, dhpt(["profA"]))

        # ================= fonctions pures =================
        check("parse_util lit util= du .dhpt (#235)",
              cp.parse_util(Path(p_accent)) == "UTILDHPT",
              repr(cp.parse_util(Path(p_accent))))
        check("parse_util : absent -> None", cp.parse_util(Path(p_nouti)) is None)
        check("parse_profiles lit les profils",
              cp.parse_profiles(Path(p_multi)) == ["profA", "profB"],
              repr(cp.parse_profiles(Path(p_multi))))
        check("parse_profiles conserve l'accent du profil",
              cp.parse_profiles(Path(p_accent)) == [PROFIL_ACCENT])

        # --- #235 : ordre --user > util= > X_USER > USERNAME ---
        check("resolve_user : --user prioritaire",
              cp.resolve_user("CLI", "UTILDHPT") == "CLI")
        check("resolve_user : util= du .dhpt avant les fallbacks poste",
              cp.resolve_user(None, "UTILDHPT") == "UTILDHPT")
        old_x, old_u = os.environ.get("X_USER"), os.environ.get("USERNAME")
        try:
            os.environ["X_USER"] = "ENVUSER"
            check("resolve_user : X_USER non vide -> None (xwin7 la lit lui-meme)",
                  cp.resolve_user(None, None) is None)
            os.environ["X_USER"] = ""
            os.environ["USERNAME"] = "WINUSER"
            check("resolve_user : dernier repli sur USERNAME",
                  cp.resolve_user(None, None) == "WINUSER")
        finally:
            for k, v in (("X_USER", old_x), ("USERNAME", old_u)):
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        # --- #301 : le cwd est DERIVE de --xwin7-path ---
        ps1 = cp.generate_ps1(xwin7_path="K:\\Divalto\\Sys\\xwin7.exe", action="build",
                              project=p_accent, profile=PROFIL_ACCENT,
                              log_path="K:\\log.txt", stdout_path="K:\\o.txt",
                              stderr_path="K:\\e.txt", user="U")
        check("#301 : Set-Location derive du dossier de --xwin7-path",
              "Set-Location 'K:\\Divalto\\Sys'" in ps1, ps1.splitlines()[1][:70])
        check("#301 : plus de C:\\divalto\\sys code en dur",
              "C:\\divalto\\sys" not in ps1)
        check("le .ps1 propage le code de sortie xwin7",
              "exit $proc.ExitCode" in ps1)
        check("-user est passe a xwin7 quand il est resolu", "-user U" in ps1)

        ps1b = cp.generate_ps1(xwin7_path="C:\\d\\xwin7.exe", action="buildall",
                               project=p_accent, profile=PROFIL_ACCENT, log_path="l.txt",
                               stdout_path="o.txt", stderr_path="e.txt",
                               sousproject="mon sousprojet.dhps", source_basename="fic.dhsf")
        check("-sousproject et -source repercutes dans l'ArgumentList",
              '-sousproject "mon sousprojet.dhps"' in ps1b and '-source "fic.dhsf"' in ps1b)

        # --- le .ps1 doit etre ecrit en ISO-8859-1 (octet 0xE9, pas 0xC3 0xA9) ---
        ps1_path = Path(tmp) / "r005.ps1"
        cp.write_iso(ps1_path, ps1)
        raw = ps1_path.read_bytes()
        check("profil accentue ecrit en ISO-8859-1 (0xE9)",
              b"\xe9" in raw and b"\xc3\xa9" not in raw)
        check("le .ps1 est en CRLF", raw.count(b"\n") == raw.count(b"\r\n"))

        # --- delegation du verdict : source unique ---
        check("le verdict est delegue a parse_compilation (meme module)",
              cp.parse_compilation is parse_compilation)

        # ================= CLI =================
        rc, js, txt = run(["--project", p_multi, "--list-profiles"])
        check("--list-profiles retourne les profils",
              rc == 0 and js is not None and js.get("profiles") == ["profA", "profB"],
              "rc=%s" % rc)

        rc, js, txt = run(["--project", p_multi, "--profile", "inconnu",
                           "--log-path", os.path.join(tmp, "l.txt")])
        check("profil absent : echec AVANT xwin7, en listant les profils",
              rc == 1 and "profA" in txt, "rc=%s" % rc)

        rc, js, txt = run(["--project", os.path.join(tmp, "absent.dhpt"),
                           "--profile", "p", "--log-path", "l.txt"])
        check("--project introuvable : echec propre",
              rc == 1 and "Traceback" not in txt, "rc=%s" % rc)

        rc, js, txt = run(["--project", os.path.join(tmp, "masource.dhsp"),
                           "--profile", "p", "--log-path", "l.txt"])
        check("--project sans extension .dhpt : echec propre",
              rc == 1 and "Traceback" not in txt, "rc=%s" % rc)

        rc, js, txt = run(["--project", p_accent, "--profile", PROFIL_ACCENT,
                           "--log-path", os.path.join(tmp, "l.txt"),
                           "--source", "fic.dhsf", "--no-execute"])
        check("--source sans --sousproject : refus (couplage xwin7 obligatoire)",
              rc == 1 and "sousproject" in txt, "rc=%s" % rc)

        # --- --no-execute : le .ps1 est produit, xwin7 n'est jamais lance ---
        log = os.path.join(tmp, "run", "compil.txt")
        rc, js, txt = run(["--project", p_accent, "--profile", PROFIL_ACCENT,
                           "--log-path", log, "--action", "buildall", "--no-execute"])
        check("--no-execute : exit 3 et JSON de contrat",
              rc == 3 and js is not None and js.get("executed") is False, "rc=%s" % rc)
        if js:
            check("--no-execute : action repercutee", js.get("action") == "buildall")
            gen = Path(js["ps1_script"]).read_bytes()
            check("le .ps1 genere est en ISO-8859-1 (profil accentue)",
                  b"\xe9" in gen and b"\xc3\xa9" not in gen)
            check("#235 : util= du .dhpt utilise sans --user",
                  b"-user UTILDHPT" in gen)

        # --- #235 : --user qui contredit util= doit AVERTIR ---
        rc, js, txt = run(["--project", p_accent, "--profile", PROFIL_ACCENT,
                           "--log-path", log, "--user", "AUTRE", "--no-execute"])
        check("#235 : --user divergent du util= -> avertissement",
              rc == 3 and "WARN" in txt and "util=" in txt, "rc=%s" % rc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not failures else "%d ECHEC(S)" % len(failures)) + " ===")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
