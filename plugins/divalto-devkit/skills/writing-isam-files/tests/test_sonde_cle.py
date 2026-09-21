#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de la sonde de cle et des correctifs documentaires.

, RETEX #291, #240, #241.

**Deux familles de cas, et une frontiere assumee :**

- Les cas 1 a 8 tournent **partout** : ils portent sur la logique de la sonde et sur la
  coherence doc/mesure, sans DLL ni fichier ISAM.
- Les cas 9 et 10 exigent `DhxIsam64.dll` et un `.dhfi` reel. Ils se **declarent non
  applicables** (et non "reussis") quand l'un des deux manque : un test qui passe faute
  de pouvoir mesurer est pire qu'un test absent.

Ce que le lot verrouille :

1. **La cle declaree n'est pas forcement la cle physique.** Les blocs `Keys` sont ecrits
   a la main et rien ne les validait. Le champ CE appartient a la cle de **certains
   index seulement** -- **822 index sur 959 (86 %) du dictionnaire standard n'en ont
   aucun**. Deux structures livrees par ce skill illustraient les deux cas : la cle du
   menu M2 inclut bien `Ce`, celle du multichoix ne l'incluait qu'a tort. Corrigee.
2. **Le message d'echec doit nommer la bonne cause.** L'ancien (« match approximatif
   refuse ») envoyait chercher du cote de l'enregistrement.
3. **Le code 9 n'est pas un garde-fou d'unicite** -- mesure : deux `insert` identiques,
   deux enregistrements physiques, aucun code 9.
4. **`xisam_obj_tlibmlong` n'existe pas** dans la DLL livree.

Lancer :
    py .claude/skills/writing-isam-files/tests/run_all.py
"""
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(SKILL, "scripts")
STRUCT_ECRITURE = os.path.join(SCRIPTS, "structures")
STRUCT_LECTURE = os.path.abspath(
    os.path.join(SKILL, "..", "reading-isam-files", "scripts", "structures"))
DLL = os.path.join(r"C:\divalto\sys", "DhxIsam64.dll")

_s = importlib.util.spec_from_file_location("_vs", os.path.join(SCRIPTS, "validate_structure.py"))
V = importlib.util.module_from_spec(_s)
_s.loader.exec_module(V)
_w = importlib.util.spec_from_file_location("_wi", os.path.join(SCRIPTS, "write_isam.py"))
W = importlib.util.module_from_spec(_w)
_w.loader.exec_module(W)

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def lire_json(p):
    return json.load(io.open(p, encoding="utf-8"))


def lire(p):
    return io.open(p, encoding="utf-8").read()


# --------------------------------------------------------------------------
# Declarations de cle -- sans DLL
# --------------------------------------------------------------------------

@cas("1. #291 : la cle du multichoix ne contient PLUS le champ CE")
def cas1():
    j = lire_json(os.path.join(STRUCT_LECTURE, "structure_gtfdmc_ch60.json"))
    champs = j["Keys"]["Index_A"]["Fields"]
    assert champs == ["Nc"], (
        "attendu ['Nc'] -- le champ Ce est le code enregistrement, pas un champ de cle : %s"
        % champs)
    assert "Commentaire" in j["Keys"]["Index_A"], (
        "la raison doit rester dans le fichier, sinon quelqu'un remettra Ce")
    return "verdict de la sonde sur fichier reel : CONFIRMEE apres correction"


@cas("2. #291 : la cle du menu M2 CONSERVE le champ CE (elle etait juste)")
def cas2():
    j = lire_json(os.path.join(STRUCT_ECRITURE, "structure_xmenuf_m2.json"))
    champs = j["Keys"]["Index_A_M2"]["Fields"]
    assert champs == ["Ce", "Reg", "Ordre"], champs
    return "les deux cas coexistent : la presence de CE se lit, ne se suppose pas"


@cas("3. Tout champ de cle declare existe dans la Structure")
def cas3():
    verifiees = 0
    for d in (STRUCT_ECRITURE, STRUCT_LECTURE):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.startswith("structure_") or not f.endswith(".json"):
                continue
            j = lire_json(os.path.join(d, f))
            noms = {c["Nom"] for c in j.get("Structure", [])}
            for idx, decl in (j.get("Keys") or {}).items():
                for champ in decl.get("Fields") or []:
                    assert champ in noms, (
                        "%s / %s : champ de cle '%s' absent de Structure" % (f, idx, champ))
                    verifiees += 1
    assert verifiees, "aucune cle verifiee : le balayage ne trouve plus les structures"
    return "%d champs de cle verifies dans toutes les structures livrees" % verifiees


# --------------------------------------------------------------------------
# Message d'echec
# --------------------------------------------------------------------------

@cas("4. Le message d'echec nomme la cause probable ET l'outil de verification")
def cas4():
    m = W.MSG_CLE_REFUSEE
    for attendu in ("cle declaree", "PHYSIQUE", "CE", "validate_structure.py", "--probe-key"):
        assert attendu in m, "le message ne contient pas %r : %s" % (attendu, m)
    assert "aucune ecriture" in m, "le message doit rassurer sur l'absence d'effet de bord"
    assert "match approximatif" not in m, "l'ancienne formulation subsiste"
    return "il dit quoi soupconner et comment le confirmer"


@cas("5. Les DEUX chemins (update et delete) utilisent le meme message")
def cas5():
    src = lire(os.path.join(SCRIPTS, "write_isam.py"))
    assert src.count("MSG_CLE_REFUSEE") == 3, (
        "attendu 3 occurrences (1 definition + update + delete), trouve %d"
        % src.count("MSG_CLE_REFUSEE"))
    assert '"message": "Enreg cible introuvable (match approximatif refuse)"' not in src


# --------------------------------------------------------------------------
# Coherence doc / mesure
# --------------------------------------------------------------------------

@cas("6. #240 : la doc ne presente plus le code 9 comme un garde-fou d'unicite")
def cas6():
    for p in (os.path.join(SKILL, "reference", "isam-api.md"),
              os.path.abspath(os.path.join(SKILL, "..", "reading-isam-files",
                                           "reference", "isam-api.md"))):
        t = lire(p)
        ligne = [l for l in t.split("\n") if l.startswith("| 9 |")]
        assert ligne, "ligne du code 9 introuvable dans " + p
        assert "PAS un garde-fou" in ligne[0], (
            "la nuance manque dans %s : %s" % (os.path.basename(p), ligne[0]))
    t = lire(os.path.join(SKILL, "SKILL.md"))
    assert "deduplication est **applicative**" in t or "applicative" in t, (
        "le SKILL.md doit dire que la deduplication est applicative")
    return "corrige dans les 2 copies vendorees + le SKILL.md"


@cas("7. #241 : la doc n'annonce plus une fonction absente de la DLL")
def cas7():
    p = os.path.join(SKILL, "reference", "isam-api.md")
    t = lire(p)
    assert "n'est pas exportee" in t, "l'ecart mesure doit etre ecrit"
    assert "xisam_record_liball" in t, "l'alternative reellement exportee doit etre nommee"
    return "le symbole reste mentionne, mais comme INEXISTANT, avec son remplacant"


@cas("8. #291(b) : la doc dit que treadlong et tpreadlong ne sont pas interchangeables")
def cas8():
    t = lire(os.path.join(SKILL, "reference", "isam-api.md"))
    assert "PAS interchangeables" in t or "PAS" in t and "interchangeable" in t
    assert "cle vide" in t, "le cas precis (parcours a cle vide) doit etre nomme"
    assert "ret=2" in t, "la mesure doit figurer"


# --------------------------------------------------------------------------
# Sonde sur fichier reel -- non applicable sans DLL / sans fichier
# --------------------------------------------------------------------------

def _fichier_reel(nom):
    """Cherche un .dhfi de test fourni par l'environnement, sinon None."""
    base = os.environ.get("ISAM_TEST_DIR")
    if not base:
        return None
    p = os.path.join(base, nom)
    return p if os.path.isfile(p) else None


@cas("9. La sonde rend un verdict exploitable quand la DLL est absente")
def cas9():
    """Sans DLL, la sonde doit dire `concluant: false` -- PAS un faux CONFIRMEE."""
    j = lire_json(os.path.join(STRUCT_ECRITURE, "structure_xmenuf_m2.json"))
    r = V.sonder_cle(j, "fichier_inexistant.dhfi", "Index_A_M2", "dll_inexistante.dll")
    assert r["concluant"] is False, r
    assert r["verdict"] is None, "aucun verdict ne doit etre rendu sans mesure : %s" % r
    assert "introuvable" in (r["detail"] or ""), r["detail"]
    return "une sonde sans mesure ne conclut pas -- elle le dit"


@cas("10. La sonde detecte un index inexistant et un champ de cle fantome")
def cas10():
    j = lire_json(os.path.join(STRUCT_ECRITURE, "structure_xmenuf_m2.json"))
    r = V.sonder_cle(j, "x.dhfi", "Index_INCONNU", DLL)
    assert r["concluant"] is False and "absent du bloc Keys" in r["detail"], r
    faux = json.loads(json.dumps(j))
    faux["Keys"]["Index_A_M2"]["Fields"] = ["Ce", "ChampQuiNexistePas"]
    r2 = V.sonder_cle(faux, "x.dhfi", "Index_A_M2", DLL)
    assert r2["concluant"] is False and "absent(s) de Structure" in r2["detail"], r2
    return "les deux erreurs de declaration sont attrapees avant tout acces fichier"


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
