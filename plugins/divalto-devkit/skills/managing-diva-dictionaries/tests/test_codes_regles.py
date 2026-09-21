#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les codes de regle de ce skill : emis, documentes, et une seule fois.

Ne du passage au prefixe par outil. Ce skill a une population de regles a TROIS
natures, et le savoir change ce que ce fichier peut asserter :

  * douze codes emis en JSON par validate_dhsd.py ;
  * DICT12 et DICT13, garde-fous de GENERATION dans generate_dhsd_block.py : ils
    levent une ValueError, le code n apparait dans aucune sortie ;
  * DICT10 et DICT11, annoncees et non codees ici -- dette gelee, et le linter les
    implemente sous D10 et D11.

Le cas 2 ne verifie donc qu UN sens : tout code emis a sa ligne de table. Le sens
inverse -- une ligne que rien n implemente -- est garde par le cas 4 de
test_coherence_doc.py, qui connait les trois natures et gele la dette. On ne
duplique pas un garde-fou plus fin que le sien.

L enumeration passe par ast et ne presuppose aucune forme de code.

Lancer :
    py plugin/skills/managing-diva-dictionaries/tests/test_codes_regles.py
"""
import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
VALIDATEUR = os.path.join(SKILL, "scripts", "validate_dhsd.py")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
TABLE_COMPLETE = os.path.join(SKILL, "reference", "dhsd-anti-patterns.md")

PREFIXE = re.compile(r"DICT\d{2}")
# Ancre sur le prefixe de l outil. `reference/nature-types.md` porte des types
# Nature DIVA ecrits D0, D2, D8 -- un seul chiffre : une ancre plus large les
# prendrait pour des codes de regle, et c est exactement l erreur qui m a fait
# annoncer une fausse ligne morte D8 dans la convention.
LIGNE_TABLE = re.compile(r"^\|\s*`?(DICT\d{2})`?\s*\|", re.M)
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
    return "%d codes, tous en DICTnn" % len(emis)


@cas("2. Tout code emis a sa ligne dans la table complete")
def cas2():
    emis = codes_emis()
    table = set(LIGNE_TABLE.findall(lire(TABLE_COMPLETE)))
    assert table, "aucune ligne de table lue -- l ancre du cas est trop faible"
    indocumentes = sorted(emis - table)
    assert not indocumentes, (
        "code(s) emis sans ligne de table : le partenaire les lira en sortie sans "
        "rien pour les comprendre : %s" % indocumentes)
    # Le sens inverse n est PAS verifie ici : DICT10/DICT11 sont une dette gelee et
    # DICT12/DICT13 des garde-fous de generation, donc « toute ligne a une emission »
    # serait faux. Le cas 4 de test_coherence_doc.py le garde, en connaissant ces
    # trois natures -- et il gele la dette nommement.
    return "%d codes emis, tous documentes parmi %d lignes" % (len(emis), len(table))


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
    autre = re.compile(r"(?<![\w-])(D(?:0[1-9]|1[0-6]))(?![\w-])")
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
                if ligne.startswith("| DICT") and ligne.rstrip().endswith("|"):
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
