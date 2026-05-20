#!/usr/bin/env python3
"""Genere un fichier Zoom SQL (.dhsp) a partir des tokens de nommage et d'un template Jinja2.

Usage (autonome, mode --params) :
    py .claude/skills/generating-zoom-sql/scripts/generate_zoom.py \
        --params --domaine Retail --entite FamRglt --table RtlFamRglt \
        --champ-cle RgltFam --description "Famille de reglement" \
        --output "output/rttzfamrglt_sql.dhsp"

Usage (tokens JSON) :
    py .claude/skills/generating-zoom-sql/scripts/generate_zoom.py \
        --file tokens.json --output "chemin/fichier.dhsp"

Sortie JSON: {path, encoding, line_endings, bytes, tokens_used}
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
TEMPLATE_NAME = "zoom_sql.dhsp.j2"


def render_template(tokens):
    """Rend le template Jinja2 avec les tokens fournis."""
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
        return None

    return template.render(**tokens)


def normalize_to_crlf(text):
    """Normalise les fins de ligne en CRLF."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', '\r\n')
    return text


def write_iso8859(path, content):
    """Ecrit le contenu en ISO-8859-1 + CRLF."""
    content = normalize_to_crlf(content)

    if content and not content.endswith('\r\n'):
        content += '\r\n'

    try:
        encoded = content.encode('iso-8859-1')
    except UnicodeEncodeError as e:
        print(f"Erreur: caractere non encodable en ISO-8859-1: {e}", file=sys.stderr)
        return None, 0

    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    with open(path, 'wb') as f:
        f.write(encoded)

    return content, len(encoded)


def main():
    parser = argparse.ArgumentParser(
        description="Genere un fichier Zoom SQL (.dhsp) a partir de tokens JSON"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stdin", action="store_true",
                       help="Lire les tokens JSON depuis stdin")
    group.add_argument("--file", help="Chemin vers un fichier JSON de tokens")
    group.add_argument("--params", action="store_true",
                       help="Mode autonome : calculer les tokens a partir des parametres entite")

    # Parametres entite (requis avec --params)
    parser.add_argument("--domaine", help="Domaine metier (ex: Retail)")
    parser.add_argument("--entite", help="Nom entite PascalCase (ex: FamRglt)")
    parser.add_argument("--table", help="Table SQL (ex: RtlFamRglt)")
    parser.add_argument("--champ-cle", help="Champ cle (ex: RgltFam)")
    parser.add_argument("--description", help="Description metier")
    parser.add_argument("--nom-vue", default=None,
                        help="Override du NomVue (si collision)")
    parser.add_argument("--champ-libelle", default="Libelle",
                        help="Nom du champ libelle dans le RecordSQL "
                             "(defaut: Libelle ; utiliser Lib si Nature=40)")

    parser.add_argument("--output", required=True,
                        help="Chemin du fichier .dhsp a generer")

    args = parser.parse_args()

    # Lire les tokens
    if args.params:
        # Mode autonome : calculer les tokens localement
        missing = [p for p in ["domaine", "entite", "table", "champ_cle", "description"]
                   if not getattr(args, p)]
        if missing:
            print(f"Erreur: --params requiert: {', '.join('--' + m.replace('_', '-') for m in missing)}",
                  file=sys.stderr)
            sys.exit(1)

        from _naming import compute_names
        tokens, error = compute_names(
            domaine=args.domaine, entite=args.entite,
            table_sql=args.table, champ_cle=args.champ_cle,
            description=args.description, nom_vue_override=args.nom_vue,
            champ_libelle=args.champ_libelle,
        )
        if error:
            print(f"Erreur naming: {error}", file=sys.stderr)
            sys.exit(1)
    else:
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
    required_tokens = [
        "DICT", "PREFIX_", "NomVue", "TableSQL", "ChampCle",
        "TABLE_MAJUSCULE", "table_minuscule", "Description",
        "date", "fichier_zoom", "overwrittenby_zoom",
        "fichier_rsql_compile", "module_mchk", "module_ficsql",
        "PREFIXRES",
    ]
    missing = [t for t in required_tokens if t not in tokens]
    if missing:
        print(f"Erreur: tokens manquants: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Verifier collision
    if tokens.get("collision_detected"):
        print(
            f"Erreur: collision detectee entre NomVue '{tokens['NomVue']}' et "
            f"TableSQL '{tokens['TableSQL']}'. Relancer avec "
            f"--nom-vue pour fournir un nom alternatif.",
            file=sys.stderr
        )
        sys.exit(1)

    # Rendre le template
    content = render_template(tokens)
    if content is None:
        sys.exit(2)

    # Ecrire le fichier
    written_content, byte_count = write_iso8859(args.output, content)
    if written_content is None:
        sys.exit(2)

    # Rapport
    result = {
        "path": args.output,
        "encoding": "iso-8859-1",
        "line_endings": "CRLF",
        "bytes": byte_count,
        "tokens_used": list(required_tokens),
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
