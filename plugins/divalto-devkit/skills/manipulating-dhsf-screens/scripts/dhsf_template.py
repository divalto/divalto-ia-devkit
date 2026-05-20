#!/usr/bin/env python3
"""Generate a .dhsf file from a template by replacing placeholder tokens.

Usage:
    py dhsf_template.py --template zoom --output <chemin.dhsf> --params <json>

Templates disponibles :
  zoom   : template_zoom_sql.dhsf  (zoom SQL standard)
  crud   : template_ecran_crud.dhsf (ecran CRUD)
  simple : template_simple.dhsf     (dialogue minimal)

Parametres JSON (--params) :
  {
    "rsql_file":       "rtlrsfamrglt",       // RecordSql sans extension (.dhoq)
    "vue_lower":       "famrglt",             // nom de vue minuscule
    "vue_camel":       "FamRglt",             // nom de vue CamelCase
    "champ_cle":       "rgltfam",             // champ cle minuscule
    "champ_cle_label": "Code",                // libelle du champ cle
    "libelle_masque":  "familles de reglement",// description du masque
    "fichier_aide":    "rtfaide",             // fichier aide (sans extension)
    "masque_file":     "rtez099_sql",         // nom du fichier masque (sans .dhsf)
    "titre_creation":  "Famille a creer",     // titre popup creation
    "utilisateur":     "ROOT"                 // utilisateur createur
  }

Tokens reserves dans les templates :
  MonEntite, monrecordsql, mavue, MaVue, mavue_sel, MaVue_Sel,
  codecle, gtfaide, template_zoom_sql / template_ecran_crud / template_simple

Sortie : fichier .dhsf en ISO-8859-1 + CRLF, pret pour le compilateur.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

TEMPLATE_MAP = {
    "zoom": "template_zoom_sql.dhsf",
    "crud": "template_ecran_crud.dhsf",
    "simple": "template_simple.dhsf",
}


# ---------------------------------------------------------------------------
# Token replacement engine
# ---------------------------------------------------------------------------

def build_replacements(params: dict, template_name: str) -> list[tuple[str, str]]:
    """Build the ordered list of (old, new) replacements.

    Order matters: longer/more specific tokens first to avoid partial matches.
    e.g., 'MaVue_Sel' before 'MaVue', 'mavue_sel' before 'mavue'.
    """
    vue_lower = params.get("vue_lower", "mavue")
    vue_camel = params.get("vue_camel", "MaVue")
    rsql_file = params.get("rsql_file", "monrecordsql")
    champ_cle = params.get("champ_cle", "codecle")
    champ_cle_label = params.get("champ_cle_label", "Code")
    libelle_masque = params.get("libelle_masque", "MonEntite")
    fichier_aide = params.get("fichier_aide", "gtfaide")
    masque_file = params.get("masque_file", template_name.replace(".dhsf", ""))
    titre_creation = params.get("titre_creation", "Entite a creer")
    utilisateur = params.get("utilisateur", "ROOT")

    # Template basename without extension (for SetModuleInfo)
    tpl_basename = template_name.replace(".dhsf", "")

    # Ordered replacements (most specific first)
    replacements = [
        # CamelCase aliases (before lowercase)
        (f"{vue_camel}_Sel",    f"{vue_camel}_Sel")  if vue_camel != "MaVue" else None,
        ("MaVue_Sel",           f"{vue_camel}_Sel"),
        ("MaVue",               vue_camel),
        # Lowercase aliases (longer first)
        (f"{vue_lower}_sel",    f"{vue_lower}_sel")  if vue_lower != "mavue" else None,
        ("mavue_sel",           f"{vue_lower}_sel"),
        ("mavue",               vue_lower),
        # RecordSql file
        ("monrecordsql",        rsql_file),
        # Key field
        ("codecle",             champ_cle),
        # Aide file
        ("gtfaide",             fichier_aide),
        # Libelle masque (in [masque] libelle=)
        ("Zoom sur MonEntite",  f"Zoom sur {libelle_masque}"),
        ("MonEntite",           libelle_masque),
        # Titre creation (popup page 2)
        ("Entite a creer",      titre_creation),
        # SetModuleInfo filename
        (tpl_basename,          masque_file),
        # Utilisateur
        # (only replace in the masque section, be careful)
    ]

    # Remove None entries (no-op when token == replacement)
    return [(old, new) for old, new in replacements if old is not None and old != new]


def update_timestamp(content: str) -> str:
    """Update the header timestamp and date_modification."""
    now = datetime.now()

    # Header: ;>xwin4obj ... YYYYMMDDHHMMSS
    timestamp_14 = now.strftime("%Y%m%d%H%M%S")
    content = _replace_header_timestamp(content, timestamp_14)

    # [masque] date_modification
    date_fr = now.strftime("%d/%m/%Y")
    content = _replace_date_modification(content, date_fr)

    return content


def _replace_header_timestamp(content: str, new_ts: str) -> str:
    """Replace the 14-digit timestamp in the ;>xwin4obj header line."""
    import re
    return re.sub(
        r"(;>xwin4obj\s+\d+\.\d+\s+)\d{14}",
        rf"\g<1>{new_ts}",
        content,
        count=1,
    )


def _replace_date_modification(content: str, new_date: str) -> str:
    """Replace date_modification value in [masque]."""
    import re
    return re.sub(
        r'(date_modification=")[^"]*(")',
        rf"\g<1>{new_date}\2",
        content,
        count=1,
    )


def apply_replacements(content: str, replacements: list[tuple[str, str]]) -> str:
    """Apply all token replacements to the content."""
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def validate_no_placeholders(content: str, template_name: str) -> list[str]:
    """Check that no placeholder tokens remain in the output."""
    placeholders = [
        "MonEntite", "monrecordsql", "codecle", "Entite a creer",
    ]
    # Only check view placeholders if template is zoom or crud
    if "zoom" in template_name or "crud" in template_name:
        # Check for unreplaced mavue/MaVue (but not as substring of real names)
        import re
        # Look for standalone "mavue" not part of a longer word
        if re.search(r'\bmavue\b', content):
            return ["mavue (token non remplace)"]
        if re.search(r'\bMaVue\b', content):
            return ["MaVue (token non remplace)"]

    warnings = []
    for ph in placeholders:
        if ph in content:
            warnings.append(f"{ph} (token non remplace)")
    return warnings


# ---------------------------------------------------------------------------
# Main generation flow
# ---------------------------------------------------------------------------

def generate(template_key: str, params: dict, output_path: str) -> dict:
    """Generate a .dhsf file from a template.

    Returns a result dict with status, warnings, and output path.
    """
    # Resolve template
    if template_key not in TEMPLATE_MAP:
        return {"success": False, "error": f"Template inconnu: {template_key}. Choix: {list(TEMPLATE_MAP.keys())}"}

    template_file = TEMPLATES_DIR / TEMPLATE_MAP[template_key]
    if not template_file.exists():
        return {"success": False, "error": f"Fichier template introuvable: {template_file}"}

    # Read template (ISO-8859-1)
    content = template_file.read_text(encoding="iso-8859-1")

    # Build and apply replacements
    replacements = build_replacements(params, TEMPLATE_MAP[template_key])
    content = apply_replacements(content, replacements)

    # Update timestamp
    content = update_timestamp(content)

    # Remove ALL ;-- comments (instructions and decorations -- invalid in .dhsf format)
    import re
    content = re.sub(r'^;--[^\r\n]*\r?\n', '', content, flags=re.MULTILINE)

    # Remove Libelle widgets if no_libelle is set
    if params.get("no_libelle"):
        # Remove complete widget blocks that reference donnee=xxx,lib,xxx
        # A widget block starts with [champ_tableau] or [champ] and ends at the next [champ...] or [onglet]
        lines = content.split("\n")
        cleaned = []
        skip = False
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            # Start of a widget block
            if stripped in ("[champ_tableau]", "[champ]"):
                # Look ahead: does this block contain donnee=...,lib,...?
                has_lib = False
                for j in range(i + 1, min(i + 30, len(lines))):
                    fwd = lines[j].strip().lower()
                    if fwd.startswith("donnee=") and ",lib," in fwd:
                        has_lib = True
                        break
                    if fwd in ("[champ_tableau]", "[champ]", "[onglet]", "[page]"):
                        break
                skip = has_lib
            if not skip:
                cleaned.append(line)
            # End of skipped block: next widget or section starts
            if skip and i > 0:
                next_stripped = lines[min(i + 1, len(lines) - 1)].strip().lower() if i + 1 < len(lines) else ""
                if next_stripped in ("[champ_tableau]", "[champ]", "[onglet]", "[page]", ""):
                    if next_stripped != "":
                        skip = False
        content = "\n".join(cleaned)

    # Add extra fields if provided
    extra_fields = params.get("fields", [])
    if extra_fields and template_key == "zoom":
        vue = params.get("vue_lower", "mavue")
        lines = content.split("\n")
        new_lines = []
        last_id = 12  # default last id in template

        # Find the highest id= in the file to avoid conflicts
        for line in lines:
            m = re.match(r'\s*id=(\d+)', line.strip())
            if m:
                last_id = max(last_id, int(m.group(1)))
        next_id = last_id + 1

        # Patterns for each zone
        fiche_field = """  [obj_texte]
  [presentation]
   position={pos_y},5
   taille=9,50
   id={id_label}
   wstyle="STD"
  [texte]
   texte="{label}"
 [champ]
  [presentation]
   position={pos_y},56
   taille=9,80
   id={id_field}
   wstyle="ZOOM_SAISI"
  [description]
   donnee={vue},{field_lower},{vue}
  [touches]
   f1=1"""

        tableau_col = """  [champ_tableau]
   [presentation]
    position=15,40
    taille=10,80
    id={id_col}
    wstyle="TABLEAU_AFF"
   [description]
    donnee={vue},{field_lower},{vue}
    saisie=non
   [traitements]
    microbol_click=8002
   [info_bulle]
   texte="{label}"
   [param_colonne]
    titre="{label}"
    fl_aff=oui
    largeur_col=80
    wstyle="ENTETE_COLONNE" """

        filtre_field = """ [obj_texte]
  [presentation]
   position={pos_y},5
   taille=9,43
   id={id_label}
   wstyle="STD"
  [texte]
   texte="{label}"
 [champ]
  [presentation]
   position={pos_y},50
   taille=9,80
   id={id_field}
   wstyle="CHAMP_SAISI"
  [description]
   donnee={vue},{field_lower},{vue}_sel
  [touches]
   f1=1"""

        # --- Insert in FICHE (page 2) : after last [champ] before [page] numero=3 ---
        fiche_insert_blocks = []
        fiche_y = 18  # start position after Code (pos 8)
        for f in extra_fields:
            name = f["name"]
            label = f.get("label", name)
            fiche_insert_blocks.append(fiche_field.format(
                pos_y=fiche_y, id_label=next_id, id_field=next_id+1,
                label=label, vue=vue, field_lower=name.lower()
            ))
            next_id += 2
            fiche_y += 10

        # --- Insert in TABLEAU (page 3) : after last [champ_tableau] before selection ---
        tableau_insert_blocks = []
        for f in extra_fields:
            name = f["name"]
            label = f.get("label", name)
            tableau_insert_blocks.append(tableau_col.format(
                id_col=next_id, label=label, vue=vue, field_lower=name.lower()
            ))
            next_id += 1

        # --- Insert in SELECTION (page 3) : after last selection [champ] before [page] numero=4 ---
        filtre_insert_blocks = []
        filtre_y = 36  # start after Code (16) and possibly Libelle (26)
        if params.get("no_libelle"):
            filtre_y = 26
        for f in extra_fields:
            name = f["name"]
            label = f.get("label", name)
            filtre_insert_blocks.append(filtre_field.format(
                pos_y=filtre_y, id_label=next_id, id_field=next_id+1,
                label=label, vue=vue, field_lower=name.lower()
            ))
            next_id += 2
            filtre_y += 10

        # Now insert into content at the right positions
        # Strategy: find markers and insert blocks
        result_lines = []
        in_page3 = False
        inserted_fiche = False
        inserted_tableau = False
        inserted_filtre = False

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip().lower()

            # Detect page transitions
            if stripped == "[page]" and i + 1 < len(lines):
                next_line = lines[i+1].strip().lower()
                # Before page 3: insert fiche fields
                if "numero=3" in next_line and not inserted_fiche and fiche_insert_blocks:
                    for block in fiche_insert_blocks:
                        result_lines.extend(block.split("\n"))
                    inserted_fiche = True

                # Before page 4: insert filtre fields
                if "numero=4" in next_line and not inserted_filtre and filtre_insert_blocks:
                    for block in filtre_insert_blocks:
                        result_lines.extend(block.split("\n"))
                    inserted_filtre = True

            # After last [champ_tableau] in page 3 (before selection [obj_texte])
            if in_page3 and stripped == "[obj_texte]" and not inserted_tableau and tableau_insert_blocks:
                for block in tableau_insert_blocks:
                    result_lines.extend(block.split("\n"))
                inserted_tableau = True

            # Track page 3
            if stripped == "[tableau]":
                in_page3 = True
            if stripped == "[page]" and in_page3 and i + 1 < len(lines) and "numero=3" not in lines[i+1].strip().lower():
                in_page3 = False

            result_lines.append(line)
            i += 1

        content = "\n".join(result_lines)

    # Validate
    warnings = validate_no_placeholders(content, template_key)

    # Write output (ISO-8859-1 + CRLF)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Normalize line endings to CRLF
    content = content.replace("\r\n", "\n").replace("\n", "\r\n")

    output.write_bytes(content.encode("iso-8859-1"))

    result = {
        "success": True,
        "output": str(output.resolve()),
        "template": template_key,
        "file_size": output.stat().st_size,
        "replacements_applied": len(replacements),
        "warnings": warnings,
    }

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a .dhsf file from a template with token replacement."
    )
    parser.add_argument(
        "--template", required=True, choices=list(TEMPLATE_MAP.keys()),
        help="Template to use: zoom, crud, simple"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output file path (.dhsf)"
    )
    parser.add_argument(
        "--params", required=True,
        help="JSON string with replacement parameters"
    )
    args = parser.parse_args()

    # Parse params
    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in --params: {e}", file=sys.stderr)
        sys.exit(1)

    result = generate(args.template, params, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["success"]:
        sys.exit(1)
    if result["warnings"]:
        sys.exit(0)  # Warnings are non-fatal


if __name__ == "__main__":
    main()
