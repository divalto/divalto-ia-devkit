#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Invariants de coherence du catalogue de regles.

La table `RULES` n'est PAS lue par le moteur : elle ne sert qu'a valider les codes
passes a `--rules`. Le comportement reel vit dans les dictionnaires `rule_map` de
chaque dispatcher et dans la severite codee en dur de chaque `check_*`. Rien
n'empeche donc les deux de deriver -- et c'est exactement ce qui s'est produit :
`R07` a ete declaree, documentee, et n'a jamais eu d'implementation.

Ces tests verrouillent les invariants qui rendent le catalogue digne de confiance.
Une regle annoncee qui ne s'execute pas est pire qu'une regle absente : un agent
croit disposer d'un controle qu'il n'a pas.

Lancer :
    py .claude/skills/linting-diva-code/tests/test_coherence_catalogue.py
"""
import importlib.util
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
LINT = os.path.join(SKILL, "scripts", "lint_diva.py")

# Regles actives non encore documentees dans reference/*.md -- dette CONNUE et GELEE.
# Ce test bloque la 10e : toute nouvelle regle doit etre documentee. Ne JAMAIS
# allonger cette liste pour faire passer le test -- documenter la regle a la place.
DETTE_DOC = {"D12", "D13", "D14", "F02", "F03", "F04", "Z14", "Z15", "Z16"}


def charge():
    spec = importlib.util.spec_from_file_location("_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_lint"] = mod
    spec.loader.exec_module(mod)
    return mod


def dispatch_reel(src, mod):
    """{code: {extensions ou la regle est reellement cablee}} d'apres les rule_map."""
    ext_de = {f.__name__: e for e, f in mod.DISPATCHERS.items()}
    out = {}
    for m in re.finditer(r"def (lint_\w+)\(.*?\n(.*?)\n    for rule_id", src, re.S):
        fn, corps = m.group(1), m.group(2)
        for code in re.findall(r'"([A-Z]+\d+)":\s*lambda', corps):
            out.setdefault(code, set()).add(ext_de.get(fn, fn))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    mod = charge()
    src = io.open(LINT, encoding="utf-8").read()
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    declarees = set(mod.RULES)
    dispatchees = dispatch_reel(src, mod)
    actives = set(dispatchees)

    # 1. aucune regle morte : declaree au catalogue mais jamais executee
    mortes = sorted(declarees - actives)
    check("aucune regle MORTE (declaree dans RULES, jamais dispatchee)",
          not mortes,
          "%s -- soit implementer, soit sortir de RULES et marquer *V2*" % mortes)

    # 2. aucune regle fantome : dispatchee sans etre declaree
    fantomes = sorted(actives - declarees)
    check("aucune regle FANTOME (dispatchee sans declaration dans RULES)",
          not fantomes, "%s" % fantomes)

    # 3. RULES['types'] doit decrire les extensions REELLEMENT cablees
    ecarts = []
    for code in sorted(actives & declarees):
        reel = sorted(dispatchees[code])
        dit = sorted(mod.RULES[code].get("types") or [])
        if reel != dit:
            ecarts.append("%s declare %s execute %s" % (code, dit, reel))
    check("RULES['types'] == extensions reellement dispatchees",
          not ecarts, " | ".join(ecarts))

    # 4. la severite declaree doit etre celle qui est emise
    emis = {}
    for m in re.finditer(r'"rule":\s*"([A-Z]+\d+)",\s*"severity":\s*"(\w+)"', src):
        emis.setdefault(m.group(1), set()).add(m.group(2))
    mauvais = []
    for code, sv in sorted(emis.items()):
        declaree = mod.RULES.get(code, {}).get("severity")
        if declaree and (len(sv) > 1 or declaree not in sv):
            mauvais.append("%s declare %s emet %s" % (code, declaree, sorted(sv)))
    check("severite declaree == severite emise", not mauvais, " | ".join(mauvais))

    # 5. les regles V2 (reportees) ne doivent PAS etre declarees dans RULES
    #    -- c'est la convention du skill, et c'est celle que R07 violait.
    skill = io.open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
    m = re.search(r"Necessitent analyse semantique ou cross-file\s*:\s*([^\r\n]+)", skill)
    v2 = set()
    if m:
        for tok in re.findall(r"([A-Z]+)(\d+)(?:-[A-Z]*(\d+))?", m.group(1)):
            fam, a, b = tok[0], int(tok[1]), tok[2]
            for n in range(a, (int(b) if b else a) + 1):
                v2.add("%s%02d" % (fam, n))
    check("la liste V2 du SKILL.md a pu etre lue", bool(v2), "regex a vide")
    intruses = sorted(v2 & declarees)
    check("aucune regle V2 declaree dans RULES", not intruses,
          "%s -- une regle reportee ne doit pas figurer au catalogue actif" % intruses)

    # 6. toute regle active doit etre documentee dans reference/*.md
    ref = os.path.join(SKILL, "reference")
    doc = "".join(io.open(os.path.join(ref, f), encoding="utf-8").read()
                  for f in sorted(os.listdir(ref)) if f.endswith(".md"))
    nondoc = {c for c in actives if not re.search(r"\b" + c + r"\b", doc)}
    nouvelles = sorted(nondoc - DETTE_DOC)
    check("aucune NOUVELLE regle non documentee dans reference/*.md",
          not nouvelles,
          "%s -- documenter la regle (ne pas l'ajouter a DETTE_DOC)" % nouvelles)
    resorbees = sorted(DETTE_DOC - nondoc)
    check("DETTE_DOC a jour (pas de regle documentee restee dans la liste)",
          not resorbees,
          "%s desormais documentee(s) : les retirer de DETTE_DOC" % resorbees)

    print()
    print("  declarees=%d  actives=%d  dette doc=%d" % (len(declarees), len(actives), len(nondoc)))
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
