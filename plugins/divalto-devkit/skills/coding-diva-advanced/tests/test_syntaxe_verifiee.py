#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de coherence entre la page de syntaxe et le releve de verification MCP.

-- RETEX #202 #233 #234 #257 #299 #323 #324 #335 (+ regles extraites de
#253 et #256).

**Pourquoi ces tests ne parlent PAS au MCP.** Le plugin a une convention explicite :
« les scripts n'invoquent jamais le MCP directement -- c'est la responsabilite de
l'orchestrateur LLM » (cf. `querying-diva-graph/scripts/query_neo4j.py`). Un test qui
appellerait le graphe la violerait, et deviendrait de surcroit dependant du reseau et
d'une cle API partenaire.

Le decoupage retenu respecte cette frontiere :

- **l'orchestrateur LLM** interroge le MCP et consigne le resultat, date et source, dans
  `reference/keywords-verifies.json` ;
- **le test**, deterministe et hors ligne, verifie que la **page** et le **releve**
  concordent -- et surtout qu'aucune affirmation de la page n'est **absente** du releve.

C'est exactement ce qui manquait pour eviter le defaut d'origine : l'issue #233 affirmait
que « Round n'existe pas » alors que `Round` **existe** (instruction sans parametre). Une
affirmation d'inexistence est une affirmation comme une autre -- elle se verifie. Le cas 3
rend desormais impossible d'ecrire « X n'existe pas » sans releve a l'appui.

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
from _communs import nu, plat  # noqa: E402  (helpers partages, cf. _communs.py)

SKILL = os.path.abspath(os.path.join(HERE, ".."))
REFERENCE = os.path.join(SKILL, "reference")
PAGE = os.path.join(REFERENCE, "syntaxe-de-base.md")
RELEVE = os.path.join(REFERENCE, "keywords-verifies.json")

CAS = []

# Mots cites par la page en exemple de code, et qui ne sont PAS des mots-cles du langage.
#
# ATTENTION -- cette liste est le point faible du cas 8, et elle a DEJA masque une erreur.
# Elle exemptait `continue` et `break` : la page les presentait comme des reflexes C sans
# equivalent DIVA, alors que les DEUX existent (famille Switch, avec un sens DIFFERENT --
# `Break` sort du Switch, `Continue` enchaine sur le Case suivant). L'exemption avait
# supprime le seul controle qui l'aurait dit, et la suite passait 11/11 sur une page
# fausse. Toute entree ajoutee ici desarme une verification : le cas 12 exige donc qu'un
# mot exempte soit inconnu du releve.
HORS_PERIMETRE = {"function", "procedure", "messagebox", "int", "carre", "affichemessage",
                  "mess", "variable", "expression", "nature", "standard", "non_verifie",
                  # Helper du STANDARD, pas un mot-cle du langage : le releve ne couvre que
                  # le langage. Il est documente par une autre page du meme skill
                  # (module-table.md), donc cite ici sans etre affirme. Le cas 12 verifie
                  # par ailleurs qu'aucune exemption ne recouvre une entree du releve.
                  "initialiser_caseacocher",
                  # Identifiants du STANDARD cites comme PREUVE D'USAGE (une concatenation
                  # et un acces indice lus dans des sources livrees). Ce sont des symboles
                  # de l'ERP, pas du langage -- le releve ne les couvre pas, et les retirer
                  # de la page reviendrait a retirer la preuve. INTERDIT d'ajouter ici un
                  # mot-cle du langage : le cas 12 le refuserait, et ce serait un trou.
                  "version_erp_ux", "wmsoc"}


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


def releve():
    return json.loads(lire(RELEVE))


def mots_en_code(texte):
    """Les identifiants cites en `code` dans la page, minuscules.

    On prend l'identifiant de TETE de chaque bloc `...` : la page cite des
    constructions entieres (`Until <expr>`, `For <cpt> = <deb> To <fin>`), pas
    seulement des mots nus. Un motif exigeant un backtick purement alphabetique
    ratait Until, For, Loop et Do -- et laissait donc passer une page qui aurait pu
    ne pas les documenter du tout.
    """
    return {m.lower() for m in re.findall(r"`([A-Za-z][A-Za-z0-9_$]*)[^`]*`", texte)}


# --------------------------------------------------------------------------

@cas("1. Le releve porte sa source, sa version et sa date")
def cas1():
    r = releve()
    for cle in ("source", "version_erp", "date_verification"):
        assert r.get(cle), "champ '%s' manquant : un releve sans provenance ne vaut rien" % cle
    assert "get_native_keyword_doc" in r["source"], r["source"]
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["date_verification"]), r["date_verification"]
    return "%s / %s / %s" % (r["source"], r["version_erp"], r["date_verification"])


@cas("2. Chaque entree du releve porte un niveau de preuve declare")
def cas2():
    r = releve()
    niveaux = set(r["niveaux_de_confiance"])
    total = 0
    for section in ("existe", "n_existe_pas"):
        for mot, info in r[section].items():
            c = info.get("confiance")
            assert c in niveaux, "%s : confiance %r hors des niveaux declares %s" % (
                mot, c, sorted(niveaux))
            total += 1
    directs = sum(1 for s in ("existe", "n_existe_pas")
                  for i in r[s].values() if i.get("confiance") == "direct")
    return "%d entrees, dont %d verifiees en direct" % (total, directs)


@cas("3. Toute INEXISTENCE affirmee par la page figure au releve")
def cas3():
    """Le coeur du lot : on n'affirme pas qu'un mot-cle n'existe pas sans l'avoir verifie."""
    texte = lire(PAGE)
    absents = set(releve()["n_existe_pas"])
    # Une revendication d'inexistence est portee par une LIGNE DE TABLEAU, et par le mot
    # de sa PREMIERE colonne : la suite de la ligne donne le remplacant, qui lui existe
    # (`If`, `Case`, `Next`). Le texte courant est exclu -- il commente les cas (« ce qui
    # n'existe pas, c'est la fonction Round(x) ») sans rien revendiquer de neuf.
    revendiques = set()
    for ligne in texte.split("\n"):
        if not ligne.lstrip().startswith("|"):
            continue
        if "n'existe pas" not in ligne.lower():
            continue
        tetes = re.findall(r"`([A-Za-z][A-Za-z0-9_$]*)", ligne)
        if tetes:
            revendiques.add(tetes[0].lower().rstrip("("))
    presents = set(releve()["existe"])
    sans_preuve = sorted(m for m in revendiques if m not in absents and m not in presents)
    assert not sans_preuve, (
        "la page affirme l'inexistence de %s sans entree au releve -- c'est exactement "
        "l'erreur que ce lot corrige (cf. Round)" % sans_preuve)
    contredits = sorted(m for m in revendiques if m in presents)
    assert not contredits, (
        "la page affirme que %s n'existe(nt) pas alors que le releve les donne EXISTANTS "
        "-- c'est litteralement le defaut Round : affirmer une inexistence contre la "
        "preuve disponible" % contredits)
    return "%d inexistence(s) affirmee(s), toutes justifiees" % len(absents)


@cas("4. Aucune contradiction : un mot du releve n'est pas dans les deux sections")
def cas4():
    r = releve()
    collision = set(r["existe"]) & set(r["n_existe_pas"])
    assert not collision, "mot(s) a la fois existant et inexistant : %s" % sorted(collision)


@cas("5. Le piege Round est documente comme tel, pas comme une inexistence")
def cas5():
    r = releve()
    assert "round" in r["existe"], (
        "Round DOIT figurer comme existant -- c'est le defaut d'origine de #233")
    assert r["existe"]["round"]["nb_params"] == 0, r["existe"]["round"]
    texte = lire(PAGE)
    assert "Round` existe" in texte or "`Round` **existe**" in texte, (
        "la page doit dire que Round EXISTE, sinon elle reproduit l'erreur du RETEX")
    assert "instruction" in texte.lower() and "Truncate" in texte, (
        "il faut dire ce que Round EST (instruction de mode) et son pendant Truncate")
    return "existence affirmee, nature (instruction 0 parametre) precisee"


@cas("6. La matrice des boucles est complete : 4 boucles x (terminateur, sortie, continue)")
def cas6():
    r = releve()["existe"]
    matrice = {
        "for":    ("next", "exitfor", "redofor"),
        "loop":   ("endloop", "exitloop", "redoloop"),
        "do":     ("wend", "exitdo", "redodo"),
        "repeat": ("until", "exitrepeat", "redorepeat"),
    }
    texte = lire(PAGE)
    for boucle, mots in matrice.items():
        for mot in mots:
            assert mot in r, "%s (boucle %s) absent du releve" % (mot, boucle)
            assert mot in mots_en_code(texte), "%s absent de la page" % mot
    return "4 boucles x 3 mots-cles = 12 entrees, toutes relevees et documentees"


@cas("7. L'asymetrie FReturn / PReturn est dite, avec sa consequence a l'EXECUTION")
def cas7():
    r = releve()["existe"]
    assert r["freturn"]["nb_params"] == 1, r["freturn"]
    assert r["preturn"]["nb_params"] == 0, r["preturn"]
    texte = lire(PAGE)
    assert "OBLIGATOIRE" in texte or "obligatoire" in texte.lower()
    assert "INTERROMPU" in texte or "interrompu" in texte.lower(), (
        "l'absence de FReturn ne casse PAS la compilation : elle casse a l'execution, "
        "c'est le point dangereux")
    return "1 parametre / 0 parametre, obligatoire / facultatif, panne au runtime"


@cas("8. Tout mot cite en code dans la page est connu du releve, ou explicitement non verifie")
def cas8():
    """Empeche d'introduire une affirmation nouvelle sans passer par la verification."""
    r = releve()
    connus = set(r["existe"]) | set(r["n_existe_pas"]) | set(r.get("non_verifie", {}))
    # Mots-cles du langage cites dans la page (on ignore noms de fichiers et sections)
    cites = {m for m in mots_en_code(lire(PAGE))
             if not m.endswith((".md", ".json")) and len(m) > 2}
    # Vocabulaire structurel cite en exemple, hors perimetre du releve
    # Vocabulaire cite en exemple ou traite par une AUTRE page du skill : hors du
    # perimetre de ce releve, mais liste explicitement -- une exemption tacite serait
    # un trou par lequel une affirmation non verifiee pourrait rentrer.
    inconnus = sorted(cites - connus - HORS_PERIMETRE)
    assert not inconnus, (
        "mot(s) cite(s) par la page sans entree au releve ni exemption : %s -- "
        "verifier au MCP puis completer keywords-verifies.json" % inconnus)
    return "%d mots-cles cites, tous adosses au releve" % len(cites & connus)


@cas("9. Les incertitudes sont declarees, pas tues")
def cas9():
    r = releve()
    nv = r.get("non_verifie") or {}
    assert nv, "le releve doit porter ce qui n'a PAS ete verifie"
    # Une incertitude RESOLUE doit sortir de non_verifie, sinon le releve se contredit et
    # la page continue d'afficher un doute leve. C'est arrive a la regle Proto (#299) :
    # verifiee dans un second temps (Proto / EndProto), ses deux entrees devaient partir.
    resolus = sorted(k for k in nv if k in r["existe"] or k in r["n_existe_pas"])
    assert not resolus, (
        "point(s) declare(s) non verifie(s) alors que le releve les a tranches : %s -- "
        "les retirer de non_verifie" % resolus)
    texte = lire(PAGE)
    assert "non verifiee" in texte or "non_verifie" in texte, (
        "la page doit signaler elle-meme ses affirmations non verifiees")
    return "%d point(s) declare(s) non verifie(s) : %s" % (len(nv), ", ".join(sorted(nv)))


@cas("10. La page est citee par le SKILL.md et le releve par la page")
def cas10():
    skill = lire(os.path.join(SKILL, "SKILL.md"))
    assert "reference/syntaxe-de-base.md" in skill, "page non atteignable depuis le SKILL.md"
    assert "keywords-verifies.json" in skill, (
        "le releve doit etre visible depuis le SKILL.md : c'est lui qui rend la page fiable")
    assert "keywords-verifies.json" in lire(PAGE), "la page doit renvoyer a son releve"


@cas("11. Le resume du SKILL.md ne contredit pas le releve")
def cas11():
    """Le SKILL.md redit le tableau des faux amis : deux textes = deux chances de deriver.

    C'est le motif qui a produit les asymetries entre scripts freres de ce cycle
    et la derive du catalogue : une duplication qui n'est mise a
    jour que si l'on y pense. Ici on la garde par un test.
    """
    skill = lire(os.path.join(SKILL, "SKILL.md"))
    r = releve()
    absents, presents = set(r["n_existe_pas"]), set(r["existe"])
    faux = []
    for ligne in skill.split("\n"):
        if not ligne.lstrip().startswith("|") or "n'existe pas" not in ligne.lower():
            continue
        tetes = re.findall(r"`([A-Za-z][A-Za-z0-9_$]*)", ligne)
        if not tetes:
            continue
        mot = tetes[0].lower().rstrip("(")
        if mot in presents:
            faux.append("%s : donne INEXISTANT par le SKILL.md, EXISTANT par le releve" % mot)
        elif mot not in absents:
            faux.append("%s : donne inexistant par le SKILL.md, absent du releve" % mot)
    assert not faux, "le resume du SKILL.md a derive : " + " | ".join(faux)
    # Et le point le plus facile a perdre en resumant : Round existe.
    assert "`Round` existe" in skill, (
        "le SKILL.md doit dire que Round EXISTE ; un resume qui coupe cette nuance "
        "reintroduit exactement l'erreur du RETEX")
    return "resume concordant avec le releve"


@cas("13. Les deux pieges qui CASSENT A L'EXECUTION sont dits, avec leur remede")
def cas13():
    """Ces deux-la ne se voient pas a la compilation. Une page qui les perd est dangereuse.

    - Sortir d'un `Switch` par un `Exit*` : le selecteur reste sur la pile (confirme par
      l'architecte, la doc parlant d'« un EXIT » sans nommer la famille).
    - Le mode `Round`/`Truncate` : sa portee n'est pas etablie, donc la page DOIT
      recommander l'indicateur porte par l'affectation.
    """
    texte = lire(PAGE)
    assert "Endswitch" in texte and "Break" in texte, "la section Switch a disparu"
    # Prose enveloppee a 88 colonnes et prefixee de '> ' dans les blocs de citation :
    # chercher une chaine litterale casserait au moindre reformatage. On aplatit d'abord --
    # le test doit tenir sur le SENS present, pas sur la position des retours a la ligne.
    plat = " ".join(texte.replace("\n>", "\n").split())
    for attendu, motif in [
        ("l'interdiction de sortir d'un Switch par un Exit*",
         "jamais sortir de la structure par un GOTO ni par un EXIT"),
        ("le remede : Break puis sortie APRES Endswitch",
         "apres `Endswitch`"),
        ("la portee non etablie du mode Round/Truncate",
         "n'est pas documente"),
        ("la recommandation d'utiliser l'indicateur",
         "l'indicateur porte par l'affectation"),
    ]:
        assert motif in plat, "%s : introuvable dans la page (motif %r)" % (attendu, motif)
    r = releve()
    assert "portee_du_mode_round_truncate" in (r.get("non_verifie") or {}), (
        "la portee du mode reste NON ETABLIE : la retirer de non_verifie sans preuve "
        "reviendrait a affirmer ce que personne n'a verifie")
    return "les 2 pieges d'execution documentes, remede inclus"


@cas("12. Aucune exemption ne couvre un mot-cle connu du releve")
def cas12():
    """Garde la liste qui garde les autres cas.

    Une exemption sur un vrai mot-cle est pire qu'inutile : elle DESARME le cas 8 sur ce
    mot. C'est ce qui est arrive a `continue` et `break` -- exemptes, donc jamais
    confrontes au releve, donc la page a pu affirmer pendant tout le lot qu'ils
    n'existaient pas en DIVA. Ils existent.
    """
    r = releve()
    connus = set(r["existe"]) | set(r["n_existe_pas"])
    morts = sorted(HORS_PERIMETRE & connus)
    assert not morts, (
        "exemption(s) portant sur un mot-cle connu du releve : %s -- une exemption "
        "desarme le cas 8 sur ce mot ; la retirer, le releve suffit" % morts)
    # Une incertitude declaree n'est pas une exemption : elle doit rester visible.
    caches = sorted(HORS_PERIMETRE & set(r.get("non_verifie") or {}))
    assert not caches, (
        "mot(s) a la fois exempte(s) et declare(s) non verifie(s) : %s -- l'exemption "
        "annule la declaration d'incertitude" % caches)
    return "%d exemptions, aucune ne masque le releve" % len(HORS_PERIMETRE)


@cas("14. Les cinq faux amis du LOT F sont au tableau ET au releve, avec leur equivalent")
def cas14():
    """RETEX #96.

    Le partenaire avait conclu a un ecart entre versions d'ERP. Les cinq noms sont en
    realite des faux amis. Ce cas garde les DEUX moities : la page doit les montrer avec
    l'equivalent DIVA, et le releve doit porter l'inexistence -- sinon la page affirmerait
    une inexistence sans trace, ce que le cas 3 interdit deja par ailleurs.
    """
    t = nu(plat(PAGE))
    r = releve()
    for faux, vrai in (("SplitCount", "SplitList"), ("SplitItem", "SplitList"),
                       ("Pos(...)", "String"), ("Len(...)", "Length")):
        assert faux in t, "faux ami absent du tableau de la page : %s" % faux
        assert vrai in t, "equivalent absent de la page : %s" % vrai
    for mot in ("splitcount", "splititem", "pos", "len"):
        assert mot in r["n_existe_pas"], "%s absent de n_existe_pas" % mot
        assert r["n_existe_pas"][mot].get("remplace_par"), (
            "%s : une inexistence sans equivalent n'aide personne" % mot)
    assert "Loop while" in t, "la forme de boucle invalide doit etre citee"
    assert "Do ... While ... Wend" in t, "et son equivalent reel donne"
    return "4 noms + 1 forme de boucle, page et releve concordants"


@cas("15. Le piege de SENS sur String est ecrit, et distingue de Str")
def cas15():
    """Le seul des cinq qui COMPILE.

    `String` existe. Un developpeur venu de BASIC l'utilisera pour fabriquer une chaine
    repetee : ca compile, et ca fait autre chose. Sans la mention du SENS, la ligne du
    tableau serait vide de contenu -- et la confusion avec `Str` (conversion) reste le
    second piege, puisque les deux noms se ressemblent.
    """
    t = nu(plat(PAGE))
    r = releve()
    assert "String existe et cherche" in t, "dire ce que String FAIT"
    assert "position" in t, "dire ce qu'il rend"
    assert "Str, qui convertit" in t, "distinguer String de Str, sinon la confusion demeure"
    note = r["existe"]["string"]["note"]
    assert "POSITION" in note.upper() and "Str" in note, (
        "le releve doit porter la meme distinction que la page")
    return "sens dit, confusion avec Str ecartee"


@cas("16. Le point « Mot inconnu != absent de cette version » porte sa raison ET sa reserve")
def cas16():
    """Ce cas garde deux choses en sens opposes.

    Sens 1 -- la page doit REFUSER le tableau par version que le RETEX demandait, en disant
    pourquoi (il encoderait une cause fausse). Sans ce refus motive, un lot ulterieur le
    reconstruirait.
    Sens 2 -- les quatre inexistences de ce lot n'ont PAS ete interrogees au graphe. La
    reserve doit rester ecrite dans le releve : la retirer transformerait une position en
    verification, ce qui est exactement la faute que la regle A2bis interdit.
    """
    t = nu(plat(PAGE))
    r = releve()
    assert "ne veut presque jamais dire" in t, "le point de tete doit etre present"
    assert "cause fausse" in t, "dire POURQUOI le tableau par version est refuse"
    assert "compilateur" in t, (
        "nommer ce qui pourrait reellement varier, sinon le refus reste une opinion")
    manquantes = [m for m in ("splitcount", "splititem", "pos", "len")
                  if "_reserve" not in r["n_existe_pas"][m]]
    assert not manquantes, (
        "inexistence(s) sans reserve alors qu'aucune variante n'a ete testee : %s" % manquantes)
    for m in ("splitcount", "splititem", "pos", "len"):
        assert r["n_existe_pas"][m]["confiance"] == "architecte", (
            "%s ne peut pas etre 'direct' : le graphe n'a pas ete interroge" % m)
        assert r["n_existe_pas"][m]["variantes_testees"] == [], (
            "%s : declarer des variantes testees serait faux" % m)
    return "refus motive du tableau, 4 reserves A2bis intactes"


# Marqueurs qui font d'une occurrence de « NON = 0 » une REFUTATION et non une prescription.
# Sans cette distinction, un controle qui bannit la chaine dans tout le fichier tombe sur la
# note de correction elle-meme -- defaut deja commis au LOT E, corrige la aussi.
REFUTATION = ("affirmait", "etait faux", "etaient faux", "ne jamais supposer",
              "ne PAS ecrire", "ne pas ecrire", "correction")


def phrases_prescrivant(texte, chaine):
    """Les phrases qui contiennent `chaine` SANS marqueur de refutation."""
    return [p for p in re.split(r"(?<=[.!?])\s+", texte)
            if chaine in p and not any(m.lower() in p.lower() for m in REFUTATION)]


@cas("17. Le booleen DIVA : trois etats, contre-exemple, mesure -- et NON=0 jamais prescrit")
def cas17():
    """RETEX #252, et la plus longue erreur du devkit corrigee par ce cycle.

    Le skill affirmait `NON = 0` et « etat intermediaire = 1 ». Les deux etaient faux, et
    l'affirmation ne vivait que dans le SKILL.md et une eval -- **aucune page ne portait la
    regle**, donc rien ne la confrontait. Le cas garde les deux sens : la regle juste doit
    etre ecrite, et l'ancienne ne doit revenir sous aucune forme prescriptive.
    """
    t = nu(plat(PAGE))
    b = releve()["mesures_graphe"]["booleen_diva"]

    assert "non renseigne" in t, "le TROISIEME etat doit etre nomme"
    assert "TROIS etats" in t, "annoncer qu'il y en a trois, pas deux"
    # Les valeurs sont confrontees a LEUR LIGNE du tableau, pas cherchees dans la page :
    # `"1" in texte` est vrai partout. C'est la meme faiblesse que le harnais a trouvee sur
    # les cas 4 et 9 de la suite du journal -- un chiffre doit etre ancre a son affirmation.
    for etat, valeur in (("NON", b["correspondance"]["non"]),
                         ("OUI", b["correspondance"]["oui"])):
        ligne = "| %s | %s | %s |" % (etat, valeur, valeur)
        assert ligne in t, (
            "le tableau des etats ne porte pas %r -- la valeur de %s doit etre lue sur sa "
            "ligne, pas devinee" % (ligne, etat))
    assert "| non renseigne | 0 | espace |" in t, (
        "la ligne du troisieme etat doit dire 0 en numerique et espace en alphanumerique")
    assert "teste « non renseigne », pas « non »" in t, (
        "montrer le contre-exemple : un test a zero ne teste pas « non »")
    assert "constantes nommees" in t, "prescrire Oui / Non plutot que les litteraux"

    for cle in ("colonnes_drapeau_numeriques", "colonnes_avec_0_1_et_2_ensemble",
                "colonnes_du_motif_1_2", "colonnes_drapeau_alphanumeriques_1c"):
        assert str(b[cle]) in t, "chiffre absent de la page : %s = %s" % (cle, b[cle])
    assert b["non_verifie"], (
        "la mesure porte sur des DONNEES, pas sur la declaration des constantes : "
        "la reserve doit rester ecrite")

    fautives = phrases_prescrivant(t, "NON = 0")
    assert not fautives, (
        "phrase(s) prescrivant NON = 0 sans la refuter : %r" % fautives[:1])
    return "3 etats, contre-exemple, %d chiffres, reserve intacte" % 4


@cas("18. Le skill ne se contredit plus : SKILL.md, eval et page disent la meme chose")
def cas18():
    """Le defaut de #252 n'etait pas une page fausse, c'etait une regle SANS page.

    Elle ne vivait que dans le sommaire et dans une eval -- deux endroits qu'aucun test ne
    confrontait l'un a l'autre. Ce cas les confronte tous les trois.
    """
    b = releve()["mesures_graphe"]["booleen_diva"]
    somm = nu(plat(os.path.join(SKILL, "SKILL.md")))
    assert "NON = %s" % b["correspondance"]["non"] in somm, (
        "le sommaire doit porter la valeur mesuree de NON")
    fautives = phrases_prescrivant(somm, "NON = 0")
    assert not fautives, "le sommaire prescrit encore NON = 0 : %r" % fautives[:1]

    evals = lire(os.path.join(SKILL, "evals.json"))
    assert "NON = 1" in evals, "l'eval doit exiger la bonne valeur"
    fautives_ev = phrases_prescrivant(nu(" ".join(evals.split())), "NON = 0")
    assert not fautives_ev, "une eval prescrit encore NON = 0 : %r" % fautives_ev[:1]

    for page in os.listdir(REFERENCE):
        if not page.endswith(".md"):
            continue
        chemin = os.path.join(REFERENCE, page)
        restes = phrases_prescrivant(nu(plat(chemin)), "NON = 0")
        assert not restes, "%s prescrit NON = 0 : %r" % (page, restes[:1])
    return "sommaire, eval et pages de reference concordants"


def milliers(n):
    """1029 -> '1 029'. Les pages ecrivent les grands nombres avec une espace."""
    return "{:,}".format(n).replace(",", " ")


@cas("19. La concatenation a sa regle DANS UNE PAGE, avec son message trompeur")
def cas19():
    """RETEX #256, premiere moitie.

    La regle existait -- dans le SKILL.md seul (« + pour concatener -> utiliser & »). Meme
    defaut structurel que #252 : une regle qu'aucune page ne porte, donc qu'aucun cas ne
    confronte. Et elle ne couvrait que la forme `+`, pas les crochets, qui est celle du cas
    vecu.
    """
    t = nu(plat(PAGE))
    b = releve()["mesures_graphe"]["concatenation"]
    assert "l'operateur est &" in t, "la regle doit etre enoncee dans la page"
    for faute in b["formes_fautives"]:
        marqueur = "+" if faute == "+" else "crochets"
        assert marqueur in t, "forme fautive non citee : %s" % faute
    assert "Parenthese attendue apres un nom de fonction" in t, (
        "donner le message tel qu'il sort du compilateur")
    assert "Le message ne nomme jamais la vraie cause" in t, (
        "dire que le message est trompeur -- c'est ce qui fait perdre le temps")
    assert b["observe_dans_le_standard"], "le releve doit porter la preuve d'usage"
    return "regle, 2 formes fautives, message trompeur nomme"


@cas("20. Champ TABLEAU : parentheses, le piege des noms ambigus, et l'indice non devine")
def cas20():
    """RETEX #256, seconde moitie -- et la partie que le RETEX ne pouvait pas mesurer.

    Le RETEX disait « toujours verifier dans le dictionnaire ». C'est juste mais sans
    raison. La raison est chiffree : le MEME nom est tableau dans un enregistrement et
    scalaire dans un autre. Sans cette phrase, la regle reste un rituel ; avec elle, le
    lecteur sait pourquoi son autre programme ne prouve rien.
    """
    t = nu(plat(PAGE))
    b = releve()["mesures_graphe"]["champs_tableau"]

    assert "Tableau sans parenthese" in t, "donner le message du compilateur"
    assert "AdrTiers(4)" in t, "montrer la forme JUSTE"
    assert "AdrTiers[4]" in t, "montrer que les crochets ne sont pas l'indexation DIVA"
    assert "L'indice peut etre une variable" in t, (
        "sinon on croit l'indice limite a un litteral")

    for phrase, quoi in (
            ("Sur %s colonnes" % milliers(b["colonnes_totales"]), "total des colonnes"),
            ("%s appartiennent a un champ multi-occurrence" % milliers(b["colonnes_indicees"]),
             "colonnes indicees"),
            ("soit %s champs tableau" % milliers(b["champs_tableau_distincts"]),
             "champs tableau"),
            ("%d noms distincts" % b["noms_de_champ_tableau"], "noms distincts"),
            ("Et %d de ces %d noms" % (b["noms_tableau_ici_scalaire_ailleurs"],
                                       b["noms_de_champ_tableau"]), "noms ambigus")):
        assert phrase in t, (
            "%s : la page ne porte pas %r -- chaque chiffre doit etre ancre a son "
            "affirmation, pas cherche dans la page" % (quoi, phrase))

    assert "tableau dans un enregistrement" in t and "scalaire dans un autre" in t, (
        "c'est la RAISON de la regle : sans elle, « verifier le dictionnaire » est un rituel")
    assert "managing-diva-dictionaries" in t, "renvoyer au skill qui possede le dictionnaire"
    assert "usage existant" in t, "donner le second moyen, celui qui donne la semantique"
    assert b["non_verifie"], (
        "la semantique des indices n'est pas etablie : la reserve doit rester ecrite")
    assert b["deduit"], "la correspondance colonne SQL <-> champ DIVA est deduite, pas lue"
    return "%s noms de champ tableau, %d ambigus -- regle, raison et reserve" % (
        milliers(b["noms_de_champ_tableau"]), b["noms_tableau_ici_scalaire_ailleurs"])


@cas("21. `Oui` / `Non` : constantes DECLAREES, et le piege est ecrit (#252)")
def cas21():
    """La valeur etait mesuree en base, la NATURE ne l'etait pas.

    Le graphe dit `obj_type=consts`, `scope_type=root` : ce sont des constantes declarees
    **par programme**, pas des mots-cles du langage. La consequence est ce qui compte pour
    un partenaire -- les ecrire dans son propre module donne « Mot inconnu » -- et c'est
    exactement le piege de la section voisine, avec un nom qui a l'air standard.
    """
    t = nu(plat(PAGE))
    r = releve()
    for nom, valeur in (("oui", 2), ("non", 1)):
        e = r["existe"].get(nom)
        assert e, "%s doit etre passe de non_verifie a existe" % nom
        assert e["confiance"] == "direct", (
            "%s : le graphe a repondu, la confiance doit etre 'direct'" % nom)
        assert e["valeur"] == valeur, (
            "%s : le releve doit porter la valeur mesuree (%d)" % (nom, valeur))
        assert "root" in e["portee"], "%s : la portee mesuree est root (programme)" % nom
    # Ancrage sur la PHRASE, pas sur « Oui » (le mot est partout dans la page).
    assert "ne sont PAS des constantes du langage" in nu(lire(PAGE)), (
        "la page doit DIRE la nature, pas seulement prescrire d'ecrire les constantes")
    assert "tant que ce module ne les declare pas" in t, (
        "#252 : la consequence pratique -- « Mot inconnu » en specifique -- doit etre ecrite")
    return "valeurs 2/1, portee root, piege du specifique ecrit"


@cas("22. `Mid` : verifie au graphe, longueur OPTIONNELLE et affectation a gauche (#96)")
def cas22():
    """L'entree venait d'une OBSERVATION terrain, jamais d'une interrogation.

    Le graphe a confirme l'existence -- et donne deux proprietes que la forme observee chez
    le partenaire (toujours avec la longueur) ne pouvait pas reveler.
    """
    t = nu(plat(PAGE))
    e = releve()["existe"].get("mid")
    assert e, "mid doit etre passe de non_verifie a existe"
    assert e["confiance"] == "direct" and e["nb_params"] == 3, e
    assert "OPTIONNELLE" in t, "la longueur facultative doit etre dite"
    assert "a gauche d'une affectation" in t, (
        "Mid sert aussi a ECRIRE dans une sous-chaine : c'est la propriete la moins connue")
    return "existence, longueur optionnelle et affectation a gauche"


@cas("23. Une dette soldee ATTERRIT -- elle ne disparait pas du releve")
def cas23():
    """Garde-fou contre la fausse solde.

    Retirer une entree de `non_verifie` est trivial ; la solder demande qu'elle REAPPARAISSE
    dans `existe` avec une preuve. Sans ce cas, « solder trois dettes » pourrait vouloir
    dire « supprimer trois lignes », et le releve maigrirait en donnant l'air de progresser.
    """
    r = releve()
    soldees = ("mid", "oui", "non")
    for m in soldees:
        assert m not in r["non_verifie"], "%s est encore declare non verifie" % m
        assert m in r["existe"], "%s a disparu au lieu d'etre solde" % m
    # Les deux qui RESTENT doivent rester : aucune ne se tranche au graphe.
    restantes = set(r["non_verifie"])
    assert restantes == {"portee_du_mode_round_truncate",
                         "socle_audit_de_la_methode_update"}, (
        "les dettes restantes ne sont pas celles attendues : %s" % sorted(restantes))
    return "3 soldees dans 'existe', 2 restantes declarees"


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
