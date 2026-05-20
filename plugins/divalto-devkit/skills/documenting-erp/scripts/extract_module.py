#!/usr/bin/env python3
"""extract_module.py -- Cree l'identite d'un module ERP.

Les parametres (bases, entities, prefix, label) sont fournis explicitement
en CLI par le collaborateur au CP1. Le skill consulte
`reference/modules-erp-summary.md` pour rappel du mapping module/prefixe/dico
des modules standards.

Produit un YAML partiel conforme a schemas/module.yaml.

Usage :
  py extract_module.py --module DAV --prefix GTF --label "Achat-Vente" \\
     --bases GTFDOS,GTFPCF,GTFAT --entities CLI,FOU,ART \\
     --output {REPERTOIRE_SORTIE}/doc-erp/DAV/module.partial.yaml
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERREUR : pyyaml requis. Installer : py -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def split_csv(s: str) -> list:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def build_module(args) -> dict:
    return {
        "kind": "module",
        "code": args.module,
        "label": args.label or args.module,
        "prefix": args.prefix,
        "domain": args.domain or "[A VERIFIER]",
        "status": "draft",
        "description": "[A ENRICHIR] Decrire le role du module en 2-3 phrases",
        "business_context": "[A ENRICHIR] Contexte metier du module pour audience 'consultants'",
        "bases": split_csv(args.bases),
        "entities": split_csv(args.entities),
        "depends_on": split_csv(args.depends_on),
        "integrates_with": split_csv(args.integrates_with),
        "owner": args.owner or "[A VERIFIER]",
        "last_reviewed": date.today().isoformat(),
        "a_verifier": [
            "Enrichir description et business_context",
            "Completer la liste des entites via extracteurs par entite",
            "Valider la coherence bases <-> entities (chaque entite pointe vers une base)",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", required=True, help="Code module, ex: DAV")
    ap.add_argument("--prefix", required=True, help="Prefixe canonique, ex: GTF ou CCF")
    ap.add_argument("--label", help="Label lisible, ex: Achat-Vente")
    ap.add_argument("--domain", help="Domaine fonctionnel, ex: 'Gestion commerciale'")
    ap.add_argument("--bases", help="Liste CSV des bases, ex: GTFDOS,GTFPCF,GTFAT")
    ap.add_argument("--entities", help="Liste CSV des entites, ex: CLI,FOU,ART")
    ap.add_argument("--depends-on", help="Liste CSV modules dont celui-ci depend")
    ap.add_argument("--integrates-with", help="Liste CSV modules integres")
    ap.add_argument("--owner", help="Equipe responsable")
    ap.add_argument("--output", required=True, help="Chemin YAML de sortie")
    args = ap.parse_args()

    module = build_module(args)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(module, f, allow_unicode=True, sort_keys=False, width=120)

    summary = {
        "module": args.module,
        "output": str(out),
        "bases_count": len(module["bases"]),
        "entities_count": len(module["entities"]),
        "depends_on": module["depends_on"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
