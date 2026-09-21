#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables : cibler l'overlay `*u` et non le fichier standard.

, RETEX #228 et #250.

Aucune DLL requise : l'avertissement se decide sur le **nom** du fichier cible.

Le defaut rejoue : une ecriture custom qui vise un fichier livre par Divalto sera
**ecrasee** a la prochaine montee de version. Deux fichiers standard ont un **overlay**
(`a5f` -> `a5fu` pour les zooms, `g3f` -> `g3fu` pour le menu) ; pour tous les autres il
n'y a PAS d'overlay et le partenaire gere son **propre** fichier. Ce sont deux regles
distinctes -- les confondre donnerait un mauvais conseil, d'ou une liste **explicite**
plutot qu'une deduction sur le nom.

Lancer :
    py .claude/skills/writing-isam-files/tests/run_all.py
"""
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(SKILL, "scripts")

_w = importlib.util.spec_from_file_location("_wi", os.path.join(SCRIPTS, "write_isam.py"))
W = importlib.util.module_from_spec(_w)
_w.loader.exec_module(W)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


# --------------------------------------------------------------------------

@cas("1. #228 : viser a5f.dhfi ou g3f.dhfi declenche l'avertissement")
def cas1():
    for nom, overlay in (("a5f.dhfi", "a5fu"), ("g3f.dhfi", "g3fu")):
        m = W.avertissement_overlay(os.path.join("C:", "peu", "importe", nom))
        assert m, "aucun avertissement pour %s" % nom
        assert overlay in m, "l'overlay a viser doit etre nomme : %s" % m
        assert "ECRASEE" in m, "la consequence (ecrasement) doit etre dite : %s" % m
    return "le message nomme la cible correcte ET la consequence"


@cas("2. #228 : viser l'overlay lui-meme ne declenche RIEN")
def cas2():
    for nom in ("a5fu.dhfi", "g3fu.dhfi"):
        assert W.avertissement_overlay(nom) is None, (
            "%s est la bonne cible : aucun avertissement ne doit sortir" % nom)
    return "sinon l'avertissement crierait sur le cas correct et serait ignore"


@cas("3. L'overlay ne se DEDUIT pas du nom : les autres fichiers sont muets")
def cas3():
    for nom in ("gtfdmc.dhfi", "a5mf.dhfi", "c3f.dhfi", "xlog.dhfi", "gtfjq.dhfi"):
        assert W.avertissement_overlay(nom) is None, (
            "%s n'a pas d'overlay connu : la regle y est le fichier PROPRE du "
            "partenaire, pas un '*u' invente" % nom)
    return "liste explicite (a5f, g3f), pas de generalisation sur le suffixe"


@cas("4. La detection est insensible a la casse et au chemin")
def cas4():
    for chemin in (r"C:\ERP\Achat-Vente\fichier\G3F.DHFI",
                   "/mnt/erp/achat-vente/fichier/g3f.dhfi",
                   r"..\..\A5F.dhfi"):
        assert W.avertissement_overlay(chemin), "non detecte : %s" % chemin


@cas("5. La liste des fichiers a overlay est courte et explicite")
def cas5():
    assert W.FICHIERS_AVEC_OVERLAY == {"a5f": "a5fu", "g3f": "g3fu"}, (
        "toute addition doit etre justifiee par une confirmation, pas par analogie : %s"
        % W.FICHIERS_AVEC_OVERLAY)
    src = lire(os.path.join(SCRIPTS, "write_isam.py"))
    assert "PAS d'overlay" in src, (
        "le code doit rappeler que les autres fichiers n'ont pas d'overlay")


@cas("6. #250 : la reference du zoom dit d'ecrire dans a5fu, pas a5f")
def cas6():
    t = lire(os.path.join(SKILL, "reference", "a5f-zoom-record.md"))
    assert "a5fu.dhfi`, pas `a5f.dhfi" in t or "a5fu" in t and "Jamais modifie" in t
    assert "arborescence specifique" in t, "l'emplacement de l'overlay doit etre dit"
    assert "union" in t.lower(), "le lien avec l'allocation (union) doit etre fait"
    return "structure de l'enregistrement ET fichier cible, sur la meme page"


@cas("7. Les deux regles distinctes sont documentees, et atteignables du SKILL.md")
def cas7():
    """Le detail vit en `reference/` (progressive disclosure, SKILL.md < 500 lignes),
    mais le SKILL.md doit porter l'essentiel ET le lien."""
    skill = lire(os.path.join(SKILL, "SKILL.md"))
    assert "reference/cible-overlay.md" in skill, "la page de detail doit etre citee"
    assert "overlay" in skill.lower() and "propre" in skill.lower(), (
        "le SKILL.md doit deja opposer overlay et fichier propre du partenaire")
    assert "dry-run" in skill, "l'avertissement en dry-run doit etre annonce des le SKILL.md"

    page = lire(os.path.join(SKILL, "reference", "cible-overlay.md"))
    assert "pas refus" in page.lower(), (
        "la page doit dire que l'ecriture reste possible si elle est intentionnelle")
    assert "arborescence specifique" in page, "l'emplacement de l'overlay doit y figurer"
    return "essentiel + lien dans le SKILL.md, detail dans la page de reference"


@cas("8. #228 : le skill du menu documente l'union g3f + g3fu")
def cas8():
    p = os.path.abspath(os.path.join(SKILL, "..", "allocating-menu-enrno", "SKILL.md"))
    t = lire(p)
    assert "g3fu" in t, "le skill du menu ignorait totalement l'overlay"
    assert "UNION" in t or "union" in t, "le used-set doit etre dit union"
    assert "--g3fu" in t, "l'option doit etre montree"
    assert "Doublons" in t or "doublon" in t.lower(), (
        "les doublons g3f/g3fu sont normaux -- il faut le dire, sinon ils seront pris "
        "pour des collisions")
    return "meme traitement que a5f/a5fu chez son voisin, enfin aligne"


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
