#!/usr/bin/env python3
"""Propose une Nature DIVA ET une cle etrangere (FK) a partir d'un nom de champ
[CHAMP], via la taxonomie de suffixes observee dans le corpus X.13.

Sources :
- Taxonomie Nature : `reference/taxonomie-suffixes.md` + `docs/CONVENTIONS.md` (batch 16, 2026-04-17)
- Taxonomie FK : `docs/CONVENTIONS.md` section "Suffixes foreign key" + `docs/FK-ZOOM-BINDING.md`
  + `docs/ZOOMS-STANDARDS-CATALOGUE.md` (batch 18 bis, 2026-04-20)

Usage:
    py scripts/suggest_nature.py --name UserCrDh
    -> {"name": "UserCrDh", "nature": "DH", "confidence": 0.98, "rule": "suffix:Dh", "fk_target": null}

    py scripts/suggest_nature.py --name RacPays
    -> {"name": "RacPays", "nature": ..., "fk_target": {"target": "T013", "kind": "t-table",
        "confidence": 1.0, "zoom_num": 9053, "module_dhop": "Gttmchkt013.dhop",
        "find_fn": "Find_T013", "get_lib_fn": "Get_T013_Lib"}}

    py scripts/suggest_nature.py --stdin
    ["AnnulFl", "CdeDt", "Mt", "ClientCod"]
    -> [...]

Le script utilise d'abord la partie **suffixe** PascalCase du nom, puis la
partie **prefixe** si le suffixe n'est pas discriminant.

Sortie JSON: { name, nature, confidence, rule, alternatives, note, fk_target }
- confidence: 0..1 -> taux observe (>0.85 = fiable, >0.6 = probable, sinon demande)
- alternatives: liste des autres Natures frequentes pour ce suffixe
- note: message pour le LLM (ex: "taille variable -- demander au collaborateur")
- fk_target: null si aucune FK detectee, sinon dict avec les 7 champs listes ci-dessus

Seuil d'inclusion FK : suffixes fiables >= 90 % (taxonomie table C de
ZOOMS-STANDARDS-CATALOGUE.md). Les suffixes ambigus (Cod, Lib, Ref) retournent
fk_target=null avec une note d'ambiguite.
"""
from __future__ import annotations

import argparse
import json
import re
import sys


# Taxonomie : suffixe -> (nature_default, confidence, alternatives, note)
# Source : output/dhsd_suffix_nature.json (batch 16, 2026-04-17)
# Les chiffres viennent de la mesure sur 24 196 champs de 21 dicos X.13.
SUFFIX_TAXONOMY = {
    "Dh": {
        "nature": "DH", "confidence": 0.98,
        "alternatives": ["BYTES(14)"],
        "note": "Timestamp (date+heure 14 octets). Correlation ~98 %.",
    },
    "Flg": {
        "nature": "1,0", "confidence": 0.99,
        "alternatives": [],
        "note": "Flag booleen (1 octet entier). Correlation ~99 %.",
    },
    "Fl": {
        "nature": "1,0", "confidence": 0.95,
        "alternatives": ["BYTES(1)"],
        "note": "Flag booleen. Correlation ~95 %.",
    },
    "Dt": {
        "nature": "D8", "confidence": 0.93,
        "alternatives": ["BYTES(8)"],
        "note": "Date AAAAMMJJ (8 octets). Correlation ~93 %.",
    },
    "He": {
        "nature": "H6", "confidence": 0.77,
        "alternatives": ["BYTES(6)"],
        "note": "Heure HHMMSS (6 octets). Correlation ~77 % (+20 % BYTES(6) equivalent).",
    },
    "Typ": {
        "nature": "1,0", "confidence": 0.85,
        "alternatives": ["2,0", "BYTES(1)"],
        "note": "Type / classification (entier court 1-2 octets). Correlation ~85 %.",
    },
    "Qte": {
        "nature": "12,D2", "confidence": 0.72,
        "alternatives": ["13,D2", "15,D2", "12,D3"],
        "note": "Quantite decimale signee (12 chiffres, 2 decimales). Correlation ~72 %.",
    },
    "Mt": {
        "nature": "16,D0", "confidence": 0.65,
        "alternatives": ["13,D0", "12,D0", "17,D6"],
        "note": "Montant signe, souvent sans decimale stockee (gestion des decimales via la devise). Correlation ~65 % sur 16,D0.",
    },
    "Nb": {
        "nature": "3,0", "confidence": 0.50,
        "alternatives": ["2,0", "4,0", "5,0", "6,0", "8,0"],
        "note": "Nombre entier court -- demander la taille (1-8 chiffres).",
    },
    "Cod": {
        "nature": None, "confidence": 0.30,
        "alternatives": ["BYTES(1)", "BYTES(4)", "BYTES(5)", "BYTES(8)", "BYTES(20)"],
        "note": "Code de reference -- DEMANDER la taille (mnemonique 1 char, code court 4-8, code long 20).",
    },
    "No": {
        "nature": None, "confidence": 0.18,
        "alternatives": ["NUM_INT(8)", "NUM_INT(10)", "NUM_INT(14)", "BYTES(20)"],
        "note": "Numero sequentiel -- DEMANDER la taille (numerique 2-14 chiffres ou chaine 10-20).",
    },
    "Ref": {
        "nature": "BYTES(25)", "confidence": 0.26,
        "alternatives": ["BYTES(33)", "BYTES(49)", "BYTES(40)"],
        "note": "Reference -- tailles courantes 25 (courte), 33 (complete), 49 ou 40 (longue).",
    },
    "Lib": {
        "nature": "BYTES(40)", "confidence": 0.35,
        "alternatives": ["BYTES(20)", "BYTES(80)", "BYTES(30)", "BYTES(155)"],
        "note": "Libelle texte -- DEMANDER la longueur (20 abrege, 40 moyen, 80 long, 155 etendu).",
    },
    "Msk": {
        "nature": "BYTES(20)", "confidence": 0.25,
        "alternatives": ["BYTES(8)", "BYTES(25)", "BYTES(41)"],
        "note": "Masque (droits / affichage) -- DEMANDER la taille.",
    },
    "Cpt": {
        "nature": "BYTES(20)", "confidence": 0.46,
        "alternatives": ["BYTES(8)", "BYTES(11)"],
        "note": "Numero de compte comptable (generalement 20 char alphanumerique).",
    },
    "Dev": {
        "nature": "BYTES(4)", "confidence": 0.36,
        "alternatives": ["NUM_INT(16)", "NUM_INT(13)", "BYTES(3)"],
        "note": "Devise -- 4 char (code devise) OU montant en devise (mettre Mt...Dev).",
    },
    "Ori": {
        "nature": None, "confidence": 0.22,
        "alternatives": ["2,0", "4,0", "5,0", "BYTES(20)"],
        "note": "Valeur originelle -- taille depend du champ source (copier la Nature du champ de base).",
    },
    "Tot": {
        "nature": "16,D0", "confidence": 0.17,
        "alternatives": ["15,D0", "12,D3"],
        "note": "Total cumule -- numerique decimal, souvent signe. Demander la taille.",
    },
    "Tb": {
        "nature": None, "confidence": 0.0,
        "alternatives": [],
        "note": "ATTENTION : `Tb` designe un TABLEAU REPETE (Nature `X*N`). Ex: `AdresseTb` = `50*10` (10 adresses de 50 car). Ce n'est PAS une cle vers table externe (utiliser `Cod` pour ca). DEMANDER la taille unitaire et le nombre de repetitions.",
    },
}

# Prefixe (premier token PascalCase) -> hint sur la Nature
PREFIX_TAXONOMY = {
    "User": {
        "nature": None, "confidence": 0.0,
        "alternatives": [],
        "note": "Audit utilisateur. Se decline en 4 formes : `UserCr`/`UserMo` = BYTES(20) code user, `UserCrDh`/`UserMoDh` = DH, `UserCrDt`/`UserMoDt` = D8, `UserCrOri`/`UserMoOri` = NUM_INT(2).",
    },
    "Ce": {
        "nature": "BYTES(1)", "confidence": 0.96,
        "alternatives": ["NUM_INT(1)"],
        "note": "Composante code enregistrement (1 octet). Noms canoniques Ce1..CeA.",
    },
    "Full": {
        "nature": "BYTES(20)", "confidence": 0.71,
        "alternatives": ["BYTES(33)"],
        "note": "Version complete d'un code court (20 ou 33 octets).",
    },
    "Pref": {
        "nature": "BYTES(10)", "confidence": 0.92,
        "alternatives": [],
        "note": "Prefixe metier (10 octets). Ex: PrefPiNo = prefixe numero piece.",
    },
    "Sref": {
        "nature": "BYTES(8)", "confidence": 0.65,
        "alternatives": ["BYTES(16)"],
        "note": "Sous-reference (8 ou 16 octets).",
    },
    "U": {
        "nature": None, "confidence": 0.0,
        "alternatives": ["BYTES(100)", "BYTES(200)", "BYTES(300)", "BYTES(500)"],
        "note": "RESERVE DISTRIBUTEUR (U<NomTable>). Taille libre selon le besoin de reserve, tailles courantes 100/200/300/500. Un seul par table.",
    },
    "Adr": {
        "nature": "BYTES(50)", "confidence": 0.15,
        "alternatives": ["BYTES(8)", "BYTES(500)", "L"],
        "note": "Adresse -- DEMANDER (50 car par defaut pour adresse courte, 500 pour longue, L pour texte long).",
    },
}

# Taxonomie FK : suffixe -> cible FK (dominante, fiabilite >= 90 %)
# Source : output/fk_pattern_stats.json (scan ERP X.13, 2026-04-20)
# Documente dans docs/ZOOMS-STANDARDS-CATALOGUE.md table C
SUFFIX_FK_TARGET = {
    # T-tables parametriques (dict GTFDD, module Gttmchkt<NNN>.dhop)
    "Pay": {"target": "T013", "kind": "t-table", "confidence": 1.00, "zoom_num": 9053},
    "Pays": {"target": "T013", "kind": "t-table", "confidence": 1.00, "zoom_num": 9053},
    "Dev": {"target": "T007", "kind": "t-table", "confidence": 0.93, "zoom_num": 9047},
    "Devise": {"target": "T007", "kind": "t-table", "confidence": 0.93, "zoom_num": 9047},
    "Depo": {"target": "T017", "kind": "t-table", "confidence": 0.97, "zoom_num": 9057},
    "Cpostal": {"target": "T057", "kind": "t-table", "confidence": 1.00, "zoom_num": None},
    "Sref1": {"target": "T019", "kind": "t-table", "confidence": 1.00, "zoom_num": None},
    "Sref2": {"target": "T019", "kind": "t-table", "confidence": 1.00, "zoom_num": None},
    # Comptes comptables (dict CCFDD, framework Compta)
    "Cpt": {"target": "C3", "kind": "c-compta", "confidence": 0.97, "zoom_num": 9055},
    "Col": {"target": "C3", "kind": "c-compta", "confidence": 1.00, "zoom_num": 9055},
    "Axe": {"target": "C5", "kind": "c-compta", "confidence": 1.00, "zoom_num": 9056},
    "Jnl": {"target": "C4", "kind": "c-compta", "confidence": 0.89, "zoom_num": None},
    # Entites metier majeures (module Gttmchk<abrege>.dhop)
    "Dos": {"target": "SOC", "kind": "entity", "confidence": 1.00, "zoom_num": 9020},
    "Ind": {"target": "ART", "kind": "entity", "confidence": 0.90, "zoom_num": 9000},
    "Affaire": {"target": "PRJAP", "kind": "entity", "confidence": 0.91, "zoom_num": None},
    # Configs applicatives
    "Caisse": {"target": "PAR", "kind": "config", "confidence": 1.00, "zoom_num": None},
    "Contact": {"target": "T2", "kind": "config", "confidence": 1.00, "zoom_num": None},
}

# Suffixes ambigus (fiabilite < 90 %) : pas de proposition auto, note d'ambiguite
SUFFIX_FK_AMBIGUOUS = {
    "Cod": "Code generique -- multiples cibles possibles (T<NNN>, entites). DEMANDER le contexte.",
    "Lib": "Libelle texte -- n'est pas une cle etrangere (sortie de validation FK, pas entree).",
    "Ref": "Reference -- souvent ART mais fiabilite 43 %. DEMANDER la cible (article ? projet ? ligne ?).",
    "No": "Numero -- souvent identifiant interne, rarement FK. DEMANDER si le champ pointe vers une entite.",
    "Fam": "Famille -- multiples cibles metier (GRTEFA, T085, ...). DEMANDER le contexte metier.",
    "Etb": "Etablissement -- cibles ETS/CETS selon domaine. Fiabilite 73 %, verifier.",
    "Fou": "Fournisseur -- majoritairement FOU mais 71 % seulement. Verifier le contexte.",
    "Individu": "Individu -- polymorphique (PINDIVIDU, CLI, FOU, PRO). DEMANDER le type de tiers.",
}


def enrich_fk_target(fk: dict) -> dict:
    """Enrichit un mapping {target, kind, confidence, zoom_num} avec module + fonctions."""
    target = fk["target"]
    return {
        **fk,
        "module_dhop": f"Gttmchk{target.lower()}.dhop",
        "find_fn": f"Find_{target}",
        "get_lib_fn": f"Get_{target}_Lib",
    }


def suggest_fk_target(name: str) -> tuple[dict | None, str | None]:
    """Retourne (fk_target_dict_ou_None, note_ambiguite_ou_None).

    Utilise le dernier token PascalCase du nom comme suffixe.
    """
    toks = tokenize_pascal(name)
    if not toks:
        return None, None
    last = toks[-1]
    if last in SUFFIX_FK_TARGET:
        return enrich_fk_target(SUFFIX_FK_TARGET[last]), None
    if last in SUFFIX_FK_AMBIGUOUS:
        return None, SUFFIX_FK_AMBIGUOUS[last]
    return None, None


# Noms canoniques : override direct (priorite sur suffixes/prefixes)
CANONICAL = {
    "Dos": ("BYTES(8)", 1.0, "Dossier multi-tenant (8 octets)."),
    "Ce1": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce2": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce3": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce4": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce5": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce6": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce7": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce8": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce9": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "CeA": ("BYTES(1)", 1.0, "Composante code enregistrement."),
    "Ce": ("BYTES(10)", 1.0, "Code enregistrement composite (Comptabilite)."),
    "UserCr": ("BYTES(20)", 1.0, "Code user createur (socle audit canonique)."),
    "UserMo": ("BYTES(20)", 1.0, "Code user modificateur (socle audit canonique)."),
    "UserCrDh": ("DH", 1.0, "Timestamp creation (socle audit canonique)."),
    "UserMoDh": ("DH", 1.0, "Timestamp modification (socle audit canonique)."),
    "UserCrDt": ("D8", 1.0, "Date creation (variante ancienne)."),
    "UserMoDt": ("D8", 1.0, "Date modification (variante ancienne)."),
    "Filler": (None, 1.0, "Mot-cle special : bourrage, pas de declaration [CHAMP]."),
}


def tokenize_pascal(name: str) -> list[str]:
    """Segmente 'UserCrDh' en ['User', 'Cr', 'Dh']."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    s = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", s)
    s = re.sub(r"([A-Z]+)(?=[A-Z][a-z])", r"\1 ", s)
    return [t for t in s.split() if t]


def suggest_nature(name: str) -> dict:
    """Retourne la proposition de Nature + FK potentielle pour un nom de champ."""
    result = {
        "name": name,
        "nature": None,
        "confidence": 0.0,
        "rule": None,
        "alternatives": [],
        "note": None,
        "fk_target": None,
        "fk_note": None,
    }

    # Detection FK en paralelle (independante de la Nature)
    fk, fk_note = suggest_fk_target(name)
    if fk:
        result["fk_target"] = fk
    if fk_note:
        result["fk_note"] = fk_note

    # 1. Check canonical name first
    if name in CANONICAL:
        nat, conf, note = CANONICAL[name]
        result.update({
            "nature": nat, "confidence": conf, "rule": f"canonical:{name}",
            "note": note,
        })
        return result

    # 2. U<Table> pattern (reserve distributeur)
    if re.match(r"^U[A-Z][a-z]", name):
        result.update({
            "nature": "BYTES(200)", "confidence": 0.5,
            "rule": "pattern:U<Table>",
            "alternatives": ["BYTES(100)", "BYTES(300)", "BYTES(500)"],
            "note": f"Reserve distributeur pour table '{name[1:]}'. Taille libre (100/200/300/500 courantes). Obligatoire sur tables metier principales.",
        })
        return result

    # 3. Suffix match (dernier token PascalCase)
    toks = tokenize_pascal(name)
    if toks:
        last = toks[-1]
        if last in SUFFIX_TAXONOMY:
            s = SUFFIX_TAXONOMY[last]
            result.update({
                "nature": s["nature"],
                "confidence": s["confidence"],
                "rule": f"suffix:{last}",
                "alternatives": s["alternatives"],
                "note": s["note"],
            })
            return result

        first = toks[0]
        if first in PREFIX_TAXONOMY:
            p = PREFIX_TAXONOMY[first]
            result.update({
                "nature": p["nature"],
                "confidence": p["confidence"],
                "rule": f"prefix:{first}",
                "alternatives": p["alternatives"],
                "note": p["note"],
            })
            return result

    # 4. Fallback
    result["note"] = (
        "Aucun suffixe/prefixe canonique reconnu. DEMANDER la Nature au collaborateur. "
        "Voir docs/CONVENTIONS.md tableau 'Suffixes typés sur les noms de champ' pour les conventions."
    )
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--name", help="Nom d'un champ PascalCase")
    ap.add_argument("--stdin", action="store_true", help="Lire liste JSON depuis stdin")
    args = ap.parse_args()

    if args.stdin:
        data = json.load(sys.stdin)
        if not isinstance(data, list):
            print("Erreur: stdin doit etre une liste JSON", file=sys.stderr)
            sys.exit(1)
        results = [suggest_nature(n) for n in data]
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.name:
        result = suggest_nature(args.name)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
