#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables des quatre detecteurs, contre l'IR du cas d'exemple livre.

Ce skill portait 1587 lignes de Python et AUCUN test, alors que son detecteur E4 venait
d'etre reecrit -- source de verite changee, deux regles de H1 retirees, colonne lue par
H5 changee -- avec pour seule preuve deux injections jetables.

La fixture `ir-fixture-simple.json` est le vrai IR produit par `ingest_deliverable.py`
sur `test_fixtures/fixture-simple`, recupere de l'historique. Les valeurs attendues
ci-dessous ont ete MESUREES en lancant les detecteurs, pas deduites de ce que les regles
devraient trouver -- et cette distinction a paye : la page `reference/exemple-de-cas.md`
affirmait que `OKK.yaml` etait « l'entite conforme : aucune detection attendue ». Mesure :
E3 en signale deux et E4 un. La page a ete corrigee sur ces chiffres.

Ce que le cas enseigne, et que les assertions gardent : un livrable peut satisfaire la
regle de citation (E1 muet sur OKK) et rester structurellement incomplet (E3 et E4
parlent). Les deux entites declenchent quelque chose, chacune autre chose.

`ingest_deliverable.py` n'est pas couvert ici : il exige `pyyaml`, une dependance que
rien ne declarait avant ce lot. Les cinq autres CLI sont en bibliotheque standard.

Lancer :
    py .claude/skills/reviewing-erp-doc/tests/test_detecteurs.py

Exit 0 = tous les verdicts attendus ; exit 1 = au moins un ecart.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
IR = os.path.join(HERE, "fixtures", "ir-fixture-simple.json")
ERP = os.path.join(HERE, "..", "test_fixtures", "fixture-simple", "erp-root")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lancer(script, *args):
    """Lance un detecteur, rend (code, resume JSON de stdout, contenu du fichier out)."""
    sortie = os.path.join(tempfile.mkdtemp(prefix="rev_"), "out.json")
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script),
                        "--ir", IR, "--out", sortie] + list(args),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    resume = {}
    if r.stdout.strip():
        try:
            resume = json.loads(r.stdout)
        except json.JSONDecodeError:
            pass
    contenu = {}
    if os.path.isfile(sortie):
        with open(sortie, encoding="utf-8") as f:
            contenu = json.load(f)
    return r.returncode, resume, contenu, (r.stderr or "")


def par_entite(items):
    d = {}
    for i in items:
        d[i["entity"]] = d.get(i["entity"], 0) + 1
    return d


# ======================================================================================
@cas("1. E1 -- les affirmations non sourcees de BAD, et rien sur OKK")
def cas1():
    # `BAD.yaml` a la MEME FORME que `OKK.yaml` : c'est ce qui rend le cas utile. Un
    # livrable peut etre parfaitement structure et entierement infonde.
    code, resume, d, err = lancer("detect_unsourced.py")
    assert code == 0, "E1 sort en %d : %s" % (code, err[:200])
    assert len(d["items"]) == 6, "attendu 6 items, obtenu %d" % len(d["items"])
    assert par_entite(d["items"]) == {"BAD": 6}, par_entite(d["items"])
    assert {i["severity"] for i in d["items"]} == {"erreur"}, \
        {i["severity"] for i in d["items"]}
    return "6 erreurs sur BAD, OKK muet"


@cas("2. E1 -- les six chemins exacts, pas seulement leur nombre")
def cas2():
    # Un compte juste peut cacher une detection qui a change de cible. Les chemins sont
    # la vraie signature de l'heuristique.
    _, _, d, _ = lancer("detect_unsourced.py")
    attendus = {
        "business.role",
        "business.business_rules[0]",
        "business.business_rules[1]",
        "technical.performance_notes",
        "technical.fields[0].business_note",
        "technical.fields[1].business_note",
    }
    obtenus = {i["yaml_path"] for i in d["items"]}
    assert obtenus == attendus, "manquants %s, en trop %s" % (
        sorted(attendus - obtenus), sorted(obtenus - attendus))
    return "les six affirmations nommees"


@cas("3. E1 -- chaque item porte son ancrage")
def cas3():
    # « Pas d'invention » est un invariant du skill : un item sans ancre ne se verifie
    # pas, et le partenaire ne peut pas le contester.
    _, _, d, _ = lancer("detect_unsourced.py")
    for i in d["items"]:
        for champ in ("entity", "yaml_path", "challenge", "severity"):
            assert i.get(champ), "item sans %s : %s" % (champ, i)
    return "entity, yaml_path, challenge, severite sur les six"


@cas("4. E3 -- les omissions structurelles d'OKK, et l'info sur BAD")
def cas4():
    # Contre-intuitif et mesure : c'est OKK, l'entite « propre », qui porte les deux
    # ERREURS d'omission -- un champ et un index declares dans `Gttokk.dhsd` et absents
    # du livrable. BAD n'a qu'une info : aucun `.dhsd` ne lui correspond sous erp-root,
    # donc E3 ne peut pas la contredire.
    code, resume, d, err = lancer("detect_omissions.py", "--erp-root", ERP)
    assert code == 0, "E3 sort en %d : %s" % (code, err[:200])
    assert len(d["items"]) == 3, "attendu 3 items, obtenu %d" % len(d["items"])
    assert par_entite(d["items"]) == {"BAD": 1, "OKK": 2}, par_entite(d["items"])
    graves = {i["title"] for i in d["items"] if i["severity"] == "erreur"}
    assert graves == {"Champ Telephone absent du livrable",
                      "Index IdxTel absent du livrable"}, graves
    info = [i for i in d["items"] if i["severity"] == "info"]
    assert len(info) == 1 and info[0]["entity"] == "BAD", info
    return "2 erreurs sur OKK, 1 info sur BAD"


@cas("5. E4 -- H1 signale AnnulFl, declare C20 pour un suffixe Fl")
def cas5():
    # Le suffixe `Fl` predit `1,0` a 95 % selon `taxonomie-suffixes.md`. `OKK.yaml`
    # declare `AnnulFl` en `C20` : un drapeau booleen sur 20 octets. C'est la seule
    # contradiction du cas, et elle est sur l'entite « propre ».
    code, resume, d, err = lancer("detect_doc_contradictions.py")
    assert code == 0, "E4 sort en %d : %s" % (code, err[:200])
    assert len(d["items"]) == 1, "attendu 1 item, obtenu %d" % len(d["items"])
    i = d["items"][0]
    assert i["entity"] == "OKK" and "AnnulFl" in i["title"], i
    assert i["severity"] == "warning", i["severity"]
    assert "C20" in i["challenge"], i["challenge"]
    return "AnnulFl en C20 contre le suffixe Fl"


@cas("6. E4 -- la table des prefixes de domaine est chargee")
def cas6():
    # H5 lit `reference/prefixes-domaine.md`, copie locale livree avec le skill. Si la
    # page manque, H5 se tait et un `warning_global` le dit : ce cas garde le chargement.
    _, resume, d, _ = lancer("detect_doc_contradictions.py")
    assert resume.get("domain_prefixes_loaded") == 15, \
        "15 domaines attendus, %s charge(s)" % resume.get("domain_prefixes_loaded")
    assert d["warnings_global"] == [], d["warnings_global"]
    return "15 domaines, aucun avertissement global"


@cas("7. E4 -- aucun item ne renvoie a un document interne")
def cas7():
    # Le `source_ref` de H1 pointait encore le referentiel dictionnaire interne, un
    # partenaire n'a pas, et il partait dans le `review.md` livre. Le lot E4 avait
    # corrige celui de H5 et oublie celui-la.
    _, _, d, _ = lancer("detect_doc_contradictions.py")
    for i in d["items"]:
        ref = i.get("source_ref") or ""
        for interdit in ("DICTIONNAIRE-DHSD", "ARCHITECTURE-ENTITE", "MODULES-ERP",
                         "(interne)"):
            assert interdit not in ref, \
                "source_ref renvoie a un document interne : %r" % ref
    return "les source_ref pointent des pages livrees"


@cas("8. Batch E2 -- les citations d'OKK sont resolues sur les sources")
def cas8():
    # E2 prepare le jugement semantique : il extrait le contexte autour de chaque
    # citation. Une citation non resolue est un signal, pas une erreur -- la source
    # peut manquer sous erp-root, comme ici pour une des six.
    code, resume, d, err = lancer("prepare_misalign_batch.py", "--erp-root", ERP)
    assert code == 0, "le batch sort en %d : %s" % (code, err[:200])
    assert resume.get("entries_total") == 6, resume
    assert resume.get("resolved") == 5, resume
    assert resume.get("source_not_found") == 1, resume
    assert {e["entity"] for e in d["entries"]} == {"OKK"}, \
        {e["entity"] for e in d["entries"]}
    return "6 entrees, 5 resolues, 1 source absente"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 92)
    print("reviewing-erp-doc -- detecteurs, %d cas" % len(CAS))
    print("=" * 92)
    ok = 0
    for titre, fn in CAS:
        try:
            detail = fn()
            print("  OK    %-58s %s" % (titre[:58], detail))
            ok += 1
        except AssertionError as e:
            print("  ECHEC %-58s %s" % (titre[:58], str(e)[:180]))
        except Exception as e:
            print("  ERREUR %-57s %s: %s" % (titre[:57], type(e).__name__,
                                             str(e)[:150]))
    print("\n  %d/%d" % (ok, len(CAS)))
    sys.exit(0 if ok == len(CAS) else 1)


if __name__ == "__main__":
    main()
