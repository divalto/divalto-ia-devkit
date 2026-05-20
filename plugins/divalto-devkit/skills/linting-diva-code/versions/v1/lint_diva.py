#!/usr/bin/env python3
"""Linter principal pour fichiers DIVA (.dhsp, .dhsq, .dhsd, .dhsf, .dhpt, .dhps).

Interface CLI :
    py scripts/lint_diva.py --path "fichier.dhsp" [--rules S01,S02] [--severity error|warning|all] [--format json|text]

Sortie JSON sur stdout, messages sur stderr.
Exit 0 = aucun probleme, exit 1 = problemes trouves, exit 2 = erreur interne.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# Catalogue de regles
# ---------------------------------------------------------------------------

RULES = {
    # .dhsp — regles structurelles
    "S01": {"severity": "error",   "types": [".dhsp"], "desc": "Concatenation avec + au lieu de &"},
    "S02": {"severity": "warning", "types": [".dhsp"], "desc": "VRAI/FAUX au lieu de True/False"},
    "S03": {"severity": "error",   "types": [".dhsp"], "desc": "Declaration de variable apres BeginP/BeginF"},
    "S04": {"severity": "error",   "types": [".dhsp"], "desc": "Function sans FReturn"},
    "S05": {"severity": "warning", "types": [".dhsp"], "desc": "EndP/EndF sans commentaire de fermeture"},
    "S06": {"severity": "error",   "types": [".dhsf"], "desc": "Code DIVA dans un .dhsf hors [diva]...[/diva]"},
    # .dhsp — regles langage interdit
    "L01": {"severity": "error",   "types": [".dhsp"], "desc": "ForEach keyword interdit"},
    "L02": {"severity": "error",   "types": [".dhsp"], "desc": "Try/Catch/Finally interdit"},
    "L03": {"severity": "error",   "types": [".dhsp"], "desc": "Class keyword interdit"},
    "L04": {"severity": "error",   "types": [".dhsp"], "desc": "Thread keywords interdits"},
    # .dhsp — regles Zoom
    "Z02": {"severity": "warning", "types": [".dhsp"], "desc": "Zoom.OK sans preturn dans les 3 lignes suivantes"},
    "Z03": {"severity": "warning", "types": [".dhsp"], "desc": "Prefixes domaine mixtes (GT_/RT_/GG_)"},
    "Z08": {"severity": "warning", "types": [".dhsp"], "desc": "Prefixe GT_/RT_/GG_ sans Module correspondant"},
    "Z11": {"severity": "warning", "types": [".dhsp"], "desc": "Seek_* sans Initialize_*_PostFetch dans les 5 lignes suivantes"},
    "Z12": {"severity": "warning", "types": [".dhsp"], "desc": "Procedure/Function GT_/RT_/GG_ sans SetPrefixeModule"},
    # .dhsp — regles Module
    "M01": {"severity": "warning", "types": [".dhsp"], "desc": "Init_Module sans Get_CheckObject_Data"},
    "M02": {"severity": "warning", "types": [".dhsp"], "desc": "Init_Module sans initialisation record (= INIT)"},
    "M03": {"severity": "warning", "types": [".dhsp"], "desc": "A5_Stack_OutputMode sans A5_UnStack_OutputMode apparie"},
    "M04": {"severity": "warning", "types": [".dhsp"], "desc": "PreUpdate_recordSql sans majuser"},
    "M05": {"severity": "warning", "types": [".dhsp"], "desc": "Check_*_Field_* sans test <> vide"},
    # .dhsp — regles Framework
    "F02": {"severity": "warning", "types": [".dhsp"], "desc": "Prefixe domaine incorrect dans appels framework"},
    "F03": {"severity": "warning", "types": [".dhsp"], "desc": "WebRequestOpen sans WebRequestClose"},
    "F04": {"severity": "warning", "types": [".dhsp"], "desc": "JsonOpen sans JsonClose"},
    # .dhsq
    "S07": {"severity": "error",   "types": [".dhsq"], "desc": "Code DIVA detecte dans un .dhsq"},
    "R01": {"severity": "warning", "types": [".dhsq"], "desc": "Pas de Dos = MZ.Dos"},
    "R02": {"severity": "warning", "types": [".dhsq"], "desc": "Pas de OverWrittenBy"},
    "R03": {"severity": "warning", "types": [".dhsq"], "desc": "Fichier vide ou tres court"},
    "R04": {"severity": "warning", "types": [".dhsq"], "desc": "Nom de fichier non conforme"},
    "R05": {"severity": "warning", "types": [".dhsq"], "desc": "Placeholder — HFileVersion"},
    # .dhsd
    "D01": {"severity": "error",   "types": [".dhsd"], "desc": "Chevauchement de champs dans [TABLE]"},
    "D02": {"severity": "error",   "types": [".dhsd"], "desc": "Trou entre champs"},
    "D03": {"severity": "warning", "types": [".dhsd"], "desc": "Champ U<Table> manquant"},
    "D04": {"severity": "warning", "types": [".dhsd"], "desc": "Placeholder"},
    "D05": {"severity": "error",   "types": [".dhsd"], "desc": "Encodage UTF-8 detecte"},
    "D06": {"severity": "error",   "types": [".dhsd"], "desc": "Fins de ligne LF detectees"},
    "D07": {"severity": "error",   "types": [".dhsd"], "desc": "[/CHAMPS] manquant"},
    "D08": {"severity": "error",   "types": [".dhsd"], "desc": "[/TABLES] manquant"},
    "D09": {"severity": "error",   "types": [".dhsd"], "desc": "[/INDEX] manquant"},
    "D10": {"severity": "warning", "types": [".dhsd"], "desc": "Placeholder"},
    "D11": {"severity": "warning", "types": [".dhsd"], "desc": "Placeholder"},
    # .dhsf
    "E01": {"severity": "warning", "types": [".dhsf"], "desc": "Element graphique sans [presentation]"},
    "E08": {"severity": "warning", "types": [".dhsf"], "desc": "[diva_base] manquant"},
    "E09": {"severity": "warning", "types": [".dhsf"], "desc": "IDs dupliques"},
    "E10": {"severity": "error",   "types": [".dhsf"], "desc": "Encodage UTF-8 detecte"},
    # .dhpt
    "P01": {"severity": "error",   "types": [".dhpt", ".dhps"], "desc": "Encodage UTF-8 detecte"},
    "P02": {"severity": "error",   "types": [".dhpt", ".dhps"], "desc": "Fins de ligne LF detectees"},
    "P04": {"severity": "error",   "types": [".dhpt", ".dhps"], "desc": "Premiere ligne incorrecte"},
    "P05": {"severity": "error",   "types": [".dhpt"], "desc": "Premiere ligne contient xwin-sprojet au lieu de xwin-projet"},
    "P06": {"severity": "error",   "types": [".dhps"], "desc": "Syntaxe fic avec espace dans [includes]"},
    "P07": {"severity": "error",   "types": [".dhps"], "desc": "Syntaxe fic sans espace dans [fichiers]"},
    "P09": {"severity": "warning", "types": [".dhps"], "desc": "zdiva.dhsp absent de [includes]"},
    "P12": {"severity": "warning", "types": [".dhps"], "desc": "Section [autres] manquante"},
    "P13": {"severity": "warning", "types": [".dhpt"], "desc": "Sections obligatoires manquantes"},
    "P14": {"severity": "warning", "types": [".dhpt"], "desc": "Mot developpement sans accent dans profil"},
    "P15": {"severity": "warning", "types": [".dhpt"], "desc": "Mot developpement_x13.txt sans accent"},
}

# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def detect_utf8_bom(raw_bytes):
    """Detecte un BOM UTF-8."""
    return raw_bytes[:3] == b'\xef\xbb\xbf'


def detect_utf8_sequences(raw_bytes):
    """Detecte des sequences multi-octets UTF-8 (accents encodes en UTF-8)."""
    # Cherche des sequences 2-octets UTF-8 typiques (accents francais)
    # 0xC0-0xDF suivi de 0x80-0xBF
    i = 0
    count = 0
    while i < len(raw_bytes) - 1:
        b = raw_bytes[i]
        if 0xC0 <= b <= 0xDF and 0x80 <= raw_bytes[i + 1] <= 0xBF:
            count += 1
            i += 2
        elif 0xE0 <= b <= 0xEF and i + 2 < len(raw_bytes) and 0x80 <= raw_bytes[i + 1] <= 0xBF and 0x80 <= raw_bytes[i + 2] <= 0xBF:
            count += 1
            i += 3
        else:
            i += 1
    return count > 0


def is_utf8_encoded(raw_bytes):
    """Retourne True si le fichier semble encode en UTF-8 (BOM ou sequences)."""
    if detect_utf8_bom(raw_bytes):
        return True
    return detect_utf8_sequences(raw_bytes)


def has_lf_line_endings(raw_bytes):
    """Retourne True si le fichier contient des fins de ligne LF sans CR."""
    # Cherche \n qui n'est pas precede de \r
    for i, b in enumerate(raw_bytes):
        if b == 0x0A:  # LF
            if i == 0 or raw_bytes[i - 1] != 0x0D:  # pas precede de CR
                return True
    return False


def strip_comment(line):
    """Retire les commentaires DIVA (// en debut ou ; en milieu de ligne).
    Retourne la partie code de la ligne."""
    stripped = line.lstrip()
    if stripped.startswith("//"):
        return ""
    # Cherche le premier ; qui n'est pas dans une chaine
    in_str = False
    quote_char = None
    for i, ch in enumerate(stripped):
        if not in_str and ch in ("'", '"'):
            in_str = True
            quote_char = ch
        elif in_str and ch == quote_char:
            in_str = False
        elif not in_str and ch == ';':
            return stripped[:i]
    return stripped


def is_comment_line(line):
    """Retourne True si la ligne est un commentaire."""
    return line.lstrip().startswith("//")


# ---------------------------------------------------------------------------
# Regles .dhsp
# ---------------------------------------------------------------------------

def check_S01(lines, findings):
    """Concatenation avec + au lieu de &."""
    # Patterns : "string" + ou + "string"
    pat1 = re.compile(r'"[^"]*"\s*\+')
    pat2 = re.compile(r'\+\s*"[^"]*"')
    pat3 = re.compile(r"'[^']*'\s*\+")
    pat4 = re.compile(r"\+\s*'[^']*'")
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        if not code:
            continue
        if pat1.search(code) or pat2.search(code) or pat3.search(code) or pat4.search(code):
            findings.append({
                "rule": "S01", "severity": "error", "line": i,
                "message": "Concatenation avec + au lieu de &",
                "context": line.rstrip()
            })


def check_S02(lines, findings):
    """VRAI/FAUX au lieu de True/False."""
    pat = re.compile(r'\b(VRAI|FAUX)\b')
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        m = pat.search(code)
        if m:
            findings.append({
                "rule": "S02", "severity": "warning", "line": i,
                "message": f"{m.group(1)} au lieu de {'True' if m.group(1) == 'VRAI' else 'False'}",
                "context": line.rstrip()
            })


def check_S03(lines, findings):
    """Declaration de variable apres BeginP/BeginF."""
    # Pattern de declaration : espaces + nombre + nom + (type potentiel)
    decl_pat = re.compile(r'^\s+\d+\s+\w+\s+')
    in_body = False
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        stripped = line.strip()
        if re.match(r'\bBegin[PF]\b', stripped):
            in_body = True
            continue
        if re.match(r'\bEnd[PF]\b', stripped):
            in_body = False
            continue
        if in_body and decl_pat.match(line):
            findings.append({
                "rule": "S03", "severity": "error", "line": i,
                "message": "Declaration de variable apres BeginP/BeginF",
                "context": line.rstrip()
            })


def check_S04(lines, findings):
    """Function sans FReturn."""
    # Parser les blocs Function...EndF
    func_start = None
    func_name = None
    has_freturn = False
    func_pat = re.compile(r'^\s*Function\s+(\w+)', re.IGNORECASE)
    endf_pat = re.compile(r'^\s*EndF\b', re.IGNORECASE)
    freturn_pat = re.compile(r'\bFReturn\b', re.IGNORECASE)

    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        m = func_pat.match(line)
        if m:
            # Si on etait deja dans une fonction (pas de EndF), signaler
            if func_start is not None and not has_freturn:
                findings.append({
                    "rule": "S04", "severity": "error", "line": func_start,
                    "message": f"Function {func_name} sans FReturn",
                    "context": ""
                })
            func_start = i
            func_name = m.group(1)
            has_freturn = False
            continue
        if func_start is not None and freturn_pat.search(strip_comment(line)):
            has_freturn = True
        if func_start is not None and endf_pat.match(line):
            if not has_freturn:
                findings.append({
                    "rule": "S04", "severity": "error", "line": func_start,
                    "message": f"Function {func_name} sans FReturn",
                    "context": ""
                })
            func_start = None
            func_name = None
            has_freturn = False


def check_S05(lines, findings):
    """EndP/EndF sans commentaire de fermeture."""
    pat = re.compile(r'^\s*(EndP|EndF)\s*$')
    for i, line in enumerate(lines, 1):
        if pat.match(line):
            findings.append({
                "rule": "S05", "severity": "warning", "line": i,
                "message": f"{line.strip()} sans commentaire de fermeture",
                "context": line.rstrip()
            })


def check_L01(lines, findings):
    """ForEach keyword."""
    pat = re.compile(r'\bForEach\b', re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        if pat.search(strip_comment(line)):
            findings.append({
                "rule": "L01", "severity": "error", "line": i,
                "message": "ForEach keyword interdit en DIVA",
                "context": line.rstrip()
            })


def check_L02(lines, findings):
    """Try/Catch/Finally."""
    pat = re.compile(r'\b(Try|Catch|Finally)\b')
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        m = pat.search(code)
        if m:
            findings.append({
                "rule": "L02", "severity": "error", "line": i,
                "message": f"{m.group(1)} keyword interdit en DIVA",
                "context": line.rstrip()
            })


def check_L03(lines, findings):
    """Class keyword."""
    pat = re.compile(r'\bClass\s+\w+')
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        if pat.search(strip_comment(line)):
            findings.append({
                "rule": "L03", "severity": "error", "line": i,
                "message": "Class keyword interdit en DIVA",
                "context": line.rstrip()
            })


def check_L04(lines, findings):
    """Thread keywords."""
    pat = re.compile(r'\b(Thread|CreateThread|StartThread)\b')
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        m = pat.search(code)
        if m:
            findings.append({
                "rule": "L04", "severity": "error", "line": i,
                "message": f"{m.group(1)} keyword interdit en DIVA",
                "context": line.rstrip()
            })


def check_Z02(lines, findings):
    """Zoom.OK = 'I'/'S'/'C' sans preturn dans les 3 lignes suivantes."""
    pat = re.compile(r"""Zoom\.OK\s*=\s*['"][ISC]['"]""")
    for i, line in enumerate(lines):
        if is_comment_line(line):
            continue
        if pat.search(strip_comment(line)):
            # Verifier les 3 lignes suivantes
            found_preturn = False
            for j in range(i + 1, min(i + 4, len(lines))):
                if re.search(r'\bpreturn\b', lines[j], re.IGNORECASE):
                    found_preturn = True
                    break
            if not found_preturn:
                findings.append({
                    "rule": "Z02", "severity": "warning", "line": i + 1,
                    "message": "Zoom.OK assigne sans preturn dans les 3 lignes suivantes",
                    "context": line.rstrip()
                })


def check_Z03(lines, findings):
    """Prefixes domaine mixtes GT_/RT_/GG_."""
    prefixes_found = set()
    for line in lines:
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        if re.search(r'\bGT_', code):
            prefixes_found.add("GT_")
        if re.search(r'\bRT_', code):
            prefixes_found.add("RT_")
        if re.search(r'\bGG_', code):
            prefixes_found.add("GG_")
    if len(prefixes_found) > 1:
        findings.append({
            "rule": "Z03", "severity": "warning", "line": 0,
            "message": f"Prefixes domaine mixtes detectes : {', '.join(sorted(prefixes_found))}",
            "context": ""
        })


def check_Z08(lines, findings):
    """GT_/RT_/GG_ utilise sans Module correspondant."""
    data = "\n".join(lines)
    # Chercher les prefixes utilises (hors commentaires)
    used_prefixes = set()
    for line in lines:
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        if re.search(r'\bGT_\w+', code):
            used_prefixes.add("gt")
        if re.search(r'\bRT_\w+', code):
            used_prefixes.add("rt")
        if re.search(r'\bGG_\w+', code):
            used_prefixes.add("gg")
    # Chercher les Module declares
    for prefix in used_prefixes:
        module_pat = re.compile(rf"Module\s+'{prefix}pmficsql\.dhop'", re.IGNORECASE)
        if not module_pat.search(data):
            findings.append({
                "rule": "Z08", "severity": "warning", "line": 0,
                "message": f"Prefixe {prefix.upper()}_ utilise sans Module '{prefix}pmficsql.dhop'",
                "context": ""
            })


def check_Z11(lines, findings):
    """Seek_* sans Initialize_*_PostFetch dans les 5 lignes suivantes."""
    seek_pat = re.compile(r'\bSeek_\w+', re.IGNORECASE)
    postfetch_pat = re.compile(r'\bInitialize_\w+_PostFetch\b', re.IGNORECASE)
    for i, line in enumerate(lines):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        if seek_pat.search(code):
            found = False
            for j in range(i + 1, min(i + 6, len(lines))):
                if postfetch_pat.search(lines[j]):
                    found = True
                    break
            if not found:
                findings.append({
                    "rule": "Z11", "severity": "warning", "line": i + 1,
                    "message": "Seek_* sans Initialize_*_PostFetch dans les 5 lignes suivantes",
                    "context": line.rstrip()
                })


def check_Z12(lines, findings):
    """Procedure/Function GT_/RT_/GG_ sans SetPrefixeModule dans le corps."""
    proc_pat = re.compile(r'^\s*(Procedure|Function)\s+((GT|RT|GG)_\w+)', re.IGNORECASE)
    end_pat = re.compile(r'^\s*End[PF]\b', re.IGNORECASE)
    set_prefix_pat = re.compile(r'\bSetPrefixeModule\b', re.IGNORECASE)

    in_block = False
    block_start = None
    block_name = None
    has_set_prefix = False

    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        m = proc_pat.match(line)
        if m:
            if in_block and not has_set_prefix:
                findings.append({
                    "rule": "Z12", "severity": "warning", "line": block_start,
                    "message": f"{block_name} sans SetPrefixeModule",
                    "context": ""
                })
            in_block = True
            block_start = i
            block_name = m.group(2)
            has_set_prefix = False
            continue
        if in_block:
            if set_prefix_pat.search(strip_comment(line)):
                has_set_prefix = True
            if end_pat.match(line):
                if not has_set_prefix:
                    findings.append({
                        "rule": "Z12", "severity": "warning", "line": block_start,
                        "message": f"{block_name} sans SetPrefixeModule",
                        "context": ""
                    })
                in_block = False
                block_start = None
                block_name = None
                has_set_prefix = False


def check_M01(lines, findings):
    """Init_Module sans Get_CheckObject_Data."""
    data_code = ""
    for line in lines:
        if not is_comment_line(line):
            data_code += strip_comment(line) + "\n"
    if re.search(r'\bInit_Module\b', data_code, re.IGNORECASE):
        if not re.search(r'\b(GT|RT|GG)_Get_CheckObject_Data\b', data_code, re.IGNORECASE):
            findings.append({
                "rule": "M01", "severity": "warning", "line": 0,
                "message": "Init_Module sans appel a Get_CheckObject_Data",
                "context": ""
            })


def check_M02(lines, findings):
    """Init_Module sans initialisation record (= INIT)."""
    data_code = ""
    for line in lines:
        if not is_comment_line(line):
            data_code += strip_comment(line) + "\n"
    if re.search(r'\bInit_Module\b', data_code, re.IGNORECASE):
        if not re.search(r'=\s*INIT\b', data_code, re.IGNORECASE):
            findings.append({
                "rule": "M02", "severity": "warning", "line": 0,
                "message": "Init_Module sans initialisation du record principal (= INIT)",
                "context": ""
            })


def check_M03(lines, findings):
    """A5_Stack_OutputMode sans A5_UnStack_OutputMode apparie."""
    stack_count = 0
    unstack_count = 0
    for line in lines:
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        stack_count += len(re.findall(r'\bA5_Stack_OutputMode\b', code, re.IGNORECASE))
        unstack_count += len(re.findall(r'\bA5_UnStack_OutputMode\b', code, re.IGNORECASE))
    if stack_count != unstack_count:
        findings.append({
            "rule": "M03", "severity": "warning", "line": 0,
            "message": f"A5_Stack_OutputMode ({stack_count}) != A5_UnStack_OutputMode ({unstack_count})",
            "context": ""
        })


def check_M04(lines, findings):
    """GT_PreUpdate_recordSql (ou RT_/GG_) sans majuser."""
    pat = re.compile(r'\b(GT|RT|GG)_PreUpdate_recordSql\b', re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        m = pat.search(code)
        if m:
            if not re.search(r'\bmajuser\b', code, re.IGNORECASE):
                findings.append({
                    "rule": "M04", "severity": "warning", "line": i,
                    "message": f"{m.group(0)} sans majuser dans les parametres",
                    "context": line.rstrip()
                })


def check_M05(lines, findings):
    """Check_*_Field_* sans test <> vide."""
    # Detecter les blocs Procedure Check_*_Field_*
    proc_pat = re.compile(r'^\s*Procedure\s+(Check_\w+_Field_\w+)', re.IGNORECASE)
    end_pat = re.compile(r'^\s*EndP\b', re.IGNORECASE)
    ne_pat = re.compile(r"""<>\s*['"]\s*['"]|<>\s*''""")

    in_check = False
    check_name = None
    check_start = None
    has_ne_test = False

    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        m = proc_pat.match(line)
        if m:
            if in_check and not has_ne_test:
                findings.append({
                    "rule": "M05", "severity": "warning", "line": check_start,
                    "message": f"{check_name} sans test <> vide",
                    "context": ""
                })
            in_check = True
            check_name = m.group(1)
            check_start = i
            has_ne_test = False
            continue
        if in_check:
            code = strip_comment(line)
            if ne_pat.search(code):
                has_ne_test = True
            if end_pat.match(line):
                if not has_ne_test:
                    findings.append({
                        "rule": "M05", "severity": "warning", "line": check_start,
                        "message": f"{check_name} sans test <> vide",
                        "context": ""
                    })
                in_check = False
                check_name = None
                check_start = None
                has_ne_test = False


def check_F02(lines, findings, filepath):
    """Prefixe domaine incorrect dans appels framework."""
    basename = os.path.basename(filepath).lower()
    # Determiner le prefixe attendu du fichier
    expected = None
    if basename.startswith("gt"):
        expected = "GT_"
    elif basename.startswith("rt"):
        expected = "RT_"
    elif basename.startswith("gg"):
        expected = "GG_"
    if expected is None:
        return

    # Chercher les appels avec un mauvais prefixe
    wrong_prefixes = {"GT_", "RT_", "GG_"} - {expected}
    for wrong in wrong_prefixes:
        pat = re.compile(rf'\b{wrong}\w+', re.IGNORECASE)
        for i, line in enumerate(lines, 1):
            if is_comment_line(line):
                continue
            code = strip_comment(line)
            if pat.search(code):
                findings.append({
                    "rule": "F02", "severity": "warning", "line": i,
                    "message": f"Prefixe {wrong} dans un fichier {expected[:-1].lower()}*.dhsp",
                    "context": line.rstrip()
                })


def check_F03(lines, findings):
    """WebRequestOpen sans WebRequestClose."""
    open_count = 0
    close_count = 0
    for line in lines:
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        open_count += len(re.findall(r'\b(WebRequestOpen|WebRequest)\b', code, re.IGNORECASE))
        close_count += len(re.findall(r'\bWebRequestClose\b', code, re.IGNORECASE))
    # WebRequest seul compte aussi comme open
    if open_count > 0 and close_count == 0:
        findings.append({
            "rule": "F03", "severity": "warning", "line": 0,
            "message": f"WebRequestOpen/WebRequest ({open_count}) sans WebRequestClose",
            "context": ""
        })
    elif open_count > close_count:
        findings.append({
            "rule": "F03", "severity": "warning", "line": 0,
            "message": f"WebRequestOpen ({open_count}) > WebRequestClose ({close_count})",
            "context": ""
        })


def check_F04(lines, findings):
    """JsonOpen sans JsonClose."""
    open_count = 0
    close_count = 0
    for line in lines:
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        open_count += len(re.findall(r'\bJsonOpen\b', code, re.IGNORECASE))
        close_count += len(re.findall(r'\bJsonClose\b', code, re.IGNORECASE))
    if open_count > 0 and close_count == 0:
        findings.append({
            "rule": "F04", "severity": "warning", "line": 0,
            "message": f"JsonOpen ({open_count}) sans JsonClose",
            "context": ""
        })
    elif open_count > close_count:
        findings.append({
            "rule": "F04", "severity": "warning", "line": 0,
            "message": f"JsonOpen ({open_count}) > JsonClose ({close_count})",
            "context": ""
        })


# ---------------------------------------------------------------------------
# Regle S06 (.dhsf) — Code DIVA hors [diva]...[/diva]
# ---------------------------------------------------------------------------

def check_S06(lines, findings):
    """Code DIVA dans un .dhsf hors bloc [diva]...[/diva]."""
    diva_keywords = re.compile(
        r'\b(Procedure|Function|If|Loop|While|EndP|EndF|EndIf|EndLoop|BeginP|BeginF)\b',
        re.IGNORECASE
    )
    in_diva_block = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip().lower()
        if stripped == "[diva]":
            in_diva_block = True
            continue
        if stripped == "[/diva]":
            in_diva_block = False
            continue
        if not in_diva_block and diva_keywords.search(line):
            findings.append({
                "rule": "S06", "severity": "error", "line": i,
                "message": "Code DIVA detecte hors bloc [diva]...[/diva]",
                "context": line.rstrip()
            })


# ---------------------------------------------------------------------------
# Regles .dhsq
# ---------------------------------------------------------------------------

def check_S07(lines, findings):
    """Code DIVA detecte dans un .dhsq."""
    diva_keywords = re.compile(
        r'\b(Procedure|Function|If|Loop|While|EndP|EndF|EndIf|EndLoop|BeginP|BeginF)\b',
        re.IGNORECASE
    )
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Ignorer les commentaires XML
        if stripped.startswith("<!--") or stripped.startswith("-->"):
            continue
        if diva_keywords.search(stripped):
            findings.append({
                "rule": "S07", "severity": "error", "line": i,
                "message": "Code DIVA detecte dans un fichier .dhsq",
                "context": line.rstrip()
            })


def check_R01(data, findings):
    """Pas de Dos = MZ.Dos."""
    if not re.search(r'Dos\s*=\s*MZ\.Dos', data):
        findings.append({
            "rule": "R01", "severity": "warning", "line": 0,
            "message": "Pas de Dos = MZ.Dos dans le fichier",
            "context": ""
        })


def check_R02(data, findings):
    """Pas de OverWrittenBy."""
    if "OverWrittenBy" not in data:
        findings.append({
            "rule": "R02", "severity": "warning", "line": 0,
            "message": "Pas de OverWrittenBy dans le fichier",
            "context": ""
        })


def check_R03(lines, findings):
    """Fichier vide ou tres court."""
    non_empty = [l for l in lines if l.strip()]
    if len(non_empty) < 5:
        findings.append({
            "rule": "R03", "severity": "warning", "line": 0,
            "message": f"Fichier tres court ({len(non_empty)} lignes non vides)",
            "context": ""
        })


def check_R04(filepath, findings):
    """Nom de fichier non conforme."""
    basename = os.path.basename(filepath).lower()
    # Les .dhsq doivent suivre un pattern type xxxrecordsql.dhsq
    if not re.match(r'^[a-z]{2,4}\w+\.dhsq$', basename):
        findings.append({
            "rule": "R04", "severity": "warning", "line": 0,
            "message": f"Nom de fichier potentiellement non conforme : {basename}",
            "context": ""
        })


def check_R05(data, findings):
    """Placeholder — HFileVersion."""
    # Placeholder : signaler si HFileVersion est absent
    if "HFileVersion" not in data:
        findings.append({
            "rule": "R05", "severity": "warning", "line": 0,
            "message": "HFileVersion absent du fichier",
            "context": ""
        })


# ---------------------------------------------------------------------------
# Regles .dhsd
# ---------------------------------------------------------------------------

def check_D01_D02(lines, findings):
    """Chevauchement (D01) et trous (D02) entre champs."""
    in_champs = False
    current_table = ""
    fields = []  # list of (line_num, name, position, size)

    field_pat = re.compile(r'^\s*(\w+)\s*=\s*(\d+)\s*,\s*(\d+)')  # nom=position,taille

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("[TABLE]") or re.match(r'\[TABLE\s', stripped):
            current_table = stripped
        if stripped == "[CHAMPS]":
            in_champs = True
            fields = []
            continue
        if stripped == "[/CHAMPS]":
            # Valider les champs
            _validate_fields(fields, current_table, findings)
            in_champs = False
            fields = []
            continue
        if in_champs:
            m = field_pat.match(stripped)
            if m:
                fields.append((i, m.group(1), int(m.group(2)), int(m.group(3))))


def _validate_fields(fields, table_name, findings):
    """Valide la continuite des champs dans une table."""
    if len(fields) < 2:
        return
    for j in range(1, len(fields)):
        prev_line, prev_name, prev_pos, prev_size = fields[j - 1]
        curr_line, curr_name, curr_pos, curr_size = fields[j]
        expected = prev_pos + prev_size
        if curr_pos < expected:
            findings.append({
                "rule": "D01", "severity": "error", "line": curr_line,
                "message": f"Chevauchement : {curr_name} (pos {curr_pos}) chevauche {prev_name} (fin {expected}) dans {table_name}",
                "context": ""
            })
        elif curr_pos > expected:
            findings.append({
                "rule": "D02", "severity": "error", "line": curr_line,
                "message": f"Trou de {curr_pos - expected} octets entre {prev_name} et {curr_name} dans {table_name}",
                "context": ""
            })


def check_D03(lines, findings):
    """Champ U<Table> manquant."""
    in_table = False
    table_name = ""
    has_u_field = False
    table_line = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        m = re.match(r'\[TABLE\]\s*(\w+)', stripped)
        if not m:
            m = re.match(r'Nom\s*=\s*(\w+)', stripped)
        if stripped == "[TABLE]":
            if in_table and table_name and not has_u_field:
                findings.append({
                    "rule": "D03", "severity": "warning", "line": table_line,
                    "message": f"Champ U{table_name} manquant dans la table {table_name}",
                    "context": ""
                })
            in_table = True
            table_name = ""
            has_u_field = False
            table_line = i
            continue
        if in_table and stripped.startswith("Nom="):
            table_name = stripped.split("=", 1)[1].strip()
        if in_table and re.match(r'^\s*U\w+\s*=', stripped):
            has_u_field = True
        if stripped in ("[/TABLE]", "[/TABLES]"):
            if in_table and table_name and not has_u_field:
                findings.append({
                    "rule": "D03", "severity": "warning", "line": table_line,
                    "message": f"Champ U{table_name} manquant dans la table {table_name}",
                    "context": ""
                })
            in_table = False


def check_D05(raw_bytes, findings):
    """Encodage UTF-8 detecte dans .dhsd."""
    if is_utf8_encoded(raw_bytes):
        findings.append({
            "rule": "D05", "severity": "error", "line": 0,
            "message": "Fichier encode en UTF-8 au lieu de ISO-8859-1",
            "context": ""
        })


def check_D06(raw_bytes, findings):
    """Fins de ligne LF dans .dhsd."""
    if has_lf_line_endings(raw_bytes):
        findings.append({
            "rule": "D06", "severity": "error", "line": 0,
            "message": "Fins de ligne LF detectees (attendu : CRLF)",
            "context": ""
        })


def check_D07(data, findings):
    """[/CHAMPS] manquant."""
    opens = data.count("[CHAMPS]")
    closes = data.count("[/CHAMPS]")
    if opens > closes:
        findings.append({
            "rule": "D07", "severity": "error", "line": 0,
            "message": f"[/CHAMPS] manquant ({opens} ouvertures, {closes} fermetures)",
            "context": ""
        })


def check_D08(data, findings):
    """[/TABLES] manquant."""
    opens = data.count("[TABLES]")
    closes = data.count("[/TABLES]")
    if opens > closes:
        findings.append({
            "rule": "D08", "severity": "error", "line": 0,
            "message": f"[/TABLES] manquant ({opens} ouvertures, {closes} fermetures)",
            "context": ""
        })


def check_D09(data, findings):
    """[/INDEX] manquant."""
    opens = data.count("[INDEX]")
    closes = data.count("[/INDEX]")
    if opens > closes:
        findings.append({
            "rule": "D09", "severity": "error", "line": 0,
            "message": f"[/INDEX] manquant ({opens} ouvertures, {closes} fermetures)",
            "context": ""
        })


# ---------------------------------------------------------------------------
# Regles .dhsf
# ---------------------------------------------------------------------------

def check_E01(lines, findings):
    """Element graphique sans [presentation]."""
    elements = {"[champ]", "[obj_texte]", "[champ_tableau]", "[tableau]", "[groupbox]"}
    for i, line in enumerate(lines, 1):
        stripped = line.strip().lower()
        if stripped in elements:
            # Chercher [presentation] dans les 15 lignes suivantes (avant le prochain element)
            found = False
            for j in range(i, min(i + 15, len(lines))):
                next_stripped = lines[j].strip().lower()
                if next_stripped == "[presentation]":
                    found = True
                    break
                if next_stripped in elements and j > i:
                    break
            if not found:
                findings.append({
                    "rule": "E01", "severity": "warning", "line": i,
                    "message": f"{line.strip()} sans [presentation]",
                    "context": line.rstrip()
                })


def check_E08(data, findings):
    """[diva_base] manquant."""
    if "[diva_base]" not in data.lower():
        findings.append({
            "rule": "E08", "severity": "warning", "line": 0,
            "message": "[diva_base] manquant dans le fichier",
            "context": ""
        })


def check_E09(lines, findings):
    """IDs dupliques."""
    id_pat = re.compile(r'\bid\s*=\s*(\d+)', re.IGNORECASE)
    ids = {}  # id -> first line
    for i, line in enumerate(lines, 1):
        m = id_pat.search(line)
        if m:
            id_val = m.group(1)
            if id_val in ids:
                findings.append({
                    "rule": "E09", "severity": "warning", "line": i,
                    "message": f"ID {id_val} duplique (deja vu ligne {ids[id_val]})",
                    "context": line.rstrip()
                })
            else:
                ids[id_val] = i


def check_E10(raw_bytes, findings):
    """Encodage UTF-8 dans .dhsf."""
    if is_utf8_encoded(raw_bytes):
        findings.append({
            "rule": "E10", "severity": "error", "line": 0,
            "message": "Fichier encode en UTF-8 au lieu de ISO-8859-1",
            "context": ""
        })


# ---------------------------------------------------------------------------
# Regles .dhpt / .dhps
# ---------------------------------------------------------------------------

def check_P01(raw_bytes, findings):
    """Encodage UTF-8."""
    if is_utf8_encoded(raw_bytes):
        findings.append({
            "rule": "P01", "severity": "error", "line": 0,
            "message": "Fichier encode en UTF-8 au lieu de ISO-8859-1",
            "context": ""
        })


def check_P02(raw_bytes, findings):
    """Fins de ligne LF."""
    if has_lf_line_endings(raw_bytes):
        findings.append({
            "rule": "P02", "severity": "error", "line": 0,
            "message": "Fins de ligne LF detectees (attendu : CRLF)",
            "context": ""
        })


def check_P04_dhpt(lines, findings):
    """Premiere ligne ne contient pas xwin-projet (.dhpt)."""
    if lines and "xwin-projet" not in lines[0].lower():
        findings.append({
            "rule": "P04", "severity": "error", "line": 1,
            "message": "Premiere ligne ne contient pas 'xwin-projet'",
            "context": lines[0].rstrip() if lines else ""
        })


def check_P04_dhps(lines, findings):
    """Premiere ligne ne contient pas xwin-sprojet (.dhps)."""
    if lines and "xwin-sprojet" not in lines[0].lower():
        findings.append({
            "rule": "P04", "severity": "error", "line": 1,
            "message": "Premiere ligne ne contient pas 'xwin-sprojet'",
            "context": lines[0].rstrip() if lines else ""
        })


def check_P05(lines, findings):
    """Premiere ligne contient xwin-sprojet au lieu de xwin-projet."""
    if lines and "xwin-sprojet" in lines[0].lower():
        findings.append({
            "rule": "P05", "severity": "error", "line": 1,
            "message": "Premiere ligne contient 'xwin-sprojet' au lieu de 'xwin-projet' (fichier .dhpt)",
            "context": lines[0].rstrip()
        })


def check_P06(lines, findings):
    """Dans [includes], syntaxe fic="x"," " (ne doit pas etre la)."""
    in_includes = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip().lower()
        if stripped == "[includes]":
            in_includes = True
            continue
        if stripped.startswith("[") and stripped != "[includes]":
            in_includes = False
            continue
        if in_includes:
            if re.search(r'fic\s*=\s*"[^"]*"\s*,\s*"\s*"', line):
                findings.append({
                    "rule": "P06", "severity": "error", "line": i,
                    "message": 'Syntaxe fic="x"," " dans [includes] (le ," " ne doit pas etre la)',
                    "context": line.rstrip()
                })


def check_P07(lines, findings):
    """Dans [fichiers], syntaxe fic="x" sans ," "."""
    in_fichiers = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip().lower()
        if stripped == "[fichiers]":
            in_fichiers = True
            continue
        if stripped.startswith("[") and stripped != "[fichiers]":
            in_fichiers = False
            continue
        if in_fichiers:
            if re.search(r'fic\s*=\s*"[^"]*"', line) and not re.search(r'fic\s*=\s*"[^"]*"\s*,\s*"\s*"', line):
                findings.append({
                    "rule": "P07", "severity": "error", "line": i,
                    "message": 'Syntaxe fic="x" sans ," " dans [fichiers]',
                    "context": line.rstrip()
                })


def check_P09(lines, findings):
    """zdiva.dhsp absent de [includes]."""
    in_includes = False
    found = False
    for line in lines:
        stripped = line.strip().lower()
        if stripped == "[includes]":
            in_includes = True
            continue
        if stripped.startswith("[") and in_includes:
            break
        if in_includes and "zdiva.dhsp" in stripped:
            found = True
            break
    if not found:
        findings.append({
            "rule": "P09", "severity": "warning", "line": 0,
            "message": "zdiva.dhsp absent de la section [includes]",
            "context": ""
        })


def check_P12(data, findings):
    """Section [autres] manquante."""
    if "[autres]" not in data.lower():
        findings.append({
            "rule": "P12", "severity": "warning", "line": 0,
            "message": "Section [autres] manquante",
            "context": ""
        })


def check_P13(lines, findings):
    """Sections obligatoires manquantes (.dhpt)."""
    required = {"[general]", "[profil]", "[sousprojets]", "[projetsfusion]", "[fabricationmere]", "[autres]"}
    found = set()
    for line in lines:
        stripped = line.strip().lower()
        if stripped in required:
            found.add(stripped)
    missing = required - found
    if missing:
        findings.append({
            "rule": "P13", "severity": "warning", "line": 0,
            "message": f"Sections obligatoires manquantes : {', '.join(sorted(missing))}",
            "context": ""
        })


def check_P14(lines, findings):
    """Mot developpement sans accent dans contexte profil."""
    in_profil = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip().lower()
        if stripped == "[profil]":
            in_profil = True
            continue
        if stripped.startswith("[") and in_profil:
            in_profil = False
        if in_profil and "developpement" in stripped and "développement" not in line.lower():
            # Verifier que ce n'est pas deja accentue (en ISO-8859-1, e accent = 0xE9)
            findings.append({
                "rule": "P14", "severity": "warning", "line": i,
                "message": "Mot 'developpement' sans accent dans section [profil]",
                "context": line.rstrip()
            })


def check_P15(lines, findings):
    """Mot developpement_x13.txt sans accent."""
    for i, line in enumerate(lines, 1):
        if "developpement_x13.txt" in line.lower():
            findings.append({
                "rule": "P15", "severity": "warning", "line": i,
                "message": "developpement_x13.txt sans accent",
                "context": line.rstrip()
            })


# ---------------------------------------------------------------------------
# Dispatch par type de fichier
# ---------------------------------------------------------------------------

def lint_dhsp(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .dhsp."""
    rule_map = {
        "S01": lambda: check_S01(lines, findings),
        "S02": lambda: check_S02(lines, findings),
        "S03": lambda: check_S03(lines, findings),
        "S04": lambda: check_S04(lines, findings),
        "S05": lambda: check_S05(lines, findings),
        "L01": lambda: check_L01(lines, findings),
        "L02": lambda: check_L02(lines, findings),
        "L03": lambda: check_L03(lines, findings),
        "L04": lambda: check_L04(lines, findings),
        "Z02": lambda: check_Z02(lines, findings),
        "Z03": lambda: check_Z03(lines, findings),
        "Z08": lambda: check_Z08(lines, findings),
        "Z11": lambda: check_Z11(lines, findings),
        "Z12": lambda: check_Z12(lines, findings),
        "M01": lambda: check_M01(lines, findings),
        "M02": lambda: check_M02(lines, findings),
        "M03": lambda: check_M03(lines, findings),
        "M04": lambda: check_M04(lines, findings),
        "M05": lambda: check_M05(lines, findings),
        "F02": lambda: check_F02(lines, findings, path),
        "F03": lambda: check_F03(lines, findings),
        "F04": lambda: check_F04(lines, findings),
    }
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            fn()


def lint_dhsq(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .dhsq."""
    rule_map = {
        "S07": lambda: check_S07(lines, findings),
        "R01": lambda: check_R01(data, findings),
        "R02": lambda: check_R02(data, findings),
        "R03": lambda: check_R03(lines, findings),
        "R04": lambda: check_R04(path, findings),
        "R05": lambda: check_R05(data, findings),
    }
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            fn()


def lint_dhsd(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .dhsd."""
    rule_map = {
        "D01": lambda: check_D01_D02(lines, findings),
        "D02": lambda: None,  # D02 est traite dans D01
        "D03": lambda: check_D03(lines, findings),
        "D05": lambda: check_D05(raw_bytes, findings),
        "D06": lambda: check_D06(raw_bytes, findings),
        "D07": lambda: check_D07(data, findings),
        "D08": lambda: check_D08(data, findings),
        "D09": lambda: check_D09(data, findings),
    }
    # D01 et D02 sont traites ensemble
    d01_d02_done = False
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            if rule_id in ("D01", "D02"):
                if not d01_d02_done:
                    check_D01_D02(lines, findings)
                    d01_d02_done = True
            else:
                fn()


def lint_dhsf(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .dhsf."""
    rule_map = {
        "S06": lambda: check_S06(lines, findings),
        "E01": lambda: check_E01(lines, findings),
        "E08": lambda: check_E08(data, findings),
        "E09": lambda: check_E09(lines, findings),
        "E10": lambda: check_E10(raw_bytes, findings),
    }
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            fn()


def lint_dhpt(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .dhpt."""
    rule_map = {
        "P01": lambda: check_P01(raw_bytes, findings),
        "P02": lambda: check_P02(raw_bytes, findings),
        "P04": lambda: check_P04_dhpt(lines, findings),
        "P05": lambda: check_P05(lines, findings),
        "P13": lambda: check_P13(lines, findings),
        "P14": lambda: check_P14(lines, findings),
        "P15": lambda: check_P15(lines, findings),
    }
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            fn()


def lint_dhps(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .dhps."""
    rule_map = {
        "P01": lambda: check_P01(raw_bytes, findings),
        "P02": lambda: check_P02(raw_bytes, findings),
        "P04": lambda: check_P04_dhps(lines, findings),
        "P06": lambda: check_P06(lines, findings),
        "P07": lambda: check_P07(lines, findings),
        "P09": lambda: check_P09(lines, findings),
        "P12": lambda: check_P12(data, findings),
    }
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            fn()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

DISPATCHERS = {
    ".dhsp": lint_dhsp,
    ".dhsq": lint_dhsq,
    ".dhsd": lint_dhsd,
    ".dhsf": lint_dhsf,
    ".dhpt": lint_dhpt,
    ".dhps": lint_dhps,
}


def main():
    parser = argparse.ArgumentParser(
        description="Linter pour fichiers DIVA (.dhsp, .dhsq, .dhsd, .dhsf, .dhpt, .dhps)"
    )
    parser.add_argument("--path", required=True, help="Chemin du fichier a analyser")
    parser.add_argument("--rules", default=None,
                        help="Liste de regles a verifier (virgule, ex: S01,S02). Defaut: toutes.")
    parser.add_argument("--severity", choices=["error", "warning", "all"], default="all",
                        help="Filtrer par severite (defaut: all)")
    parser.add_argument("--format", choices=["json", "text"], default="json",
                        help="Format de sortie (defaut: json)")
    args = parser.parse_args()

    filepath = os.path.abspath(args.path)
    if not os.path.isfile(filepath):
        print(f"Erreur : fichier introuvable : {filepath}", file=sys.stderr)
        sys.exit(2)

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in DISPATCHERS:
        print(f"Erreur : extension non supportee : {ext}", file=sys.stderr)
        print(f"Extensions supportees : {', '.join(sorted(DISPATCHERS.keys()))}", file=sys.stderr)
        sys.exit(2)

    # Lire le fichier en binaire
    try:
        with open(filepath, "rb") as f:
            raw_bytes = f.read()
    except OSError as e:
        print(f"Erreur lecture fichier : {e}", file=sys.stderr)
        sys.exit(2)

    # Decoder en ISO-8859-1
    data = raw_bytes.decode("iso-8859-1")
    lines = data.splitlines()

    # Filtrer les regles demandees
    active_rules = None
    if args.rules:
        active_rules = set(r.strip().upper() for r in args.rules.split(","))
        # Verifier que les regles existent
        unknown = active_rules - set(RULES.keys())
        if unknown:
            print(f"Attention : regles inconnues ignorees : {', '.join(sorted(unknown))}", file=sys.stderr)
            active_rules -= unknown

    # Executer le linter
    findings = []
    print(f"Analyse de {filepath} ({ext})...", file=sys.stderr)
    DISPATCHERS[ext](filepath, data, lines, raw_bytes, findings, active_rules)

    # Filtrer par severite
    if args.severity == "error":
        findings = [f for f in findings if f["severity"] == "error"]
    elif args.severity == "warning":
        findings = [f for f in findings if f["severity"] == "warning"]

    # Trier par numero de ligne
    findings.sort(key=lambda f: (f["line"], f["rule"]))

    # Construire la sortie
    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]

    result = {
        "file": filepath,
        "type": ext,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total": len(findings),
            "errors": len(errors),
            "warnings": len(warnings),
        }
    }

    if args.format == "json":
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()  # newline final
    else:
        # Format texte lisible
        print(f"{'=' * 60}")
        print(f"Fichier : {filepath}")
        print(f"Type    : {ext}")
        print(f"{'=' * 60}")
        if not findings:
            print("Aucun probleme detecte.")
        else:
            for f in findings:
                sev = f["severity"].upper()
                line_info = f"L{f['line']}" if f["line"] > 0 else "---"
                print(f"[{sev:7s}] {f['rule']} {line_info}: {f['message']}")
                if f["context"]:
                    print(f"          | {f['context']}")
        print(f"{'-' * 60}")
        print(f"Total: {len(findings)} ({len(errors)} erreurs, {len(warnings)} warnings)")

    # Exit code
    if findings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
