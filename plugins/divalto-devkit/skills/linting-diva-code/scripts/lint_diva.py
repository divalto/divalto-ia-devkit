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
    "Z14": {"severity": "info",    "types": [".dhsd"], "desc": "Champ [CHAMP] avec suffixe FK standard (rappel Check_*_Field_*)"},
    "Z15": {"severity": "warning", "types": [".dhsp"], "desc": "Check_*_Field_* appelle Find_<X> sans import Module de validation"},
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
    "R05": {"severity": "warning", "types": [".dhsq"], "desc": "Balise <DictionarySql> absente du fichier .dhsq"},
    "R07": {"severity": "warning", "types": [".dhsp"], "desc": "ReaderOpen sans ReaderClose"},
    # CI — Regles shift-left moulinettes CI
    "CI01": {"severity": "warning", "types": [".dhsp", ".dhsi", ".dhse", ".dhsq", ".dhsf"], "desc": "SetModuleInfo/ModuleInfo absent"},
    "CI02": {"severity": "error",   "types": [".dhsp"], "desc": "Procedure/Function non PUBLIC dans TT/TE"},
    "CI03": {"severity": "warning", "types": [".dhsp"], "desc": ".WHERE sans AddCondition"},
    "CI04": {"severity": "error",   "types": [".dhsp"], "desc": "Include de PC*.dhsp dans TT/TM"},
    "CI05": {"severity": "warning", "types": [".dhsq"], "desc": "#top sans #fetch (fuite)"},
    "CI06": {"severity": "error",   "types": [".dhsq"], "desc": "GROUP BY avec INSERT/UPDATE/DELETE=YES"},
    "CI07": {"severity": "warning", "types": [".sql"],  "desc": "Variable SQL casse incoherente"},
    "CI08": {"severity": "error",   "types": [".dhsq"], "desc": "CE/CEBIN compare a un entier"},
    "CI09": {"severity": "warning", "types": [".dhsq"], "desc": "SELECT TOP 1 au lieu de #TOP1"},
    "CI10": {"severity": "warning", "types": [".dhsp"], "desc": "ScrollBar au lieu de ScrollBar32"},
    "CI11": {"severity": "warning", "types": [".dhsp"], "desc": "Code mort apres RETURN"},
    # .dhsd
    "D01": {"severity": "error",   "types": [".dhsd"], "desc": "Chevauchement de champs dans [TABLE]"},
    "D02": {"severity": "error",   "types": [".dhsd"], "desc": "Trou entre champs"},
    "D03": {"severity": "warning", "types": [".dhsd"], "desc": "Champ U<Table> manquant"},
    "D04": {"severity": "warning", "types": [".dhsd"], "desc": "Champ reference dans [CHAMPS] sans [CHAMP] correspondant"},
    "D05": {"severity": "error",   "types": [".dhsd"], "desc": "Encodage UTF-8 detecte"},
    "D06": {"severity": "error",   "types": [".dhsd"], "desc": "Fins de ligne LF detectees"},
    "D07": {"severity": "error",   "types": [".dhsd"], "desc": "[/CHAMPS] manquant"},
    "D08": {"severity": "error",   "types": [".dhsd"], "desc": "[/TABLES] manquant"},
    "D09": {"severity": "error",   "types": [".dhsd"], "desc": "[/INDEX] manquant"},
    "D10": {"severity": "warning", "types": [".dhsd"], "desc": "Mauvais numero de table dans la CLE de l'index"},
    "D11": {"severity": "warning", "types": [".dhsd"], "desc": "Base nommee sans le prefixe du dictionnaire"},
    "D12": {"severity": "warning", "types": [".dhsd"], "desc": "Champ [CHAMP] hors PascalCase (hors canoniques Ce1..CeA)"},
    "D13": {"severity": "warning", "types": [".dhsd"], "desc": "Base [BASE] hors PascalCase"},
    "D14": {"severity": "warning", "types": [".dhsd"], "desc": "Index [INDEX] hors pattern Index_<Lettre>[_<Desc>]"},
    # .dhsf
    "E01": {"severity": "warning", "types": [".dhsf"], "desc": "Element graphique sans [presentation]"},
    "E08": {"severity": "warning", "types": [".dhsf"], "desc": "[diva_base] manquant"},
    "E09": {"severity": "warning", "types": [".dhsf"], "desc": "IDs dupliques"},
    "E10": {"severity": "error",   "types": [".dhsf"], "desc": "Encodage UTF-8 detecte"},
    "E12": {"severity": "warning", "types": [".dhsf"], "desc": "Code DIVA excessif dans [diva] (> 200 lignes)"},
    "E13": {"severity": "info",    "types": [".dhsf"], "desc": "Enregistrement declare mais non reference"},
    "E14": {"severity": "info",    "types": [".dhsf"], "desc": "Melange WPF/classique detecte"},
    "E15": {"severity": "info",    "types": [".dhsf"], "desc": "Page vide hors convention zoom"},
    "E16": {"severity": "error",   "types": [".dhsf"], "desc": "Champ audit (UserCr/UserMo/UserCrDh/UserMoDh) attendu mais absent du masque zoom"},
    "E17": {"severity": "warning", "types": [".dhsf"], "desc": "Ordre des groupboxes de l'onglet Identifiants non canonique"},
    "E18": {"severity": "info",    "types": [".dhsf"], "desc": "Positions X hors valeurs canoniques (5, 8, 10, 12, 14, 16, 18, 26) -- rapport de deviation"},
    "E19": {"severity": "warning", "types": [".dhsf"], "desc": "Taille d'ecran (nb_lig x nb_col) hors normes"},
    "E20": {"severity": "error",   "types": [".dhsf"], "desc": "Groupbox sous-dimensionne (taille_H < NbLignes * 10 + 18)"},
    "E21": {"severity": "warning", "types": [".dhsf"], "desc": "Gap insuffisant (< 8) entre deux groupbox consecutives sur meme colonne X"},
    "Z16": {"severity": "warning", "types": [".dhsf"], "desc": "Champ [champ] avec suffixe FK fiable dont [touches] n'a pas le f8=<zoom> attendu"},
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
    """Pas de OverWrittenBy (recherche insensible a la casse -- ERP X.13 utilise lowercase)."""
    if "overwrittenby" not in data.lower():
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
    """Balise <DictionarySql> absente du fichier .dhsq."""
    if "<DictionarySql" not in data:
        findings.append({
            "rule": "R05", "severity": "warning", "line": 0,
            "message": "Balise <DictionarySql> absente — le fichier n'est peut-etre pas un .dhsq valide",
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


def check_D04(lines, findings):
    """Champ reference dans [CHAMPS] sans [CHAMP] correspondant."""
    # Collecter tous les noms de [CHAMP] declares
    declared_fields = set()
    champ_pat = re.compile(r'^\[CHAMP\]')
    nom_pat = re.compile(r'^Nom\s*=\s*(\w+)')

    in_champ = False
    for line in lines:
        stripped = line.strip()
        if champ_pat.match(stripped):
            in_champ = True
            continue
        if in_champ and nom_pat.match(stripped):
            m = nom_pat.match(stripped)
            declared_fields.add(m.group(1))
            in_champ = False
        if stripped.startswith("[") and not stripped.startswith("[CHAMP]"):
            in_champ = False

    # Noms reserves qui n'ont pas de [CHAMP] correspondant
    reserved_names = {"Filler"}

    # Scanner les [CHAMPS] pour trouver les champs references
    in_champs = False
    champs_field_pat = re.compile(r'^Nom\s*=\s*(\w+)\s*,')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "[CHAMPS]":
            in_champs = True
            continue
        if stripped == "[/CHAMPS]":
            in_champs = False
            continue
        if in_champs:
            m = champs_field_pat.match(stripped)
            if m:
                field_name = m.group(1)
                if field_name not in declared_fields and field_name not in reserved_names:
                    findings.append({
                        "rule": "D04", "severity": "warning", "line": i,
                        "message": f"Champ '{field_name}' utilise dans [CHAMPS] sans [CHAMP] correspondant",
                        "context": stripped[:80]
                    })


def check_D10(path, lines, findings):
    """Mauvais numero de table dans la CLE de l'index."""
    # Collecter les bases et leurs tables avec leur numero d'ordre
    # [BASE] -> [TABLES] -> Nom=TableName,NumeroOrdre
    base_tables = {}  # base_name -> {table_name: order_index}
    current_base = ""
    in_tables_section = False

    base_nom_pat = re.compile(r'^Nom\s*=\s*(\w+)')
    table_ref_pat = re.compile(r'^Nom\s*=\s*(\w+)\s*,\s*(\d+)')

    in_base = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[BASE]":
            in_base = True
            current_base = ""
            continue
        if in_base and not in_tables_section and base_nom_pat.match(stripped):
            m = base_nom_pat.match(stripped)
            current_base = m.group(1)
            base_tables[current_base] = {}
        if stripped == "[TABLES]":
            in_tables_section = True
            continue
        if stripped == "[/TABLES]":
            in_tables_section = False
            continue
        if in_tables_section:
            m = table_ref_pat.match(stripped)
            if m:
                base_tables.setdefault(current_base, {})[m.group(1)] = int(m.group(2))
        if stripped in ("[/BASE]", "[INDEX]", "[CHAMP]"):
            in_base = False

    # Scanner les [INDEX] et verifier CLE=base,lettre,champ,taille,...
    # Le numero de table dans CLE doit correspondre a l'ordre dans [TABLES]
    cle_pat = re.compile(r'^CLE\s*=\s*(\w+)\s*,')
    in_index = False
    index_line = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "[INDEX]":
            in_index = True
            index_line = i
            continue
        if stripped == "[/INDEX]":
            in_index = False
            continue
        if in_index:
            m = cle_pat.match(stripped)
            if m:
                base_ref = m.group(1)
                if base_ref not in base_tables:
                    findings.append({
                        "rule": "D10", "severity": "warning", "line": i,
                        "message": f"CLE reference la base '{base_ref}' qui n'est pas declaree dans [BASE]",
                        "context": stripped[:80]
                    })


def check_D11(path, lines, findings):
    """Base nommee sans le prefixe du dictionnaire."""
    # Extraire le prefixe du dictionnaire depuis le nom du fichier
    # Convention: a5dd.dhsd -> prefixe "a5", gtfdd.dhsd -> prefixe "gtf"
    basename = os.path.basename(path).lower()
    if not basename.endswith(".dhsd"):
        return

    # Le prefixe est tout ce qui precede "dd.dhsd" ou "fdd.dhsd"
    name_no_ext = basename[:-5]  # retirer .dhsd
    # Chercher le pattern xxxfdd ou xxxdd
    dict_prefix = ""
    if name_no_ext.endswith("fdd"):
        dict_prefix = name_no_ext[:-3]  # retirer "fdd"
    elif name_no_ext.endswith("dd"):
        dict_prefix = name_no_ext[:-2]  # retirer "dd"

    if not dict_prefix:
        return  # impossible de determiner le prefixe

    # Scanner les [BASE] et verifier que leur nom commence par le prefixe
    in_base = False
    base_nom_pat = re.compile(r'^Nom\s*=\s*(\w+)')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "[BASE]":
            in_base = True
            continue
        if in_base and base_nom_pat.match(stripped):
            m = base_nom_pat.match(stripped)
            base_name = m.group(1)
            if not base_name.lower().startswith(dict_prefix):
                findings.append({
                    "rule": "D11", "severity": "warning", "line": i,
                    "message": f"Base '{base_name}' ne commence pas par le prefixe '{dict_prefix}' du dictionnaire {basename}",
                    "context": stripped[:80]
                })
            in_base = False
        if stripped in ("[/BASE]", "[INDEX]", "[CHAMP]", "[TABLE]"):
            in_base = False


# Noms canoniques ALLCAPS tolerés malgre le "hors PascalCase" (Ce1..CeA, Ce, CEBIN, CENOTE, filler)
_D12_CANONICAL_ALLCAPS = {
    "CE", "CE1", "CE2", "CE3", "CE4", "CE5", "CE6", "CE7", "CE8", "CE9", "CEA",
    "CEBIN", "CENOTE", "CEJOINT", "CEFOU", "CECLI", "CEART",
    "ID", "L1", "L2",
}


def _is_pascal_case(name: str) -> bool:
    """True si name = PascalCase (premiere lettre majuscule, pas d'underscore, pas ALLCAPS)."""
    if not name or not name[0].isupper():
        return False
    if "_" in name or "-" in name:
        return False
    has_lower = any(c.islower() for c in name)
    return has_lower  # au moins une minuscule


def check_D12(lines, findings):
    """Champ [CHAMP] hors PascalCase (hors canoniques Ce1..CeA)."""
    in_champ = False
    nom_pat = re.compile(r'^Nom\s*=\s*([^,]+)')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "[CHAMP]":
            in_champ = True
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_champ = False
            continue
        if in_champ and line.startswith("Nom="):
            m = nom_pat.match(stripped)
            if m:
                field_name = m.group(1).strip()
                # Ignorer les canoniques ALLCAPS
                if field_name.upper() in _D12_CANONICAL_ALLCAPS:
                    in_champ = False
                    continue
                if not _is_pascal_case(field_name):
                    findings.append({
                        "rule": "D12", "severity": "warning", "line": i,
                        "message": f"Champ '{field_name}' hors PascalCase (convention DIVA a 91 % PascalCase)",
                        "context": stripped[:80]
                    })
            in_champ = False  # Nom= apparait une fois par bloc [CHAMP]


def check_D13(path, lines, findings):
    """Base [BASE] hors PascalCase (complementaire de D11 sur la casse).

    D11 verifie le prefixe, D13 verifie la casse PascalCase. Couverture reelle :
    97 % des bases X.13 sont en PascalCase. Les ALLCAPS (mofdd, rcftredd) et les
    lowercase (pvftmp, qufjq, xqfu) sont des anomalies historiques.
    """
    in_base = False
    base_nom_pat = re.compile(r'^Nom\s*=\s*(\w+)')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "[BASE]":
            in_base = True
            continue
        if in_base and base_nom_pat.match(stripped):
            m = base_nom_pat.match(stripped)
            base_name = m.group(1)
            if not _is_pascal_case(base_name):
                findings.append({
                    "rule": "D13", "severity": "warning", "line": i,
                    "message": f"Base '{base_name}' hors PascalCase (97 % des bases X.13 sont en PascalCase)",
                    "context": stripped[:80]
                })
            in_base = False
        if stripped in ("[/BASE]", "[INDEX]", "[CHAMP]", "[TABLE]"):
            in_base = False


# ---------------------------------------------------------------------------
# Z14 -- FK orphelin cote dictionnaire (advisory)
# ---------------------------------------------------------------------------
_Z14_FK_SUFFIXES = {
    # Suffixes predicteurs fiables (>=90 %) de cible FK -- cf. docs/ZOOMS-STANDARDS-CATALOGUE.md table C
    "Pay", "Pays", "Dev", "Devise", "Depo",
    "Cpt", "Col", "Axe", "Jnl",
    "Sref1", "Sref2", "Cpostal",
    "Dos", "Caisse", "Affaire", "Contact",
    "Ind",
}


def check_Z14(lines, findings):
    """Champ [CHAMP] avec suffixe FK standard -- rappel documentaire.

    Ne verifie pas l'existence du Check_*_Field_* correspondant (hors scope
    linter fichier-unique). Emet un INFO pour chaque champ dont le suffixe
    est dans la taxonomie FK fiable : rappel au developpeur d'implementer
    les Check_*_Field_* + import Module dans le .dhsp Module Check associe.
    """
    in_champ = False
    nom_pat = re.compile(r'^Nom\s*=\s*([^,]+)')
    tok_pat = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z]|$)")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "[CHAMP]":
            in_champ = True
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_champ = False
            continue
        if in_champ and line.startswith("Nom="):
            m = nom_pat.match(stripped)
            if m:
                field_name = m.group(1).strip()
                toks = tok_pat.findall(field_name)
                if toks and toks[-1] in _Z14_FK_SUFFIXES:
                    findings.append({
                        "rule": "Z14", "severity": "info", "line": i,
                        "message": (
                            f"Champ '{field_name}' a un suffixe FK standard ({toks[-1]}) -- "
                            f"verifier Check_<SRC>_Field_{field_name}(+_Lib) et "
                            f"import Module dans le .dhsp Module Check"
                        ),
                        "context": stripped[:80]
                    })
            in_champ = False


# ---------------------------------------------------------------------------
# Z15 -- Find_<X> sans Module import (orphelin)
# ---------------------------------------------------------------------------
# Exemptions : cibles qui n'ont pas de module Gttmchk<x>.dhop dedie
_Z15_EXEMPT_TARGETS = {
    # Comptes comptables : framework CC indirect, pas de module unique
    "C3", "C4", "C5", "C6", "C7", "C8", "C9",
}


def check_Z15(path, lines, findings):
    """Check_*_Field_* appelle Find_<X> sans import Module "Gttmchk<x>.dhop".

    Detecte les imports orphelins : compilation reussira par resolution tardive
    uniquement si un autre module de la chaine importe Gttmchk<x>.dhop
    (contingent) -- sinon erreur "Mot inconnu".
    """
    text = "\n".join(lines)
    # Modules importes dans le fichier
    modules = {m.lower() for m in re.findall(r'Module\s+"([^"]+\.dhop)"', text, re.IGNORECASE)}
    # Find_<X> definis localement (pas besoin d'import)
    local_defs = {
        m.group(1).lower()
        for m in re.finditer(
            r'(?:^|\n)\s*(?:Public|Private)?\s*(?:function|procedure)\s+\w+\s+Find_([A-Za-z0-9]+)\b',
            text, re.IGNORECASE,
        )
    }
    # Check_*_Field_* procedures
    check_pat = re.compile(
        r'Public\s+function\s+int\s+(Check_[A-Za-z0-9_]+?_Field_[A-Za-z0-9]+)\s*\(',
        re.IGNORECASE,
    )
    find_pat = re.compile(r'Find_([A-Za-z0-9]+)\s*\(', re.IGNORECASE)
    end_pat = re.compile(r'\bendf\b', re.IGNORECASE)

    reported = set()  # eviter doublons (proc, target)
    for cm in check_pat.finditer(text):
        proc_name = cm.group(1)
        if proc_name.lower().endswith("_lib"):
            continue
        start_line = text[:cm.start()].count('\n') + 1
        body_start = cm.end()
        endm = end_pat.search(text, body_start)
        body_end = endm.start() if endm else body_start + 5000
        body = text[body_start:body_end]
        for fm in find_pat.finditer(body):
            target = fm.group(1)
            target_key = target.upper()
            if target_key in _Z15_EXEMPT_TARGETS:
                continue
            if target.lower() in local_defs:
                continue
            expected_module = f"gttmchk{target.lower()}.dhop"
            if expected_module in modules:
                continue
            # Tolerer si le module cible est le fichier lui-meme
            basename = os.path.basename(path).lower()
            if basename == f"gttmchk{target.lower()}.dhsp":
                continue
            key = (proc_name, target)
            if key in reported:
                continue
            reported.add(key)
            findings.append({
                "rule": "Z15", "severity": "warning", "line": start_line,
                "message": (
                    f"{proc_name} appelle Find_{target} sans import "
                    f'Module "{expected_module}" (orphelin)'
                ),
                "context": f"Find_{target}(...)"
            })


# ---------------------------------------------------------------------------
# Z16 -- Champ .dhsf avec suffixe FK fiable sans f8=<zoom> attendu
# ---------------------------------------------------------------------------
# Mapping restreint aux suffixes >=95 % fiables ayant un zoom t-table unique.
# Source : docs/ZOOMS-STANDARDS-CATALOGUE.md Table A (numeros) + Table C (suffixes).
# Elargir avec precaution : ne pas inclure les suffixes c-compta (Cpt, Col, Axe,
# Jnl) qui ciblent C3/C4/C5 sans zoom simple unique.
_Z16_SUFFIX_TO_ZOOM = {
    "Pay":     9053,  # Pays (T013)
    "Pays":    9053,
    "Dev":     9047,  # Devise (T007)
    "Devise":  9047,
    "Depo":    9057,  # Depot (T017)
    "Cpostal": 9097,  # CodePostal (T057)
    "Lang":    9056,  # Langue (T016)
    "Op":      9060,  # CodeOperation (T020)
}
# Lookup case-insensitive : `pay` aussi bien que `Pay` (les .dhsf utilisent
# souvent `donnee=xq,pay,g3xq` en minuscules).
_Z16_SUFFIX_LOWER_TO_EXPECTED = {
    k.lower(): (k, v) for k, v in _Z16_SUFFIX_TO_ZOOM.items()
}


def _z16_extract_field_segments(donnee_value):
    """Extrait les segments alphanumeriques d'un `donnee=<value>`.

    Format 1 : `Table.Field` (ou sous-cle) -> split par '.'.
    Format 2 : `alias,field,recordsql` (masque ecran) -> split par ','.
    Retourne la liste des segments non-vides.
    """
    parts = []
    # Split combine sur ',' et '.'
    for chunk in donnee_value.replace(".", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


def _z16_detect_suffix_in_segments(segments):
    """Cherche un suffixe FK fiable dans les segments extraits.

    Pour chaque segment, decompose en tokens PascalCase et teste le dernier
    (case-insensitive). Retourne (suffixe_canonique, zoom_attendu) ou None.
    """
    tok_pat = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z]|$)")
    for seg in segments:
        toks = tok_pat.findall(seg)
        if not toks:
            continue
        last = toks[-1].lower()
        if last in _Z16_SUFFIX_LOWER_TO_EXPECTED:
            return _Z16_SUFFIX_LOWER_TO_EXPECTED[last]
    return None


def check_Z16(lines, findings):
    """Champ [champ] de .dhsf avec suffixe FK fiable sans f8=<zoom> attendu.

    Parse chaque bloc [champ] de top-niveau et verifie la coherence :
    - si `donnee=` contient un segment dont le suffixe FK est catalogue
      (Pay/Pays, Dev/Devise, Depo, Cpostal, Lang, Op),
    - alors la section [touches] du meme bloc doit contenir `f8=<num>` avec
      le numero de zoom standard correspondant.

    Les blocs sans `donnee=` (textes, groupboxes, boutons) sont ignores.
    Les champs dont le suffixe n'est PAS dans le catalogue sont ignores
    (pas de warning a tort sur les champs metiers genuinely non-FK).
    """
    # Parcours lineaire avec etat : bloc [champ] courant -> donnee/f8 collectes
    in_champ = False
    block_start = 0
    donnee_value = None
    f8_value = None

    def emit_if_needed():
        if donnee_value is None:
            return
        segments = _z16_extract_field_segments(donnee_value)
        match = _z16_detect_suffix_in_segments(segments)
        if match is None:
            return
        suffix_canon, expected_zoom = match
        if f8_value is None:
            findings.append({
                "rule": "Z16", "severity": "warning", "line": block_start,
                "message": (
                    f"Champ 'donnee={donnee_value}' a un suffixe FK fiable "
                    f"'{suffix_canon}' mais aucun 'f8=' dans [touches]. "
                    f"Attendu : f8={expected_zoom} (zoom {suffix_canon})."
                ),
                "context": f"donnee={donnee_value}",
            })
        elif f8_value != str(expected_zoom):
            findings.append({
                "rule": "Z16", "severity": "warning", "line": block_start,
                "message": (
                    f"Champ 'donnee={donnee_value}' (suffixe FK '{suffix_canon}') "
                    f"a 'f8={f8_value}' au lieu de 'f8={expected_zoom}' attendu."
                ),
                "context": f"donnee={donnee_value}, f8={f8_value}",
            })

    for i, line in enumerate(lines, 1):
        # Un nouveau bloc top-niveau (sans indentation) reinitialise l'etat.
        if line.startswith("[") and line.rstrip().endswith("]"):
            # Avant de reinitialiser, emettre pour le bloc precedent si pertinent.
            if in_champ:
                emit_if_needed()
            header = line.rstrip()
            if header == "[champ]":
                in_champ = True
                block_start = i
                donnee_value = None
                f8_value = None
            else:
                in_champ = False
            continue

        if not in_champ:
            continue

        stripped = line.strip()
        if stripped.startswith("donnee="):
            donnee_value = stripped.split("=", 1)[1].strip()
        elif stripped.startswith("f8="):
            f8_value = stripped.split("=", 1)[1].strip()

    # Emettre pour le dernier bloc (fin de fichier sans nouveau top-header)
    if in_champ:
        emit_if_needed()


def check_D14(lines, findings):
    """Index [INDEX] hors pattern `Index_<Lettre>[_<Discriminant>]`.

    Pattern canonique (73 % X.13) : Index_A, Index_B, ..., Index_Z
    Pattern descriptif acceptable (27 %) : Index_A_<DescriptifPascalCase>
    """
    in_index = False
    idx_nom_pat = re.compile(r'^Nom\s*=\s*([^,]+)')
    # Accepte Index_A, Index_A_Desc, index_a, Sql_... NON
    canonical_pat = re.compile(r'^[Ii]ndex_[A-Za-z0-9]+(_[A-Za-z0-9]+)?$')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "[INDEX]":
            in_index = True
            continue
        if in_index and stripped.startswith("Nom="):
            m = idx_nom_pat.match(stripped)
            if m:
                idx_name = m.group(1).strip()
                if not canonical_pat.match(idx_name):
                    findings.append({
                        "rule": "D14", "severity": "warning", "line": i,
                        "message": f"Index '{idx_name}' hors pattern canonique Index_<Lettre>[_<Desc>]",
                        "context": stripped[:80]
                    })
            in_index = False  # Nom= n'apparait qu'une fois par bloc [INDEX]
        if stripped in ("[/INDEX]", "[CHAMP]", "[TABLE]", "[BASE]"):
            in_index = False


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


def check_E12(lines, findings):
    """E12 — Code DIVA excessif dans [diva] (> 200 lignes)."""
    in_diva = False
    diva_start = 0
    diva_lines = 0
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped == '[diva]':
            in_diva = True
            diva_start = i + 1
            diva_lines = 0
        elif stripped == '[/diva]' and in_diva:
            if diva_lines > 200:
                findings.append({
                    "rule": "E12", "severity": "warning", "line": diva_start,
                    "message": f"Section [diva] contient {diva_lines} lignes (seuil: 200). Externaliser dans un .dhsp",
                    "context": ""
                })
            in_diva = False
        elif in_diva:
            diva_lines += 1


def check_E13(data, lines, findings):
    """E13 — Enregistrements declares mais non references par les champs."""
    # Extraire les alias de [enregistrements]
    in_enreg = False
    aliases = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower() == '[enregistrements]':
            in_enreg = True
            continue
        if in_enreg:
            if stripped.startswith('[') and stripped != '[enregistrements]':
                break
            # Format: "fichier.dhsd",,vue,alias,taille,type
            parts = stripped.strip('"').split(',')
            if len(parts) >= 4:
                alias = parts[3].strip().strip('"')
                if alias:
                    aliases[alias] = i + 1

    if not aliases:
        return

    # Scanner donnee= dans tout le fichier
    data_lower = data.lower()
    for alias, line_num in aliases.items():
        # Chercher alias dans donnee=xxx,yyy,ALIAS ou dans le code DIVA
        if alias.lower() not in data_lower:
            findings.append({
                "rule": "E13", "severity": "info", "line": line_num,
                "message": f"Enregistrement alias '{alias}' declare mais non reference dans le masque",
                "context": ""
            })


def check_E14(lines, findings):
    """E14 — Melange WPF/classique detecte."""
    has_wpf = False
    has_classic = False
    for line in lines:
        stripped = line.strip().lower()
        if stripped in ('[panel_wpf]', '[grille_wpf]'):
            has_wpf = True
        elif stripped in ('[champ]', '[champ_tableau]', '[tableau]', '[groupbox]'):
            has_classic = True
    if has_wpf and has_classic:
        findings.append({
            "rule": "E14", "severity": "info", "line": 0,
            "message": "Melange d'elements WPF (panel_wpf/grille_wpf) et classiques. Verifier que le melange est par zone logique (page complete)",
            "context": ""
        })


AUDIT_FIELDS = ("UserCr", "UserCrDh", "UserMo", "UserMoDh")

AUTHORIZED_SIZES = {
    (33, 120), (35, 120), (31, 120),
    (25, 90), (25, 60), (25, 120),
    (33, 130), (35, 130),
}

CANONICAL_X_VALUES = {0, 5, 8, 10, 12, 14, 16, 18, 26}


def _find_identifiants_page_range(lines):
    """Retourne (start_line, end_line) 0-based de la page Identifiants, ou None.

    Detection : page contenant un [onglet_page] avec libelle="Identifiants".
    """
    page_starts = []
    for i, line in enumerate(lines):
        if line.strip().lower() == "[page]":
            page_starts.append(i)
    page_starts.append(len(lines))

    for k in range(len(page_starts) - 1):
        start, end = page_starts[k], page_starts[k + 1]
        chunk = "\n".join(lines[start:end])
        m = re.search(r'\[onglet_page\][^\[]*?libelle\s*=\s*"([^"]+)"', chunk, re.DOTALL)
        if m and m.group(1).lower().startswith("identifiant"):
            return (start, end)
    return None


def _extract_groupboxes_in_range(lines, start, end):
    """Retourne [(line_idx, Y, X, texte), ...] pour chaque [groupbox] entre start et end."""
    results = []
    i = start
    while i < end:
        if lines[i].strip().lower() == "[groupbox]":
            box_start = i
            y = x = None
            texte = None
            j = i + 1
            while j < end and not (
                lines[j].strip().lower().startswith("[groupbox]")
                or (lines[j].strip().startswith("[") and not lines[j].strip().lower().startswith("[param"))
                and lines[j].strip().lower() not in (
                    "[presentation]", "[param_groupbox]", "[description]",
                )
            ):
                if y is None:
                    m = re.match(r'\s*position\s*=\s*(\d+)\s*,\s*(\d+)', lines[j])
                    if m:
                        y, x = int(m.group(1)), int(m.group(2))
                if texte is None:
                    m = re.match(r'\s*texte\s*=\s*"([^"]*)"', lines[j])
                    if m:
                        texte = m.group(1)
                j += 1
                if y is not None and texte is not None:
                    break
            if y is not None and texte is not None:
                results.append((box_start + 1, y, x if x is not None else 0, texte))
            i = j
        else:
            i += 1
    return results


def check_E16(data, lines, findings):
    """E16 -- Champs audit presents dans le masque zoom mais absents de l'onglet Identifiants.

    Heuristique single-file : si le masque est un zoom (type_masque=2) et contient un onglet
    Identifiants, on s'attend a ce que UserCr/UserCrDh/UserMo/UserMoDh apparaissent dans les
    `donnee=` de la page Identifiants. Rapport champ par champ si absent.
    """
    data_lower = data.lower()
    is_zoom = 'type_masque=2' in data_lower.replace(' ', '') or 'type_masque = 2' in data_lower
    if not is_zoom:
        return
    id_range = _find_identifiants_page_range(lines)
    if id_range is None:
        return
    start, end = id_range
    chunk = "\n".join(lines[start:end])
    donnees = re.findall(r'donnee\s*=\s*[^,]+,\s*([^,\n]+)\s*,', chunk, re.IGNORECASE)
    donnee_fields = {d.strip() for d in donnees}

    for field in AUDIT_FIELDS:
        if not any(field.lower() == d.lower() for d in donnee_fields):
            findings.append({
                "rule": "E16", "severity": "error", "line": start + 1,
                "message": f"Champ audit '{field}' absent de l'onglet Identifiants (zoom detecte). Socle audit canonique incomplet. Voir NORMES-GRAPHIQUES.md section 7",
                "context": ""
            })


def check_E17(data, lines, findings):
    """E17 -- Ordre des groupboxes de l'onglet Identifiants non canonique.

    Canonique : Codes enregistrement* en 1er (Y min), Creation + Derniere modification en
    dernier (Y max parmi les groupboxes audit). Extensions domaine tolerees au-dela.
    """
    id_range = _find_identifiants_page_range(lines)
    if id_range is None:
        return
    start, end = id_range
    boxes = _extract_groupboxes_in_range(lines, start, end)
    if not boxes:
        return
    boxes_sorted = sorted(boxes, key=lambda b: b[1])  # tri par Y

    def match_codes_enr(t):
        return re.search(r'code\s*enregistr', t, re.IGNORECASE) is not None

    def match_creation(t):
        return re.fullmatch(r'\s*cr[ée]ation\s*', t, re.IGNORECASE) is not None

    def match_derniere_modif(t):
        return re.search(r"derni[eè]re\s+modif", t, re.IGNORECASE) is not None

    codes_idx = next((i for i, b in enumerate(boxes_sorted) if match_codes_enr(b[3])), None)
    creation_idx = next((i for i, b in enumerate(boxes_sorted) if match_creation(b[3])), None)
    derniere_idx = next((i for i, b in enumerate(boxes_sorted) if match_derniere_modif(b[3])), None)

    # Codes enregistrement doit etre en premier si present
    if codes_idx is not None and codes_idx != 0:
        findings.append({
            "rule": "E17", "severity": "warning", "line": boxes_sorted[codes_idx][0],
            "message": f"Groupbox 'Codes enregistrement*' attendu en 1er (Y min) de l'onglet Identifiants mais place en position {codes_idx + 1} sur {len(boxes_sorted)}",
            "context": f'texte="{boxes_sorted[codes_idx][3]}"'
        })

    # Creation + Derniere modification forment le "coeur de fin" : le MAX(creation_idx, derniere_idx)
    # doit correspondre au dernier groupbox "audit" (on tolere des extensions domaine apres).
    audit_indices = [i for i in (creation_idx, derniere_idx) if i is not None]
    if len(audit_indices) >= 1:
        audit_group_end = max(audit_indices)
        # Tous les groupboxes entre 0 et audit_group_end doivent etre connus du socle audit,
        # sinon il y a une extension domaine intercalee a tort au milieu.
        for i in range(audit_group_end + 1):
            t = boxes_sorted[i][3]
            if not (
                match_codes_enr(t) or match_creation(t) or match_derniere_modif(t)
                or re.search(r'protection|derni[eè]re\s+op[eé]ration', t, re.IGNORECASE)
            ):
                findings.append({
                    "rule": "E17", "severity": "warning", "line": boxes_sorted[i][0],
                    "message": f"Groupbox '{t}' intercale dans le bloc audit Identifiants (position {i + 1}) alors que le bloc audit canonique (Codes enr / Protection / Derniere op / Creation / Derniere modif) doit etre contigu",
                    "context": ""
                })


def check_E18(data, lines, findings):
    """E18 -- Positions X hors valeurs canoniques. Rapport agrege en 1 seule info."""
    total = 0
    deviant = 0
    for line in lines:
        m = re.match(r'\s*position\s*=\s*(\d+)\s*,\s*(\d+)', line)
        if m:
            x = int(m.group(2))
            # On regarde uniquement les X "faibles" (< 30), les plus pertinents pour
            # la regle "bord gauche X=5" -- les X eleves sont souvent des 2nd/3eme colonnes
            # pour lesquelles la norme n'impose pas de valeur fixe.
            if x < 30:
                total += 1
                if x not in CANONICAL_X_VALUES:
                    deviant += 1
    if total == 0:
        return
    ratio = 100.0 * deviant / total
    if deviant > 0:
        findings.append({
            "rule": "E18", "severity": "info", "line": 0,
            "message": f"{deviant}/{total} positions X en 1re colonne hors valeurs canoniques {{5, 8, 10, 12, 14, 16, 18, 26}} ({ratio:.1f}%). Voir NORMES-GRAPHIQUES.md section 2",
            "context": ""
        })


def check_E19(data, lines, findings):
    """E19 -- Taille d'ecran (page 1 nb_lig x nb_col) hors normes."""
    # On cherche la 1re occurrence nb_lig + nb_col (typiquement page 1 = page principale)
    lig = None
    col = None
    line_num = 0
    for i, line in enumerate(lines):
        m1 = re.match(r'\s*nb_lig\s*=\s*(\d+)', line)
        m2 = re.match(r'\s*nb_col\s*=\s*(\d+)', line)
        if m1 and lig is None:
            lig = int(m1.group(1))
            line_num = i + 1
        if m2 and col is None:
            col = int(m2.group(1))
        if lig is not None and col is not None:
            break
    if lig is None or col is None:
        return
    if (lig, col) not in AUTHORIZED_SIZES:
        authorized_str = ", ".join(f"{a}x{b}" for a, b in sorted(AUTHORIZED_SIZES))
        findings.append({
            "rule": "E19", "severity": "warning", "line": line_num,
            "message": f"Taille {lig}x{col} hors normes autorisees ({authorized_str}). Voir NORMES-GRAPHIQUES.md section 3.1",
            "context": ""
        })


def _extract_all_groupboxes(lines):
    """Scan minimal : retourne [{line, page, y, x, h, w, n_children}] pour tous les groupbox.

    Heuristique : pour chaque [groupbox] au niveau indent 1 d'une page, lit position et taille
    dans la sous-section [presentation], puis compte les [champ]/[obj_texte] au niveau indent 2
    jusqu'au prochain element de meme indent ou fin de page.
    """
    out = []
    cur_page = 0
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.lower().startswith("[page]"):
            cur_page = 0  # sera capture par numero= suivant
            i += 1
            continue
        m_num = re.match(r'\s*numero\s*=\s*(\d+)\s*$', line)
        if m_num:
            cur_page = int(m_num.group(1))
            i += 1
            continue
        if stripped.lower() == "[groupbox]":
            gb_line = i + 1
            indent = len(line) - len(line.lstrip(" "))
            y, x, h, w = None, None, None, None
            n_children = 0
            j = i + 1
            while j < n:
                s2 = lines[j]
                ind2 = len(s2) - len(s2.lstrip(" "))
                t2 = s2.strip().lower()
                # Fin de ce groupbox : prochaine section de meme indent ou inferieur
                if ind2 <= indent and s2.lstrip().startswith("[") and t2 != "[presentation]" and t2 != "[param_groupbox]" and not t2.startswith("[info_bulle"):
                    # inclut les autres [groupbox], [champ], [obj_texte], [page], etc.
                    break
                m_pos = re.match(r'\s*position\s*=\s*(\d+)\s*,\s*(\d+)', s2)
                if m_pos and y is None:
                    y, x = int(m_pos.group(1)), int(m_pos.group(2))
                m_tail = re.match(r'\s*taille\s*=\s*(\d+)\s*,\s*(\d+)', s2)
                if m_tail and h is None:
                    h, w = int(m_tail.group(1)), int(m_tail.group(2))
                if t2 in ("[champ]", "[obj_texte]", "[case_a_cocher]", "[bouton_radio]", "[groupe_radio]") and ind2 == indent + 1:
                    n_children += 1
                j += 1
            if y is not None and h is not None:
                out.append({
                    "line": gb_line, "page": cur_page,
                    "y": y, "x": x or 0, "h": h, "w": w or 0,
                    "n_children": n_children,
                })
            i = j
            continue
        i += 1
    return out


def check_E20(data, lines, findings):
    """E20 -- Groupbox sous-dimensionne (taille_H < NbLignes * 10 + 18).

    Borne minimale (espacement 10 + overhead 18). Si `H < n_children * 10 + 18` avec
    `n_children > 0`, le titre sera tronque ou chevauchera le premier champ
    (incident RaceChat 2026-04-23, cf R-007).
    """
    gbs = _extract_all_groupboxes(lines)
    for gb in gbs:
        if gb["n_children"] <= 0:
            continue
        min_h = gb["n_children"] * 10 + 18
        if gb["h"] < min_h:
            findings.append({
                "rule": "E20", "severity": "error", "line": gb["line"],
                "message": (
                    f"Groupbox page {gb['page']} taille_H={gb['h']} < min {min_h} "
                    f"({gb['n_children']} enfants * 10 espacement min + 18 overhead) -- "
                    f"formule canonique NbLignes * espacement (10/12/14) + 18. "
                    f"Voir NORMES-GRAPHIQUES.md section 2.5"
                ),
                "context": ""
            })


def check_E21(data, lines, findings):
    """E21 -- Gap < 8 entre deux groupbox consecutives sur meme colonne X (norme v7 section 2.5)."""
    gbs = _extract_all_groupboxes(lines)
    # Grouper par (page, x) puis trier par Y
    by_col = {}
    for gb in gbs:
        key = (gb["page"], gb["x"])
        by_col.setdefault(key, []).append(gb)
    for key, group in by_col.items():
        group.sort(key=lambda g: g["y"])
        for prev, cur in zip(group, group[1:]):
            gap = cur["y"] - (prev["y"] + prev["h"])
            if gap < 8:
                findings.append({
                    "rule": "E21", "severity": "warning", "line": cur["line"],
                    "message": (
                        f"Gap {gap} < 8 entre groupbox (Y={prev['y']} H={prev['h']}) "
                        f"et groupbox (Y={cur['y']}) -- page {cur['page']}, colonne X={cur['x']}. "
                        f"Tolere empiriquement en production X.13 (chevauchement de bordures) "
                        f"mais non-conforme norme v7 section 2.5"
                    ),
                    "context": ""
                })


def check_E15(data, lines, findings):
    """E15 — Pages vides hors convention zoom (pages 4-10 des zooms sont OK)."""
    is_zoom = 'type_masque=2' in data.lower() or 'type_masque = 2' in data.lower()

    # Parser les pages et leurs contenus
    pages = []
    current_page = None
    current_page_line = 0
    current_page_num = 0
    has_children = False

    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped == '[page]':
            if current_page is not None and not has_children:
                pages.append((current_page_num, current_page_line))
            current_page = True
            current_page_line = i + 1
            current_page_num = 0
            has_children = False
        elif current_page is not None:
            # Detecter le numero de page
            m = re.match(r'\s*numero\s*=\s*(\d+)', line, re.IGNORECASE)
            if m:
                current_page_num = int(m.group(1))
            # Detecter un element enfant
            if stripped in ('[obj_texte]', '[champ]', '[champ_tableau]', '[tableau]',
                           '[groupbox]', '[onglet_page]', '[multi_choix]',
                           '[multi_choix_tableau]', '[groupe_radio]', '[bouton_graphique]',
                           '[arbre]', '[panel_wpf]', '[grille_wpf]'):
                has_children = True

    # Derniere page
    if current_page is not None and not has_children:
        pages.append((current_page_num, current_page_line))

    # Filtrer les pages vides
    for page_num, line_num in pages:
        if is_zoom and 4 <= page_num <= 10:
            continue  # Convention zoom : pages 4-10 vides OK
        if page_num == 1 and is_zoom:
            continue  # Page 1 du zoom = conteneur principal, souvent vide
        if page_num > 0:
            findings.append({
                "rule": "E15", "severity": "info", "line": line_num,
                "message": f"Page {page_num} ne contient aucun element graphique",
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
# Regles CI — Shift-left des moulinettes CI nightly
# ---------------------------------------------------------------------------

def check_CI01(filepath, lines, findings):
    """SetModuleInfo (ou ModuleInfo pour .dhsq) absent dans les 100 premieres lignes.
    Source : moulinette 001. Min 30 chars (.dhsp/.dhsi/.dhse/.dhsf), 120 chars (.dhsq).
    """
    ext = os.path.splitext(filepath)[1].lower()
    is_dhsq = ext == ".dhsq"
    keyword = "MODULEINFO" if is_dhsq else "SETMODULEINFO"
    min_len = 120 if is_dhsq else 30
    max_lines = min(100, len(lines))

    for i in range(max_lines):
        line = lines[i]
        if is_comment_line(line):
            continue
        code = strip_comment(line).upper()
        if keyword in code and len(line.rstrip()) >= min_len:
            return  # OK
    findings.append({
        "rule": "CI01", "severity": "warning", "line": 0,
        "message": f"{keyword} absent ou trop court dans les 100 premieres lignes (min {min_len} chars)",
        "context": ""
    })


def check_CI02(filepath, lines, findings):
    """Procedure/Function non PUBLIC dans un programme TT*.dhsp ou TE*.dhsp.
    Source : moulinette 004.
    """
    basename = os.path.basename(filepath).upper()
    name_no_ext = os.path.splitext(basename)[0]
    # Cible : TT* et TE* uniquement
    if not (name_no_ext.startswith("TT") or name_no_ext.startswith("TE")):
        return
    # Exclure certains prefixes en positions 3-4
    if len(name_no_ext) >= 4:
        mid = name_no_ext[2:4]
        if mid in ("PP", "PC", "PM", "QC", "TC", "TM", "P9", "PZ"):
            return
    if name_no_ext.startswith("DIVALTO") or name_no_ext.startswith("IA_"):
        return

    proc_pat = re.compile(r'^\s*(Procedure|Function)\s+\w+', re.IGNORECASE)
    exclude_pat = re.compile(r'(GETADRESS|PROCEDURECALL|FUNCTIONCALL)', re.IGNORECASE)
    public_pat = re.compile(r'\bPublic\b', re.IGNORECASE)
    proto_pat = re.compile(r'\bProto\b', re.IGNORECASE)

    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        if not proc_pat.match(code):
            continue
        if exclude_pat.search(code):
            continue
        if public_pat.search(code) or proto_pat.search(code):
            continue
        findings.append({
            "rule": "CI02", "severity": "error", "line": i,
            "message": f"Procedure/Function non PUBLIC dans {basename}",
            "context": line.rstrip()
        })


def check_CI03(lines, findings):
    """.WHERE sans AddCondition/AddAndCondition/AddOrCondition dans les 10 lignes suivantes.
    Source : moulinette 009. Detecte .WHERE. suivi d'aucun appel AddCondition.
    Exclut les appels directs .Where.Equal_*, .Where.NotEqual_*, etc. (conditions en ligne).
    """
    where_pat = re.compile(r'\.WHERE\.', re.IGNORECASE)
    # Patterns qui rendent le .WHERE valide (conditions appliquees)
    cond_pat = re.compile(
        r'\.(ADDCONDITION|ADDANDCONDITION|ADDORCONDITION|REMOVECONDITION|USECLAUSE|EXISTS)\b',
        re.IGNORECASE
    )
    # Methodes de condition directes sur WHERE (pas un .WHERE nu)
    direct_cond_pat = re.compile(
        r'\.WHERE\.(EQUAL_|NOTEQUAL_|LIKE_|NOTLIKE_|GREATERTHAN_|LESSTHAN_|GREATEROREQUAL_|LESSOREQUAL_|BETWEEN_|IN_|NOTIN_|ISNULL_|ISNOTNULL_)',
        re.IGNORECASE
    )
    for i, line in enumerate(lines):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        if not where_pat.search(code):
            continue
        # Les appels directs .Where.Equal_*() sont des conditions valides
        if direct_cond_pat.search(code):
            continue
        # Verifier si la ligne elle-meme contient deja une condition
        if cond_pat.search(code):
            continue
        # Chercher dans les 10 lignes suivantes
        found = False
        for j in range(i + 1, min(i + 11, len(lines))):
            next_code = strip_comment(lines[j])
            if cond_pat.search(next_code):
                found = True
                break
        if not found:
            findings.append({
                "rule": "CI03", "severity": "warning", "line": i + 1,
                "message": ".WHERE sans AddCondition/AddAndCondition/AddOrCondition dans les 10 lignes suivantes",
                "context": line.rstrip()
            })


def check_CI04(filepath, lines, findings):
    """Include d'un programme PC*.dhsp dans un TT*.dhsp ou TM*.dhsp.
    Source : moulinette 020.
    """
    basename = os.path.basename(filepath).upper()
    name_no_ext = os.path.splitext(basename)[0]
    if not (name_no_ext.startswith("TT") or name_no_ext.startswith("TM")):
        return

    include_pat = re.compile(r'\bInclude\s+["\']?(PC\w+\.dhsp)', re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        m = include_pat.search(code)
        if m:
            findings.append({
                "rule": "CI04", "severity": "error", "line": i,
                "message": f"Include de {m.group(1)} dans {basename} (PC* interdit dans TT/TM)",
                "context": line.rstrip()
            })


def check_CI05(data, findings):
    """#top sans #fetch correspondant (fuite de ressources).
    Source : moulinette 040.
    """
    # Dans un .dhsq, #top est dans les tags XML
    top_pat = re.compile(r'#top\b', re.IGNORECASE)
    fetch_pat = re.compile(r'#fetch\b', re.IGNORECASE)
    top_count = len(top_pat.findall(data))
    fetch_count = len(fetch_pat.findall(data))
    if top_count > 0 and fetch_count == 0:
        findings.append({
            "rule": "CI05", "severity": "warning", "line": 0,
            "message": f"#top ({top_count} occurrence(s)) sans #fetch correspondant (fuite de ressources)",
            "context": ""
        })


def check_CI06(data, findings):
    """GROUP BY present avec INSERT=YES, UPDATE=YES ou DELETE=YES dans le <FROM>.
    Source : moulinette 052.
    """
    has_groupby = bool(re.search(r'<GroupBy>', data, re.IGNORECASE))
    if not has_groupby:
        return
    # Chercher INSERT=YES, UPDATE=YES, DELETE=YES dans les blocs <FROM>
    from_blocks = re.findall(r'<FROM>(.*?)</FROM>', data, re.IGNORECASE | re.DOTALL)
    for block in from_blocks:
        for attr in ("INSERT", "UPDATE", "DELETE"):
            if re.search(rf'{attr}\s*=\s*"?YES"?', block, re.IGNORECASE):
                findings.append({
                    "rule": "CI06", "severity": "error", "line": 0,
                    "message": f"GROUP BY avec {attr}=YES dans <FROM> (incompatible)",
                    "context": ""
                })
                return  # Un seul signalement suffit


def check_CI07(lines, findings):
    """Variable SQL declaree avec une casse et utilisee avec une autre.
    Source : moulinette 056. Cible : fichiers .sql.
    """
    declare_pat = re.compile(r'DECLARE\s+(@\w+)', re.IGNORECASE)
    var_pat = re.compile(r'(@\w+)')

    # Collecter les declarations
    declarations = {}  # nom_lower -> (nom_declare, ligne)
    for i, line in enumerate(lines, 1):
        for m in declare_pat.finditer(line):
            var_name = m.group(1)
            declarations[var_name.lower()] = (var_name, i)

    if not declarations:
        return

    # Chercher les utilisations avec casse differente
    reported = set()
    for i, line in enumerate(lines, 1):
        for m in var_pat.finditer(line):
            var_name = m.group(1)
            key = var_name.lower()
            if key in declarations:
                declared_name, decl_line = declarations[key]
                if var_name != declared_name and key not in reported:
                    reported.add(key)
                    findings.append({
                        "rule": "CI07", "severity": "warning", "line": i,
                        "message": f"Variable {var_name} utilisee avec casse differente de la declaration {declared_name} (ligne {decl_line})",
                        "context": line.rstrip()
                    })


def check_CI08(lines, findings):
    """Comparaison CE/CEBIN avec un entier au lieu d'une chaine.
    Source : moulinette 801.
    """
    # Pattern : CE = 1, CEBIN = 0, CE <> 2, etc. (pas CE = '1')
    ce_int_pat = re.compile(r'\b(CE\d?|CEBIN\d?)\s*(=|<>|<|>|<=|>=)\s*(\d+)\b', re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        m = ce_int_pat.search(code)
        if m:
            findings.append({
                "rule": "CI08", "severity": "error", "line": i,
                "message": f"{m.group(1)} {m.group(2)} {m.group(3)} : comparer avec une chaine ('{m.group(3)}'), pas un entier",
                "context": line.rstrip()
            })


def check_CI09(data, findings):
    """SELECT TOP 1 au lieu de SELECT #TOP1 (incompatible DB2).
    Source : moulinette 801.
    """
    # Dans un .dhsq, SELECT TOP 1 devrait etre SELECT #TOP1
    top1_pat = re.compile(r'SELECT\s+TOP\s+1\b', re.IGNORECASE)
    for i, line in enumerate(data.splitlines(), 1):
        if top1_pat.search(line):
            findings.append({
                "rule": "CI09", "severity": "warning", "line": i,
                "message": "SELECT TOP 1 au lieu de SELECT #TOP1 (incompatible DB2)",
                "context": line.rstrip()
            })


def check_CI10(lines, findings):
    """ScrollBar au lieu de ScrollBar32.
    Source : moulinette 802.
    """
    pat = re.compile(r'\bScrollBar\b(?!32)', re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        if is_comment_line(line):
            continue
        code = strip_comment(line)
        if pat.search(code):
            findings.append({
                "rule": "CI10", "severity": "warning", "line": i,
                "message": "ScrollBar au lieu de ScrollBar32",
                "context": line.rstrip()
            })


def check_CI11(lines, findings):
    """Code apres instruction RETURN (code mort).
    Source : moulinette 802.
    """
    return_pat = re.compile(r'^\s*RETURN\b', re.IGNORECASE)
    end_pat = re.compile(r'^\s*(EndP|EndF|Procedure|Function)\b', re.IGNORECASE)

    for i, line in enumerate(lines):
        if is_comment_line(line):
            continue
        if return_pat.match(line):
            # Verifier les lignes suivantes jusqu'a EndP/EndF/Procedure/Function
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped or is_comment_line(next_line):
                    continue
                if end_pat.match(next_line):
                    break  # EndP/EndF suit le RETURN, c'est normal
                # Il y a du code actif apres le RETURN
                findings.append({
                    "rule": "CI11", "severity": "warning", "line": j + 1,
                    "message": "Code mort apres RETURN",
                    "context": next_line.rstrip()
                })
                break  # Un seul signalement par RETURN


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
        "Z15": lambda: check_Z15(path, lines, findings),
        "M01": lambda: check_M01(lines, findings),
        "M02": lambda: check_M02(lines, findings),
        "M03": lambda: check_M03(lines, findings),
        "M04": lambda: check_M04(lines, findings),
        "M05": lambda: check_M05(lines, findings),
        "F02": lambda: check_F02(lines, findings, path),
        "F03": lambda: check_F03(lines, findings),
        "F04": lambda: check_F04(lines, findings),
        "CI01": lambda: check_CI01(path, lines, findings),
        "CI02": lambda: check_CI02(path, lines, findings),
        "CI03": lambda: check_CI03(lines, findings),
        "CI04": lambda: check_CI04(path, lines, findings),
        "CI10": lambda: check_CI10(lines, findings),
        "CI11": lambda: check_CI11(lines, findings),
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
        "CI01": lambda: check_CI01(path, lines, findings),
        "CI05": lambda: check_CI05(data, findings),
        "CI06": lambda: check_CI06(data, findings),
        "CI08": lambda: check_CI08(lines, findings),
        "CI09": lambda: check_CI09(data, findings),
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
        "D04": lambda: check_D04(lines, findings),
        "D10": lambda: check_D10(path, lines, findings),
        "D11": lambda: check_D11(path, lines, findings),
        "D12": lambda: check_D12(lines, findings),
        "D13": lambda: check_D13(path, lines, findings),
        "D14": lambda: check_D14(lines, findings),
        "Z14": lambda: check_Z14(lines, findings),
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
        "E12": lambda: check_E12(lines, findings),
        "E13": lambda: check_E13(data, lines, findings),
        "E14": lambda: check_E14(lines, findings),
        "E15": lambda: check_E15(data, lines, findings),
        "E16": lambda: check_E16(data, lines, findings),
        "E17": lambda: check_E17(data, lines, findings),
        "E18": lambda: check_E18(data, lines, findings),
        "E19": lambda: check_E19(data, lines, findings),
        "E20": lambda: check_E20(data, lines, findings),
        "E21": lambda: check_E21(data, lines, findings),
        "Z16": lambda: check_Z16(lines, findings),
        "CI01": lambda: check_CI01(path, lines, findings),
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

def lint_dhsi(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .dhsi (include)."""
    rule_map = {
        "CI01": lambda: check_CI01(path, lines, findings),
    }
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            fn()


def lint_dhse(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .dhse (ecran)."""
    rule_map = {
        "CI01": lambda: check_CI01(path, lines, findings),
    }
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            fn()


def lint_sql(path, data, lines, raw_bytes, findings, active_rules):
    """Lint d'un fichier .sql."""
    rule_map = {
        "CI07": lambda: check_CI07(lines, findings),
    }
    for rule_id, fn in rule_map.items():
        if active_rules is None or rule_id in active_rules:
            fn()


DISPATCHERS = {
    ".dhsp": lint_dhsp,
    ".dhsq": lint_dhsq,
    ".dhsd": lint_dhsd,
    ".dhsf": lint_dhsf,
    ".dhpt": lint_dhpt,
    ".dhps": lint_dhps,
    ".dhsi": lint_dhsi,
    ".dhse": lint_dhse,
    ".sql": lint_sql,
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
    infos = [f for f in findings if f["severity"] == "info"]

    result = {
        "file": filepath,
        "type": ext,
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "summary": {
            "total": len(findings),
            "errors": len(errors),
            "warnings": len(warnings),
            "infos": len(infos),
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
