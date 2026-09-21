#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests du flux de connexion de `testing-erp` -- #222.

Le retour terrain qui a produit ces cas est un **feuilleton de debogage en cinq episodes**
dont les trois du milieu se sont reveles etre une **fausse piste** : le remede a ete cherche
du cote de `utilisateurHtml5.txt` pendant trois sessions, avant que la page de login ne
resolve le probleme.

Ce que ces cas gardent, et pourquoi :

- **La fausse piste ne doit pas revenir comme prescription** (cas 2). Le fichier est nomme
  dans la page -- il faut bien le nommer pour dire de ne pas y aller -- donc le controle
  travaille **phrase par phrase** et n'accepte le nom que dans une phrase qui le **refute**.
  Interdire le mot partout tomberait sur la mise en garde elle-meme : c'est une erreur deja
  commise ailleurs dans ce cycle.
- **La reserve reste ecrite** (cas 3). On ne sait pas si `/LCWeb` redirige de lui-meme vers
  `login.aspx` sur une install saine : l'observation vient d'une mise en service. D'ou un
  **repli**, pas un changement d'URL de depart -- et le cas garde les deux sens.
- **La frontiere avec le deploiement est ecrite** (cas 5). Les quatre autres episodes du
  feuilleton sont hors perimetre : conversion en application IIS, pool, compte de service.
  Sans cette phrase, le skill invite a repartir dans un terrier ou Claude ne peut rien.

Lancer :
    py plugin/skills/testing-erp/tests/test_connexion_verifiee.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
PAGE = os.path.join(SKILL, "SKILL.md")
EVALS = os.path.join(SKILL, "evals.json")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


REFUTATION = ("ne pas", "ne PAS", "ignore", "l'ignore", "fausse piste", "ne sert a rien",
              "appartient aux pages generiques", "jamais")


# Le gras markdown mettait le decoupeur en defaut : « ...txt`.** Ce fichier » ne coupait
# PAS, parce que le caractere avant l'espace est `*` et non `.`. Toute une mise en garde
# devenait donc UNE phrase, et son marqueur de refutation couvrait la prescription voisine.
# Une mutation l'a montre. On coupe aussi sur les fins de ligne : en markdown, la structure
# porte autant que la ponctuation.
COUPURE = re.compile(r"(?<=[.!?])[*_`)\]]*\s+|\n")


def phrases(texte):
    return [p for p in COUPURE.split(texte) if p and p.strip()]


def phrases_prescrivant(texte, chaine):
    """Les phrases qui contiennent `chaine` SANS marqueur de refutation."""
    return [p for p in phrases(texte)
            if chaine in p and not any(m.lower() in p.lower() for m in REFUTATION)]


# --------------------------------------------------------------------- les cas

@cas("1. Le repli nomme explicitement la page de login")
def cas1():
    t = lire(PAGE)
    # Ancrer sur L'ETAPE du workflow : l'URL figure aussi dans le texte explicatif, donc
    # une assertion sur la page entiere survivrait a sa disparition du mode operatoire.
    # C'est une mutation qui l'a montre -- la classe d'erreur la plus tenace de ce cycle.
    debut = t.index("## 3. Connexion a l'ERP")
    fin = t.index("### Le formulaire n'apparait pas")
    etapes = [e for e in re.findall(r"^\d+\. .*(?:\n   .*)*", t[debut:fin], re.M)
              if "login/login.aspx" in e]
    assert etapes, ("aucune ETAPE du workflow ne porte l'URL de repli "
                    "(elle est peut-etre encore citee dans le texte, ce qui ne suffit pas)")
    assert any("formulaire" in e.lower() for e in etapes), \
        "l'etape cite l'URL sans dire QUAND s'en servir"
    return "l'URL de repli est dans le mode operatoire, pas seulement dans le texte"


@cas("2. `utilisateurHtml5.txt` n'est nomme QUE pour etre ecarte")
def cas2():
    t = lire(PAGE)
    assert "utilisateurHtml5.txt" in t, \
        "la fausse piste n'est plus nommee -- elle reviendra par le raisonnement"
    fautives = phrases_prescrivant(t, "utilisateurHtml5.txt")
    assert not fautives, ("phrase(s) qui PRESCRIVENT la fausse piste :\n         %s"
                          % "\n         ".join(f[:160] for f in fautives))
    return "nomme, et refute dans chacune de ses phrases"


@cas("3. La reserve sur la redirection est ecrite, dans les DEUX sens")
def cas3():
    t = lire(PAGE)
    bloc = [p for p in phrases(t) if "redirige" in p.lower()]
    assert bloc, "l'incertitude sur la redirection n'est pas ecrite"
    assert any("Non verifie" in p or "non verifie" in p.lower() for p in bloc) \
        or "**Non verifie**" in t, "l'incertitude n'est pas declaree comme telle"
    assert "repli" in t.lower(), \
        "la consequence de l'incertitude -- un REPLI, pas un changement d'URL -- a disparu"
    depart = re.search(r"1\. `browser_navigate` vers `([^`]+)`", t)
    assert depart and depart.group(1).rstrip("/").endswith("/LCWeb"), \
        "l'URL de DEPART a ete changee alors que la redirection n'est pas verifiee : %s" \
        % (depart.group(1) if depart else "introuvable")
    return "incertitude ecrite, URL de depart inchangee"


@cas("4. Le workflow de connexion est numerote sans trou ni doublon")
def cas4():
    t = lire(PAGE)
    debut = t.index("## 3. Connexion a l'ERP")
    fin = t.index("### Le formulaire n'apparait pas")
    nums = [int(n) for n in re.findall(r"^(\d+)\. ", t[debut:fin], re.M)]
    assert nums == list(range(1, len(nums) + 1)), \
        "numerotation cassee par l'insertion : %s" % nums
    assert len(nums) >= 8, "le workflow a perdu des etapes : %d" % len(nums)
    return "%d etapes, numerotation continue" % len(nums)


@cas("5. La frontiere avec le deploiement est ecrite")
def cas5():
    t = lire(PAGE)
    assert "MachineToApplication" in t, \
        "l'erreur de deploiement la plus frequente n'est pas nommee"
    portantes = [p for p in phrases(t) if "MachineToApplication" in p
                 or "elevation" in p.lower()]
    assert any("deploiement" in p.lower() or "serveur" in p.lower() for p in portantes), \
        "l'erreur est nommee sans dire que c'est le deploiement, hors perimetre"
    return "frontiere nommee avec son symptome"


@cas("6. « Utilisateur inconnu » est rattache a Harmony, pas au deploiement")
def cas6():
    t = lire(PAGE)
    i = t.lower().find("utilisateur inconnu")
    assert i > 0, "le diagnostic « utilisateur inconnu » a disparu"
    bloc = t[i:i + 400]
    assert "Harmony" in bloc, "le diagnostic ne renvoie pas a la couche Harmony"
    assert re.search(r"ne pas repartir|NE PAS repartir|pas un probleme de deploiement",
                     bloc, re.I), \
        "rien n'interdit de repartir sur le deploiement -- c'est le terrier a eviter"
    return "rattache a Harmony, retour au deploiement interdit"


@cas("7. Les evals portent les deux situations")
def cas7():
    d = json.load(io.open(EVALS, encoding="utf-8"))
    noms = [s["name"] for s in d["scenarios"]]
    assert "connexion-formulaire-absent" in noms, "le scenario du formulaire absent manque"
    assert "utilisateur-inconnu-apres-login" in noms, "le scenario « utilisateur inconnu » manque"
    brut = json.dumps(d, ensure_ascii=False)
    assert "login/login.aspx" in brut, "les evals ne citent pas l'URL de repli"
    assert "utilisateurHtml5.txt" in brut and "NE PAS" in brut, \
        "les evals ne rappellent pas d'ecarter la fausse piste"
    return "%d scenarios, les deux situations couvertes" % len(noms)


@cas("8. Aucun mot de passe suggere, aucune trace de poste, page sous la limite")
def cas8():
    t = lire(PAGE)
    # Une MENTION n'est pas une prescription : « il contiendrait un mot de passe en clair »
    # est un argument CONTRE. On ne signale donc que si un verbe d'action l'accompagne.
    ACTION = ("creer", "ecrire", "renseigner", "saisir", "stocker", "mettre", "ajouter")
    fautives = [p for p in phrases(t)
                if "mot de passe en clair" in p.lower()
                and any(a in p.lower() for a in ACTION)
                and not any(m.lower() in p.lower() for m in REFUTATION)]
    assert not fautives, "une phrase suggere d'ecrire un mot de passe en clair : %s" % fautives
    # C:\Divalto\ est la racine du PRODUIT (identique partout), pas une trace de poste.
    for m in re.finditer(r"[A-Za-z]:\\{1,2}[^\s`)]*", t):
        assert re.match(r"[A-Za-z]:\\{1,2}Divalto\\", m.group(0), re.I), \
            "chemin absolu du poste dans une page distribuee : %s" % m.group(0)
    n = t.count("\n") + 1
    assert n < 500, "SKILL.md depasse la limite de 500 lignes : %d" % n
    return "%d lignes, aucun chemin de poste" % n


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
