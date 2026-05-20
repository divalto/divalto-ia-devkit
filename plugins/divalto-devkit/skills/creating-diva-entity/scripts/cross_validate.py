#!/usr/bin/env python3
"""Verifie la coherence entre les 3 fichiers generes d'une entite DIVA.

Usage:
    py .claude/skills/creating-diva-entity/scripts/cross_validate.py \
        --rsql output/fichier.dhsq --mchk output/fichier.dhsp --zoom output/fichier.dhsp \
        --tokens tokens.json

Sortie JSON: {valid, errors, warnings, checks}
Exit codes: 0 = succes (meme si warnings), 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import re
import sys


def read_file(path):
    """Lit un fichier en ISO-8859-1."""
    try:
        with open(path, 'r', encoding='iso-8859-1') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Fichier non trouve : {path}", file=sys.stderr)
        sys.exit(1)


def check_nomvue_coherence(rsql_content, mchk_content, zoom_content, tokens):
    """XV01 — NomVue utilise de maniere coherente dans les 3 fichiers."""
    issues = []
    nom_vue = tokens.get("NomVue", "")
    if not nom_vue:
        return issues

    for name, content in [("rsql", rsql_content), ("mchk", mchk_content), ("zoom", zoom_content)]:
        if not re.search(re.escape(nom_vue), content, re.IGNORECASE):
            issues.append({
                "rule": "XV01",
                "severity": "error",
                "message": f"NomVue '{nom_vue}' absent du fichier {name}",
            })
    return issues


def check_rsql_reference_in_zoom(zoom_content, tokens):
    """XV02 — Le zoom reference le bon fichier RecordSql compile."""
    issues = []
    fichier_rsql = tokens.get("fichier_rsql_compile", "")
    if fichier_rsql and not re.search(re.escape(fichier_rsql), zoom_content, re.IGNORECASE):
        issues.append({
            "rule": "XV02",
            "severity": "error",
            "message": f"RecordSql compile '{fichier_rsql}' absent du fichier zoom",
        })
    return issues


def check_mchk_module_in_zoom(zoom_content, tokens):
    """XV03 — Le zoom reference le bon module mchk."""
    issues = []
    module_mchk = tokens.get("module_mchk", "")
    if module_mchk and not re.search(re.escape(module_mchk), zoom_content, re.IGNORECASE):
        issues.append({
            "rule": "XV03",
            "severity": "error",
            "message": f"Module mchk '{module_mchk}' absent du fichier zoom",
        })
    return issues


def check_prefix_coherence(mchk_content, zoom_content, tokens):
    """XV04 — Le meme prefixe domaine est utilise dans mchk et zoom."""
    issues = []
    prefix = tokens.get("PREFIX_", "")
    if not prefix:
        return issues

    for name, content in [("mchk", mchk_content), ("zoom", zoom_content)]:
        all_prefixes = ["GT_", "RT_", "GG_", "CC_", "GA_"]
        wrong_prefixes = [p for p in all_prefixes if p != prefix]
        for wp in wrong_prefixes:
            pattern = r'(?i)\b' + re.escape(wp) + r'(Pre|Post)(Insert|Update|Delete)_recordSql\b'
            if re.search(pattern, content):
                issues.append({
                    "rule": "XV04",
                    "severity": "error",
                    "message": f"Prefixe incorrect {wp} dans {name} (attendu: {prefix})",
                })
    return issues


def check_overwrittenby_coherence(mchk_content, zoom_content, tokens):
    """XV05 — OverWrittenBy present et coherent dans mchk et zoom."""
    issues = []
    owb_mchk = tokens.get("overwrittenby_mchk", "")
    owb_zoom = tokens.get("overwrittenby_zoom", "")

    if owb_mchk and not re.search(re.escape(owb_mchk), mchk_content, re.IGNORECASE):
        issues.append({
            "rule": "XV05",
            "severity": "warning",
            "message": f"OverWrittenBy mchk '{owb_mchk}' absent du fichier mchk",
        })
    if owb_zoom and not re.search(re.escape(owb_zoom), zoom_content, re.IGNORECASE):
        issues.append({
            "rule": "XV05",
            "severity": "warning",
            "message": f"OverWrittenBy zoom '{owb_zoom}' absent du fichier zoom",
        })
    return issues


def check_champkle_coherence(rsql_content, mchk_content, zoom_content, tokens):
    """XV06 — Le champ cle est reference dans les 3 fichiers."""
    issues = []
    champ_cle = tokens.get("ChampCle", "")
    if not champ_cle:
        return issues

    for name, content in [("rsql", rsql_content), ("mchk", mchk_content), ("zoom", zoom_content)]:
        if not re.search(re.escape(champ_cle), content, re.IGNORECASE):
            issues.append({
                "rule": "XV06",
                "severity": "warning",
                "message": f"ChampCle '{champ_cle}' absent du fichier {name}",
            })
    return issues


def check_alias_block(alias_content, tokens):
    """XV07 — Le bloc d'alias contient 16 alias avec le bon NomVue et PREFIX_."""
    issues = []
    if not alias_content:
        return issues

    nom_vue = tokens.get("NomVue", "")
    prefix = tokens.get("PREFIX_", "")

    # Compter les lignes Alias
    alias_lines = [l for l in alias_content.split('\n') if l.strip().startswith('Alias ')]
    if len(alias_lines) != 16:
        issues.append({
            "rule": "XV07",
            "severity": "error",
            "message": f"Bloc d'alias : {len(alias_lines)} alias trouves, 16 attendus",
        })

    # Verifier que NomVue est present dans les alias
    if nom_vue:
        for line in alias_lines:
            if nom_vue not in line:
                issues.append({
                    "rule": "XV07",
                    "severity": "error",
                    "message": f"NomVue '{nom_vue}' absent d'une ligne alias: {line.strip()}",
                })
                break

    # Verifier le prefixe
    if prefix:
        for line in alias_lines:
            if prefix not in line:
                issues.append({
                    "rule": "XV07",
                    "severity": "error",
                    "message": f"PREFIX_ '{prefix}' absent d'une ligne alias: {line.strip()}",
                })
                break

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Verifie la coherence entre les 3 fichiers generes d'une entite DIVA"
    )
    parser.add_argument("--rsql", required=True,
                        help="Chemin du fichier RecordSql (.dhsq)")
    parser.add_argument("--mchk", required=True,
                        help="Chemin du fichier Module Check (.dhsp)")
    parser.add_argument("--zoom", required=True,
                        help="Chemin du fichier Zoom SQL (.dhsp)")
    parser.add_argument("--alias", default=None,
                        help="Chemin du fichier bloc d'alias (optionnel)")
    parser.add_argument("--tokens", required=True,
                        help="Chemin vers le fichier JSON de tokens")

    args = parser.parse_args()

    # Lire les tokens
    try:
        with open(args.tokens, "r", encoding="utf-8") as f:
            tokens = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Erreur lecture tokens : {e}", file=sys.stderr)
        sys.exit(1)

    # Lire les fichiers
    rsql_content = read_file(args.rsql)
    mchk_content = read_file(args.mchk)
    zoom_content = read_file(args.zoom)
    alias_content = read_file(args.alias) if args.alias else None

    # Executer toutes les verifications
    all_issues = []
    all_issues.extend(check_nomvue_coherence(rsql_content, mchk_content, zoom_content, tokens))
    all_issues.extend(check_rsql_reference_in_zoom(zoom_content, tokens))
    all_issues.extend(check_mchk_module_in_zoom(zoom_content, tokens))
    all_issues.extend(check_prefix_coherence(mchk_content, zoom_content, tokens))
    all_issues.extend(check_overwrittenby_coherence(mchk_content, zoom_content, tokens))
    all_issues.extend(check_champkle_coherence(rsql_content, mchk_content, zoom_content, tokens))
    if alias_content:
        all_issues.extend(check_alias_block(alias_content, tokens))

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
