#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de coherence de la page RecordSql.

RETEX #162 #163 #232 #271 #298 #317 #325.

Meme principe que les deux suites precedentes : l'orchestrateur LLM interroge le graphe et
consigne, la suite verifie **hors ligne** que la page et le releve concordent.

Ce que ce lot a appris et que les cas gardent :

- La section `Collate` etait **fausse sur trois points** parce qu'elle avait ete ecrite de
  memoire. Le cas 2 exige la signature exacte, le cas 3 le mecanisme reel (un moteur de
  ruptures, pas une boucle ou l'on ecrit son traitement), et le cas 4 la consigne de **ne
  pas l'etendre de memoire**.
- La page **enseignait un anti-pattern** : `AddCondition(nom, 'sql_brut')`. Le cas 6 le
  garde ferme.
- L'inversion des conventions de retour est **masquee par le corpus** : le cas 7 exige que
  la page le dise avec ses chiffres.
- Une regle de lint a ete **mesuree puis ecartee** (81 faux positifs sur le standard) : le
  cas 10 verifie que la mesure et le verdict restent ecrits, pour qu'on ne la reintroduise
  pas sans relire.

Lancer :
    py .claude/skills/coding-diva-advanced/tests/run_all.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _communs import lire, nu, plat  # noqa: E402  (helpers partages, cf. _communs.py)
SKILL = os.path.abspath(os.path.join(HERE, ".."))
SKILLS = os.path.abspath(os.path.join(SKILL, ".."))
PAGE = os.path.join(SKILL, "reference", "recordsql-advanced.md")
RELEVE = os.path.join(SKILL, "reference", "keywords-verifies.json")
PAGE_CI = os.path.join(SKILLS, "linting-diva-code", "reference", "rules-ci.md")
LINTER = os.path.join(SKILLS, "linting-diva-code", "scripts", "lint_diva.py")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def releve():
    return json.loads(lire(RELEVE))


# --------------------------------------------------------------------------

@cas("1. Les 5 fonctions Collate sont au releve, verifiees en direct")
def cas1():
    e = releve()["existe"]
    fns = ("collateopen", "collateaddrecordsql", "collatenext", "collateclose",
           "collateprogressbar")
    manquantes = [f for f in fns if f not in e]
    assert not manquantes, "absente(s) du releve : %s" % manquantes
    indirectes = [f for f in fns if e[f]["confiance"] != "direct"]
    assert not indirectes, ("l'API Collate est le defaut d'origine de #317 : elle doit etre "
                            "verifiee en DIRECT, pas citee -- %s" % indirectes)
    return "5 fonctions, toutes en preuve directe"


@cas("2. La signature de `CollateAddRecordSQL` est complete et ordonnee")
def cas2():
    t = nu(plat(PAGE))
    for p in ("idCollate", "Name", "ProcBegin", "ProcEnd", "ProcDetail", "FuncKey",
              "ModuleName"):
        assert p in t, "parametre %s absent de la page" % p
    assert "ModuleName]" in t or "[, ModuleName" in t, (
        "l'optionalite de ModuleName doit etre visible -- c'est ce que le manuel rend mal")
    assert "sous forme de chaine" in t, (
        "Name est le NOM du RecordSql en chaine : c'est le piege principal de #317")
    return "7 parametres, optionalite et nature de Name dites"


@cas("3. La page dit ce que `Collate` EST : un moteur de ruptures")
def cas3():
    """L'ancienne version decrivait une boucle de fusion. Le code n'aurait rien fait."""
    t = nu(plat(PAGE))
    assert "moteur de ruptures" in t, (
        "sans ca, un lecteur ecrit une boucle et se demande pourquoi rien ne se passe")
    for mot in ("ProcBegin", "ProcDetail", "callbacks"):
        assert mot in t, "%s absent : le travail se fait dans les procedures" % mot
    assert "H_EOF" in t, "la sentinelle nommee de CollateNext"
    assert "heterogenes" in t and "meme" in t, (
        "la seule obligation entre RecordSql : le meme critere de tri")
    assert "AVANT d'ajouter" in t or "AVANT l'appel" in t, (
        "CollateAddRecordSQL execute le ReaderSelect : tri et filtrage AVANT")
    return "mecanisme, callbacks, H_EOF, regle de tri, ordre des operations"


@cas("4. La section Collate porte sa provenance et l'interdiction de l'etendre de memoire")
def cas4():
    """C'est la reponse de fond a #317 : le defaut venait de la paraphrase."""
    t = nu(plat(PAGE))
    assert "ne recopie pas le manuel" in t, (
        "dire que la section ne duplique pas le manuel")
    assert "Ne PAS l'etendre de memoire" in t or "ne PAS l'etendre de memoire" in t, (
        "l'interdiction explicite : c'est la paraphrase de memoire qui a produit le defaut")
    assert "Ycollate.dhop" in t, "le module porteur"
    assert "get_native_keyword_doc" in t, "le moyen de re-verifier"
    return "provenance, module, moyen de re-verification"


@cas("5. `Where.<X>` est presente comme un `Case`, genere ou declare")
def cas5():
    t = nu(plat(PAGE))
    assert "toujours un Case" in t, (
        "unifier les deux formes : il n'y a pas deux API, c'est la meme")
    assert "declarez dans un .dhsq" in t or "vous declarez" in t, (
        "la voie normale pour un critere maison")
    return "les deux formes unifiees"


@cas("6. L'anti-pattern SQL brut est nomme et ferme")
def cas6():
    """La page le presentait comme un usage normal."""
    t = nu(plat(PAGE))
    assert "A NE PAS FAIRE" in t, "le contre-exemple doit etre marque comme tel"
    assert "Ne PAS injecter de SQL brut" in t, "titre explicite"
    assert "OverWrite=" in t, (
        "la voie de remplacement : declarer un Case dans une surcharge .dhsq")
    # Et la table des fonctions ne doit plus vendre AddCondition comme du SQL brut
    for ligne in lire(PAGE).split("\n"):
        if ligne.lstrip().startswith("|") and "AddCondition(nom" in ligne:
            assert "brute" not in ligne.lower() and "sql" not in ligne.lower(), (
                "la ligne de tableau vend encore AddCondition comme du SQL brut : %s" % ligne)
    return "contre-exemple, titre, voie de remplacement, tableau nettoye"


@cas("7. Le contrat de la condition dit les DEUX facons de perdre le filtre")
def cas7():
    t = nu(plat(PAGE))
    assert "n'entre dans le WHERE que par AddCondition" in t, (
        "le contrat en une phrase")
    assert "incomplet" in t and "quasi non filtree" in t, (
        "les deux oublis n'ont pas la meme consequence : un filtre incomplet, ou aucun filtre")
    assert "aucune erreur" in t.lower(), (
        "le point qui rend le piege couteux : rien ne le signale")
    return "contrat + les deux modes de perte + le silence"


@cas("8. Les trois conventions de retour sont dites, avec leurs mesures")
def cas8():
    m = releve()["mesures_graphe"]["conventions_de_retour"]
    t = nu(plat(PAGE))
    assert m["instance_select_teste_egal_zero"] == 0, m
    for val in ("642", "628", "3 181", "7"):
        assert val in t, "mesure %s absente de la page" % val
    assert "non-zero" in t, "la convention des methodes d'instance"
    assert "<> 0" in t, "la forme correcte du test"
    # Les 7 usages ont ete lus : 4 en commentaire, et deux vivants comparent a une
    # constante LOCALE. Recommander SQL_RESULTOK par mimetisme donnerait Erreur 99.
    assert "SQL_RESULTOK" in t, "la forme rencontree dans le standard doit etre nommee"
    assert "n'est PAS une constante generale" in t, (
        "l'avertissement est le point utile : la constante n'est declaree que dans 2 "
        "programmes, en portee root")
    assert "test de verite nu" in t, "la forme portable"
    return "3 familles, mesures citees, piege SQL_RESULTOK ferme"


@cas("9. La question du socle d'audit reste declaree NON VERIFIEE")
def cas9():
    """#271 laisse une question ouverte qui demande un test a l'execution."""
    nv = releve()["non_verifie"]
    assert "socle_audit_de_la_methode_update" in nv, (
        "la question du partenaire doit rester consignee, pas disparaitre")
    t = nu(plat(PAGE))
    assert "NON VERIFIE" in t, "la page doit signaler l'incertitude la ou on la rencontre"
    assert "UserMo" in t, "nommer les champs concernes"
    assert "preferer la fonction generee" in t, (
        "une incertitude doit venir avec une consigne provisoire, pas seulement un doute")
    return "incertitude consignee, nommee, et assortie d'une consigne"


@cas("10. L'angle mort de CI03 est documente, avec la mesure qui ecarte la regle")
def cas10():
    m = releve()["mesures_graphe"]["angle_mort_ci03"]
    assert m["candidats_restants"] == 81, m
    doc = nu(plat(PAGE_CI))
    assert "ANGLE MORT" in doc, "l'angle mort doit etre nomme dans la fiche de la regle"
    for val in ("3 456", "223", "142", "81"):
        assert val in doc, "mesure %s absente de la fiche CI03" % val
    assert "par adresse" in doc, (
        "la raison des faux positifs : l'accumulateur est souvent un &parametre")
    assert "silence de CI03" in doc, (
        "dire explicitement qu'un CI03 muet ne valide pas le filtre")
    code = lire(LINTER)
    assert "ANGLE MORT ASSUME" in code, (
        "le code doit porter l'avertissement : sinon un futur lecteur 'corrige' la regle "
        "sans relire la mesure")
    return "fiche + code, 4 mesures, cause des faux positifs"


@cas("11. La surcharge du critere de zoom : deux cas, confrontes a du code reel")
def cas11():
    t = nu(plat(PAGE))
    # Confronte a une surcharge de PRODUCTION le 2026-08-28 : la page presentait le
    # masquage comme LA technique, alors que le cas courant est purement ADDITIF.
    assert "Deux cas" in t, (
        "il y a deux cas -- ajouter (courant) et supprimer (rare) : les confondre a produit "
        "une page qui compliquait le cas simple")
    assert "le simple est le plus frequent" in t, "dire lequel est courant"
    assert "aucune ruse" in t, "le cas additif ne demande pas de masquage"
    assert "Standard.Construire_Condition_Selection(nom, premier)" in t, (
        "le standard est appele EN PREMIER dans la forme observee")
    assert "nom de condition distinct" in t or "Nom de condition distinct" in t, (
        "AddCondition est indexe par nom : reutiliser le nom standard l'ecrase")
    assert "Ajouter_Condition(" in t, (
        "la variante d'accumulation employee par la production doit etre citee")
    assert "119" in t and "3 456" in t, (
        "dire laquelle domine : 119 routines pour le helper contre 3456 -- sinon on croit "
        "avoir trouve l'idiome principal")
    assert "non observee en production" in t, (
        "le filtrage sur `nom` est notre precaution, PAS une pratique observee : le dire")
    return "deux cas distingues, ordre observe, helper chiffre, precaution marquee"


@cas("15. #162 : la forme du standard est mesuree, la technique est dite DERIVEE")
def cas15():
    """Distinguer ce qui est mesure de ce qui est deduit.

    L'ossature du standard est mesuree sur 1125 occurrences. Le squelette de surcharge, lui,
    n'a PAS ete compile -- et il n'y a aucun module de surcharge dans le standard, donc rien
    a lire. Presenter les deux au meme niveau serait une sur-affirmation : la question a ete
    posee par l'architecte, et la page ne la portait pas.
    """
    m = releve()["mesures_graphe"]["construire_condition_selection"]
    assert m["occurrences"] == 1125 and m["protegees"] == 2, m
    t = nu(plat(PAGE))
    for val in ("1 125", "1 051", "1 064", "1 071"):
        assert val in t, "mesure %s absente de la page" % val
    assert "non extrapole" in t or "n'est donc pas extrapole" in t, (
        "dire que l'ossature n'est pas tiree d'un seul exemple")
    # Le statut a EVOLUE : la forme du cas 1 a ete confrontee a une surcharge de production
    # (donc plus « deduite »), mais elle n'est toujours pas compilee par nous -- et le cas 2
    # reste, lui, une deduction. Les trois niveaux doivent rester distincts.
    assert "observee dans une surcharge de production" in t, (
        "le cas 1 n'est plus une deduction : le dire")
    assert "pas ete compilee par nous" in t, (
        "observee n'est pas compilee : la limite subsiste")
    assert "reste, lui, deduit" in t or "reste, lui, **deduit**" in t, (
        "le cas 2 (suppression) n'a PAS ete observe : ne pas lui preter le meme statut")
    assert "aucun module de surcharge dans le standard" in t, (
        "dire POURQUOI on ne peut pas recouper une seconde fois")
    assert "limite_de_verification" in json.dumps(m, ensure_ascii=False), (
        "la limite doit etre consignee au releve, pas seulement dans la page")
    return "1125 occurrences mesurees, technique marquee derivee"


@cas("12. `Erreur 27` : la cause et l'endroit ou regarder")
def cas12():
    t = nu(plat(PAGE))
    assert "Erreur 27" in t, "le message reellement obtenu"
    assert "jointures" in t or "joint" in t, "la cause : les jointures internes du RecordSql"
    assert "n'expose pas" in t, (
        "dire que le graphe ne porte PAS cette structure -- sinon on cherche au mauvais endroit")
    assert ".dhsq" in t, "l'endroit ou regarder"
    return "message, cause, limite du graphe, source a lire"


@cas("13. La page ne renvoie plus vers une reference « interne »")
def cas13():
    """Un partenaire n'a pas acces a une reference interne : le renvoi etait mort."""
    t = lire(PAGE)
    assert "(interne)" not in t, (
        "renvoi vers une reference inaccessible a un partenaire")
    assert "syntaxe-de-base.md" in t, "le renvoi utile, livre au LOT A"
    return "renvoi mort remplace"


@cas("14. Tous les liens de la page resolvent")
def cas14():
    base = os.path.dirname(PAGE)
    casses = [c for c in re.findall(r"\]\(([^)#]+\.md)\)", lire(PAGE))
              if not os.path.isfile(os.path.normpath(os.path.join(base, c)))]
    assert not casses, "lien(s) casse(s) : %s" % casses
    return "liens verifies"


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
