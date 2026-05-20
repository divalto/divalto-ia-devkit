#!/usr/bin/env python3
"""Valide un fichier Module Check (.dhsp) selon les regles M01-M05.

Usage:
    py .claude/skills/generating-objet-metier/scripts/validate_mchk.py --path fichier.dhsp
    py .claude/skills/generating-objet-metier/scripts/validate_mchk.py --path fichier.dhsp --tokens tokens.json

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


def check_m01(content, tokens=None):
    """M01 — Init_Module avec Get_CheckObject_Data."""
    issues = []
    has_init_module = bool(re.search(r'(?i)\bfunction\s+int\s+Init_Module\b', content))
    if not has_init_module:
        issues.append({
            "rule": "M01",
            "severity": "error",
            "message": "Init_Module absent du fichier",
        })
        return issues

    has_get_checkobject = bool(re.search(r'(?i)Get_CheckObject_Data\s*\(', content))
    if not has_get_checkobject:
        issues.append({
            "rule": "M01",
            "severity": "error",
            "message": "Init_Module ne contient pas d'appel a Get_CheckObject_Data",
        })

    return issues


def check_m02(content, tokens=None):
    """M02 — Record INIT initialise dans Init_Module."""
    issues = []
    has_init_call = bool(re.search(r'(?i)Initialize_\w+_New\s*\(\s*\w+_INIT\s*\)', content))
    if not has_init_call:
        issues.append({
            "rule": "M02",
            "severity": "error",
            "message": "Record _INIT non initialise dans Init_Module (Initialize_*_New(*_INIT) absent)",
        })
    return issues


def check_m03(content, tokens=None):
    """M03 — Stack/UnStack OutputMode dans PostFetch."""
    issues = []
    has_postfetch = bool(re.search(r'(?i)\b(function|procedure)\s+\w*\s*Initialize_\w+_PostFetch\b', content))
    if has_postfetch:
        has_stack = bool(re.search(r'(?i)A5_Stack_OutputMode', content))
        has_unstack = bool(re.search(r'(?i)A5_UnStack_OutputMode', content))
        if not has_stack or not has_unstack:
            issues.append({
                "rule": "M03",
                "severity": "warning",
                "message": "PostFetch sans A5_Stack_OutputMode / A5_UnStack_OutputMode",
            })
    return issues


def check_m04(content, tokens=None):
    """M04 — OverWrittenBy present."""
    issues = []
    has_overwrittenby = bool(re.search(r'(?i)OverWrittenBy\s+["\']', content))
    if not has_overwrittenby:
        issues.append({
            "rule": "M04",
            "severity": "warning",
            "message": "OverWrittenBy absent du fichier mchk",
        })

    # Verification croisee avec tokens
    if tokens and has_overwrittenby:
        expected = tokens.get("overwrittenby_mchk", "")
        if expected:
            pattern = re.escape(expected)
            if not re.search(pattern, content, re.IGNORECASE):
                issues.append({
                    "rule": "M04",
                    "severity": "warning",
                    "message": f"OverWrittenBy ne correspond pas au token attendu: {expected}",
                })

    return issues


def check_m05(content, tokens=None):
    """M05 — Encodage ISO-8859-1 + CRLF."""
    issues = []
    raw, _ = read_file_content.__defaults__ if hasattr(read_file_content, '__defaults__') else (None, None)
    # On re-lit le fichier en mode binaire pour verifier l'encodage
    # Cette verification est faite dans check_encoding separement
    return issues


def check_encoding(raw_bytes):
    """Verifie l'encodage ISO-8859-1 + CRLF."""
    issues = []

    # Verifier fins de ligne CRLF
    text = raw_bytes.decode('iso-8859-1')
    lines_lf_only = 0
    i = 0
    while i < len(raw_bytes):
        if raw_bytes[i:i+1] == b'\n' and (i == 0 or raw_bytes[i-1:i] != b'\r'):
            lines_lf_only += 1
        i += 1

    if lines_lf_only > 0:
        issues.append({
            "rule": "M05",
            "severity": "error",
            "message": f"Fins de ligne LF detectees ({lines_lf_only} occurrences). Attendu: CRLF",
        })

    # Verifier pas de BOM UTF-8
    if raw_bytes[:3] == b'\xef\xbb\xbf':
        issues.append({
            "rule": "M05",
            "severity": "error",
            "message": "BOM UTF-8 detecte. Le fichier doit etre en ISO-8859-1 sans BOM",
        })

    # Verifier encodage ISO-8859-1 (pas de sequences multi-octets UTF-8)
    try:
        raw_bytes.decode('ascii')
    except UnicodeDecodeError:
        # Contient des octets > 127 — verifier que ce n'est pas du UTF-8 valide avec multi-octets
        try:
            raw_bytes.decode('utf-8')
            # Si ca decode en UTF-8 et qu'il y a des octets > 127, c'est probablement du UTF-8
            has_high_bytes = any(b > 127 for b in raw_bytes)
            if has_high_bytes:
                # Verifier si c'est du UTF-8 multi-octets
                has_utf8_multibyte = bool(re.search(b'[\xc0-\xdf][\x80-\xbf]|[\xe0-\xef][\x80-\xbf]{2}', raw_bytes))
                if has_utf8_multibyte:
                    issues.append({
                        "rule": "M05",
                        "severity": "error",
                        "message": "Fichier encode en UTF-8 avec caracteres multi-octets. Attendu: ISO-8859-1",
                    })
        except UnicodeDecodeError:
            pass  # Ni ASCII ni UTF-8 valide — probablement ISO-8859-1, OK

    return issues


def check_mandatory_functions(content, tokens=None):
    """Verifie la presence des fonctions obligatoires du pattern mchk."""
    issues = []

    # Fonctions obligatoires (categories: proprietes, champs, exposition, controle, init, pre/post, autorisations)
    mandatory_patterns = [
        (r'(?i)\bGet_\w+_ChkData\b', "Get_{TABLE}_ChkData (proprietes)"),
        (r'(?i)\bGet_\w+_FieldProperties\b', "Get_{TABLE}_FieldProperties (proprietes)"),
        (r'(?i)\bGet_\w+_FieldNames_Min\b', "Get_{TABLE}_FieldNames_Min (champs)"),
        (r'(?i)\bGet_\w+_FieldNames_All\b', "Get_{TABLE}_FieldNames_All (champs)"),
        (r'(?i)\bGet_\w+_Record\b', "Get_{TABLE}_Record (exposition)"),
        (r'(?i)\bGet_\w+_Lib\b', "Get_{TABLE}_Lib (exposition)"),
        (r'(?i)\bGet_\w+_Key\b', "Get_{TABLE}_Key (exposition)"),
        (r'(?i)\bGet_\w+_Reservation\b', "Get_{entity}_Reservation (exposition)"),
        (r'(?i)\bCheck_\w+_Key\b', "Check_{TABLE}_Key (controle)"),
        (r'(?i)\bCheck_\w+_FieldCod\b', "Check_{TABLE}_FieldCod (controle)"),
        (r'(?i)\bInitialize_\w+_New\b', "Initialize_{entity}_New (init)"),
        (r'(?i)\bInitialize_\w+_PostFetch\b', "Initialize_{entity}_PostFetch (init)"),
        (r'(?i)\bInitialize_\w+_Duplication\b', "Initialize_{entity}_Duplication (init)"),
        (r'(?i)\bInitialize_\w+_PreInsert\b', "Initialize_{entity}_PreInsert (pre/post)"),
        (r'(?i)\bInitialize_\w+_PostInsert\b', "Initialize_{entity}_PostInsert (pre/post)"),
        (r'(?i)\bInitialize_\w+_PreUpdate\b', "Initialize_{entity}_PreUpdate (pre/post)"),
        (r'(?i)\bInitialize_\w+_PostUpdate\b', "Initialize_{entity}_PostUpdate (pre/post)"),
        (r'(?i)\bInitialize_\w+_PreDelete\b', "Initialize_{entity}_PreDelete (pre/post)"),
        (r'(?i)\bInitialize_\w+_PostDelete\b', "Initialize_{entity}_PostDelete (pre/post)"),
        (r'(?i)\bAuthorize_\w+_Insert\b', "Authorize_{entity}_Insert (autorisations)"),
        (r'(?i)\bAuthorize_\w+_Update\b', "Authorize_{entity}_Update (autorisations)"),
        (r'(?i)\bAuthorize_\w+_Delete\b', "Authorize_{entity}_Delete (autorisations)"),
    ]

    missing = []
    for pattern, name in mandatory_patterns:
        if not re.search(pattern, content):
            missing.append(name)

    if missing:
        issues.append({
            "rule": "STRUCT",
            "severity": "error",
            "message": f"Fonctions obligatoires manquantes: {', '.join(missing)}",
        })

    return issues


def check_naming_coherence(content, tokens):
    """Verifie la coherence des noms avec les tokens."""
    issues = []
    if not tokens:
        return issues

    table_maj = tokens.get("TABLE_MAJUSCULE", "")
    nom_vue = tokens.get("NomVue", "")

    # Verifier que le nom de la table apparait dans les fonctions
    if table_maj:
        if not re.search(r'(?i)ChkData_' + re.escape(table_maj), content):
            issues.append({
                "rule": "NAMING",
                "severity": "warning",
                "message": f"ChkData_{table_maj} non trouve dans le fichier",
            })

    # Verifier que RS_{NomVue} est declare
    if nom_vue:
        if not re.search(r'(?i)RS_' + re.escape(nom_vue), content):
            issues.append({
                "rule": "NAMING",
                "severity": "warning",
                "message": f"RS_{nom_vue} non trouve dans le fichier",
            })

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Valide un fichier Module Check (.dhsp) selon les regles M01-M05"
    )
    parser.add_argument("--path", required=True,
                        help="Chemin du fichier .dhsp a valider")
    parser.add_argument("--tokens", default=None,
                        help="Chemin vers un fichier JSON de tokens (optionnel, pour verifications croisees)")

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
    all_issues.extend(check_m01(content, tokens))
    all_issues.extend(check_m02(content, tokens))
    all_issues.extend(check_m03(content, tokens))
    all_issues.extend(check_m04(content, tokens))
    all_issues.extend(check_encoding(raw_bytes))
    all_issues.extend(check_mandatory_functions(content, tokens))
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
