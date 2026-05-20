#!/usr/bin/env python3
"""Genere le bloc de 16 alias pour *pmficsql.dhsp a partir des tokens de nommage.

Usage:
    py .claude/skills/creating-diva-entity/scripts/generate_alias.py --file tokens.json --output "output/alias_block.txt"
    cat tokens.json | py .claude/skills/creating-diva-entity/scripts/generate_alias.py --stdin --output "output/alias_block.txt"

Sortie JSON: {path, aliases_count, tokens_used}
Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import sys

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
except ImportError:
    print("Erreur: Jinja2 non installe. Installer avec: py -m pip install Jinja2",
          file=sys.stderr)
    sys.exit(2)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
TEMPLATE_NAME = "alias_block.txt.j2"


def main():
    parser = argparse.ArgumentParser(
        description="Genere le bloc de 16 alias pour *pmficsql.dhsp"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stdin", action="store_true",
                       help="Lire les tokens JSON depuis stdin")
    group.add_argument("--file", help="Chemin vers un fichier JSON de tokens")

    parser.add_argument("--output", required=True,
                        help="Chemin du fichier de sortie")

    args = parser.parse_args()

    # Lire les tokens
    try:
        if args.stdin:
            tokens = json.load(sys.stdin)
        else:
            with open(args.file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Erreur JSON : {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Fichier non trouve : {args.file}", file=sys.stderr)
        sys.exit(1)

    # Verifier les tokens obligatoires
    required_tokens = ["PREFIX_", "NomVue", "Description"]
    missing = [t for t in required_tokens if t not in tokens]
    if missing:
        print(f"Erreur: tokens manquants: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Rendre le template
    try:
        env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            keep_trailing_newline=True,
            autoescape=False,
        )
        template = env.get_template(TEMPLATE_NAME)
    except TemplateNotFound:
        print(f"Erreur: template '{TEMPLATE_NAME}' non trouve dans {TEMPLATES_DIR}",
              file=sys.stderr)
        sys.exit(2)

    content = template.render(**tokens)

    # Ecrire le fichier
    parent = os.path.dirname(args.output)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    with open(args.output, 'w', encoding='iso-8859-1', newline='\r\n') as f:
        f.write(content)

    # Rapport
    result = {
        "path": args.output,
        "aliases_count": 16,
        "tokens_used": required_tokens,
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
