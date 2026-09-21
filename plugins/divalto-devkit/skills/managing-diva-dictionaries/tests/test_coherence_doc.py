#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Invariants de coherence entre la DOCUMENTATION du skill et son CODE.

Le LOT C est purement documentaire -- et une documentation ne "tombe" pas en erreur : elle
derive en silence. Ces cas verrouillent les affirmations verifiables **par execution**,
pour qu'elles ne deviennent pas fausses sans que rien ne le signale.

La lecon vient d'un autre skill : une regle de lint y a ete **declaree au catalogue,
documentee dans une page de reference, et n'a jamais eu d'implementation**. Une regle
annoncee qui ne s'execute pas est pire qu'une regle absente -- un agent croit disposer d'un
controle qu'il n'a pas. Meme risque ici pour :

- les **5 lignes obligatoires** du bloc `[CHAMP]` : la page les enumere, le generateur les
  emet. Rien ne garantit que les deux restent d'accord -- sauf le cas 1 ;
- les **regles DICTnn** citees par la documentation : le cas 4 verifie qu'elles existent
  vraiment dans `validate_dhsd.py` ;
- l'**inventaire des pages de reference**, qui a reellement derive : trois pages ont existe
  longtemps sans figurer au catalogue de `discovering-skills` (cas 5), donc invisibles.

Lancer :
    py .claude/skills/managing-diva-dictionaries/tests/run_all.py
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
REFERENCE = os.path.join(SKILL, "reference")
SCRIPTS = os.path.join(SKILL, "scripts")
GEN = os.path.join(SCRIPTS, "generate_dhsd_block.py")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(chemin):
    return io.open(chemin, encoding="utf-8").read()


def skill_md():
    return lire(os.path.join(SKILL, "SKILL.md"))


# --------------------------------------------------------------------------

@cas("1. Les 5 lignes documentees comme OBLIGATOIRES sont bien celles emises")
def cas1():
    """La page enumere Version/Nom/Gel/Nature/Flags et dit DateM facultatif.
    Le generateur doit emettre exactement ces lignes, et PAS de DateM."""
    params = {"table": "Coh", "ce_value": "A", "base": "AlgCoh",
              "fields": [{"name": "Cod", "nature": "20"}]}
    r = subprocess.run([sys.executable, GEN, "--stdin", "--user", "coh_test"],
                       input=json.dumps(params).encode("utf-8"), capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    js = json.loads(out[out.find("{"):])
    bloc = js["blocks"]["champs"][0]["block"]
    cles = [l.split("=")[0] for l in bloc.split("\n") if "=" in l]

    obligatoires = ["Version", "Nom", "Gel", "Nature", "Flags"]
    for k in obligatoires:
        assert k in cles, "ligne %s documentee obligatoire mais absente du bloc genere" % k
    assert "DateM" not in cles, (
        "la page dit DateM facultatif et le generateur n'en emet pas : "
        "il en emet un maintenant, la doc est fausse")

    page = lire(os.path.join(REFERENCE, "ajout-champ-table-existante.md"))
    for k in obligatoires:
        assert ("`%s=`" % k) in page, "la page n'enumere plus la ligne obligatoire %s" % k
    return "5 lignes obligatoires + DateM absent, doc et code d'accord"


@cas("2. Toute page de reference citee par le SKILL.md existe")
def cas2():
    md = skill_md()
    cites = set(re.findall(r"\(reference/([\w.-]+\.md)\)", md))
    assert cites, "aucune page de reference citee : le motif de detection a change"
    for f in sorted(cites):
        assert os.path.isfile(os.path.join(REFERENCE, f)), "page citee absente : " + f
    return "%d pages citees, toutes presentes" % len(cites)


@cas("3. Aucune page de reference ORPHELINE (presente mais jamais citee)")
def cas3():
    md = skill_md()
    cites = set(re.findall(r"\(reference/([\w.-]+\.md)\)", md))
    sur_disque = {f for f in os.listdir(REFERENCE) if f.endswith(".md")}
    orphelines = sorted(sur_disque - cites)
    assert not orphelines, (
        "page(s) de reference que le SKILL.md ne cite pas, donc jamais chargee(s) : %s"
        % orphelines)
    return "%d pages, toutes atteignables depuis le SKILL.md" % len(sur_disque)


@cas("4. Toute regle DICTnn citee dans la doc est implementee quelque part")
def cas4():
    # Deux familles d'implementation, et il faut regarder les DEUX -- ne scanner que
    # validate_dhsd.py faisait passer DICT12/DICT13 pour des regles fantomes alors qu'elles
    # sont bien codees, en garde-fous PRE-GENERATION dans generate_dhsd_block.py.
    code = lire(os.path.join(SCRIPTS, "validate_dhsd.py"))
    implementees = set(re.findall(r'"rule":\s*"(DICT\d+)"', code))
    gen = lire(GEN)
    implementees |= set(re.findall(r"Regle (DICT\d\d)\b", gen))
    assert implementees, "aucune regle trouvee dans le validateur : motif change"
    citees = set()
    for f in os.listdir(REFERENCE):
        if f.endswith(".md"):
            citees |= set(re.findall(r"\bDICT(\d\d)\b", lire(os.path.join(REFERENCE, f))))
    citees = {"DICT" + n for n in citees}
    citees |= set(re.findall(r"\bDICT\d\d\b", skill_md()))

    # DETTE GELEE -- regles citees par la documentation SANS implementation.
    # Les DEUX ont ete trouvees par ce test meme, au LOT C :
    #   DICT10 : n'existe que dans une docstring de validate_dhsd.py, aucun code ;
    #   DICT11 : une boucle qui se termine sur `pass` ("Verification complexe, on
    #         laisse en warning simple") -- elle ne remonte rien.
    # Les deux sont desormais marquees "non implementee" dans la page de reference,
    # pour ne pas laisser croire a un garde-fou qui n'existe pas -- et la colonne
    # "Regle linter" de la page de reference dit ou la verification existe
    # vraiment : le linter les implemente sous `D10` et `D11`.
    # NE JAMAIS ALLONGER CETTE LISTE pour faire passer le test : soit implementer la
    # regle, soit retirer sa mention de la documentation. Le test est la pour bloquer
    # la TROISIEME.
    DETTE = {"DICT10", "DICT11"}

    fantomes = sorted(citees - implementees - DETTE)
    assert not fantomes, (
        "regle(s) citee(s) par la documentation sans implementation dans "
        "validate_dhsd.py : %s -- soit l'implementer, soit retirer la mention" % fantomes)
    # Une regle sortie de la dette (enfin implementee) doit quitter la liste
    reparees = sorted(DETTE & implementees)
    assert not reparees, (
        "regle(s) desormais implementee(s) mais encore listee(s) comme dette : %s "
        "-- retirer de DETTE" % reparees)
    return ("%d regles implementees ; dette gelee a %d regles annoncees non codees"
            % (len(implementees), len(DETTE & citees)))


@cas("5. L'inventaire du catalogue liste bien les pages de reference reelles")
def cas5():
    catalog = os.path.abspath(os.path.join(
        SKILL, "..", "discovering-skills", "reference", "catalog.json"))
    if not os.path.isfile(catalog):
        return "catalogue absent (skill distribue seul) : cas non applicable"
    j = json.loads(lire(catalog))
    entree = j.get("skills", {}).get(os.path.basename(SKILL))
    assert entree is not None, "skill absent du catalogue"
    au_catalogue = set(entree.get("references") or [])
    sur_disque = {f for f in os.listdir(REFERENCE) if f.endswith(".md")}
    manquantes = sorted(sur_disque - au_catalogue)
    fantomes = sorted(au_catalogue - sur_disque)
    assert not manquantes, (
        "page(s) sur disque absente(s) du catalogue, donc invisibles de "
        "discovering-skills : %s" % manquantes)
    assert not fantomes, "page(s) au catalogue mais absente(s) du disque : %s" % fantomes
    return "%d pages, catalogue synchronise" % len(sur_disque)


@cas("6. Les liens inter-skills de la doc pointent sur des skills existants")
def cas6():
    ko = []
    for f in os.listdir(REFERENCE):
        if not f.endswith(".md"):
            continue
        p = os.path.join(REFERENCE, f)
        for cible in re.findall(r"\((\.\./\.\./[\w.-]+/SKILL\.md)\)", lire(p)):
            if not os.path.isfile(os.path.normpath(os.path.join(REFERENCE, cible))):
                ko.append("%s -> %s" % (f, cible))
    assert not ko, "lien(s) inter-skills mort(s) : %s" % ko
    return "liens vers les skills voisins tous valides"


# --------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    echecs = []
    for titre, fn in CAS:
        try:
            note = fn()
            print("  OK   %s" % titre)
            if note:
                print("         -> %s" % note)
        except AssertionError as e:
            echecs.append(titre)
            print("  ECHEC %s" % titre)
            print("         %s" % str(e)[:400])
        except Exception as e:
            echecs.append(titre)
            print("  ERREUR %s : %s: %s" % (titre, type(e).__name__, str(e)[:300]))
    print("")
    if echecs:
        print("BILAN : %d/%d cas en ECHEC" % (len(echecs), len(CAS)))
        for t in echecs:
            print("  - " + t)
        return 1
    print("BILAN : %d/%d cas OK" % (len(CAS), len(CAS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
