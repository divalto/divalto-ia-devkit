"""
build_report.py -- Assemble le rapport d'analyse pre-action.

Produit un markdown + un JSON de metriques a partir des 3 JSON intermediaires
(request, candidates_x12, evidence_x13).

Pipeline catalogue-driven :
- Evalue les types de contenus pertinents via `content_types.py`.
- Amorce le contenu de chaque type selectionne (`build_seeds`).
- Le template principal `report.md.j2` est minimal, il inclut les fragments des types retenus.
- Trace la selection dans `metrics.json` via `types_included`.

Encodage du livrable : UTF-8 + LF (livrable humain, pas source DIVA).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Vendor content_types (catalogue + scoring)
sys.path.insert(0, str(Path(__file__).parent))
from content_types import (  # noqa: E402
    ctx_from_json, evaluate_catalog, ReportContext,
)

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("Jinja2 non installe. Installer avec : py -m pip install jinja2", file=sys.stderr)
    sys.exit(3)

TEMPLATES_DIR = Path(__file__).parent / "templates"


# --- Constantes metier pour seeding type 7 ------------------------------

CE4_TABLE = [
    {"code": "1", "label": "active"},
    {"code": "2", "label": "suspendue"},
    {"code": "4", "label": "modele"},
    {"code": "7", "label": "provisoire"},
    {"code": "8", "label": "perimee"},
    {"code": "9", "label": "transferee"},
    {"code": "A", "label": "archivee"},
]


_LITERAL_SCAN = re.compile(
    r"(Ce4|TiCod|PiCod|AsCod)\s*[=<>!]+\s*['\"][\w\d]{1,3}['\"]",
    re.IGNORECASE,
)
_OVERWRITE_SCAN = re.compile(r"\b(Xmt_Call|OverWrittenBy)\b", re.IGNORECASE)

_DOSSIER_TRIGGERS = {"dossier", "parametrage", "onglet", "option", "parametre"}


# Pronoms relatifs qui, seuls en debut de proposition, produiraient un fragment de phrase
# (au lieu d'un enonce complet). Utilises pour rejeter les extractions fragmentaires.
_RELATIVE_PRONOUNS_START = re.compile(r"^\s*(?:qui|que|dont|ou)\b", re.IGNORECASE)

# Marqueur "<antecedent>, qui/que/dont <predicate> [alors qu'il ne faudrait pas]".
# On matche la partie apres la virgule : "qui/que/dont + predicate + fin".
# La fin est une alternative : exception detectee, fin de phrase, ou fin de chaine.
# La reptition non-greedy {0,15}? permet au predicat de s'arreter avant "alors qu'il..."
# pour que le groupe exception puisse matcher.
# L'antecedent est ensuite cherche en arriere (determinant + 1-3 mots avant la virgule).
_EXCEPTION_MARKER = re.compile(
    r",\s*(?P<pronom>qui|que|dont)\s+"
    r"(?P<predicate>\w+(?:\s+[\w\u00e0-\u00ff'\u2019\-]+){0,15}?)"
    r"(?:"
    r"(?P<exception>\s+alors\s+qu[\'\u2019]?il\s+ne\s+(?:faudrait|devrait)\s+pas)"
    r"|\s*[\.\?!]"
    r"|\s*$"
    r")",
    re.IGNORECASE,
)

# Antecedent = determinant + 1 a 3 substantifs, colle a la fin de la portion avant la virgule.
_ANTECEDENT_TAIL = re.compile(
    r"\b(?P<det>la|le|les|l[\'\u2019]|un|une|ce|cette|ces|mon|ma|mes|son|sa|ses)\s+"
    r"(?P<noun>[\w\u00e0-\u00ff'\u2019\-]+(?:\s+[\w\u00e0-\u00ff'\u2019\-]+){0,2})\s*$",
    re.IGNORECASE,
)

# Verbes irreguliers frequents (3e pers sing -> infinitif). La couverture n'est pas
# exhaustive : en cas d'echec, on utilise des heuristiques suffixales.
_VERBES_IRREGULIERS = {
    "est": "etre", "sont": "etre",
    "a": "avoir", "ont": "avoir",
    "fait": "faire", "font": "faire",
    "dit": "dire", "disent": "dire",
    "met": "mettre", "mettent": "mettre",
    "prend": "prendre", "prennent": "prendre",
    "peut": "pouvoir", "peuvent": "pouvoir",
    "doit": "devoir", "doivent": "devoir",
    "veut": "vouloir", "veulent": "vouloir",
    "sait": "savoir", "savent": "savoir",
    "voit": "voir", "voient": "voir",
    "vient": "venir", "viennent": "venir",
    "va": "aller", "vont": "aller",
}


def _verbe_to_infinitif(verb: str) -> str:
    """Convertit un verbe conjugue 3e pers (sing ou pluriel) vers son infinitif.

    Heuristique simple couvrant -er, -ir, -re reguliers + table d'irreguliers. Retourne
    le verbe inchange si aucune regle ne s'applique (degradation gracieuse pour ne jamais
    inserer un verbe visiblement casse dans le rapport).
    """
    v = verb.lower().strip()
    if not v:
        return verb
    if v in _VERBES_IRREGULIERS:
        return _VERBES_IRREGULIERS[v]
    # -er : "active" (3s) -> "activer", "activent" (3p) -> "activer"
    if v.endswith("ent") and len(v) >= 5:
        return v[:-3] + "er"
    if v.endswith("e") and len(v) >= 3 and not v.endswith("re"):
        return v + "r"
    # -ir : "finit" (3s) -> "finir", "finissent" (3p) -> "finir"
    if v.endswith("issent") and len(v) >= 7:
        return v[:-6] + "ir"
    if v.endswith("it") and len(v) >= 4:
        return v[:-1] + "r"
    # -re : "vend" (3s) -> "vendre"
    if v.endswith("d") and len(v) >= 4:
        return v + "re"
    return verb


def _reformuler_anomalie(request: dict) -> dict:
    """Extrait observe/attendu depuis le resume en produisant des phrases completes.

    Strategie (par ordre de priorite) :
    1. Pattern <antecedent>, qui/que/dont <predicate> [alors qu'il ne faudrait pas]
       -> observe = phrase complete "<antecedent> <predicate>" (sujet reconstruit)
       -> attendu = "<antecedent> ne doit pas <infinitif(verbe)> <reste>" si exception detectee
    2. Pattern "X au lieu de Y" -> observe = X, attendu = Y
    3. Fallback : premiere phrase du resume contenant un verbe d'action et ne commencant
       PAS par un pronom relatif (rejet strict des fragments type "qui active...").
    4. Echec : observe="", attendu="" (le template omet la section Observe/Attendu).

    INVARIANT : ne jamais retourner un observe commencant par un pronom relatif.
    Un tel fragment serait rattrape par le validator mais autant ne pas le produire.
    """
    resume = (request.get("resume") or "").strip()
    if not resume:
        return {"observe": "", "attendu": "", "fallback": True}

    # --- 1. Pattern antecedent + pronom relatif -------------------------------
    m = _EXCEPTION_MARKER.search(resume)
    if m:
        predicate = m.group("predicate").strip().rstrip(",.")
        exception_matched = bool(m.group("exception"))
        before = resume[: m.start()].rstrip()
        ant_match = _ANTECEDENT_TAIL.search(before)
        if ant_match:
            det = ant_match.group("det").strip()
            noun = ant_match.group("noun").strip()
            antecedent = f"{det} {noun}".strip()
            observe = f"{antecedent} {predicate}".strip()
            if observe:
                observe = observe[0].upper() + observe[1:]

            attendu = ""
            if exception_matched:
                vm = re.match(r"(\w+)(.*)", predicate)
                if vm:
                    verb = vm.group(1)
                    reste = vm.group(2).strip()
                    inf = _verbe_to_infinitif(verb)
                    if inf and inf != verb:
                        # Conjugaison connue : produire attendu factuel
                        attendu = f"{antecedent} ne doit pas {inf}"
                        if reste:
                            attendu += " " + reste
                    else:
                        # Verbe non conjugable surement : attendu generique factuel
                        attendu = f"Ce comportement ne doit pas se produire ({antecedent} concerne)."
                    if attendu:
                        attendu = attendu[0].upper() + attendu[1:]
            return {"observe": observe, "attendu": attendu, "fallback": False}

    # --- 2. Pattern "X au lieu de Y" ------------------------------------------
    m = re.search(r"([^.]{10,150}?)\s+au\s+lieu\s+de\s+([^.]{10,150})", resume, re.IGNORECASE)
    if m:
        return {
            "observe": m.group(1).strip(),
            "attendu": m.group(2).strip().rstrip(".,"),
            "fallback": False,
        }

    # --- 3. Fallback : phrase verbale complete --------------------------------
    phrases = [p.strip() for p in re.split(r"[.!?]\s+", resume) if p.strip()]
    for p in phrases:
        # INVARIANT : rejeter les fragments commencant par un pronom relatif
        if _RELATIVE_PRONOUNS_START.search(p):
            continue
        if len(p) >= 30 and re.search(
            r"\b(active|supprime|passe|modifie|remplace|transforme|bascule|cree|change|reste|arrive|apparait|disparait|bloque|plante)\b",
            p,
            re.IGNORECASE,
        ):
            return {"observe": p[:200], "attendu": "", "fallback": True}

    # --- 4. Echec : vide pour que le template omette --------------------------
    return {"observe": "", "attendu": "", "fallback": True}


# --- Nettoyage request brut ---------------------------------------------


_RESUME_NOISE_PATTERNS = [
    re.compile(r"\bBonjour\s*[,.]?\s*", re.IGNORECASE),
    re.compile(r"\bMerci\s*[.,]?\s*", re.IGNORECASE),
    re.compile(r"\bCordialement\s*[.,]?\s*", re.IGNORECASE),
    re.compile(r"\bVoir (?:leur|le|la) document\s+\w+\.?", re.IGNORECASE),
    re.compile(r"\bJ'ai\s+(?:reproduit|cree|teste|lance|verifie|essaye|fait)\s+[^.]{0,80}", re.IGNORECASE),
    re.compile(r"\bParametrage\s+de\s+(?:l['\u2019]|la\s+)", re.IGNORECASE),
    # Duplication titre ticket myService au debut du resume
    re.compile(r"^Ticket myService\s*-\s*", re.IGNORECASE),
    # --- Extensions P2 RETEX 2026-04-18 Session 2 ---
    # Noms de fichiers images attaches : image-YYYYMMDD-HHMMSS.png et variantes
    re.compile(r"\bimage[-_]\d{4,}[-_\d]*\.\w{2,5}\b", re.IGNORECASE),
    # Reference numero de dossier de test : "en 222e", "en 123e :"
    re.compile(r"\ben\s+\d{1,4}[a-z]*\s*:?", re.IGNORECASE),
    # Steps de reproduction ("je clique sur", "je valide", "je retourne sur"...)
    re.compile(r"\b[Jj]e\s+(?:clique|selectionne|valide|retourne|cree|teste|verifie|lance|ferme|ouvre|vais|coche|saisis|tape|rempli)\b[^.]{0,100}", re.IGNORECASE),
    re.compile(r"\b[Cc]lic(?:k)?\s+sur\b[^.]{0,50}", re.IGNORECASE),
    # Formules de politesse de fin
    re.compile(r"\b(?:Bonne\s+journee|A\s+bientot|En\s+vous\s+remerciant)\s*[.,]?\s*", re.IGNORECASE),
    re.compile(r"\b(?:Cdt|cdlt)\s*[.,]?\s*", re.IGNORECASE),
]

_KEYWORDS_STOPWORDS = {
    "bonjour", "merci", "cordialement", "document", "reproduit", "voir",
    "leur", "probleme", "active", "faudrait", "word",
    # --- Extensions P2 RETEX 2026-04-18 Session 2 ---
    # Formats de fichiers
    "image", "png", "jpg", "jpeg", "pdf", "docx", "xlsx",
    # Verbes d'action utilisateur (descriptions de reproduction, pas de signal metier)
    "clique", "selectionne", "valide", "retourne", "cree", "teste",
    "verifie", "lance", "essaye", "coche", "saisi", "saisis",
    "fait", "rempli", "tape",
    # Formules de politesse
    "bonne", "journee", "bientot", "cdt", "cdlt",
    # Mots-scories generiques
    "reproduction", "test", "tests", "truc", "chose",
    # Pronoms et articles qui peuvent remonter dans les keywords
    "cela", "ceci",
}


def _clean_resume(raw: str) -> str:
    """Supprime les boilerplates typiques (salutations, mentions de document joint).

    Le resume du parser est souvent un collage brut du ticket. Cette passe le normalise
    pour qu'un dev voie le signal (l'observation) sans le bruit (la politesse).
    """
    if not raw:
        return ""
    cleaned = raw
    for pat in _RESUME_NOISE_PATTERNS:
        cleaned = pat.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,.")
    return cleaned


def _filter_keywords(kws: list) -> list:
    """Retire les stop-words metier du parser (bonjour, document, reproduit, ...)."""
    return [k for k in kws if isinstance(k, str) and k.lower() not in _KEYWORDS_STOPWORDS]


# --- Slug (inchange) ----------------------------------------------------


def slugify(text: str, max_len: int = 40) -> str:
    """ASCII-lowercase avec tirets, 40 car max."""
    text = text.lower()
    replacements = {
        "e\u0301": "e", "e\u0300": "e", "e\u0302": "e",
        "a\u0300": "a", "a\u0302": "a",
        "i\u0302": "i", "i\u0308": "i",
        "o\u0302": "o", "u\u0302": "u",
        "\u00e9": "e", "\u00e8": "e", "\u00ea": "e", "\u00eb": "e",
        "\u00e0": "a", "\u00e2": "a",
        "\u00ee": "i", "\u00ef": "i",
        "\u00f4": "o", "\u00fc": "u", "\u00fb": "u", "\u00f9": "u",
        "\u00e7": "c",
    }
    for accented, plain in replacements.items():
        text = text.replace(accented, plain)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:max_len].rstrip("-") or "sans-titre"


# --- Seeding par type de contenu ----------------------------------------


def _rank_confirmed_by_relevance(confirmed: list[dict], request: dict) -> list[dict]:
    """Trie les confirmed par pertinence aux keywords (symbol match > block match > file match).

    Un confirmed avec `targeted_symbol` qui contient un keyword est prioritaire sur un confirmed
    sans symbole (snippet fallback middle-of-file). Essentiel pour que les symboles cles de la
    demande (ex: `Supprimer_LienContremarque` pour un ticket contremarque) ne soient pas tronques
    par `examples[:3]`.
    """
    kws_raw = (request.get("keywords_techniques") or []) + (request.get("keywords_metier") or [])
    kws = {k.lower() for k in kws_raw if isinstance(k, str) and len(k) >= 3}

    def score(c: dict) -> int:
        s = 0
        ts = (c.get("targeted_symbol") or "").lower()
        blk = (c.get("context_sample") or {}).get("enclosing_block") or {}
        blk_name = (blk.get("name") or "").lower()
        fp = (c.get("file_path") or "").lower()
        if ts:
            s += 10
            if any(kw in ts for kw in kws):
                s += 20
        if blk_name:
            s += 5
            if any(kw in blk_name for kw in kws):
                s += 10
        if any(kw in fp for kw in kws):
            s += 3
        return -s  # tri descendant via sorted ascending

    return sorted(confirmed, key=score)


def _seed_type_1(evidence: dict, request: dict) -> dict:
    """Exemples cibles : max 5 confirmed, prioritises par pertinence aux keywords.

    Enrichissement SVN (S-15, optionnel) : si evidence.confirmed[i].svn_log_recent
    est present (produit par verify_x13.py --svn-enrich), on ajoute svn_last_commit
    a l'example pour afficher la "fraicheur" du code.
    """
    ranked = _rank_confirmed_by_relevance(evidence.get("confirmed", []), request)
    examples = []
    for c in ranked[:5]:
        ctx = c.get("context_sample", {}) or {}
        example = {
            "name": c.get("from_x12", "?"),
            "file": c.get("file_path", ""),
            "line_range": c.get("line_range", [1, 1]),
            "enclosing": ctx.get("enclosing_block"),
            "snippet": ctx.get("snippet", ""),
            "status": c.get("status", "CONFIRME X.13"),
            "targeted_symbol": c.get("targeted_symbol"),
        }
        svn_log_recent = c.get("svn_log_recent") or []
        if svn_log_recent:
            last = svn_log_recent[0]
            msg = (last.get("message") or "").splitlines()
            example["svn_last_commit"] = {
                "revision": last.get("revision"),
                "author": last.get("author", ""),
                "date": (last.get("date", "") or "")[:10],
                "message_excerpt": (msg[0][:80] if msg else ""),
            }
        examples.append(example)
    return {
        "examples": examples,
        "disappeared": evidence.get("disappeared", []),
    }


def _seed_type_2(evidence: dict) -> dict:
    """Fonctions extraites des enclosing_block confirmed+new, dedup, filtre Int/main."""
    seen: set[str] = set()
    fns: list[dict] = []
    sources = list(evidence.get("confirmed", [])) + list(evidence.get("new_findings", []))
    for item in sources:
        blk = (item.get("context_sample") or {}).get("enclosing_block") or {}
        name = blk.get("name")
        if not name or name in seen or name.lower() in {"int", "main"}:
            continue
        seen.add(name)
        fns.append({
            "name": name,
            "usage_file": item.get("file_path", ""),
            "usage_line": blk.get("decl_line", 0),
        })
        if len(fns) >= 10:
            break
    return {"functions_seeded": fns}


def _seed_type_3(evidence: dict, candidates: dict) -> dict:
    """Etude d'impact : callers (evidence + fallback X.12) + propagation .dhsp only."""
    callers: list[dict] = []
    for c in evidence.get("impact", {}).get("callers", [])[:15]:
        callers.append({
            "file": c.get("file_path", ""),
            "line": c.get("line", 0),
            "callee": c.get("callee", ""),
            "status": c.get("status", "CONFIRME X.13"),
            "text_excerpt": c.get("text", ""),
        })
    # Fallback : si evidence.impact.callers est vide, recuperer depuis
    # candidates.relations.callers_of (advisory X.12). Le format est une liste de
    # {"caller": ..., "callee": ..., "status": ...}.
    if not callers:
        relations = candidates.get("relations") or {}
        for r in (relations.get("callers_of") or [])[:10]:
            callers.append({
                "file": "(advisory X.12, a confirmer en X.13)",
                "line": 0,
                "callee": r.get("callee", "?"),
                "status": "X.12 advisory",
                "text_excerpt": r.get("caller", "?"),
            })

    # Propagation : restreindre aux .dhsp (code executable). Les .dhsq (RecordSql declaratif)
    # contiennent des litteraux dans des CASE/WHEN de filtres, PAS des affectations. Les exclure
    # evite 90% des faux positifs observes dans les new_findings.
    prop: list[dict] = []
    for nf in evidence.get("new_findings", []):
        fp = nf.get("file_path", "")
        if not fp.lower().endswith(".dhsp"):
            continue
        snippet = (nf.get("context_sample") or {}).get("snippet", "")
        for line in snippet.split("\n"):
            # Skip lignes commentaires DIVA (;)
            if line.lstrip().startswith(";"):
                continue
            m = _LITERAL_SCAN.search(line)
            if m:
                prop.append({
                    "file": fp,
                    "line": nf.get("line_range", [0, 0])[0],
                    "pattern": m.group(0).strip(),
                })
                break  # 1 par new_finding
    return {"callers": callers, "propagation_sites": prop}


_ACTION_CONST_SCAN = re.compile(r"\bC_Action_\w+\b")


# S-15 -- Extraction des tickets Divalto dans les messages SVN des confirmed.
# Formats observes empiriquement sur l'historique SVN Divalto :
# - `US #NNNNN` (User Story Azure DevOps)
# - `\xa7DMS-NNNNN` (JIRA projet DMS, separateur section sign)
_TICKET_US = re.compile(r"\bUS\s*#(\d{3,7})\b", re.IGNORECASE)
_TICKET_DMS = re.compile("\xa7DMS-(\\d{3,7})")


def _extract_related_tickets_from_svn(evidence: dict, max_tickets: int = 5) -> list[dict]:
    """Extrait les tickets US/DMS des messages svn_log_recent des confirmed.

    Dedup sur (type, number), max `max_tickets`. Retourne liste vide si aucun confirme
    n'est enrichi SVN (le champ svn_log_recent est produit par verify_x13.py --svn-enrich).
    """
    seen: set = set()
    tickets: list[dict] = []
    for c in evidence.get("confirmed", []):
        log = c.get("svn_log_recent") or []
        if not log:
            continue
        file_label = Path(c.get("file_path", "")).name
        for entry in log:
            msg = entry.get("message") or ""
            rev = entry.get("revision", 0)
            for m in _TICKET_US.finditer(msg):
                key = ("US", m.group(1))
                if key not in seen:
                    seen.add(key)
                    tickets.append({"type": "US", "number": m.group(1), "file": file_label, "rev": rev})
            for m in _TICKET_DMS.finditer(msg):
                key = ("DMS", m.group(1))
                if key not in seen:
                    seen.add(key)
                    tickets.append({"type": "DMS", "number": m.group(1), "file": file_label, "rev": rev})
            if len(tickets) >= max_tickets:
                return tickets
    return tickets


def _pick_best_action(actions: set[str], request: dict) -> str | None:
    """Priorise l'action ERP la plus pertinente au ticket, pas par ordre alphabetique.

    Score = nb de tokens de l'action (split sur `_`) qui ont une intersection substring avec
    les mots-cles du ticket (keywords + message_erreur). En cas d'egalite, privilegie l'action
    la plus longue (plus specifique).

    Exemple : ticket contremarque suppression ->
    - `C_Action_Ctm_Lien_Suppr` : "lien" in "lien" (msg_erreur), "suppr" in "supprimer" => 2
    - `C_Action_Ctm_Fou_Mouv_Ajout` : "fou" in "fournisseur" => 1
    -> prioritise Lien_Suppr (correct).
    """
    if not actions:
        return None
    kws = {k.lower() for k in (request.get("keywords_techniques") or []) + (request.get("keywords_metier") or [])
           if isinstance(k, str) and len(k) >= 3}
    msg = (request.get("message_erreur") or "").lower()
    for w in re.findall(r"\b[a-z]{3,}\b", msg):
        kws.add(w)

    def score(action: str) -> tuple[int, int]:
        # Chaque token de l'action compte 1 point max (pas double si matche plusieurs kws)
        a_tokens = [t for t in action.lower().split("_") if len(t) >= 3]
        matches = sum(
            1
            for at in a_tokens
            if any(at in kw or kw in at for kw in kws)
        )
        return (matches, len(action))

    return max(actions, key=score)


def _seed_type_4(evidence: dict, request: dict) -> dict:
    """Endroit ou agir : 1-2 propositions amorcees avec hypothese factuelle.

    Prioritise les confirmed avec `targeted_symbol` (les non-cibles sont du fallback grossier).
    L'hypothese est derivee des litteraux et constantes d'action detectees dans le snippet --
    pas de stub "a preciser par le LLM" transmis au dev.
    """
    request_type = request.get("type", "unknown")
    confirmed = evidence.get("confirmed", [])

    # Ne retenir que les confirmed exploitables (prefere targeted_symbol, sinon enclosing_block)
    def has_anchor(c: dict) -> bool:
        if c.get("targeted_symbol"):
            return True
        blk = (c.get("context_sample") or {}).get("enclosing_block") or {}
        return bool(blk.get("name") and blk.get("name").lower() not in {"int", "main"})

    anchored = [c for c in confirmed if has_anchor(c)]
    # Trier par pertinence aux keywords (reuse tri type 1)
    anchored = _rank_confirmed_by_relevance(anchored, request)

    props: list[dict] = []
    for c in anchored[:2]:
        ctx = c.get("context_sample") or {}
        blk = ctx.get("enclosing_block") or {}
        snippet = ctx.get("snippet", "")
        symbol = c.get("targeted_symbol") or blk.get("name") or c.get("from_x12", "?")

        # Detection des signaux dans le snippet pour fabriquer une hypothese concrete
        literals = {m.group(0).strip() for m in _LITERAL_SCAN.finditer(snippet)}
        actions = set(_ACTION_CONST_SCAN.findall(snippet))

        if request_type == "ticket":
            action_kind = f"investiguer `{symbol}`"
            parts = []
            best_action = _pick_best_action(actions, request)
            if best_action:
                parts.append(
                    f"Le bloc declenche `{best_action}` (action ERP asynchrone). "
                    f"Les listeners de cette action sont candidats a examiner : un "
                    f"handler pourrait modifier l'etat observe sans garde conditionnelle."
                )
            if literals:
                sample = ", ".join(sorted(literals)[:3])
                parts.append(
                    f"Litteraux metier dans le snippet : {sample}. "
                    f"Rechercher les sites d'affectation (`<champ> = <valeur>`) dans la cascade."
                )
            if not parts:
                parts.append(
                    "Tracer les appels sortants (`Xmt_Call`, `A5_Action_*`, events Harmony) "
                    "pour identifier la site modifiant l'etat observe dans le ticket."
                )
            hypothese = " ".join(parts)
            next_step = (
                f"rg '\\b{best_action}\\b' X.13/"
                if best_action
                else f"rg '\\b{symbol}\\b' X.13/"
            )
        elif request_type == "feature":
            action_kind = f"reutiliser le pattern de `{symbol}` comme reference"
            hypothese = (
                f"Pattern confirme en X.13 dans `{symbol}`. Ouvrir ce fichier pour comprendre "
                "la structure existante (declarations, procedures, appels framework) puis decliner "
                "pour la nouvelle entite en preservant la nomenclature du domaine cible."
            )
            # Commande concrete pour explorer le pattern : grep des callers du symbole + ouverture
            # du fichier exemple. Pas de liste de UC : le skill gere ca dans une autre session.
            next_step = f"rg '\\b{symbol}\\b' X.13/  # voir qui consomme ce pattern"
        else:
            action_kind = f"clarifier puis analyser `{symbol}`"
            hypothese = "Type de demande non confirme -- clarification CP1 requise avant d'agir."
            next_step = "Re-parser la demande apres precision du collaborateur."

        # N6 : filtrer les enclosing_block "int" / "main" (main body du program, pas une
        # procedure pertinente). Laisser a None pour que le template n'affiche rien.
        enclosing_name = blk.get("name")
        if enclosing_name and enclosing_name.lower() in {"int", "main"}:
            enclosing_name = None

        props.append({
            "title": symbol,
            "file": c.get("file_path", ""),
            "line": blk.get("decl_line") or (c.get("line_range") or [1, 1])[0],
            "enclosing": enclosing_name,
            "action_kind": action_kind,
            "next_uc": next_step,
            "hypothese": hypothese,
        })
    result = {"propositions": props}
    # S-15 : tickets Divalto extraits des commits SVN des confirmed (si enrichissement actif)
    related_tickets = _extract_related_tickets_from_svn(evidence)
    if related_tickets:
        result["related_tickets"] = related_tickets
    return result


def _seed_type_5(request: dict, evidence: dict) -> dict:
    """Pistes complementaires : commandes pour combler les trous. Pas de redondance avec type 10.

    Type 5 = exploration supplementaire si signal insuffisant. Type 10 = validation de l'analyse.
    V3 : le new_finding propose doit :
    - etre un .dhsp (code executable)
    - etre dans le MEME repertoire qu'un confirmed (meme domaine)
    - ET avoir un nom de fichier proche d'un keyword (pas juste en voisinage)
    Sinon, clientswdhub.dhsp & co remontent (meme repertoire qu'un confirmed mais hors-scope).
    """
    hints: list[dict] = []
    confirmed = evidence.get("confirmed", [])
    confirmed_dirs = {str(Path(c.get("file_path", "")).parent).lower() for c in confirmed if c.get("file_path")}
    # Noms des fichiers confirmed (pour comparer par "voisinage lexicographique")
    confirmed_stems = {Path(c.get("file_path", "")).stem.lower()[:6] for c in confirmed if c.get("file_path")}
    kws = {k.lower() for k in request.get("keywords_metier", []) + request.get("keywords_techniques", [])
           if isinstance(k, str) and len(k) >= 4}
    nfs = evidence.get("new_findings", [])

    def _in_scope(nf: dict) -> bool:
        fp = nf.get("file_path", "")
        if not fp.lower().endswith(".dhsp"):
            return False
        parent = str(Path(fp).parent).lower()
        if parent not in confirmed_dirs:
            return False
        stem = Path(fp).stem.lower()
        # Rejeter si le nom ne partage aucun prefixe commun avec un confirmed (evite
        # clientswdhub.dhsp dont le stem 'client' n'est pas dans les confirmed 'gtpp*', 'gttc*'...)
        stem_prefix = stem[:6]
        if stem_prefix in confirmed_stems:
            return True
        # Ou le nom contient un keyword explicite de la demande
        if any(kw in stem for kw in kws):
            return True
        return False

    if len(nfs) > 10:
        in_scope = [
            nf for nf in nfs
            if _in_scope(nf)
            and ((nf.get("context_sample") or {}).get("enclosing_block") or {}).get("name")
        ]
        if in_scope:
            nf = in_scope[0]
            fp = nf.get("file_path", "")
            line = nf.get("line_range", [0])[0]
            blk = (nf.get("context_sample") or {}).get("enclosing_block") or {}
            blk_name = blk.get("name", "?")
            hints.append({
                "intent": f"Examiner le new_finding le plus informatif (`{blk_name}`)",
                "command": f'py .claude/skills/searching-erp-sources/scripts/extract_context.py --file "{fp}" --line {line}',
                "expected": f"contexte complet autour de `{blk_name}`",
            })
    if len(confirmed) < 3:
        hints.append({
            "intent": "Elargir la recherche hors du domaine pressenti",
            "command": ('py .claude/skills/searching-erp-sources/scripts/verify_x13.py '
                        '--candidates output/candidates_x12.json --request output/request.json '
                        '--erp-root <CHEMIN_ERP_STANDARD> --domain-scope all --max-files 50'),
            "expected": "candidats dans d'autres modules (Retail, Reglement, Comptabilite...)",
        })
    return {"hints": hints}


def _seed_type_6(evidence: dict) -> dict:
    """Points d'attention : surcharges detectees dans le code (pas dans les commentaires).

    V3 : scan ligne par ligne, skip les commentaires DIVA (;...) et les chaines. Pattern plus
    strict (`Xmt_Call\\s*\\(` ou `OverWrittenBy\\s+<ident>`) pour eviter les matches dans du
    texte libre (ex: un XML serialize dans un commentaire).
    """
    overs: list[dict] = []
    # Pattern strict : Xmt_Call( ou OverWrittenBy <nom> -- pas dans les commentaires.
    strict_scan = re.compile(
        r"(Xmt_Call\s*\(|\bOverWrittenBy\s+[A-Za-z_])",
        re.IGNORECASE,
    )
    # V3 : ne scanner QUE les confirmed (relies au domaine pertinent).
    # Les new_findings ramenent trop de faux positifs hors-scope (ex: clientswdhub).
    for item in evidence.get("confirmed", []):
        snippet = (item.get("context_sample") or {}).get("snippet", "")
        if not snippet:
            continue
        for line in snippet.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith(";"):
                continue  # commentaire DIVA
            m = strict_scan.search(line)
            if m:
                file_path = item.get("file_path", "")
                overs.append({
                    "file": Path(file_path).name if file_path else "?",
                    "pattern": m.group(0).strip(),
                    "context": f"`{stripped[:100]}`",
                })
                if len(overs) >= 5:
                    break
        if len(overs) >= 5:
            break
    return {"overwrites": overs}


_KNOWN_LITERAL_TABLES: dict[str, dict] = {
    "Ce4": {
        "name": "Ce4 (etat piece)",
        "canonical_source_doc": "../docs/ETATS-PIECE.md",
        "canonical_source_code": "Achat-Vente/source/Dav/dav_sd.dhsq:453",
        "table": CE4_TABLE,
        "note": "Pas de constantes nommees -- litteraux bruts dans 30+ sites.",
    },
}


def _seed_type_7(literals_detected: tuple[str, ...], request: dict | None = None) -> dict:
    """Constantes metier : ne livre que les patterns pour lesquels la table canonique est connue.

    V3 : pour les patterns detectes mais sans table documentee (TiCod, PiCod, AsCod...), OMETTRE
    plutot que livrer une ligne vide "a documenter". Un placeholder transmis au dev = bruit.
    Quand un pattern est detecte mais omis, on ajoute une note de backlog dans `omitted_patterns`.

    V4 (RETEX Session 3) : si la request mentionne des libelles d'etat metier specifiques
    (ex: "preparation", "valide en facture", "facture en avoir"), enrichir la note du Ce4 avec
    une proposition de correspondance pour donner un point de depart au dev.
    """
    lits: list[dict] = []
    omitted: list[str] = []
    for name in literals_detected:
        if name in _KNOWN_LITERAL_TABLES:
            # Copier pour ne pas muter le dict canonique
            entry = dict(_KNOWN_LITERAL_TABLES[name])
            if name == "Ce4" and request:
                correspondance = _detect_etat_correspondance(request)
                if correspondance:
                    entry["note"] = (
                        f"Correspondance US detectee : {correspondance}. "
                        "**A verifier** sur le domaine cible -- les libelles Ce4 peuvent differer "
                        "selon la famille de piece."
                    )
            lits.append(entry)
        else:
            omitted.append(name)
    return {"literals": lits, "omitted_patterns": omitted}


def _detect_etat_correspondance(request: dict) -> str:
    """Detecte les libelles d'etat metier dans la request et propose une correspondance Ce4.

    Ex: keyword/ca mentionne "preparation" -> suggere Ce4='7' (provisoire).
    Retourne une chaine descriptive ou "" si aucune correspondance claire.
    """
    text = " ".join([
        request.get("resume", ""),
        " ".join(request.get("keywords_metier", [])),
        " ".join(request.get("ca_detectes", [])),
    ]).lower()
    correspondances = []
    if "preparation" in text or "provisoire" in text:
        correspondances.append("*en preparation* / *provisoire* -> Ce4='7'")
    if ("facture" in text and ("valide" in text or "active" in text)) or "valide en facture" in text:
        correspondances.append("*valide en facture* / *active* -> Ce4='1'")
    if "avoir" in text:
        correspondances.append("*facture en avoir* -> Ce4='A' (archivee) ou valeur specifique metier [A VERIFIER]")
    if "suspendu" in text:
        correspondances.append("*suspendue* -> Ce4='2'")
    return " ; ".join(correspondances)


def _seed_type_8(ctx: ReportContext) -> dict:
    """Parametrage dossier : trigger detectes + piste grep ciblee sur GTFDD.dhsd.

    V3 : retirer les noms inventes (CtmFl, CtmMode), grep sur GTFDD.dhsd (dictionnaire dossier)
    plutot que sur tous les .dhsp de Dav. Utiliser les keywords techniques comme racine de probe.
    """
    triggers = sorted((set(ctx.keywords_metier) | set(ctx.keywords_techniques)) & _DOSSIER_TRIGGERS)
    # Extraire une probe courte d'un keyword technique pour le grep
    probe_kws = [k for k in ctx.keywords_techniques if len(k) >= 4]
    probe = probe_kws[0].lower()[:4] if probe_kws else "ctm"
    grep_hint = (
        f'rg -ni "{probe}" '
        '"<ERP>/Fichier/gtfdd.dhsd"'
    )
    return {"triggers_hit": triggers, "grep_hint": grep_hint}


def _seed_type_10(request: dict, evidence: dict) -> dict:
    """Verification prealable : commandes CIBLEES (pas de rg global qui ramene 2000 matches).

    V3 :
    - Piste 1 : grep du symbole cible (plus specifique que le keyword)
    - Piste 2 : grep des constantes `C_Action_*` detectees dans les snippets (plus utile que
      grep du keyword)
    - Piste 3 : pointeur dossier (si parametrage detecte) -> dictionnaire `gtfdd.dhsd`
    """
    verifs: list[dict] = []
    confirmed = evidence.get("confirmed", [])

    # Piste 1 : grep du symbole cible (word boundary pour eviter les matches partiels)
    # V10 : eviter les symboles trop generiques (ex: `ActionERP_Contremarque` ramenera 200+ matches).
    # Prioriser les symboles plus specifiques (nom long).
    sym_candidates = sorted(
        (c.get("targeted_symbol") for c in confirmed if c.get("targeted_symbol")),
        key=len,
        reverse=True,
    )
    # Filtrer : exclure les symboles trop courts (< 15 chars) qui ramenent trop de bruit
    sym_specific = [s for s in sym_candidates if s and len(s) >= 15]
    chosen_sym = sym_specific[0] if sym_specific else (sym_candidates[0] if sym_candidates else None)
    if chosen_sym:
        verifs.append({
            "intent": f"Confirmer la cascade d'appels autour de `{chosen_sym}`",
            "command": f'rg -n "\\b{chosen_sym}\\b" "C:/Developpements harmony/Standard/Version X.13"',
            "expected": "appelants directs du symbole (1-20 matches typiquement)",
        })

    # Piste 2 : constantes C_Action_* detectees dans les snippets (VRAI signal du ticket)
    actions_found: set[str] = set()
    for c in confirmed:
        snippet = (c.get("context_sample") or {}).get("snippet", "")
        actions_found.update(_ACTION_CONST_SCAN.findall(snippet))
    best_action = _pick_best_action(actions_found, request)
    if best_action:
        verifs.append({
            "intent": f"Identifier les listeners de `{best_action}` (action ERP detectee dans le snippet)",
            "command": f'rg -n "\\b{best_action}\\b" "C:/Developpements harmony/Standard/Version X.13"',
            "expected": "site qui consomme l'action (listener candidat pour la cause racine)",
        })

    # Piste 3 : dictionnaire dossier si parametrage detecte
    kw_set = {k.lower() for k in request.get("keywords_metier", []) + request.get("keywords_techniques", []) if isinstance(k, str)}
    if kw_set & {"dossier", "parametrage", "onglet", "option", "parametre"}:
        kws_tech = [k for k in request.get("keywords_techniques", []) if isinstance(k, str)][:1]
        probe = kws_tech[0].lower()[:4] if kws_tech else "ctm"
        verifs.append({
            "intent": "Localiser les champs dossier lies au parametrage mentionne",
            "command": f'rg -ni "{probe}" "C:/Developpements harmony/Standard/Version X.13/Fichier/gtfdd.dhsd"',
            "expected": "champs dossier candidats (ex: CtmActif, CtmMode, ...) dans le dictionnaire",
        })

    if not verifs:
        verifs.append({
            "intent": "Requete Cypher pour elargir la recherche",
            "command": 'MATCH (n) WHERE (n:Program OR n:DObj OR n:Procedure) AND toLower(n.name) CONTAINS "<keyword>" RETURN n LIMIT 25',
            "expected": "candidats advisory X.12 complementaires",
        })
    return {"verifications": verifs[:3]}


def _build_chain_of_blame(request: dict, candidates: dict, evidence: dict) -> dict:
    """Construit la chaine d'appels UI -> caller -> callee -> action -> listener inconnu.

    Pour un ticket d'anomalie, cette chaine est la donnee principale : elle montre le flux
    d'execution du bouton clique jusqu'au point ou le bug se produit probablement.

    Source :
    - Niveau 0 : `request.message_erreur` (libelle du bouton UI du ticket)
    - Niveau 1-2 : `candidates.relations.callers_of[0]` (caller + callee, advisory X.12)
    - Niveau 3 : pattern `A5_Action_Generer_Action(C_Action_*, ...)` dans le snippet du callee
    - Niveau 4 : gap explicite "LISTENER INCONNU -- chercher qui consomme C_Action_*"

    Retourne {available: bool, nodes: list, action_const: str or None}.
    """
    ui_label = (request.get("message_erreur") or "").strip()
    relations = candidates.get("relations") or {}
    callers_of = relations.get("callers_of") or []
    if not callers_of:
        return {"available": False, "nodes": [], "action_const": None}

    first = callers_of[0]
    caller_name = first.get("caller", "?")
    callee_name = first.get("callee", "?")

    # Localiser caller et callee dans candidates.functions
    functions = candidates.get("functions") or []
    loc_map: dict[str, tuple[str, int | str]] = {}
    for f in functions:
        name_lower = (f.get("name") or "").lower()
        prog = f.get("program") or "?"
        line = f.get("line", "?")
        if name_lower:
            loc_map[name_lower] = (prog, line)

    def pretty_name(raw: str) -> str:
        """Retourne la forme canonique (CamelCase) du symbole depuis evidence.

        Cherche dans 3 sources :
        1) targeted_symbol exact match
        2) enclosing_block.name exact match
        3) Grep du nom dans les snippets (retourne la forme trouvee)
        Fallback : Title_Case a partir du snake_case lowercase.
        """
        raw_lower = raw.lower()
        for c in evidence.get("confirmed", []):
            ts = c.get("targeted_symbol") or ""
            if ts.lower() == raw_lower:
                return ts
            blk = (c.get("context_sample") or {}).get("enclosing_block") or {}
            name = blk.get("name") or ""
            if name.lower() == raw_lower:
                return name
        # 3) Chercher dans les snippets (forme cannonique peut apparaitre dans un appel)
        for c in evidence.get("confirmed", []):
            snippet = (c.get("context_sample") or {}).get("snippet", "")
            # Cherche un mot avec la bonne sequence de lettres, ignore-casse
            m = re.search(re.escape(raw_lower), snippet, re.IGNORECASE)
            if m:
                return snippet[m.start():m.end()]
        # Fallback : si raw est lowercase_snake, convertir en CamelCase_Snake
        if "_" in raw and raw == raw.lower():
            return "_".join(part.capitalize() if part else "" for part in raw.split("_"))
        return raw

    caller_pretty = pretty_name(caller_name)
    callee_pretty = pretty_name(callee_name)
    caller_loc = loc_map.get(caller_name.lower())
    callee_loc = loc_map.get(callee_name.lower())

    def _needs_line(loc: tuple | None) -> bool:
        """Retourne True si la loc n'a pas de ligne exploitable (None, '?', 0)."""
        if not loc:
            return True
        _, line = loc
        return line in (None, "?", 0, "0")

    def _find_in_evidence(name_lower: str, prefer_prog: str | None = None,
                           avoid_prog: str | None = None) -> tuple[str, int] | None:
        """Cherche un symbole (case-insensitive) dans les snippets confirmed X.13.

        Retourne (program_stem, line) si trouve, sinon None.

        prefer_prog : prioriser la recherche dans ce programme.
        avoid_prog : exclure ce programme (typiquement le caller, pour eviter de trouver le
                     site d'appel plutot que la declaration).
        """
        candidates_list = list(evidence.get("confirmed", []))
        if avoid_prog:
            candidates_list = [
                c for c in candidates_list
                if Path(c.get("file_path", "")).stem.lower() != avoid_prog.lower()
            ]
        if prefer_prog:
            candidates_list.sort(
                key=lambda c: (Path(c.get("file_path", "")).stem.lower() != prefer_prog.lower())
            )
        # 1re passe : match exact sur targeted_symbol ou enclosing_block.name
        for c in candidates_list:
            ts = (c.get("targeted_symbol") or "").lower()
            blk = (c.get("context_sample") or {}).get("enclosing_block") or {}
            blk_name = (blk.get("name") or "").lower()
            fp = c.get("file_path", "")
            prog = Path(fp).stem if fp else None
            if not prog:
                continue
            if blk_name == name_lower or ts == name_lower:
                line = blk.get("decl_line") or (c.get("line_range") or [0])[0]
                return (prog, line)
        # 2e passe : chercher une DECLARATION du symbole (Procedure|Function <name>)
        # dans les snippets. Plus fiable qu'un grep generique.
        decl_pat = re.compile(
            rf"\b(?:Public\s+)?(?:Procedure|Function(?:\s+\w+)?)\s+{re.escape(name_lower)}\b",
            re.IGNORECASE,
        )
        for c in candidates_list:
            fp = c.get("file_path", "")
            prog = Path(fp).stem if fp else None
            if not prog:
                continue
            snippet = (c.get("context_sample") or {}).get("snippet", "")
            m = decl_pat.search(snippet)
            if m:
                snippet_start = (c.get("context_sample") or {}).get("snippet_start", 1)
                line_no_in_snippet = snippet[:m.start()].count("\n")
                return (prog, snippet_start + line_no_in_snippet)
        # 3e passe : grep litteral dans snippet (site d'appel possible, moins fiable)
        for c in candidates_list:
            fp = c.get("file_path", "")
            prog = Path(fp).stem if fp else None
            if not prog:
                continue
            snippet = (c.get("context_sample") or {}).get("snippet", "")
            if name_lower in snippet.lower():
                snippet_start = (c.get("context_sample") or {}).get("snippet_start", 1)
                for i, line in enumerate(snippet.split("\n")):
                    if name_lower in line.lower():
                        return (prog, snippet_start + i)
        return None

    # Completer caller_loc si la ligne manque (priorite au programme du caller)
    caller_prog_hint = caller_loc[0] if caller_loc else None
    if _needs_line(caller_loc):
        found = _find_in_evidence(caller_name.lower(), prefer_prog=caller_prog_hint)
        if found:
            caller_loc = found
    # Idem pour callee_loc (priorite au programme du callee, EVITER le programme du caller)
    callee_prog_hint = callee_loc[0] if callee_loc else None
    if not callee_prog_hint:
        # Heuristique : callee commencant par "actionerp_" est dans un fichier gttm*
        cn_low = callee_name.lower()
        if cn_low.startswith("actionerp_"):
            for p in candidates.get("programs", []):
                pname = (p.get("name") or "").lower()
                if pname.startswith("gttm"):
                    callee_prog_hint = p.get("name")
                    break
    if _needs_line(callee_loc):
        # Chercher le nom dans les snippets en EVITANT le programme du caller (c'est la ou le
        # callee est *appele*, pas declare). Preferer le prog hint deduit ci-dessus.
        excluded = caller_prog_hint if caller_prog_hint != callee_prog_hint else None
        found = _find_in_evidence(callee_name.lower(),
                                   prefer_prog=callee_prog_hint,
                                   avoid_prog=excluded)
        if found:
            callee_loc = found
        elif callee_prog_hint and not callee_loc:
            # On sait le programme mais pas la ligne -- acceptable
            callee_loc = (callee_prog_hint, None)

    # Detecter l'action ERP dans le snippet du confirmed correspondant au callee
    # (ex: A5_Action_Generer_Action(C_Action_Ctm_Lien_Suppr, ...))
    # IMPORTANT : on ne publie file:line que si on a extrait l'action depuis le snippet
    # exact du callee. Sinon, on reporte uniquement la constante d'action (pas de ligne)
    # pour eviter de lier une ligne a un symbole qui ne la contient pas.
    action_const = None
    action_file = None
    action_line = None
    action_in_callee_snippet = False  # flag : action trouvee dans le snippet du callee ?
    action_pat = re.compile(
        r"A5_Action_Generer_Action\s*\([^)]*?(C_Action_\w+)",
        re.IGNORECASE | re.DOTALL,
    )
    callee_prog = callee_loc[0] if callee_loc else None

    def _snippet_contains_symbol(c: dict, sym_lower: str) -> bool:
        """Verifie que le snippet du confirmed contient la declaration du symbole callee."""
        if not sym_lower:
            return False
        ts = (c.get("targeted_symbol") or "").lower()
        if ts == sym_lower:
            return True
        blk = (c.get("context_sample") or {}).get("enclosing_block") or {}
        if (blk.get("name") or "").lower() == sym_lower:
            return True
        # Fallback : presence du nom en majuscules DIVA dans le snippet
        snippet = (c.get("context_sample") or {}).get("snippet", "")
        decl_pat = re.compile(
            rf"\b(?:Public\s+)?(?:Procedure|Function(?:\s+\w+)?)\s+{re.escape(sym_lower)}\b",
            re.IGNORECASE,
        )
        return bool(decl_pat.search(snippet))

    callee_lower = callee_name.lower() if callee_name else ""
    for c in evidence.get("confirmed", []):
        # Chercher uniquement dans le confirmed qui contient EFFECTIVEMENT le callee
        if not _snippet_contains_symbol(c, callee_lower):
            continue
        snippet = (c.get("context_sample") or {}).get("snippet", "")
        m = action_pat.search(snippet)
        if m:
            action_const = m.group(1)
            snippet_start = (c.get("context_sample") or {}).get("snippet_start", 1)
            for i, line in enumerate(snippet.split("\n")):
                if action_const in line:
                    action_line = snippet_start + i
                    break
            action_file = c.get("file_path")
            action_in_callee_snippet = True
            break

    # Fallback : action trouvee dans N'IMPORTE quel confirmed (pas forcement le callee).
    # Dans ce cas, on recupere la constante mais PAS de file:line (evite fausse attribution).
    if action_const is None:
        for c in evidence.get("confirmed", []):
            snippet = (c.get("context_sample") or {}).get("snippet", "")
            m = action_pat.search(snippet)
            if m:
                action_const = m.group(1)
                # Pas de file/line : l'action n'est pas dans le snippet du callee
                action_file = None
                action_line = None
                action_in_callee_snippet = False
                break

    # Construire les noeuds
    nodes = []
    if ui_label:
        nodes.append({"kind": "ui", "label": ui_label})
    if caller_loc:
        nodes.append({
            "kind": "fn",
            "name": caller_pretty,
            "file": f"{caller_loc[0]}.dhsp",
            "line": caller_loc[1],
        })
    # Toujours afficher le callee, meme si line inconnue (noeud conceptuel important)
    if callee_name:
        if callee_loc and callee_loc[1] and callee_loc[1] not in ("?", 0, "0"):
            nodes.append({
                "kind": "fn",
                "name": callee_pretty,
                "file": f"{callee_loc[0]}.dhsp",
                "line": callee_loc[1],
            })
        elif callee_loc and callee_loc[0]:
            # Fichier connu mais ligne non trouvee : afficher sans ligne
            nodes.append({
                "kind": "fn_noline",
                "name": callee_pretty,
                "file": f"{callee_loc[0]}.dhsp",
            })
        elif callee_prog:
            nodes.append({
                "kind": "fn_noline",
                "name": callee_pretty,
                "file": f"{callee_prog}.dhsp",
            })
    if action_const:
        # N'afficher file:line que si l'action a ete trouvee dans le snippet du callee
        # (sinon c'est une fausse attribution -- cf. RETEX analyse de reception).
        action_node = {
            "kind": "action",
            "name": f"A5_Action_Generer_Action({action_const}, ...)",
            "const": action_const,
        }
        if action_in_callee_snippet and action_file and action_line:
            action_node["file"] = Path(action_file).name
            action_node["line"] = action_line
        else:
            # On sait qu'il y a un appel a l'action quelque part, mais pas exactement ou
            # dans la procedure callee. Le dev devra chercher dans le callee.
            action_node["file"] = None
            action_node["line"] = None
            action_node["note_emplacement"] = (
                "emplacement exact dans le callee a identifier (le pipeline a detecte la "
                "constante mais hors du snippet extrait)"
            )
        nodes.append(action_node)
        nodes.append({
            "kind": "gap",
            "label": f"LISTENER INCONNU -- chercher qui consomme `{action_const}`",
        })

    return {
        "available": len(nodes) >= 2,
        "nodes": nodes,
        "action_const": action_const,
    }


def build_seeds(ctx: ReportContext, request: dict, candidates: dict, evidence: dict) -> dict:
    """Construit tous les seeds necessaires aux fragments Jinja + le TL;DR global.

    Tous les types sont seedes meme s'ils sont omis : le script reste deterministe,
    c'est la selection dans le template qui decide de l'inclusion.
    """
    seeds = {
        "type_1": _seed_type_1(evidence, request),
        "type_2": _seed_type_2(evidence),
        "type_3": _seed_type_3(evidence, candidates),
        "type_4": _seed_type_4(evidence, request),
        "type_5": _seed_type_5(request, evidence),
        "type_6": _seed_type_6(evidence),
        "type_7": _seed_type_7(ctx.literals_detected, request),
        "type_8": _seed_type_8(ctx),
        "type_10": _seed_type_10(request, evidence),
    }
    seeds["chain_of_blame"] = _build_chain_of_blame(request, candidates, evidence)
    seeds["ca_mapping"] = _build_ca_mapping(request, candidates, evidence)
    return seeds


_STOP_WORDS_CA = {
    "le", "la", "les", "un", "une", "des", "de", "du", "en", "a", "au",
    "et", "ou", "pas", "ne", "que", "qui", "sur", "dans", "pour", "par",
    "si", "sinon", "lorsque", "d", "l", "ca", "n", "est", "sont",
}

# Synonymes metier francais -> tokens techniques DIVA (pour matching CA -> fonctions).
# Inverse d'un dictionnaire d'abreviations : ici "visualiser" -> "consulter" car les
# fonctions DIVA utilisent "consulter" (ex: tunnel_situation_consulter).
_CA_SYNONYMS = {
    "visualiser": {"consulter", "afficher", "voir"},
    "ajouter": {"creer", "insertion", "ajouter", "add"},
    "supprimer": {"supprimer", "suppression", "delete", "suppr"},
    "valider": {"valider", "validation", "validate", "ok"},
    "liberer": {"liberer", "supprlien", "detacher", "dissocier"},
    "enregistrer": {"enregistrer", "writeent", "save", "insertion"},
    "controler": {"controler", "controle", "verifier", "check"},
    "parametrage": {"parametrage", "dossier", "gtfdd", "setting"},
    "autoliquidation": {"autoliquidation", "autoliq", "tva", "regimetva"},
    "indicateur": {"indicateur", "flag", "coche", "checkbox"},
    "selectionner": {"selectionner", "selection", "liste", "enliste"},
}


def _ca_keywords(ca_text: str) -> set[str]:
    """Extrait les tokens significatifs d'un CA (apres filtrage stop-words + synonymes)."""
    import re as _re
    tokens = _re.findall(r"[A-Za-z]{3,}", ca_text.lower())
    base = {t for t in tokens if t not in _STOP_WORDS_CA}
    # Elargir avec synonymes : si le CA mentionne "visualiser", on autorise aussi "consulter".
    expanded = set(base)
    for t in list(base):
        if t in _CA_SYNONYMS:
            expanded.update(_CA_SYNONYMS[t])
    return expanded


def _build_ca_mapping(request: dict, candidates: dict, evidence: dict) -> dict:
    """Associe chaque CA (feature) ou anomalie (ticket) detecte a la fonction la plus pertinente.

    Strategie : pour chaque item, tokenise le texte, cherche la fonction confirmee X.13 ou
    candidate X.12 dont le nom a le plus de tokens en commun. Retourne uniquement les items
    avec un match non trivial (>= 1 token metier commun).

    V4 (RETEX Session 4) : extension aux tickets multi-anomalies. Un ticket type "feedback client
    avec N bugs listes" beneficie du meme mapping qu'une feature multi-CA -- l'item_label change
    (CA -> A pour anomalie, formulation "item_type" dans le fragment).
    """
    req_type = request.get("type")
    if req_type not in ("feature", "ticket"):
        return {"entries": [], "item_type": None}
    cas = request.get("ca_detectes", [])
    if not cas:
        return {"entries": [], "item_type": None}

    # Construire le catalogue des fonctions disponibles : confirmes X.13 (prio) + candidates X.12
    candidates_fns: list[dict] = []
    for c in evidence.get("confirmed", []):
        blk = (c.get("context_sample") or {}).get("enclosing_block") or {}
        name = blk.get("name")
        if not name or name.lower() in {"int", "main"}:
            continue
        candidates_fns.append({
            "name": name,
            "file": c.get("file_path", ""),
            "line": blk.get("decl_line") or (c.get("line_range") or [1, 1])[0],
            "tier": "x13",
        })
    # Map program name -> X.13 path (derivee de X.12 en remplacant la version).
    # Chemin X.12 typique : /mnt/c/Developpements harmony/Standard/Version X.12/Achat-Vente/source/Dav/gtppdtr020.dhsp
    prog_x13_paths: dict[str, str] = {}
    for p in candidates.get("programs", []):
        pname = (p.get("name") or "").lower()
        ppath = p.get("path") or ""
        if not pname or not ppath:
            continue
        # Normaliser : /mnt/c/... -> C:/... et X.12 -> X.13
        x13 = ppath.replace("/mnt/c/", "C:/").replace("Version X.12", "Version X.13")
        prog_x13_paths[pname] = x13

    for f in candidates.get("functions", [])[:15]:
        fname = f.get("name")
        if not fname:
            continue
        # Resoudre le fichier depuis caller_program si dispo
        prog = (f.get("program") or "").lower()
        file_abs = prog_x13_paths.get(prog, "")
        candidates_fns.append({
            "name": fname,
            "file": file_abs,
            "line": "?",
            "tier": "x12",
        })

    def tokenize_fname(name: str) -> set[str]:
        """Decompose un nom snake_case ou CamelCase en tokens lowercase."""
        import re as _re
        parts = _re.split(r"[_\s]+|(?<=[a-z])(?=[A-Z])", name)
        return {p.lower() for p in parts if len(p) >= 3}

    entries: list[dict] = []
    # Prefix de l'id : CA pour feature, A (anomalie) pour ticket.
    default_prefix = "CA" if req_type == "feature" else "A"
    for i, ca_text in enumerate(cas, 1):
        # Extraire l'id (ex: "CA1:" -> "CA1", "A1:" -> "A1")
        ca_id = f"{default_prefix}{i}"
        import re as _re
        m = _re.match(r"\s*([AC]A?\d+|A\d+)\s*[:\-]", ca_text)
        if m:
            ca_id = m.group(1)
        ca_toks = _ca_keywords(ca_text)

        # Scorer chaque fonction par overlap de tokens
        best = None
        best_score = 0
        for fn in candidates_fns:
            fn_toks = tokenize_fname(fn["name"])
            overlap = ca_toks & fn_toks
            if len(overlap) > best_score:
                best_score = len(overlap)
                best = (fn, overlap)

        if best and best_score >= 1:
            fn, overlap = best
            file_short = fn["file"].replace("\\", "/").split("/")[-1] if fn["file"] else "?"
            file_uri = _file_uri(fn["file"]) if fn["file"] else ""
            why = "match tokens: " + ", ".join(sorted(overlap))
            entries.append({
                "ca_id": ca_id,
                "function": fn["name"],
                "file_short": file_short,
                "file_uri": file_uri,
                "line": fn["line"],
                "why": why,
                "tier": fn["tier"],
            })

    item_type = "CA" if req_type == "feature" else "Anomalie"
    return {"entries": entries, "item_type": item_type}


def _file_uri(abs_path: str) -> str:
    """Convertit un chemin absolu Windows en URI file:// URL-encoded.

    Ex: C:/Developpements harmony/.../gttmaction.dhsp
      -> file:///C:/Developpements%20harmony/.../gttmaction.dhsp
    """
    if not abs_path:
        return ""
    from urllib.parse import quote
    norm = abs_path.replace("\\", "/")
    # Windows absolute path -> file:/// prefix
    if len(norm) >= 2 and norm[1] == ":":
        return "file:///" + quote(norm, safe="/:")
    return "file://" + quote(norm, safe="/")


def _strip_erp_root(seeds: dict, erp_root: str) -> None:
    """Remplace les chemins absolus par des chemins relatifs a erp_root dans tous les seeds.

    Modifie `seeds` en place. Les chemins hors erp_root sont laisses tels quels.
    Ajoute aussi `file_uri` (URI file://) pour les liens cliquables Claude Desktop.
    """
    if not erp_root:
        return
    erp_norm = erp_root.replace("\\", "/").rstrip("/")
    erp_norm_lower = erp_norm.lower()

    def shorten(path: str) -> str:
        if not path:
            return path
        norm = path.replace("\\", "/")
        if norm.lower().startswith(erp_norm_lower):
            return norm[len(erp_norm):].lstrip("/")
        return path

    def abs_from_relative(rel: str) -> str:
        """Reconstruit le chemin absolu depuis le chemin relatif a erp_root."""
        if not rel:
            return ""
        if rel.startswith(erp_norm) or (len(rel) >= 2 and rel[1] == ":"):
            return rel  # deja absolu
        return f"{erp_norm}/{rel.lstrip('/')}"

    # Type 1 : examples -- shorten + file_uri pour liens cliquables
    for ex in seeds["type_1"]["examples"]:
        orig = ex["file"]
        ex["file"] = shorten(orig)
        ex["file_uri"] = _file_uri(abs_from_relative(orig))
    # Type 2 : fonctions_seeded (usage_file)
    for fn in seeds["type_2"]["functions_seeded"]:
        orig = fn["usage_file"]
        fn["usage_file"] = shorten(orig)
        fn["file_uri"] = _file_uri(abs_from_relative(orig))
    # Type 3 : callers + propagation
    for c in seeds["type_3"]["callers"]:
        orig = c["file"]
        c["file"] = shorten(orig)
        c["file_uri"] = _file_uri(abs_from_relative(orig)) if orig and "(advisory" not in orig else ""
    for p in seeds["type_3"]["propagation_sites"]:
        orig = p["file"]
        p["file"] = shorten(orig)
        p["file_uri"] = _file_uri(abs_from_relative(orig))
    # Type 4 : propositions
    for p in seeds["type_4"]["propositions"]:
        orig = p["file"]
        p["file"] = shorten(orig)
        p["file_uri"] = _file_uri(abs_from_relative(orig))
    # Type 5 : hints (cmd peut contenir un path)
    for h in seeds["type_5"]["hints"]:
        h["command"] = h["command"].replace(erp_norm, "<ERP>").replace(erp_norm.replace("/", "\\"), "<ERP>")
    # Type 10 : verifications (cmd)
    for v in seeds["type_10"]["verifications"]:
        v["command"] = v["command"].replace(erp_norm, "<ERP>").replace(erp_norm.replace("/", "\\"), "<ERP>")
    # Chain of blame : les noeuds ont un file en nom court (ex: gttmaction.dhsp).
    # Reconstruire un chemin absolu en cherchant dans les confirmed du meme stem.
    if seeds["chain_of_blame"].get("available"):
        # Map stem -> abs_path depuis seeds.type_1 (qui contient les confirmed)
        stem_to_abs: dict[str, str] = {}
        for ex in seeds["type_1"]["examples"]:
            rel = ex.get("file", "")
            if rel:
                stem = Path(rel).stem.lower()
                # Reconstruire l'abs depuis le relatif (shorten a deja passe)
                abs_full = f"{erp_norm}/{rel.lstrip('/')}"
                stem_to_abs[stem] = abs_full

        for node in seeds["chain_of_blame"]["nodes"]:
            file_name = node.get("file") or ""
            if file_name:
                stem = Path(file_name).stem.lower()
                abs_full = stem_to_abs.get(stem)
                node["file_uri"] = _file_uri(abs_full) if abs_full else ""


# --- Metriques ----------------------------------------------------------


def compute_metrics(
    request: dict,
    candidates: dict,
    evidence: dict,
    selection: list[dict],
) -> dict:
    """Calcule les metriques du rapport + liste `types_included` (CA10)."""
    confirmed = evidence.get("confirmed", [])
    disappeared = evidence.get("disappeared", [])
    new_findings = evidence.get("new_findings", [])
    callers = evidence.get("impact", {}).get("callers", [])

    fonctions_uniques: set[str] = set()
    for c in confirmed + new_findings:
        blk = (c.get("context_sample") or {}).get("enclosing_block") or {}
        name = blk.get("name")
        if name and name.lower() not in {"int", "main"}:
            fonctions_uniques.add(name)

    nb_confirmed = len(confirmed)
    nb_fonctions = len(fonctions_uniques)
    if nb_confirmed >= 3 and nb_fonctions >= 5:
        confiance = "forte"
    elif nb_confirmed >= 1:
        confiance = "moyenne"
    else:
        confiance = "faible"

    upstream = (evidence.get("scope") or {}).get("neo4j_status_upstream", "ok")
    couverture = {
        "ok": "disponible",
        "partial": "partielle",
        "unavailable": "absente",
    }.get(upstream, "disponible")

    total_findings = nb_confirmed + len(new_findings)
    signal_ratio = nb_confirmed / total_findings if total_findings > 0 else 0.0

    return {
        "exemples_cibles": nb_confirmed,
        "new_findings_bruts": len(new_findings),
        "fonctions_extraites": nb_fonctions,
        "appelants_potentiels": len(callers),
        "disclaimers_x12": len(candidates.get("disclaimers", [])),
        "confirmed_x13": nb_confirmed,
        "disappeared_x13": len(disappeared),
        "new_x13": len(new_findings),
        "signal_ratio": round(signal_ratio, 3),
        "confiance_globale": confiance,
        "couverture_neo4j": couverture,
        "types_included": selection,
    }


# --- Preparation du contexte du template --------------------------------


def prepare_context(
    request: dict,
    candidates: dict,
    evidence: dict,
    date_str: str,
    metrics_json_path: str = "",
    erp_root: str = "",
) -> dict:
    ctx = ctx_from_json(request, candidates, evidence)
    # Nettoyer le resume brut du ticket (stop-words typiques + troncature naturelle)
    cleaned_request = dict(request)
    cleaned_request["resume"] = _clean_resume(request.get("resume", ""))
    cleaned_request["keywords_metier"] = _filter_keywords(request.get("keywords_metier", []))
    selection = evaluate_catalog(ctx)
    seeds = build_seeds(ctx, cleaned_request, candidates, evidence)
    _strip_erp_root(seeds, erp_root)
    metrics = compute_metrics(cleaned_request, candidates, evidence, selection)

    types_selected = [r for r in selection if r["included"]]
    types_omitted = [r for r in selection if not r["included"]]

    # Version condensee pour le rapport markdown (sans types_included, redondant avec la
    # table d'audit affichee juste au-dessus et avec le .json parallele).
    metrics_condensed = {k: v for k, v in metrics.items() if k != "types_included"}

    # Reformulation observe/attendu (pour Anomalie section)
    anomalie_reformulee = _reformuler_anomalie(cleaned_request)

    return {
        "date_iso": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "date_short": date_str,
        "request": cleaned_request,
        "candidates": candidates,
        "evidence": evidence,
        "seeds": seeds,
        "types_selected": types_selected,
        "types_selected_full": selection,
        "types_included_ids": [f"T{r['id']}" for r in types_selected],
        "types_omitted_ids": [f"T{r['id']}" for r in types_omitted],
        "disappeared": evidence.get("disappeared", []),
        "metrics": metrics,
        "metrics_condensed": metrics_condensed,
        "metrics_json_path": metrics_json_path,
        "anomalie_reformulee": anomalie_reformulee,
    }


# --- Render --------------------------------------------------------------


def render(context: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    tpl = env.get_template("report.md.j2")
    return tpl.render(**context)


# --- Validator de livraison ---------------------------------------------

# Patterns qui ne doivent JAMAIS apparaitre dans un rapport livre au dev.
# Ces patterns indiquent un stub d'enrichissement LLM non resolu -- le rapport doit etre
# publishable-as-is (lisible et actionnable sans post-process LLM). Un rapport qui contient
# l'un de ces patterns est une regression : signaler plutot que livrer silencieusement.
_FORBIDDEN_PATTERNS = [
    # "LLM (CP5) : ..." eventuellement precede par _ ou espaces
    (re.compile(r"LLM\s*\(CP\d+\)\s*:", re.IGNORECASE), "directive LLM residuelle"),
    # "a preciser par le LLM", "a completer par le LLM", etc.
    (re.compile(r"a?\s*(?:preciser|completer|definir|rediger|enrichir)\s+par\s+le\s+LLM", re.IGNORECASE), "placeholder d'enrichissement LLM"),
    # "[a definir]", "[a preciser]"
    (re.compile(r"\[a\s+(?:definir|preciser|completer)\]", re.IGNORECASE), "placeholder a remplir"),
    # TODO LLM explicite
    (re.compile(r"\bTODO\s+LLM\b", re.IGNORECASE), "TODO LLM residuel"),
    # "A completer par le LLM au CP5" et variantes (sans "par")
    (re.compile(r"A\s+completer\s+(?:au\s+)?CP\d+", re.IGNORECASE), "action CP residuelle"),
    # --- RETEX 2026-04-18 Session 2 ---
    # Fragment de phrase commencant par un pronom relatif lowercase apres un label de bullet
    # Ex: "- **Observe** : qui active..." -> fragment sans sujet, inacceptable
    (re.compile(r"^\s*-\s*\*\*[\w\s]+\*\*\s*:\s*(?:qui|que|qu['\u2019]|dont|ou|ni)[\s,]", re.MULTILINE), "fragment de phrase (pronom relatif apres label)"),
    # Italique contenant un placeholder en angle brackets (casse le rendu Markdown)
    # Ex: "_Attendu : ... <champ> = '<valeur>' ..._" -> les _ s'affichent en dur
    (re.compile(r"_[^_\n]*<[a-z][a-z0-9_-]*>[^_\n]*_"), "italique avec placeholder HTML-like (risque de casser le rendu)"),
    # Stub de placeholder inutile : "(cf. ticket d'origine)", "(voir original)", etc.
    (re.compile(r"\(\s*cf\.?\s+ticket\s+d['\u2019]?origine\s*\)", re.IGNORECASE), "stub inutile '(cf. ticket d'origine)'"),
    # Stubs generiques non-LLM
    (re.compile(r"\b(?:a\s+completer)\b", re.IGNORECASE), "placeholder 'a completer'"),
    (re.compile(r"\b(?:FIXME|XXX)\b"), "marqueur TODO/FIXME/XXX residuel"),
    # TODO seul (hors TODO LLM deja detecte)
    (re.compile(r"\bTODO\b(?!\s+LLM)", re.IGNORECASE), "TODO residuel"),
    # Balises HTML non supportees par le renderer Mermaid de Claude Desktop
    # <br/> est OK, <details>/<summary> sont des blocs MD valides, mais <code>/<em>/<span>/<strong>
    # dans un noeud Mermaid s'affichent en dur
    (re.compile(r"<(?:code|em|span|strong)\b[^>]*>"), "balise HTML non rendue (Mermaid/MD fragile)"),
]


def validate_report(markdown: str) -> list[str]:
    """Verifie qu'un rapport est publishable-as-is : zero directive LLM / placeholder.

    Retourne la liste des violations trouvees (vide = rapport valide).
    """
    violations: list[str] = []
    for pattern, label in _FORBIDDEN_PATTERNS:
        for m in pattern.finditer(markdown):
            line_no = markdown[:m.start()].count("\n") + 1
            excerpt = markdown[max(0, m.start() - 20):m.end() + 30].replace("\n", " ")
            violations.append(f"ligne {line_no} : {label} -- ...{excerpt}...")
    return violations


# --- Pre-flight des JSON d'entree ---------------------------------------

def preflight_check(request: dict, candidates: dict, evidence: dict) -> tuple[list[str], list[str]]:
    """Verifie que les 3 JSON d'entree sont exploitables AVANT de construire le rapport.

    Retourne (errors, warnings). Si errors non vide, le pipeline doit s'arreter :
    regenerer les JSON en amont (re-parser, re-querier, re-verifier) avant de relancer.
    Les warnings sont des signaux de qualite degradee mais pas bloquants.

    Regles :
    - ERROR request.type absent ou 'unknown' -> parse_request a rate
    - ERROR request.resume vide -> rien a traiter
    - WARN request.domaine_pressenti absent -> candidates par keyword seulement
    - WARN request.keywords_techniques < 2 -> couverture candidats reduite
    - ERROR candidates vides ET evidence vide -> pipeline aveugle
    - WARN candidates.functions vides ET type=ticket -> chain_of_blame degradee
    - WARN evidence.confirmed[] sans targeted_symbol -> snippets random attendus
    - ERROR evidence.confirmed[] contient enclosing_block=None partout -> pattern verify_x13 --symbols manque
    """
    errors: list[str] = []
    warnings: list[str] = []

    # --- request.json ---
    req_type = (request.get("type") or "").lower()
    if not req_type or req_type == "unknown":
        errors.append("request.type absent ou 'unknown' -- parse_request a probablement rate, re-parser le ticket.")
    if not (request.get("resume") or "").strip():
        errors.append("request.resume vide -- rien a analyser. Verifier l'input du parser.")
    if not request.get("domaine_pressenti"):
        warnings.append("request.domaine_pressenti absent -- les candidats seront moins cibles.")
    kws = request.get("keywords_techniques") or []
    if len(kws) < 2:
        warnings.append(f"request.keywords_techniques faible ({len(kws)} items) -- enrichir au CP1.")

    # --- candidates_x12.json ---
    fns = candidates.get("functions") or []
    progs = candidates.get("programs") or []
    rels = (candidates.get("relations") or {}).get("callers_of") or []
    neo4j_status = candidates.get("neo4j_status")
    if not (fns or progs or rels) and neo4j_status != "unavailable":
        errors.append(
            "candidates_x12 vide alors que Neo4j est disponible -- probablement un bug de Cypher/keywords. "
            "Verifier les requetes generees avant de continuer."
        )
    if req_type == "ticket" and not fns:
        warnings.append(
            "candidates.functions vide pour un ticket -- la chaine d'appels sera degradee, "
            "verifier qu'un symbole metier precis a ete remonte par Neo4j."
        )
    if req_type == "feature" and not fns and not rels:
        # N8 (RETEX Session 3 2026-04-18) : pour une feature, functions + relations vides
        # = rapport "plat" sans pistes nommees. Mieux vaut bloquer que livrer un rapport sans signal.
        errors.append(
            "feature sans fonctions ni relations -- candidats trop generiques (programs seuls). "
            "Enrichir les keywords_techniques CP1 ou elargir callers_of avant de continuer."
        )

    # --- evidence_x13.json ---
    confirmed = evidence.get("confirmed") or []
    new_findings = evidence.get("new_findings") or []
    if not (confirmed or new_findings):
        errors.append(
            "evidence_x13 vide (ni confirmed ni new_findings) -- relancer verify_x13.py "
            "avec --domain-scope all ou elargir les keywords."
        )
    targeted = [c for c in confirmed if c.get("targeted_symbol")]
    if confirmed and not targeted:
        warnings.append(
            "evidence.confirmed present mais aucun avec targeted_symbol -- snippets risquent "
            "d'etre hors-sujet. Passer --symbols a verify_x13.py pour cibler."
        )
    if confirmed:
        enclosings = [
            (c.get("context_sample") or {}).get("enclosing_block")
            for c in confirmed
        ]
        if enclosings and not any(enclosings):
            warnings.append(
                "evidence.confirmed : aucun enclosing_block resolu. L'amorcage des "
                "propositions (section 'Endroit ou agir') sera faible."
            )

    return errors, warnings


# --- CLI -----------------------------------------------------------------


def _cli() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description="Construit le rapport d'analyse pre-action (catalogue-driven).")
    ap.add_argument("--request", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--output-dir", default="output")
    ap.add_argument("--slug")
    ap.add_argument("--date")
    ap.add_argument("--erp-root", default="C:/Developpements harmony/Standard/Version X.13",
                    help="Racine ERP pour rendre les chemins relatifs dans le rapport.")
    args = ap.parse_args()

    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))

    # Pre-flight : refuser de construire un rapport sur des JSON degrades.
    # Permet au collaborateur de voir les problemes AVANT de passer 30s a generer
    # un rapport qui aurait de toute facon ete rejete par la grille de qualite.
    pf_errors, pf_warnings = preflight_check(request, candidates, evidence)
    if pf_errors:
        print("ERREUR : inputs JSON degrades, impossible de construire un rapport exploitable :", file=sys.stderr)
        for e in pf_errors:
            print(f"  - {e}", file=sys.stderr)
        if pf_warnings:
            print("\nAvertissements supplementaires :", file=sys.stderr)
            for w in pf_warnings:
                print(f"  ! {w}", file=sys.stderr)
        print("\nRegenerer les JSON en amont (phases 1-3) avant de relancer.", file=sys.stderr)
        return 3
    if pf_warnings:
        print("Pre-flight avertissements (rapport genere mais qualite potentiellement degradee) :", file=sys.stderr)
        for w in pf_warnings:
            print(f"  ! {w}", file=sys.stderr)

    slug = args.slug or slugify(request.get("titre", request.get("resume", "sans-titre"))[:60])
    date_str = args.date or datetime.now().strftime("%Y%m%d")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / f"preaction-{slug}-{date_str}.md"
    json_path = out_dir / f"preaction-{slug}-{date_str}.json"

    context = prepare_context(request, candidates, evidence, date_str,
                               metrics_json_path=str(json_path),
                               erp_root=args.erp_root)
    rendered = render(context)

    # Validator "publishable-as-is" : refuser tout rapport qui contient des directives LLM
    # residuelles. Le rapport doit etre lisible et actionnable sans post-process LLM.
    violations = validate_report(rendered)
    if violations:
        print("ERREUR : rapport non publishable (stubs LLM detectes) :", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print("Corriger les templates fragments correspondants.", file=sys.stderr)
        return 4

    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(rendered)

    # --- Metriques qualite post-render ---------------
    # `report_size_lines` : objectif 1-2 pages (100-200L). Au-dela, risque "noie le dev".
    # `preflight_warnings` : nombre de warns du pre-flight (qualite amont degradee).
    report_size_lines = len(rendered.splitlines())
    context["metrics"]["report_size_lines"] = report_size_lines
    context["metrics"]["preflight_warnings"] = len(pf_warnings)

    metrics_out = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "slug": slug,
        "request_type": request.get("type"),
        "domaine": request.get("domaine_pressenti"),
        "metrics": context["metrics"],
        "confiance_globale": context["metrics"]["confiance_globale"],
        "couverture_neo4j": context["metrics"]["couverture_neo4j"],
    }
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(metrics_out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    result = {
        "markdown_path": str(md_path),
        "metrics_path": str(json_path),
        "types_included": [r["id"] for r in context["types_selected"]],
        "types_omitted": [r["id"] for r in context["types_selected_full"] if not r["included"]],
        "metrics": context["metrics"],
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
