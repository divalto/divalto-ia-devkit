#!/usr/bin/env python3
"""Genere un fichier Module Check (.dhsp) a partir des tokens de nommage et d'un template Jinja2.

Usage (autonome, mode --params) :
    py .claude/skills/generating-objet-metier/scripts/generate_mchk.py \
        --params --domaine Retail --entite FamRglt --table RtlFamRglt \
        --champ-cle RgltFam --description "Famille de reglement" \
        --output "output/rttmchkrtlfamrglt.dhsp"

Usage (tokens JSON) :
    py .claude/skills/generating-objet-metier/scripts/generate_mchk.py \
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
TEMPLATE_NAME = "mchk.dhsp.j2"


def augment_tokens(tokens):
    """Ajoute les tokens derives necessaires au template mchk."""
    t = dict(tokens)
    # NomVue en majuscules (DIVA case-insensitive, mais le pattern ERP utilise les deux)
    t["NOMVUE_MAJUSCULE"] = t["NomVue"].upper()
    # ChampCle avec premiere lettre en minuscule (pour parametre dans Seek)
    champ = t["ChampCle"]
    t["ChampCle_lower"] = champ[0].lower() + champ[1:] if champ else champ
    # FKs : default []
    t.setdefault("fks", [])
    return t


def parse_fk_args(fk_args):
    """Transforme ['RacPays:T013:9053', 'RacDev:T007'] en liste de dicts structures.

    Chaque dict contient : champ, target, module_dhop, find_fn, get_lib_fn, zoom_num.
    Le mapping module / find / get_lib suit la convention empirique (cf.
    docs/FK-ZOOM-BINDING.md section 6). Pour les exemptions CC (C3/C4/C5/C6/C7/C8/C9),
    module_dhop = None (framework Compta indirect).
    """
    CC_EXEMPT = {"C3", "C4", "C5", "C6", "C7", "C8", "C9"}
    fks = []
    for raw in fk_args:
        parts = raw.split(":")
        if len(parts) < 2:
            print(
                f"Erreur: --fk '{raw}' invalide. Format attendu : 'champ:cible[:zoom]'.",
                file=sys.stderr,
            )
            sys.exit(1)
        champ = parts[0].strip()
        target = parts[1].strip()
        zoom_num = None
        if len(parts) >= 3 and parts[2].strip():
            try:
                zoom_num = int(parts[2].strip())
            except ValueError:
                print(
                    f"Erreur: --fk '{raw}' -- zoom_num doit etre un entier.",
                    file=sys.stderr,
                )
                sys.exit(1)
        if target in CC_EXEMPT:
            module_dhop = None  # framework CC indirect
        else:
            module_dhop = f"Gttmchk{target.lower()}.dhop"
        fks.append({
            "champ": champ,
            "target": target,
            "module_dhop": module_dhop,
            "find_fn": f"Find_{target}",
            "get_lib_fn": f"Get_{target}_Lib",
            "zoom_num": zoom_num,
        })
    return fks


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
        description="Genere un fichier Module Check (.dhsp) a partir de tokens JSON"
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

    parser.add_argument(
        "--fk",
        action="append",
        default=[],
        metavar="CHAMP:TARGET",
        help=(
            "Foreign key a generer (repetable) : 'champ:cible' ou 'champ:cible:zoom_num'. "
            "Ex : --fk RacPays:T013:9053 --fk RacDev:T007. "
            "Genere Module import + Check_<SRC>_Field_<Champ>(+_Lib). "
            "Cf. docs/FK-ZOOM-BINDING.md + docs/ZOOMS-STANDARDS-CATALOGUE.md."
        ),
    )

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
        "TABLE_MAJUSCULE", "table_minuscule", "CHAMPCLE",
        "Description", "date", "fichier_mchk", "overwrittenby_mchk",
        "domaine_2l", "prefix_db", "base", "PREFIXRES", "entity",
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

    # Injecter les FK (--fk) ; prioritaire sur tokens["fks"] si both fournis
    if args.fk:
        tokens["fks"] = parse_fk_args(args.fk)

    # Augmenter les tokens avec les derives
    tokens = augment_tokens(tokens)

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
