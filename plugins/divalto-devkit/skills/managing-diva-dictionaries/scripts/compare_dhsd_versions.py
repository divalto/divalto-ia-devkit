#!/usr/bin/env python3
"""Compare deux versions d'un dictionnaire .dhsd -- COMPATIBILITE BINAIRE.

Repond a une seule question : **quelles tables ont change de taille ?**

A QUOI CA SERT, CONCRETEMENT
----------------------------
Quand un partenaire monte de version, les objets du standard lui arrivent recompiles par
l'editeur -- mais **son specifique**, lui, a ete compile contre l'ANCIEN dictionnaire. Or
un objet compile **memorise la taille** des tables qu'il utilise. Pour toute table dont la
`Taille=` a change, il **doit recompiler** son specifique qui l'utilise, sinon l'execution
leve :

    "enregistrement deja alloue avec la taille X par le module Y"

(Message **rapporte par le RETEX #110**, non reproduit par nos tests : il faut deux
objets compiles contre deux dictionnaires divergents et un runtime pour le declencher.)

La liste produite ici est donc une **liste de travail** : sur un pas de Service Pack
mesure, 16 tables ont change de taille sur 957 -- c'est le perimetre a recompiler, pas
les 957.

CE QUE LE PARTENAIRE NE PEUT PAS FAIRE
--------------------------------------
Il ne peut **pas corriger** un dictionnaire standard : les sources du standard sont
protegees, il ne peut pas les recompiler. Face a une anomalie du standard, sa seule action
est de la **remonter a Divalto**. Son travail a lui porte sur SON specifique.

LE CRITERE : `Taille=`, PAS LE NOMBRE DE CHAMPS
------------------------------------------------
Mesure a l'appui sur un dictionnaire du standard, entre deux versions majeures
(763 tables communes) :

| Cas                                        | Tables |
|--------------------------------------------|--------|
| inchangees (taille ET champs)              | 477    |
| **meme Taille=, nombre de champs different**| **129**|
| Taille= differente                         | 157    |

Compter les champs se trompe **dans les deux sens**, et c'est mesure :

- **faux positifs** -- 129 tables ont gagne des champs a taille CONSTANTE : Divalto ajoute
  regulierement des champs sans changer la taille de l'enregistrement (`artdepo` 31 -> 37
  champs a Taille=500, `bpent` 45 -> 48 a Taille=1400). Un controle par le nombre de
  champs les signalerait a tort ;
- **faux negatifs** -- sur un pas de Service Pack (X.12 -> X.13), **7 des 16 tables** qui
  ont change de taille l'ont fait avec un nombre de champs **identique** (`G5t1` 9 -> 9 a
  Taille 3700 -> 3750, `Gt622` 42 -> 42, `Xq` 16 -> 16, `Xt` 3 -> 3...). Un controle par le
  nombre de champs les manquerait purement et simplement -- et ce sont justement celles
  qui obligent a recompiler.

CE QUE CE SCRIPT NE SIGNALE PAS -- et pourquoi
----------------------------------------------
Les variations de la zone `Filler` ne sont **pas** rapportees. Le `Filler` est la
reserve que **Divalto garde pour lui-meme** : mesure sur les memes fichiers,
**262 tables** l'ont vu diminuer entre X.5 et X.13, le standard y logeant ses
nouveaux champs a taille constante.

Cela ne concerne pas l'integrateur : sa zone d'extension est le container
`U<NomTable>`. Un Service Pack qui mange du Filler est donc transparent pour qui a
respecte la regle.

Les containers `U` sont rapportes a part. La regle, donnee par le distributeur, est
qu'ils **restent stables ou s'agrandissent** : sur un pas de Service Pack la section
est vide, et sur un pas de version majeure les changements observes etaient 1
apparition et des **augmentations** (100 -> 600, 400 -> 800 octets).

  (Reserve : ce comptage a ete fait AVANT le correctif qui cesse de rapporter un simple
  changement de casse du nom de container, et il n'a pas ete rejoue. Le correctif ne
  peut que RETIRER des constats, pas en ajouter.)

Une **reduction** est donc **anormale**. Un seul cas mesure (X.7 -> X.13, un container
passe de 1501 a 1000 octets -- la valeur 1501 etant suspecte, il s'agit vraisemblablement
d'une correction cote editeur). Le script la signale pour ce qu'elle est : une anomalie
a **remonter a Divalto**, pas un travail a faire cote integrateur.

Usage :
    py compare_dhsd_versions.py --from <ancien.dhsd> --to <nouveau.dhsd>
    py compare_dhsd_versions.py --from a.dhsd --to b.dhsd --only-incompatible
    py compare_dhsd_versions.py --from a.dhsd --to b.dhsd --format text

Sortie JSON :
    {
      "from": "...", "to": "...",
      "resume": {"tables_communes": N, "taille_changee": N, "champs_ajoutes_taille_stable": N,
                 "inchangees": N, "tables_ajoutees": N, "tables_supprimees": N,
                 "containers_u_modifies": N},
      "incompatibles": [{"table","taille_avant","taille_apres","champs_avant","champs_apres"}],
      "compatibles_champs_ajoutes": [...],
      "tables_ajoutees": [...], "tables_supprimees": [...],
      "containers_u_modifies": [{"table","avant","apres","nature"}],
      "note_filler": "..."
    }

Exit codes :
    0 = aucune incompatibilite binaire (aucun changement de Taille=)
    1 = au moins une table a change de taille
    2 = erreur (fichier introuvable, illisible)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

ENCODING = "iso-8859-1"

# Format documente d'une ligne de [CHAMPS] (cf. reference/dhsd-5-zones.md) :
#   Nom=<nom>,<position>,<nature>,N,<?>,<taille>,N,<?>
# La taille est en 6e position ; elle est renseignee pour les zones reservees
# (`Filler`, `U<NomTable>`) et vaut 0 pour un champ dont la taille decoule de sa Nature.
_CHAMP_LIGNE = re.compile(r"^Nom=([^,]+),(\d+),[^,]*,[^,]*,[^,]*,(\d+)", re.IGNORECASE)
_NOM_BLOC = re.compile(r"^Nom=([^,]+)", re.IGNORECASE)
_TAILLE = re.compile(r"^Taille=(\d+)", re.IGNORECASE)
_NATURE = re.compile(r"^Nature=(\S+)", re.IGNORECASE)


def _taille_de_nature(nature: str):
    """Taille en octets d'un code Nature. Delegue a nature_to_size.py du meme skill.

    Import par chemin plutot que `from nature_to_size import ...` : les scripts du
    skill sont invocables individuellement, un import nu casserait selon le cwd.
    Si le module est introuvable, on retombe sur la lecture directe du code Nature
    (exact pour les natures alphanumeriques, qui sont le cas des containers `U<X>`).
    """
    try:
        import importlib.util
        chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "nature_to_size.py")
        spec = importlib.util.spec_from_file_location("_nature_to_size", chemin)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.nature_to_size(nature).get("size")
    except Exception:
        return int(nature) if nature.isdigit() else None


def lire(path: str):
    """Lit un `.dhsd`. Retourne `(tables, natures)`.

    - `tables` : {nom_minuscule: {"nom", "taille", "champs": [(nom, pos, taille_ligne)]}}
      depuis les blocs `[TABLE]` + `[CHAMPS]` (placement physique).
    - `natures` : {nom_champ_minuscule: taille_octets} depuis les blocs `[CHAMP]`
      (declarations globales). Necessaire pour la capacite des containers `U<X>`, dont
      la taille N'EST PAS dans la ligne de placement (cf. container_u).
    """
    tables: dict = {}
    natures: dict = {}
    section = None
    nom = None
    taille = None
    champs: list = []
    champ_nom = None

    def cloturer():
        if nom:
            tables[nom.lower()] = {"nom": nom, "taille": taille, "champs": list(champs)}

    with open(path, "r", encoding=ENCODING, errors="replace") as fh:
        for ligne in fh:
            s = ligne.strip()
            if s.startswith("["):
                if section == "CHAMPS":
                    cloturer()
                section = s.strip("[]").upper()
                if section == "TABLE":
                    nom, taille, champs = None, None, []
                elif section == "CHAMP":
                    champ_nom = None
                continue
            if section == "CHAMP":
                m = _NOM_BLOC.match(s)
                if m and champ_nom is None:
                    champ_nom = m.group(1)
                m = _NATURE.match(s)
                if m and champ_nom:
                    natures[champ_nom.lower()] = _taille_de_nature(m.group(1))
            elif section == "TABLE":
                m = _NOM_BLOC.match(s)
                if m and nom is None:
                    nom = m.group(1)
                m = _TAILLE.match(s)
                if m:
                    taille = int(m.group(1))
            elif section == "CHAMPS":
                m = _CHAMP_LIGNE.match(s)
                if m:
                    champs.append((m.group(1), int(m.group(2)), int(m.group(3))))
    if section == "CHAMPS":
        cloturer()
    return tables, natures


def container_u(table_cle: str, info: dict, natures: dict):
    """Le container `U<NomTable>` de la table : `(nom, capacite_octets)` ou None.

    C'est la zone d'extension reservee au distributeur/integrateur -- le SEUL point
    d'ancrage legitime d'un champ custom (cf. reference/dhsd-surcharge-pattern.md).

    ATTENTION -- deux conventions coexistent dans un meme `.dhsd`, et les confondre
    rend la comparaison VIDE DE SENS :

    - le `Filler` porte sa taille EN LIGNE, 6e position du `[CHAMPS]`
      (`Nom=Filler,2097,2,N,0,404,N,1` = 404 octets) ;
    - un container `U<X>` a `0` a cette meme position : sa capacite est sa **Nature**,
      declaree une seule fois dans le bloc `[CHAMP]` global
      (`Nom=UArt` / `Nature=1500` = 1500 octets reserves).

    Lire la 6e position pour un container revient donc a comparer des zeros -- ce que
    faisait la premiere version de ce script, qui concluait « aucun container modifie »
    sur n'importe quelle paire de fichiers.
    """
    cible = "u" + table_cle
    for nom, _pos, _taille_ligne in info["champs"]:
        if nom.lower() == cible:
            return (nom, natures.get(nom.lower()))
    return None


def comparer(avant: dict, apres: dict, nat_avant: dict, nat_apres: dict) -> dict:
    communes = sorted(set(avant) & set(apres))
    incompatibles, compat_champs, inchangees, u_modifies = [], [], [], []

    for cle in communes:
        a, b = avant[cle], apres[cle]
        na, nb = len(a["champs"]), len(b["champs"])
        if a["taille"] != b["taille"]:
            incompatibles.append({
                "table": b["nom"],
                "taille_avant": a["taille"], "taille_apres": b["taille"],
                "champs_avant": na, "champs_apres": nb,
            })
        elif na != nb:
            compat_champs.append({
                "table": b["nom"], "taille": b["taille"],
                "champs_avant": na, "champs_apres": nb,
            })
        else:
            inchangees.append(b["nom"])

        ua, ub = container_u(cle, a, nat_avant), container_u(cle, b, nat_apres)
        # Comparer la PRESENCE et la CAPACITE, jamais le tuple : un simple
        # changement de casse du nom (UArt -> UART) n'est pas un changement de
        # capacite et serait rapporte 'capacite augmentee 1500 -> 1500'
        # (faux positif attrape par tests/, cas 17).
        if ((ua is None) != (ub is None)
                or (ua is not None and ub is not None and ua[1] != ub[1])):
            u_modifies.append({
                "table": b["nom"],
                "avant": None if ua is None else {"nom": ua[0], "taille": ua[1]},
                "apres": None if ub is None else {"nom": ub[0], "taille": ub[1]},
                "nature": _nature_du_changement(ua, ub),
            })

    return {
        "resume": {
            "tables_communes": len(communes),
            "taille_changee": len(incompatibles),
            "champs_ajoutes_taille_stable": len(compat_champs),
            "inchangees": len(inchangees),
            "tables_ajoutees": len(set(apres) - set(avant)),
            "tables_supprimees": len(set(avant) - set(apres)),
            "containers_u_modifies": len(u_modifies),
        },
        "incompatibles": sorted(incompatibles, key=lambda d: d["table"].lower()),
        "compatibles_champs_ajoutes": sorted(compat_champs, key=lambda d: d["table"].lower()),
        "tables_ajoutees": sorted(apres[c]["nom"] for c in set(apres) - set(avant)),
        "tables_supprimees": sorted(avant[c]["nom"] for c in set(avant) - set(apres)),
        "containers_u_modifies": sorted(u_modifies, key=lambda d: d["table"].lower()),
        "action": (
            "Recompiler le specifique qui utilise les tables listees dans `incompatibles` : "
            "un objet compile memorise la taille des tables, et un objet reste compile "
            "contre l'ancienne taille leve a l'execution \"enregistrement deja alloue avec "
            "la taille X par le module Y\". Les anomalies de `containers_u_modifies` sont a "
            "remonter a Divalto : un dictionnaire standard n'est pas corrigeable cote "
            "partenaire (sources protegees, non recompilables)."
        ),
        "note_filler": (
            "Les variations de la zone Filler ne sont volontairement PAS rapportees : le "
            "Filler est la reserve de Divalto (262 tables l'ont vu diminuer entre X.5 et "
            "X.13, l'editeur y logeant ses nouveaux champs a taille constante), pas la zone "
            "d'extension de l'integrateur. Celle-ci est le container U<NomTable>, dont la "
            "regle est de rester stable ou de s'agrandir. Un Service Pack qui consomme du "
            "Filler est donc transparent pour qui a respecte la regle."
        ),
    }


def _nature_du_changement(ua, ub) -> str:
    """Qualifie un changement de container. La capacite peut etre inconnue (None)
    si la Nature du container n'a pas ete trouvee dans les blocs [CHAMP] : on le dit
    plutot que de comparer des None."""
    if ub is None:
        return ("container DISPARU -- ANOMALIE a remonter a Divalto : les champs "
                "custom perdent leur point d'ancrage")
    if ua is None:
        return "container apparu -- la table devient surchargeable (sans risque)"
    if ua[1] is None or ub[1] is None:
        return "capacite non determinee (Nature absente des blocs [CHAMP])"
    if ub[1] < ua[1]:
        return ("capacite REDUITE %d -> %d octets -- ANOMALIE : un container U reste "
                "stable ou s'agrandit. A remonter a Divalto." % (ua[1], ub[1]))
    return "capacite augmentee %d -> %d octets" % (ua[1], ub[1])


def rendu_texte(res: dict) -> str:
    r = res["resume"]
    out = [
        "=" * 72,
        "Comparaison de dictionnaires -- compatibilite binaire",
        "=" * 72,
        f"  de  : {res['from']}",
        f"  vers: {res['to']}",
        "",
        f"  tables communes ............................. {r['tables_communes']}",
        f"  TAILLE CHANGEE (incompatibilite binaire) ... {r['taille_changee']}",
        f"  champs ajoutes, Taille= stable (compatible)  {r['champs_ajoutes_taille_stable']}",
        f"  inchangees ................................. {r['inchangees']}",
        f"  tables ajoutees / supprimees ............... {r['tables_ajoutees']} / {r['tables_supprimees']}",
        f"  containers U modifies ...................... {r['containers_u_modifies']}",
    ]
    if res["incompatibles"]:
        out += ["", "--- Tables ayant change de TAILLE (a verifier) ---"]
        for d in res["incompatibles"][:40]:
            out.append("  %-26s Taille %6s -> %-6s  champs %d -> %d"
                       % (d["table"], d["taille_avant"], d["taille_apres"],
                          d["champs_avant"], d["champs_apres"]))
        if len(res["incompatibles"]) > 40:
            out.append("  ... +%d autres" % (len(res["incompatibles"]) - 40))
    if res["containers_u_modifies"]:
        out += ["", "--- Containers U modifies (ATTENTION : ne devrait pas arriver) ---"]
        for d in res["containers_u_modifies"][:20]:
            out.append("  %-26s %s" % (d["table"], d["nature"]))
    out += [""]
    if res["incompatibles"]:
        out += ["A FAIRE : recompiler le specifique qui utilise les tables ci-dessus. Un "
                "objet compile memorise la taille des tables ; laisse tel quel, il leve a "
                "l'execution \"enregistrement deja alloue avec la taille X par le module Y\".",
                ""]
    if res["containers_u_modifies"]:
        out += ["A REMONTER A DIVALTO : un dictionnaire standard n'est pas corrigeable cote "
                "partenaire (sources protegees, non recompilables).", ""]
    out += ["Note : " + res["note_filler"]]
    return "\n".join(out)


def main() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Compare deux .dhsd sur le critere de compatibilite binaire (Taille=).")
    ap.add_argument("--from", dest="avant", required=True,
                    help="Dictionnaire de depart (version ancienne / standard d'origine).")
    ap.add_argument("--to", dest="apres", required=True,
                    help="Dictionnaire d'arrivee (version cible / nouveau Service Pack).")
    ap.add_argument("--only-incompatible", action="store_true",
                    help="N'inclure que les tables ayant change de Taille= (sortie compacte).")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    args = ap.parse_args()

    for chemin in (args.avant, args.apres):
        if not os.path.isfile(chemin):
            print(f"Erreur : fichier introuvable : {chemin}", file=sys.stderr)
            return 2
    try:
        avant, nat_avant = lire(args.avant)
        apres, nat_apres = lire(args.apres)
    except OSError as e:
        print(f"Erreur lecture : {e}", file=sys.stderr)
        return 2

    res = comparer(avant, apres, nat_avant, nat_apres)
    res = {"from": args.avant, "to": args.apres, **res}
    if args.only_incompatible:
        for cle in ("compatibles_champs_ajoutes", "tables_ajoutees", "tables_supprimees"):
            res[cle] = []

    if args.format == "text":
        print(rendu_texte(res))
    else:
        json.dump(res, sys.stdout, indent=2, ensure_ascii=False)
        print()
    return 1 if res["resume"]["taille_changee"] else 0


if __name__ == "__main__":
    sys.exit(main())
