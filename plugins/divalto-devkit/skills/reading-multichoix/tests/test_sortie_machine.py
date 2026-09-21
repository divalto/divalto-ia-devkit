#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables du contrat de sortie de `read_multichoix.py` (RETEX #170).

**7 des 9 cas tournent partout, sans DLL et sans `.dhfi`.** Les fonctions de decodage du
script sont **pures** : elles travaillent sur des enregistrements de 420 octets, pas sur un
fichier. On les alimente donc avec des enregistrements **fabriques** aux offsets documentes,
exactement comme les autres suites du plugin fabriquent leurs dictionnaires en temporaire.

Seuls **2 cas** exigent un vrai fichier, parce qu'ils mesurent le **processus** et non la
logique : l'encodage de la sortie **redirigee** et les **codes retour**. Ceux-la se
declarent **non applicables** -- jamais « reussis » -- quand la DLL ou le fichier manquent.
Pour les activer, pointer `MULTICHOIX_TEST_FILE` sur une **COPIE** d'un `XXfdmc.dhfi`.

> Etat initial de cette suite : 5 cas sur 8 ne s'executaient **jamais** par defaut. Elle
> garantissait que la doc *dit* la bonne chose, pas que le code *fait* la bonne chose.

Ce que la suite verrouille :

1. **La forme de la sortie.** L'issue #170 rapportait `--all-details` rendant une **liste
   de chaines** au lieu d'objets (`AttributeError: 'str' object has no attribute 'get'`).
   **Ce defaut n'est plus reproductible** -- ce qui manquait etait un test, pas un
   correctif. Le cas 6 verrouille en plus la confusion d'origine : `--list` et
   `--all-details` n'ont **pas** la meme forme.
2. **L'encodage.** La sortie n'etait pas en UTF-8 : redirigee, elle sortait en cp1252
   (**842 octets `0xE9`** sur un dump du dictionnaire standard). Le script frere
   `read_isam.py` forcait deja son encodage ; celui-ci non.
3. **Les codes retour**, mesures **sans pipe** -- `$?` derriere un pipe rapporte le code du
   dernier element du pipe, ce qui avait fait croire a un defaut inexistant.

Lancer :
    py .claude/skills/reading-multichoix/tests/run_all.py
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
SCRIPT = os.path.join(SKILL, "scripts", "read_multichoix.py")
DLL = os.path.join(r"C:\divalto\sys", "DhxIsam64.dll")
FICHIER = os.environ.get("MULTICHOIX_TEST_FILE")

# Import du module SANS charger la DLL : elle n'est ouverte que par read_all_records().
_s = importlib.util.spec_from_file_location("_rm", SCRIPT)
M = importlib.util.module_from_spec(_s)
_s.loader.exec_module(M)

CAS = []
NON_APPLICABLES = {}


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


# --------------------------------------------------------------------------
# Fabrication d'enregistrements 420 octets aux offsets documentes
# --------------------------------------------------------------------------

def enregistrement(ce, nc, mc_type, choix="", valeur="",
                   enreg="", donnee="", prefixe="", ideb="", ifin=""):
    """Un enregistrement multichoix brut, initialise a l'espace comme le vrai fichier."""
    b = bytearray(b" " * M.RECORD_SIZE)

    def poser(offset, valeur_txt, taille):
        v = valeur_txt.encode(M.ENCODING)[:taille]
        b[offset:offset + len(v)] = v

    poser(M.OFF_CE, ce, 1)
    poser(M.OFF_NC, nc, 16)
    poser(M.OFF_TYPE, mc_type, 1)
    if mc_type == "3":
        poser(M.OFF_ENREG, enreg, 32)
        poser(M.OFF_DONNEE, donnee, 32)
        poser(M.OFF_PREFIXE, prefixe, 32)
        poser(M.OFF_IDEB, ideb, 4)
        poser(M.OFF_IFIN, ifin, 4)
    else:
        poser(M.OFF_CHOIX, choix, 104)
        poser(M.OFF_VALEUR, valeur, 80)
    return bytes(b)


def jeu_fabrique():
    """Trois multichoix couvrant les 3 Types, avec des accents EN DUR.

    Les accents sont deliberes : ils reproduisent la donnee qui a casse le consommateur
    du partenaire. Et le Type 4 est present ici alors qu'un fichier reel donne peut ne
    pas en contenir -- le jeu fabrique couvre donc des cas que la mesure ne couvre pas.
    """
    from collections import OrderedDict
    return OrderedDict([
        ("LISTEFIXE", [
            enregistrement("1", "LISTEFIXE", "1", choix="Créé à Strasbourg"),
            enregistrement("2", "LISTEFIXE", "1", choix="Dépôt régional", valeur="D"),
            enregistrement("2", "LISTEFIXE", "1", choix="Été / hiver", valeur="E"),
        ]),
        ("AXENO", [
            enregistrement("1", "AXENO", "3", enreg="ca", donnee="axelibtb",
                           prefixe="ca", ideb="1", ifin="4"),
        ]),
        ("IDEXTERNE", [
            enregistrement("1", "IDEXTERNE", "4", choix="", valeur="IdFicJoint"),
        ]),
    ])


def executer(*args):
    """Lance le script en REDIRECTION (jamais en pipe) et rend (code, octets bruts)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as fh:
        sortie = fh.name
    try:
        with open(sortie, "wb") as out:
            r = subprocess.run([sys.executable, SCRIPT, "--file", FICHIER] + list(args),
                               stdout=out, stderr=subprocess.DEVNULL)
        with open(sortie, "rb") as fh:
            return r.returncode, fh.read()
    finally:
        os.unlink(sortie)


def besoin_fichier(num):
    """Enregistre et retourne la raison de non-applicabilite, sinon None."""
    raison = None
    if not FICHIER:
        raison = "MULTICHOIX_TEST_FILE non defini (pointer une COPIE d'un XXfdmc.dhfi)"
    elif not os.path.isfile(FICHIER):
        raison = "fichier introuvable : %s" % FICHIER
    elif not os.path.isfile(DLL):
        raison = "DhxIsam64.dll absente de ce poste"
    if raison:
        NON_APPLICABLES[num] = raison
    return raison


# --------------------------------------------------------------------------
# 1-3 : contrat code et documentation
# --------------------------------------------------------------------------

@cas("1. Le script force sa sortie en UTF-8, AVANT toute ecriture, comme son frere")
def cas1():
    src = lire(SCRIPT)
    i = src.find('reconfigure(encoding="utf-8")')
    assert i > 0, ("sans cela la sortie redirigee sort en cp1252 et casse un consommateur "
                   "qui lit en UTF-8")
    j = src.find("json.dump")
    assert j > 0 and i < j, (
        "le reconfigure doit precéder la premiere ecriture, sinon il arrive trop tard")
    frere = os.path.abspath(os.path.join(SKILL, "..", "reading-isam-files",
                                         "scripts", "read_isam.py"))
    assert "reconfigure" in lire(frere), (
        "le script frere le faisait deja -- si ce n'est plus vrai, verifier les deux")
    return "present, et place avant la sortie"


@cas("2. La doc documente la FORME de --all-details, pas seulement son contenu")
def cas2():
    t = lire(os.path.join(SKILL, "SKILL.md"))
    assert "### `--all-details`" in t, (
        "la section Format de sortie documentait --list, --detail et --stats mais PAS "
        "--all-details : c'est le trou qui a laisse la derive passer")
    bloc = t[t.index("### `--all-details`"):][:2500]
    assert "dictionnaire indexe par Nc" in bloc, "la forme doit etre nommee explicitement"
    assert "pas un compteur" in bloc.lower(), (
        "`entries` change de nature entre --list (compteur) et --all-details (liste)")
    return "la forme est dite, et l'ecart avec --list est signale"


@cas("3. La doc annonce le contrat UTF-8, en tete du format de sortie")
def cas3():
    t = lire(os.path.join(SKILL, "SKILL.md"))
    i = t.index("## Format de sortie")
    assert "UTF-8" in t[i:i + 900], "le contrat d'encodage doit figurer en tete de section"


# --------------------------------------------------------------------------
# 4-7 : comportement, sur enregistrements FABRIQUES (sans DLL ni fichier)
# --------------------------------------------------------------------------

@cas("4. --all-details : `multichoix` est un DICT, `entries` une LISTE d'objets")
def cas4():
    res = M.cmd_all_details(jeu_fabrique())
    m = res["multichoix"]
    assert isinstance(m, dict), (
        "c'est exactement le defaut de #170 : attendu un dict, obtenu %s" % type(m).__name__)
    assert res["total_nc"] == len(m) == 3, res["total_nc"]
    for nc, mc in m.items():
        assert isinstance(mc, dict), "%s : %r n'est pas un objet" % (nc, mc)
        assert mc.get("nc") == nc, mc
        assert "type" in mc, "%s : `type` absent" % nc
        assert isinstance(mc.get("entries"), list), (
            "%s : `entries` doit etre une LISTE decodee, pas un compteur -- %r"
            % (nc, mc.get("entries")))
    assert len(m["LISTEFIXE"]["entries"]) == 3, m["LISTEFIXE"]
    return "3 multichoix fabriques, forme conforme a la doc, sans DLL"


@cas("5. --all-details : `lookup` present pour le Type 3, ABSENT pour les Types 1 et 4")
def cas5():
    m = M.cmd_all_details(jeu_fabrique())["multichoix"]
    assert m["AXENO"]["type"] == "3", m["AXENO"]
    lk = m["AXENO"].get("lookup")
    assert lk, "Type 3 sans `lookup`"
    assert lk == {"enreg": "ca", "donnee": "axelibtb", "prefixe": "ca",
                  "ideb": 1, "ifin": 4}, lk
    for nc in ("LISTEFIXE", "IDEXTERNE"):
        assert "lookup" not in m[nc], "%s (Type %s) ne doit pas porter de `lookup`" % (
            nc, m[nc]["type"])
    return "ideb/ifin convertis en entiers, lookup absent hors Type 3"


@cas("6. --list et --all-details n'ont PAS la meme forme -- c'est la confusion d'origine")
def cas6():
    jeu = jeu_fabrique()
    liste = M.cmd_list(jeu)["multichoix"]
    detail = M.cmd_all_details(jeu)["multichoix"]
    assert isinstance(liste, list), "--list doit rendre une LISTE : %s" % type(liste).__name__
    assert isinstance(detail, dict), "--all-details doit rendre un DICT"
    e = [x for x in liste if x["nc"] == "LISTEFIXE"][0]["entries"]
    assert isinstance(e, int) and e == 3, (
        "--list : `entries` doit etre un COMPTEUR, obtenu %r" % e)
    assert isinstance(detail["LISTEFIXE"]["entries"], list), (
        "--all-details : `entries` doit etre une LISTE")
    return "compteur d'un cote, liste de l'autre : la doc le dit maintenant"


@cas("7. --detail <NC> rend le meme contenu que l'entree correspondante de --all-details")
def cas7():
    jeu = jeu_fabrique()
    tout = M.cmd_all_details(jeu)["multichoix"]
    for nc in jeu:
        det = M.cmd_detail(jeu, nc)
        assert det.get("found") is True, nc
        assert det["type"] == tout[nc]["type"], nc
        assert det["entries"] == tout[nc]["entries"], (
            "%s : --detail et --all-details divergent" % nc)
        assert det.get("lookup") == tout[nc].get("lookup"), nc
    absent = M.cmd_detail(jeu, "NC_QUI_NEXISTE_PAS")
    assert absent.get("found") is False, absent
    return "boucler --detail par Nc est inutile (N lectures ISAM pour rien)"


# --------------------------------------------------------------------------
# 8-9 : mesures sur le PROCESSUS -- exigent un vrai fichier
# --------------------------------------------------------------------------

@cas("8. [mesure] Sortie REDIRIGEE decodable en UTF-8, zero octet cp1252")
def cas8():
    if besoin_fichier(8):
        return None
    code, brut = executer("--all-details")
    assert code == 0, "code retour %d" % code
    try:
        brut.decode("utf-8")
    except UnicodeDecodeError as e:
        raise AssertionError("sortie non decodable en UTF-8 : %s" % e)
    nb = brut.count(bytes([0xE9]))
    assert nb == 0, "%d octet(s) 0xE9 brut(s) : la sortie est encore en cp1252" % nb
    assert brut.count(b"\xc3\xa9") > 0, (
        "aucune sequence UTF-8 accentuee : le fichier de mesure ne discrimine pas")
    return "%d Ko lisibles, %d sequences UTF-8 accentuees" % (
        len(brut) // 1024, brut.count(b"\xc3\xa9"))


@cas("9. [mesure] Codes retour figes, mesures SANS pipe")
def cas9():
    if besoin_fichier(9):
        return None
    for args, attendu in ((("--all-details",), 0), (("--list",), 0),
                          (("--detail", "NC_QUI_NEXISTE_PAS"), 1),
                          (("--resolve", "ACOMPTE"), 1)):
        code, _b = executer(*args)
        assert code == attendu, "%s -> code %d, attendu %d" % (args[0], code, attendu)
    return "--resolve sort bien en 1 : un releve pollue par un pipe l'avait dit a 0"


# --------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    echecs = []
    for titre, fn in CAS:
        num = int(titre.split(".")[0])
        try:
            note = fn()
            if num in NON_APPLICABLES:
                print("  N/A  %s" % titre)
                print("         -> non applicable : %s" % NON_APPLICABLES[num])
                continue
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
    na = len(NON_APPLICABLES)
    if echecs:
        print("BILAN : %d/%d cas en ECHEC (%d non applicable(s))" % (len(echecs), len(CAS), na))
        for t in echecs:
            print("  - " + t)
        return 1
    print("BILAN : %d/%d cas OK, %d non applicable(s)" % (len(CAS) - na, len(CAS), na))
    if na:
        print("  (definir MULTICHOIX_TEST_FILE sur une COPIE d'un XXfdmc.dhfi pour les activer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
