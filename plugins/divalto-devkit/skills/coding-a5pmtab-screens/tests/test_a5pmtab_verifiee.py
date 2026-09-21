#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de coherence du skill A5PMTAB.

RETEX #280 #281 #284 #302 #304.

Meme principe que les suites de `coding-diva-advanced` : l'orchestrateur LLM interroge le
graphe et lit les sources livrees, il consigne dans `reference/keywords-verifies.json`, et
cette suite verifie **hors ligne** que les pages et le releve concordent. Les scripts du
devkit n'appellent jamais le MCP.

Ce que ce lot a appris, et que les cas gardent :

- **La regle du suffixe** (le suffixe change la SIGNATURE, pas seulement le nom) est le
  coeur du skill : elle explique le message d'erreur de #302 et rien ne la documente
  ailleurs. Cas 2 et 3.
- **Le fichier de prototypes livre par Divalto est FAUX sur `Id`** (il ecrit `Id` sans
  esperluette ; c'est `&Id`). Notre premiere redaction avait suivi le prototype -- corrigee
  sur reponse de l'architecte. Cas 4 : la page doit porter l'avertissement, pas la
  prescription inverse.
- **Trois points restent non resolus** et doivent le rester tant qu'ils ne sont pas
  tranches : cas 8. Une page qui prescrirait une valeur de retour d'`ArretSpecifique`
  serait pire qu'une page muette.

Lancer :
    py .claude/skills/coding-a5pmtab-screens/tests/run_all.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
REF = os.path.join(SKILL, "reference")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
CATALOGUE = os.path.join(REF, "callbacks-catalogue.md")
INVOCATION = os.path.join(REF, "invocation.md")
PIEGES = os.path.join(REF, "pieges-execution.md")
RELEVE = os.path.join(REF, "keywords-verifies.json")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


def nu(texte):
    """Depouille le balisage d'emphase. Ne PAS retirer `_` : les noms A5PMTAB en sont pleins."""
    return re.sub(r"[*`]", "", texte)


def plat(p):
    """Texte aplati, marqueur de citation retire apres indentation eventuelle."""
    return " ".join(re.sub(r"\n[ \t]*>", "\n", lire(p)).split())


def releve():
    return json.loads(lire(RELEVE))


def toutes_les_pages():
    return " ".join(nu(plat(p)) for p in (SKILL_MD, CATALOGUE, INVOCATION, PIEGES))


# --------------------------------------------------------------------------

@cas("1. Le releve porte ses sources, leur valeur inegale et sa date")
def cas1():
    r = releve()
    for cle in ("sources", "version_erp", "date_verification", "niveaux_de_confiance"):
        assert r.get(cle), "champ '%s' manquant" % cle
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["date_verification"]), r["date_verification"]
    s = r["sources"]
    assert "prototype" in s and "extraits" in s, s
    assert "AUTORITAIRE" in s["prototype"], (
        "le prototype doit etre designe comme source autoritaire pour ce qu'il vaut")
    return "%d sources, %d niveaux de preuve, %s" % (
        len(s), len(r["niveaux_de_confiance"]), r["date_verification"])


@cas("2. La regle du suffixe est enoncee par sa CAUSE (`Fperso`), chiffree, et dans le SKILL.md")
def cas2():
    """Le coeur du skill -- et la formulation a ete corrigee une fois.

    La premiere version disait « un tableau -> non suffixee, plusieurs -> suffixee ». Juste
    dans l'effet, FAUX dans la cause : c'est `Fperso` qui decide, tableau par tableau. Et
    elle omettait le point actionnable -- **le suffixe se declare dans `Nom=`**, il ne
    s'invente pas. Ce cas garde la cause, pas la formulation.
    """
    g = releve()["regle_du_suffixe"]
    assert g["non_suffixees_avec_id_par_adresse"] == 0, g
    assert g["suffixees"] == g["non_suffixees"], (
        "le prototype apparie les deux formes une a une : %s" % g)
    assert "Fperso" in g["mecanisme"], (
        "le mecanisme consigne doit nommer Fperso, pas le nombre de tableaux : %s" % g)
    assert g.get("correction_du_2026_08_28"), (
        "la correction doit rester tracee au releve -- sinon on peut y revenir sans le savoir")
    for page, nom in ((CATALOGUE, "catalogue"), (SKILL_MD, "SKILL.md")):
        t = nu(plat(page))
        assert "Fperso" in t, "%s : la cause doit etre nommee" % nom
        assert "Nom =" in t or "Nom=" in t, (
            "%s : le point actionnable -- le suffixe se declare dans Nom=" % nom)
        assert "ne s'invente pas" in t, (
            "%s : dire explicitement qu'ecrire un suffixe sans Nom= ne produit rien" % nom)
        assert "aucun Id" in t, "%s : la forme suffixee ne recoit pas Id" % nom
        assert "nombre de tableaux" in t, (
            "%s : ecarter explicitement la fausse cause -- c'est celle qu'on avait ecrite"
            % nom)
    t = nu(plat(CATALOGUE))
    for val in (str(g["declarations_brutes"]), str(g["noms_distincts"]),
                str(g["paires_appariees"]), str(g["paires_avec_un_parametre_d_ecart"])):
        assert val in t, "chiffre %s du releve absent du catalogue" % val
    return "%d declarations / %d noms, %d paires, %d a un parametre d'ecart" % (
        g["declarations_brutes"], g["noms_distincts"], g["paires_appariees"],
        g["paires_avec_un_parametre_d_ecart"])


@cas("3. Le message d'erreur reel est cite, et rattache a la regle du suffixe")
def cas3():
    """Sans le message, un lecteur ne fait pas le lien avec son propre symptome."""
    # Le message doit etre dans la page ou l'on DIAGNOSTIQUE, pas seulement quelque part
    # dans le skill : une premiere version cherchait sur toutes les pages, et le cas passait
    # encore apres l'avoir retire de pieges-execution.md.
    p = nu(plat(PIEGES))
    assert "0 parametre(s)" in p and "1 parametre(s)" in p, (
        "le message d'erreur runtime doit etre cite dans pieges-execution.md, tel qu'il "
        "apparait -- c'est la que va un lecteur qui a ce symptome")
    assert "sur la pile" in p, "citer le message en entier"
    assert "le suffixe ne s'invente pas" in p.lower(), (
        "la page doit affirmer le point actionnable : le suffixe se declare dans Nom=")
    assert "Fperso" in p, "le correctif doit nommer Fperso"
    return "message cite, rattache a Fperso et a Nom="


@cas("4. Le piege `Id` du prototype est un AVERTISSEMENT, pas une prescription")
def cas4():
    """Notre premiere redaction avait suivi le prototype et prescrit `Id` sans esperluette."""
    r = releve()
    p = r.get("piege_id_du_prototype")
    assert p, "le fait etabli doit etre consigne au releve"
    assert p["confiance"] == "architecte", p
    assert "PAR ADRESSE" in p["fait_etabli"], p["fait_etabli"]
    assert "id_par_valeur_ou_par_adresse" not in (r.get("non_verifie") or {}), (
        "la question est tranchee : elle ne doit plus figurer en non_verifie")
    for page, nom in ((CATALOGUE, "catalogue"), (PIEGES, "pieges"), (SKILL_MD, "SKILL.md")):
        t = nu(plat(page))
        assert "&Id" in t, "%s : la forme correcte doit etre montree" % nom
        assert "proto_a5pmtab.dhsp" in t, (
            "%s : nommer le fichier qui se trompe -- sinon l'avertissement est inutilisable"
            % nom)
    t = nu(plat(CATALOGUE))
    # Insensible a la casse : la page peut ecrire « liste » ou « LISTE », le sens compte.
    assert "liste" in t.lower() and "nombre de parametres" in t.lower(), (
        "dire pour quoi le prototype reste fiable : la liste et le nombre de parametres")
    return "fait etabli, fichier nomme, portee du prototype delimitee"


@cas("5. `1A` est explique comme un ALIGNEMENT, pas comme un pointeur")
def cas5():
    t = nu(plat(PIEGES))
    assert "alignement" in t.lower(), "dire ce que A signifie"
    assert "pas" in t and "pointeur" in t, (
        "refuter explicitement l'interpretation 'type adresse/pointeur' du RETEX")
    assert "sous-donnee" in t, (
        "le point qui rend le piege comprehensible : A vise les sous-donnees, et le niveau 1 "
        "est deja aligne automatiquement")
    assert "1A Retour X" in nu(plat(PIEGES)), (
        "montrer le cas LEGITIME du prototype -- c'est lui qui rend l'erreur credible")
    return "alignement, refutation, cas legitime"


@cas("6. L'invocation porte les deux modules et la nature HMP des options")
def cas6():
    t = nu(plat(INVOCATION))
    assert "A5PMTAB.dhop" in t and "A5PMTAB000" in t, (
        "les DEUX modules doivent etre declares -- Module n'est pas transitif")
    assert "pas transitive" in t, "rappeler pourquoi les deux sont necessaires"
    assert "Creer_Parametre(" in t and "AP_Interroger_Tableaux(" in t, "les deux appels"
    assert "HmpEncode(" in t, "les options sont une chaine HMP"
    assert "ignoree" in t, (
        "consequence de la chaine balisee : une option mal orthographiee ne provoque AUCUNE "
        "erreur")
    return "modules, appels, HMP, option silencieusement ignoree"


@cas("7. Le motif `XmeNext` est refute par la mesure, pas par l'opinion")
def cas7():
    m = releve()["mesures_graphe"]
    assert m["routines_a5pmtab_utilisant_xmenext"] == 0, m
    t = nu(plat(PIEGES))
    assert str(m["routines_appelant_ap_tableaux"]) in t, (
        "citer le denominateur : 0 sur combien ?")
    assert "XmeNext" in t, "nommer le motif incrimine"
    assert "production" in t, (
        "dire que le motif vient de code EN PRODUCTION -- c'est ce qui le rend credible")
    return "0/%d mesure et cite" % m["routines_appelant_ap_tableaux"]


@cas("8. La semantique du retour est PRESCRITE, et les vraies limites restent declarees")
def cas8():
    """Ce cas a d'abord protege une ERREUR -- il exigeait que la semantique reste « non
    resolue ». Or elle etait ecrite dans la section Suggestion du RETEX : `0` = « je gere,
    ne fais rien », `1` = « laisse faire ». Le partenaire demandait meme d'en faire un point
    de tete de chapitre. Le cas garde desormais les DEUX sens : la resolution ne doit pas se
    perdre, et les limites restantes ne doivent pas se dissoudre.
    """
    r = releve()
    nv = r.get("non_verifie") or {}

    # 1. Ce qui a ete RESOLU ne doit plus figurer comme incertain
    resolus_a_tort = [k for k in ("retour_de_arretspecifique", "aller_retour_saisie_tableau")
                      if k in nv]
    assert not resolus_a_tort, (
        "point(s) TRANCHE(S) par les RETEX toujours declare(s) non verifie(s) : %s -- c'est "
        "l'erreur que cet audit a corrigee" % resolus_a_tort)

    # 2. La semantique doit etre consignee comme fait etabli, avec son historique
    s = r.get("semantique_du_retour")
    assert s, "la semantique 0/1 doit etre un fait etabli du releve"
    assert "1 est le REPLI" in s["fait_etabli"] or "1 est le repli" in s["fait_etabli"], s
    assert s.get("historique"), (
        "l'historique de la correction doit rester -- sinon on peut retomber dans l'erreur")
    assert r.get("aller_retour_saisie_tableau", {}).get("correctif"), (
        "le correctif de l'aller-retour doit etre consigne")

    # 3. Le SKILL.md doit porter le point en TETE, comme le partenaire le demande
    t = nu(plat(SKILL_MD))
    assert "le plus couteux a ignorer" in t, (
        "le partenaire demande explicitement un point de tete de chapitre mis en evidence")
    assert "laisse faire" in t and "je gere" in t, "la semantique doit etre dans le SKILL.md"
    assert "Aucune valeur n'est prescrite" not in t, (
        "cette phrase etait la trace de l'erreur : la valeur EST prescrite (1 en repli)")

    # 4. Les limites qui SUBSISTENT, et le differe, doivent rester visibles
    for k in ("mecanisme_de_la_corruption_1A", "resolution_des_callbacks_par_le_moteur"):
        assert k in nv, "limite reelle disparue du releve : %s" % k
    d = r.get("differe_declare") or {}
    assert len(d) >= 5, (
        "les demandes des RETEX non couvertes doivent etre listees -- sinon on croit le "
        "skill complet : %s" % list(d))
    for attendu in ("critere_interro_vs_saisie", "lint_1a"):
        assert attendu in d, "demande de RETEX non tracee : %s" % attendu
    assert "ne couvre pas ENCORE" in t, (
        "le differe doit etre visible depuis le SKILL.md, pas seulement dans le releve")
    return "semantique prescrite, %d limites reelles, %d demandes differees tracees" % (
        len(nv), len(d) - 1)


@cas("9. Les irregularites du fichier livre sont documentees")
def cas9():
    r = releve()
    irr = r.get("irregularites_du_fichier_livre") or []
    assert len(irr) >= 3, "au moins les trois irregularites relevees : %s" % irr
    t = nu(plat(CATALOGUE))
    assert "DefProcTriAvant" in t, (
        "les noms non suffixes qui perdent le tiret bas : le nom se LIT, il ne se deduit pas")
    assert "Click_Autre_Tableau" in t, "l'incoherence de signature du fichier livre"
    assert "(XMT)" in t, "les doubles declarations Function / (XMT) Procedure"
    return "%d irregularites consignees et documentees" % len(irr)


@cas("10. La mesure d'usage justifie l'existence du skill")
def cas10():
    """#280 dit 'aucune reference' -- le chiffre dit a quel point ca manquait."""
    m = releve()["mesures_graphe"]
    t = nu(plat(SKILL_MD))
    for val in ("7 663", "661"):
        assert val in t, "mesure %s absente du SKILL.md" % val
    assert m["callbacks_dans_le_standard"] == 7663, m
    assert m["programmes_utilisant_des_callbacks"] == 661, m
    return "%d callbacks dans %d programmes" % (
        m["callbacks_dans_le_standard"], m["programmes_utilisant_des_callbacks"])


@cas("11. Le catalogue du prototype est complet dans le releve")
def cas11():
    cb = releve()["callbacks_prototype"]
    assert len(cb) >= 150, "le prototype porte 180 declarations : %d relevees" % len(cb)
    suff = [n for n, v in cb.items() if v["suffixee"]]
    non = [n for n, v in cb.items() if not v["suffixee"]]
    assert len(suff) == len(non), (
        "appariement rompu : %d suffixees / %d non suffixees" % (len(suff), len(non)))
    # aucune non suffixee ne doit porter &Id dans le prototype -- c'est le fait du piege
    with_amp = [n for n, v in cb.items()
                if not v["suffixee"] and v["params"] and v["params"][0].startswith("&")]
    assert not with_amp, (
        "le prototype n'ecrit JAMAIS &Id -- si cela change, l'avertissement du cas 4 doit "
        "etre relu : %s" % with_amp[:3])
    return "%d declarations, %d/%d appariees" % (len(cb), len(suff), len(non))


@cas("12. Tous les liens des pages resolvent")
def cas12():
    casses = []
    for f in (SKILL_MD, CATALOGUE, INVOCATION, PIEGES):
        base = os.path.dirname(f)
        for c in re.findall(r"\]\(([^)#]+\.(?:md|json))\)", lire(f)):
            if not os.path.isfile(os.path.normpath(os.path.join(base, c))):
                casses.append((os.path.basename(f), c))
    assert not casses, "lien(s) casse(s) : %s" % casses
    return "liens verifies sur 4 pages"


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
