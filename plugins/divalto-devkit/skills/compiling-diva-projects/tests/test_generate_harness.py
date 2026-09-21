#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de generate_harness.py (aucun xwin7 requis).

Le script ne fait que GENERER des fichiers : tout est verifiable hors poste Divalto.
Les modeles `.dhpt` sont fabriques a la volee dans un dossier temporaire (ISO-8859-1 + CRLF,
comme un vrai fichier DIVA) -- rien n'est ecrit dans le depot.

Lancer :
    py .claude/skills/compiling-diva-projects/tests/test_generate_harness.py

Exit 0 = tous les comportements attendus ; exit 1 = au moins un ecart.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "generate_harness.py")


def write_iso(path, text):
    """Ecrit un fichier DIVA realiste : ISO-8859-1 + CRLF."""
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("iso-8859-1")
    with open(path, "wb") as f:
        f.write(data)


def model_dhpt(profils):
    """Contenu d'un .dhpt modele. `profils` = liste de dicts (nom/implicites/versioncible)."""
    out = ["xwin-projet        2.0", "[general]", 'nom="projet modele"',
           'progexec="monexec.dhop"', 'util="UTIL1"', 'cheminbases="/../../sources/pack"',
           "[profildefaut]"]
    for p in profils:
        out.append("[profil]")
        for k in ("nom", "implicites", "versioncible"):
            if p.get(k):
                out.append(k + '="' + p[k] + '"')
        out.append('repobjet="/objets/du_modele"')
        out.append('repobjetsurcharge="/objets/surcharge_du_modele"')
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
    tmp = tempfile.mkdtemp(prefix="harness_tests_")
    failures = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            failures.append(label)

    try:
        mono = os.path.join(tmp, "mono.dhpt")
        write_iso(mono, model_dhpt([{"nom": "profil unique", "implicites": "monimplicite.txt",
                                     "versioncible": "X.99"}]))
        multi = os.path.join(tmp, "multi.dhpt")
        write_iso(multi, model_dhpt([{"nom": "profA", "implicites": "ia.txt"},
                                     {"nom": "profB", "implicites": "ib.txt"}]))
        noimpl = os.path.join(tmp, "noimpl.dhpt")
        write_iso(noimpl, model_dhpt([{"nom": "profX"}]))
        noname = os.path.join(tmp, "noname.dhpt")
        write_iso(noname, model_dhpt([{"implicites": "i.txt"}]))

        src = os.path.join(tmp, "masource.dhsp")
        write_iso(src, "; source de test\nProc Test()\nFinproc\n")
        src2 = os.path.join(tmp, "autresource.dhsq")
        write_iso(src2, "; recordsql de test\n")
        masque = os.path.join(tmp, "unmasque.dhsf")
        write_iso(masque, "[page]\n")

        # --- 1. --from-dhpt OBLIGATOIRE : le harness n'invente aucune config ---
        rc, js, txt = run(["--source", src, "--output-dir", os.path.join(tmp, "o1")])
        check("--from-dhpt obligatoire", rc == 2 and "from-dhpt" in txt, "rc=%s" % rc)

        # --- 2. emprunt de la config du modele + isolation des objets ---
        out2 = os.path.join(tmp, "o2")
        rc, js, txt = run(["--from-dhpt", mono, "--source", src, "--output-dir", out2])
        check("generation mono-profil", rc == 0 and js is not None, "rc=%s %s" % (rc, txt[:120]))
        if js:
            dhpt = open(js["dhpt"], "rb").read().decode("iso-8859-1")
            check("emprunte implicites= du modele", 'implicites="monimplicite.txt"' in dhpt)
            check("emprunte util= du modele", 'util="UTIL1"' in dhpt)
            check("emprunte progexec= du modele", 'progexec="monexec.dhop"' in dhpt)
            check("emprunte cheminbases= du modele", 'cheminbases="/../../sources/pack"' in dhpt)
            check("emprunte versioncible= du modele", 'versioncible="X.99"' in dhpt)
            check("emprunte le nom du profil", 'nom="profil unique"' in dhpt)
            check("repobjet FORCE sur le jetable (pas celui du modele)",
                  "/objets/du_modele" not in dhpt and js["objet_dir"] in dhpt)
            check("repobjetsurcharge FORCE sur le jetable",
                  "/objets/surcharge_du_modele" not in dhpt)
            check("[communs] OMIS (une section vide est refusee par xwin7)",
                  "[communs]" not in dhpt)
            check("borrowed_profile retourne", js.get("borrowed_profile") == "profil unique")
            check("source copiee dans le dossier objet",
                  os.path.isfile(os.path.join(js["objet_dir"], "masource.dhsp")))
            check("aucun .ps1 genere (compile delegue a compile_project)",
                  not os.path.isdir(os.path.join(out2, "scripts")))
            for key in ("dhpt", "dhps"):
                raw = open(js[key], "rb").read()
                ok_enc = True
                try:
                    raw.decode("iso-8859-1")
                except Exception:
                    ok_enc = False
                lf = raw.count(b"\n") - raw.count(b"\r\n")
                check("%s en ISO-8859-1 + CRLF" % key, ok_enc and lf == 0, "lf=%s" % lf)

        # --- 3. multi-profils : refus explicite, puis selection ---
        rc, js, txt = run(["--from-dhpt", multi, "--source", src,
                           "--output-dir", os.path.join(tmp, "o3")])
        check("multi-profils sans --profile : echec listant les profils",
              rc == 1 and "profA" in txt and "profB" in txt, "rc=%s" % rc)
        rc, js, txt = run(["--from-dhpt", multi, "--profile", "profB", "--source", src,
                           "--output-dir", os.path.join(tmp, "o4")])
        check("multi-profils avec --profile : selectionne le bon",
              rc == 0 and js is not None and js.get("borrowed_profile") == "profB", "rc=%s" % rc)
        rc, js, txt = run(["--from-dhpt", multi, "--profile", "inconnu", "--source", src,
                           "--output-dir", os.path.join(tmp, "o5")])
        check("profil inexistant : echec listant les profils disponibles",
              rc == 1 and "profA" in txt, "rc=%s" % rc)

        # --- 4. garde-fous sur le modele ---
        rc, js, txt = run(["--from-dhpt", noimpl, "--source", src,
                           "--output-dir", os.path.join(tmp, "o6")])
        check("profil sans implicites= : echec propre (champ critique)",
              rc == 1 and "implicites" in txt, "rc=%s" % rc)
        rc, js, txt = run(["--from-dhpt", noname, "--source", src,
                           "--output-dir", os.path.join(tmp, "o7")])
        check("profil sans nom= : echec propre (pas de traceback)",
              rc == 1 and "Traceback" not in txt, "rc=%s" % rc)

        # --- 5. perimetre : sources programme uniquement (.dhsp/.dhsq) ---
        rc, js, txt = run(["--from-dhpt", mono, "--source", masque,
                           "--output-dir", os.path.join(tmp, "o8")])
        check("masque .dhsf refuse (non isolable hors de son dictionnaire)",
              rc == 1 and "dhsp" in txt, "rc=%s" % rc)
        rc, js, txt = run(["--from-dhpt", mono, "--source", os.path.join(tmp, "absent.dhsp"),
                           "--output-dir", os.path.join(tmp, "o9")])
        check("source introuvable : echec propre", rc == 1 and "Traceback" not in txt, "rc=%s" % rc)

        # --- 6. multi-sources (#28 dependance locale / #216 .dhps orpheline) ---
        rc, js, txt = run(["--from-dhpt", mono, "--sources", src, src2,
                           "--output-dir", os.path.join(tmp, "o10"), "--with-zdiva"])
        check("--sources multiples acceptees",
              rc == 0 and js is not None and len(js["source_copies"]) == 2, "rc=%s" % rc)
        if js:
            dhps = open(js["dhps"], "rb").read().decode("iso-8859-1")
            check("les 2 sources sont dans [fichiers] du .dhps",
                  'fic="masource.dhsp"' in dhps and 'fic="autresource.dhsq"' in dhps)
            check("--with-zdiva ajoute zdiva dans [includes]", 'fic="zdiva.dhsp"' in dhps)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not failures else "%d ECHEC(S)" % len(failures)) + " ===")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
