"""
parse_request.py -- Parse une user story ou un ticket myService en JSON canonique.

Entree : texte libre (stdin ou fichier UTF-8).
Sortie : JSON stdout conforme a scripts/templates/request.schema.json.

Deterministe : regex + heuristiques uniquement. Si le signal est insuffisant, le flag
`needs_clarification: true` est leve -- le LLM orchestrateur decide quoi faire.

Couche "parse" du pipeline d'analyse pre-action (parse / query / verify).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --- Patterns de detection du type ---------------------------------------

FEATURE_PATTERNS = [
    r'\bEn tant que\b',
    r'\bJe veux\b',
    r'\bAfin de\b',
    r'\bEtant donn[eé]\b',
    r'\bQuand\b.+\bAlors\b',
    r'\bCrit[eè]res? d\'acceptation\b',
    r'\bUser story\b',
]

TICKET_PATTERNS = [
    r'\banomalie\b',
    r'\bbug\b',
    r'\berreur\b',
    r'\bplante\b',
    r'\bcass[eé]\b',
    r'\bne fonctionne pas\b',
    r'\bticket\s+myService\b',
    r'\bJIRA\b',
    r'^\s*at\s+\w+\.\w+',  # stack trace Java-like
]

# --- Domaines ERP (aligne sur docs/MODULES-ERP.md) -----------------------

DOMAINS = [
    ("GT_", "Achat-Vente / Dav", ["gestion commerciale", "facture", "client", "article",
                                   "commande", "vente", "achat", "devis", "livraison"]),
    ("RT_", "Retail", ["retail", "caisse", "ticket", "point de vente", "magasin"]),
    ("GG_", "Prod / Atelier", ["production", "atelier", "fabrication", "nomenclature",
                                "gamme", "of", "ordre de fabrication"]),
    ("CC_", "Comptabilite", ["compta", "comptabilit", "ecriture", "journal", "bilan",
                              "tva", "grand livre"]),
    ("RC_", "Reglement", ["reglement", "banque", "paiement", "relance", "echeance"]),
    ("PP_", "Paie", ["paie", "salaire", "bulletin", "cotisation", "employe"]),
    ("GA_", "Affaires", ["affaire", "chantier", "analytique"]),
    ("QU_", "Qualite", ["qualite", "controle qualite", "non-conformite", "ncf"]),
    ("GR_", "Relation-Tiers", ["crm", "contact", "prospect", "tiers"]),
    ("GM_", "GRM", ["grm", "ressources materiel", "parc materiel"]),
    ("PV_", "Point de vente", ["point de vente"]),
    ("A5", "Framework A5", ["framework", "menu", "dossier", "utilisateur", "securite",
                             "a5f", "mz.dos"]),
]

# --- Patterns techniques -------------------------------------------------

PASCALCASE_PAT = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b')
UPPERCASE_PAT = re.compile(r'\b([A-Z]{3,})\b')
FILENAME_PAT = re.compile(r'\b([a-z][a-z0-9_]*\.(?:dhsp|dhsq|dhsd|dhsf|dhpt|dhps|dhfi|dhoq|dhop))\b',
                          re.IGNORECASE)
FUNCTION_CALL_PAT = re.compile(r'\b([A-Z][A-Za-z0-9_]*)\s*\(')

# Stop-words metier (ne pas inclure dans keywords_metier)
STOP_METIER = {
    "dans", "pour", "avec", "cette", "celui", "celle", "entre", "apres", "avant",
    "parce", "ainsi", "donc", "mais", "quand", "alors", "tant", "veux", "afin",
    "etant", "qu'il", "qu'elle", "lors", "dont", "sans", "toute", "tout", "meme",
    "noter", "voir", "faire", "mettre", "avoir", "etre", "autre", "plus",
    "moins", "peut", "doit", "peuvent", "doivent", "encore", "deja", "bien",
    "actuel", "actuelle", "nouvelle", "nouveau", "propre", "sera", "serait",
}

# --- Abreviations Divalto (catalogue reference/abreviations-divalto.md) ----

_ABREV_PATH = Path(__file__).parent.parent / "reference" / "abreviations-divalto.md"
_ABREV_ROW_PAT = re.compile(r'^\|\s*([a-z0-9]{2,6})\s*\|\s*([^|]+?)\s*\|', re.IGNORECASE)


def load_abreviations() -> dict[str, str]:
    """Charge le mapping abreviation -> forme complete depuis le catalogue .md.

    Le catalogue est une table Markdown au format `| abr | forme complete | contexte |`.
    La ligne d'en-tete et le separateur `|---|---|---|` sont ignores.
    """
    if not _ABREV_PATH.exists():
        return {}
    mapping: dict[str, str] = {}
    for line in _ABREV_PATH.read_text(encoding="utf-8").splitlines():
        m = _ABREV_ROW_PAT.match(line)
        if not m:
            continue
        abrv = m.group(1).strip().lower()
        full = m.group(2).strip().lower()
        if abrv.startswith("-") or abrv in ("abreviation",):
            continue
        if full.startswith("-") or full.startswith("forme"):
            continue
        if abrv and full and abrv != full and "|" not in full:
            mapping[abrv] = full
    return mapping


ABREVIATIONS: dict[str, str] = load_abreviations()


def expand_abreviations(text: str, existing_metier: list[str],
                        abbrev_map: dict[str, str]) -> list[str]:
    """Enrichit keywords_metier avec les abreviations et leurs formes completes.

    Pour chaque (abr, full) du catalogue : si abr OU full apparait dans le texte
    (mot entier), ajoute les deux formes dans la liste. Permet a Neo4j de matcher
    un program nomme avec l'abreviation courte (gtppctm310) meme quand le redacteur
    ecrit la forme longue ("contremarque"), et inversement.
    """
    if not abbrev_map:
        return list(existing_metier)
    result = list(existing_metier)
    seen = set(result)
    text_lower = text.lower()
    for abrv, full in abbrev_map.items():
        has_abrv = re.search(rf'\b{re.escape(abrv)}\b', text_lower) is not None
        has_full = re.search(rf'\b{re.escape(full)}\b', text_lower) is not None
        if has_abrv or has_full:
            if abrv not in seen:
                result.append(abrv)
                seen.add(abrv)
            if full not in seen:
                result.append(full)
                seen.add(full)
    return result


# --- Fonctions d'extraction ----------------------------------------------


def detect_type(text: str, forced: str) -> str:
    if forced in ("feature", "ticket"):
        return forced
    feature_score = sum(1 for p in FEATURE_PATTERNS
                        if re.search(p, text, re.IGNORECASE | re.MULTILINE))
    ticket_score = sum(1 for p in TICKET_PATTERNS
                       if re.search(p, text, re.IGNORECASE | re.MULTILINE))
    if ticket_score > feature_score:
        return "ticket"
    if feature_score > 0:
        return "feature"
    return "unknown"


def extract_acteurs(text: str) -> list[str]:
    acteurs = []
    for m in re.finditer(r'En tant que\s+([^,.\n]+)', text, re.IGNORECASE):
        acteurs.append(m.group(1).strip().rstrip(":"))
    return acteurs


def extract_donnees(text: str) -> list[str]:
    donnees: set[str] = set()
    for m in PASCALCASE_PAT.finditer(text):
        donnees.add(m.group(1))
    for m in UPPERCASE_PAT.finditer(text):
        tok = m.group(1)
        # Ignorer les mots francais en majuscules (OK, CAS, etc.) -- heuristique : >= 3 et non-commun
        if tok not in {"CAS", "OK", "KO", "DIVA", "ERP", "JIRA", "API", "SQL", "XML", "JSON",
                        "HTTP", "REST", "URL", "UTF", "ISO", "LLM", "MCP"}:
            donnees.add(tok)
    return sorted(donnees)


def extract_domaine(text: str) -> str | None:
    text_lower = text.lower()
    # 1. Prefixe explicite mentionne
    for prefix, _, _ in DOMAINS:
        if re.search(rf'\b{re.escape(prefix)}', text):
            return prefix
    # 2. Nom de module ou mots-cles declencheurs
    best = None
    best_score = 0
    for prefix, module, keywords in DOMAINS:
        score = 0
        if module.lower() in text_lower:
            score += 3
        for kw in keywords:
            if re.search(rf'\b{re.escape(kw)}\b', text_lower):
                score += 1
        if score > best_score:
            best_score = score
            best = prefix
    return best if best_score >= 1 else None


def extract_keywords(text: str) -> dict:
    tech: set[str] = set()
    for m in FILENAME_PAT.finditer(text):
        tech.add(m.group(1).lower())
    for m in PASCALCASE_PAT.finditer(text):
        tech.add(m.group(1))
    for m in FUNCTION_CALL_PAT.finditer(text):
        tech.add(m.group(1))

    # Metier : substantifs 5+ lettres, dedup, top 15 par ordre d'apparition
    raw = re.findall(r'\b[a-zA-ZéèêàâîïôûùçÉÈÊÀÂÎÏÔÛÙÇ]{5,}\b', text.lower())
    metier_ordered = []
    seen = set()
    for w in raw:
        if w not in STOP_METIER and w not in seen:
            seen.add(w)
            metier_ordered.append(w)
        if len(metier_ordered) >= 15:
            break
    metier_ordered = expand_abreviations(text, metier_ordered, ABREVIATIONS)
    return {"techniques": sorted(tech), "metier": metier_ordered}


def extract_ca(text: str) -> list[str]:
    """Cherche une section "Criteres d'acceptation" ou "CA" avec bullets."""
    # Pattern 1 : section dediee suivie de bullets
    section_pat = re.compile(
        r'(?:Crit[eè]res? d\'acceptation|Acceptance criteria|\bCA\s*:)\s*:?\s*\n'
        r'((?:\s*(?:[-*\u2022]|\d+\.)\s+[^\n]+\n?)+)',
        re.IGNORECASE,
    )
    m = section_pat.search(text)
    if m:
        bullet_pat = re.compile(r'^\s*(?:[-*\u2022]|\d+\.)\s+([^\n]+)', re.MULTILINE)
        return [b.strip() for b in bullet_pat.findall(m.group(1))]

    # Pattern 2 : "CA1 :" / "CA2 :"
    ca_items = re.findall(r'\bCA\s*\d+\s*:\s*([^\n]+)', text, re.IGNORECASE)
    if ca_items:
        return [c.strip() for c in ca_items]

    # Pattern 3 : ligne isolee commencant par "- " precedee d'un mot-cle BDD
    return []


def extract_error(text: str) -> str | None:
    # Message entre quotes de >= 10 caracteres
    for pat in (r'"([^"]{10,})"', r"'([^']{10,})'"):
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    # Ligne "erreur: XXX"
    m = re.search(r'\b(?:erreur|error)\s*:?\s*([^\n]{5,})', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip(".")
    return None


def build_title(text: str, max_len: int = 80) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line and len(line) >= 5:
            return line[:max_len]
    return "Demande sans titre"


def build_resume(text: str, max_sentences: int = 3, max_len: int = 400) -> str:
    clean = re.sub(r'\s+', ' ', text.strip())
    parts = re.split(r'(?<=[.!?])\s+', clean)
    joined = " ".join(parts[:max_sentences])
    return joined[:max_len]


# --- Entree principale ---------------------------------------------------


def parse(text: str, forced_type: str = "auto") -> dict:
    type_ = detect_type(text, forced_type)
    acteurs = extract_acteurs(text)
    donnees = extract_donnees(text)
    domaine = extract_domaine(text)
    keywords = extract_keywords(text)
    ca = extract_ca(text) if type_ == "feature" else []
    err = extract_error(text) if type_ == "ticket" else None

    needs_clar = (
        type_ == "unknown"
        or (type_ == "feature" and not acteurs and not ca)
        or (type_ == "ticket" and err is None)
    )

    return {
        "type": type_,
        "titre": build_title(text),
        "resume": build_resume(text),
        "acteurs": acteurs,
        "donnees": donnees,
        "domaine_pressenti": domaine,
        "keywords_techniques": keywords["techniques"],
        "keywords_metier": keywords["metier"],
        "ca_detectes": ca,
        "message_erreur": err,
        "needs_clarification": needs_clar,
    }


def _cli() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description="Parse une user story ou un ticket myService en JSON canonique.")
    ap.add_argument("--input", help="Chemin fichier texte (UTF-8). Sinon lit stdin.")
    ap.add_argument("--type", choices=["auto", "feature", "ticket"], default="auto")
    args = ap.parse_args()

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    if not text.strip():
        print(json.dumps({"error": "input_empty"}), file=sys.stderr)
        return 2

    out = parse(text, args.type)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
