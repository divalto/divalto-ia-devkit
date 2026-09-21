#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les codes de regle de validate_names.py : emis, documentes, et d'une seule severite.

Ce skill emettait `V01` a `V09` sous la cle `rule` -- donc le partenaire les lisait en
sortie -- sans qu'aucune page ne les explique : cinq d'entre eux (`V02`, `V03`, `V04`,
`V06`, `V09`) n'etaient nommes nulle part, et le skill n'avait aucun test. Il ne figurait
pas non plus dans le recensement des outils emetteurs de la convention, qui en comptait
sept pour neuf.

Chaque cas garde un defaut REEL, pas une precaution :

1. L'enumeration passe par `ast` et ne presuppose aucune forme de code. C'est la lecon
   du lot des prefixes par outil : quatre codes s'ecrivaient EN TOUTES LETTRES ailleurs
   dans le plugin, invisibles a tout inventaire qui cherchait lettres+chiffres.
2. Un code emis sans ligne de table est indocumente : le partenaire le lit en sortie et
   n'a rien pour le comprendre. C'est exactement ce qui s'est passe ici.
3. Une ligne de table sans emission est un code mort qu'on cherchera en vain.
4. La severite ANNONCEE doit etre celle qui est EMISE. Une table peut dire `error` la ou
   le script emet `warning` : le partenaire priorise alors sur une information fausse.
   Ce cas est repris de l'invariant 4 de `linting-diva-code`, ou la divergence avait
   deja ete constatee.

Lancer :
    py plugin/skills/naming-diva-entities/tests/test_codes_regles.py
"""
import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
VALIDATEUR = os.path.join(SKILL, "scripts", "validate_names.py")
SKILL_MD = os.path.join(SKILL, "SKILL.md")

PREFIXE = re.compile(r"V\d{2}")
# Ancre sur le prefixe de l'outil, jamais sur une majuscule quelconque : les autres
# tables du skill portent des noms de tokens, pas des codes de regle.
LIGNE_TABLE = re.compile(r"^\|\s*`?(V\d{2})`?\s*\|\s*([a-z]+)\s*\|", re.M)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


def emissions():
    """[(code, severite)] -- tout couple pose dans un meme dict de sortie."""
    out = []
    for n in ast.walk(ast.parse(lire(VALIDATEUR))):
        if not isinstance(n, ast.Dict):
            continue
        champs = {}
        for cle, val in zip(n.keys, n.values):
            if (isinstance(cle, ast.Constant) and isinstance(val, ast.Constant)
                    and isinstance(val.value, str)):
                champs[cle.value] = val.value
        if "rule" in champs:
            out.append((champs["rule"], champs.get("severity", "")))
    return out


def codes_emis():
    return {c for c, _ in emissions()}


@cas("1. Tout code emis porte le prefixe de l'outil, quelle que soit sa forme")
def cas1():
    emis = codes_emis()
    assert emis, "aucun code emis trouve -- le cas ne mesure rien"
    hors = sorted(c for c in emis if not PREFIXE.fullmatch(c))
    assert not hors, (
        "code(s) hors convention -- chaque outil emetteur possede SON prefixe et "
        "numerote en continu chez lui : %s" % hors)
    return "%d codes, tous en Vnn" % len(emis)


@cas("2. Tout code emis a sa ligne dans la table du SKILL.md")
def cas2():
    emis = codes_emis()
    table = {c for c, _ in LIGNE_TABLE.findall(lire(SKILL_MD))}
    assert table, "aucune ligne de table lue -- l'ancre du cas est trop faible"
    indocumentes = sorted(emis - table)
    assert not indocumentes, (
        "code(s) emis sans ligne de table : le partenaire les lira en sortie sans rien "
        "pour les comprendre : %s" % indocumentes)
    return "%d codes emis, %d lignes de table" % (len(emis), len(table))


@cas("3. Aucune ligne de table ne promet un code que le skill n'emet pas")
def cas3():
    emis = codes_emis()
    table = {c for c, _ in LIGNE_TABLE.findall(lire(SKILL_MD))}
    morts = sorted(table - emis)
    assert not morts, (
        "ligne(s) de table qu'aucune emission ne produit : %s" % morts)
    return "recouvrement exact dans les deux sens"


@cas("4. La severite annoncee est celle qui est emise")
def cas4():
    """Une table qui annonce `error` la ou le script emet `warning` fait prioriser le
    partenaire sur une information fausse."""
    annoncee = dict(LIGNE_TABLE.findall(lire(SKILL_MD)))
    assert annoncee, "table illisible -- le cas ne mesure rien"
    par_code = {}
    for code, sev in emissions():
        if sev:
            par_code.setdefault(code, set()).add(sev)
    ecarts = []
    for code, severites in sorted(par_code.items()):
        if len(severites) > 1:
            ecarts.append("%s emet %s" % (code, sorted(severites)))
        elif code in annoncee and annoncee[code] not in severites:
            ecarts.append("%s annonce %s emet %s"
                          % (code, annoncee[code], sorted(severites)))
    assert not ecarts, "severite(s) divergente(s) : %s" % ecarts
    return "%d codes, severite annoncee == severite emise" % len(par_code)


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
