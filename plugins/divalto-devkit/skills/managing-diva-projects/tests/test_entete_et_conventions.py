#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de validate_project.py -- en-tetes et regles de convention.

Deux defauts rejoues ici :

1. **PROJ04 / PROJ05 etaient structurellement inatteignables.** Le type du fichier etait
   deduit de `detect_file_type(lines)`, c'est-a-dire de l'EN-TETE que ces regles
   sont censees valider. `validate_dhps` (qui porte PROJ04) n'etait donc appele que si
   l'en-tete etait DEJA un en-tete de .dhps, ou son test ne peut jamais etre vrai.
   Un melange en-tete/extension etait invisible par construction : un `.dhps`
   portant `xwin-projet` repondait `valid: true` et se declarait `type: dhpt`.
   Le type vient desormais de l'EXTENSION, l'en-tete n'est plus que ce qu'on compare.

2. **PROJ09 etait une `error` "obligatoire".** `zdiva.dhsp` dans `[includes]` est une
   CONVENTION : le standard X.13 livre ne le fait JAMAIS (0 / 2304 `.dhps`) alors
   qu'un specifique le fait a 80-98 %. En `error` et active par defaut, la regle
   rendait `valid: false` sur 100 % des sous-projets du standard -- que l'on valide
   couramment comme modele de reference. Elle est hors jeu par defaut (`--with-rules`).

Lancer :
    py .claude/skills/managing-diva-projects/tests/run_all.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VALID = os.path.abspath(os.path.join(HERE, "..", "scripts", "validate_project.py"))

PROJET = ('[general]\nnom="p"\n[profildefaut]\n[profil]\nnom="x"\n'
          '[sousprojets]\n[projetsfusion]\n[fabricationmere]\n[communs]\nnom="g"\n[autres]\n')
SPROJET = ('[general]\n[communs]\nnom="g"\n[fichiers]\n[includes]\n'
           'fic="zdiva.dhsp"\n[autres]\n')
SPROJET_SANS_Z = ('[general]\n[communs]\nnom="g"\n[fichiers]\n[includes]\n'
                  'fic="autre.dhsp"\n[autres]\n')


def valide(path, *extra):
    """Lance validate_project.py. Retourne (valid, {codes}, type, type_entete, exit)."""
    r = subprocess.run([sys.executable, VALID, "--path", path] + list(extra),
                       capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    i = out.find("{")
    if i < 0:
        return None, set(), None, None, r.returncode
    js = json.loads(out[i:])
    codes = {e["rule"] for e in js.get("errors") or []}
    codes |= {w["rule"] for w in js.get("warnings") or []}
    return (js.get("valid"), codes, js.get("type"),
            js.get("type_annonce_par_entete"), r.returncode)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tmp = tempfile.mkdtemp(prefix="mdp_tests_")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    def f(nom, entete, corps):
        p = os.path.join(tmp, nom)
        with open(p, "wb") as fh:
            fh.write((entete + "\n" + corps).replace("\r\n", "\n")
                     .replace("\n", "\r\n").encode("iso-8859-1"))
        return p

    try:
        # ============ matrice en-tete x extension : UN code par extension ============
        MATRICE = [
            # (extension, en-tete,             code attendu ou None)
            (".dhpt", "xwin-projet        2.0", None),    # standard, correct
            (".dhpt", "xwin-s-projet      2.0", None),    # surcharge, correct
            (".dhpt", "xwin-sprojet       2.0", "PROJ05"),   # en-tete de SOUS-projet
            (".dhpt", "xwin-s-sprojet     2.0", "PROJ05"),   # sous-projet de surcharge
            (".dhps", "xwin-sprojet       2.0", None),    # standard, correct
            (".dhps", "xwin-s-sprojet     2.0", None),    # surcharge, correct
            (".dhps", "xwin-projet        2.0", "PROJ04"),   # en-tete de PROJET
            (".dhps", "xwin-s-projet      2.0", "PROJ04"),   # projet de surcharge
        ]
        for i, (ext, entete, attendu) in enumerate(MATRICE):
            corps = PROJET if ext == ".dhpt" else SPROJET
            p = f("m%d%s" % (i, ext), entete, corps)
            _, codes, _, _, _ = valide(p)
            obtenus = sorted(codes & {"PROJ04", "PROJ05"})
            check('matrice %s + "%s" -> %s'
                  % (ext, entete.split()[0], attendu or "aucun constat d'en-tete"),
                  obtenus == ([attendu] if attendu else []),
                  "attendu=%s obtenu=%s (tous: %s)"
                  % ([attendu] if attendu else [], obtenus, sorted(codes)))

        # --- le type annonce doit etre celui de l'EXTENSION, pas celui de l'en-tete ---
        p = f("melange.dhps", "xwin-projet        2.0", PROJET)
        valid, codes, typ, typ_ent, code_sortie = valide(p)
        check("un .dhps portant un en-tete de projet n'est plus valid=true",
              valid is False, "valid=%s codes=%s" % (valid, sorted(codes)))
        check("le champ `type` suit l'EXTENSION (.dhps), pas l'en-tete",
              typ == "dhps", "type=%s" % typ)
        check("le type annonce par l'en-tete est rapporte a part (dhpt)",
              typ_ent == "dhpt", "type_annonce_par_entete=%s" % typ_ent)
        check("exit code non nul quand le fichier est invalide",
              code_sortie == 1, "exit=%s" % code_sortie)

        # --- en-tete absent / non reconnu : constat structure, plus un exit brut ---
        p = f("bidon.dhps", "n'importe quoi", SPROJET)
        valid, codes, typ, typ_ent, code_sortie = valide(p)
        check("en-tete non reconnu -> PROJ04 dans le JSON (et non un exit sans sortie)",
              "PROJ04" in codes and typ == "dhps", "codes=%s type=%s" % (sorted(codes), typ))
        check("en-tete non reconnu -> type_annonce_par_entete = null",
              typ_ent is None, "type_annonce_par_entete=%s" % typ_ent)

        # --- extension non geree : erreur claire, exit 2 ---
        p = f("truc.txt", "xwin-sprojet       2.0", SPROJET)
        valid, codes, _, _, code_sortie = valide(p)
        check("extension non geree -> exit 2 (erreur interne, pas un verdict)",
              code_sortie == 2, "exit=%s" % code_sortie)

        # ============ PROJ09 : convention, hors jeu par defaut ============
        p = f("noz.dhps", "xwin-sprojet       2.0", SPROJET_SANS_Z)
        valid, codes, _, _, _ = valide(p)
        check("[PROJ09] zdiva.dhsp absent : MUETTE par defaut",
              "PROJ09" not in codes, "codes=%s" % sorted(codes))
        check("[PROJ09] et le fichier reste valide (ce n'est pas un defaut)",
              valid is True, "valid=%s codes=%s" % (valid, sorted(codes)))

        valid, codes, _, _, _ = valide(p, "--with-rules", "PROJ09")
        check("[PROJ09] --with-rules PROJ09 : l'absence est signalee",
              "PROJ09" in codes, "codes=%s" % sorted(codes))
        check("[PROJ09] --with-rules PROJ09 : signalee SANS rendre le fichier invalide",
              valid is True, "valid=%s" % valid)

        p2 = f("avecz.dhps", "xwin-sprojet       2.0", SPROJET)
        _, codes, _, _, _ = valide(p2, "--with-rules", "PROJ09")
        check("[PROJ09] --with-rules PROJ09 : presence -> muet",
              "PROJ09" not in codes, "codes=%s" % sorted(codes))

        # --- --with-rules AJOUTE, il ne FILTRE pas (contrairement au --rules du linter) ---
        p3 = f("melange2.dhps", "xwin-projet        2.0", SPROJET_SANS_Z)
        _, codes, _, _, _ = valide(p3, "--with-rules", "PROJ09")
        check("--with-rules AJOUTE au jeu normal : PROJ04 remonte toujours avec PROJ09",
              {"PROJ04", "PROJ09"} <= codes, "codes=%s" % sorted(codes))

        # --- un code hors REGLES_HORS_DEFAUT passe a --with-rules est ignore, pas fatal ---
        valid, codes, _, _, code_sortie = valide(p2, "--with-rules", "PROJ04")
        check("--with-rules avec un code deja actif : ignore, sans plantage",
              code_sortie == 0, "exit=%s codes=%s" % (code_sortie, sorted(codes)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
