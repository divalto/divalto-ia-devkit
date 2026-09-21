#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables du linter -- faux positifs signales par les RETEX.

Un faux positif systematique fait ignorer le rapport entier : ces cas gardent les
corrections, ET les detections legitimes qu'elles ne doivent pas casser.

Lancer :
    py .claude/skills/linting-diva-code/tests/test_faux_positifs.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.abspath(os.path.join(HERE, "..", "scripts", "lint_diva.py"))


def lint(path, *extra):
    """Lance le linter. Retourne ({codes}, {code: severite}, sortie brute)."""
    r = subprocess.run([sys.executable, LINT, "--path", path] + list(extra),
                       capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    i = out.find("{")                      # le script prefixe une ligne "Analyse de ..."
    if i < 0:
        return set(), {}, out + r.stderr.decode("utf-8", "replace")
    try:
        js = json.loads(out[i:])
    except Exception as e:
        return set(), {}, "JSON illisible : %s / %s" % (e, out[:200])
    codes, sev = set(), {}
    for cle in ("errors", "warnings", "infos", "info"):
        for fnd in js.get(cle) or []:
            codes.add(fnd.get("rule"))
            sev[fnd.get("rule")] = fnd.get("severity")
    return codes, sev, out


def main():
    tmp = tempfile.mkdtemp(prefix="lint_tests_")
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

    PROJET = '\n[general]\nnom="p"\n[profildefaut]\n[profil]\n[sousprojets]\n[autres]\n'
    SPROJET = '\n[general]\n[communs]\n[fichiers]\n[includes]\nfic="zdiva.dhsp"\n[autres]\n'

    try:
        # ============ #293 + #307 : P04 rejette les en-tetes de SURCHARGE ============
        codes, _, _ = lint(f("surch.dhps", "xwin-s-sprojet     2.0" + SPROJET))
        check("[#293/#307] .dhps de surcharge (xwin-s-sprojet) : pas de P04",
              "P04" not in codes, "codes=%s" % sorted(codes))

        codes, _, _ = lint(f("surch.dhpt", "xwin-s-projet      2.0" + PROJET))
        check("[#307] .dhpt de surcharge (xwin-s-projet) : pas de P04",
              "P04" not in codes, "codes=%s" % sorted(codes))

        # --- detections legitimes a NE PAS casser ---
        codes, _, _ = lint(f("std.dhps", "xwin-sprojet       2.0" + SPROJET))
        check("non-regression : .dhps standard accepte", "P04" not in codes,
              "codes=%s" % sorted(codes))

        codes, _, _ = lint(f("std.dhpt", "xwin-projet        2.0" + PROJET))
        check("non-regression : .dhpt standard accepte", "P04" not in codes,
              "codes=%s" % sorted(codes))

        codes, _, _ = lint(f("mauvais.dhpt", "xwin-sprojet       2.0" + PROJET))
        check("non-regression : .dhpt portant un en-tete de .dhps -> P05 (vrai melange)",
              "P05" in codes, "codes=%s" % sorted(codes))

        codes, _, _ = lint(f("bidon.dhpt", "n'importe quoi" + PROJET))
        check("non-regression : .dhpt en-tete invalide -> P05", "P05" in codes,
              "codes=%s" % sorted(codes))

        codes, _, _ = lint(f("bidon.dhps", "n'importe quoi" + SPROJET))
        check("non-regression : .dhps en-tete invalide -> P04", "P04" in codes,
              "codes=%s" % sorted(codes))

        # --- matrice COMPLETE en-tete x type de fichier (blindage) ---
        # Un en-tete valide pour un type ne doit JAMAIS etre accepte pour l'autre.
        # UN SEUL code par extension : P04 pour le .dhps, P05 pour le .dhpt. Un .dhpt
        # mal en-tete remontait auparavant P04 ET P05 -- deux constats pour un defaut.
        MATRICE = [
            # (extension, en-tete,             code attendu ou None)
            ('.dhpt', 'xwin-projet        2.0', None),    # standard, correct
            ('.dhpt', 'xwin-s-projet      2.0', None),    # surcharge, correct
            ('.dhpt', 'xwin-sprojet       2.0', 'P05'),   # en-tete de SOUS-projet -> refus
            ('.dhpt', 'xwin-s-sprojet     2.0', 'P05'),   # sous-projet surcharge -> refus
            ('.dhps', 'xwin-sprojet       2.0', None),    # standard, correct
            ('.dhps', 'xwin-s-sprojet     2.0', None),    # surcharge, correct
            ('.dhps', 'xwin-projet        2.0', 'P04'),   # en-tete de PROJET -> refus
            ('.dhps', 'xwin-s-projet      2.0', 'P04'),   # projet surcharge -> refus
        ]
        for i, (ext, entete, attendu) in enumerate(MATRICE):
            corps = PROJET if ext == '.dhpt' else SPROJET
            codes, _, _ = lint(f('matrice_%d%s' % (i, ext), entete + corps))
            entete_codes = sorted(codes & {'P04', 'P05'})
            check('matrice %s + "%s" -> %s' % (ext, entete.split()[0],
                                               attendu or 'aucun constat d\'en-tete'),
                  entete_codes == ([attendu] if attendu else []),
                  'attendu=%s obtenu=%s (tous: %s)'
                  % ([attendu] if attendu else [], entete_codes, sorted(codes)))

        # tolerances du motif ancre : espaces de tete et casse
        codes, _, _ = lint(f('espaces.dhps', '   xwin-s-sprojet   2.0' + SPROJET))
        check('espaces de tete toleres', 'P04' not in codes, 'codes=%s' % sorted(codes))
        codes, _, _ = lint(f('casse.dhps', 'XWIN-S-SPROJET     2.0' + SPROJET))
        check('en-tete insensible a la casse', 'P04' not in codes, 'codes=%s' % sorted(codes))

        # ====== #243 : CI01 (SetModuleInfo) = audit de convention, HORS jeu par defaut ==
        # SetModuleInfo n'est PAS obligatoire : son absence ne produit aucune erreur de
        # compilation. Elle a en revanche un effet A L'EXECUTION -- l'information est lue
        # par ModuleInfo, et Divalto s'en sert pour afficher la version du module. Le
        # standard la pose systematiquement, le specifique est libre. Donc : muette par
        # defaut, activable par --rules CI01.
        MARQ = "SetModuleInfo('$Id: m.dhsf 127012 2021-11-15 17:10:00Z als $')"
        BOURRE = "\n".join('libelle%d="x"' % i for i in range(150))
        # masque dont le bloc [diva] (et donc le marqueur) arrive APRES la ligne 100
        MASQUE_OK = "[masque]\nnb_col=80\n" + BOURRE + "\n[diva]\n" + MARQ + "\n[autres]\n"
        MASQUE_SANS = "[masque]\nnb_col=80\n" + BOURRE + "\n[diva]\n[autres]\n"
        CODE_SANS = "; module sans SetModuleInfo\nProc Test()\nFinproc\n"
        CODE_OK = MARQ + "\nProc Test()\nFinproc\n"

        for nom, contenu in (("d_impr.dhsi", MASQUE_SANS), ("d_ecr.dhsf", MASQUE_SANS),
                             ("d_code.dhsp", CODE_SANS), ("d_rsql.dhsq", CODE_SANS)):
            codes, _, _ = lint(f(nom, contenu))
            check("[#243] %-12s sans marqueur : CI01 MUETTE par defaut" % nom,
                  "CI01" not in codes, "codes=%s" % sorted(codes))

        # --- activee explicitement : la fenetre de recherche doit etre juste ---
        codes, sev, _ = lint(f("o_impr.dhsi", MASQUE_OK), "--rules", "CI01")
        check("[#243] --rules CI01 : .dhsi dont le marqueur est APRES la ligne 100 -> muet",
              "CI01" not in codes, "codes=%s (fenetre 100 lignes non corrigee)" % sorted(codes))

        codes, sev, _ = lint(f("o_ecr.dhsf", MASQUE_OK), "--rules", "CI01")
        check("[#243] --rules CI01 : .dhsf dont le marqueur est APRES la ligne 100 -> muet",
              "CI01" not in codes, "codes=%s (fenetre 100 lignes non corrigee)" % sorted(codes))

        codes, sev, _ = lint(f("k_impr.dhsi", MASQUE_SANS), "--rules", "CI01")
        check("--rules CI01 : masque reellement sans marqueur -> signale en `info`",
              codes == {"CI01"} and sev.get("CI01") == "info",
              "codes=%s sev=%s" % (sorted(codes), sev))

        codes, sev, _ = lint(f("k_code.dhsp", CODE_SANS), "--rules", "CI01")
        check("--rules CI01 : .dhsp sans marqueur -> signale",
              "CI01" in codes, "codes=%s" % sorted(codes))

        codes, _, _ = lint(f("o_code.dhsp", CODE_OK), "--rules", "CI01")
        check("--rules CI01 : .dhsp avec marqueur en tete -> muet (fenetre code intacte)",
              "CI01" not in codes, "codes=%s" % sorted(codes))

        codes, _, _ = lint(f("court.dhsp", "SetModuleInfo('$Id$')\nProc T()\nFinproc\n"),
                           "--rules", "CI01")
        check("--rules CI01 : mot-cle SVN non substitue ($Id$ nu, < 30 car.) -> signale",
              "CI01" in codes, "codes=%s" % sorted(codes))

        # ====== P09 : zdiva.dhsp dans [includes] = convention, HORS jeu par defaut ======
        # Le standard X.13 livre ne met JAMAIS zdiva.dhsp dans les [includes] de ses
        # sous-projets (0 / 2304 .dhps mesures) alors qu'un specifique le fait a 80-98 %.
        # Active par defaut, la regle remonte 100 % des sous-projets du standard -- or
        # linter un .dhps standard comme MODELE DE REFERENCE est un usage courant.
        SANS_Z = '\n[general]\n[fichiers]\n[includes]\nfic="autre.dhsp"\n[autres]\n'
        AVEC_Z = '\n[general]\n[fichiers]\n[includes]\nfic="zdiva.dhsp"\n[autres]\n'

        codes, _, _ = lint(f('p09_def.dhps', 'xwin-sprojet       2.0' + SANS_Z))
        check('[P09] .dhps sans zdiva.dhsp : MUETTE par defaut',
              'P09' not in codes, 'codes=%s' % sorted(codes))

        codes, sev, _ = lint(f('p09_on.dhps', 'xwin-sprojet       2.0' + SANS_Z),
                             '--rules', 'P09')
        check('[P09] --rules P09 : absence signalee en `info`',
              codes == {'P09'} and sev.get('P09') == 'info',
              'codes=%s sev=%s' % (sorted(codes), sev))

        codes, _, _ = lint(f('p09_ok.dhps', 'xwin-sprojet       2.0' + AVEC_Z),
                           '--rules', 'P09')
        check('[P09] --rules P09 : presence -> muet (detection legitime preservee)',
              'P09' not in codes, 'codes=%s' % sorted(codes))
        # --- le mecanisme hors-defaut ne doit pas avoir desactive les AUTRES regles ---
        codes, _, _ = lint(f("vraidefaut.dhsp", 's = "a" + "b"\n'))
        check("garde-fou mecanisme : les regles normales restent actives par defaut (S01)",
              "S01" in codes, "codes=%s" % sorted(codes))

        codes, _, _ = lint(f("vraidefaut2.dhsp", "Proc T()\nForEach x\nFinproc\n"))
        check("garde-fou mecanisme : L01 (ForEach) toujours actif par defaut",
              "L01" in codes, "codes=%s" % sorted(codes))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
