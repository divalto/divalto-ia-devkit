#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de coherence des pages d'appel inter-programmes.

RETEX #176 #178 #318 #319.

Meme principe que les autres suites du skill : l'orchestrateur LLM interroge le graphe et
consigne dans `reference/keywords-verifies.json`, la suite verifie **hors ligne** que les
pages et le releve concordent. Les scripts du plugin n'appellent jamais le MCP.

Ce que ce lot a appris, et que les cas gardent :

- La page `overwrite-pattern.md` **inversait le sens de la dependance** entre les deux
  modules qu'elle donnait en exemple, alors que le bloc de code juste au-dessus etait
  juste. Le cas 10 tombe sur l'etat d'avant, dans les deux sens : il exige la bonne phrase
  **et** interdit la mauvaise.
- Deux des quatre RETEX proposaient un **diagnostic** en plus de leur observation. Celui de
  #319 est une regle juste par correlation : 100 % du standard ecrit l'extension, donc le
  nom nu « ne fonctionne pas ». La mesure ne dit pas ca. Le cas 4 garde les **deux** sens :
  la mise en garde doit etre presente, et l'affirmation d'echec doit rester absente.
- Les pages citent des **mesures**. Une page qui derive des chiffres qui la fondent est
  pire qu'une page sans chiffres : les cas 3, 6 et 11 les confrontent au releve.
- Le controle d'anonymisation est **structurel** (pas de chemin absolu, pas d'adresse
  mail), et non une liste noire de noms de clients : cette suite est distribuee avec le
  skill, et y ecrire les noms qu'on veut proteger les publierait.

Lancer :
    py .claude/skills/coding-diva-advanced/tests/run_all.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _communs import lire, nu, plat  # noqa: E402  (helpers partages, cf. _communs.py)

SKILL = os.path.abspath(os.path.join(HERE, ".."))
SKILLS = os.path.abspath(os.path.join(SKILL, ".."))
PAGE_TUN = os.path.join(SKILL, "reference", "tunnels.md")
PAGE_SUR = os.path.join(SKILL, "reference", "overwrite-pattern.md")
RELEVE = os.path.join(SKILL, "reference", "keywords-verifies.json")
PAGE_ERR = os.path.join(SKILLS, "compiling-diva-projects", "reference",
                        "compilation-errors.md")

# Pages que CE lot ecrit -- perimetre du controle d'anonymisation (cas 13).
PAGES_DU_LOT = (PAGE_TUN, PAGE_SUR)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def releve():
    return json.loads(lire(RELEVE))


def milliers(n):
    """1306 -> '1 306'. Les pages ecrivent les grands nombres avec une espace."""
    return "{:,}".format(n).replace(",", " ")


# --------------------------------------------------------------------------

@cas("1. Le releve porte les trois blocs de mesures du lot, dates et rattaches a leur page")
def cas1():
    m = releve()["mesures_graphe"]
    attendus = {
        "programcall": "tunnels.md",
        "contexte_tunnel_xq": "tunnels.md",
        "portee_module_donnees": "overwrite-pattern.md",
    }
    manquants = [b for b in attendus if b not in m]
    assert not manquants, "bloc(s) absent(s) du releve : %s" % manquants
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", m["date"]), "le releve doit porter une date"
    for bloc, page in attendus.items():
        pages = m[bloc].get("_page") or m[bloc].get("_pages")
        assert page in (pages if isinstance(pages, list) else [pages]), (
            "le bloc %s ne dit pas quelle page il fonde" % bloc)
    assert "tunnels.md" in m["_note"], (
        "la note du releve doit citer les pages qui s'appuient dessus, tunnels.md comprise")
    return "3 blocs, dates au %s, chacun rattache a sa page" % m["date"]


@cas("2. tunnels.md ENONCE la regle .dhop, au lieu de la suivre en silence")
def cas2():
    """Avant ce lot la page ecrivait deja ProgramCall(\"MONPROG.dhop\") dans son exemple.

    Un exemple conforme n'est pas une regle : le lecteur qui ecrit le nom nu n'a rien
    a quoi se raccrocher. Le cas exige donc une PHRASE, pas la seule presence de
    l'extension dans un bloc de code.
    """
    t = nu(plat(PAGE_TUN))
    assert "Regle : ecrire ProgramCall('monprogramme.dhop')" in t, (
        "la regle doit etre enoncee, pas seulement illustree")
    assert "jamais ProgramCall('monprogramme')" in t, (
        "nommer explicitement la forme a ne pas ecrire")
    return "regle enoncee, forme fautive nommee"


@cas("3. Les chiffres ProgramCall de la page concordent avec le releve")
def cas3():
    b = releve()["mesures_graphe"]["programcall"]
    t = nu(plat(PAGE_TUN))
    for cle, libelle in (("sites_appel_vivants", "sites vivants"),
                         ("litteral_avec_extension", "litteraux avec extension"),
                         ("litteral_sans_extension", "litteraux sans extension"),
                         ("via_variable_ou_expression", "via variable")):
        assert milliers(b[cle]) in t, (
            "la page ne porte pas le chiffre %s (%s = %d)" % (libelle, cle, b[cle]))
    assert b["litteral_sans_extension"] == 0, (
        "si un jour un appel sans extension apparait dans le standard, la regle doit etre "
        "reexaminee, pas recopiee")
    return "4 chiffres concordants (%d / %d / %d / %d)" % (
        b["sites_appel_vivants"], b["litteral_avec_extension"],
        b["litteral_sans_extension"], b["via_variable_ou_expression"])


@cas("4. La page ne transforme PAS la correlation en echec du nom nu")
def cas4():
    """Garde les deux sens.

    Sens 1 -- la mise en garde doit etre la : sans elle, le lecteur comprend que la forme
    nue plante, ce que personne n'a mesure.
    Sens 2 -- l'affirmation d'echec doit rester absente. C'est le sens qui tombe si
    quelqu'un « simplifie » la page en reprenant la formulation du RETEX.
    """
    t = nu(plat(PAGE_TUN))
    assert "Ce qui n'est pas etabli" in t, "la limite de la preuve doit etre ecrite"
    assert "regle de conformite au standard, pas un theoreme sur le runtime" in t, (
        "dire la NATURE de la regle : conformite, pas comportement du runtime")
    for interdit in ("ne fonctionne pas de maniere fiable",
                     "ne fonctionne pas sans extension"):
        assert interdit not in t.lower(), (
            "la page affirme un echec non mesure : %r" % interdit)
    # Controle fin : toute PHRASE qui parle du nom nu doit porter sa reserve.
    # Une premiere version interdisait la chaine « le nom nu echoue » n'importe ou dans la
    # page -- et tombait sur la mise en garde elle-meme (« Ce qui n'est pas etabli : que le
    # nom nu echoue »). Un controle qui interdit de NOMMER ce qu'on refute est inutilisable.
    reserves = ("n'est pas etabli", "pas un theoreme", "personne ne l'a mesure",
                "non mesure", "n'est pas verifie")
    for phrase in re.split(r"(?<=[.!?])\s+", t):
        if "nom nu" not in phrase.lower():
            continue
        assert any(r in phrase.lower() for r in reserves), (
            "phrase affirmative sur le nom nu, sans reserve : %r" % phrase[:180])
    b = releve()["mesures_graphe"]["programcall"]
    assert "non_etabli" in b, "le releve doit porter la meme reserve que la page"
    return "reserve presente, affirmation d'echec absente"


@cas("5. La CAUSE du contexte vide est ecrite, pas seulement le symptome")
def cas5():
    t = nu(plat(PAGE_TUN))
    assert "fait reussir le PingReceive" in t, (
        "la cause : le test de tunnel REUSSIT, c'est pour ca que le vide passe")
    assert "recopie du vide dans MZ" in t, "dire ou atterrit le vide"
    assert "Hql_Init" in t, "nommer la procedure d'entree ou la branche se joue"
    assert "branche Else EST la specification a reproduire" in t, (
        "designer la source de verite cote appelant")
    return "cause, destination du vide et source de verite nommees"


@cas("6. La liste des champs de la branche non-tunnel est complete et concorde")
def cas6():
    b = releve()["mesures_graphe"]["contexte_tunnel_xq"]
    t = nu(plat(PAGE_TUN))
    manquants = [c for c in b["champs_gtqc000"] if c not in t]
    assert not manquants, "champ(s) absent(s) de la page : %s" % manquants
    assert str(b["modules_de_domaine"]) in t, (
        "la page doit porter le nombre de modules mesures")
    absents = [m for m in b["modules"] if m not in t]
    assert not absents, "module(s) mesure(s) non cite(s) par la page : %s" % absents
    return "%d champs, %d modules cites" % (len(b["champs_gtqc000"]), len(b["modules"]))


@cas("7. Tunnel est donne pour un CODE, et l'effet reel de TRUE est dit")
def cas7():
    """Le point que le RETEX avait faux.

    Ecrire `Tunnel = TRUE` n'echoue pas : le champ est un `2,0`, donc TRUE y ecrit 1, qui
    est un code d'action valide. Dire « ca ne marche pas » serait plus rassurant et plus
    faux : la cible fait AUTRE CHOSE, ce qui se diagnostique bien plus mal.
    """
    t = nu(plat(PAGE_TUN))
    assert "Tunnel est declare 2,0" in t, "donner le TYPE, c'est lui qui tranche"
    assert "code d'action" in t, "dire ce que le champ porte"
    assert "Tunnel_Init(C_APPLIC_" in t, "montrer l'initialisation du standard"
    assert "il ecrit 1" in t, (
        "dire l'effet REEL de TRUE : il ecrit 1, il ne rate pas")
    assert "faire autre chose" in t, "dire la consequence pour la cible"
    b = releve()["mesures_graphe"]["contexte_tunnel_xq"]
    assert "2,0" in b["tunnel_type"], "le releve doit porter le type, source de la regle"
    return "type, code d'action, effet reel de TRUE"


@cas("8. La dependance au domaine est ecrite, avec ses ecarts mesures")
def cas8():
    """Une liste de champs presentee comme universelle serait une regle fausse.

    Les quatre ecarts ne sont pas de la decoration : ils sont la preuve qu'il faut ALLER
    LIRE le Hql_Init de la cible plutot que recopier celui de la page.
    """
    b = releve()["mesures_graphe"]["contexte_tunnel_xq"]["ecarts_par_domaine"]
    t = nu(plat(PAGE_TUN))
    for marqueur in ("DosCpt", "NomPrg8", "ZECHANGE_GTPCE"):
        assert marqueur in t, "ecart non cite par la page : %s" % marqueur
    for ecart, modules in b.items():
        for mod in modules:
            assert mod in t, "module %s cite par le releve (%s) absent de la page" % (mod, ecart)
    assert "depend du domaine" in t, "l'enoncer, pas seulement le montrer"
    assert "ouvrir le Hql_Init du domaine de la cible" in t, (
        "donner la METHODE, pas seulement la liste")
    return "%d ecarts, methode d'acces a la bonne liste" % len(b)


@cas("9. Les deux modes de lancement et le piege du ProgramExit sont ecrits")
def cas9():
    t = nu(plat(PAGE_TUN))
    assert "Ping('zechange', MZ)" in t, (
        "l'alternative supportee au remplissage complet du XQ")
    assert "ProgramExit" in t, "nommer l'instruction qui fait sortir la cible"
    assert "sort sans un message" in t, (
        "dire que l'echec est SILENCIEUX : c'est ce qui le rend couteux")
    assert "reprend la main comme si tout s'etait bien passe" in t, (
        "dire que l'appelant ne voit rien non plus")
    b = releve()["mesures_graphe"]["contexte_tunnel_xq"]
    assert b["modules_avec_programexit"] == b["modules_de_domaine"], (
        "le piege n'est general que si TOUS les modules mesures le portent")
    return "2 modes, sortie silencieuse documentee sur %d/%d modules" % (
        b["modules_avec_programexit"], b["modules_de_domaine"])


@cas("10. Le sens de la dependance gttmpce / gtpmpce est le bon")
def cas10():
    """Le cas qui tombe sur l'etat d'avant.

    La page enoncait « get_program_overview montre gttmpce dans les dependances de
    gtpmpce ». C'est l'inverse : gttmpce declare gtpmpce. Le bloc de code juste au-dessus
    etait correct, ce qui rendait la phrase indetectable a la relecture rapide.
    """
    b = releve()["mesures_graphe"]["portee_module_donnees"]
    t = nu(plat(PAGE_SUR))
    bon = "gtpmpce dans les dependances de gttmpce"
    mauvais = "gttmpce dans les dependances de gtpmpce"
    assert bon in t, "la page doit dire le bon sens de la dependance"
    assert mauvais not in t, "la page porte encore le sens inverse"
    assert "gtpmpce ne declare meme pas gttmpce" in t, (
        "le cas reel du RETEX : dans SON sens, la dependance n'existe pas du tout")
    assert "gttt545" in t and b["gttt545"], "citer le programme du standard qui fait les deux"
    return "sens correct, cas reel documente"


@cas("11. Module n'apporte pas les enregistrements -- regle, mesure et niveau de preuve")
def cas11():
    b = releve()["mesures_graphe"]["portee_module_donnees"]
    t = nu(plat(PAGE_SUR))
    assert "n'apporte aucun enregistrement" in t, "enoncer la regle"
    assert "Public Record 'GTFDD.dhsd' XZ G3XZ" in t, "montrer la forme correcte"
    for cle in ("declarations_record_xz", "programmes_declarant_xz"):
        assert milliers(b[cle]) in t, "chiffre %s absent de la page (%d)" % (cle, b[cle])
    assert "Zoom" in t and "RowInfo" in t, (
        "la corroboration par le manuel : la convention vaut pour d'autres enregistrements")
    assert "observe en production" in t, (
        "le non-franchissement de la frontiere de module n'est pas reproduit ici")
    assert "n'a pas de compilateur" in t, "dire POURQUOI ce n'est pas reproduit"
    assert "observe_non_reproduit" in b, "le releve doit porter la meme reserve"
    return "regle, %s declarations / %s programmes, preuve qualifiee" % (
        milliers(b["declarations_record_xz"]), milliers(b["programmes_declarant_xz"]))


@cas("12. compiling-diva-projects distingue les trois causes de l'Erreur 99")
def cas12():
    """La correction touche un AUTRE skill : c'est la que le partenaire rencontre le mur.

    Sans la distinction, un lecteur ajoute un `Module` pour resoudre un enregistrement --
    et ne comprend pas pourquoi ca ne change rien.
    """
    assert os.path.isfile(PAGE_ERR), "page absente : %s" % PAGE_ERR
    brut = lire(PAGE_ERR)
    t = nu(plat(PAGE_ERR))
    assert "Erreur 99 : Mot inconnu" in t, "la page doit traiter le message tel qu'il sort"
    assert "trois causes" in t.lower(), "annoncer qu'il y en a plusieurs"
    # Le mot « trois » ne suffit pas : une premiere version de ce cas etait satisfaite par
    # le seul titre de section, et survivait a la suppression de l'enumeration. On compte
    # donc les lignes du tableau, et on verifie qu'elles s'accordent avec le mot.
    rangs = [n for n in ("1", "2", "3", "4", "5")
             if ("| %s |" % n) in brut or ("| **%s** |" % n) in brut]
    assert rangs == ["1", "2", "3"], (
        "le tableau des causes porte les rangs %s, la page en annonce trois" % rangs)
    assert "implicite actif" in t, "cause 1 -- environnement"
    assert "Module\" dans votre source" in t or "dans votre source" in t, (
        "cause 2 -- declaration Module manquante")
    assert "Public Record" in t, "cause 3 -- enregistrement non declare"
    assert "n'apporte que des fonctions et des procedures" in t, (
        "dire ce que Module apporte, sinon on confond les causes 2 et 3")
    assert "pas transitif" in t, "rappeler la non-transitivite au point d'usage"
    assert "coding-diva-advanced" in t, "renvoyer vers la page qui detaille"
    cible = os.path.join(SKILL, "reference", "overwrite-pattern.md")
    assert os.path.isfile(cible), "le renvoi pointe une page inexistante"
    return "3 causes distinguees, renvoi resolu"


@cas("13. Aucune trace de poste ni d'identite dans les pages touchees")
def cas13():
    """Controle STRUCTUREL, volontairement pas une liste noire.

    Ces tests sont distribues avec le skill : ecrire ici les noms qu'on veut proteger
    reviendrait a les publier. On interdit donc les FORMES -- chemin absolu, chemin UNC,
    adresse mail -- qui sont les vecteurs par lesquels ces noms arrivent.

    Perimetre : les pages que CE lot ecrit. `compilation-errors.md` en est exclue -- elle
    porte deja, hors de ce lot, un chemin d'installation absolu du produit (prerequis
    xwin7). C'est un ecart reel a la convention « pas de chemin absolu » du workspace, mais
    il n'a rien a voir avec #176/#178 : il est renvoye au chantier de purge du plugin
    plutot que corrige au passage. L'elargir a cette page ici la ferait echouer sur un
    defaut que ce lot n'a ni introduit ni mandat de traiter.
    """
    motifs = [
        (r"[A-Za-z]:[\\/]", "chemin absolu Windows"),
        (r"\\\\[A-Za-z0-9]", "chemin UNC"),
        (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "adresse mail"),
    ]
    trouves = []
    for page in PAGES_DU_LOT:
        texte = lire(page)
        for motif, libelle in motifs:
            for m in re.finditer(motif, texte):
                trouves.append("%s : %s %r" % (os.path.basename(page), libelle, m.group(0)))
    assert not trouves, "\n         ".join(trouves)
    return "%d pages, %d formes interdites, 0 occurrence" % (len(PAGES_DU_LOT), len(motifs))


@cas("14. Tous les liens des pages touchees resolvent")
def cas14():
    casses = []
    for page in (PAGE_TUN, PAGE_SUR, PAGE_ERR):
        base = os.path.dirname(page)
        for cible in re.findall(r"\]\(([^)#]+\.md)\)", lire(page)):
            if not os.path.isfile(os.path.normpath(os.path.join(base, cible))):
                casses.append("%s -> %s" % (os.path.basename(page), cible))
    assert not casses, "lien(s) casse(s) : %s" % casses
    return "liens verifies sur 3 pages"


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
