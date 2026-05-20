#!/usr/bin/env python3
"""_dhsd_parser.py -- Mini-parseur de fichier dictionnaire Divalto (.dhsd).

**Vendoring selectif** : extraction de la fonction `parse_dhsd_table` depuis
`managing-diva-dictionaries/scripts/validate_dhsd.py`. Le validateur complet
embarque les regles D01-D11 qui ne sont pas utiles au relecteur ; on ne garde
que l'extraction structurelle (champs + indexes).

API :
- parse_dhsd_file(path, table_name) -> {"fields": [...], "indexes": [...], "taille": N}

Source canonique : managing-diva-dictionaries/scripts/validate_dhsd.py
"""
from __future__ import annotations

from pathlib import Path


def parse_dhsd_fields(content: str, table_name: str) -> list[dict]:
    """Extrait la liste des champs declares dans [CHAMPS] de la table cible.

    Reproduit la logique de parse_dhsd_table de validate_dhsd.py.
    """
    lines = content.splitlines()
    in_target_table = False
    in_champs = False
    champs: list[dict] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line == "[TABLE]":
            j = i + 1
            found = False
            while j < len(lines):
                tl = lines[j].strip()
                if tl.startswith("Nom="):
                    parts = tl[4:].split(",", 1)
                    if parts[0] == table_name:
                        in_target_table = True
                        found = True
                    break
                if tl.startswith("[") and not tl.startswith("[TABLE"):
                    break
                j += 1
            if not found:
                i = j
                continue

        if in_target_table:
            if line == "[CHAMPS]":
                in_champs = True
                i += 1
                continue
            if line == "[/CHAMPS]":
                break
            if in_champs and line.startswith("Nom="):
                parts = line[4:].split(",")
                if parts:
                    champs.append({
                        "name": parts[0],
                        "position": int(parts[1]) if len(parts) > 1 and parts[1].strip().isdigit() else None,
                    })

        i += 1
    return champs


def parse_dhsd_indexes(content: str, table_name: str) -> list[dict]:
    """Extrait la liste des index declares dans [INDEX]...[/INDEX] de la table cible.

    Format attendu (aligne sur le standard Divalto) :
        [INDEX]
        Nom=IdxTiers,Ce1,TIERS,...
        Nom=IdxDate,Ce2,DateCre,...
        [/INDEX]
    """
    lines = content.splitlines()
    in_target_table = False
    in_indexes = False
    indexes: list[dict] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line == "[TABLE]":
            j = i + 1
            found = False
            while j < len(lines):
                tl = lines[j].strip()
                if tl.startswith("Nom="):
                    parts = tl[4:].split(",", 1)
                    if parts[0] == table_name:
                        in_target_table = True
                        found = True
                    break
                if tl.startswith("[") and not tl.startswith("[TABLE"):
                    break
                j += 1
            if not found:
                i = j
                continue

        if in_target_table:
            if line == "[INDEX]":
                in_indexes = True
                i += 1
                continue
            if line == "[/INDEX]":
                in_indexes = False
                in_target_table = False
                break
            if in_indexes and line.startswith("Nom="):
                parts = line[4:].split(",")
                if parts:
                    indexes.append({
                        "name": parts[0],
                        "ce": parts[1] if len(parts) > 1 else "",
                        "fields": [p for p in parts[2:] if p and not p.isdigit()],
                    })

        i += 1
    return indexes


def parse_dhsd_file(path: Path, table_name: str) -> dict:
    content = path.read_text(encoding="iso-8859-1")
    return {
        "fields": parse_dhsd_fields(content, table_name),
        "indexes": parse_dhsd_indexes(content, table_name),
    }
