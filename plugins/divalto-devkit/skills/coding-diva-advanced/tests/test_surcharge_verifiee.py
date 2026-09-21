#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de coherence de la page de surcharge.

RETEX #36 #226 #272 #294 #297 #300 #320.

Meme principe que `test_syntaxe_verifiee.py` : l'orchestrateur LLM interroge le graphe et
consigne, la suite verifie **hors ligne** que la page et le releve concordent. Les scripts
du plugin n'appellent jamais le MCP.

Ce que ce lot a appris et que les cas gardent :

- Deux lignes du tableau de visibilite etaient **fausses** -- `Private` donne « non
  verifie » alors qu'il est documente, et `Protected` donne « inexistant en pratique »
  alors qu'on le cherchait la ou il ne peut pas apparaitre (ce n'est pas un modificateur
  de fonction). Les cas 2 et 3 empechent ces deux affirmations de revenir.
- La page cite des **mesures** (PP/TT, params vides). Une page qui derive des chiffres qui
  la fondent est pire qu'une page sans chiffres : le cas 6 les confronte au releve.
- La correction touche un **autre skill** (`manipulating-dhsf-screens`). Le cas 9 verifie
  que la nuance y est, et qu'elle renvoie ici.

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
PAGE = os.path.join(SKILL, "reference", "overwrite-pattern.md")
RELEVE = os.path.join(SKILL, "reference", "keywords-verifies.json")
PAGE_DHSF = os.path.join(SKILLS, "manipulating-dhsf-screens", "reference",
                         "dhsf-overwrite-pattern.md")
PAGE_MCP = os.path.join(SKILLS, "querying-diva-graph", "reference", "mcp-query-pitfalls.md")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def releve():
    return json.loads(lire(RELEVE))


# --------------------------------------------------------------------------

@cas("1. Le releve couvre les mots-cles de visibilite cites par la page")
def cas1():
    e = releve()["existe"]
    attendus = ("public", "private", "protected", "extern", "overwrite", "overwrittenby",
                "module")
    manquants = [m for m in attendus if m not in e]
    assert not manquants, "absent(s) du releve : %s" % manquants
    directs = [m for m in attendus if e[m]["confiance"] == "direct"]
    return "%d mots-cles, dont %d verifies en direct" % (len(attendus), len(directs))


def ligne_tableau(chemin, mot):
    """La ligne de tableau dont la PREMIERE cellule porte ce mot-cle.

    On teste la ligne, pas la page entiere : la page contient forcement l'ancienne
    formulation, puisqu'elle la cite dans sa note de correction (« Private y etait donne
    non verifie »). Une assertion sur l'absence d'une chaine dans TOUTE la page
    interdirait donc de documenter la correction -- c'est le piege dans lequel ces deux
    cas sont tombes a leur premiere ecriture.
    """
    for ligne in lire(chemin).split("\n"):
        if not ligne.lstrip().startswith("|"):
            continue
        cellules = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if cellules and cellules[0].strip("`* ").lower() == mot.lower():
            return " ".join(cellules)
    raise AssertionError("aucune ligne de tableau pour `%s` dans %s"
                         % (mot, os.path.basename(chemin)))


@cas("2. `Private` est presente comme un mecanisme documente, pas comme une inconnue")
def cas2():
    """L'ancienne ligne disait « non verifie. Ne pas s'y fier : utiliser la forme canonique »."""
    ligne = ligne_tableau(PAGE, "Private")
    assert "non verifie" not in ligne.lower(), (
        "la ligne Private ne doit plus la donner pour non verifiee : %s" % ligne)
    assert "n'est PAS une surcharge" in nu(ligne), (
        "la ligne doit dire ce que Private SIGNIFIE : cette fonction n'est pas une surcharge")
    t = nu(plat(PAGE))
    assert "ni Public ni Private est une fonction de surcharge" in t, (
        "la regle qui structure la section doit etre ecrite : sans modificateur = surcharge")
    note = releve()["existe"]["private"]["note"]
    assert "module de SURCHARGE" in note, note
    return "ligne corrigee, corollaire et provenance ecrits"


@cas("3. `Protected` n'est PAS presente comme un modificateur de fonction")
def cas3():
    """Ancienne erreur de categorie : compte a 0 la ou il ne peut pas apparaitre."""
    ligne = ligne_tableau(PAGE, "Protected")
    assert "inexistant" not in ligne.lower(), (
        "Protected n'etait pas absent, il etait cherche au mauvais endroit : %s" % ligne)
    assert "DONNEES" in ligne, "la ligne doit dire ce que Protected EST"
    t = plat(PAGE)
    for decl in ("HFile", "HTmpFile", "Record", "RecordDiva"):
        assert decl in t, "%s absent : les declarations que Protected peut preceder" % decl
    note = releve()["existe"]["protected"]["note"]
    assert "JAMAIS" in note, note
    return "categorie corrigee, les 4 declarations citees"


@cas("4. Le partage de DONNEES entre modules est documente (`Extern`), pas nie")
def cas4():
    """La page prescrivait « tout en parametres » -- trop absolu, Extern existe."""
    t = nu(plat(PAGE))
    assert "Extern" in t, "le mecanisme Extern doit etre documente"
    assert "aucune memoire" in t or "rien" in t, (
        "le point cle d'Extern : Diva n'alloue rien, la donnee pointe sur l'appelant")
    assert "module appelant" in t, "Extern pointe sur l'instance du module APPELANT"
    return "Public / Protected / Extern presentes ensemble"


@cas("5. La non-transitivite de `Module` est dite, avec son corollaire non greppable")
def cas5():
    t = plat(PAGE)
    assert "pas transitive" in t, "#300 : la declaration Module n'est pas transitive"
    assert "Erreur 99" in t, "le symptome mesure par le RETEX"
    assert "greppable" in t, (
        "#226 : le module manquant peut etre un .dhop dont la source n'est pas livree -- "
        "la recherche textuelle ne le trouvera pas")
    return "regle, symptome et cas non greppable"


@cas("6. Les mesures citees par la page concordent avec le releve")
def cas6():
    """Une page qui derive des chiffres qui la fondent est pire qu'une page sans chiffres."""
    m = releve()["mesures_graphe"]
    t = plat(PAGE)
    pp = m["pp_tt"]
    chiffres = [
        ("programmes PP", "%d" % pp["programmes_pp"]),
        ("programmes TT", "%d" % pp["programmes_tt"]),
        ("appariement PP/TT", "%d" % pp["pp_avec_tt_de_meme_numero"]),
        ("routines PP protegees", "11 169"),
        ("routines TT", "6 447"),
        ("TT portant des hooks", "%d" % pp["tt_portant_des_hooks"]),
        ("hooks Av/Ap", "3305"),
        ("hooks quasi vides", "2195"),
    ]
    absents = [nom for nom, val in chiffres if val not in t]
    assert not absents, "chiffre(s) du releve absent(s) de la page : %s" % absents
    assert "%d" % m["signature_protegee"]["routines_totales"] in t or "195 665" in t, (
        "le total sur lequel params a ete mesure doit etre cite")
    return "%d mesures confrontees, plus le total des routines" % len(chiffres)


@cas("7. La nuance PP/TT est dite comme quasi-systematique, PAS comme absolue")
def cas7():
    """18 exceptions sur 410 : une regle presentee comme absolue serait fausse."""
    m = releve()["mesures_graphe"]["pp_tt"]
    assert m["programmes_pp"] - m["pp_avec_tt_de_meme_numero"] == m["pp_sans_tt"], m
    t = plat(PAGE)
    assert "pas** absolu" in t or "pas absolu" in t, (
        "la page doit dire que l'appariement n'est PAS absolu")
    assert "18 exceptions" in t, "le nombre d'exceptions doit etre donne"
    assert "Erreur 106" in t, "l'erreur reellement obtenue par le partenaire"
    return "%d/%d apparies, %d exceptions dites" % (
        m["pp_avec_tt_de_meme_numero"], m["programmes_pp"], m["pp_sans_tt"])


@cas("8. La signature d'une routine protegee : ce qui NE marche pas est dit avec sa mesure")
def cas8():
    """#297 proposait `n.args`. La propriete n'existe pas, et params est vide partout."""
    m = releve()["mesures_graphe"]["signature_protegee"]
    assert m["params_renseignes"] == 0, m
    assert m["params_vides"] == m["routines_totales"], m
    t = plat(PAGE)
    assert "Programme protégé, non livré." in t or "Programme prot" in t, (
        "dire ce que le graphe rend a la place du corps")
    assert "`params`" in t, "nommer la propriete reellement presente"
    assert "appelant" in t, "donner la voie qui marche : remonter a un appelant livre"
    assert "mcp-query-pitfalls.md" in t, "renvoyer au skill qui porte la requete"
    return "inexistence mesuree (0/%d) + contournement + renvoi" % m["routines_totales"]


@cas("9. La correction est propagee a `manipulating-dhsf-screens`, et elle renvoie ici")
def cas9():
    """Une correction qui laisse un autre skill enseigner l'ancienne regle est incomplete."""
    t = plat(PAGE_DHSF)
    assert "Private" in t, "la nuance masque -> Private doit y etre"
    assert "l'inverse" in t or "INVERSE" in t.upper(), (
        "l'asymetrie dictionnaire/masque est le point : les deux regles sont opposees")
    assert "overwrite-pattern.md" in t, "le renvoi vers la page de reference doit tenir"
    return "nuance presente et renvoi intact"


@cas("10. Le piege de signature est aussi documente cote `querying-diva-graph`")
def cas10():
    t = plat(PAGE_MCP)
    assert "195 665" in t, "la mesure doit etre citee la ou la requete se fait"
    assert "has_body" in t, (
        "l'avertissement sur has_body est essentiel : il vaut true meme sur un corps protege")
    assert "[:CALLS]" in t, "la requete de contournement doit y etre"
    assert "overwrite-pattern.md" in t, "renvoi croise vers la page de surcharge"
    return "mesure, piege has_body, requete et renvoi"


@cas("11. Les surcharges multiples d'add-on (`AS alias`) sont documentees")
def cas11():
    t = plat(PAGE)
    assert "as addon" in t.lower(), "la forme Module ... AS alias doit etre montree"
    assert "add-on" in t.lower(), "dire a quoi ca sert"
    assert releve()["existe"]["overwrittenby"], "OverWrittenBy doit etre au releve"
    return "forme, usage et releve"


@cas("12. La surchargeabilite est presentee comme declaree par la base (opt-in)")
def cas12():
    t = plat(PAGE)
    assert "opt-in" in t.lower(), (
        "c'est le principe qui explique l'erreur 106 : rien n'est surchargeable par defaut")
    assert "recompiler les dictionnaires de surcharge" in t, (
        "avertissement de montee de version, issu de la doc")
    return "opt-in + avertissement de montee de version"


@cas("13. Les erreurs compilateur du lot sont toutes nommees COMME telles")
def cas13():
    """Chercher le numero nu ne vaut rien : trois chiffres se trouvent n'importe ou.

    Ce cas a d'abord teste `"106" in texte` -- et il ne discriminait pas, la page citant
    par ailleurs assez de nombres. On exige donc le numero **precede de son label**, ce
    qui est la seule forme utile a un lecteur qui vient d'obtenir le message.
    """
    texte = lire(PAGE)
    # Deux formes legitimes, et il fallait les distinguer : en PROSE (« Erreur 210 ») et en
    # COLONNE d'un tableau dont l'en-tete est « Erreur » (216, 82, 98, 142). Exiger la
    # forme prose pour toutes accusait la page a tort.
    trouves = {int(n) for n in re.findall(
        r"[Ee]rreur(?:\s+compilateur)?(?:\s+xwin7)?\s+#?(\d{2,3})", nu(plat(PAGE)))}
    col_erreur = None
    for ligne in texte.split("\n"):
        if not ligne.lstrip().startswith("|"):
            col_erreur = None if not ligne.strip() else col_erreur
            continue
        cellules = [c.strip() for c in ligne.strip().strip("|").split("|")]
        entetes = [c.strip("* ").lower() for c in cellules]
        if "erreur" in entetes:
            col_erreur = entetes.index("erreur")
            continue
        if col_erreur is not None and col_erreur < len(cellules):
            for n in re.findall(r"\b(\d{2,3})\b", cellules[col_erreur]):
                trouves.add(int(n))
    attendus = {210, 106, 216, 142, 99, 82, 98}
    manquantes = sorted(attendus - trouves)
    assert not manquantes, (
        "erreur(s) ni nommee(s) en prose ni portee(s) par une colonne « Erreur » : %s "
        "-- trouvees : %s" % (manquantes, sorted(trouves)))
    return "%d erreurs du lot presentes (prose + colonnes)" % len(attendus)


@cas("15. L'asymetrie nomme ses deux supports, et desamorce la confusion `.dhsd`")
def cas15():
    """« Traitement de dictionnaire » est un piege de lecture.

    Un partenaire lit ces mots et pense a son travail quotidien sur un `.dhsd` -- declarer
    une table, un champ, un index. Ce n'est pas ca : la regle ne vise que les rares `.dhsd`
    portant un bloc `[diva]`. Sans l'avertissement, la page envoie le lecteur appliquer une
    regle de visibilite a des zones de declaration.
    """
    t = nu(plat(PAGE))
    assert "absente du code de base" in t or "absente de la base" in t, (
        "la condition est load-bearing : la regle ne vaut QUE pour une fonction absente "
        "de la base -- sans elle, on lit une interdiction generale de Public")
    assert "[diva] d'un .dhsf" in t, "nommer precisement le support masque"
    assert "[diva] dans un .dhsd" in t, "nommer precisement le support dictionnaire"
    assert "en voie d'abandon" in t, (
        "le cas dictionnaire est rare et en voie d'abandon : le taire donnerait aux deux "
        "moities un poids egal qu'elles n'ont pas")
    assert "managing-diva-dictionaries" in t and "rien a voir" in t, (
        "il faut ecarter explicitement le travail habituel sur un .dhsd")
    return "deux supports nommes, rarete dite, confusion ecartee"


@cas("16. Le piege de montee de version porte sa SORTIE, pas seulement le mur")
def cas16():
    """Documenter un mur sans sa sortie laisse le lecteur bloque."""
    t = nu(plat(PAGE))
    assert "Standard.ApresRead()" in t, (
        "la resolution documentee : retirer Private et chainer sur le standard")
    assert "plus de Private" in t, "montrer que le modificateur DISPARAIT"
    assert "pattern canonique" in t, (
        "boucler sur le pattern canonique de la page : la surcharge redevient ordinaire")
    return "resolution montree et rattachee au pattern canonique"


@cas("17. Les deux blocs d'un masque surcharge ont des `Module` independants (#225)")
def cas17():
    """La regle generale etait la ; SON CAS ne l'etait pas.

    `#225` decrit exactement la non-transitivite -- mais entre `[diva]` et `[diva_base]`
    d'un masque surcharge, pas entre deux fichiers. La page portait la regle et **ne
    nommait jamais les deux blocs** : le lecteur devait faire le saut lui-meme. Le cas
    verifie donc que le cas concret est ECRIT, pas seulement deductible.
    """
    t = nu(plat(PAGE))
    # Ancrage sur la PHRASE, pas sur `[diva]` (13 occurrences) ni `Erreur 99` (8).
    assert "Leurs declarations Module sont independantes" in t, (
        "#225 : la page doit DIRE que les declarations Module des deux blocs sont "
        "independantes -- la regle generale ne suffit pas, c'est son cas qui manquait")
    assert "declare seulement dans [diva_base]" in t, (
        "le declencheur precis du RETEX : appeler depuis [diva] un module declare "
        "uniquement dans [diva_base]")
    assert "jamais ajouter une" in t and "casse le diff de surcharge" in t, (
        "le contournement fautif -- depanner en declarant dans [diva_base] -- doit etre "
        "interdit AVEC sa raison")
    return "cas nomme, declencheur et fausse sortie"


@cas("18. La corroboration citee par la page existe vraiment (#225)")
def cas18():
    """Une page qui cite une preuve doit tomber si la preuve disparait.

    La marque de preuve dit `rapporte`, corrobore par `converting-diva-lectab`. Si cette
    regle-la change de camp un jour, la page devient un ouI-dire non corrobore **sans que
    rien ne le signale**. Le cas relie donc l'affirmation a sa source, dans l'autre skill.
    """
    t = nu(plat(PAGE))
    assert "rapporte" in t and "corrobore" in t, (
        "le niveau de preuve doit etre declare, et la corroboration nommee")
    source = os.path.join(SKILLS, "converting-diva-lectab", "reference", "regles.md")
    assert os.path.isfile(source), "la source citee n'existe pas : %s" % source
    r = nu(plat(source))
    assert "restreint l'insertion des directives Module à ce seul bloc" in r, (
        "la corroboration citee a disparu de converting-diva-lectab : la page de "
        "surcharge ne peut plus s'en reclamer")
    return "affirmation reliee a sa source, dans l'autre skill"


@cas("14. Tous les liens de la page resolvent")
def cas14():
    base = os.path.dirname(PAGE)
    casses = []
    for cible in re.findall(r"\]\(([^)#]+\.md)\)", lire(PAGE)):
        if not os.path.isfile(os.path.normpath(os.path.join(base, cible))):
            casses.append(cible)
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
