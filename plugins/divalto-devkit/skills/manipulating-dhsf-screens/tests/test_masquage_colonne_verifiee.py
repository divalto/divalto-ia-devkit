#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests du masquage conditionnel de colonne.

RETEX #180.

Le RETEX donne une recette complete en cinq etapes. La mesure sur les **8 022 sources
livrees** du pack en confirme quatre, en **corrige une** et en laisse une **non etablie** --
et ces trois statuts doivent rester distincts dans la page. C'est ce que ces cas gardent.

- **Les deux contextes sont mesures**, pas devines : `ZoomEnteteTableau` vit dans 718
  programmes, tous de la famille zoom ; `XmeListGetId` dans 119, dont 89 % sans aucun
  `Zoom.Idtableau`. Le cas 2 confronte ces chiffres au releve.
- **La signature du RETEX est fausse** : il ecrit `XmeListGetId("NomDuTableau")`, un argument.
  Le standard en passe quatre, le nom en troisieme. Le cas 4 garde la correction -- suivre le
  RETEX a la lettre donne une erreur de nombre de parametres.
- **Le champ existe, les valeurs non.** `COLUMNINFO.Affichage` est verifie dans le
  dictionnaire systeme ; les constantes `AFFCOL_*` n'apparaissent nulle part. Le cas 7 garde
  les deux sens : la reserve doit rester ecrite, et la distinction champ/valeurs ne doit pas
  s'effacer -- sans quoi on retomberait soit sur « rien n'est verifie », soit sur « tout l'est ».

Lancer :
    py .claude/skills/manipulating-dhsf-screens/tests/run_all.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
REF = os.path.join(SKILL, "reference")
RELEVE = os.path.join(REF, "mesures-corpus.json")
PAGE = os.path.join(REF, "xmesetattribut-dynamique.md")
SKILL_MD = os.path.join(SKILL, "SKILL.md")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


def nu(texte):
    return re.sub(r"[*`]", "", texte)


def plat(p):
    return " ".join(re.sub(r"\n[ \t]*>", "\n", lire(p)).split())


def bloc():
    return json.loads(lire(RELEVE))["masquage_colonne"]


def milliers(n):
    return "{:,}".format(n).replace(",", " ")


# --------------------------------------------------------------------------

@cas("1. Le releve porte le bloc, date, et dit sur quoi la mesure a porte")
def cas1():
    b = bloc()
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", b.get("date", "")), "bloc sans date"
    assert b.get("_page") == "xmesetattribut-dynamique.md", "le bloc doit dire quelle page il fonde"
    note = b.get("_note", "")
    assert "8022" in note.replace(" ", ""), "dire le volume mesure"
    assert "ddsys" in note, (
        "la lecture du dictionnaire systeme est une source distincte du corpus : le dire")
    assert b.get("niveau") == "mesure", "niveau de preuve manquant"
    return "bloc date au %s" % b["date"]


@cas("2. Les deux contextes sont ecrits, avec leurs chiffres concordants")
def cas2():
    t = nu(plat(PAGE))
    c = bloc()["deux_contextes"]
    pct = round(100.0 * c["xmelistgetid_sans_zoom_idtableau"] / c["xmelistgetid_programmes"])
    # Chaque chiffre est ancre a SA LIGNE du tableau. Le chercher seul ne prouve rien : 119
    # apparait deux fois dans la page (« 119 » et « 106 sur 119 »), et le harnais de mutation
    # a montre qu'en changer un laissait le cas passer. Meme faiblesse que les cas 4 et 9 des
    # autres suites -- ancrer sur la phrase, jamais sur le nombre.
    for phrase, quoi in (
            ("appelant ZoomEnteteTableau | %d" % c["zoomentetetableau_programmes"],
             "programmes Zoom"),
            ("appelant XmeListGetId | %d" % c["xmelistgetid_programmes"], "programmes hors Zoom"),
            ("dont %d sans aucun" % c["xmelistgetid_hors_famille_zoom"], "hors famille zoom"),
            ("%d sur %d, soit %d %%" % (c["xmelistgetid_sans_zoom_idtableau"],
                                        c["xmelistgetid_programmes"], pct),
             "part disjointe"),
            ("se croisent | %d" % c["intersection"], "intersection")):
        assert phrase in t, (
            "%s : la page ne porte pas %r -- un chiffre non rattache a son affirmation ne "
            "prouve rien" % (quoi, phrase))
    assert "Zoom SQL" in t and "hors Zoom SQL" in t, "nommer les deux contextes"
    assert "Zoom.Idtableau" in t and "XmeListGetId" in t, (
        "donner l'identifiant a employer dans chaque contexte")
    assert "surcharge du masque" in t, "dire OU brancher le traitement hors Zoom"
    return "%d vs %d programmes, %d %% disjoints" % (
        c["zoomentetetableau_programmes"], c["xmelistgetid_programmes"], pct)


@cas("3. ZoomEnteteTableau hors Zoom : jamais appelee, et SANS erreur")
def cas3():
    """C'est le silence qui coute.

    Implementer la procedure dans un programme protege ne produit ni effet ni message : on
    cherche ailleurs pendant des heures. Une page qui dirait seulement « ca ne marche pas »
    n'aiderait pas.
    """
    t = nu(plat(PAGE))
    assert "n'est appelee que par le moteur Zoom SQL" in t, "enoncer la regle"
    assert "jamais" in t, "et sa consequence dans un programme protege"
    assert "aucune erreur" in t, (
        "dire que rien ne le signale -- c'est ce qui rend le piege couteux")
    return "regle et silence documentes"


@cas("4. La signature de XmeListGetId est CORRIGEE, avec l'erreur qu'elle evite")
def cas4():
    """Le RETEX ecrit un appel a UN argument, le nom en premiere position. Faux sur les deux
    points : 131 des 132 appels du standard en passent quatre, et le nom est le troisieme.
    """
    t = nu(plat(PAGE))
    x = bloc()["xmelistgetid"]
    assert "QUATRE arguments" in t, "dire le nombre en toutes lettres"
    assert str(x["appels"]) in t and str(x["a_quatre_arguments"]) in t, (
        "les chiffres qui fondent la correction doivent figurer")
    assert "3e argument, pas le 1er" in t or "3e argument" in t, (
        "dire OU se trouve le nom du tableau")
    assert "erreur de nombre de parametres" in t, (
        "dire ce qui arrive si on suit la forme fautive")
    assert x.get("correction_du_retex"), "le releve doit garder la correction"
    return "%d appels, %d a quatre arguments" % (x["appels"], x["a_quatre_arguments"])


@cas("5. Le numero de colonne : ordinal, jamais un nom, et la consigne qui le protege")
def cas5():
    t = nu(plat(PAGE))
    n = bloc()["numero_de_colonne"]
    assert n["second_argument_nom"] == 0, "le releve doit porter le zero"
    assert str(n["appels_get_et_set"]) in t, "le nombre d'appels mesures doit figurer"
    assert "toujours un numero" in t and "jamais un nom" in t, "enoncer la regle"
    assert "aucune fonction de correspondance" in t, (
        "dire qu'il n'existe pas de lookup -- sinon on le cherche")
    assert "change silencieusement" in t, (
        "l'ordinal bouge si l'ordre des colonnes change : c'est le vrai risque")
    assert "commentaire a cote de l'appel" in t, (
        "donner la parade, sinon l'avertissement est sterile")
    return "%d appels, 0 par nom" % n["appels_get_et_set"]


@cas("6. COLUMNINFO : le champ Affichage existe, et Visibilite en est distinct")
def cas6():
    t = nu(plat(PAGE))
    c = bloc()["columninfo"]
    assert "ddsys.dhsd" in t, "nommer la source du dictionnaire"
    assert str(c["nb_champs"]) in t, "le nombre de champs doit figurer"
    assert "Affichage" in t and "Visibilite" in t, "nommer les deux champs"
    # Ancre sur LA LIGNE du tableau, pas sur « ne pas confondre » -- cette formule apparait
    # aussi dans le titre de section et dans le sommaire, sans rapport avec ces deux champs.
    # Le harnais l'a montre : confondre les deux champs laissait le cas passer.
    assert "Visibilite | un autre champ, distinct" in t, (
        "les deux champs existent : la ligne doit dire explicitement qu'ils sont distincts")
    assert "EXISTE" in c["champ_affichage"], (
        "le releve doit porter que le champ est VERIFIE, pas suppose")
    for champ in ("Libelle", "Nomdonnee", "Bulle"):
        assert champ in t, "champ reellement employe non cite : %s" % champ
    return "%d champs, Affichage verifie, Visibilite distinct" % c["nb_champs"]


@cas("7. Les VALEURS AFFCOL sont declarees non verifiees -- et le champ reste verifie")
def cas7():
    """Garde les deux sens, et la distinction entre les deux.

    Sens 1 -- la reserve sur les valeurs doit rester ecrite, avec son chiffre.
    Sens 2 -- elle ne doit pas contaminer le CHAMP, qui est verifie. Effacer la distinction
    ferait retomber la page soit sur « rien n'est etabli », soit sur « tout l'est ».
    """
    t = nu(plat(PAGE))
    b = bloc()
    assert "AFFCOL_NON" in t and "AFFCOL_JAMAIS" in t, "nommer les valeurs en question"
    assert "n'apparaissent nulle part" in t, "dire le resultat de la recherche"
    assert "8 022" in t, "avec le volume qui le fonde"
    assert "repertoire systeme" in t, "et dire que la recherche a couvert les deux endroits"
    assert "module compile" in t, "donner l'hypothese la plus probable"
    assert "Le champ Affichage, lui, existe" in t, (
        "la reserve porte sur les VALEURS, pas sur le champ : la distinction doit tenir")
    assert b.get("non_verifie"), "le releve doit porter la meme reserve"
    assert "CHAMP Affichage, lui, est verifie" in b["non_verifie"], (
        "et la meme distinction")

    # Aucune phrase ne doit PRESCRIRE les valeurs sans les reserver.
    reserves = ("n'apparaissent nulle part", "n'est pas etabli", "non etabli", "nomme",
                "vraisemblablement", "interroger le graphe", "retour terrain")
    for phrase in re.split(r"(?<=[.!?])\s+", t):
        if "AFFCOL" not in phrase:
            continue
        assert any(m in phrase.lower() for m in reserves), (
            "phrase prescrivant AFFCOL sans reserve : %r" % phrase[:170])
    return "valeurs reservees, champ verifie, distinction gardee"


@cas("8. La demarche en cinq etapes est la, et dit lesquelles sont mesurees")
def cas8():
    t = nu(plat(PAGE))
    for etape in ("surcharge du masque", "avant affichage", "XmeListGetId",
                  "XmeListGetColumn", "XmeListSetColumn"):
        assert etape in t, "etape absente de la demarche : %s" % etape
    assert "1 a 4 sont mesurees" in t, (
        "distinguer ce qui est mesure de ce qui vient d'un retour terrain")
    assert "vient d'un retour terrain" in t, "et le dire de l'etape 5"
    return "5 etapes, provenance distinguee"


@cas("9. Aucune trace de poste, page atteignable, liens resolus")
def cas9():
    motifs = [
        (r"[A-Za-z]:[\\/]", "chemin absolu Windows"),
        (r"\\\\[A-Za-z0-9]", "chemin UNC"),
        (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "adresse mail"),
    ]
    trouves = []
    texte = lire(PAGE)
    for motif, libelle in motifs:
        for m in re.finditer(motif, texte):
            trouves.append("%s : %s %r" % (os.path.basename(PAGE), libelle, m.group(0)))
    assert not trouves, "\n         ".join(trouves)
    assert "xmesetattribut-dynamique.md" in lire(SKILL_MD), (
        "une page que le SKILL.md ne cite pas n'existe pas pour le lecteur")
    base = os.path.dirname(PAGE)
    casses = [c for c in re.findall(r"\]\(([^)#]+\.(?:md|json))\)", texte)
              if not os.path.isfile(os.path.normpath(os.path.join(base, c)))]
    assert not casses, "lien(s) casse(s) : %s" % casses
    return "3 formes interdites, page citee, liens resolus"


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
