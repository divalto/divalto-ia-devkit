#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les deux heuristiques de E4, sur des entrees ciblees.

`test_detecteurs.py` mesure les detecteurs sur le cas livre complet. Cette suite-la
cible chaque regle de E4 separement, parce que E4 vient d'etre reecrit et que ses deux
regressions possibles ne se voient pas sur le cas d'exemple :

  - H1 affirmait `Mt -> 8,N` et `Qte -> 8,N`, alors que les deux sources qu'elle
    s'attribue -- `taxonomie-suffixes.md` et `suggest_nature.py` de
    `managing-diva-dictionaries` -- donnent `16,D0` a 65 % et `12,D2` a 72 %, la bande
    « proposer + demander confirmation ». Un livrable declarant la BONNE Nature etait
    signale comme contradiction. Les deux regles ont ete retirees ; les cas 1 et 2
    gardent ce retrait.
  - H5 lisait la colonne « Prefixe code » (`GT_`) et la comparait a `gttcli` : ca ne
    concordait que par accident de troncature. Elle lit desormais « Prefixe module »
    (`gtt`). Les cas 5 et 6 gardent la colonne.

Les IR de cette suite sont construits a la main, et c'est assume : une regle se teste sur
l'entree minimale qui la declenche. Le cas livre complet est couvert par l'autre suite.

Une limite de FORME est gardee ici aussi, parce qu'elle m'a fait ecrire un cas qui ne
pouvait pas tomber : H1 extrait le suffixe en FIN de nom. `LotQte` porte `Qte`, mais
`QteCde` porte `Cde`. Un champ dont le token type est en tete echappe a H1.

Lancer :
    py .claude/skills/reviewing-erp-doc/tests/test_e4_heuristiques.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DETECTEUR = os.path.join(HERE, "..", "scripts", "detect_doc_contradictions.py")

CAS = []


def cas(titre):
    def deco(fn):
        CAS.append((titre, fn))
        return fn
    return deco


def detecter(entites, module="DAV"):
    """Lance E4 sur un IR construit a la main. Rend la liste des items."""
    d = tempfile.mkdtemp(prefix="e4_")
    ir = os.path.join(d, "ir.json")
    out = os.path.join(d, "e4.json")
    with open(ir, "w", encoding="utf-8") as f:
        json.dump({"module": {"code": module}, "entities": entites}, f)
    r = subprocess.run([sys.executable, DETECTEUR, "--ir", ir, "--out", out],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    assert r.returncode == 0, "E4 sort en %d : %s" % (r.returncode, (r.stderr or "")[:200])
    with open(out, encoding="utf-8") as f:
        return json.load(f)["items"]


def champs(*paires):
    return [{"code": "CLI", "module": "DAV", "affirmations": [],
             "structures": {"fields": [{"name": n, "nature": v} for n, v in paires]}}]


def citations(*refs, module="DAV"):
    # Le module de l'ENTITE est prioritaire sur celui de l'IR : `check_h5_domain_prefix`
    # fait `entity.get("module") or ir_module_code`. Mon premier cas 7 changeait le
    # module de l'IR en laissant `DAV` sur l'entite -- il ne pouvait pas tomber.
    return [{"code": "CLI", "module": module,
             "affirmations": [{"yaml_path": "business.role", "citations": list(refs)}],
             "structures": {"fields": []}}]


# ======================================================================================
@cas("1. H1 -- un montant en 16,D0 ne se signale PLUS")
def cas1():
    # La regle retiree affirmait `8,N`. `taxonomie-suffixes.md` donne `16,D0` a 65 % :
    # une correlation moderee, qu'on ne transforme pas en contradiction.
    items = detecter(champs(("AmoMt", "16,D0")))
    assert items == [], "AmoMt en 16,D0 est signale a tort : %s" % items
    return "la Nature que la source donne passe"


@cas("2. H1 -- une quantite en 12,D2 ne se signale PLUS")
def cas2():
    items = detecter(champs(("LotQte", "12,D2")))
    assert items == [], "LotQte en 12,D2 est signale a tort : %s" % items
    return "idem pour Qte a 72 %"


@cas("3. H1 -- une date qui n'est pas D8 se signale")
def cas3():
    # Temoin : sans lui, les deux cas precedents passeraient aussi avec une table vide.
    items = detecter(champs(("CdeDt", "C8")))
    assert len(items) == 1, "attendu 1 item, obtenu %d : %s" % (len(items), items)
    assert "CdeDt" in items[0]["title"] and items[0]["severity"] == "warning", items[0]
    return "Dt attend D8, et le dit"


@cas("4. H1 -- le suffixe se lit en FIN de nom, pas en tete")
def cas4():
    # Limite de forme, mesuree : `QteCde` finit par `Cde`, donc H1 ne le regarde pas
    # comme une quantite. Ce cas garde la portee reelle de l'heuristique -- sans lui,
    # un futur elargissement du motif passerait inapercu.
    # `DtCde` porte `Dt` EN TETE, et `Dt` est dans la table : lu en fin il donne
    # `Cde` (rien), lu en tete il donne `Dt` (signale). C'est ce contraste qui rend
    # le cas discriminant -- ma premiere version utilisait `QteCde` et `MtHT`, dont
    # les deux suffixes ont ete RETIRES de la table : elle passait quelle que soit
    # l'extremite lue.
    items = detecter(champs(("DtCde", "C20"), ("QteCde", "C20")))
    assert items == [], "un token type EN TETE ne devrait pas declencher H1 : %s" % items
    return "portee de l'heuristique gardee"


@cas("5. H5 -- un prefixe de fichier incoherent avec le domaine se signale")
def cas5():
    # `DAV` attend le prefixe module `gtt`. Un fichier `rtt*` vient d'un autre domaine.
    items = detecter(citations("Rttcli.dhop:44"))
    assert len(items) == 1, "attendu 1 item, obtenu %d : %s" % (len(items), items)
    assert "Rttcli.dhop" in items[0]["title"], items[0]
    assert "gtt" in items[0]["excerpt_source"], items[0]["excerpt_source"]
    return "rtt pour DAV est signale, et gtt est nomme"


@cas("6. H5 -- le bon prefixe ne se signale pas")
def cas6():
    # C'est la colonne « Prefixe module » (`gtt`) qui compte. L'ancienne version lisait
    # « Prefixe code » (`GT_`) et ne concordait que par troncature.
    items = detecter(citations("Gttcli.dhop:12"))
    assert items == [], "le bon prefixe est signale a tort : %s" % items
    return "gtt pour DAV passe"


@cas("7. H5 -- un domaine hors table reste muet")
def cas7():
    # Regle de precedence du skill : mieux vaut une detection muette qu'un faux positif.
    # Le module se pose sur l'ENTITE -- c'est lui que H5 lit en premier.
    items = detecter(citations("Xxxcli.dhop:12", module="DOMAINE_INCONNU"))
    assert items == [], "H5 parle sur un domaine qu'elle ne connait pas : %s" % items
    return "silence plutot que faux positif"


@cas("7bis. H5 -- le module de l'ENTITE est prioritaire sur celui de l'IR")
def cas7bis():
    # Decouvert en ecrivant le cas 7, qui ne pouvait pas tomber : changer le module de
    # l'IR sans changer celui de l'entite ne change rien. La precedence est une regle
    # du detecteur, elle merite son cas.
    items = detecter(citations("Rttcli.dhop:44", module="DAV"), module="DOMAINE_INCONNU")
    assert len(items) == 1, \
        "le module de l'IR a pris le pas sur celui de l'entite : %s" % items
    return "entity.module d'abord, ir.module en secours"


@cas("8. Le source_ref des items nomme une page livree")
def cas8():
    items = detecter(champs(("CdeDt", "C8"))) + detecter(citations("Rttcli.dhop:44"))
    assert len(items) == 2, items
    for i in items:
        ref = i.get("source_ref") or ""
        assert ref, "item sans source_ref : %s" % i
        for interdit in ("DICTIONNAIRE-DHSD", "MODULES-ERP", "(interne)"):
            assert interdit not in ref, "source_ref interne : %r" % ref
    return "H1 et H5 citent des pages que le partenaire a"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 92)
    print("reviewing-erp-doc -- heuristiques E4, %d cas" % len(CAS))
    print("=" * 92)
    ok = 0
    for titre, fn in CAS:
        try:
            detail = fn()
            print("  OK    %-58s %s" % (titre[:58], detail))
            ok += 1
        except AssertionError as e:
            print("  ECHEC %-58s %s" % (titre[:58], str(e)[:180]))
        except Exception as e:
            print("  ERREUR %-57s %s: %s" % (titre[:57], type(e).__name__,
                                             str(e)[:150]))
    print("\n  %d/%d" % (ok, len(CAS)))
    sys.exit(0 if ok == len(CAS) else 1)


if __name__ == "__main__":
    main()
