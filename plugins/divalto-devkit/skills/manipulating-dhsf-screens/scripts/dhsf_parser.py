#!/usr/bin/env python3
"""Parse a .dhsf file (Divalto screen mask) into a structural tree.

Usage:
    py dhsf_parser.py --path <chemin.dhsf>
    py dhsf_parser.py --path <chemin.dhsf> --summary

Output: JSON to stdout.
  - Full mode (default): complete tree with pages, elements, line ranges
  - Summary mode (--summary): tree skeleton with metrics only

The tree preserves line ranges (line_start / line_end, 1-based) for every
node so that downstream tools can perform surgical text replacement
(round-tripping).
"""

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Widget element types that can appear inside a [page]
WIDGET_TYPES = {
    "obj_texte", "champ", "champ_tableau", "tableau", "groupbox",
    "multi_choix", "multi_choix_tableau", "groupe_radio", "radio_bouton",
    "bouton_graphique", "arbre", "panel_wpf", "grille_wpf", "onglet_page",
}

# Widget types counted in the total (compatible with dhsf_info.py).
# radio_bouton is excluded because it's a child of groupe_radio, not standalone.
COUNTED_WIDGET_TYPES = WIDGET_TYPES - {"radio_bouton"}

# Container elements whose children are also widget elements
CONTAINER_CHILDREN = {
    "tableau": {"champ_tableau", "multi_choix_tableau"},
    "groupe_radio": {"radio_bouton"},
}

# Top-level section names (indent 0)
TOP_SECTIONS = {
    "masque", "defaut", "enregistrements", "onglet", "page",
    "ressources", "diva", "diva_base",
}

# Section header pattern
SEC_PAT = re.compile(r"^\[(/?\w+)\]")

# Attribute pattern: key=value (value may be quoted)
ATTR_PAT = re.compile(r"^(\w+)\s*=\s*(.*)")


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _indent(line: str) -> int:
    """Return the number of leading spaces on *line* (tab counts as 1)."""
    count = 0
    for ch in line:
        if ch == " ":
            count += 1
        elif ch == "\t":
            count += 1
        else:
            break
    return count


def _unquote(val: str) -> str:
    """Strip surrounding double-quotes if present."""
    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
        return val[1:-1]
    return val


def _parse_int(val: str, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _parse_pair(val: str):
    """Parse 'A,B' -> [int, int] or return raw string."""
    parts = val.split(",")
    if len(parts) == 2:
        try:
            return [int(parts[0]), int(parts[1])]
        except ValueError:
            pass
    return val


def _parse_donnee(val: str) -> dict:
    """Parse 'vue,champ,alias[,subindex]' into a dict."""
    parts = val.split(",")
    result = {}
    if len(parts) >= 1:
        result["vue"] = parts[0].strip()
    if len(parts) >= 2:
        result["champ"] = parts[1].strip()
    if len(parts) >= 3:
        result["alias"] = parts[2].strip()
    if len(parts) >= 4:
        result["subindex"] = parts[3].strip()
    return result


# ---------------------------------------------------------------------------
# Line scanner
# ---------------------------------------------------------------------------

class LineScanner:
    """Stateful line-by-line scanner over the file content."""

    def __init__(self, lines: list[str]):
        self._lines = lines
        self._pos = 0
        self._total = len(lines)

    @property
    def pos(self) -> int:
        return self._pos

    @pos.setter
    def pos(self, value: int):
        self._pos = value

    @property
    def exhausted(self) -> bool:
        return self._pos >= self._total

    def peek(self) -> str | None:
        if self._pos < self._total:
            return self._lines[self._pos]
        return None

    def advance(self) -> str:
        line = self._lines[self._pos]
        self._pos += 1
        return line

    def lineno(self) -> int:
        """Current 1-based line number."""
        return self._pos + 1

    def section_at(self) -> str | None:
        """If current line is a [section], return its name, else None."""
        line = self.peek()
        if line is None:
            return None
        m = SEC_PAT.match(line.strip())
        return m.group(1).lower() if m else None


# ---------------------------------------------------------------------------
# Header parser
# ---------------------------------------------------------------------------

def parse_header(scanner: LineScanner) -> dict:
    """Parse the ;>xwin4obj header line."""
    result = {"raw": "", "version": "", "timestamp": ""}
    line = scanner.peek()
    if line and line.strip().startswith(";>xwin4obj"):
        result["raw"] = line.rstrip("\r\n")
        result["line"] = scanner.lineno()
        # Extract version and timestamp
        m = re.search(r"(\d+\.\d+)", line)
        if m:
            result["version"] = m.group(1)
        m = re.search(r"(\d{14})", line)
        if m:
            result["timestamp"] = m.group(1)
        scanner.advance()
    return result


# ---------------------------------------------------------------------------
# Key-value attribute collector
# ---------------------------------------------------------------------------

def collect_attrs(scanner: LineScanner, min_indent: int) -> dict:
    """Collect key=value attributes at indent >= min_indent.

    Stops when hitting a [section] or a line at indent < min_indent.
    Returns a dict of parsed attributes.
    """
    attrs = {}
    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()
        # Stop conditions
        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue
        ind = _indent(line)
        if ind < min_indent:
            break
        if SEC_PAT.match(stripped):
            break
        # Parse key=value
        m = ATTR_PAT.match(stripped)
        if m:
            key = m.group(1)
            val = _unquote(m.group(2).strip())
            attrs[key] = val
        scanner.advance()
    return attrs


# ---------------------------------------------------------------------------
# [masque] section
# ---------------------------------------------------------------------------

def parse_masque(scanner: LineScanner) -> dict:
    """Parse [masque] section attributes."""
    line_start = scanner.lineno()
    scanner.advance()  # skip [masque]
    attrs = collect_attrs(scanner, 1)
    # Normalize known fields
    result = {
        "line_start": line_start,
        "libelle": attrs.get("libelle", ""),
        "utilisateur": attrs.get("utilisateur", ""),
        "date_modification": attrs.get("date_modification", ""),
        "feuille_style": attrs.get("feuille_style", ""),
        "id_traitements": _parse_int(attrs.get("id_traitements", "0")),
        "type_masque": _parse_int(attrs.get("type_masque", "0")),
        "dernier_id": _parse_int(attrs.get("dernier_id", "0")),
        "dernier_id_page": _parse_int(attrs.get("dernier_id_page", "0")),
    }
    result["is_zoom"] = result["type_masque"] == 2
    return result


# ---------------------------------------------------------------------------
# [defaut] section
# ---------------------------------------------------------------------------

def parse_defaut(scanner: LineScanner) -> dict:
    """Parse [defaut] section with aide_page and touches sub-sections."""
    line_start = scanner.lineno()
    scanner.advance()  # skip [defaut]
    result = {"line_start": line_start, "aide_page": {}, "touches": {}}

    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue
        ind = _indent(line)
        if ind == 0 and SEC_PAT.match(stripped):
            break  # next top-level section
        sec = scanner.section_at()
        if sec == "aide_page":
            scanner.advance()
            result["aide_page"] = collect_attrs(scanner, 2)
        elif sec == "touches":
            scanner.advance()
            result["touches"] = collect_attrs(scanner, 2)
        else:
            scanner.advance()  # skip unknown lines
    return result


# ---------------------------------------------------------------------------
# [enregistrements] section
# ---------------------------------------------------------------------------

def parse_enregistrements(scanner: LineScanner) -> list:
    """Parse [enregistrements] lines into structured records."""
    scanner.advance()  # skip [enregistrements]
    records = []

    enr_pat = re.compile(
        r'^\s*"([^"]+)"\s*,\s*([^,]*)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,\s*(\d+)'
    )

    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue
        ind = _indent(line)
        if ind == 0 and SEC_PAT.match(stripped):
            break
        m = enr_pat.match(line)
        if m:
            records.append({
                "line": scanner.lineno(),
                "fichier": m.group(1),
                "reserved": m.group(2).strip(),
                "vue": m.group(3),
                "alias": m.group(4),
                "taille": int(m.group(5)),
                "type": int(m.group(6)),
            })
        scanner.advance()
    return records


# ---------------------------------------------------------------------------
# [onglet] section
# ---------------------------------------------------------------------------

def parse_onglet(scanner: LineScanner) -> dict:
    """Parse one [onglet] section."""
    line_start = scanner.lineno()
    scanner.advance()  # skip [onglet]
    result = {
        "line_start": line_start,
        "presentation": {},
        "param_onglet": {},
    }

    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue
        ind = _indent(line)
        if ind == 0 and SEC_PAT.match(stripped):
            break
        sec = scanner.section_at()
        if sec == "presentation":
            scanner.advance()
            result["presentation"] = collect_attrs(scanner, 2)
        elif sec == "param_onglet":
            scanner.advance()
            result["param_onglet"] = collect_attrs(scanner, 2)
        else:
            scanner.advance()

    # Normalize
    pres = result["presentation"]
    result["id"] = _parse_int(pres.get("id", "0"))
    result["position"] = _parse_pair(pres.get("position", "0,0"))
    result["taille"] = _parse_pair(pres.get("taille", "0,0"))
    po = result["param_onglet"]
    result["nom"] = po.get("nom", "")

    return result


# ---------------------------------------------------------------------------
# Element parser (widgets inside a page)
# ---------------------------------------------------------------------------

def parse_sub_section(scanner: LineScanner, min_indent: int) -> dict:
    """Parse a sub-section like [presentation], [description], etc.

    Returns its key-value attributes.
    """
    scanner.advance()  # skip [section_name]
    return collect_attrs(scanner, min_indent)


def parse_info_bulle(scanner: LineScanner, parent_indent: int) -> str:
    """Parse [info_bulle] which has a special format: texte= on same indent."""
    scanner.advance()  # skip [info_bulle]
    # The texte= line is at the SAME indent as [info_bulle], not deeper
    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue
        ind = _indent(line)
        if ind < parent_indent:
            break
        if SEC_PAT.match(stripped):
            break
        m = ATTR_PAT.match(stripped)
        if m and m.group(1) == "texte":
            val = _unquote(m.group(2).strip())
            scanner.advance()
            return val
        scanner.advance()
    return ""


def parse_boutons_list(scanner: LineScanner, min_indent: int) -> list:
    """Parse [boutons] section: each line is a quoted button name."""
    scanner.advance()  # skip [boutons]
    boutons = []
    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue
        ind = _indent(line)
        if ind < min_indent:
            break
        if SEC_PAT.match(stripped):
            break
        # Quoted button name
        if stripped.startswith('"') and stripped.endswith('"'):
            boutons.append(stripped[1:-1])
        scanner.advance()
    return boutons


def parse_element(scanner: LineScanner, element_type: str, elem_indent: int) -> dict:
    """Parse a single element (obj_texte, champ, tableau, etc.).

    *elem_indent* is the indent of the [element_type] line itself.
    Sub-sections are at elem_indent+1, their attrs at elem_indent+2.
    """
    line_start = scanner.lineno()
    scanner.advance()  # skip [element_type]

    elem = {
        "type": element_type,
        "line_start": line_start,
        "line_end": line_start,
        "id": 0,
        "position": [0, 0],
        "taille": [0, 0],
        "wstyle": "",
        "sub_sections": {},
        "children": [],
    }

    sub_indent = elem_indent + 1
    attr_indent = elem_indent + 2

    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue

        ind = _indent(line)

        # If we hit something at elem_indent or less, we're done
        if ind <= elem_indent:
            # But check: is this a child element for a container?
            sec = scanner.section_at()
            if sec and sec in CONTAINER_CHILDREN.get(element_type, set()):
                child = parse_element(scanner, sec, ind)
                elem["children"].append(child)
                elem["line_end"] = child["line_end"]
                continue
            break

        sec = scanner.section_at()
        if sec:
            if sec == "presentation":
                pres = parse_sub_section(scanner, attr_indent)
                elem["sub_sections"]["presentation"] = pres
                elem["id"] = _parse_int(pres.get("id", "0"))
                elem["position"] = _parse_pair(pres.get("position", "0,0"))
                elem["taille"] = _parse_pair(pres.get("taille", "0,0"))
                elem["wstyle"] = pres.get("wstyle", "")
                # Extra presentation attrs
                for k in ("attache_lgx", "attache_lgy", "attache_x",
                          "noms", "colonnes_saisie"):
                    if k in pres:
                        elem[k] = pres[k]
            elif sec == "info_bulle":
                elem["info_bulle"] = parse_info_bulle(scanner, ind)
            elif sec == "boutons":
                elem["boutons"] = parse_boutons_list(scanner, ind + 1)
            elif sec in WIDGET_TYPES:
                # Child element (e.g. champ_tableau inside tableau)
                child = parse_element(scanner, sec, ind)
                elem["children"].append(child)
                elem["line_end"] = child["line_end"]
            else:
                # Generic sub-section (description, param_saisie, etc.)
                attrs = parse_sub_section(scanner, attr_indent)
                elem["sub_sections"][sec] = attrs
                # Extract common useful fields
                if sec == "description" and "donnee" in attrs:
                    elem["donnee"] = _parse_donnee(attrs["donnee"])
                if sec == "texte" and "texte" in attrs:
                    elem["texte"] = attrs["texte"]
                if sec == "param_colonne":
                    elem["param_colonne"] = attrs
                if sec == "param_tableau":
                    elem["param_tableau"] = attrs
                if sec == "param_groupbox":
                    elem["param_groupbox"] = attrs
                if sec == "param_onglet_page":
                    elem["param_onglet_page"] = attrs
                if sec == "param_multi":
                    elem["param_multi"] = attrs
                if sec == "param_groupe":
                    elem["param_groupe"] = attrs
                if sec == "param_radio":
                    elem["param_radio"] = attrs
                if sec == "param_bouton":
                    elem["param_bouton"] = attrs
                if sec == "param_arbre":
                    elem["param_arbre"] = attrs
        else:
            scanner.advance()

        elem["line_end"] = scanner.lineno() - 1

    # Ensure line_end is at least line_start
    if elem["line_end"] < elem["line_start"]:
        elem["line_end"] = elem["line_start"]

    return elem


# ---------------------------------------------------------------------------
# [page] section
# ---------------------------------------------------------------------------

def parse_page(scanner: LineScanner) -> dict:
    """Parse one [page] section including all its child elements."""
    line_start = scanner.lineno()
    scanner.advance()  # skip [page]

    page = {
        "line_start": line_start,
        "line_end": line_start,
        "numero": 0,
        "attrs": {},
        "elements": [],
    }

    # Collect page-level attributes (at indent 1)
    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue

        ind = _indent(line)

        # End of page: another top-level section at indent 0
        if ind == 0 and SEC_PAT.match(stripped):
            break

        sec = scanner.section_at()

        # If it's a widget element type, parse it
        if sec and sec in WIDGET_TYPES:
            elem = parse_element(scanner, sec, ind)
            page["elements"].append(elem)
            page["line_end"] = elem["line_end"]
            continue

        # Attribute line
        if not sec:
            m = ATTR_PAT.match(stripped)
            if m:
                key = m.group(1)
                val = _unquote(m.group(2).strip())
                page["attrs"][key] = val
            scanner.advance()
            continue

        # Unknown sub-section within page (skip it)
        scanner.advance()

    # Extract key attributes
    page["numero"] = _parse_int(page["attrs"].get("numero", "0"))
    page["libelle"] = page["attrs"].get("libelle", "")
    page["fond"] = page["attrs"].get("fond", "")
    page["nature"] = page["attrs"].get("nature", "")
    page["type"] = page["attrs"].get("type", "")
    page["titre"] = page["attrs"].get("titre", "")
    page["efface"] = page["attrs"].get("efface", "")
    page["ident_unique"] = _parse_int(page["attrs"].get("ident_unique", "0"))
    page["suiv"] = _parse_int(page["attrs"].get("suiv", "0")) or None
    page["prec"] = _parse_int(page["attrs"].get("prec", "0")) or None

    if page["line_end"] < page["line_start"]:
        page["line_end"] = max(page["line_start"], scanner.lineno() - 1)

    return page


# ---------------------------------------------------------------------------
# [ressources] section
# ---------------------------------------------------------------------------

def parse_ressources(scanner: LineScanner) -> dict:
    """Parse [ressources] section with toolbars and menus."""
    line_start = scanner.lineno()
    scanner.advance()  # skip [ressources]
    result = {"line_start": line_start, "toolbars": [], "menus": []}

    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue

        ind = _indent(line)
        if ind == 0 and SEC_PAT.match(stripped):
            break

        sec = scanner.section_at()
        if sec == "toolbar":
            tb = _parse_toolbar_or_menu(scanner, "toolbar")
            result["toolbars"].append(tb)
        elif sec == "menu":
            menu = _parse_toolbar_or_menu(scanner, "menu")
            result["menus"].append(menu)
        else:
            scanner.advance()

    return result


def _parse_toolbar_or_menu(scanner: LineScanner, kind: str) -> dict:
    """Parse a [toolbar] or [menu] block with its [item] children."""
    line_start = scanner.lineno()
    tb_indent = _indent(scanner.peek())
    scanner.advance()  # skip [toolbar] or [menu]

    obj = {"type": kind, "line_start": line_start, "ident": "", "items": []}

    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue

        ind = _indent(line)
        if ind <= tb_indent:
            sec = scanner.section_at()
            if sec and sec != "item":
                break

        sec = scanner.section_at()

        if not sec:
            # Attribute of toolbar/menu
            m = ATTR_PAT.match(stripped)
            if m:
                key = m.group(1)
                val = _unquote(m.group(2).strip())
                if key == "ident":
                    obj["ident"] = val
                else:
                    obj[key] = val
            scanner.advance()
        elif sec == "item":
            item = _parse_resource_item(scanner, ind)
            obj["items"].append(item)
        else:
            # Nested sub-section or next toolbar/menu
            if ind <= tb_indent:
                break
            scanner.advance()

    return obj


def _parse_resource_item(scanner: LineScanner, item_indent: int) -> dict:
    """Parse one [item] inside a toolbar/menu."""
    line_start = scanner.lineno()
    scanner.advance()  # skip [item]

    item = {"line_start": line_start}

    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue

        ind = _indent(line)
        if ind <= item_indent:
            break

        sec = scanner.section_at()
        if sec == "param_bouton":
            scanner.advance()
            item["param_bouton"] = collect_attrs(scanner, ind + 2)
        elif sec == "info_bulle":
            item["info_bulle"] = parse_info_bulle(scanner, ind)
        elif sec:
            # Other sub-sections (skip)
            scanner.advance()
        else:
            # Attribute of [item] itself (type=, dessin=)
            m = ATTR_PAT.match(stripped)
            if m:
                item[m.group(1)] = _unquote(m.group(2).strip())
            scanner.advance()

    return item


# ---------------------------------------------------------------------------
# [diva] / [diva_base] blocks
# ---------------------------------------------------------------------------

def parse_diva_block(scanner: LineScanner) -> dict:
    """Parse [diva] ... [/diva] or [diva_base] ... [/diva] block."""
    block_name = scanner.section_at()
    line_start = scanner.lineno()
    scanner.advance()  # skip opening tag

    code_lines = []
    records = []
    recordsql = []
    procedures = []
    functions = []
    includes = []
    modules = []

    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()

        # Check for closing tag
        if stripped.lower() in ("[/diva]", "[/diva_base]"):
            scanner.advance()
            break

        code_lines.append(line.rstrip("\r\n"))

        # Extract declarations
        if re.match(r"^Public\s+Record\s+", stripped):
            records.append(stripped)
        elif re.match(r"^Public\s+RecordSql\s+", stripped):
            recordsql.append(stripped)
        elif re.match(r"^Public\s+Procedure\b", stripped):
            m = re.match(r"^Public\s+Procedure\s+(\w+)", stripped)
            if m:
                procedures.append(m.group(1))
        elif re.match(r"^Public\s+Function\b", stripped):
            m = re.match(r"^Public\s+Function\s+(\w+)", stripped)
            if m:
                functions.append(m.group(1))
        elif re.match(r"^Include\s+", stripped):
            m = re.match(r'^Include\s+"([^"]+)"', stripped)
            if m:
                includes.append(m.group(1))
        elif re.match(r"^Module\s+", stripped):
            m = re.match(r"^Module\s+(\S+)", stripped)
            if m:
                modules.append(m.group(1))

        scanner.advance()

    return {
        "block": block_name,
        "line_start": line_start,
        "line_end": scanner.lineno() - 1,
        "code_lines": len(code_lines),
        "records": records,
        "recordsql": recordsql,
        "procedures": procedures,
        "functions": functions,
        "includes": includes,
        "modules": modules,
    }


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_dhsf(path: str) -> dict:
    """Parse a .dhsf file and return the full structural tree."""
    file_size = os.path.getsize(path)

    with open(path, encoding="iso-8859-1") as f:
        raw_lines = f.readlines()

    scanner = LineScanner(raw_lines)

    tree = {
        "path": os.path.abspath(path),
        "file_size": file_size,
        "total_lines": len(raw_lines),
        "header": {},
        "masque": {},
        "defaut": {},
        "enregistrements": [],
        "onglets": [],
        "pages": [],
        "ressources": {"toolbars": [], "menus": []},
        "diva": {},
        "diva_base": {},
    }

    # Parse header line (;>xwin4obj)
    tree["header"] = parse_header(scanner)

    # Skip comment/blank lines between header and first section
    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()
        if stripped and not stripped.startswith(";"):
            break
        scanner.advance()

    # Parse top-level sections
    while not scanner.exhausted:
        line = scanner.peek()
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            scanner.advance()
            continue

        sec = scanner.section_at()

        if sec == "masque":
            tree["masque"] = parse_masque(scanner)
        elif sec == "defaut":
            tree["defaut"] = parse_defaut(scanner)
        elif sec == "enregistrements":
            tree["enregistrements"] = parse_enregistrements(scanner)
        elif sec == "onglet":
            tree["onglets"].append(parse_onglet(scanner))
        elif sec == "page":
            tree["pages"].append(parse_page(scanner))
        elif sec == "ressources":
            tree["ressources"] = parse_ressources(scanner)
        elif sec in ("diva", "diva_base"):
            block = parse_diva_block(scanner)
            tree[sec] = block
        else:
            # Unknown top-level line, skip
            scanner.advance()

    return tree


# ---------------------------------------------------------------------------
# Metrics (compatible with dhsf_info.py output)
# ---------------------------------------------------------------------------

def compute_metrics(tree: dict) -> dict:
    """Compute aggregate metrics from the parsed tree."""
    masque = tree.get("masque", {})

    # Count widgets per type (all types for detail, counted types for total)
    widgets = {wt: 0 for wt in sorted(WIDGET_TYPES)}

    def _count_widgets(elements):
        for elem in elements:
            etype = elem.get("type", "")
            if etype in widgets:
                widgets[etype] += 1
            _count_widgets(elem.get("children", []))

    for page in tree.get("pages", []):
        _count_widgets(page.get("elements", []))

    # widgets_total excludes radio_bouton (compatible with dhsf_info.py)
    widgets_total = sum(v for k, v in widgets.items() if k in COUNTED_WIDGET_TYPES)

    # Empty pages (no elements)
    empty_pages = sorted(
        p["numero"] for p in tree.get("pages", [])
        if not p.get("elements")
    )

    # Max id across all elements
    max_id = 0

    def _max_id(elements):
        nonlocal max_id
        for elem in elements:
            eid = elem.get("id", 0)
            if eid > max_id:
                max_id = eid
            _max_id(elem.get("children", []))

    for page in tree.get("pages", []):
        _max_id(page.get("elements", []))

    # Diva block metrics
    diva = tree.get("diva", {})

    return {
        "is_zoom": masque.get("is_zoom", False),
        "dernier_id": masque.get("dernier_id", 0),
        "dernier_id_page": masque.get("dernier_id_page", 0),
        "max_id_found": max_id,
        "pages_count": len(tree.get("pages", [])),
        "onglets_count": len(tree.get("onglets", [])),
        "enregistrements_count": len(tree.get("enregistrements", [])),
        "widgets": widgets,
        "widgets_total": widgets_total,
        "empty_pages": empty_pages,
        "diva_lines": diva.get("code_lines", 0),
        "procedures_count": len(diva.get("procedures", [])),
        "functions_count": len(diva.get("functions", [])),
        "includes_count": len(diva.get("includes", [])),
        "modules_count": len(diva.get("modules", [])),
        "toolbars_count": len(tree.get("ressources", {}).get("toolbars", [])),
        "menus_count": len(tree.get("ressources", {}).get("menus", [])),
    }


# ---------------------------------------------------------------------------
# Summary mode
# ---------------------------------------------------------------------------

def make_summary(tree: dict) -> dict:
    """Produce a compact summary (no raw attributes, no children details)."""
    metrics = compute_metrics(tree)

    pages_summary = []
    for page in tree.get("pages", []):
        elem_types = {}
        def _count(elems):
            for e in elems:
                t = e.get("type", "?")
                elem_types[t] = elem_types.get(t, 0) + 1
                _count(e.get("children", []))
        _count(page.get("elements", []))

        pages_summary.append({
            "numero": page["numero"],
            "libelle": page.get("libelle", ""),
            "type": page.get("type", ""),
            "elements_count": len(page.get("elements", [])),
            "element_types": elem_types,
            "suiv": page.get("suiv"),
            "prec": page.get("prec"),
        })

    return {
        "path": tree["path"],
        "file_size": tree["file_size"],
        "total_lines": tree["total_lines"],
        "masque": tree.get("masque", {}),
        "enregistrements_count": metrics["enregistrements_count"],
        "onglets": [
            {"nom": o.get("nom", ""), "id": o.get("id", 0)}
            for o in tree.get("onglets", [])
        ],
        "pages": pages_summary,
        "toolbars": [
            tb.get("ident", "") for tb in
            tree.get("ressources", {}).get("toolbars", [])
        ],
        "menus": [
            m.get("ident", "") for m in
            tree.get("ressources", {}).get("menus", [])
        ],
        "diva": {
            "code_lines": tree.get("diva", {}).get("code_lines", 0),
            "procedures": tree.get("diva", {}).get("procedures", []),
            "functions": tree.get("diva", {}).get("functions", []),
            "includes": tree.get("diva", {}).get("includes", []),
            "modules": tree.get("diva", {}).get("modules", []),
        },
        "metrics": metrics,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse a .dhsf file into a structural tree (JSON)."
    )
    parser.add_argument(
        "--path", required=True, help="Path to the .dhsf file."
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Output compact summary instead of full tree."
    )
    args = parser.parse_args()

    if not os.path.isfile(args.path):
        print(f"Error: file not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    tree = parse_dhsf(args.path)

    if args.summary:
        output = make_summary(tree)
    else:
        output = tree
        output["metrics"] = compute_metrics(tree)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
