#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de coherence de la grammaire .dhsf.

RETEX #254 #259 #260 #283.

Deux familles de cas :

- **doc <-> releve** : les pages citent des chiffres mesures sur le corpus des masques du
  standard ; `reference/mesures-corpus.json` les porte, date et qualifie. Un test hors ligne
  verifie que les deux concordent. Une page qui derive des mesures qui la fondent est pire
  qu'une page sans chiffres.
- **fonctionnels** : le controle de chaine des pages est execute sur un masque reellement
  casse, fabrique depuis le template livre avec le skill.

Ce que ces cas gardent, et pourquoi :

- **Deux des trois RETEX se trompaient.** #254 concluait que `esp_si_zero` n'est pas un
  attribut valide ; il est employe 33 576 fois. #260 donnait `RTF_NOTE` pour LE style du
  `rich_edit` ; c'est le 4e. Les cas 4 et 3 gardent la mesure **et** la refutation, de sorte
  que la conclusion fausse ne puisse pas revenir sous forme de prescription.
- **Une regle de lint demandee a ete mesuree puis ECARTEE** (#283, `col_depl`). Le cas 6
  garde le chiffre qui la refute : sans lui, un lot ulterieur la reintroduirait.
- **Le skill se contredisait lui-meme** : trois composants qu'il DOCUMENTE etaient absents de
  la liste blanche de son propre parser. Le cas 8 en fait un invariant -- toute page
  `composant-*.md` doit avoir son type reconnu.

Style : ce fichier utilise le decorateur `@cas`, comme les suites des autres skills du
plugin. `test_surcharge_presomption.py` emploie une forme anterieure ; l'aligner est trace
note pour plus tard plutot que fait ici, hors perimetre.

Lancer :
    py .claude/skills/manipulating-dhsf-screens/tests/run_all.py
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
REF = os.path.join(SKILL, "reference")
SCRIPTS = os.path.join(SKILL, "scripts")
RELEVE = os.path.join(REF, "mesures-corpus.json")
PAGE_STRUCT = os.path.join(REF, "dhsf-structure.md")
PAGE_RICH = os.path.join(REF, "composant-rich-edit.md")
SKILL_MD = os.path.join(SKILL, "SKILL.md")
TEMPLATE_ZOOM = os.path.join(SKILL, "templates", "template_zoom_sql.dhsf")

# Pages que CE lot ecrit -- perimetre du controle structurel (cas 11).
PAGES_DU_LOT = (PAGE_STRUCT, PAGE_RICH)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


def nu(texte):
    """Texte depouille du balisage d'emphase Markdown (jamais `_` : il est dans les noms)."""
    return re.sub(r"[*`]", "", texte)


def plat(p):
    """Texte aplati sur une ligne : la prose est enveloppee, chercher une chaine casserait."""
    return " ".join(re.sub(r"\n[ \t]*>", "\n", lire(p)).split())


def releve():
    return json.loads(lire(RELEVE))


def milliers(n):
    return "{:,}".format(n).replace(",", " ")


# --------------------------------------------------------------------------

@cas("1. Le releve porte sa source, sa date, et les six blocs du lot")
def cas1():
    r = releve()
    for cle in ("source", "version_erp", "date_mesure", "corpus"):
        assert r.get(cle), "champ '%s' manquant : un releve sans provenance ne vaut rien" % cle
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["date_mesure"]), r["date_mesure"]
    attendus = ("esp_si_zero", "col_depl", "rich_edit", "widgets_de_page",
                "chaine_des_pages", "param_case")
    manquants = [b for b in attendus if b not in r]
    assert not manquants, "bloc(s) absent(s) : %s" % manquants
    assert "chemin" in r["corpus"].get("_note", "").lower(), (
        "le releve doit dire pourquoi le chemin du corpus n'y figure pas")
    return "%d blocs, mesure du %s sur %d masques" % (
        len(attendus), r["date_mesure"], r["corpus"]["masques_dhsf"])


@cas("2. composant-rich-edit.md existe, est atteignable, et concorde avec le releve")
def cas2():
    assert os.path.isfile(PAGE_RICH), "page absente"
    t = nu(plat(PAGE_RICH))
    b = releve()["rich_edit"]
    assert "composant-rich-edit.md" in lire(SKILL_MD), (
        "une page que le SKILL.md ne cite pas n'existe pas pour le lecteur")
    assert "composant-rich-edit.md" in lire(PAGE_STRUCT), (
        "dhsf-structure.md doit la citer comme 7e type de composant")
    assert "7e type de composant" in t, "annoncer sa place dans la famille"
    for cle in ("blocs", "masques_porteurs"):
        assert milliers(b[cle]) in t, "chiffre %s absent de la page (%s)" % (cle, b[cle])
    for k, n in b["param_rich_edit_cles"].items():
        assert k in t, "cle %s de [param_rich_edit] absente de la page" % k
    assert "largeur" in t and str(b["param_rich_edit_cles"]["largeur"]) in t, (
        "largeur est systematique : la page doit porter le compte")
    return "%d blocs / %d masques, %d cles" % (
        b["blocs"], b["masques_porteurs"], len(b["param_rich_edit_cles"]))


@cas("3. RTF_NOTE est remis a sa place -- 4e style, pas LE style")
def cas3():
    """#260 generalisait depuis le seul masque qu'il avait ouvert."""
    t = nu(plat(PAGE_RICH))
    w = releve()["rich_edit"]["wstyle_observes"]
    ordre = sorted(w.items(), key=lambda kv: -kv[1])
    assert ordre[3][0] == "RTF_NOTE", (
        "le releve ne place plus RTF_NOTE en 4e position : %s" % ordre[:5])
    for style, n in ordre[:4]:
        assert style in t, "style %s absent de la page" % style
        assert str(n) in t, "frequence de %s absente de la page (%d)" % (style, n)
    assert "quatrieme" in t.lower(), "dire explicitement son rang"
    for dominant, _ in ordre[:3]:
        assert dominant in t, "le style dominant %s doit etre cite" % dominant
    return "7 styles, RTF_NOTE en 4e (%d occurrences)" % w["RTF_NOTE"]


@cas("4. esp_si_zero : regle de PLACEMENT, et la conclusion fausse du RETEX est refutee")
def cas4():
    """Le cas garde les deux sens.

    Sens 1 -- la regle juste (placement dans [param_saisie]) doit etre ecrite.
    Sens 2 -- la conclusion du RETEX (« attribut invalide, ne pas l'inclure ») ne doit pas
    revenir comme prescription. Elle est CITEE pour etre refutee : le controle porte donc
    sur la phrase, pas sur le fichier -- interdire la chaine partout ferait tomber le cas
    sur la refutation elle-meme.
    """
    t = nu(plat(PAGE_STRUCT))
    b = releve()["esp_si_zero"]
    assert "param_saisie" in t, "nommer la sous-section qui l'accueille"
    assert b["occurrences_hors_param_saisie"] == 0, "le releve doit porter le zero"
    assert "0 occurrence ailleurs" in t, "dire qu'il n'apparait nulle part ailleurs"
    assert "description" in t, "nommer le placement fautif du cas vecu"
    for cle in ("occurrences", "masques_porteurs", "avec_saisie_non"):
        assert milliers(b[cle]) in t, "chiffre %s absent (%s)" % (cle, b[cle])
    assert "%d %%" % b["part_saisie_non_pct"] in t or "%d%%" % b["part_saisie_non_pct"] in t, (
        "la part de saisie=non doit figurer : c'est elle qui refute l'exception supposee")

    reserves = ("correction", "inverse", "la mesure dit", "refut", "avait conclu",
                "reviendrait a retirer")
    for phrase in re.split(r"(?<=[.!?])\s+", t):
        if "pas un attribut valide" not in phrase.lower():
            continue
        assert any(m in phrase.lower() for m in reserves), (
            "phrase prescrivant l'invalidite sans la refuter : %r" % phrase[:170])
    return "regle de placement, %s occurrences, %d%% en saisie=non" % (
        milliers(b["occurrences"]), b["part_saisie_non_pct"])


@cas("5. param_case : deux composants, systematique, chiffres concordants")
def cas5():
    t = nu(plat(PAGE_STRUCT))
    b = releve()["param_case"]
    assert b["occurrences_ailleurs"] == 0, "le releve doit porter le zero"
    # Le total et le nombre de masques etaient cites par la page sans etre confrontes au
    # releve : le harnais de mutation l'a montre en changeant 7 729 sans faire tomber le cas.
    for cle in ("occurrences", "masques_porteurs"):
        assert milliers(b[cle]) in t, "chiffre %s absent de la page (%s)" % (cle, b[cle])
    for parent, n in b["parents_observes"].items():
        assert parent in t, "parent %s absent de la page" % parent
        assert milliers(n) in t, "compte de %s absent de la page (%d)" % (parent, n)
    assert "systematique" in t, (
        "un pour un : le bloc est obligatoire, pas seulement autorise -- le dire")
    assert "saisie=non" in t, "dire ce que fait un [champ] saisie=non"
    return "%s occurrences, 2 parents, 0 ailleurs" % milliers(b["occurrences"])


@cas("6. col_depl : le piege est ecrit, et la regle de lint est ECARTEE avec son chiffre")
def cas6():
    """#283 demandait un avertissement quand col_depl manque.

    Mesuree puis ecartee : 40 % des [param_tableau] du standard n'en ont pas. Sans le
    chiffre dans la page, un lot ulterieur reintroduirait la regle.
    """
    t = nu(plat(PAGE_STRUCT))
    b = releve()["col_depl"]
    assert "ni les fleches du clavier ni le clic" in t, (
        "le symptome doit etre decrit : c'est ce qui rend le piege reconnaissable")
    assert "Aucune erreur de compilation" in t, "dire que rien ne le signale"
    for cle in ("occurrences", "masques_porteurs", "param_tableau_sans_col_depl",
                "param_tableau_total"):
        assert milliers(b[cle]) in t, "chiffre %s absent (%s)" % (cle, b[cle])
    assert "n'emet pas" in t, "dire que ce skill N'EMET PAS l'avertissement demande"
    assert "faux positifs" in t, "et pourquoi"
    assert b.get("non_verifie"), "la semantique du nombre n'est pas etablie : le declarer"
    assert "n'est pas etabli" in t, "et l'ecrire dans la page"
    return "%s%% des blocs sans col_depl -> regle ecartee" % b["part_sans_col_depl_pct"]


@cas("7. La chaine des pages : la regle, le piege silencieux, l'indissociabilite")
def cas7():
    t = nu(plat(PAGE_STRUCT))
    assert "n'a PAS de ligne suiv=" in t, (
        "l'omission est la fin de chaine : il n'y a pas de valeur « aucune »")
    assert "0 erreur" in t, "dire que le lien orphelin COMPILE"
    assert "OUVERTURE" in t, "et que ca casse a l'ouverture, pas avant"
    assert "page N du masque inexistante" in t, "donner le message tel qu'il sort"
    assert "indissociables" in t, (
        "page 12 et ses deux liens partent ensemble -- sinon on recree le defaut")
    assert "socle audit" in t, "dire QUAND la page 12 doit disparaitre"
    return "regle, piege silencieux et indissociabilite ecrits"


@cas("8. INVARIANT : tout composant documente par le skill est reconnu par son parser")
def cas8():
    """Le controle qui aurait attrape la contradiction interne.

    Trois composants -- cadre, bitmap_constante, bitmap_variable -- avaient leur page
    `composant-*.md` depuis toujours, et etaient absents de WIDGET_TYPES. Un masque qui en
    contient etait parse sans les voir. Ce cas empeche que ca se reproduise pour un
    septieme composant.
    """
    src = lire(os.path.join(SCRIPTS, "dhsf_parser.py"))
    m = re.search(r"WIDGET_TYPES\s*=\s*\{(.*?)\n\}", src, re.S)
    assert m, "WIDGET_TYPES introuvable dans le parser"
    connus = set(re.findall(r'"([a-z_0-9]+)"', m.group(1)))

    documentes = set()
    for p in glob.glob(os.path.join(REF, "composant-*.md")):
        nom = os.path.basename(p)[len("composant-"):-len(".md")].replace("-", "_")
        documentes.add(nom)
    manquants = sorted(documentes - connus)
    assert not manquants, (
        "composant(s) documente(s) par une page mais absent(s) de WIDGET_TYPES : %s -- "
        "un masque qui en contient est parse sans les voir" % manquants)

    b = releve()["widgets_de_page"]
    absents = [w for w in b["ajoutes_au_parser"] if w not in connus]
    assert not absents, "widget(s) du releve absent(s) du parser : %s" % absents
    assert b.get("non_ajoutes_volontairement"), (
        "ce qui n'a PAS ete ajoute doit etre declare, sinon on croit la liste complete")
    return "%d composants documentes, tous reconnus ; %d widgets ajoutes" % (
        len(documentes), len(b["ajoutes_au_parser"]))


@cas("9. FONCTIONNEL : validate attrape un suiv= orphelin sur un masque reellement casse")
def cas9():
    """Rejoue le cas #259 : la page 12 supprimee, le suiv=12 laisse en place."""
    assert os.path.isfile(TEMPLATE_ZOOM), "template absent : %s" % TEMPLATE_ZOOM
    brut = io.open(TEMPLATE_ZOOM, encoding="iso-8859-1").read()
    i = brut.index("numero=12")
    coupe = brut[:brut.rindex("[page]", 0, i)]
    d = tempfile.mkdtemp(prefix="dhsf_")
    casse = os.path.join(d, "casse.dhsf")
    io.open(casse, "w", encoding="iso-8859-1").write(coupe)

    def valider(chemin):
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "dhsf_modify.py"),
             "--path", chemin, "--action", "validate", "--params", "{}"],
            capture_output=True)
        return json.loads(r.stdout.decode("utf-8", "replace"))

    sain = valider(TEMPLATE_ZOOM)
    chaine_sain = [v for v in sain.get("violations", []) if v["rule"] in ("DHSF06", "DHSF07")]
    assert not chaine_sain, (
        "faux positif : le template INTACT ne doit produire aucune violation de chaine (%s)"
        % chaine_sain[:1])

    rapport = valider(casse)
    c1 = [v for v in rapport.get("violations", []) if v["rule"] == "DHSF06"]
    assert c1, "le suiv= orphelin n'est PAS detecte -- le controle ne sert a rien"
    assert rapport.get("success") is False, "un lien orphelin doit invalider le masque"
    detail = c1[0]["detail"]
    assert "12" in detail and "suiv" in detail, "le message doit nommer le lien fautif"
    assert "OUVERTURE" in detail.upper(), (
        "le message doit dire QUAND ca casse -- sinon on cherche a la compilation")
    return "intact : 0 violation ; casse : DHSF06 leve avec un message actionnable"


@cas("10. Ce qui n'a PAS ete ajoute au parser est declare, pas tu")
def cas10():
    b = releve()["widgets_de_page"]["non_ajoutes_volontairement"]
    for attendu in ("aide_page", "boutons", "hierarchie_grille_wpf"):
        assert attendu in b, "non-ajout non declare : %s" % attendu
        assert len(b[attendu]) > 40, "%s : la raison doit etre ecrite, pas suggeree" % attendu
    src = lire(os.path.join(SCRIPTS, "dhsf_parser.py"))
    assert "NON ajoutes" in src, (
        "le parser doit porter la meme liste : un lecteur du code ne lit pas le releve")
    return "%d non-ajouts declares, des deux cotes" % len(b)


@cas("11. Aucune trace de poste ni d'identite dans les pages ecrites par ce lot")
def cas11():
    """Controle STRUCTUREL, pas une liste noire : ces tests sont distribues avec le skill,
    y ecrire les noms a proteger reviendrait a les publier. La mesure de ce lot a ete faite
    sur un pack reel -- c'est exactement le genre de lot ou un chemin absolu se glisse.
    """
    motifs = [
        (r"[A-Za-z]:[\\/]", "chemin absolu Windows"),
        (r"\\\\[A-Za-z0-9]", "chemin UNC"),
        (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "adresse mail"),
    ]
    trouves = []
    for page in PAGES_DU_LOT + (RELEVE,):
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
    return "%d fichiers, 3 formes interdites, liens resolus" % (len(PAGES_DU_LOT) + 1)


@cas("12. INVARIANT : la table des regles et les codes emis se recouvrent exactement")
def cas12():
    """Ce qui manquait quand `validate_page_chain()` est arrive.

    Ses deux codes etaient emis et decrits nulle part : la table de `SKILL.md` ne
    couvrait que le layout des groupbox. Personne ne pouvait le voir -- aucun cas ne
    confrontait la table a ce que le script emet.

    L'enumeration passe par `ast`, pas par un motif : c'est un motif qui a rate ces
    deux codes-la. Et elle vaut dans les deux sens, parce que les deux defauts sont
    reels : un code emis sans ligne de table est indocumente, une ligne sans emission
    est un code que le partenaire cherchera en vain dans une sortie.
    """
    import ast

    src = lire(os.path.join(SCRIPTS, "dhsf_modify.py"))
    emis = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Dict):
            for cle, val in zip(n.keys, n.values):
                if (isinstance(cle, ast.Constant) and cle.value == "rule"
                        and isinstance(val, ast.Constant)):
                    emis.add(val.value)
        # la forme `for cle, regle in (("suiv", "DHSF06"), ...)` : le code est
        # dans un tuple, jamais dans le dict -- une lecture du dict seul la rate.
        if isinstance(n, ast.Tuple) and len(n.elts) == 2 and all(
                isinstance(e, ast.Constant) and isinstance(e.value, str)
                for e in n.elts):
            if re.fullmatch(r"DHSF\d\d", n.elts[1].value):
                emis.add(n.elts[1].value)
    assert emis, "aucun code emis trouve -- le cas ne mesure rien"

    table = set(re.findall(r"^\|\s*(DHSF\d\d)\s*\|", lire(SKILL_MD), re.M))
    indocumentes = sorted(emis - table)
    morts = sorted(table - emis)
    assert not indocumentes, (
        "code(s) emis sans ligne de table -- le partenaire les lira en sortie sans "
        "pouvoir les comprendre : %s" % indocumentes)
    assert not morts, (
        "ligne(s) de table qu'aucune emission ne produit : %s" % morts)

    hors = sorted(c for c in emis if not re.fullmatch(r"DHSF\d\d", c))
    assert not hors, (
        "code(s) hors convention de prefixe (cf. un prefixe par outil emetteur) : %s"
        % hors)
    return "%d codes emis, %d lignes de table, recouvrement exact" % (
        len(emis), len(table))

@cas("13. FONCTIONNEL : la post-validation cumule les DEUX familles, comme validate")
def cas13():
    """La post-validation qui suit une MODIFICATION n executait que le layout.

    `--action validate` cumule le layout des groupbox et la chaine des pages. La
    post-validation, elle, n appelait que le premier : un partenaire qui editait un
    masque a la chaine cassee ne le voyait pas, alors que la meme commande en mode
    `validate` le lui aurait dit. Deux verdicts differents sur le meme fichier.

    Le cas verifie la SORTIE d une action modifiante, pas la fonction : c est le JSON
    que l orchestrateur lit.
    """
    assert os.path.isfile(TEMPLATE_ZOOM), "template absent : %s" % TEMPLATE_ZOOM
    brut = io.open(TEMPLATE_ZOOM, encoding="iso-8859-1", newline="").read()
    i = brut.index("numero=12")
    d = tempfile.mkdtemp(prefix="dhsf_")
    casse = os.path.join(d, "casse.dhsf")
    io.open(casse, "w", encoding="iso-8859-1", newline="").write(
        brut[:brut.rindex("[page]", 0, i)])

    params = {"page_numero": 1, "label": "Test", "vue": "FamRgltRtl",
              "champ": "RgltFam", "alias": "ZZTest"}
    r = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "dhsf_modify.py"),
         "--path", casse, "--action", "add-field", "--params",
         json.dumps(params)], capture_output=True)
    sortie = r.stdout.decode("utf-8", "replace")
    assert sortie.strip(), "aucune sortie : %s" % (
        r.stderr.decode("utf-8", "replace")[-200:])
    rapport = json.loads(sortie)
    assert rapport.get("success"), "la modification elle-meme doit reussir"
    pv = rapport.get("post_validation") or {}

    # la FORME ne change pas : les appelants lisent ces trois cles
    for cle in ("valid", "violations", "stats"):
        assert cle in pv, "post_validation a perdu la cle %r" % cle

    codes = sorted(v["rule"] for v in pv["violations"])
    assert "DHSF06" in codes, (
        "la chaine cassee n est pas remontee par la post-validation : %s" % codes)
    assert pv["stats"]["total"] == len(pv["violations"]), (
        "les stats ne comptent pas les violations qu elles accompagnent")
    return "post_validation : %s, forme intacte" % ", ".join(codes)

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
