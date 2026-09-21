#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests des garde-fous d'edition d'un .dhsf.

RETEX #173 #187 #268.

Deux familles, comme la suite de grammaire : **doc <-> releve** (les pages citent des chiffres
mesures sur le corpus, `reference/mesures-corpus.json` les porte et les qualifie) et
**fonctionnels** (les correctifs de script sont executes sur de vrais fichiers).

Ce que ces cas gardent :

- **Le defaut de #268 avait une cause plus profonde que son symptome.** `compute_max_id` ne
  regardait que les id PRESENTS et ignorait `dernier_id`, que le parser expose pourtant --
  alors que `action_add_page` respectait deja `dernier_id_page`. Une asymetrie a l'interieur
  d'un meme fichier. Le cas 6 rejoue le defaut reel : sans le plancher, un masque de surcharge
  a `dernier_id=1000000` recevait un id standard.
- **La regle de #187 ne se verifie pas.** Le RETEX enonce que la somme des `nb_lig` des pages
  de panels vaut la hauteur de la grille : 23 % au mieux sur 336 grilles. Le cas 9 garde les
  deux sens -- le refus doit rester ecrit avec son chiffre, et la formule ne doit pas revenir
  comme prescription.
- **Le compteur qui manquait.** Perdre un bouton dans un toolbar conserve laisse
  `toolbars_count` inchange : seul le compte des ITEMS le voit. Les cas 3 et 4 le gardent,
  documente et execute.

Lancer :
    py .claude/skills/manipulating-dhsf-screens/tests/run_all.py
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
REF = os.path.join(SKILL, "reference")
SCRIPTS = os.path.join(SKILL, "scripts")
RELEVE = os.path.join(REF, "mesures-corpus.json")
PAGE_STRUCT = os.path.join(REF, "dhsf-structure.md")
PAGE_SURCH = os.path.join(REF, "dhsf-overwrite-pattern.md")
PAGE_GRILLE = os.path.join(REF, "composant-grille-wpf.md")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
TEMPLATE_ZOOM = os.path.join(SKILL, "templates", "template_zoom_sql.dhsf")

PAGES_DU_LOT = (PAGE_STRUCT, PAGE_SURCH, PAGE_GRILLE)

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


def releve():
    return json.loads(lire(RELEVE))


def milliers(n):
    return "{:,}".format(n).replace(",", " ")


def executer(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                       capture_output=True)
    return json.loads(r.stdout.decode("utf-8", "replace"))


# --------------------------------------------------------------------------

@cas("1. Le releve porte les trois blocs du lot")
def cas1():
    r = releve()
    manquants = [b for b in ("bloc_ressources", "plancher_id", "grille_et_panels")
                 if b not in r]
    assert not manquants, "bloc(s) absent(s) : %s" % manquants
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["date_mesure"]), "releve sans date"
    for b in ("bloc_ressources", "grille_et_panels"):
        assert r[b].get("niveau") == "mesure", "%s : niveau de preuve manquant" % b
    return "3 blocs, mesure du %s" % r["date_mesure"]


@cas("2. [ressources] : portee MASQUE, 2 340/2 340, et le piege de l'adjacence")
def cas2():
    t = nu(plat(PAGE_STRUCT))
    b = releve()["bloc_ressources"]
    assert b["exceptions"] == 0, "le releve doit porter le zero exception"
    assert milliers(b["masques_avec_ressources"]) in t, "le total doit figurer"
    assert "APRES la derniere" in t, "dire ou le bloc se place"
    assert "portee est le masque entier" in t or "portee MASQUE" in t, "dire sa portee"
    # Ancre sur la PHRASE entiere : « touche » seul est un mot trop commun dans cette page
    # (la section [touches] existe), et le harnais de mutation l'a montre -- remplacer la
    # phrase laissait le cas passer. Meme faiblesse que chercher un chiffre nu.
    assert "le bloc touche la derniere page, sans lui appartenir" in t, (
        "c'est l'adjacence qui trompe : le dire en toutes lettres, sinon la regle parait "
        "arbitraire et se perd a la premiere reecriture")
    assert "Rien ne l'a signale" in t, (
        "dire que la perte est silencieuse -- ni compilateur, ni ouverture")
    return "%s/%s masques, 0 exception" % (
        milliers(b["ressources_apres_la_derniere_page"]),
        milliers(b["masques_avec_ressources"]))


@cas("3. La recette compteurs avant/apres est donnee, et nomme le compteur qui manquait")
def cas3():
    t = nu(plat(PAGE_STRUCT))
    assert "--summary" in t, "donner la commande, pas seulement l'intention"
    for compteur in ("pages_count", "widgets_total", "toolbars_count", "menus_count",
                     "ressources_items_count", "enregistrements_count"):
        assert compteur in t, "compteur absent de la recette : %s" % compteur
    assert "toolbars_count inchange" in t, (
        "dire POURQUOI le compte des items etait indispensable")
    assert "signal d'arret" in t, (
        "une baisse non voulue arrete l'edition, elle ne s'explique pas apres coup")
    return "6 compteurs, dont celui qui manquait"


@cas("4. FONCTIONNEL : le parser rend bien ressources_items_count")
def cas4():
    d = executer("dhsf_parser.py", "--path", TEMPLATE_ZOOM, "--summary")
    m = d.get("metrics", {})
    assert "ressources_items_count" in m, (
        "le compteur n'est pas rendu : la recette de la page ne marcherait pas")
    assert isinstance(m["ressources_items_count"], int), "doit etre un entier"
    for autre in ("toolbars_count", "menus_count", "pages_count", "widgets_total"):
        assert autre in m, "compteur %s disparu des metrics" % autre
    return "metrics : items=%s, toolbars=%s, menus=%s" % (
        m["ressources_items_count"], m["toolbars_count"], m["menus_count"])


@cas("5. Le plancher d'id est documente, avec sa formule et son refus du code en dur")
def cas5():
    t = nu(plat(PAGE_SURCH))
    b = releve()["plancher_id"]
    assert "plancher d'allocation" in t, "nommer le mecanisme"
    assert "plus grand id present" in t and "dernier_id declare" in t, (
        "donner la formule : le max des deux")
    assert "code en dur" in t, "dire qu'on ne code PAS 1000000 en dur"
    assert "2623" in t, (
        "citer la mesure qui justifie que respecter dernier_id vaut aussi pour un standard")
    assert b.get("pourquoi_pas_la_suggestion_du_retex"), (
        "le releve doit garder pourquoi la suggestion du RETEX n'a pas ete suivie telle quelle")
    assert b.get("asymetrie_interne"), "et la nature du defaut : une asymetrie interne"
    return "formule, refus du code en dur, mesure temoin"


@cas("6. FONCTIONNEL : l'allocation respecte le plancher sur un masque de surcharge")
def cas6():
    """Rejeu du defaut reel de #268.

    Masque a `dernier_id=1000000` dont les id presents restent bas : sans le plancher,
    l'allocation redonnait un id standard.
    """
    d = tempfile.mkdtemp(prefix="dhsf_b_")
    try:
        cible = os.path.join(d, "surcharge.dhsf")
        brut = io.open(TEMPLATE_ZOOM, encoding="iso-8859-1").read()
        mute = re.sub(r"dernier_id\s*=\s*\d+", "dernier_id=1000000", brut, count=1)
        assert "dernier_id=1000000" in mute, "le masque de test n'a pas ete prepare"
        io.open(cible, "w", encoding="iso-8859-1").write(mute)

        avant = executer("dhsf_parser.py", "--path", cible, "--summary")["metrics"]
        assert avant["dernier_id"] == 1000000, avant["dernier_id"]
        assert avant["max_id_found"] < 1000, (
            "le test n'a de sens que si les id presents sont BAS : %s" % avant["max_id_found"])

        page_tableau = None
        for p in executer("dhsf_parser.py", "--path", cible, "--summary")["pages"]:
            if p.get("element_types", {}).get("tableau"):
                page_tableau = p["numero"]
                break
        assert page_tableau is not None, "aucune page a tableau dans le template"

        res = executer("dhsf_modify.py", "--path", cible, "--action", "add-column",
                       "--params", json.dumps({"page_numero": page_tableau, "titre": "T",
                                               "vue": "ART", "champ": "Ref", "alias": "ART"}))
        assert res.get("success"), "add-column a echoue : %s" % res.get("error")
        alloue = res.get("id_allocated")
        assert alloue and alloue > 1000000, (
            "id alloue %s : le plancher n'est PAS respecte -- c'est exactement le defaut #268"
            % alloue)

        apres = executer("dhsf_parser.py", "--path", cible, "--summary")["metrics"]
        assert apres["dernier_id"] == alloue, (
            "dernier_id doit suivre l'allocation : %s != %s" % (apres["dernier_id"], alloue))
        return "id present %s + dernier_id %s -> alloue %s" % (
            avant["max_id_found"], avant["dernier_id"], alloue)
    finally:
        shutil.rmtree(d, ignore_errors=True)


@cas("7. Grille et panels : le mecanisme est ecrit, systematique, et atteignable")
def cas7():
    assert os.path.isfile(PAGE_GRILLE), "page absente"
    t = nu(plat(PAGE_GRILLE))
    b = releve()["grille_et_panels"]
    assert "composant-grille-wpf.md" in lire(SKILL_MD), (
        "une page que le SKILL.md ne cite pas n'existe pas pour le lecteur")
    assert "grille_parent" in t and "param_panel" in t, "nommer les deux cles"
    assert "idGrille" in t and "ligne" in t and "colonne" in t, (
        "donner la forme de grille_parent")
    assert str(b["panels"]) in t, "le nombre de panels mesures doit figurer"
    assert "fenetre ouverte sur une page" in t, (
        "dire ce qu'est un panel -- c'est ce qui explique la suite")
    return "%d grilles, %d panels, mecanisme systematique" % (
        b["grilles_exploitables"], b["panels"])


@cas("8. L'unite de ligne est mesuree, pas supposee")
def cas8():
    t = nu(plat(PAGE_GRILLE))
    u = releve()["grille_et_panels"]["unite_de_ligne"]
    assert "mediane 8,00" in t, "donner la mediane mesuree"
    assert str(u["arrondi_a_8"]) in t, "et le nombre de panels qui donnent 8"
    assert str(u["ecart_max_1_ligne_avec_k8_pct"]) in t, "et la part a une ligne pres"
    assert "environ 8 unites" in t, "enoncer l'ordre de grandeur a retenir"
    assert "12 unites" in t, "la marge fait partie du dimensionnement"
    return "mediane 8,00 ; %d/%d panels ; %d %% a une ligne pres" % (
        u["arrondi_a_8"], releve()["grille_et_panels"]["panels"],
        u["ecart_max_1_ligne_avec_k8_pct"])


@cas("9. La formule du RETEX est declaree NON verifiee, et n'est pas prescrite")
def cas9():
    """Garde les deux sens.

    Sens 1 -- le refus doit rester ecrit AVEC son chiffre : sans lui, un lot ulterieur
    reintroduirait la regle et le lint qui va avec.
    Sens 2 -- la formule ne doit pas revenir comme prescription. Elle est citee pour etre
    refutee, donc le controle porte sur la PHRASE, pas sur le fichier.
    """
    t = nu(plat(PAGE_GRILLE))
    b = releve()["grille_et_panels"]
    assert "ne le confirme pas" in t or "NON etabli" in t or "n'est PAS etabli" in t, (
        "le refus doit etre explicite")
    assert "23 %" in t, "avec le chiffre qui le fonde"
    assert "aucun controle automatique" in t, "et la consequence : pas de lint"
    assert b.get("regle_du_retex_NON_VERIFIEE"), "le releve doit porter la meme reserve"

    reserves = ("ne le confirme pas", "ne se verifie pas", "au mieux", "plafonne",
                "n'est pas ecrite", "23 %")
    for phrase in re.split(r"(?<=[.!?])\s+", t):
        if "somme" not in phrase.lower() or "nb_lig" not in phrase.lower():
            continue
        assert any(m in phrase.lower() for m in reserves), (
            "phrase prescrivant la formule sans la refuter : %r" % phrase[:170])
    return "refus motive, %d %% au mieux, pas de lint" % 23


@cas("10. L'ecart 8 vs 14 est SIGNALE, pas corrige en douce")
def cas10():
    """La regle DHSF05 du validate utilise nb_lig * 14 ; la mesure donne 8 en contexte panel.

    Les deux ne parlent peut-etre pas de la meme chose. Toucher DHSF05 sans le verifier serait
    exactement l'erreur que ce lot reproche aux RETEX : conclure d'une observation a une cause.
    """
    b = releve()["grille_et_panels"]
    assert b.get("signale_non_traite"), "l'ecart doit etre consigne"
    assert "14" in b["signale_non_traite"] and "8" in b["signale_non_traite"], (
        "nommer les deux constantes")
    assert "NON touche" in b["signale_non_traite"] or "non touche" in b["signale_non_traite"], (
        "dire explicitement qu'on n'y touche pas")
    src = lire(os.path.join(SCRIPTS, "dhsf_modify.py"))
    assert "nb_lig * 14" in src or "* 14" in src, (
        "DHSF05 utilise toujours 14 : si ce n'est plus le cas, le signalement est perime")
    return "ecart consigne, DHSF05 intacte"


@cas("11. Aucune trace de poste, et les liens resolvent")
def cas11():
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

    casses = []
    for page in PAGES_DU_LOT:
        base = os.path.dirname(page)
        for cible in re.findall(r"\]\(([^)#]+\.(?:md|json))\)", lire(page)):
            if not os.path.isfile(os.path.normpath(os.path.join(base, cible))):
                casses.append("%s -> %s" % (os.path.basename(page), cible))
    assert not casses, "lien(s) casse(s) : %s" % casses
    return "%d pages, 3 formes interdites, liens resolus" % len(PAGES_DU_LOT)


@cas("12. Le README ne peut pas mentir sur ses comptes")
def cas12():
    """Un chiffre ecrit dans le README doit etre CALCULE sur le code, pas affirme.

    Ce cas existe parce que le README annoncait TROIS cas fonctionnels la ou il y en a
    DEUX : j'avais compte les trois invocations du cas 6 comme trois cas. Rien ne
    confrontait ce chiffre au fichier -- c'est la meme classe que les ancres trop faibles,
    vue huit fois sur ce cycle.
    """
    readme = lire(os.path.join(HERE, "README.md"))
    MOTS = {"un": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6}
    ecarts = []

    # (a) « ... (N cas) » == nombre de « def casN(» du fichier
    # Le motif s'ancrait sur une etiquette de lot interne : il la PARSAIT, donc
    # la purge des identifiants internes a casse ce cas. Il s'ancre
    # desormais sur le titre de section, qui ne bouge pas.
    annonces = dict((f, int(n)) for f, n in
                    re.findall(r"`(test_\w+\.py)`[^\n]*?\((\d+) cas\)", readme))
    assert len(annonces) >= 3, "le README n'annonce plus le compte de ses suites"
    for fichier, annonce in sorted(annonces.items()):
        reel = len(re.findall(r"\ndef cas\d+\(", lire(os.path.join(HERE, fichier))))
        if annonce != reel:
            ecarts.append("%s : README annonce %d cas, le fichier en porte %d"
                          % (fichier, annonce, reel))

    # (b) « avec **<mot> cas fonctionnels** » == nombre de cas qui EXECUTENT un script
    m = re.search(r"`(test_\w+\.py)`(?:(?!\n## ).)*?avec \*\*(\w+) cas fonctionnels\*\*",
                  readme, re.S)
    assert m, ("le README n'annonce plus de compte de cas fonctionnels -- "
               "ce controle ne doit pas passer par absence de sa cible")
    annonce = MOTS.get(m.group(2).lower())
    assert annonce, "compte de cas fonctionnels illisible : %r" % m.group(2)
    corps = re.split(r"\ndef (cas\d+)\(", lire(os.path.join(HERE, m.group(1))))
    # un appel, pas une MENTION : le litteral ci-dessous est precede d'un guillemet,
    # et ce cas se compterait lui-meme sans cette precaution.
    APPEL = re.compile(r"(?<![\"'])executer\(")
    reel = sum(1 for i in range(1, len(corps), 2) if APPEL.search(corps[i + 1]))
    if annonce != reel:
        ecarts.append("%s : README annonce %d cas fonctionnels, %d appellent le lanceur"
                      % (m.group(1), annonce, reel))

    assert not ecarts, "\n         ".join(ecarts)
    return "%d suites confrontees, %d cas fonctionnels verifies" % (len(annonces), reel)

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
