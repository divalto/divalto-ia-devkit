#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables -- une surcharge se reconnait a son EN-TETE, jamais a son nom.

Le suffixe `u` d'un nom de fichier est une **convention de nommage**, pas un
marqueur. Mesure sur un corpus reel de 2513 entrees `[sousprojets]` : le test
`stem.endswith("u")` produisait **31 faux positifs et zero vrai positif** -- il
flaguait tout mot finissant par la lettre `u` :

    gt_menu.dhps  a5_menu.dhps  pp_menu.dhps  cc_commun menu.dhps
    rc_cpt_bordereau.dhps  gt_transport bordereau.dhps
    pp_zoom individu.dhps  rh_prg competence individu.dhps
    wm_rf saisie complement lieu.dhps  gt_zoom stat revente fou.dhps
    dmc_cbn_budget_niveau.dhps  gt_dau.dhps  ...visu.dhps

Dont **30 noms figurant dans des `.dhpt` du standard livre**. Deux consequences,
rejouees ici :

1. **`validate_project.py` (PROJ17, `error`)** declarait ces `.dhpt` du standard
   **invalides** pour une surcharge inexistante.
2. **`add_to_project.py` REFUSAIT l'ecriture** (exit 1) : impossible d'enregistrer
   `gt_menu.dhps` dans un projet. Un refus bloque le travail, la ou un faux constat
   ne fait que fatiguer.

Le comble : un commentaire situe trois lignes plus loin dans `validate_project.py`
avertissait deja de ce piege exact -- « detection par en-tete (autoritaire), pas par
suffixe 'u' (qui produirait des faux positifs : menu.dhps, bureau.dhps...) ».

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
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
VALID = os.path.join(SCRIPTS, "validate_project.py")
ADD = os.path.join(SCRIPTS, "add_to_project.py")

DHPS_STD = 'xwin-sprojet       2.0\n[general]\n[fichiers]\n[includes]\n[autres]\n'
DHPS_SURCH = 'xwin-s-sprojet     2.0\n[general]\n[fichiers]\n[includes]\n[autres]\n'


def ecrire(path, contenu):
    with open(path, "wb") as fh:
        fh.write(contenu.replace("\r\n", "\n").replace("\n", "\r\n").encode("iso-8859-1"))
    return path


def dhpt(sousprojets):
    lignes = ["xwin-projet        2.0", "[general]", 'nom="p"', "[profildefaut]",
              "[profil]", 'nom="x"', "[sousprojets]"]
    lignes += ['fic="%s"," "' % s for s in sousprojets]
    lignes += ["[projetsfusion]", "[fabricationmere]", "[communs]", 'nom="g"', "[autres]", ""]
    return "\n".join(lignes)


def lance(script, *args):
    """Retourne (dict, exit). En cas d'erreur, add_to_project ecrit sur STDERR
    (`Erreur : ...`) et non en JSON : on la recupere sous la cle "error" pour
    que les cas puissent l'inspecter."""
    r = subprocess.run([sys.executable, script] + list(args), capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace").strip()
    i = out.find("{")
    if i >= 0:
        return json.loads(out[i:]), r.returncode
    return ({"error": err} if err else {}), r.returncode


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tmp = tempfile.mkdtemp(prefix="mdp_surch_")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    try:
        # Les 3 .dhps du decor : un nom qui FINIT par 'u' sans etre une surcharge,
        # une vraie surcharge, et un nom ordinaire.
        ecrire(os.path.join(tmp, "gt_menu.dhps"), DHPS_STD)         # men-u : PAS une surcharge
        ecrire(os.path.join(tmp, "rc_bordereau.dhps"), DHPS_STD)    # bordere-au : idem
        ecrire(os.path.join(tmp, "basu.dhps"), DHPS_SURCH)          # VRAIE surcharge
        ecrire(os.path.join(tmp, "gt_article.dhps"), DHPS_STD)      # nom ordinaire

        # ================= PROJ17 dans validate_project.py =================
        p = ecrire(os.path.join(tmp, "std.dhpt"),
                   dhpt(["gt_menu.dhps", "rc_bordereau.dhps", "gt_article.dhps"]))
        js, code = lance(VALID, "--path", p)
        codes = {e["rule"] for e in js.get("errors") or []}
        check("[PROJ17] 3 sous-projets standard dont 2 finissant par 'u' : aucun PROJ17",
              "PROJ17" not in codes, "codes=%s" % sorted(codes))
        check("[PROJ17] et le .dhpt est declare valide",
              js.get("valid") is True and code == 0,
              "valid=%s exit=%s errors=%s" % (js.get("valid"), code, js.get("errors")))

        p = ecrire(os.path.join(tmp, "avec_surcharge.dhpt"),
                   dhpt(["gt_article.dhps", "basu.dhps"]))
        js, code = lance(VALID, "--path", p)
        codes = {e["rule"] for e in js.get("errors") or []}
        check("[PROJ17] une VRAIE surcharge (en-tete xwin-s-sprojet) reste signalee",
              "PROJ17" in codes, "codes=%s" % sorted(codes))
        msgs = " ".join(e["message"] for e in js.get("errors") or [])
        check("[PROJ17] le message nomme l'en-tete, pas le suffixe",
              "xwin-s-sprojet" in msgs and "suffixe" not in msgs.lower(),
              "message=%r" % msgs[:150])

        p = ecrire(os.path.join(tmp, "absent.dhpt"), dhpt(["jamais_creeu.dhps"]))
        js, code = lance(VALID, "--path", p)
        codes = {e["rule"] for e in js.get("errors") or []}
        check("[PROJ17] .dhps referencee INTROUVABLE : on se tait (on ne peut pas savoir)",
              "PROJ17" not in codes, "codes=%s" % sorted(codes))

        # ================= le garde-fou de add_to_project.py =================
        base = ecrire(os.path.join(tmp, "cible.dhpt"), dhpt(["gt_article.dhps"]))

        js, code = lance(ADD, "--dhpt", base, "--dhps", "gt_menu.dhps",
                         "--output", os.path.join(tmp, "out1.dhpt"))
        check("[add] ajouter 'gt_menu.dhps' (men-u, standard) : ACCEPTE",
              code == 0 and "error" not in js,
              "exit=%s error=%r" % (code, js.get("error")))
        check("[add] et aucun avertissement (le fichier a pu etre lu)",
              "warning" not in js, "warning=%r" % js.get("warning"))

        js, code = lance(ADD, "--dhpt", base, "--dhps", "rc_bordereau.dhps",
                         "--output", os.path.join(tmp, "out2.dhpt"))
        check("[add] ajouter 'rc_bordereau.dhps' (bordere-au, standard) : ACCEPTE",
              code == 0 and "error" not in js,
              "exit=%s error=%r" % (code, js.get("error")))

        js, code = lance(ADD, "--dhpt", base, "--dhps", "basu.dhps",
                         "--output", os.path.join(tmp, "out3.dhpt"))
        check("[add] une VRAIE surcharge reste REFUSEE",
              code != 0 and "error" in js, "exit=%s js=%s" % (code, js))
        check("[add] le refus invoque l'en-tete, pas le suffixe",
              "xwin-s-sprojet" in (js.get("error") or "")
              and "suffixe" not in (js.get("error") or "").lower(),
              "error=%r" % js.get("error"))

        js, code = lance(ADD, "--dhpt", base, "--dhps", "pas_encore_creeu.dhps",
                         "--output", os.path.join(tmp, "out4.dhpt"))
        check("[add] .dhps pas encore creee : ACCEPTE (ne pas bloquer sur une inconnue)",
              code == 0 and "error" not in js,
              "exit=%s error=%r" % (code, js.get("error")))
        check("[add] ... et l'incertitude est DITE dans le JSON",
              "warning" in js and "NON verifie" in js["warning"],
              "warning=%r" % js.get("warning"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
