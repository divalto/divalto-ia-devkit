#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables de `compare_dhsd_versions.py` (RETEX #110).

Aucun poste Divalto requis : chaque cas **fabrique** ses deux dictionnaires en
ISO-8859-1 + CRLF dans un repertoire temporaire. Aucune dependance a une
arborescence de sources, ni a une version particuliere de l'ERP.

Ce que ces cas verrouillent :

1. **le critere est `Taille=`, pas le nombre de champs** -- et le comptage se trompe
   dans les DEUX sens : une table qui change de taille a nombre de champs constant
   (cas 1, faux negatif) et une table qui gagne des champs a taille constante
   (cas 2, faux positif) ;
2. **la capacite d'un container `U<X>` se lit dans sa `Nature=` globale**, pas en 6e
   position de sa ligne `[CHAMPS]` -- ou elle vaut toujours 0. Le cas 5 embarque la
   lecture fautive comme **temoin** : il verifie qu'elle ne voit rien la ou la lecture
   correcte voit une reduction de 1501 a 1000 octets ;
3. **le `Filler` n'est pas rapporte** : c'est la reserve de Divalto, sa consommation
   est transparente pour l'integrateur qui a respecte la zone `U` (cas 3) ;
4. les **codes retour** 0 / 1 / 2, contractuels pour un usage en garde-fou de script.

Lancer :
    py .claude/skills/managing-diva-dictionaries/tests/run_all.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "..", "scripts", "compare_dhsd_versions.py"))
CRLF = chr(13) + chr(10)
ENC = "iso-8859-1"

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


# --------------------------------------------------------------------------
# Fabrication de dictionnaires minimaux
# --------------------------------------------------------------------------

def bloc_champ(nom, nature, desc="Champ de test"):
    """Un bloc [CHAMP] global. C'est ici que vit la capacite d'un container U."""
    return ["[CHAMP]",
            "Version=1,20260101120000,Test,20260101120000,Test",
            "Nom=%s,%s,1" % (nom, desc),
            "Gel=3",
            "Nature=%s" % nature,
            "NomOdbc=%s" % nom,
            "Flags=o,1,n,n,n,n,n,n,n",
            "[/CHAMP]"]


def bloc_table(nom, taille, champs):
    """Un bloc [TABLE] + [CHAMPS]. `champs` = [(nom, pos, taille_en_ligne, gel)].

    La `taille_en_ligne` (6e position) est renseignee pour le `Filler` et vaut 0
    partout ailleurs -- container `U<X>` compris. C'est la convention du standard.
    """
    lignes = ["[TABLE]",
              "Version=1,20260101120000,Test,20260101120000,Test",
              "Nom=%s,Table de test,1" % nom,
              "NomOdbc=%s" % nom,
              "Taille=%d,%d" % (taille, taille),
              "Pack=0,0",
              "CE=Ce1,1",
              "[CHAMPS]"]
    for nom_c, pos, taille_ligne, gel in champs:
        lignes.append("Nom=%s,%d,2,N,0,%d,N,%d" % (nom_c, pos, taille_ligne, gel))
    lignes += ["[/CHAMPS]", "[/TABLE]"]
    return lignes


def ecrire(chemin, blocs):
    """Ecrit le .dhsd en ISO-8859-1 + CRLF (encodage DIVA)."""
    texte = CRLF.join([l for bloc in blocs for l in bloc]) + CRLF
    with open(chemin, "wb") as fh:
        fh.write(texte.encode(ENC))
    return chemin


def paire(tmp, blocs_avant, blocs_apres):
    return (ecrire(os.path.join(tmp, "avant.dhsd"), blocs_avant),
            ecrire(os.path.join(tmp, "apres.dhsd"), blocs_apres))


# --------------------------------------------------------------------------
# Invocation du script
# --------------------------------------------------------------------------

def run(avant, apres, *extra):
    r = subprocess.run([sys.executable, SCRIPT, "--from", avant, "--to", apres]
                       + list(extra), capture_output=True)
    return (r.returncode,
            r.stdout.decode("utf-8", "replace"),
            r.stderr.decode("utf-8", "replace"))


def run_json(avant, apres, *extra):
    code, out, err = run(avant, apres, *extra)
    i = out.find("{")
    assert i >= 0, "aucun JSON en sortie (code %d) : %s / %s" % (code, out[:200], err[:200])
    return code, json.loads(out[i:])


def tables_de(liste):
    return sorted(d["table"].lower() for d in liste)


# --------------------------------------------------------------------------
# Cas
# --------------------------------------------------------------------------

@cas("1. FAUX NEGATIF du comptage : Taille change, nombre de champs IDENTIQUE")
def cas1(tmp):
    champs = [("Ce1", 1, 0, 3), ("Dos", 3, 0, 3), ("Lib", 11, 0, 3),
              ("Filler", 61, 100, 1), ("UXq", 161, 0, 3)]
    a, b = paire(tmp,
                 [bloc_champ("UXq", "1500")] + [bloc_table("Xq", 13500, champs)],
                 [bloc_champ("UXq", "1500")] + [bloc_table("Xq", 13700, champs)])
    code, js = run_json(a, b)
    assert code == 1, "exit attendu 1, obtenu %d" % code
    assert tables_de(js["incompatibles"]) == ["xq"], js["incompatibles"]
    d = js["incompatibles"][0]
    assert (d["taille_avant"], d["taille_apres"]) == (13500, 13700), d
    assert d["champs_avant"] == d["champs_apres"], (
        "le cas doit avoir un nombre de champs CONSTANT, sinon il ne prouve rien : %s" % d)
    return "5 champs de part et d'autre, 13500 -> 13700 octets : signale"


@cas("2. FAUX POSITIF du comptage : champs ajoutes, Taille= CONSTANTE")
def cas2(tmp):
    av = [("Ce1", 1, 0, 3), ("Dos", 3, 0, 3),
          ("Filler", 11, 100, 1), ("UArtdepo", 111, 0, 3)]
    ap = [("Ce1", 1, 0, 3), ("Dos", 3, 0, 3),
          ("NouvA", 11, 0, 3), ("NouvB", 31, 0, 3),
          ("Filler", 51, 60, 1), ("UArtdepo", 111, 0, 3)]
    glob = [bloc_champ("UArtdepo", "1500"), bloc_champ("NouvA", "20"),
            bloc_champ("NouvB", "20")]
    a, b = paire(tmp,
                 glob + [bloc_table("Artdepo", 500, av)],
                 glob + [bloc_table("Artdepo", 500, ap)])
    code, js = run_json(a, b)
    assert code == 0, "exit attendu 0 (aucune incompatibilite), obtenu %d" % code
    assert js["incompatibles"] == [], js["incompatibles"]
    assert tables_de(js["compatibles_champs_ajoutes"]) == ["artdepo"], js
    d = js["compatibles_champs_ajoutes"][0]
    assert (d["champs_avant"], d["champs_apres"]) == (4, 6), d
    return "4 -> 6 champs a Taille=500 : classee compatible, pas d'alerte"


@cas("3. Filler consomme sans ajout de champ : AUCUN constat (transparent)")
def cas3(tmp):
    def t(taille_filler):
        return [bloc_champ("UArt", "1500"),
                bloc_table("Art", 500, [("Ce1", 1, 0, 3),
                                        ("Filler", 3, taille_filler, 1),
                                        ("UArt", 403, 0, 3)])]
    a, b = paire(tmp, t(400), t(200))
    code, js = run_json(a, b)
    assert code == 0, code
    assert js["incompatibles"] == [] and js["compatibles_champs_ajoutes"] == [], js
    assert js["containers_u_modifies"] == [], js["containers_u_modifies"]
    assert js["resume"]["inchangees"] == 1, js["resume"]
    return "Filler 400 -> 200 octets : rien de rapporte, table dite inchangee"


@cas("4. Container U REDUIT : anomalie, a remonter a Divalto")
def cas4(tmp):
    champs = [("Ce1", 1, 0, 3), ("UArt", 3, 0, 3)]
    a, b = paire(tmp,
                 [bloc_champ("UArt", "1501")] + [bloc_table("Art", 1504, champs)],
                 [bloc_champ("UArt", "1000")] + [bloc_table("Art", 1504, champs)])
    code, js = run_json(a, b)
    mods = js["containers_u_modifies"]
    assert len(mods) == 1, mods
    assert (mods[0]["avant"]["taille"], mods[0]["apres"]["taille"]) == (1501, 1000), mods
    nat = mods[0]["nature"]
    assert "REDUITE" in nat and "Divalto" in nat, nat
    return "1501 -> 1000 octets qualifie ANOMALIE + remontee Divalto"


@cas("5. TEMOIN : la lecture en 6e position ne voit RIEN sur le cas 4")
def cas5(tmp):
    champs = [("Ce1", 1, 0, 3), ("UArt", 3, 0, 3)]
    a, b = paire(tmp,
                 [bloc_champ("UArt", "1501")] + [bloc_table("Art", 1504, champs)],
                 [bloc_champ("UArt", "1000")] + [bloc_table("Art", 1504, champs)])

    def lecture_fautive(chemin):
        """La v1 du script : capacite = 6e position de la ligne [CHAMPS]."""
        vals = []
        dans_champs = False
        with open(chemin, "r", encoding=ENC) as fh:
            for ligne in fh:
                s = ligne.strip()
                if s.upper() == "[CHAMPS]":
                    dans_champs = True
                elif s.startswith("["):
                    dans_champs = False
                elif dans_champs and s.lower().startswith("nom=uart,"):
                    vals.append(int(s.split(",")[5]))
        return vals

    fautif_a, fautif_b = lecture_fautive(a), lecture_fautive(b)
    assert fautif_a == fautif_b == [0], (fautif_a, fautif_b)

    code, js = run_json(a, b)
    assert len(js["containers_u_modifies"]) == 1, (
        "la lecture correcte doit voir le changement que le temoin ne voit pas")
    return "lecture fautive : 0 == 0 (aucun constat) / lecture correcte : 1501 -> 1000"


@cas("6. Container U agrandi : rapporte SANS qualification d'anomalie")
def cas6(tmp):
    champs = [("Ce1", 1, 0, 3), ("UArt", 3, 0, 3)]
    a, b = paire(tmp,
                 [bloc_champ("UArt", "1000")] + [bloc_table("Art", 1004, champs)],
                 [bloc_champ("UArt", "1500")] + [bloc_table("Art", 1004, champs)])
    code, js = run_json(a, b)
    nat = js["containers_u_modifies"][0]["nature"]
    assert "augmentee" in nat, nat
    assert "ANOMALIE" not in nat, "un agrandissement n'est pas une anomalie : " + nat
    return "1000 -> 1500 octets : signale, non qualifie anomalie"


@cas("7. Container U DISPARU : anomalie (les champs custom perdent leur ancrage)")
def cas7(tmp):
    a, b = paire(tmp,
                 [bloc_champ("UArt", "1500")]
                 + [bloc_table("Art", 1504, [("Ce1", 1, 0, 3), ("UArt", 3, 0, 3)])],
                 [bloc_table("Art", 1504, [("Ce1", 1, 0, 3), ("Filler", 3, 1500, 1)])])
    code, js = run_json(a, b)
    mods = js["containers_u_modifies"]
    assert len(mods) == 1 and mods[0]["apres"] is None, mods
    assert "DISPARU" in mods[0]["nature"] and "ANOMALIE" in mods[0]["nature"], mods


@cas("8. Container U apparu : la table devient surchargeable, sans risque")
def cas8(tmp):
    a, b = paire(tmp,
                 [bloc_table("Art", 1504, [("Ce1", 1, 0, 3), ("Filler", 3, 1500, 1)])],
                 [bloc_champ("UArt", "1500")]
                 + [bloc_table("Art", 1504, [("Ce1", 1, 0, 3), ("UArt", 3, 0, 3)])])
    code, js = run_json(a, b)
    nat = js["containers_u_modifies"][0]["nature"]
    assert "apparu" in nat and "sans risque" in nat, nat


@cas("9. Tables ajoutees / supprimees")
def cas9(tmp):
    def t(n):
        return bloc_table(n, 100, [("Ce1", 1, 0, 3)])
    a, b = paire(tmp, [t("Art"), t("Vieux")], [t("Art"), t("Neuf")])
    code, js = run_json(a, b)
    assert js["tables_ajoutees"] == ["Neuf"], js["tables_ajoutees"]
    assert js["tables_supprimees"] == ["Vieux"], js["tables_supprimees"]
    assert js["resume"]["tables_communes"] == 1, js["resume"]


@cas("10. Dictionnaires identiques : exit 0, rien a signaler")
def cas10(tmp):
    blocs = [bloc_champ("UArt", "1500"),
             bloc_table("Art", 500, [("Ce1", 1, 0, 3), ("UArt", 3, 0, 3)])]
    a, b = paire(tmp, blocs, blocs)
    code, js = run_json(a, b)
    assert code == 0, code
    assert js["resume"]["taille_changee"] == 0, js["resume"]
    assert js["containers_u_modifies"] == [], js["containers_u_modifies"]


@cas("11. Fichier introuvable : exit 2 + message sur stderr")
def cas11(tmp):
    a = ecrire(os.path.join(tmp, "avant.dhsd"),
               [bloc_table("Art", 100, [("Ce1", 1, 0, 3)])])
    code, out, err = run(a, os.path.join(tmp, "inexistant.dhsd"))
    assert code == 2, "exit attendu 2, obtenu %d" % code
    assert "introuvable" in err.lower(), err[:200]


@cas("12. --only-incompatible : ne garde que le perimetre a recompiler")
def cas12(tmp):
    av = [("Ce1", 1, 0, 3), ("Filler", 3, 100, 1)]
    ap = [("Ce1", 1, 0, 3), ("Nouv", 3, 0, 3), ("Filler", 23, 80, 1)]
    a, b = paire(tmp,
                 [bloc_table("Grande", 500, av),
                  bloc_table("Part", 100, [("Ce1", 1, 0, 3)])],
                 [bloc_champ("Nouv", "20"), bloc_table("Grande", 700, ap),
                  bloc_table("Neuve", 100, [("Ce1", 1, 0, 3)])])
    code, js = run_json(a, b, "--only-incompatible")
    assert code == 1, code
    assert tables_de(js["incompatibles"]) == ["grande"], js["incompatibles"]
    for cle in ("compatibles_champs_ajoutes", "tables_ajoutees", "tables_supprimees"):
        assert js[cle] == [], "%s devrait etre vide : %s" % (cle, js[cle])


@cas("13. --format text : porte le message actionnable")
def cas13(tmp):
    champs = [("Ce1", 1, 0, 3)]
    a, b = paire(tmp, [bloc_table("Art", 100, champs)],
                 [bloc_table("Art", 150, champs)])
    code, out, err = run(a, b, "--format", "text")
    assert code == 1, code
    for attendu in ("A FAIRE", "recompiler", "enregistrement deja alloue", "Taille"):
        assert attendu in out, "manque %r dans la sortie texte" % attendu
    assert "Filler" in out, "la note Filler doit rester visible en sortie texte"


@cas("14. Lecture ISO-8859-1 : un libelle accentue ne fait pas deriver l'analyse")
def cas14(tmp):
    ch = [("Ce1", 1, 0, 3)]
    lib = bloc_champ("Lib", "20", "Libellé de l'article, créé à Strasbourg (été)")
    a, b = paire(tmp, [lib, bloc_table("Art", 100, ch)],
                 [lib, bloc_table("Art", 150, ch)])
    brut = open(a, "rb").read()
    assert bytes([0xE9]) in brut, "le fixture doit porter un octet ISO-8859-1 accentue"
    code, js = run_json(a, b)
    assert code == 1 and tables_de(js["incompatibles"]) == ["art"], js
    return "libelle accentue en ISO-8859-1 : lu sans erreur, analyse inchangee"


@cas("15. Casse du nom de table : Art et ART sont la MEME table")
def cas15(tmp):
    a, b = paire(tmp,
                 [bloc_table("Art", 100, [("Ce1", 1, 0, 3)])],
                 [bloc_table("ART", 150, [("Ce1", 1, 0, 3)])])
    code, js = run_json(a, b)
    assert js["resume"]["tables_communes"] == 1, js["resume"]
    assert js["tables_ajoutees"] == [] and js["tables_supprimees"] == [], js
    assert tables_de(js["incompatibles"]) == ["art"], js["incompatibles"]


@cas("16. Capacite U indeterminable : le script le DIT au lieu de comparer des None")
def cas16(tmp):
    champs = [("Ce1", 1, 0, 3), ("UArt", 3, 0, 3)]
    a, b = paire(tmp,
                 [bloc_champ("UArt", "1500")] + [bloc_table("Art", 1504, champs)],
                 [bloc_table("Art", 1504, champs)])
    code, js = run_json(a, b)
    mods = js["containers_u_modifies"]
    assert len(mods) == 1, mods
    assert "non determinee" in mods[0]["nature"], mods[0]["nature"]


@cas("17. Casse du nom de container a capacite egale : AUCUN faux constat")
def cas17(tmp):
    a, b = paire(tmp,
                 [bloc_champ("UArt", "1500")]
                 + [bloc_table("Art", 1504, [("Ce1", 1, 0, 3), ("UArt", 3, 0, 3)])],
                 [bloc_champ("UART", "1500")]
                 + [bloc_table("Art", 1504, [("Ce1", 1, 0, 3), ("UART", 3, 0, 3)])])
    code, js = run_json(a, b)
    assert js["containers_u_modifies"] == [], (
        "UArt -> UART a capacite identique n'est pas un changement de capacite : %s"
        % js["containers_u_modifies"])
    assert code == 0, code


# --------------------------------------------------------------------------

def main():
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    echecs = []
    for titre, fn in CAS:
        tmp = tempfile.mkdtemp(prefix="dhsd_cmp_")
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
