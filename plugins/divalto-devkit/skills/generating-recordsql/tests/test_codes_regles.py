#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les codes de regle de validate_rsql.py : emis, documentes, et une seule fois.

Ce fichier est ne du passage au prefixe par outil, et chacun de ses cas garde un
defaut REEL trouve dans le plugin, pas une precaution theorique :

1. Un code peut ne pas avoir la forme d un code. generating-zoom-sql en portait
   quatre ecrits en toutes lettres, invisibles a tout inventaire qui cherchait
   lettres+chiffres. Le cas 1 enumere TOUTE valeur posee sous la cle rule.
2. Un code emis sans ligne de table est indocumente : le partenaire le lit en sortie
   et n a rien pour le comprendre. C est arrive a manipulating-dhsf-screens, ou un
   second validateur avait ete ajoute sans que la table suive.
3. Une ligne de table sans emission est un code mort qu on cherchera en vain.
4. Ce skill porte DEUX tables -- le resume de SKILL.md et la table complete. Deux
   tables peuvent diverger ; celles de generating-zoom-sql l avaient fait.

L enumeration passe par ast et ne presuppose aucune forme de code.

Lancer :
    py plugin/skills/generating-recordsql/tests/test_codes_regles.py
"""
import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
VALIDATEUR = os.path.join(SKILL, "scripts", "validate_rsql.py")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
TABLE_COMPLETE = os.path.join(SKILL, "reference", "recordsql-anti-patterns.md")

PREFIXE = re.compile(r"RSQ\d{2}")
# Ancre sur le prefixe de l outil, jamais sur une majuscule quelconque : d autres
# tables du skill portent des identifiants qui ne sont pas des codes de regle.
LIGNE_TABLE = re.compile(r"^\|\s*`?(RSQ\d{2})`?\s*\|", re.M)
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
    return "%d codes, tous en RSQnn" % len(emis)


@cas("2. La table complete et les emissions se recouvrent exactement")
def cas2():
    emis = codes_emis()
    table = set(LIGNE_TABLE.findall(lire(TABLE_COMPLETE)))
    assert table, "aucune ligne de table lue -- l ancre du cas est trop faible"
    indocumentes = sorted(emis - table)
    morts = sorted(table - emis)
    assert not indocumentes, (
        "code(s) emis sans ligne de table : le partenaire les lira en sortie sans "
        "rien pour les comprendre : %s" % indocumentes)
    assert not morts, (
        "ligne(s) de table qu aucune emission ne produit : %s" % morts)
    return "%d codes, %d lignes, recouvrement exact" % (len(emis), len(table))


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
    autre = re.compile(r"(?<![\w-])(R\d{2})(?![\w-])")
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
                if ligne.startswith("| RSQ") and ligne.rstrip().endswith("|"):
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
