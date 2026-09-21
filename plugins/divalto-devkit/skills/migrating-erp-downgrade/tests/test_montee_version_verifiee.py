#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de la page « montee de version d'une surcharge » -- #230.

Le retour terrain avait reconstruit la semantique de deux actions `xwin7` en extrayant les
chaines du binaire. Nous avons refait la mesure plutot que de le croire : **tout ce qu'il
annonce se verifie**, y compris son point le plus utile -- `-Base_Nm1` **n'existe pas**.

Ce que ces cas gardent, et pourquoi :

- **Le piege `-Base_Nm1`** (cas 2). C'est le seul point de la page qu'un agent effacerait
  « par bon sens » : la paire `-OverLoad_Nm1` / `-OverLoad_N` appelle un `-Base_Nm1` qui
  n'existe pas. Le cas garde **l'interdiction ET sa preuve**.
- **Les trois niveaux de preuve** (cas 3 et 4). La page distingue ce qui est verifie dans le
  binaire, ce qui est observe dans un journal, et ce qui est **rapporte sans reproduction**.
  Effacer ces marques rendrait la page plus lisse et moins vraie.
- **La reference reste unique** (cas 6). La table de `compiling-diva-projects` **nomme** les
  deux actions -- c'est la que le partenaire les a cherchees -- et **renvoie** ; elle ne
  duplique pas la syntaxe. Deux pages qui expliquent la meme chose divergent.
- **Aucune trace interne** (cas 7) : ni URL de wiki interne, ni chemin de poste, ni nom de
  client. La page part chez le partenaire.

Lancer :
    py plugin/skills/migrating-erp-downgrade/tests/test_montee_version_verifiee.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
PAGE = os.path.join(SKILL, "reference", "montee-version-surcharge.md")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
SYNTAXE = os.path.abspath(os.path.join(
    SKILL, "..", "compiling-diva-projects", "reference", "xwin7-syntax.md"))

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


# Decouper un markdown en phrases demande DEUX precautions, apprises l'une apres l'autre :
#   1. le gras met en defaut la ponctuation seule -- apres `mot.**` le caractere avant
#      l'espace est `*`, pas `.`, donc aucune coupure ;
#   2. mais couper sur CHAQUE fin de ligne est l'exces inverse : dans un fichier a la ligne
#      dure, une phrase traverse les retours a la ligne, et son verbe de negation peut
#      tomber sur la ligne suivante. C'est arrive ici : « ...un `-Base_Nm1` **qui n'existe /
#      pas** » etait lu comme une phrase qui PRESCRIT le parametre.
# On recolle donc les lignes d'un meme paragraphe, en gardant separes les blocs qui ont un
# sens propre : items de liste, lignes de tableau, titres, citations, blocs de code.
#   3. et une citation (`>`) est un paragraphe comme un autre : couper a chacune de ses
#      lignes la hacherait. On retire donc le marqueur de citation AVANT de decouper.
BLOC = re.compile(r"\n\s*\n|\n(?=\s*(?:[-*#|]|\d+\.|```))")
FIN_DE_PHRASE = re.compile(r"(?<=[.!?])[*_`)\]]*\s+")


def phrases(texte):
    texte = re.sub(r"^[ \t]*>[ \t]?", "", texte, flags=re.M)
    out = []
    for bloc in BLOC.split(texte):
        bloc = re.sub(r"\s*\n\s*", " ", bloc)
        out.extend(p for p in FIN_DE_PHRASE.split(bloc) if p.strip())
    return out


# --------------------------------------------------------------------- les cas

@cas("1. Les deux actions sont nommees, avec leurs parametres")
def cas1():
    t = lire(PAGE)
    for action in ("creerprojetsurcharge", "mettreAJourMasquesSurcharge"):
        assert action in t, "l'action %s a disparu de la page" % action
    # Chercher le parametre DANS SA LIGNE DE TABLEAU : la plupart sont aussi cites dans la
    # demarche ou les encadres, donc « present dans la page » survit a la suppression de sa
    # ligne de documentation. Une mutation l'a montre.
    lignes = [l for l in t.split("\n") if l.startswith("| `-")]
    documentes = {re.match(r"\| `(-\w+)", l).group(1) for l in lignes
                  if re.match(r"\| `(-\w+)", l)}
    for p in ("-Base_N", "-OverLoad_Nm1", "-OverLoad_N", "-AnalyzeOnly", "-ClearFUpgrade",
              "-pack", "-OverLoad"):
        assert p in documentes, \
            "le parametre %s n'a plus de ligne dans un tableau de parametres" % p
    return "2 actions, %d parametres documentes en tableau" % len(documentes)


@cas("2. `-Base_Nm1` est interdit, ET la preuve de son inexistence est donnee")
def cas2():
    t = lire(PAGE)
    assert "-Base_Nm1" in t, \
        "le piege n'est plus nomme -- il sera reinvente par symetrie avec -OverLoad_Nm1"
    # Il ne doit apparaitre QUE dans des phrases qui le refutent.
    REFUS = ("n'existe pas", "ne pas", "zero occurrence", "piege", "refusera", "inventer")
    fautives = [p for p in phrases(t)
                if "-Base_Nm1" in p and not any(m in p.lower() for m in REFUS)]
    assert not fautives, ("phrase(s) qui presentent -Base_Nm1 comme utilisable :\n         %s"
                          % "\n         ".join(f[:140] for f in fautives))
    assert "zero occurrence" in t.lower(), \
        "l'interdiction n'est plus etayee : sans la mesure, c'est une opinion"
    return "nomme, refute dans chacune de ses phrases, et etaye"


@cas("3. Les trois niveaux de preuve sont declares et utilises")
def cas3():
    t = lire(PAGE)
    for marque in ("[binaire]", "[observe]", "[rapporte]"):
        n = t.count(marque)
        assert n >= 2, ("la marque %s n'est plus utilisee que %d fois : la page redevient "
                        "un bloc d'affirmations de meme poids" % (marque, n))
    assert "executer" in t.lower(), \
        "la page n'explique plus POURQUOI certains points restent rapportes"
    return "binaire %d, observe %d, rapporte %d" % (t.count("[binaire]"), t.count("[observe]"),
                                                    t.count("[rapporte]"))


@cas("4. Ce qui n'a pas ete reproduit reste marque comme tel")
def cas4():
    # Ancrer sur LA PHRASE qui porte le point, pas sur une fenetre de caracteres : une
    # fenetre large attrape la marque d'un point VOISIN et le cas survit a la mutation.
    # Une mutation l'a montre -- passer ce point-ci en [observe] ne le faisait pas tomber.
    t = lire(PAGE)
    for ancre, libelle in (("Conservation de la surcharge", "le vocabulaire non observe"),
                           ("cosmetique", "le code de sortie")):
        portantes = [p for p in phrases(t) if ancre.lower() in p.lower()]
        assert portantes, "%s n'est plus cite dans la page" % libelle
        assert all("[rapporte]" in p for p in portantes), \
            ("%s est presente comme etabli alors qu'il n'a pas ete reproduit :\n         %s"
             % (libelle, "\n         ".join(p[:140] for p in portantes)))
    return "les deux points non reproduits portent leur marque, dans leur phrase"


@cas("5. La demarche impose l'analyse a blanc et un run par projet")
def cas5():
    t = lire(PAGE)
    assert "-AnalyzeOnly" in t and "n'ecrit rien" in t, \
        "l'analyse a blanc n'est plus prescrite comme premiere etape"
    assert "-ClearFUpgrade" in t and "precedent" in t.lower(), \
        "la raison de vider le journal a disparu : sans elle, on lit le run d'avant"
    assert re.search(r"un run par [`\s]*\.?dhpt", t, re.I), \
        "le perimetre par projet n'est plus dit"
    return "analyse a blanc, journal vide, un run par projet"


@cas("6. La table de syntaxe NOMME les actions et RENVOIE, sans dupliquer")
def cas6():
    t = lire(SYNTAXE)
    for action in ("creerprojetsurcharge", "mettreAJourMasquesSurcharge"):
        assert action in t, ("%s absente de la table des actions -- c'est la page ou le "
                             "partenaire l'a cherchee" % action)
    assert "montee-version-surcharge.md" in t, "la table ne renvoie pas vers la page detaillee"
    # Elle ne doit PAS reexpliquer la syntaxe : sinon deux pages a maintenir.
    for detail in ("-Base_Nm1", "-ClearFUpgrade", "-OverLoad_Nm1"):
        assert detail not in t, \
            ("la table de syntaxe redocumente %s : la reference se dedouble et divergera"
             % detail)
    return "nomme et renvoie, sans dupliquer la syntaxe"


@cas("7. Aucune trace interne dans une page distribuee")
def cas7():
    INTERDITS = (
        (r"atlassian\.net", "URL de wiki interne"),
        (r"confluence", "renvoi Confluence"),
        (r"Developpements[ _]Harmony", "chemin du poste de l'editeur"),
        (r"[A-Za-z]:\\{1,2}(?![Dd]ivalto\\)[^\s`)\"']+", "chemin absolu hors racine produit"),
    )
    for f in (PAGE, SKILL_MD):
        texte = lire(f)
        for motif, libelle in INTERDITS:
            m = re.search(motif, texte, re.I)
            assert not m, "%s : %s -- %r" % (os.path.basename(f), libelle, m.group(0)[:60])
    return "ni wiki interne, ni chemin de poste"


@cas("8. Le SKILL.md porte l'essentiel et renvoie a la page")
def cas8():
    t = lire(SKILL_MD)
    assert "montee-version-surcharge.md" in t, "le SKILL.md ne renvoie pas a la page"
    for piege in ("-Base_N", "-Base_Nm1", "FUpgrade.log"):
        assert piege in t, ("le piege %s n'est plus visible depuis le SKILL.md : il faudrait "
                            "ouvrir la page pour le decouvrir" % piege)
    assert "CIBLE" in t, "le sens de -Base_N, le piege le plus couteux, a disparu du sommaire"
    n = t.count("\n") + 1
    assert n < 500, "SKILL.md depasse la limite de 500 lignes : %d" % n
    return "%d lignes, les 3 pieges visibles des le SKILL.md" % n


@cas("9. La tension du nom est assumee, pas tue")
def cas9():
    t = lire(PAGE)
    assert "downgrade" in t.lower() and "bidirectionnel" in t.lower(), \
        ("la page ne dit plus pourquoi une MONTEE de version est documentee dans un skill "
         "nomme downgrade -- le lecteur ira chercher ailleurs")
    return "l'ambiguite du nom est traitee en tete"


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
    print()
    if echecs:
        print("BILAN : %d/%d cas en ECHEC" % (len(echecs), len(CAS)))
        for t in echecs:
            print("  - %s" % t)
        sys.exit(1)
    print("BILAN : %d/%d cas OK" % (len(CAS), len(CAS)))


if __name__ == "__main__":
    main()
