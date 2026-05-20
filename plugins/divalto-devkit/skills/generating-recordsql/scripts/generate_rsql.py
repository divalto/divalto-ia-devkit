#!/usr/bin/env python3
"""Genere un fichier RecordSql (.dhsq) a partir des tokens de nommage et d'un template Jinja2.

Usage (autonome, mode --params, toujours mono-table) :
    py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
        --params --domaine Retail --entite FamRglt --table RtlFamRglt \
        --champ-cle RgltFam --description "Famille de reglement" \
        --output "output/rtlrsfamrglt.dhsq"

Usage (tokens JSON, peut etre mono ou multi-table) :
    py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
        --file tokens.json --output "chemin/fichier.dhsq"

Multi-table (G-021) : les tokens JSON peuvent inclure deux cles optionnelles :
    "joined_tables": [
        {
            "table_sql": "TIA", "alias": "TIA",
            "join_type": "implicit",   # ou "left_join"
            "join_condition": "TIA.Dos = MZ.Dos AND CLI.Ticod = TIA.Ticod",
            "columns_selected": ["TIA.TiaLib"]
        }
    ]
    "additional_cases": [
        {"name": "Equal_Ref", "field": "Ref", "type": "equal", "param": "char"},
        {"name": "Between_DateMaj", "field": "DateMaj", "type": "between", "param": "date"}
    ]
Absentes -> mode mono-table (backcompat).

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


# Chemin vers le repertoire templates (relatif au script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
TEMPLATE_NAME = "recordsql.dhsq.j2"

# Repertoire des squelettes G-022 (reference/skeletons/ au niveau du skill)
SKELETONS_DIR = os.path.join(
    os.path.dirname(SCRIPT_DIR), "reference", "skeletons"
)


def parse_fk_args(fk_args):
    """Transforme ['Pay:T013:9053'] en liste de dicts FK structures.

    Chaque dict contient : champ, target, zoom_num. Vendored depuis
    generating-objet-metier (sans la logique CC_EXEMPT qui ne sert pas
    cote SQL).
    """
    fks = []
    for raw in fk_args:
        parts = raw.split(":")
        if len(parts) < 2:
            print(
                f"Erreur: --fk '{raw}' invalide. Format attendu : "
                f"'champ:cible[:zoom]'.",
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
        fks.append({"champ": champ, "target": target, "zoom_num": zoom_num})
    return fks


def fks_to_joined_tables(fks, main_table):
    """Convertit une liste de FK en entrees joined_tables.

    Pour chaque FK : LEFT JOIN syntaxique avec condition explicite ON
    `<MAIN>.<champ> = <TARGET>.<champ> AND <MAIN>.Dos = <TARGET>.Dos`.
    Colonne joint nommee `<champ>_Lib` (coherente avec le pattern callback
    genere par `manipulating-dhsf-screens/dhsf_add_fk.py`).
    """
    joined = []
    for fk in fks:
        champ = fk["champ"]
        target = fk["target"]
        joined.append({
            "table_sql": target,
            "alias": target,
            "join_type": "left_join",
            "join_condition": (
                f"{main_table}.{champ} = {target}.{champ} "
                f"AND {main_table}.Dos = {target}.Dos"
            ),
            "columns_selected": [f"{target}.Lib AS {champ}_Lib"],
        })
    return joined


def load_skeleton(name, main_table):
    """Charge un squelette G-022 et substitue le placeholder {MAIN} par main_table.

    Retourne un dict {joined_tables, additional_cases} pret a merger dans les tokens.
    """
    path = os.path.join(SKELETONS_DIR, f"{name}.skel.json")
    if not os.path.exists(path):
        print(f"Erreur: skeleton '{name}' non trouve dans {SKELETONS_DIR}",
              file=sys.stderr)
        return None
    with open(path, "r", encoding="utf-8") as f:
        skel = json.load(f)

    # Substituer {MAIN} dans les conditions de jointure
    joined = []
    for jt in skel.get("joined_tables", []):
        jt = dict(jt)
        jt["join_condition"] = jt["join_condition"].replace("{MAIN}", main_table)
        joined.append(jt)

    return {
        "joined_tables": joined,
        "additional_cases": skel.get("additional_cases", []),
    }


def render_template(tokens):
    """Rend le template Jinja2 avec les tokens fournis."""
    try:
        env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            keep_trailing_newline=True,
            # Pas d'autoescape : c'est du XML DIVA, pas du HTML
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

    # S'assurer que le fichier termine par CRLF
    if content and not content.endswith('\r\n'):
        content += '\r\n'

    try:
        encoded = content.encode('iso-8859-1')
    except UnicodeEncodeError as e:
        print(f"Erreur: caractere non encodable en ISO-8859-1: {e}", file=sys.stderr)
        return None, 0

    # Creer le repertoire parent si necessaire
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    with open(path, 'wb') as f:
        f.write(encoded)

    return content, len(encoded)


def main():
    parser = argparse.ArgumentParser(
        description="Genere un fichier RecordSql (.dhsq) a partir de tokens JSON"
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

    parser.add_argument("--skeleton", default=None,
                        help="Nom d'un squelette G-022 (ex: zoom-reglement-19). "
                             "Le squelette ajoute des jointures pre-configurees.")

    parser.add_argument(
        "--fk",
        action="append",
        default=[],
        metavar="CHAMP:TARGET[:ZOOM]",
        help="FK a joindre, repetable. Genere un LEFT JOIN explicite + une "
             "colonne <CHAMP>_Lib dans le SELECT, coherent avec le pattern "
             "callback de dhsf_add_fk.py. Ex : --fk Pay:T013:9053",
    )

    parser.add_argument("--output", required=True,
                        help="Chemin du fichier .dhsq a generer")

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
        "DICT", "overwrittenby_rsql", "fichier_rsql", "date",
        "Description", "NomVue", "TableSQL", "ChampCle",
    ]
    missing = [t for t in required_tokens if t not in tokens]
    if missing:
        print(f"Erreur: tokens manquants: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Squelette G-022 : fusionne dans les tokens (ecrase joined_tables + additional_cases)
    if args.skeleton:
        skel_data = load_skeleton(args.skeleton, tokens["TableSQL"])
        if skel_data is None:
            sys.exit(1)
        tokens["joined_tables"] = skel_data["joined_tables"]
        tokens["additional_cases"] = skel_data["additional_cases"]
        tokens["has_joins"] = len(skel_data["joined_tables"]) > 0

    # FK --fk : append aux joined_tables (compatible avec --skeleton)
    if args.fk:
        fks = parse_fk_args(args.fk)
        fk_joined = fks_to_joined_tables(fks, tokens["TableSQL"])
        existing = tokens.get("joined_tables", [])
        tokens["joined_tables"] = existing + fk_joined
        tokens["has_joins"] = True
        tokens.setdefault("fks", []).extend(fks)

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
