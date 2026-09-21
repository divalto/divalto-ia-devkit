#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables des 3 regles ajoutees (solde).

- **S11** (#274) -- une procedure/fonction locale appelee avant sa definition, **sans
  `Proto`**. La contrainte est reelle : *« pour qu'une fonction/procedure puisse etre
  utilisee, il faut qu'elle soit prealablement declaree »* (Manuel de reference DIVA,
  « Les prototypes »), et `Proto ... EndProto` existe exactement pour la lever. Mesure
  sur le standard X.13 : **37 appels anticipes, TOUS prototypes, aucun sans**.

- **S12** (#198) -- ligne **physique** > 251 caracteres : la compilation passe mais
  l'editeur XWin **refuse d'ouvrir** le fichier. Portee `.dhsp` / `.dhsf` seulement --
  les `.dhpt` en sont exclus **sur preuve contraire** (le standard livre contient une
  ligne `filtres=` de 282 caracteres dans `divalto modules communs.dhpt`, qui marche).

- **E18** (#348) -- les positions hors normes sont desormais **nommees avec leur
  numero de ligne** dans un constat unique. Un constat par position aurait fait 20
  lignes de rapport sur un masque qui en compte 20 ; la question posee est « la position
  que je viens d'ajouter fait-elle partie des fautives ? », et une liste y repond.

Lancer :
    py .claude/skills/linting-diva-code/tests/run_all.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.abspath(os.path.join(HERE, "..", "scripts", "lint_diva.py"))


def lint(path):
    """Retourne ({codes}, [constats]) du linter sur ce fichier."""
    r = subprocess.run([sys.executable, LINT, "--path", path], capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    i = out.find("{")
    if i < 0:
        return set(), []
    js = json.loads(out[i:])
    tous = []
    for cle in ("errors", "warnings", "infos"):
        tous += js.get(cle) or []
    return {f["rule"] for f in tous}, tous


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tmp = tempfile.mkdtemp(prefix="sc005_")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    def f(nom, contenu):
        p = os.path.join(tmp, nom)
        with open(p, "wb") as fh:
            fh.write(contenu.replace("\r\n", "\n").replace("\n", "\r\n").encode("iso-8859-1"))
        return p

    try:
        # ===================== S11 : appel avant definition =====================
        AVANT = ("Procedure Point_Entree\n"
                 "BeginP\n"
                 "    Calculer_Marge(True)\n"
                 "EndP\n"
                 "Procedure Calculer_Marge(flag)\n"
                 "BeginP\n"
                 "EndP\n")
        codes, _ = lint(f("s11_sans_proto.dhsp", AVANT))
        check("[S11] appel ligne 3, definition ligne 5, sans Proto -> signale",
              "S11" in codes, "codes=%s" % sorted(codes))

        AVEC = ("Proto Procedure Calculer_Marge(flag)\n"
                "  flag B\n"
                "EndProto\n" + AVANT)
        codes, _ = lint(f("s11_avec_proto.dhsp", AVEC))
        check("[S11] le meme code avec un Proto prealable -> muet",
              "S11" not in codes, "codes=%s" % sorted(codes))

        APRES = ("Procedure Calculer_Marge(flag)\n"
                 "BeginP\n"
                 "EndP\n"
                 "Procedure Point_Entree\n"
                 "BeginP\n"
                 "    Calculer_Marge(True)\n"
                 "EndP\n")
        codes, _ = lint(f("s11_ordre_ok.dhsp", APRES))
        check("[S11] definition avant l'appel -> muet",
              "S11" not in codes, "codes=%s" % sorted(codes))

        # Le faux positif REEL rencontre en mettant la regle au point : un commentaire
        # de MILIEU de ligne contenant `mot (` ressemble a un appel.
        COMMENT = ("Structure X\n"
                   "    1 totflg    B    ;a totaliser (sous total, total, coef)\n"
                   "EndStructure\n"
                   "Procedure Totaliser(IdlAxe)\n"
                   "BeginP\n"
                   "EndP\n")
        codes, _ = lint(f("s11_commentaire.dhsp", COMMENT))
        check("[S11] `;a totaliser (...)` en commentaire de milieu de ligne -> muet",
              "S11" not in codes,
              "codes=%s (commentaire pris pour un appel)" % sorted(codes))

        # Une fonction est traitee comme une procedure
        FONC = ("Procedure P\nBeginP\n    x = Convertir(1)\nEndP\n"
                "Function Int Convertir(v)\nBeginF\n    FReturn 0\nEndF\n")
        codes, _ = lint(f("s11_fonction.dhsp", FONC))
        check("[S11] s'applique aussi a une Function appelee avant sa definition",
              "S11" in codes, "codes=%s" % sorted(codes))

        # Un appel qualifie par un module n'est PAS un appel local
        MODULE = ("Procedure P\nBeginP\n    GTUZ000.Calculer_Marge(True)\nEndP\n"
                  "Procedure Calculer_Marge(flag)\nBeginP\nEndP\n")
        codes, _ = lint(f("s11_module.dhsp", MODULE))
        check("[S11] appel qualifie `Module.Proc()` -> pas un appel local, muet",
              "S11" not in codes, "codes=%s" % sorted(codes))

        # ===================== S12 : ligne > 251 caracteres =====================
        LONGUE = "Procedure P\nBeginP\n    s = \"" + ("A" * 260) + "\"\nEndP\n"
        codes, constats = lint(f("s12_longue.dhsp", LONGUE))
        check("[S12] .dhsp avec une ligne de plus de 251 caracteres -> signale",
              "S12" in codes, "codes=%s" % sorted(codes))
        s12 = [c for c in constats if c["rule"] == "S12"]
        check("[S12] le constat porte le bon numero de ligne et la longueur",
              s12 and s12[0]["line"] == 3 and "270" in s12[0]["message"],
              "constat=%s" % (s12[0] if s12 else None))

        codes, _ = lint(f("s12_limite.dhsp",
                          "Procedure P\nBeginP\n    s = \"" + ("A" * 240) + "\"\nEndP\n"))
        check("[S12] une ligne sous la limite -> muet",
              "S12" not in codes, "codes=%s" % sorted(codes))

        MASQUE = "[masque]\nnb_col=80\n[page]\nlibelle=\"" + ("B" * 260) + "\"\n[autres]\n"
        codes, _ = lint(f("s12_masque.dhsf", MASQUE))
        check("[S12] s'applique aussi aux masques .dhsf",
              "S12" in codes, "codes=%s" % sorted(codes))

        # PREUVE CONTRAIRE : le standard livre a une ligne `filtres=` de 282 caracteres
        # dans un .dhpt qui fonctionne -> la limite ne s'applique PAS aux fichiers projet.
        PROJ = ('xwin-projet        2.0\n[general]\nnom="p"\nfiltres="'
                + ("x" * 280) + '"\n[profildefaut]\n[profil]\nnom="x"\n'
                '[sousprojets]\n[projetsfusion]\n[fabricationmere]\n[autres]\n')
        codes, _ = lint(f("s12_projet.dhpt", PROJ))
        check("[S12] .dhpt HORS portee (preuve contraire du standard) -> muet",
              "S12" not in codes, "codes=%s" % sorted(codes))

        # ===================== E18 : nommer les lignes fautives =====================
        E18M = ("[masque]\nnb_col=80\n[page]\n"
                " [groupbox]\n  [presentation]\n   position=5,5\n"
                " [groupbox]\n  [presentation]\n   position=10,19\n"
                " [groupbox]\n  [presentation]\n   position=12,28\n"
                "[autres]\n")
        codes, constats = lint(f("e18.dhsf", E18M))
        e18 = [c for c in constats if c["rule"] == "E18"]
        check("[E18] un seul constat, pas un par position fautive",
              len(e18) == 1, "%d constats" % len(e18))
        check("[E18] le constat nomme les lignes fautives",
              e18 and "L9" in e18[0]["message"] and "L12" in e18[0]["message"],
              "message=%r" % (e18[0]["message"] if e18 else None))
        check("[E18] le constat est ancre sur une vraie ligne (plus `line: 0`)",
              e18 and e18[0]["line"] > 0, "line=%s" % (e18[0]["line"] if e18 else None))

        E18OK = ("[masque]\nnb_col=80\n[page]\n"
                 " [groupbox]\n  [presentation]\n   position=5,5\n"
                 " [groupbox]\n  [presentation]\n   position=10,10\n"
                 "[autres]\n")
        codes, _ = lint(f("e18_ok.dhsf", E18OK))
        check("[E18] toutes les positions canoniques -> muet",
              "E18" not in codes, "codes=%s" % sorted(codes))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
