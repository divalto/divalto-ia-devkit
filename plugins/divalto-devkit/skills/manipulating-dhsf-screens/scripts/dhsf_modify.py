#!/usr/bin/env python3
"""Modifications incrementales sur un fichier .dhsf existant.

Usage:
    py dhsf_modify.py --path <fichier.dhsf> --action <action> --params <json>

Actions :
  add-field     Ajoute un champ (obj_texte + champ) a une page
  add-column    Ajoute une colonne (champ_tableau) a un tableau
  add-page      Ajoute une page avec onglet_page
  add-groupbox  Ajoute un groupbox englobant une liste de champs existants
                (mode wrapper-only -- champs non repositionnes)
  validate      Re-valide le layout du masque (regles R1-R5)

Chaque action met a jour automatiquement dernier_id et le timestamp.
Le fichier est modifie en place (ISO-8859-1 + CRLF).

Sortie : JSON sur stdout avec le detail des modifications.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Import the parser from the same directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dhsf_parser import parse_dhsf


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Standard indentation in .dhsf files
INDENT_1 = " "      # element inside page
INDENT_2 = "  "     # sub-section inside element
INDENT_3 = "   "    # attribute inside sub-section


# ---------------------------------------------------------------------------
# ID management
# ---------------------------------------------------------------------------

def compute_max_id(tree: dict) -> int:
    """Find the maximum id used across all elements."""
    max_id = 0

    def _walk(elements):
        nonlocal max_id
        for elem in elements:
            eid = elem.get("id", 0)
            if eid > max_id:
                max_id = eid
            _walk(elem.get("children", []))

    for page in tree.get("pages", []):
        _walk(page.get("elements", []))

    # Also check onglets
    for onglet in tree.get("onglets", []):
        oid = onglet.get("id", 0)
        if oid > max_id:
            max_id = oid

    return max_id


def next_id(tree: dict) -> int:
    """Return the next available id."""
    return compute_max_id(tree) + 1


# ---------------------------------------------------------------------------
# Line manipulation helpers
# ---------------------------------------------------------------------------

def read_file(path: str) -> list[str]:
    """Read a .dhsf file, returning lines with original endings."""
    with open(path, encoding="iso-8859-1") as f:
        return f.readlines()


def write_file(path: str, lines: list[str]):
    """Write lines back to the file in ISO-8859-1 + CRLF."""
    content = ""
    for line in lines:
        # Normalize line ending
        stripped = line.rstrip("\r\n")
        content += stripped + "\r\n"
    Path(path).write_bytes(content.encode("iso-8859-1"))


def insert_lines(lines: list[str], position: int, new_lines: list[str]) -> list[str]:
    """Insert new_lines into lines at the given position (0-based)."""
    return lines[:position] + new_lines + lines[position:]


def update_dernier_id(lines: list[str], new_id: int) -> list[str]:
    """Update dernier_id= in the [masque] section."""
    pat = re.compile(r"^(\s*dernier_id\s*=\s*)\d+")
    for i, line in enumerate(lines):
        m = pat.match(line)
        if m:
            lines[i] = f"{m.group(1)}{new_id}\n"
            break
    return lines


def update_timestamp(lines: list[str]) -> list[str]:
    """Update the header timestamp and date_modification."""
    now = datetime.now()
    ts14 = now.strftime("%Y%m%d%H%M%S")
    date_fr = now.strftime("%d/%m/%Y")

    # Header line
    for i, line in enumerate(lines):
        if line.strip().startswith(";>xwin4obj"):
            lines[i] = re.sub(r"\d{14}", ts14, line)
            break

    # date_modification
    pat = re.compile(r'(date_modification=")[^"]*(")')
    for i, line in enumerate(lines):
        m = pat.search(line)
        if m:
            lines[i] = pat.sub(rf"\g<1>{date_fr}\2", line)
            break

    return lines


# ---------------------------------------------------------------------------
# Block generators
# ---------------------------------------------------------------------------

def gen_field_block(
    label: str,
    vue: str,
    champ: str,
    alias: str,
    id_texte: int,
    id_champ: int,
    y_pos: int,
    x_label: int = 5,
    x_champ: int = 51,
    label_width: int = 45,
    champ_width: int = 80,
    wstyle: str = "CHAMP_SAISI",
    saisie: bool = True,
) -> list[str]:
    """Generate the lines for an obj_texte + champ pair."""
    block = []
    height = 9  # standard field height

    # obj_texte (label)
    block.append(f"{INDENT_1}[obj_texte]\n")
    block.append(f"{INDENT_2}[presentation]\n")
    block.append(f"{INDENT_3}position={y_pos},{x_label}\n")
    block.append(f"{INDENT_3}taille={height},{label_width}\n")
    block.append(f"{INDENT_3}id={id_texte}\n")
    block.append(f"{INDENT_3}wstyle=\"STD\"\n")
    block.append(f"{INDENT_2}[texte]\n")
    block.append(f"{INDENT_3}texte=\"{label}\"\n")

    # champ
    block.append(f"{INDENT_1}[champ]\n")
    block.append(f"{INDENT_2}[presentation]\n")
    block.append(f"{INDENT_3}position={y_pos},{x_champ}\n")
    block.append(f"{INDENT_3}taille={height},{champ_width}\n")
    block.append(f"{INDENT_3}id={id_champ}\n")
    block.append(f"{INDENT_3}wstyle=\"{wstyle}\"\n")
    block.append(f"{INDENT_2}[description]\n")
    block.append(f"{INDENT_3}donnee={vue},{champ},{alias}\n")
    if not saisie:
        block.append(f"{INDENT_3}saisie=non\n")
    block.append(f"{INDENT_2}[touches]\n")
    block.append(f"{INDENT_3}f7=135\n")
    block.append(f"{INDENT_3}shift_f6=10000\n")
    block.append(f"{INDENT_2}[traitements]\n")
    block.append(f"{INDENT_3}microbol_click=8002\n")

    return block


def gen_column_block(
    titre: str,
    vue: str,
    champ: str,
    alias: str,
    col_id: int,
    y_pos: int = 12,
    x_pos: int = 168,
    largeur_col: int = 60,
    wstyle: str = "TABLEAU_AFF",
    saisie: bool = False,
) -> list[str]:
    """Generate the lines for a champ_tableau (table column)."""
    block = []

    block.append(f"{INDENT_2}[champ_tableau]\n")
    block.append(f"{INDENT_3}[presentation]\n")
    block.append(f"    position={y_pos},{x_pos}\n")
    block.append(f"    taille=8,18\n")
    block.append(f"    id={col_id}\n")
    block.append(f"    wstyle=\"{wstyle}\"\n")
    block.append(f"{INDENT_3}[description]\n")
    block.append(f"    donnee={vue},{champ},{alias}\n")
    if not saisie:
        block.append(f"    saisie=non\n")
    block.append(f"{INDENT_3}[traitements]\n")
    block.append(f"    microbol_click=8002\n")
    block.append(f"{INDENT_3}[info_bulle]\n")
    block.append(f"{INDENT_3}texte=\"{titre}\"\n")
    block.append(f"{INDENT_3}[param_colonne]\n")
    block.append(f"    titre=\"{titre}\"\n")
    block.append(f"    largeur_col={largeur_col}\n")
    block.append(f"    wstyle=\"ENTETE_COLONNE\"\n")

    return block


def gen_page_block(
    numero: int,
    libelle: str,
    onglet_nom: str,
    onglet_libelle: str,
    ident_unique: int,
    suiv: int | None = None,
    prec: int | None = None,
) -> list[str]:
    """Generate the lines for a new page with onglet_page."""
    block = []

    block.append(f"[page]\n")
    block.append(f"{INDENT_1}numero={numero}\n")
    if libelle:
        block.append(f"{INDENT_1}libelle=\"{libelle}\"\n")
    block.append(f"{INDENT_1}fond=\"STD\"\n")
    block.append(f"{INDENT_1}efface=partiel\n")
    block.append(f"{INDENT_1}nb_lig=25\n")
    block.append(f"{INDENT_1}nb_col=70\n")
    block.append(f"{INDENT_1}offset_lig=1\n")
    block.append(f"{INDENT_1}offset_col=1\n")
    if suiv is not None:
        block.append(f"{INDENT_1}suiv={suiv}\n")
    if prec is not None:
        block.append(f"{INDENT_1}prec={prec}\n")
    block.append(f"{INDENT_1}attache_x=oui\n")
    block.append(f"{INDENT_1}attache_lgy=oui\n")
    block.append(f"{INDENT_1}ident_unique={ident_unique}\n")

    # onglet_page
    block.append(f"{INDENT_1}[onglet_page]\n")
    block.append(f"{INDENT_2}[param_onglet_page]\n")
    block.append(f"{INDENT_3}nom=\"{onglet_nom}\"\n")
    block.append(f"{INDENT_3}libelle=\"{onglet_libelle}\"\n")
    block.append(f"{INDENT_3}couleur_fond=\"STD\"\n")

    return block


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def action_add_field(path: str, tree: dict, params: dict) -> dict:
    """Add an obj_texte + champ pair to a page.

    Required params:
      page_numero (int): target page number
      label (str): label text
      vue (str): view name for donnee=
      champ (str): field name for donnee=
      alias (str): alias for donnee=

    Optional params:
      y_pos (int): vertical position (auto-calculated if omitted)
      wstyle (str): field style (default: CHAMP_SAISI)
      saisie (bool): editable? (default: true)
    """
    page_num = params["page_numero"]
    label = params["label"]
    vue = params["vue"]
    champ = params["champ"]
    alias = params["alias"]
    wstyle = params.get("wstyle", "CHAMP_SAISI")
    saisie = params.get("saisie", True)

    # Find the target page
    page = None
    for p in tree["pages"]:
        if p["numero"] == page_num:
            page = p
            break

    if page is None:
        return {"success": False, "error": f"Page {page_num} introuvable"}

    # Verifier que la page a les attributs obligatoires (R-011)
    required_attrs = ["numero", "nb_lig", "nb_col", "offset_lig", "offset_col"]
    attrs = page.get("attrs", {}) or {}
    missing = [a for a in required_attrs if not attrs.get(a)]
    if missing:
        return {
            "success": False,
            "error": (
                f"Page [page] numero={page_num} incomplete : attributs "
                f"obligatoires manquants {missing}. Initialiser la page "
                f"(numero, nb_lig, nb_col, offset_lig, offset_col) avant "
                f"d'y ajouter des champs. Dans un masque zoom, utiliser la "
                f"page 11 (fiche zoom) pour les champs metier."
            ),
        }

    # Auto-calculate y_pos: find max Y of existing elements + 14
    y_pos = params.get("y_pos")
    if y_pos is None:
        max_y = 20
        for elem in page.get("elements", []):
            pos = elem.get("position", [0, 0])
            if isinstance(pos, list) and len(pos) >= 1:
                max_y = max(max_y, pos[0])
        y_pos = max_y + 14

    # Allocate IDs
    current_max = compute_max_id(tree)
    id_texte = current_max + 1
    id_champ = current_max + 2

    # Generate block
    block = gen_field_block(
        label=label, vue=vue, champ=champ, alias=alias,
        id_texte=id_texte, id_champ=id_champ,
        y_pos=y_pos, wstyle=wstyle, saisie=saisie,
    )

    # Determine insertion point: end of last element in page, or after page attrs
    lines = read_file(path)
    if page["elements"]:
        last_elem = page["elements"][-1]
        insert_at = last_elem["line_end"]  # 1-based, insert after
    else:
        insert_at = page["line_start"] + len([
            k for k in page["attrs"] if page["attrs"][k]
        ]) + 1

    # Insert (convert 1-based to 0-based)
    lines = insert_lines(lines, insert_at, block)

    # Update dernier_id
    lines = update_dernier_id(lines, id_champ)
    lines = update_timestamp(lines)

    write_file(path, lines)

    return {
        "success": True,
        "action": "add-field",
        "page": page_num,
        "label": label,
        "donnee": f"{vue},{champ},{alias}",
        "ids_allocated": [id_texte, id_champ],
        "y_pos": y_pos,
        "lines_inserted": len(block),
    }


def action_add_column(path: str, tree: dict, params: dict) -> dict:
    """Add a champ_tableau to the tableau on a given page.

    Required params:
      page_numero (int): page containing the tableau
      titre (str): column header
      vue (str): view name
      champ (str): field name
      alias (str): alias

    Optional params:
      largeur_col (int): column width (default: 60)
      wstyle (str): column style (default: TABLEAU_AFF)
      saisie (bool): editable? (default: false)
    """
    page_num = params["page_numero"]
    titre = params["titre"]
    vue = params["vue"]
    champ = params["champ"]
    alias = params["alias"]
    largeur = params.get("largeur_col", 60)
    wstyle = params.get("wstyle", "TABLEAU_AFF")
    saisie = params.get("saisie", False)

    # Find the tableau on the target page
    page = None
    for p in tree["pages"]:
        if p["numero"] == page_num:
            page = p
            break

    if page is None:
        return {"success": False, "error": f"Page {page_num} introuvable"}

    tableau = None
    for elem in page.get("elements", []):
        if elem["type"] == "tableau":
            tableau = elem
            break

    if tableau is None:
        return {"success": False, "error": f"Aucun [tableau] sur la page {page_num}"}

    # Allocate ID
    current_max = compute_max_id(tree)
    col_id = current_max + 1

    # Generate block
    block = gen_column_block(
        titre=titre, vue=vue, champ=champ, alias=alias,
        col_id=col_id, largeur_col=largeur, wstyle=wstyle, saisie=saisie,
    )

    # Insert after last child of tableau (or after tableau's own sub-sections)
    lines = read_file(path)
    if tableau["children"]:
        last_child = tableau["children"][-1]
        insert_at = last_child["line_end"]  # 1-based
    else:
        insert_at = tableau["line_end"]

    lines = insert_lines(lines, insert_at, block)

    # Update dernier_id
    lines = update_dernier_id(lines, col_id)
    lines = update_timestamp(lines)

    write_file(path, lines)

    return {
        "success": True,
        "action": "add-column",
        "page": page_num,
        "titre": titre,
        "donnee": f"{vue},{champ},{alias}",
        "id_allocated": col_id,
        "lines_inserted": len(block),
    }


def action_add_page(path: str, tree: dict, params: dict) -> dict:
    """Add a new page with onglet_page.

    Required params:
      numero (int): page number
      libelle (str): page description
      onglet_nom (str): tab name (e.g., "FICHE")
      onglet_libelle (str): tab label (e.g., "Details")

    Optional params:
      suiv (int): next page number
      prec (int): previous page number
    """
    numero = params["numero"]
    libelle = params["libelle"]
    onglet_nom = params["onglet_nom"]
    onglet_libelle = params["onglet_libelle"]
    suiv = params.get("suiv")
    prec = params.get("prec")

    # Check page doesn't already exist
    for p in tree["pages"]:
        if p["numero"] == numero:
            return {"success": False, "error": f"Page {numero} existe deja"}

    # Allocate ident_unique
    max_ident = max(
        (p.get("ident_unique", 0) for p in tree["pages"]),
        default=0
    )
    ident_unique = max_ident + 1

    # Update dernier_id_page
    masque = tree.get("masque", {})
    new_dernier_id_page = max(masque.get("dernier_id_page", 0), ident_unique)

    # Generate block
    block = gen_page_block(
        numero=numero, libelle=libelle,
        onglet_nom=onglet_nom, onglet_libelle=onglet_libelle,
        ident_unique=ident_unique, suiv=suiv, prec=prec,
    )

    # Find insertion point: after the last page, before [ressources]
    lines = read_file(path)

    # Find [ressources] or [diva] line
    insert_at = len(lines)
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped in ("[ressources]", "[diva]"):
            insert_at = i
            break

    lines = insert_lines(lines, insert_at, block)

    # Update dernier_id_page
    pat = re.compile(r"^(\s*dernier_id_page\s*=\s*)\d+")
    for i, line in enumerate(lines):
        m = pat.match(line)
        if m:
            lines[i] = f"{m.group(1)}{new_dernier_id_page}\n"
            break

    lines = update_timestamp(lines)

    write_file(path, lines)

    return {
        "success": True,
        "action": "add-page",
        "numero": numero,
        "ident_unique": ident_unique,
        "libelle": libelle,
        "onglet": f"{onglet_nom}/{onglet_libelle}",
        "lines_inserted": len(block),
    }


# ---------------------------------------------------------------------------
# Validation des formules groupbox / bornes de grille (R-007 2026-04-23)
# ---------------------------------------------------------------------------

# Valeurs canoniques reference/normes-graphiques.md section 5
GROUPBOX_MIN_ESPACEMENT = 10   # "tasse" (plus petit espacement standard)
GROUPBOX_OVERHEAD = 18         # +15 titre haut +3 marge bas
GROUPBOX_MIN_GAP = 8           # entre deux groupes
GROUPBOX_TITLE_RESERVE = 15    # premier champ a Y >= groupbox.Y + 15
GRID_COL_UNIT = 4              # X max = nb_col * 4
GRID_LIG_UNIT = 14             # base Y max = nb_lig * 14 (formule theorique)
# Marge Y empirique : xwin7 echoue avec "Objet en dehors de la clip grille"
# pour des max_Y bien sous nb_lig*14 sur les pages avec onglet (page nb_lig=25
# saturee a max_Y=231 alors que 350 theorique). Le header d'onglet + footer
# prennent ~30 unites non comptabilisees. La marge ne s'applique qu'aux pages
# "fiche" avec onglet (nb_lig >= seuil). Les petites pages (bandeau en-tete,
# nb_lig <= 5) n'ont pas de header d'onglet.
GRID_LIG_MARGE = 30            # marge header onglet + footer (empirique)
GRID_LIG_MARGE_THRESHOLD = 10  # appliquer la marge seulement si nb_lig > seuil

_GROUPBOX_CHILD_TYPES = {
    "champ", "obj_texte", "case_a_cocher",
    "bouton_radio", "groupe_radio",
}


def _max_xy(elem: dict) -> tuple[int, int]:
    """Retourne (max_X, max_Y) d'un element : position + taille."""
    pos = elem.get("position", [0, 0])
    taille = elem.get("taille", [0, 0])
    if not (isinstance(pos, list) and isinstance(taille, list)):
        return (0, 0)
    return (pos[1] + taille[1], pos[0] + taille[0])


def _flatten_elements(elements):
    for elem in elements:
        yield elem
        yield from _flatten_elements(elem.get("children", []))


def validate_groupbox_layout(tree: dict) -> dict:
    """Valide un masque parse contre les formules normes-graphiques.md section 5.

    Regles :
        R1 (error)   : taille_groupbox >= NbLignes * 10 + 18 (borne min, espacement 10)
        R2 (warning) : Y(premier enfant) - Y(groupbox) >= 15 (reserve titre)
        R3 (warning) : gap (entre groupbox N+1 et fin groupbox N) >= 8
        R4 (error)   : max_X(obj) <= nb_col * 4 (saturation largeur, cause 'clip grille')
        R5 (error)   : max_Y(obj) <= nb_lig * 14 (saturation hauteur)

    Convention positions : position=Y,X  et taille=H,L (cf dhsf_parser._parse_pair).

    Args:
        tree: arbre retourne par parse_dhsf().

    Returns:
        {"valid": bool, "violations": [{rule, severity, page, id, type, detail}, ...]}
    """
    from collections import defaultdict

    violations = []

    for page in tree.get("pages", []):
        page_no = page.get("numero", 0)
        attrs = page.get("attrs", {})
        try:
            nb_col = int(attrs.get("nb_col", "0"))
            nb_lig = int(attrs.get("nb_lig", "0"))
        except (TypeError, ValueError):
            nb_col = nb_lig = 0
        max_x_bound = nb_col * GRID_COL_UNIT if nb_col else None
        # Borne Y effective = nb_lig*14 - marge si page "fiche" avec onglet
        # (nb_lig > seuil), sinon borne theorique pour les bandeaux courts.
        if nb_lig:
            marge = GRID_LIG_MARGE if nb_lig > GRID_LIG_MARGE_THRESHOLD else 0
            max_y_bound = nb_lig * GRID_LIG_UNIT - marge
        else:
            max_y_bound = None

        # R4/R5 : bornes de grille sur tous les elements
        for elem in _flatten_elements(page.get("elements", [])):
            if not isinstance(elem.get("position"), list):
                continue
            max_x, max_y = _max_xy(elem)
            if max_x_bound is not None and max_x > max_x_bound:
                violations.append({
                    "rule": "R4",
                    "severity": "error",
                    "page": page_no,
                    "id": elem.get("id", 0),
                    "type": elem.get("type", "?"),
                    "detail": f"max_X {max_x} > nb_col*4 ({nb_col}*4={max_x_bound}) -- saturation largeur (cause 'Objet en dehors de la clip grille')",
                })
            if max_y_bound is not None and max_y > max_y_bound:
                violations.append({
                    "rule": "R5",
                    "severity": "error",
                    "page": page_no,
                    "id": elem.get("id", 0),
                    "type": elem.get("type", "?"),
                    "detail": f"max_Y {max_y} > borne effective {max_y_bound} (nb_lig*14 - marge {marge}) -- saturation hauteur (cause 'Objet en dehors de la clip grille')",
                })

        # R1/R2 : sur groupbox uniquement (children directs)
        groupboxes = [e for e in page.get("elements", []) if e.get("type") == "groupbox"]
        for gb in groupboxes:
            pos = gb.get("position", [0, 0])
            taille = gb.get("taille", [0, 0])
            if not (isinstance(pos, list) and isinstance(taille, list)):
                continue
            gb_y = pos[0]
            gb_h = taille[0]
            gb_id = gb.get("id", 0)
            children = gb.get("children", [])
            n_lines = sum(1 for c in children if c.get("type") in _GROUPBOX_CHILD_TYPES)

            if n_lines > 0:
                min_expected = n_lines * GROUPBOX_MIN_ESPACEMENT + GROUPBOX_OVERHEAD
                if gb_h < min_expected:
                    violations.append({
                        "rule": "R1",
                        "severity": "error",
                        "page": page_no,
                        "id": gb_id,
                        "type": "groupbox",
                        "detail": (
                            f"taille H={gb_h} < min attendu {min_expected} "
                            f"({n_lines} lignes * 10 espacement min + 18 overhead) -- "
                            f"formule : NbLignes * espacement (10/12/14) + 18"
                        ),
                    })

                child_ys = [
                    c.get("position", [0, 0])[0]
                    for c in children
                    if isinstance(c.get("position"), list) and c.get("type") in _GROUPBOX_CHILD_TYPES
                ]
                if child_ys:
                    first_y = min(child_ys)
                    margin = first_y - gb_y
                    if margin < GROUPBOX_TITLE_RESERVE:
                        violations.append({
                            "rule": "R2",
                            "severity": "warning",
                            "page": page_no,
                            "id": gb_id,
                            "type": "groupbox",
                            "detail": (
                                f"Y(premier enfant)={first_y} - Y(groupbox)={gb_y} = {margin} "
                                f"< {GROUPBOX_TITLE_RESERVE} (reserve titre) -- risque titre tronque"
                            ),
                        })

        # R3 : gap entre groupbox consecutives, regroupees par colonne X
        by_col = defaultdict(list)
        for gb in groupboxes:
            pos = gb.get("position", [0, 0])
            if not isinstance(pos, list):
                continue
            by_col[pos[1]].append(gb)

        for x_col, gbs in by_col.items():
            sorted_gbs = sorted(gbs, key=lambda g: g["position"][0])
            for i in range(len(sorted_gbs) - 1):
                cur = sorted_gbs[i]
                nxt = sorted_gbs[i + 1]
                cur_end = cur["position"][0] + cur["taille"][0]
                nxt_y = nxt["position"][0]
                gap = nxt_y - cur_end
                if gap < GROUPBOX_MIN_GAP:
                    violations.append({
                        "rule": "R3",
                        "severity": "warning",
                        "page": page_no,
                        "id": nxt.get("id", 0),
                        "type": "groupbox",
                        "detail": (
                            f"gap {gap} < {GROUPBOX_MIN_GAP} entre groupbox id={cur.get('id', 0)} "
                            f"(fin Y={cur_end}) et groupbox id={nxt.get('id', 0)} (debut Y={nxt_y}) "
                            f"-- colonne X={x_col}"
                        ),
                    })

    has_error = any(v["severity"] == "error" for v in violations)
    return {
        "valid": not has_error,
        "violations": violations,
        "stats": {
            "total": len(violations),
            "errors": sum(1 for v in violations if v["severity"] == "error"),
            "warnings": sum(1 for v in violations if v["severity"] == "warning"),
        },
    }


def action_validate(path: str, tree: dict, params: dict) -> dict:
    """Action 'validate' : valide le masque sans modification. Lecture seule."""
    report = validate_groupbox_layout(tree)
    return {
        "success": report["valid"],
        "action": "validate",
        **report,
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def gen_groupbox_block(
    texte: str,
    gb_id: int,
    y_pos: int,
    x_pos: int,
    height: int,
    width: int,
) -> list[str]:
    """Generate the lines for a [groupbox] declarative block (wrapper-only).

    The groupbox declares the visual frame around the listed fields. Children
    are NOT moved into the block in this MVP -- they remain as siblings inside
    the page, visually inside the groupbox.
    """
    block = []
    block.append(f"{INDENT_1}[groupbox]\n")
    block.append(f"{INDENT_2}[presentation]\n")
    block.append(f"{INDENT_3}position={y_pos},{x_pos}\n")
    block.append(f"{INDENT_3}taille={height},{width}\n")
    block.append(f"{INDENT_3}id={gb_id}\n")
    block.append(f"{INDENT_3}wstyle=\"GROUPBOX\"\n")
    block.append(f"{INDENT_2}[texte]\n")
    block.append(f"{INDENT_3}texte=\"{texte}\"\n")
    return block


def action_add_groupbox(path: str, tree: dict, params: dict) -> dict:
    """Add a visual groupbox enveloping a list of existing fields (MVP).

    Required params:
      page_numero (int): target page number
      texte (str): groupbox title
      champs (list[int]): ids of fields to envelop

    Optional params:
      margin_x (int): horizontal padding around bbox (default: 5)
      margin_top (int): top reserve for title (default: 16, norme graphique)
      margin_bottom (int): bottom padding (default: 6)

    Mode wrapper-only : le groupbox est insere avant le 1er champ cible.
    Les champs ne sont pas repositionnes (restent en freres dans la page).
    Un mode "repositionnement automatique" reste un chantier dedie.
    """
    page_num = params["page_numero"]
    texte = params["texte"]
    champs_ids = params.get("champs", [])
    if not champs_ids:
        return {"success": False, "error": "params.champs vide -- aucun id de champ a englober"}

    margin_x = params.get("margin_x", 5)
    margin_top = params.get("margin_top", 16)
    margin_bottom = params.get("margin_bottom", 6)

    # Find the target page
    page = None
    for p in tree["pages"]:
        if p["numero"] == page_num:
            page = p
            break
    if page is None:
        return {"success": False, "error": f"Page {page_num} introuvable"}

    # Localiser les champs cibles dans page["elements"]
    target_ids = set(champs_ids)
    matched = []
    for elem in page.get("elements", []):
        if elem.get("id") in target_ids:
            matched.append(elem)
    if not matched:
        return {"success": False, "error": f"Aucun des ids {champs_ids} trouve sur la page {page_num}"}
    missing = target_ids - {e.get("id") for e in matched}
    if missing:
        return {
            "success": False,
            "error": f"ids non trouves sur la page {page_num} : {sorted(missing)}",
        }

    # Calculer la bounding box des champs cibles
    min_y = min_x = None
    max_y = max_x = 0
    for elem in matched:
        pos = elem.get("position", [0, 0])
        tai = elem.get("taille", [0, 0])
        if not (isinstance(pos, list) and isinstance(tai, list)):
            continue
        y, x = pos[0], pos[1]
        h, w = tai[0], tai[1]
        if min_y is None or y < min_y:
            min_y = y
        if min_x is None or x < min_x:
            min_x = x
        if y + h > max_y:
            max_y = y + h
        if x + w > max_x:
            max_x = x + w
    if min_y is None or min_x is None:
        return {"success": False, "error": "Champs sans position parsable"}

    # Position et taille du groupbox (marges norme graphique)
    gb_y = max(0, min_y - margin_top)
    gb_x = max(0, min_x - margin_x)
    gb_height = (max_y - gb_y) + margin_bottom
    gb_width = (max_x - gb_x) + margin_x

    # Allouer l'id
    gb_id = compute_max_id(tree) + 1

    # Bloc groupbox
    block = gen_groupbox_block(
        texte=texte, gb_id=gb_id,
        y_pos=gb_y, x_pos=gb_x,
        height=gb_height, width=gb_width,
    )

    # Insertion : avant le 1er champ cible (par ordre line_start)
    first_target = min(matched, key=lambda e: e.get("line_start", 0))
    insert_at = first_target.get("line_start", 0)
    if insert_at <= 0:
        return {"success": False, "error": "Impossible de determiner la ligne d'insertion"}
    # Convertir 1-based parser -> 0-based python index
    insert_at -= 1

    lines = read_file(path)
    lines = insert_lines(lines, insert_at, block)
    lines = update_dernier_id(lines, gb_id)
    lines = update_timestamp(lines)
    write_file(path, lines)

    return {
        "success": True,
        "action": "add-groupbox",
        "page": page_num,
        "texte": texte,
        "champs_englobes": sorted(target_ids),
        "id_allocated": gb_id,
        "position": [gb_y, gb_x],
        "taille": [gb_height, gb_width],
        "lines_inserted": len(block),
        "mode": "wrapper-only (champs non repositionnes)",
    }


ACTIONS = {
    "add-field": action_add_field,
    "add-column": action_add_column,
    "add-page": action_add_page,
    "add-groupbox": action_add_groupbox,
    "validate": action_validate,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Modifications incrementales sur un fichier .dhsf."
    )
    parser.add_argument(
        "--path", required=True, help="Fichier .dhsf a modifier"
    )
    parser.add_argument(
        "--action", required=True, choices=list(ACTIONS.keys()),
        help="Action a effectuer"
    )
    parser.add_argument(
        "--params", required=True,
        help="JSON avec les parametres de l'action"
    )
    args = parser.parse_args()

    if not os.path.isfile(args.path):
        print(f"Error: file not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in --params: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse the file to get the tree
    tree = parse_dhsf(args.path)

    # Dispatch
    action_fn = ACTIONS[args.action]
    result = action_fn(args.path, tree, params)

    # Post-modification : valider le layout groupbox / bornes grille (R-007 2026-04-23).
    # Chirurgical : juste emettre l'info dans le JSON de retour, ne pas bloquer l'action.
    # L'appelant (orchestrateur creating-diva-entity ou humain) decide quoi faire.
    if args.action != "validate" and result.get("success"):
        try:
            retree = parse_dhsf(args.path)
            result["post_validation"] = validate_groupbox_layout(retree)
        except Exception as e:  # noqa: BLE001
            result["post_validation"] = {
                "valid": None,
                "error": f"post-validation skipped: {e}",
            }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
