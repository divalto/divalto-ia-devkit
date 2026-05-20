#!/usr/bin/env python3
"""Valide un fichier RecordSql (.dhsq) contre les regles R01-R08.

R01 (error)   : filtre multi-dossier '.Dos = MZ.Dos' dans WHERE
R02 (warning) : OverWrittenBy present dans DictionarySql
R03           : nom RecordSql coherent (error si vide, warning si divergent des tokens)
R04 (error)   : sections SELECT et FROM presentes
R05 (warning) : DefaultDictionary present et coherent
R06 (error)   : encodage ISO-8859-1 + CRLF
R07 (warning) : coherence FROM/WHERE -- chaque table implicite dans FROM doit avoir une ref dans WHERE (G-021)
R08 (warning) : syntaxe LEFT JOIN bien formee -- 'LEFT JOIN <table> [alias] ON <condition>' (G-021)

Usage:
    py .claude/skills/generating-recordsql/scripts/validate_rsql.py --path "chemin/fichier.dhsq"

    Avec tokens (pour verifications croisees) :
    py .claude/skills/generating-recordsql/scripts/validate_rsql.py --path "chemin/fichier.dhsq" --tokens tokens.json

Sortie JSON: {path, valid, errors[], warnings[], summary}
Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import re
import sys


def read_file(path):
    """Lit le fichier en essayant ISO-8859-1 puis UTF-8."""
    for enc in ('iso-8859-1', 'utf-8'):
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read(), enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    print(f"Erreur: impossible de lire '{path}' (encodage inconnu)", file=sys.stderr)
    return None, None


def check_r01_filtre_dos(content, lines):
    """R01: Le WHERE doit contenir Dos = MZ.Dos (ERREUR)."""
    findings = []

    # Trouver toutes les sections <WHERE>
    in_where = False
    where_start = 0
    has_dos_filter = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith('<WHERE>') or stripped == '<WHERE>':
            in_where = True
            where_start = i
            has_dos_filter = False
            continue

        if in_where and (stripped.startswith('<ORDERBY>') or stripped.startswith('<') and '>' in stripped and not stripped.startswith('<WHERE')):
            if not has_dos_filter:
                findings.append({
                    "rule": "R01",
                    "severity": "error",
                    "line": where_start,
                    "message": "Filtre multi-dossier absent: pas de '.Dos = MZ.Dos' dans la section WHERE",
                    "context": f"<WHERE> a la ligne {where_start}",
                })
            in_where = False
            continue

        if in_where:
            # Chercher .Dos = MZ.Dos (insensible a la casse, espaces variables)
            if re.search(r'\.Dos\s*=\s*MZ\.Dos', stripped, re.IGNORECASE):
                has_dos_filter = True

    # Fin de fichier avec WHERE encore ouvert
    if in_where and not has_dos_filter:
        findings.append({
            "rule": "R01",
            "severity": "error",
            "line": where_start,
            "message": "Filtre multi-dossier absent: pas de '.Dos = MZ.Dos' dans la section WHERE",
            "context": f"<WHERE> a la ligne {where_start}",
        })

    return findings


def check_r02_overwrittenby(content, lines):
    """R02: OverWrittenBy doit etre present dans le DictionarySql (WARNING)."""
    findings = []

    has_overwrittenby = False
    for i, line in enumerate(lines, 1):
        if 'overwrittenby=' in line.lower() or 'overwrittenby =' in line.lower():
            has_overwrittenby = True
            break

    if not has_overwrittenby:
        findings.append({
            "rule": "R02",
            "severity": "warning",
            "line": 1,
            "message": "OverWrittenBy absent: la surcharge utilisateur est impossible",
            "context": "Ligne <DictionarySql>",
        })

    return findings


def check_r03_recordsql_name(content, lines, tokens=None):
    """R03: Verifications sur les noms RecordSql (WARNING/ERREUR selon contexte)."""
    findings = []

    # Extraire tous les Name= du fichier
    names = re.findall(r'<RecordSql\s+Name=(\S+)', content)

    for name in names:
        # Verifier que le nom n'est pas vide
        if not name or name == '""':
            findings.append({
                "rule": "R03",
                "severity": "error",
                "line": 1,
                "message": "Nom du RecordSql vide",
                "context": "<RecordSql Name=...>",
            })

    # Si tokens fournis, verifier coherence
    if tokens:
        expected_name = tokens.get("NomVue")
        if expected_name and names and names[0] != expected_name:
            findings.append({
                "rule": "R03",
                "severity": "warning",
                "line": 1,
                "message": f"Nom RecordSql '{names[0]}' ne correspond pas au NomVue attendu '{expected_name}'",
                "context": f"<RecordSql Name={names[0]}>",
            })

    return findings


def check_r04_select_from(content, lines):
    """R04: Les sections SELECT et FROM doivent etre presentes (ERREUR)."""
    findings = []

    has_select = any('<SELECT>' in line or '<SELECT ' in line for line in lines)
    has_from = any('<FROM' in line for line in lines)

    if not has_select:
        findings.append({
            "rule": "R04",
            "severity": "error",
            "line": 1,
            "message": "Section <SELECT> manquante",
            "context": "Structure RecordSql",
        })

    if not has_from:
        findings.append({
            "rule": "R04",
            "severity": "error",
            "line": 1,
            "message": "Section <FROM> manquante",
            "context": "Structure RecordSql",
        })

    return findings


def check_r05_dictionary(content, lines, tokens=None):
    """R05: DefaultDictionary doit etre present et correct (WARNING)."""
    findings = []

    match = re.search(r'DefaultDictionary=(\S+)', content)
    if not match:
        findings.append({
            "rule": "R05",
            "severity": "warning",
            "line": 1,
            "message": "DefaultDictionary absent dans <DictionarySql>",
            "context": "Ligne <DictionarySql>",
        })
    elif tokens:
        expected_dict = tokens.get("DICT", "") + ".dhsd"
        actual_dict = match.group(1)
        if actual_dict.lower() != expected_dict.lower():
            findings.append({
                "rule": "R05",
                "severity": "warning",
                "line": 1,
                "message": f"DefaultDictionary '{actual_dict}' ne correspond pas au dictionnaire attendu '{expected_dict}'",
                "context": f"DefaultDictionary={actual_dict}",
            })

    return findings


def check_r06_encoding(path):
    """R06: Le fichier doit etre en ISO-8859-1 + CRLF (ERREUR)."""
    findings = []

    with open(path, 'rb') as f:
        raw = f.read()

    # Verifier CRLF
    has_lf_only = b'\n' in raw and b'\r\n' not in raw
    has_mixed = b'\r\n' in raw and raw.replace(b'\r\n', b'').count(b'\n') > 0

    if has_lf_only:
        findings.append({
            "rule": "R06",
            "severity": "error",
            "line": 0,
            "message": "Fins de ligne LF detectees (attendu: CRLF)",
            "context": "Encodage fichier",
        })
    elif has_mixed:
        findings.append({
            "rule": "R06",
            "severity": "error",
            "line": 0,
            "message": "Fins de ligne mixtes LF/CRLF detectees (attendu: CRLF uniquement)",
            "context": "Encodage fichier",
        })

    # Verifier pas de BOM UTF-8
    if raw.startswith(b'\xef\xbb\xbf'):
        findings.append({
            "rule": "R06",
            "severity": "error",
            "line": 0,
            "message": "BOM UTF-8 detecte (le fichier doit etre en ISO-8859-1)",
            "context": "Encodage fichier",
        })

    # Verifier les sequences UTF-8 multi-octets (signe de non-ISO-8859-1)
    # Les octets 0xC0-0xFF suivis de 0x80-0xBF sont des sequences UTF-8
    i = 0
    while i < len(raw):
        b = raw[i]
        if 0xC0 <= b <= 0xDF and i + 1 < len(raw) and 0x80 <= raw[i + 1] <= 0xBF:
            findings.append({
                "rule": "R06",
                "severity": "error",
                "line": 0,
                "message": f"Sequence UTF-8 multi-octets detectee a l'offset {i} (attendu: ISO-8859-1)",
                "context": "Encodage fichier",
            })
            break  # Un seul rapport suffit
        i += 1

    return findings


def check_r07_from_where_coherence(content, lines):
    """R07: Chaque table implicite dans <FROM> doit apparaitre dans <WHERE> (warning).

    Heuristique : on extrait les noms de tables declarees dans FROM (hors LEFT JOIN),
    on saute la table principale (premiere), puis on verifie que chaque autre apparait
    dans WHERE sous la forme '<table>.' (condition de jointure).
    """
    findings = []

    from_match = re.search(
        r'<FROM[^>]*>(.*?)(?=<WHERE>|<ORDERBY>|$)',
        content, re.DOTALL | re.IGNORECASE,
    )
    where_match = re.search(
        r'<WHERE>(.*?)(?=<ORDERBY>|$)',
        content, re.DOTALL | re.IGNORECASE,
    )
    if not from_match or not where_match:
        return findings

    from_body = from_match.group(1)
    where_body = where_match.group(1)

    tables = []
    for line in from_body.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith(';'):
            continue
        upper = stripped.upper()
        if upper.startswith('LEFT JOIN') or upper.startswith('INNER JOIN') \
                or upper.startswith('RIGHT JOIN') or upper.startswith('CROSS JOIN'):
            continue
        parts = stripped.split()
        if parts and re.match(r'^[A-Za-z_]\w*$', parts[0]):
            tables.append(parts[0])

    for table in tables[1:]:
        if not re.search(r'\b' + re.escape(table) + r'\.', where_body):
            findings.append({
                "rule": "R07",
                "severity": "warning",
                "line": 1,
                "message": f"Table '{table}' declaree dans <FROM> sans condition de jointure dans <WHERE>",
                "context": f"Jointure implicite : {table}",
            })

    return findings


def check_r08_left_join_syntax(content, lines):
    """R08: LEFT JOIN bien forme -- 'LEFT JOIN <table> [alias] ON <condition>' (warning)."""
    findings = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not re.search(r'\bLEFT\s+JOIN\b', stripped, re.IGNORECASE):
            continue
        if not re.search(
            r'LEFT\s+JOIN\s+[A-Za-z_]\w*(?:\s+[A-Za-z_]\w*)?\s+ON\s+\S',
            stripped, re.IGNORECASE,
        ):
            findings.append({
                "rule": "R08",
                "severity": "warning",
                "line": i,
                "message": "LEFT JOIN mal forme : attendu 'LEFT JOIN <table> [alias] ON <condition>'",
                "context": stripped[:100],
            })

    return findings


def check_public_record_mz(content, lines):
    """Verifier que Public Record A5DD.dhsd MZ est present (WARNING)."""
    findings = []

    has_mz = any(
        re.search(r'Public\s+Record\s+[\'"]?A5DD\.dhsd[\'"]?\s+MZ', line, re.IGNORECASE)
        for line in lines
    )

    if not has_mz:
        findings.append({
            "rule": "R01",
            "severity": "warning",
            "line": 1,
            "message": "Public Record A5DD.dhsd MZ absent (necessaire pour MZ.Dos dans le filtre WHERE)",
            "context": "Declaration MZ",
        })

    return findings


def validate_rsql(path, tokens=None):
    """Execute toutes les regles de validation."""
    content, encoding = read_file(path)
    if content is None:
        return None

    lines = content.splitlines()

    errors = []
    warnings = []

    # Toutes les regles
    all_findings = []
    all_findings.extend(check_r01_filtre_dos(content, lines))
    all_findings.extend(check_public_record_mz(content, lines))
    all_findings.extend(check_r02_overwrittenby(content, lines))
    all_findings.extend(check_r03_recordsql_name(content, lines, tokens))
    all_findings.extend(check_r04_select_from(content, lines))
    all_findings.extend(check_r05_dictionary(content, lines, tokens))
    all_findings.extend(check_r06_encoding(path))
    all_findings.extend(check_r07_from_where_coherence(content, lines))
    all_findings.extend(check_r08_left_join_syntax(content, lines))

    for f in all_findings:
        if f["severity"] == "error":
            errors.append(f)
        else:
            warnings.append(f)

    return {
        "path": path,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total": len(errors) + len(warnings),
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Valide un fichier RecordSql (.dhsq) contre les regles R01-R06"
    )
    parser.add_argument("--path", required=True,
                        help="Chemin du fichier .dhsq a valider")
    parser.add_argument("--tokens", default=None,
                        help="Chemin vers le fichier JSON de tokens (pour verifications croisees)")

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Fichier non trouve : {args.path}", file=sys.stderr)
        sys.exit(1)

    tokens = None
    if args.tokens:
        try:
            with open(args.tokens, "r", encoding="utf-8") as f:
                tokens = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Erreur lecture tokens : {e}", file=sys.stderr)
            sys.exit(1)

    report = validate_rsql(args.path, tokens)
    if report is None:
        sys.exit(2)

    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
