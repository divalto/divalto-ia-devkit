#!/usr/bin/env python3
"""Parse un rapport de synchronisation SQL xwin7 synchroauto.

Extrait le marqueur [TOTAL_ERRORS]N et les erreurs du rapport.

Usage :
    py parse_synchro.py --path rapport.txt

Sortie JSON :
    {
        "file": "rapport.txt",
        "success": true,
        "total_errors": 0,
        "errors": []
    }

Exit codes :
    0 = synchronisation reussie (0 erreur)
    1 = synchronisation echouee (erreurs trouvees)
    2 = erreur interne (rapport illisible)
"""

import argparse
import json
import os
import re
import sys


def parse_total_errors(lines):
    """Cherche le marqueur [TOTAL_ERRORS]N dans le rapport.

    Format attendu :
        [TOTAL_ERRORS]0
        [TOTAL_ERRORS]3

    Returns:
        int ou None si marqueur non trouve
    """
    pattern = re.compile(r'\[TOTAL_ERRORS\](\d+)')

    for line in reversed(lines):
        match = pattern.search(line)
        if match:
            return int(match.group(1))

    return None


def extract_errors(lines):
    """Extrait les lignes d'erreur du rapport avec contexte.

    Les erreurs de synchronisation contiennent typiquement :
    - Des messages d'erreur SQL (CREATE TABLE, ALTER TABLE echoue)
    - Des erreurs de connexion
    - Des erreurs de droits

    Returns:
        list of dict: [{line: N, message: "...", context: "..."}]
    """
    errors = []
    error_pattern = re.compile(r'(erreur|error|echec|failed|impossible)', re.IGNORECASE)

    # Exclure la ligne [TOTAL_ERRORS] elle-meme
    total_errors_pattern = re.compile(r'\[TOTAL_ERRORS\]')

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if total_errors_pattern.search(stripped):
            continue
        if error_pattern.search(stripped):
            context = lines[i - 1].strip() if i > 0 else ""
            errors.append({
                "line": i + 1,
                "message": stripped,
                "context": context
            })

    return errors


def _bracket_idents(text):
    """Extrait les identifiants entre crochets [Nom] (colonnes, tables SQL Server)."""
    return re.findall(r'\[(\w+)\]', text)


def extract_changes(content):
    """Extrait le DELTA de schema d'un rapport/script de synchro SQL.

    Source de verite = les instructions DDL reelles (robuste sur les 2 formats :
    .sql avec separateurs `GO`, ou .log avec `*** AuditOdbc`). Le rapport decrit
    un vrai delta (ALTER TABLE ADD/DROP COLUMN, CREATE/DROP INDEX), pas un
    DROP+CREATE en bloc (sauf table neuve).

    Bruit filtre : tables `*_oldcolumns` (sauvegarde liee a un DROP COLUMN),
    `INSERT INTO`, `sp_addextendedproperty`, drop-constraint dynamique.

    Returns:
        dict {tables_modified, tables[], procedures{created,dropped}, functions[]}
    """
    # Decoupage en instructions : 'GO' (script .sql) sinon '*** AuditOdbc' (log)
    if re.search(r'(?im)^\s*GO\s*$', content):
        blocks = re.split(r'(?im)^\s*GO\s*$', content)
    else:
        blocks = re.split(r'\*\*\* AuditOdbc', content)

    tables = {}
    procedures = {"created": [], "dropped": []}
    functions = []

    def T(name):
        return tables.setdefault(name, {
            "table": name, "created": False, "dropped": False,
            "add_columns": [], "drop_columns": [],
            "create_index": [], "drop_index": [],
        })

    for blk in blocks:
        m = re.search(r'(?i)ALTER\s+TABLE\s+\[dbo\]\.\[(\w+)\]\s+ADD\b', blk)
        if m:
            tname = m.group(1)
            cols = [c for c in _bracket_idents(blk[m.end():]) if c.lower() != tname.lower()]
            for c in cols:
                if c not in T(tname)["add_columns"]:
                    T(tname)["add_columns"].append(c)
            continue
        m = re.search(r'(?i)ALTER\s+TABLE\s+\[dbo\]\.\[(\w+)\]\s+DROP\s+COLUMN\b', blk)
        if m:
            tname = m.group(1)
            cols = [c for c in _bracket_idents(blk[m.end():]) if c.lower() != tname.lower()]
            for c in cols:
                if c not in T(tname)["drop_columns"]:
                    T(tname)["drop_columns"].append(c)
            continue
        m = re.search(r'(?i)DROP\s+INDEX\s+\[(\w+)\]\s+ON\s+\[dbo\]\.\[(\w+)\]', blk)
        if m:
            T(m.group(2))["drop_index"].append(m.group(1))
            continue
        m = re.search(
            r'(?i)CREATE\s+(?:UNIQUE\s+)?(?:NON)?CLUSTERED?\s+INDEX\s+\[(\w+)\]\s+ON\s+\[dbo\]\.\[(\w+)\]',
            blk,
        )
        if m:
            T(m.group(2))["create_index"].append(m.group(1))
            continue
        mc = re.search(r'(?i)CREATE\s+TABLE\s+\[dbo\]\.\[(\w+)\]', blk)
        if mc:
            tn = mc.group(1)
            if not tn.lower().endswith("_oldcolumns"):
                T(tn)["created"] = True
            continue
        md = re.search(r'(?i)DROP\s+TABLE\s+\[dbo\]\.\[(\w+)\]', blk)
        if md:
            tn = md.group(1)
            if not tn.lower().endswith("_oldcolumns"):
                T(tn)["dropped"] = True
            continue
        m = re.search(r'(?i)\bCREATE\s+PROCEDURE\s+\[dbo\]\.\[(\w+)\]', blk)
        if m:
            procedures["created"].append(m.group(1))
            continue
        m = re.search(r'(?i)\bDROP\s+PROCEDURE\s+\[dbo\]\.\[(\w+)\]', blk)
        if m:
            procedures["dropped"].append(m.group(1))
            continue
        m = re.search(r'(?i)\bCREATE\s+FUNCTION\s+\[dbo\]\.\[(\w+)\]', blk)
        if m:
            functions.append(m.group(1))
            continue

    # Une table sans aucun delta reel (created/dropped False + listes vides) est ecartee
    def has_change(t):
        return (t["created"] or t["dropped"] or t["add_columns"] or t["drop_columns"]
                or t["create_index"] or t["drop_index"])

    table_list = sorted((t for t in tables.values() if has_change(t)), key=lambda t: t["table"])
    return {
        "tables_modified": len(table_list),
        "tables": table_list,
        "procedures": {
            "created": sorted(set(procedures["created"])),
            "dropped": sorted(set(procedures["dropped"])),
        },
        "functions": sorted(set(functions)),
    }


def parse_report(file_path):
    """Parse un rapport de synchronisation complet.

    Args:
        file_path: chemin du fichier rapport

    Returns:
        dict: resultat structure
    """
    try:
        with open(file_path, "r", encoding="iso-8859-1") as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"Fichier introuvable : {file_path}"}
    except Exception as e:
        return {"error": f"Erreur lecture : {e}"}

    lines = content.split("\n")

    # Chercher le marqueur [TOTAL_ERRORS]
    total_errors = parse_total_errors(lines)

    if total_errors is None:
        return {
            "error": "Marqueur [TOTAL_ERRORS] introuvable dans le rapport. "
                     "Verifier que le rapport est un fichier synchroauto xwin7."
        }

    # Extraire les erreurs
    errors = extract_errors(lines) if total_errors > 0 else []

    return {
        "file": file_path,
        "success": total_errors == 0,
        "total_errors": total_errors,
        "errors": errors
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parse un rapport de synchronisation SQL xwin7 synchroauto"
    )
    parser.add_argument(
        "--path", required=True,
        help="Chemin du fichier rapport de synchronisation"
    )
    parser.add_argument(
        "--changes", action="store_true",
        help="Extrait le DELTA de schema (ALTER ADD/DROP COLUMN, index, tables/procs/fonctions) "
             "groupe par table. Substitut a posteriori de l'apercu (pas de dry-run natif xwin7). "
             "Marche sur le rapport synchroauto ET le log d'audit (DhOdbcConfigSql.log/.sql)."
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Erreur : fichier introuvable : {args.path}", file=sys.stderr)
        sys.exit(2)

    # Mode --changes : delta de schema, autonome (ne requiert pas le marqueur [TOTAL_ERRORS])
    if args.changes:
        try:
            with open(args.path, "r", encoding="iso-8859-1") as f:
                content = f.read()
        except Exception as e:
            print(f"Erreur lecture : {e}", file=sys.stderr)
            sys.exit(2)
        changes = extract_changes(content)
        total_errors = parse_total_errors(content.split("\n"))  # inclus si present
        out = {"file": args.path, "mode": "changes", "changes": changes}
        if total_errors is not None:
            out["total_errors"] = total_errors
        json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
        print()
        sys.exit(0)

    result = parse_report(args.path)

    if "error" in result:
        print(f"Erreur : {result['error']}", file=sys.stderr)
        sys.exit(2)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
