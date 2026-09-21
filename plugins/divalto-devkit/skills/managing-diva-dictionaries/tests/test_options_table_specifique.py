#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables des options de table specifique (RETEX #207 / #245).

Aucun poste Divalto requis : chaque cas fabrique ses dictionnaires et ses JSON de
blocs en ISO-8859-1 + CRLF dans un repertoire temporaire.

Les trois defauts rejoues :

1. **#245 -- `creator` non expose.** Toutes les lignes `Version=` portaient `"Claude"`
   au lieu du login du developpeur, alors que le script voisin
   `generate_surcharge_field.py` exige deja `--user`. Le login DIVA ne se devine pas
   (ce n'est pas le login Windows) : l'identifiant est donc **obligatoire**, sans
   valeur par defaut, et deux gardes protegent la tracabilite -- refus de la virgule
   (qui casserait la ligne) et refus au-dela de 20 caracteres (qui serait tronque en
   silence).

2. **#207 -- champs standard imposes.** `Ce1`/`Dos`, les 4 champs d'audit et un
   container `U` etaient ajoutes sans condition, et `u_field_size=0` ne desactivait
   rien : le script **refusait de tourner** (`Nature invalide pour le champ 'U...': 0`).
   Le container est desormais absent par defaut -- convention pour une table dont
   l'integrateur est proprietaire -- et `--no-audit` retire les champs d'audit.
   `Ce1` reste **toujours** genere : une table peut exister sans discriminateur, mais
   en prevoir un fait partie des bonnes pratiques.

3. **#207 -- base existante.** L'insertion echouait sur `Base 'X' existe deja`. La
   suggestion du RETEX (ne pas generer le bloc `[BASE]`) aurait livre une table
   **orpheline** : le rattachement passe par une ligne `Nom=<table>,0` dans le
   `[TABLES]` de la base cible. Mesure sur un dictionnaire specifique reel : 10 bases
   sur 24 sont multi-tables, et leurs `[TABLES]` sont triees alphabetiquement sans
   exception -- d'ou le rang d'insertion teste ici.

Lancer :
    py .claude/skills/managing-diva-dictionaries/tests/run_all.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
GEN = os.path.join(SCRIPTS, "generate_dhsd_block.py")
VAL = os.path.join(SCRIPTS, "validate_dhsd.py")
INS = os.path.join(SCRIPTS, "insert_dhsd_blocks.py")
CRLF = chr(13) + chr(10)
ENC = "iso-8859-1"
LOGIN = "gjo_dev222"

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def run(cmd, entree=None):
    r = subprocess.run(cmd, capture_output=True,
                       input=None if entree is None else entree.encode("utf-8"))
    return (r.returncode,
            r.stdout.decode("utf-8", "replace"),
            r.stderr.decode("utf-8", "replace"))


def params(**extra):
    p = {"table": "Trace", "ce_value": "A", "base": "AlgTrace", "dict_name": "gtfdd",
         "fields": [{"name": "Cod", "nature": "20", "description": "Code"}],
         "indexes": [{"name": "Index_A", "description": "Cle",
                      "fields": ["Dos", "Cod"], "unique": True}]}
    p.update(extra)
    return p


def generer(tmp, args=(), **extra):
    """Lance le generateur. Retourne (code, dict_json_ou_None, stderr)."""
    sortie = os.path.join(tmp, "blocs.json")
    code, out, err = run([sys.executable, GEN, "--stdin", "--output", sortie] + list(args),
                         entree=json.dumps(params(**extra)))
    if code != 0 or not os.path.isfile(sortie):
        return code, None, err
    with open(sortie, "r", encoding="utf-8") as fh:
        return code, json.load(fh), err


def valider_blocs(tmp, blocs, args=()):
    p = os.path.join(tmp, "a_valider.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(blocs, fh)
    code, out, err = run([sys.executable, VAL, "--blocks", p] + list(args))
    i = out.find("{")
    assert i >= 0, "pas de JSON : " + out[:200] + err[:200]
    return json.loads(out[i:])


def regles(rapport, cle):
    return {d["rule"] for d in rapport.get(cle) or []}


def lignes_version(blocs):
    """Toutes les lignes Version= de tous les blocs generes."""
    textes = [blocs["blocks"]["table"], blocs["blocks"]["base"]]
    textes += [c["block"] for c in blocs["blocks"]["champs"]]
    textes += [i["block"] for i in blocs["blocks"]["indexes"]]
    out = []
    for t in textes:
        out += [l for l in t.split("\n") if l.startswith("Version=")]
    return out


# --------------------------------------------------------------------------
# Fabrication d'un dictionnaire complet (6 zones detectables)
# --------------------------------------------------------------------------

def dictionnaire(tables_de_la_base):
    """Un .dhsd minimal mais complet. `tables_de_la_base` = [TABLES] de AlgTrace."""
    L = ["[CHAMP]",
         "Version=1,20260101120000,ROOT,20260101120000,ROOT",
         "Nom=Lib,Libelle,1", "Gel=3", "Nature=20", "NomOdbc=Lib",
         "Flags=o,1,n,n,n,n,n,n,n", "[/CHAMP]",
         "[TABLE]",
         "Version=1,20260101120000,ROOT,20260101120000,ROOT",
         "Nom=Deja,Table préexistante créée,1", "NomOdbc=Deja",
         "Taille=29,29", "Pack=0,0", "CE=Ce1,Z", "[CHAMPS]",
         "Nom=Ce1,1,2,N,0,0,N,3", "Nom=Dos,2,2,N,0,0,N,3", "Nom=Lib,10,2,N,0,0,N,3",
         "[/CHAMPS]", "[/TABLE]",
         "[BASE]",
         "Version=1,20260101120000,ROOT,20260101120000,ROOT",
         "Nom=AlgTrace,Base de trace,1", "DateM=AAAA", "Fichier=I,0,ALGTRACE.dhfi",
         "Versionbase=223", "DateMIndex=BBBB", "[TABLES]"]
    L += ["Nom=%s,0" % t for t in tables_de_la_base]
    L += ["[/TABLES]",
          "[BASE]",
          "Version=1,20260101120000,ROOT,20260101120000,ROOT",
          "Nom=AlgZautre,Autre base,1", "DateM=CCCC", "Fichier=I,0,ALGZAUTRE.dhfi",
          "Versionbase=223", "DateMIndex=DDDD", "[TABLES]", "Nom=Deja,0", "[/TABLES]",
          "[INDEX]",
          "Version=1,20260101120000,ROOT,20260101120000,ROOT",
          "Nom=Index_Z,Cle preexistante,1", "DateM=EEEE",
          "CLE=AlgTrace,Z,Ce1,2,Z,n,1,n", "[CHAMPS]", "Nom=Dos,1,0,", "[/CHAMPS]",
          "[/INDEX]",
          "[INDEXL]", "Nom=AlgTrace,Deja,Index_Z,0", "[/INDEXL]"]
    return L


def ecrire_dico(chemin, lignes):
    with open(chemin, "wb") as fh:
        fh.write((CRLF.join(lignes) + CRLF).encode(ENC))
    return chemin


def empreinte(chemin):
    return hashlib.sha256(open(chemin, "rb").read()).hexdigest()


def tables_de_la_base(chemin, base="AlgTrace"):
    """Liste des tables rattachees a `base`, lue dans le fichier."""
    lignes = open(chemin, "r", encoding=ENC).read().replace(CRLF, chr(10)).split(chr(10))
    i = 0
    while i < len(lignes):
        if lignes[i].strip() == "[BASE]":
            j, nom = i + 1, None
            while j < len(lignes) and lignes[j].strip() != "[TABLES]":
                if lignes[j].startswith("Nom=") and nom is None:
                    nom = lignes[j][4:].split(",")[0]
                j += 1
            if nom == base:
                k, out = j + 1, []
                while k < len(lignes) and lignes[k].strip() != "[/TABLES]":
                    if lignes[k].startswith("Nom="):
                        out.append(lignes[k][4:].split(",")[0])
                    k += 1
                return out
            i = j
        i += 1
    return None


def inserer(tmp, blocs, args=(), tables=("Deja",)):
    """Fabrique un dictionnaire, insere les blocs, retourne (code, rapport, dico)."""
    dico = ecrire_dico(os.path.join(tmp, "algdd.dhsd"), dictionnaire(list(tables)))
    pb = os.path.join(tmp, "blocs_ins.json")
    with open(pb, "w", encoding="utf-8") as fh:
        json.dump(blocs, fh)
    code, out, err = run([sys.executable, INS, "--dhsd", dico, "--blocks", pb,
                          "--no-backup"] + list(args))
    i = out.find("{")
    rapport = json.loads(out[i:]) if i >= 0 else None
    return code, rapport, dico


# --------------------------------------------------------------------------
# Cas -- #245 : identifiant du developpeur
# --------------------------------------------------------------------------

@cas("1. #245 : sans --user, le generateur REFUSE (plus de defaut 'Claude')")
def cas1(tmp):
    code, blocs, err = generer(tmp)
    assert code == 1, "exit attendu 1, obtenu %d" % code
    assert blocs is None
    assert "login" in err.lower() and "--user" in err, err[:200]
    return "aucune valeur par defaut inventee"


@cas("2. #245 : --user propage dans TOUTES les lignes Version=, plus aucun 'Claude'")
def cas2(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN, "--u-field-size", "500"])
    assert code == 0, err[:200]
    vs = lignes_version(blocs)
    assert len(vs) >= 4, "attendu au moins 4 lignes Version= (champ/table/base/index) : %d" % len(vs)
    for v in vs:
        assert LOGIN in v, "login absent de : " + v
        assert "Claude" not in v, "'Claude' subsiste dans : " + v
    assert blocs["summary"]["creator"] == LOGIN, blocs["summary"]
    return "%d lignes Version= estampillees %s" % (len(vs), LOGIN)


@cas("3. #245 : une virgule dans le login est REFUSEE (elle casserait Version=)")
def cas3(tmp):
    code, blocs, err = generer(tmp, ["--user", "gjo,dev"])
    assert code == 1 and blocs is None, code
    assert "virgule" in err.lower(), err[:200]


@cas("4. #245 : un login > 20 car. est REFUSE, pas tronque en silence")
def cas4(tmp):
    long_login = "g" * 25
    code, blocs, err = generer(tmp, ["--user", long_login])
    assert code == 1 and blocs is None, code
    assert "tronque" in err.lower(), err[:200]
    return "la troncature silencieuse detruirait la tracabilite demandee"


@cas("5. #245 : le login peut aussi venir du JSON, et le CLI est prioritaire")
def cas5(tmp):
    code, blocs, err = generer(tmp, [], creator="par_le_json")
    assert code == 0, err[:200]
    assert blocs["summary"]["creator"] == "par_le_json", blocs["summary"]
    code, blocs, err = generer(tmp, ["--user", LOGIN], creator="par_le_json")
    assert code == 0, err[:200]
    assert blocs["summary"]["creator"] == LOGIN, "le CLI doit gagner : %s" % blocs["summary"]


# --------------------------------------------------------------------------
# Cas -- #207 : champs standard
# --------------------------------------------------------------------------

@cas("6. #207 : PAS de container U par defaut (avant : le script refusait de tourner)")
def cas6(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN])
    assert code == 0, err[:200]
    assert blocs["summary"]["u_field"] is None, blocs["summary"]
    assert "UTrace" not in blocs["positions"], list(blocs["positions"])
    assert "UTrace" not in [c["name"] for c in blocs["blocks"]["champs"]], "bloc [CHAMP] parasite"
    assert "UTrace" not in blocs["blocks"]["table"], "ligne de placement parasite"
    return "ni declaration [CHAMP] ni ligne de placement"


@cas("7. #207 : --u-field-size 500 en ajoute un (ce n'est pas faux, c'est un choix)")
def cas7(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN, "--u-field-size", "500"])
    assert code == 0, err[:200]
    assert blocs["summary"]["u_field"] == {"name": "UTrace", "size": 500}, blocs["summary"]
    assert blocs["positions"]["UTrace"]["size"] == 500, blocs["positions"]["UTrace"]


@cas("8. #207 : --no-audit retire les 4 champs d'audit")
def cas8(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN, "--no-audit"])
    assert code == 0, err[:200]
    for champ in ("UserCr", "UserMo", "UserCrDh", "UserMoDh"):
        assert champ not in blocs["positions"], "%s toujours present" % champ
    assert blocs["summary"]["audit_fields"] is False, blocs["summary"]
    assert list(blocs["positions"]) == ["Ce1", "Dos", "Cod"], list(blocs["positions"])
    return "Ce1 et Dos conserves : une table generee prevoit son discriminateur"


@cas("9. #207 : Ce1 TOUJOURS genere, meme avec toutes les options desactivantes")
def cas9(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN, "--no-audit", "--u-field-size", "0"])
    assert code == 0, err[:200]
    assert list(blocs["positions"])[0] == "Ce1", list(blocs["positions"])
    assert "CE=Ce1,A" in blocs["blocks"]["table"], "ligne CE= attendue dans le bloc [TABLE]"
    return "le discriminateur n'est pas desactivable a la generation, par decision"


@cas("10. #207 : positions sans trou dans les 4 combinaisons d'options")
def cas10(tmp):
    combis = [[], ["--no-audit"], ["--u-field-size", "500"],
              ["--no-audit", "--u-field-size", "500"]]
    for extra in combis:
        code, blocs, err = generer(tmp, ["--user", LOGIN] + extra)
        assert code == 0, err[:200]
        attendu = 1
        for nom, info in blocs["positions"].items():
            assert info["position"] == attendu, (
                "trou/chevauchement avec %s : %s attendu pos %d, trouve %d"
                % (extra, nom, attendu, info["position"]))
            attendu += info["size"]
        assert blocs["taille"] == attendu - 1, (extra, blocs["taille"], attendu - 1)
    return "4 combinaisons : positions contigues et Taille= coherente"


# --------------------------------------------------------------------------
# Cas -- DICT03 : absence deliberee vs accidentelle
# --------------------------------------------------------------------------

@cas("11. DICT03 : absence DELIBEREE du container U -> warning, blocs valides")
def cas11(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN, "--no-audit"])
    assert code == 0, err[:200]
    r = valider_blocs(tmp, blocs)
    assert r["valid"] is True, r["errors"]
    assert "DICT03" in regles(r, "warnings"), r
    assert "DICT03" not in regles(r, "errors"), r["errors"]
    assert "deliberee" in " ".join(d["message"] for d in r["warnings"]), r["warnings"]
    return "sans ca, le generateur produirait des blocs refuses par son propre validateur"


@cas("12. TEMOIN : le meme JSON prive de la cle u_field -> DICT03 redevient une ERREUR")
def cas12(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN, "--no-audit"])
    assert code == 0, err[:200]
    del blocs["summary"]["u_field"]        # etat d'un JSON d'avant le correctif
    r = valider_blocs(tmp, blocs)
    assert r["valid"] is False, "le temoin doit echouer, sinon le cas 11 ne prouve rien"
    assert "DICT03" in regles(r, "errors"), r
    return "l'absence non declaree reste une erreur : le laxisme est cible, pas global"


@cas("13. DICT03 sur fichier : --no-u-field passe en warning, sans lui reste une erreur")
def cas13(tmp):
    lignes = dictionnaire(["Deja"])
    dico = ecrire_dico(os.path.join(tmp, "algdd.dhsd"), lignes)
    code, out, err = run([sys.executable, VAL, "--path", dico, "--table", "Deja"])
    r = json.loads(out[out.find("{"):])
    assert "DICT03" in regles(r, "errors"), "sans le drapeau, DICT03 doit rester une erreur"
    code, out, err = run([sys.executable, VAL, "--path", dico, "--table", "Deja",
                          "--no-u-field"])
    r2 = json.loads(out[out.find("{"):])
    assert "DICT03" in regles(r2, "warnings") and "DICT03" not in regles(r2, "errors"), r2
    assert "assumee" in " ".join(d["message"] for d in r2["warnings"]), r2["warnings"]


# --------------------------------------------------------------------------
# Cas -- #207 : base existante
# --------------------------------------------------------------------------

@cas("14. #207 : base existante SANS --attach-to-base -> erreur qui NOMME l'option")
def cas14(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN])
    dico_code, rapport, dico = inserer(tmp, blocs)
    assert dico_code == 1, "exit attendu 1, obtenu %d" % dico_code
    msg = " ".join(rapport["errors"])
    assert "existe deja" in msg, msg
    assert "--attach-to-base" in msg, "le message doit dire quoi faire : " + msg
    return "avant, l'erreur laissait le developpeur sans issue"


@cas("15. #207 : --attach-to-base rattache la table SANS creer de bloc [BASE]")
def cas15(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN])
    ins_code, rapport, dico = inserer(tmp, blocs, ["--attach-to-base", "AlgTrace"])
    assert ins_code == 0, rapport.get("errors")
    assert "rattachee" in rapport["insertions"]["base"]["action"], rapport["insertions"]["base"]
    contenu = open(dico, "r", encoding=ENC).read()
    assert contenu.count("[BASE]") == 2, "aucun nouveau bloc [BASE] ne doit apparaitre"
    assert tables_de_la_base(dico) == ["Deja", "Trace"], tables_de_la_base(dico)
    return "la table est RATTACHEE : ne pas creer le [BASE] seul l'aurait laissee orpheline"


@cas("16. #207 : rang alphabetique respecte au milieu d'une liste existante")
def cas16(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN])
    ins_code, rapport, dico = inserer(tmp, blocs, ["--attach-to-base", "AlgTrace"],
                                      tables=("Alpha", "Zoulou"))
    assert ins_code == 0, rapport.get("errors")
    assert tables_de_la_base(dico) == ["Alpha", "Trace", "Zoulou"], tables_de_la_base(dico)
    return "convention mesuree sur 10 bases multi-tables reelles : tri alpha"


@cas("17. #207 : insertion en fin de liste, juste avant [/TABLES]")
def cas17(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN])
    ins_code, rapport, dico = inserer(tmp, blocs, ["--attach-to-base", "AlgTrace"],
                                      tables=("Alpha", "Beta"))
    assert ins_code == 0, rapport.get("errors")
    assert tables_de_la_base(dico) == ["Alpha", "Beta", "Trace"], tables_de_la_base(dico)


@cas("18. #207 : table deja rattachee -> erreur, fichier INCHANGE")
def cas18(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN])
    dico = ecrire_dico(os.path.join(tmp, "algdd.dhsd"), dictionnaire(["Deja", "Trace"]))
    avant = empreinte(dico)
    pb = os.path.join(tmp, "b.json")
    with open(pb, "w", encoding="utf-8") as fh:
        json.dump(blocs, fh)
    c, out, e = run([sys.executable, INS, "--dhsd", dico, "--blocks", pb, "--no-backup",
                     "--attach-to-base", "AlgTrace"])
    r = json.loads(out[out.find("{"):])
    assert c == 1, c
    assert "deja rattachee" in " ".join(r["errors"]), r["errors"]
    assert empreinte(dico) == avant, "le fichier a ete modifie malgre l'erreur"


@cas("19. #207 : base inexistante -> erreur, fichier INCHANGE")
def cas19(tmp):
    # Les blocs doivent REFERENCER la base absente, sinon c'est le controle de
    # coherence (cas 20) qui repond le premier et ce cas ne teste rien.
    code, blocs, err = generer(tmp, ["--user", LOGIN], base="AlgInexistante")
    assert code == 0, err[:200]
    dico = ecrire_dico(os.path.join(tmp, "algdd.dhsd"), dictionnaire(["Deja"]))
    avant = empreinte(dico)
    pb = os.path.join(tmp, "b.json")
    with open(pb, "w", encoding="utf-8") as fh:
        json.dump(blocs, fh)
    c, out, e = run([sys.executable, INS, "--dhsd", dico, "--blocks", pb, "--no-backup",
                     "--attach-to-base", "AlgInexistante"])
    r = json.loads(out[out.find("{"):])
    assert c == 1, c
    assert "introuvable" in " ".join(r["errors"]), r["errors"]
    assert empreinte(dico) == avant, "le fichier a ete modifie malgre l'erreur"


@cas("20. #207 : incoherence base rattachee / base des index -> refus")
def cas20(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN])   # blocs referencent AlgTrace
    dico = ecrire_dico(os.path.join(tmp, "algdd.dhsd"), dictionnaire(["Deja"]))
    avant = empreinte(dico)
    pb = os.path.join(tmp, "b.json")
    with open(pb, "w", encoding="utf-8") as fh:
        json.dump(blocs, fh)
    c, out, e = run([sys.executable, INS, "--dhsd", dico, "--blocks", pb, "--no-backup",
                     "--attach-to-base", "AlgZautre"])
    r = json.loads(out[out.find("{"):])
    assert c == 1, c
    msg = " ".join(r["errors"])
    assert "Incoherence" in msg and "AlgTrace" in msg, msg
    assert empreinte(dico) == avant, "le fichier a ete modifie malgre l'erreur"
    return "sinon : table rattachee a une base, index pointant vers une autre"


@cas("21. #207 : apres rattachement, encodage ISO-8859-1 + CRLF preserve")
def cas21(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN])
    ins_code, rapport, dico = inserer(tmp, blocs, ["--attach-to-base", "AlgTrace"])
    assert ins_code == 0, rapport.get("errors")
    brut = open(dico, "rb").read()
    assert brut.count(CRLF.encode()) == brut.count(chr(10).encode()), "fin de ligne cassee"
    # Le fixture porte un libelle accentue : le test n'est discriminant que si
    # l'octet ISO-8859-1 est encore la ET que le fichier n'est PAS de l'UTF-8
    # (une reecriture en UTF-8 aurait produit deux octets pour le meme caractere).
    assert bytes([0xE9]) in brut, "l'octet accentue ISO-8859-1 a disparu"
    try:
        brut.decode("utf-8")
        raise AssertionError("le fichier decode en UTF-8 : il a ete reecrit dans le "
                             "mauvais encodage")
    except UnicodeDecodeError:
        pass
    brut.decode(ENC)                      # doit se relire en ISO-8859-1
    return "CRLF pur, octet accentue intact, non decodable en UTF-8"


@cas("22. #207 : la validation post-insertion ne remonte PAS DICT03 en erreur")
def cas22(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN, "--no-audit"])
    ins_code, rapport, dico = inserer(tmp, blocs, ["--attach-to-base", "AlgTrace"])
    assert ins_code == 0, rapport.get("errors")
    v = rapport.get("validation")
    assert v is not None, "la validation post-insertion doit tourner"
    assert "DICT03" not in regles(v, "errors"), (
        "l'inséreur doit propager l'absence deliberee du container U : %s" % v["errors"])
    return "le drapeau --no-u-field est propage depuis summary.u_field"


@cas("23. #207 : une base NOUVELLE continue de fonctionner (non-regression)")
def cas23(tmp):
    code, blocs, err = generer(tmp, ["--user", LOGIN], base="AlgNeuve")
    ins_code, rapport, dico = inserer(tmp, blocs)
    assert ins_code == 0, rapport.get("errors")
    assert rapport["insertions"]["base"]["action"] == "base creee", rapport["insertions"]["base"]
    contenu = open(dico, "r", encoding=ENC).read()
    assert contenu.count("[BASE]") == 3, "le nouveau bloc [BASE] doit avoir ete insere"


# --------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    echecs = []
    for titre, fn in CAS:
        tmp = tempfile.mkdtemp(prefix="dhsd_lotb_")
        try:
            note = fn(tmp)
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
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
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
