#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de coherence de la page du journal des anomalies.

RETEX #197.

Meme principe que les autres suites du skill : la verification est faite en amont par
l'orchestrateur et consignee dans `reference/keywords-verifies.json` ; la suite verifie
**hors ligne** que les pages et le releve concordent.

Particularite de ce lot : la mesure n'a **pas** ete faite au graphe -- `diva-mcp` etait
indisponible. Elle a ete faite en lisant les fichiers de messages d'un pack standard avec le
skill `managing-diva-error-messages`. Le releve le dit, et le cas 1 verifie qu'il le dit.

Ce que les cas gardent :

- **Le mecanisme, pas seulement la convention.** Le RETEX affirmait « 9999 = texte libre ».
  C'est vrai, et la mesure dit *pourquoi* : le libelle stocke pour 9999 vaut `$1`, un pur
  passe-plat. Une page qui garderait la convention en perdant le mecanisme redeviendrait une
  regle juste par correlation -- le cas 3 l'interdit.
- **Une contre-observation levee, pas effacee.** Un appel `R3_Log_Ano(9000, ...)` releve chez
  un partenaire laissait croire a une seconde valeur reservee. La mesure montre que 9000 est
  un message catalogue ordinaire. Le cas 6 garde cette distinction.
- **Deux exceptions mesurees** qui rendent la regle utilisable : le prefixe de `a5ferr`, et
  les deux fichiers sans 9999. Les taire donnerait une regle plus simple et fausse.

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
PAGE = os.path.join(SKILL, "reference", "log-anomalies.md")
RELEVE = os.path.join(SKILL, "reference", "keywords-verifies.json")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
PAGE_ERRS = os.path.join(SKILLS, "managing-diva-error-messages", "SKILL.md")

# Pages que CE lot ecrit -- perimetre du controle structurel (cas 10).
PAGES_DU_LOT = (PAGE, PAGE_ERRS)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def bloc():
    return json.loads(lire(RELEVE))["mesures_graphe"]["log_ano"]


# --------------------------------------------------------------------------

@cas("1. Le releve porte le bloc log_ano, date, et DIT qu'il ne vient pas du graphe")
def cas1():
    """Une mesure faite autrement que d'habitude doit le declarer.

    Toutes les autres mesures du releve viennent du graphe. Celle-ci vient de la lecture
    des fichiers de messages. Laisser croire a une interrogation du graphe rendrait la
    provenance fausse, et la reserve invisible.
    """
    b = bloc()
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", b.get("date", "")), "bloc sans date"
    assert b.get("_page") == "log-anomalies.md", "le bloc doit dire quelle page il fonde"
    assert "pas au graphe" in b.get("_note", ""), (
        "la provenance doit etre explicite : ce n'est pas une mesure au graphe")
    assert b.get("niveau") == "mesure", "niveau de preuve manquant"
    assert b.get("non_verifie"), (
        "ce qui vient du seul retour partenaire doit rester declare non verifie")
    return "bloc date au %s, provenance et reserve declarees" % b["date"]


@cas("2. L'interdit MZ.Dos porte son contre-exemple, sa forme correcte, et le fait que ca COMPILE")
def cas2():
    """Le defaut que le RETEX signale a ete commis en generant du code.

    Une page qui dirait seulement « le 1er parametre est un numero » n'empecherait rien :
    c'est le contre-exemple nomme, et le fait que l'erreur passe la compilation, qui
    rendent la regle memorable.
    """
    t = nu(plat(PAGE))
    assert "JAMAIS MZ.Dos" in t, "l'interdit doit etre enonce, pas seulement suggere"
    assert "G3_Log_Ano(MZ.Dos" in t, "montrer la forme FAUSSE"
    assert "G3_Log_Ano(9999" in t, "montrer la forme JUSTE a cote"
    assert "compile" in t, "dire que l'erreur passe la compilation"
    assert "variable de contexte metier" in t, (
        "generaliser : ce n'est pas seulement MZ.Dos qui est interdit")
    return "interdit, contre-exemple, forme juste, silence du compilateur"


@cas("3. 9999 est explique par son MECANISME, pas donne comme une convention")
def cas3():
    """Le coeur du lot.

    « 9999 = texte libre » est une regle juste par usage. Le libelle `$1` en est la CAUSE :
    le message affiche est le parametre. Perdre cette phrase, c'est reperdre la difference
    entre une correlation et un mecanisme.
    """
    t = nu(plat(PAGE))
    assert "$1" in t, "le libelle qui explique tout doit figurer"
    assert "passe-plat" in t, "nommer ce que fait ce libelle"
    assert "concue pour ca" in t or "concue pour cela" in t, (
        "dire que ce n'est PAS une convention arbitraire")
    b = bloc()
    assert "passe-plat" in b.get("mecanisme", ""), (
        "le releve doit porter le meme mecanisme que la page")
    return "mecanisme ecrit des deux cotes"


@cas("4. Les chiffres de la page concordent avec le releve")
def cas4():
    """Chaque chiffre est ancre a SA phrase, pas cherche dans toute la page.

    La premiere version testait `str(n) in texte`. C'est un test de **sous-chaine** : il
    reste vrai quand le chiffre subsiste ailleurs -- dans une autre phrase, ou meme cache
    a l'interieur d'un nombre plus long. Le harnais de mutation l'a montre : changer
    « 11 portent 9999 » en « 12 portent » laissait le cas passer. Un chiffre doit donc
    etre confronte a l'affirmation qu'il fonde.
    """
    b = bloc()
    t = nu(plat(PAGE))
    total = b["fichiers_xxferr_du_pack"]
    avec = b["portant_le_code_9999"]
    exact = b["libelle_9999_exactement_dollar1"]
    sans = total - avec

    phrases = [
        ("sur les %d fichiers de messages" % total, "le total du pack"),
        ("sur les %d fichiers de messages qui portent" % avec, "le nombre portant 9999"),
        ("%d valent exactement" % exact, "le nombre au libelle exact"),
        ("%d ne portent pas" % sans, "le nombre sans 9999"),
    ]
    for phrase, libelle in phrases:
        assert phrase.lower() in t.lower(), (
            "%s : la page ne porte pas la phrase %r -- un chiffre qui n'est pas rattache "
            "a son affirmation ne prouve rien" % (libelle, phrase))

    assert sans == len(b["sans_le_code_9999"]), (
        "le releve se contredit : %d manquants annonces, %d nommes"
        % (sans, len(b["sans_le_code_9999"])))
    return "%d fichiers, %d avec 9999, %d au libelle exact, %d sans -- chacun dans sa phrase" % (
        total, avec, exact, sans)


@cas("5. L'exception du socle est ecrite avec son EFFET, pas seulement signalee")
def cas5():
    """Signaler « a5ferr differe » n'aide personne.

    Ce qui compte est le resultat concret : le texte sort prefixe. C'est la seule forme qui
    permet au lecteur de decider s'il s'en moque ou pas.
    """
    t = nu(plat(PAGE))
    b = bloc()
    assert "a5ferr" in t, "nommer le fichier concerne"
    assert "Erreur $1" in t, "donner le libelle qui differe"
    assert "Erreur Traitement termine" in t or "ecrit Erreur" in t, (
        "montrer l'EFFET sur un appel reel")
    assert "a5ferr" in b.get("exception", ""), "le releve doit porter la meme exception"
    return "exception nommee, effet montre"


@cas("6. 9000 est traite comme un code catalogue, pas comme une 2e valeur reservee")
def cas6():
    """Leve une contre-observation, sans l'effacer.

    Un appel `R3_Log_Ano(9000, ...)` releve chez un partenaire pouvait faire croire a une
    seconde valeur reservee. La mesure dit le contraire. Le cas garde la distinction :
    sans elle, un lecteur pourrait reintroduire 9000 comme « autre facon d'ecrire libre ».
    """
    t = nu(plat(PAGE))
    b = bloc()
    assert "9000" in t, "le code temoin doit figurer"
    assert "Fichier $2 absent" in t, "donner son libelle reel"
    assert "n'ecrit donc pas ce texte" in t or "n'ecrit donc" in t, (
        "dire la consequence : passer 9000 avec un texte n'ecrit pas ce texte")
    assert "seconde valeur reservee" in b.get("code_catalogue_temoin", ""), (
        "le releve doit garder la trace de la contre-observation levee")
    return "9000 documente comme code ordinaire"


@cas("7. La page donne le moyen de VERIFIER, et nomme le skill qui le porte")
def cas7():
    t = nu(plat(PAGE))
    assert "managing-diva-error-messages" in t, "nommer le skill proprietaire des codes"
    assert "--check" in t, "donner la commande, pas seulement l'intention"
    assert "found" in t and "message" in t, (
        "dire ce que la reponse contient -- c'est le libelle qui tranche")
    cible = os.path.join(SKILLS, "managing-diva-error-messages", "SKILL.md")
    assert os.path.isfile(cible), "le skill cite n'existe pas : %s" % cible
    return "commande donnee, skill existant"


@cas("8. Les niveaux de preuve sont distingues : mesure / corrobore / non verifie")
def cas8():
    """Trois provenances differentes dans une meme page.

    Les melanger donnerait a la signature -- qui vient du seul retour partenaire -- le meme
    poids qu'aux chiffres mesures. C'est precisement ce que le tableau doit empecher.
    """
    t = nu(plat(PAGE))
    for marqueur in ("mesure", "corrobore", "NON verifie"):
        assert marqueur in t, "niveau de preuve absent du tableau : %s" % marqueur
    assert "applic" in t, "le point non verifie doit etre NOMME, pas resume"
    assert "Interroger le graphe" in t or "interroger le graphe" in t.lower(), (
        "dire ce qui reste a faire")
    return "3 niveaux distingues, point non verifie nomme"


@cas("9. managing-diva-error-messages porte la reciproque, et ses chiffres concordent")
def cas9():
    """La correction touche deux skills ; celui qui possede les codes doit le savoir.

    Sans cette section, un lecteur du skill des messages ne saurait pas que 9999 a un
    consommateur, ni pourquoi son libelle est un simple `$1`.
    """
    t = nu(plat(PAGE_ERRS))
    b = bloc()
    assert "Log_Ano" in t, "la reciproque doit nommer les fonctions consommatrices"
    assert "9999" in t and "$1" in t, "et porter le mecanisme"
    assert "coding-diva-advanced" in t, "renvoyer vers la page qui detaille"
    assert "log-anomalies.md" in t, "et la nommer"
    # Meme discipline qu'au cas 4 : le chiffre est confronte a SA phrase. Un `str(n) in t`
    # reste vrai quand le nombre subsiste ailleurs -- c'est ce qui laissait ce cas passer
    # sur une page mutee.
    for phrase, libelle in (
            ("sur les %d" % b["fichiers_xxferr_du_pack"], "total du pack"),
            ("%d portent" % b["portant_le_code_9999"], "nombre portant 9999"),
            ("dont %d avec exactement" % b["libelle_9999_exactement_dollar1"],
             "nombre au libelle exact")):
        assert phrase.lower() in t.lower(), (
            "%s : la page reciproque ne porte pas %r -- deux pages qui citent la meme "
            "mesure doivent citer les memes chiffres" % (libelle, phrase))
    return "reciproque presente, 3 chiffres ancres a leur phrase"


@cas("10. Aucune trace de poste ni d'identite dans les pages ecrites par ce lot")
def cas10():
    """Controle STRUCTUREL, volontairement pas une liste noire.

    Ces tests sont distribues avec le skill : y ecrire les noms qu'on veut proteger
    reviendrait a les publier. On interdit donc les FORMES par lesquelles ils arrivent.
    La mesure de ce lot a ete faite sur un pack reel d'un poste -- c'est exactement le
    genre de lot ou un chemin absolu se glisse.
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


@cas("11. La page est atteignable depuis le SKILL.md")
def cas11():
    t = lire(SKILL_MD)
    assert "log-anomalies.md" in t, (
        "une page que le sommaire ne cite pas n'existe pas pour le lecteur")
    base = os.path.dirname(PAGE)
    casses = [c for c in re.findall(r"\]\(([^)#]+\.md)\)", lire(PAGE))
              if not os.path.isfile(os.path.normpath(os.path.join(base, c)))]
    assert not casses, "lien(s) casse(s) dans la page : %s" % casses
    return "citee par le sommaire, liens resolus"


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
