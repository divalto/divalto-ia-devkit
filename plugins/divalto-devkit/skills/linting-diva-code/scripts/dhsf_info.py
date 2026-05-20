#!/usr/bin/env python3
"""Extract metrics from a .dhsf file (Divalto screen mask).

Usage:
    py dhsf_info.py --path <chemin_vers_fichier.dhsf>

Output: JSON to stdout.
"""

import argparse
import json
import os
import re
import sys


# Widget types to count (top-level section names inside a [page])
WIDGET_TYPES = [
    "obj_texte",
    "champ",
    "champ_tableau",
    "tableau",
    "groupbox",
    "multi_choix",
    "multi_choix_tableau",
    "groupe_radio",
    "bouton_graphique",
    "arbre",
    "panel_wpf",
    "grille_wpf",
    "onglet_page",
]


def parse_dhsf(path: str) -> dict:
    file_size = os.path.getsize(path)

    with open(path, encoding="iso-8859-1") as f:
        lines = f.readlines()

    # --- [masque] section ---
    is_zoom = False
    dernier_id = 0
    dernier_id_page = 0
    in_masque = False

    # --- [enregistrements] section ---
    enregistrements_count = 0
    in_enregistrements = False

    # --- [diva] / [/diva] section ---
    in_diva = False
    diva_lines = 0
    procedures_count = 0
    functions_count = 0
    includes_count = 0
    modules_count = 0

    # --- pages & onglets ---
    pages_count = 0
    onglets_count = 0

    # --- widgets per type ---
    widgets = {wt: 0 for wt in WIDGET_TYPES}

    # Track which page we are in and whether it has child widgets
    current_page_num = None
    page_has_children = {}  # page_num -> bool

    # Depth tracking: we need to know if a [widget_type] is a direct child
    # of a [page] vs nested inside another widget. For simplicity, we count
    # all occurrences of widget-type sections that appear while inside a page.
    in_page = False

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        stripped = line.strip()

        # Detect top-level sections (lines starting with '[')
        section_match = re.match(r"^\[(\w+)\]", stripped)

        if section_match:
            section_name = section_match.group(1).lower()

            # End previous contexts when hitting a new top-level section
            if section_name in ("masque", "defaut", "enregistrements", "onglet",
                                "page", "ressources", "diva", "diva_base"):
                in_masque = False
                in_enregistrements = False

            if section_name == "masque":
                in_masque = True
                continue

            if section_name == "defaut":
                continue

            if section_name == "enregistrements":
                in_enregistrements = True
                continue

            if section_name == "onglet":
                onglets_count += 1
                in_page = False
                continue

            if section_name == "page":
                pages_count += 1
                in_page = True
                current_page_num = None  # will be set by numero= line
                continue

            if section_name == "ressources":
                in_page = False
                continue

            if section_name == "diva":
                in_diva = True
                in_page = False
                continue

            # [/diva] ends the diva block
            # Also handle via the /diva check below

            # Widget types (can appear inside a page)
            if section_name in widgets:
                widgets[section_name] += 1
                if current_page_num is not None:
                    page_has_children[current_page_num] = True
                continue

        # Check for [/diva]
        if stripped.lower() == "[/diva]":
            in_diva = False
            continue

        # --- Parse [masque] fields ---
        if in_masque:
            m = re.match(r"\s*type_masque\s*=\s*(\d+)", stripped)
            if m:
                is_zoom = int(m.group(1)) == 2

            m = re.match(r"\s*dernier_id\s*=\s*(\d+)", stripped)
            if m:
                dernier_id = int(m.group(1))

            m = re.match(r"\s*dernier_id_page\s*=\s*(\d+)", stripped)
            if m:
                dernier_id_page = int(m.group(1))

        # --- Count [enregistrements] lines (non-comment, non-empty) ---
        if in_enregistrements:
            # A new top-level section ends enregistrements
            if section_match and section_match.group(1).lower() != "enregistrements":
                in_enregistrements = False
            elif not stripped.startswith(";") and stripped:
                enregistrements_count += 1

        # --- Page numero ---
        if in_page and current_page_num is None:
            m = re.match(r"\s*numero\s*=\s*(\d+)", stripped)
            if m:
                current_page_num = int(m.group(1))
                if current_page_num not in page_has_children:
                    page_has_children[current_page_num] = False

        # --- [diva] content ---
        if in_diva:
            diva_lines += 1

            # Public Procedure
            if re.match(r"^Public\s+Procedure\b", stripped):
                procedures_count += 1

            # Public Function
            if re.match(r"^Public\s+Function\b", stripped):
                functions_count += 1

            # Include
            if re.match(r"^Include\s+", stripped):
                includes_count += 1

            # Module
            if re.match(r"^Module\s+", stripped):
                modules_count += 1

    widgets_total = sum(widgets.values())

    # Empty pages: pages with no child widgets
    empty_pages = sorted(
        num for num, has_children in page_has_children.items()
        if not has_children
    )

    result = {
        "path": os.path.abspath(path),
        "file_size": file_size,
        "is_zoom": is_zoom,
        "dernier_id": dernier_id,
        "dernier_id_page": dernier_id_page,
        "pages_count": pages_count,
        "onglets_count": onglets_count,
        "enregistrements_count": enregistrements_count,
        "widgets": widgets,
        "widgets_total": widgets_total,
        "diva_lines": diva_lines,
        "procedures_count": procedures_count,
        "functions_count": functions_count,
        "includes_count": includes_count,
        "modules_count": modules_count,
        "empty_pages": empty_pages,
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract metrics from a .dhsf file (Divalto screen mask)."
    )
    parser.add_argument(
        "--path", required=True, help="Path to the .dhsf file to analyze."
    )
    args = parser.parse_args()

    if not os.path.isfile(args.path):
        print(f"Error: file not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    result = parse_dhsf(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
