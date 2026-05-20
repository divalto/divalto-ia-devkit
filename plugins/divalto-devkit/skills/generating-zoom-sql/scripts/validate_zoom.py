#!/usr/bin/env python3
"""Valide un fichier Zoom SQL (.dhsp) selon les regles Z01-Z12.

Usage:
    py .claude/skills/generating-zoom-sql/scripts/validate_zoom.py --path fichier.dhsp
    py .claude/skills/generating-zoom-sql/scripts/validate_zoom.py --path fichier.dhsp --tokens tokens.json

Sortie JSON: {valid, errors, warnings, checks}
Exit codes: 0 = succes (meme si warnings), 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import re
import sys


def read_file_content(path):
    """Lit le fichier en ISO-8859-1."""
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        return raw, raw.decode('iso-8859-1')
    except FileNotFoundError:
        print(f"Fichier non trouve : {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erreur lecture : {e}", file=sys.stderr)
        sys.exit(2)


# Les 27 procedures obligatoires du zoom
MANDATORY_PROCEDURES = [
    "Construire_Condition_Selection",
    "ZoomDebut",
    "ZoomAbandon",
    "ZoomValidation",
    "ZoomFin",
    "ZoomCreation",
    "ZoomDuplication",
    "ZoomApresCleCreation",
    "ZoomCreationRes",
    "ZoomAvantWrite",
    "ZoomApresCreation",
    "ZoomModification",
    "ZoomModificationRes",
    "ZoomAvantRewrite",
    "ZoomApresModification",
    "ZoomSuppression",
    "ZoomSuppressionRes",
    "ZoomAvantDelete",
    "ZoomApresSuppression",
    "ZoomAvantConsult",
    "ZoomConsult",
    "ZoomAvantInput",
    "ZoomArret",
    "ZoomFiltreAvantValeur",
    "ZoomFiltreApresValeur",
    "ZoomApresCle",
    "ZoomApresRead",
]


def check_z01(content, tokens=None):
    """Z01 — 27 procedures obligatoires presentes."""
    issues = []
    missing = []
    for proc in MANDATORY_PROCEDURES:
        pattern = r'(?i)\bProcedure\s+' + re.escape(proc) + r'\b'
        if not re.search(pattern, content):
            missing.append(proc)
    if missing:
        issues.append({
            "rule": "Z01",
            "severity": "error",
            "message": f"Procedures obligatoires manquantes ({len(missing)}/{len(MANDATORY_PROCEDURES)}): {', '.join(missing)}",
        })
    return issues


def check_z02(content, tokens=None):
    """Z02 — preturn apres Zoom.OK = 'I' ou 'S' ou 'C'."""
    issues = []
    # Chercher les patterns Zoom.OK = 'I' ou Zoom.Ok = 'S' sans preturn dans les 2 lignes suivantes
    lines = content.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.search(r'(?i)ZOOM\.OK?\s*=\s*[\'"]([ISC])[\'"]', stripped):
            # Verifier que preturn est present dans les 3 lignes suivantes
            found_preturn = False
            for j in range(i + 1, min(i + 4, len(lines))):
                if re.search(r'(?i)\bpreturn\b', lines[j]):
                    found_preturn = True
                    break
            if not found_preturn:
                # Verifier si preturn est sur la meme ligne (pattern compact)
                if not re.search(r'(?i)\bpreturn\b', stripped):
                    issues.append({
                        "rule": "Z02",
                        "severity": "warning",
                        "message": f"Ligne {i+1}: Zoom.OK affecte sans preturn dans les lignes suivantes",
                    })
    return issues


def check_z03(content, tokens=None):
    """Z03 — Pas de melange de prefixes domaine."""
    issues = []
    if not tokens:
        return issues

    prefix = tokens.get("PREFIX_", "")
    if not prefix:
        return issues

    # Prefixes connus
    all_prefixes = ["GT_", "RT_", "GG_", "CC_", "GA_"]
    wrong_prefixes = [p for p in all_prefixes if p != prefix]

    for wp in wrong_prefixes:
        # Chercher des appels framework avec le mauvais prefixe
        pattern = r'(?i)\b' + re.escape(wp) + r'(PreInsert|PostInsert|PreUpdate|PostUpdate|PreDelete|PostDelete)_recordSql\b'
        if re.search(pattern, content):
            issues.append({
                "rule": "Z03",
                "severity": "error",
                "message": f"Prefixe domaine incorrect: {wp} trouve alors que {prefix} est attendu",
            })
    return issues


def check_z08(content, tokens=None):
    """Z08 — Module ficsql present."""
    issues = []
    if not re.search(r'(?i)Module\s+[\'"].*pmficsql\.dhop[\'"]', content):
        issues.append({
            "rule": "Z08",
            "severity": "error",
            "message": "Module pmficsql.dhop absent — les fonctions framework ne seront pas trouvees",
        })
    return issues


def check_z10(content, tokens=None):
    """Z10 — Gestion du prefixe '-' dans ZOOM.Scevaleur."""
    issues = []
    if not re.search(r'(?i)Mid\s*\(\s*ZOOM\.Scevaleur', content):
        issues.append({
            "rule": "Z10",
            "severity": "warning",
            "message": "Gestion du prefixe '-' dans ZOOM.Scevaleur non detectee (recherche par libelle)",
        })
    return issues


def check_overwrittenby(content, tokens=None):
    """Verifie OverWrittenBy present et coherent."""
    issues = []
    has_owb = bool(re.search(r'(?i)OverWrittenBy\s+[\'"]', content))
    if not has_owb:
        issues.append({
            "rule": "OWB",
            "severity": "warning",
            "message": "OverWrittenBy absent du fichier zoom",
        })
    elif tokens:
        expected = tokens.get("overwrittenby_zoom", "")
        if expected and not re.search(re.escape(expected), content, re.IGNORECASE):
            issues.append({
                "rule": "OWB",
                "severity": "warning",
                "message": f"OverWrittenBy ne correspond pas au token attendu: {expected}",
            })
    return issues


def check_majuser(content, tokens=None):
    """Z04/M04 — majuser=true dans PreUpdate."""
    issues = []
    if re.search(r'(?i)PreUpdate_recordSql\s*\(', content):
        if not re.search(r'(?i)PreUpdate_recordSql\s*\([^)]*majuser\s*=\s*true', content):
            issues.append({
                "rule": "M04",
                "severity": "error",
                "message": "PreUpdate_recordSql sans majuser=true — UserMo/UserMoDh ne seront pas mis a jour",
            })
    return issues


def check_valretour(content, tokens=None):
    """S08 — Zoom.Valretour initialise dans ZoomValidation."""
    issues = []
    # Trouver la section ZoomValidation
    match = re.search(r'(?i)Procedure\s+ZoomValidation.*?Endp', content, re.DOTALL)
    if match:
        section = match.group()
        if not re.search(r'(?i)Zoom\.Valretour\s*=', section):
            issues.append({
                "rule": "S08",
                "severity": "warning",
                "message": "Zoom.Valretour non initialise dans ZoomValidation",
            })
    return issues


def check_encoding(raw_bytes):
    """Verifie l'encodage ISO-8859-1 + CRLF."""
    issues = []

    # Verifier fins de ligne CRLF
    i = 0
    lines_lf_only = 0
    while i < len(raw_bytes):
        if raw_bytes[i:i+1] == b'\n' and (i == 0 or raw_bytes[i-1:i] != b'\r'):
            lines_lf_only += 1
        i += 1

    if lines_lf_only > 0:
        issues.append({
            "rule": "ENC",
            "severity": "error",
            "message": f"Fins de ligne LF detectees ({lines_lf_only} occurrences). Attendu: CRLF",
        })

    # Verifier pas de BOM UTF-8
    if raw_bytes[:3] == b'\xef\xbb\xbf':
        issues.append({
            "rule": "ENC",
            "severity": "error",
            "message": "BOM UTF-8 detecte. Le fichier doit etre en ISO-8859-1 sans BOM",
        })

    # Verifier pas de sequences multi-octets UTF-8
    try:
        raw_bytes.decode('ascii')
    except UnicodeDecodeError:
        has_utf8_multibyte = bool(re.search(b'[\xc0-\xdf][\x80-\xbf]|[\xe0-\xef][\x80-\xbf]{2}', raw_bytes))
        if has_utf8_multibyte:
            issues.append({
                "rule": "ENC",
                "severity": "error",
                "message": "Fichier encode en UTF-8 avec caracteres multi-octets. Attendu: ISO-8859-1",
            })

    return issues


def check_naming_convention(path):
    """Verifie que le nom du fichier suit la convention de nommage .dhsf/.dhsp.

    Convention: [prefixe 2 lettres][e][z][identifiant][_sql].dhsp
    La 4e lettre doit etre 'z' pour un zoom.
    """
    issues = []
    basename = os.path.basename(path).lower()
    # Retirer l'extension
    name = os.path.splitext(basename)[0]
    if len(name) >= 4 and name[2] == 'e':
        if name[3] != 'z':
            issues.append({
                "rule": "NAMING_CONV",
                "severity": "warning",
                "message": f"La 4e lettre du fichier est '{name[3]}', attendu 'z' pour un zoom (convention: [prefixe]z[id]_sql.dhsp)",
            })
    return issues


def check_naming_coherence(content, tokens):
    """Verifie la coherence des noms avec les tokens."""
    issues = []
    if not tokens:
        return issues

    nom_vue = tokens.get("NomVue", "")
    if nom_vue:
        # RecordSql doit etre declare
        if not re.search(r'(?i)RecordSql\s+.*' + re.escape(nom_vue), content):
            issues.append({
                "rule": "NAMING",
                "severity": "warning",
                "message": f"RecordSql {nom_vue} non declare dans le fichier",
            })
        # Instance _Sel doit exister
        if not re.search(re.escape(nom_vue) + r'_Sel', content):
            issues.append({
                "rule": "NAMING",
                "severity": "warning",
                "message": f"{nom_vue}_Sel non declare dans le fichier",
            })

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Valide un fichier Zoom SQL (.dhsp) selon les regles Z01-Z12"
    )
    parser.add_argument("--path", required=True,
                        help="Chemin du fichier .dhsp a valider")
    parser.add_argument("--tokens", default=None,
                        help="Chemin vers un fichier JSON de tokens (optionnel)")

    args = parser.parse_args()

    # Lire le fichier
    raw_bytes, content = read_file_content(args.path)

    # Lire les tokens si fournis
    tokens = None
    if args.tokens:
        try:
            with open(args.tokens, "r", encoding="utf-8") as f:
                tokens = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Erreur lecture tokens : {e}", file=sys.stderr)
            sys.exit(1)

    # Executer toutes les verifications
    all_issues = []
    all_issues.extend(check_z01(content, tokens))
    all_issues.extend(check_z02(content, tokens))
    all_issues.extend(check_z03(content, tokens))
    all_issues.extend(check_z08(content, tokens))
    all_issues.extend(check_z10(content, tokens))
    all_issues.extend(check_overwrittenby(content, tokens))
    all_issues.extend(check_majuser(content, tokens))
    all_issues.extend(check_valretour(content, tokens))
    all_issues.extend(check_encoding(raw_bytes))
    all_issues.extend(check_naming_convention(args.path))
    if tokens:
        all_issues.extend(check_naming_coherence(content, tokens))

    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]

    result = {
        "valid": len(errors) == 0,
        "errors": len(errors),
        "warnings": len(warnings),
        "checks": all_issues,
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
