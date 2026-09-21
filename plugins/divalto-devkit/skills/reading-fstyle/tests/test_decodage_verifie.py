#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests du decodage fstyle -- #326.

Le retour terrain disait : *« decodage incomplet, mais presente comme complet »*. Les 18
styles de la famille `DATA` sortaient tous identiques alors que leurs enregistrements sont
tous differents.

Deux familles de cas :

- **fonctionnels** : ils construisent des enregistrements en memoire et les passent aux
  decodeurs. Aucun n'a besoin du fichier reel ni de la DLL -- une suite qui ne tourne que
  sur un poste equipe de Divalto ne tourne nulle part ailleurs.
- **coherence** : ce que la page de reference affirme est ce que le code fait.

Ce que ces cas gardent, et pourquoi :

- **La couleur est a un OFFSET FIXE, pas dans les tokens** (cas 1 a 3). C'est ce qui a
  ete mesure -- 142 Type 1 sur 142 -- et c'est ce qui distingue `DATA` de `DATA_10`.
- **La 4e composante n'est PAS nommee « alpha »** (cas 4). Elle vaut 0 sur les 142
  enregistrements mesures : sa semantique n'est pas etablie, et lui donner un nom serait
  une supposition presentee comme un fait.
- **La sortie DIT ce qu'elle ignore** (cas 5). C'est la demande centrale du retour
  terrain : un decodage muet sur ses trous parait complet.
- **Les slots du Type 7 sont positionnels** (cas 6 et 7) : leurs noms promettent une
  semantique que la donnee ne porte pas dans un quart des cas, et l'outil doit exposer le
  **type reel** de la cible plutot que laisser deduire du nom de la cle.

Lancer :
    py plugin/skills/reading-fstyle/tests/test_decodage_verifie.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(SKILL, "scripts")
PAGE = os.path.join(SKILL, "reference", "fstyle-types.md")
EVALS = os.path.join(SKILL, "evals.json")
sys.path.insert(0, SCRIPTS)
import read_fstyle as rf  # noqa: E402

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire(p):
    return io.open(p, encoding="utf-8").read()


def fabriquer(type_, nom, queue=b"", couleur=None):
    """Un enregistrement fstyle synthetique : type, nom cadre, queue de tokens, couleur."""
    raw = bytearray(b" " * rf.RECORD_SIZE)
    raw[rf.OFF_TYPE] = ord(type_)
    n = nom.encode(rf.ENCODING)[:rf.NOM_LEN]
    raw[rf.OFF_NOM:rf.OFF_NOM + len(n)] = n
    debut = rf.OFF_NOM + rf.NOM_LEN
    raw[debut:debut + len(queue)] = queue
    if couleur is not None:
        z = "".join("%3d" % c for c in couleur).encode(rf.ENCODING)
        raw[rf.OFF_COULEUR_T1:rf.OFF_COULEUR_T1 + len(z)] = z
    return bytes(raw)


QUEUE_POLICE = b"8 0 0 0 400000 0 3 2 1 34Tahoma"


# --------------------------------------------------------------------- les cas

@cas("1. Deux polices identiques sur taille/poids/famille se distinguent par la couleur")
def cas1():
    noir = rf.decode_record(fabriquer("1", "DATA", QUEUE_POLICE, (0, 0, 0, 0)))
    rouge = rf.decode_record(fabriquer("1", "DATA_10", QUEUE_POLICE, (255, 0, 0, 0)))
    for d in (noir, rouge):
        assert (d["taille"], d["poids"], d["famille"]) == ("8", "400000", "Tahoma"), \
            "le decodage historique a change : %s" % d
    assert noir["couleur_texte"] != rouge["couleur_texte"], \
        "les deux styles restent indistinguables -- c'est le defaut d'origine"
    assert rouge["couleur_texte"] == {"r": 255, "g": 0, "b": 0}, \
        "couleur mal decodee : %s" % rouge["couleur_texte"]
    return "noir vs rouge, distingues"


@cas("2. La couleur vient d'un OFFSET FIXE, pas des tokens")
def cas2():
    # Meme queue de tokens, couleurs differentes -> le decodage doit differer.
    a = rf.decode_record(fabriquer("1", "A", QUEUE_POLICE, (128, 128, 128, 0)))
    b = rf.decode_record(fabriquer("1", "B", QUEUE_POLICE, (255, 255, 255, 0)))
    assert a["couleur_texte"] == {"r": 128, "g": 128, "b": 128}, a["couleur_texte"]
    assert b["couleur_texte"] == {"r": 255, "g": 255, "b": 255}, b["couleur_texte"]
    src = lire(os.path.join(SCRIPTS, "read_fstyle.py"))
    assert "OFF_COULEUR_T1" in src, "l'offset n'est plus une constante nommee"
    assert re.search(r"OFF_COULEUR_T1\s*=\s*\d+", src), "l'offset n'est plus defini"
    return "offset nomme, deux gris/blanc distingues"


@cas("3. Une zone qui n'a pas le format ne produit PAS une fausse couleur")
def cas3():
    raw = bytearray(fabriquer("1", "ABIME", QUEUE_POLICE, (0, 0, 0, 0)))
    raw[rf.OFF_COULEUR_T1:rf.OFF_COULEUR_T1 + 3] = b"xyz"
    d = rf.decode_record(bytes(raw))
    assert "couleur_texte" not in d, \
        "une zone illisible a produit une couleur : %s" % d.get("couleur_texte")
    assert "couleur_texte" in (d.get("attributs_non_decodes") or []), \
        "la couleur illisible n'est pas declaree non decodee : %s" % d
    return "refus de deviner, et refus declare"


@cas("4. La 4e composante n'est jamais nommee « alpha »")
def cas4():
    d = rf.decode_record(fabriquer("1", "X", QUEUE_POLICE, (1, 2, 3, 7)))
    assert d.get("couleur_texte_composante_4") == 7, \
        "la 4e composante n'est pas exposee : %s" % d
    assert "a" not in d and "alpha" not in json.dumps(d).lower(), \
        "la 4e composante est nommee alpha : semantique NON etablie, c'est une supposition"
    src = lire(os.path.join(SCRIPTS, "read_fstyle.py"))
    i = src.index("OFF_COULEUR_T1")
    assert "semantique" in src[i - 900:i + 3000].lower(), \
        "le code n'explique plus pourquoi la 4e composante reste anonyme"
    return "exposee, non nommee"


@cas("5. La sortie DIT ce qu'elle ignore")
def cas5():
    d = rf.decode_record(fabriquer("1", "X", QUEUE_POLICE, (0, 0, 0, 0)))
    manquants = d.get("attributs_non_decodes")
    assert manquants, "la sortie ne declare rien comme non decode -- elle parait complete"
    assert "drapeaux_apres_famille" in manquants, \
        "le champ de drapeaux, qui distingue les collisions restantes, n'est pas declare"
    return "%d attributs declares non decodes" % len(manquants)


@cas("6. Type 7 : le type REEL de chaque cible est expose")
def cas6():
    by_nom = {
        "P": fabriquer("1", "P", QUEUE_POLICE, (0, 0, 0, 0)),
        "C": fabriquer("6", "C", b"SANS"),
        "K": fabriquer("2", "K", b"255  0  00"),
        "S": fabriquer("7", "S", b"P C K"),
    }
    d = rf.annoter_refs_type7(rf.decode_record(by_nom["S"]), by_nom)
    assert d["refs_types_reels"] == {"police_ref": "1", "cadre_ref": "6", "couleur_ref": "2"}, \
        "types reels mal resolus : %s" % d["refs_types_reels"]
    assert "refs_hors_type_attendu" not in d, \
        "un cas nominal est signale comme un ecart : %s" % d.get("refs_hors_type_attendu")
    return "trois slots resolus, aucun ecart annonce a tort"


@cas("7. Type 7 : un slot qui ne vise pas son type attendu est DIT")
def cas7():
    by_nom = {
        "P": fabriquer("1", "P", QUEUE_POLICE, (0, 0, 0, 0)),
        "C": fabriquer("6", "C", b"SANS"),
        # le slot couleur vise une POLICE -- le cas reel de ENTETE_COLONNE_T
        "S": fabriquer("7", "S", b"P C P"),
    }
    d = rf.annoter_refs_type7(rf.decode_record(by_nom["S"]), by_nom)
    ecarts = d.get("refs_hors_type_attendu") or []
    assert ecarts, "un slot hors type attendu passe en silence"
    assert any("couleur_ref" in e and "Type 1" in e for e in ecarts), \
        "l'ecart ne nomme ni le slot ni le type reel : %s" % ecarts
    assert d["couleur_ref"] == "P", "la reference brute a ete alteree"
    return "ecart nomme, reference brute preservee"


@cas("8. La page de reference porte les mesures, pas des affirmations nues")
def cas8():
    p = lire(PAGE)
    for attendu in ("142 Type 1 sur 142", "235 / 235", "Aucune reference n'est pendante",
                    "attributs_non_decodes"):
        assert attendu in p, "la page ne porte plus : %r" % attendu
    # Le tableau avant/apres : les deux colonnes doivent rester, sinon le gain n'est
    # plus verifiable et l'incompletude restante disparait du discours.
    # Cibler LA LIGNE DU TABLEAU, pas n'importe quelle ligne qui parle de fstylewpf :
    # la phrase de mesure contient elle aussi « fstylewpf » et « 142 ».
    ligne = [l for l in p.split("\n") if l.startswith("| `fstylewpf`")]
    assert ligne, "la ligne du tableau avant/apres des collisions a disparu"
    assert "64" in ligne[0] and "21" in ligne[0], \
        "l'etat AVANT ou l'etat APRES a ete efface : %s" % ligne[0]
    return "mesures presentes, avant/apres conserve"


@cas("9. Les evals couvrent la couleur et le piege du Type 7")
def cas9():
    d = json.load(io.open(EVALS, encoding="utf-8"))
    brut = json.dumps(d, ensure_ascii=False)
    assert "couleur_texte" in brut, "aucune eval sur la couleur du texte"
    assert "refs_types_reels" in brut or "refs_hors_type_attendu" in brut, \
        "aucune eval sur le type reel des references de Type 7"
    assert "alpha" in brut.lower(), \
        "aucune eval ne rappelle que la 4e composante n'est pas de l'alpha"
    return "les deux sujets sont couverts"


@cas("10. Aucune trace de poste dans les fichiers du skill")
def cas10():
    # Detecter LA CHOSE, pas sa forme. « Tout chemin absolu » est un mauvais critere : il
    # tombe sur `K:\` cite en exemple dans un commentaire, et sur le placeholder
    # `C:\autre\chemin\` d'une ligne d'usage -- deux MENTIONS, dont l'une explique un
    # correctif. Ce qu'on veut interdire, c'est le poste de l'editeur : on cherche donc
    # ses marqueurs reels.
    # Pas de motif UNC ici : `\\divalto\\` est l'ECHAPPEMENT Python d'un chemin dans une
    # chaine d'aide, pas un partage reseau. Une regle qui tombe sur l'echappement d'un
    # langage ne mesure pas ce qu'elle croit.
    POSTE = (r"Developpements[ _]Harmony", r"DAN-lourd", r"C:\\+Users\\+[A-Za-z]")
    for f in (PAGE, os.path.join(SCRIPTS, "read_fstyle.py"), os.path.join(SKILL, "SKILL.md")):
        texte = lire(f)
        for motif in POSTE:
            trouve = re.search(motif, texte)
            assert not trouve, "%s : trace de poste -- %r" % (os.path.basename(f),
                                                              trouve.group(0))
    return "seuls des chemins sous la racine produit"


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
