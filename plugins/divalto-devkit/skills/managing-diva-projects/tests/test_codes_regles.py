#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les codes de regle de ce skill : emis, documentes, et une seule fois.

Dernier producteur du passage au prefixe par outil. Dix-sept regles annoncees,
quinze emises -- et les deux autres ne sont pas des oublis :

  * PROJ03 n est pas une verification, c est une consigne a l OPERATEUR (ne pas
    editer un fichier accentue avec Edit/Write). Ce qui la fait respecter est le
    hook protect_encoding.py, pas le validateur.
  * PROJ11 (melange de prefixes domaine) est annoncee et codee nulle part -- ni ici,
    ni chez le linter, dont la table la presente pourtant comme un warning actif.

Le cas 2 verifie donc les DEUX sens avec une liste GELEE. Ne jamais l allonger pour
faire passer le test : soit implementer la regle, soit retirer sa mention. Le test
est la pour bloquer la troisieme.

L enumeration passe par ast et ne presuppose aucune forme de code.

Lancer :
    py plugin/skills/managing-diva-projects/tests/test_codes_regles.py
"""
import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
VALIDATEUR = os.path.join(SKILL, "scripts", "validate_project.py")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
TABLE_COMPLETE = os.path.join(SKILL, "reference", "project-anti-patterns.md")

PREFIXE = re.compile(r"PROJ\d{2}")
# Ancre sur le prefixe de l outil, jamais sur une majuscule quelconque.
LIGNE_TABLE = re.compile(r"^\|\s*`?(PROJ\d{2})`?\s*\|", re.M)
NOMME_LINTER = re.compile(r"(?i)lint(?:er|_diva|ing-diva-code)")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


def codes_emis():
    """TOUTE valeur posee sous une cle `rule`, quelle que soit sa forme."""
    emis = set()
    for n in ast.walk(ast.parse(lire(VALIDATEUR))):
        if isinstance(n, ast.Dict):
            for cle, val in zip(n.keys, n.values):
                if (isinstance(cle, ast.Constant) and cle.value in ("rule", "code")
                        and isinstance(val, ast.Constant)
                        and isinstance(val.value, str)):
                    emis.add(val.value)
    return emis


@cas("1. Tout code emis porte le prefixe de l outil, y compris les codes en toutes lettres")
def cas1():
    emis = codes_emis()
    assert emis, "aucun code emis trouve -- le cas ne mesure rien"
    hors = sorted(c for c in emis if not PREFIXE.fullmatch(c))
    assert not hors, (
        "code(s) hors convention -- chaque outil emetteur possede SON prefixe et "
        "numerote en continu chez lui ; un code en toutes lettres reste un code : %s"
        % hors)
    return "%d codes, tous en PROJnn" % len(emis)


@cas("2. Table et emissions se recouvrent, hors les gelees declarees")
def cas2():
    emis = codes_emis()
    table = set(LIGNE_TABLE.findall(lire(TABLE_COMPLETE)))
    assert table, "aucune ligne de table lue -- l ancre du cas est trop faible"
    # GELEE -- regles annoncees par la table SANS emission, et pourquoi :
    #   PROJ03 : une consigne a l operateur, appliquee par le hook protect_encoding.py ;
    #   PROJ11 : annoncee, codee nulle part, ici comme chez le linter.
    # NE JAMAIS ALLONGER CETTE LISTE pour faire passer le test : soit implementer la
    # regle, soit retirer sa mention de la documentation.
    GELEES = {"PROJ03", "PROJ11"}
    indocumentes = sorted(emis - table)
    morts = sorted(table - emis - GELEES)
    reparees = sorted(GELEES & emis)
    assert not indocumentes, (
        "code(s) emis sans ligne de table : le partenaire les lira en sortie sans "
        "rien pour les comprendre : %s" % indocumentes)
    assert not morts, (
        "ligne(s) de table qu aucune emission ne produit : %s -- soit l implementer, "
        "soit retirer la mention" % morts)
    assert not reparees, (
        "regle(s) desormais emise(s) mais encore listee(s) comme gelee(s) : %s "
        "-- retirer de GELEES" % reparees)
    return ("%d codes emis, %d lignes de table, %d gelee(s) declaree(s)"
            % (len(emis), len(table), len(GELEES)))


@cas("3. Le resume de SKILL.md ne diverge pas de la table complete")
def cas3():
    resume = set(LIGNE_TABLE.findall(lire(SKILL_MD)))
    table = set(LIGNE_TABLE.findall(lire(TABLE_COMPLETE)))
    assert resume, "SKILL.md n annonce plus aucune regle"
    assert resume == table, (
        "les deux tables du skill divergent -- SKILL.md seul : %s ; page seule : %s"
        % (sorted(resume - table), sorted(table - resume)))
    return "%d regles, les deux tables concordent" % len(resume)


@cas("4. Aucun code d un autre outil ne traine sans etre nomme")
def cas4():
    """Dans la colonne Regle linter, un code court est voulu : c est celui du linter,
    nomme la ou la convention veut qu il le soit. Le meme code ailleurs, sans que le
    linter soit nomme, est un reste de l ancienne numerotation -- et le partenaire le
    chercherait dans la mauvaise table.
    """
    autre = re.compile(r"(?<![\w-])(P(?:0[1-9]|1[0-7]))(?![\w-])")
    # Ce fichier-ci PORTE la liste des anciens codes : son motif et sa docstring les
    # nomment forcement. Il est donc le seul exempte, et on verifie que l exemption ne
    # masque que lui -- une exemption qui s elargit en silence rend le controle creux.
    moi = os.path.abspath(__file__)
    vu_moi = False
    restes = []
    for dossier, sous, noms in os.walk(SKILL):
        sous[:] = [d for d in sous if d not in ("__pycache__", ".pytest_cache")]
        for nom in sorted(noms):
            if os.path.splitext(nom)[1] not in (".md", ".py", ".json", ".j2", ".txt"):
                continue
            p = os.path.join(dossier, nom)
            if os.path.abspath(p) == moi:
                vu_moi = True
                continue
            for i, ligne in enumerate(
                    io.open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
                if NOMME_LINTER.search(ligne):
                    continue
                derniere = ""
                if ligne.startswith("| PROJ") and ligne.rstrip().endswith("|"):
                    cells = [c.strip() for c in ligne.strip().strip("|").split("|")]
                    derniere = cells[-1] if cells else ""
                for m in autre.finditer(ligne):
                    if m.group(1) in derniere:
                        continue
                    restes.append("%s:%d %s" % (os.path.relpath(p, SKILL), i, m.group(1)))
    assert vu_moi, (
        "le fichier exempte n a pas ete rencontre : l exemption ne mesure plus rien")
    assert not restes, "reste(s) de l ancienne numerotation : %s" % restes
    return "aucun reste ; 1 seule exemption, ce fichier, et elle est verifiee"


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
