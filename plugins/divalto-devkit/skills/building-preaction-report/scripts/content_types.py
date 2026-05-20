"""
content_types.py -- Catalogue des types de contenus du rapport pre-action.

Le rapport n'est pas un template fixe de 7 sections systematiquement remplies. Il est la
concatenation des types de contenus **pertinents** pour la demande analysee. Chaque type
a un score de pertinence deterministe, calcule depuis `request.json` + `candidates_x12.json`
+ `evidence_x13.json`. Un type est inclus ssi son score depasse son seuil (`threshold`).

Extensibilite : ajouter un nouveau type = ajouter une dataclass dans CATALOG + un template
Jinja dans `templates/fragments/`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class ReportContext:
    """Donnees consolidees pour calculer les scores de pertinence d'un type de contenu.

    Construit par `build_report.py` depuis les 3 JSON d'entree (request, candidates, evidence).
    """
    request_type: str  # 'feature' | 'ticket' | 'unknown'
    confirmed_x13: int
    new_findings: int
    disappeared_x13: int
    callers: int = 0
    literals_detected: tuple[str, ...] = ()       # ex: ('Ce4', 'TiCod')
    overwrites_detected: int = 0                   # surcharges Xmt_Call/OverWrittenBy
    keywords_metier: tuple[str, ...] = ()          # lowercase, pour detection type 8
    keywords_techniques: tuple[str, ...] = ()      # lowercase


@dataclass(frozen=True)
class ContentType:
    """Declaration d'un type de contenu candidat a l'inclusion dans le rapport.

    Le catalogue global `CATALOG` est une liste ordonnee (l'ordre determine l'ordre des
    sections dans le rapport final).
    """
    id: int
    slug: str
    title: str
    score_fn: Callable[[ReportContext], float]
    template: str                         # nom du fragment Jinja dans templates/fragments/
    default_section_level: int = 2        # niveau '## ' par defaut
    tags: tuple[str, ...] = ()            # categorisation libre (feature, ticket, meta, ...)
    threshold: float = 0.5                # score >= threshold => inclus

    def evaluate(self, ctx: ReportContext) -> tuple[float, bool]:
        """Retourne (score, inclus)."""
        score = self.score_fn(ctx)
        return score, score >= self.threshold


# --- Fonctions de score par type -----------------------------------------


def score_type_1_exemples(ctx: ReportContext) -> float:
    """Type 1 -- Exemples de code DIVA similaires.

    Regle : score = min(1.0, confirmed_x13 / 3). 3 confirmes = 1.0, 1 confirme = 0.33.
    Seuil defaut 0.5 -> inclus si >= 2 confirmed. Si 1 confirmed (score 0.33 < 0.5), type
    omis pour eviter un exemple isole. Le collaborateur peut surcharger via CP4.
    """
    return min(1.0, ctx.confirmed_x13 / 3.0)


def score_type_4_endroit_agir(ctx: ReportContext) -> float:
    """Type 4 -- Endroit ou agir (propositions).

    Regle : score = 1.0 si >= 1 confirmed (il y a quelque chose a proposer), sinon 0.0.
    Pas de proposition sans ancrage X.13 -- c'est la valeur principale pour un ticket,
    et le point d'entree pour une feature (meme si la conclusion est souvent UC-001).
    """
    return 1.0 if ctx.confirmed_x13 >= 1 else 0.0


def score_type_5_pistes(ctx: ReportContext) -> float:
    """Type 5 -- Pistes de recherche complementaires.

    Regle : score = 1.0 si signal insuffisant (< 50% des findings sont confirmes), 0.3 sinon.
    Le signal_ratio mesure la proportion de matiere confirmee (pas du hasard du grep).
    Seuil par defaut 0.6 (plus exigeant) -> inclus uniquement quand il manque de matiere.
    """
    total = ctx.confirmed_x13 + ctx.new_findings
    if total == 0:
        return 1.0  # vraiment rien trouve -> pistes obligatoires
    signal_ratio = ctx.confirmed_x13 / total
    return 1.0 if signal_ratio < 0.5 else 0.3


def score_type_2_fonctions_langage(ctx: ReportContext) -> float:
    """Type 2 -- Fonctions du langage DIVA potentiellement utiles.

    Regle : 0.8 si feature (nouveau code -> connaissance langage utile), 0.2 si ticket
    (anomalie sur code existant -> dev suppose connaitre). Seuil defaut 0.5.
    """
    return 0.8 if ctx.request_type == "feature" else 0.2


def score_type_3_etude_impact(ctx: ReportContext) -> float:
    """Type 3 -- Etude d'impact (appelants, propagation).

    Regle : 1.0 si callers > 0 OU (confirmed >= 1 ET new_findings > 3, suggerant propagation).
    Sinon 0.3. Seuil defaut 0.5.
    """
    if ctx.callers > 0:
        return 1.0
    if ctx.confirmed_x13 >= 1 and ctx.new_findings > 3:
        return 1.0
    return 0.3


def score_type_6_attention(ctx: ReportContext) -> float:
    """Type 6 -- Points d'attention (surcharges, effets de bord critiques).

    Regle : 1.0 si au moins 1 surcharge Xmt_Call/OverWrittenBy detectee dans les confirmed,
    sinon 0.0 (omission par defaut, les points d'attention meta noient le signal).

    Note V3 : le `ctx.overwrites_detected` compte les matches grossiers (incluant commentaires
    et lignes de fichiers .dhsq). Le filtrage strict (lignes code .dhsp seulement) est fait dans
    `build_report._seed_type_6`. Le score reste sur le compte grossier pour la selection, mais
    le fragment rend une section vide si 0 apres filtrage strict -- dans ce cas, on compte
    sur le `if seeds.type_6.overwrites` dans le template pour omettre.
    """
    return 1.0 if ctx.overwrites_detected >= 1 else 0.0


def score_type_7_constantes_metier(ctx: ReportContext) -> float:
    """Type 7 -- Constantes et conventions metier (codes etat, codes tiers, litteraux).

    Regle : 1.0 si au moins 1 litteral metier recurrent detecte (ex: 'Ce4'), sinon 0.0.
    """
    return 1.0 if len(ctx.literals_detected) >= 1 else 0.0


# Triggers type 8 : soit un mot metier exact (dossier/parametrage/...), soit un
# sous-chaine technique DIVA caracteristique du parametrage dossier. Ces derniers
# (SOC.EntCodN(, Soc_Gerer_, ConfEnr(, Give_ETS) sont systematiquement utilises
# quand une option dossier est en jeu -- leur presence dans keywords_techniques
# doit suffire a declencher le type 8 (RETEX 2026-04-23 cas Nicolas : keywords
# techniques remplis de SOC.EntCodN(22|24), mais type 8 omis car set-intersection
# ne matchait que des mots complets, pas des sous-chaines).
_DOSSIER_EXACT_TRIGGERS = frozenset({
    "dossier", "parametrage", "paramétrage", "onglet", "option", "parametre", "paramètre",
})
_DOSSIER_SUBSTRING_TRIGGERS = (
    "soc.entcodn", "entcodn(", "soc_gerer_", "confenr(", "give_ets",
)


def score_type_8_parametrage_dossier(ctx: ReportContext) -> float:
    """Type 8 -- Parametrage dossier / systeme.

    Regle : 1.0 si au moins 1 mot-cle metier exact est detecte ('dossier', 'option',
    'parametrage', ...) OU si un keyword technique contient une sous-chaine
    caracteristique du parametrage DIVA (`SOC.EntCodN(`, `Soc_Gerer_`, `ConfEnr(`,
    `Give_ETS`). Sinon 0.0.
    """
    all_kw = set(ctx.keywords_metier) | set(ctx.keywords_techniques)
    if all_kw & _DOSSIER_EXACT_TRIGGERS:
        return 1.0
    for kw in all_kw:
        for trig in _DOSSIER_SUBSTRING_TRIGGERS:
            if trig in kw:
                return 1.0
    return 0.0


def score_type_10_verification_prealable(ctx: ReportContext) -> float:
    """Type 10 -- Verification prealable (commandes pretes a executer).

    Regle : 1.0 si confirmed >= 1 (il y a quelque chose a verifier avant d'agir), sinon 0.3.
    Synergique avec type 4 : quand on propose une action, on fournit aussi les commandes
    pour confirmer l'hypothese.
    """
    return 1.0 if ctx.confirmed_x13 >= 1 else 0.3


# --- Catalogue V3 (dev-action-ordered) ----------------------------------
# L'ordre du catalogue determine l'ordre de presentation dans le rapport. Post-critique
# UX dev : ce qui sert a **agir** passe avant ce qui sert a **comprendre**, qui passe avant
# ce qui sert a **explorer**. Les types non critiques (langage, attention) en fin.


CATALOG: list[ContentType] = [
    # Agir (priorite dev)
    ContentType(
        id=4,
        slug="endroit_agir",
        title="Endroit ou agir",
        score_fn=score_type_4_endroit_agir,
        template="type_4_endroit_agir.md.j2",
        tags=("feature", "ticket"),
        threshold=0.5,
    ),
    ContentType(
        id=10,
        slug="verification_prealable",
        title="Verification prealable (commandes)",
        score_fn=score_type_10_verification_prealable,
        template="type_10_verification_prealable.md.j2",
        tags=("feature", "ticket"),
        threshold=0.5,
    ),
    # Comprendre
    ContentType(
        id=7,
        slug="constantes_metier",
        title="Constantes et conventions metier",
        score_fn=score_type_7_constantes_metier,
        template="type_7_constantes_metier.md.j2",
        tags=("feature", "ticket"),
        threshold=0.5,
    ),
    ContentType(
        id=1,
        slug="exemples",
        title="Exemples de code DIVA",
        score_fn=score_type_1_exemples,
        template="type_1_exemples.md.j2",
        tags=("feature", "ticket"),
        threshold=0.5,
    ),
    ContentType(
        id=3,
        slug="etude_impact",
        title="Etude d'impact",
        score_fn=score_type_3_etude_impact,
        template="type_3_etude_impact.md.j2",
        tags=("feature", "ticket"),
        threshold=0.5,
    ),
    # Explorer plus loin
    ContentType(
        id=8,
        slug="parametrage_dossier",
        title="Parametrage dossier",
        score_fn=score_type_8_parametrage_dossier,
        template="type_8_parametrage_dossier.md.j2",
        tags=("feature", "ticket"),
        threshold=0.5,
    ),
    ContentType(
        id=5,
        slug="pistes_recherche",
        title="Pistes de recherche complementaires",
        score_fn=score_type_5_pistes,
        template="type_5_pistes.md.j2",
        tags=("feature", "ticket"),
        threshold=0.6,
    ),
    # Meta (rarement utile sur un ticket anomalie)
    ContentType(
        id=2,
        slug="fonctions_langage",
        title="Fonctions du langage DIVA utiles",
        score_fn=score_type_2_fonctions_langage,
        template="type_2_fonctions_langage.md.j2",
        tags=("feature",),
        threshold=0.5,
    ),
    ContentType(
        id=6,
        slug="attention",
        title="Points d'attention",
        score_fn=score_type_6_attention,
        template="type_6_attention.md.j2",
        tags=("feature", "ticket"),
        threshold=0.5,
    ),
]


# --- API publique -------------------------------------------------------


def evaluate_catalog(
    ctx: ReportContext,
    catalog: list[ContentType] | None = None,
) -> list[dict]:
    """Retourne la selection complete : liste de dicts trace-able pour metrics.json.

    Format : `[{id, slug, title, score, included, threshold, template, reason}]`.
    `reason` est une chaine courte expliquant le score (pour audit humain).
    """
    if catalog is None:
        catalog = CATALOG
    results = []
    for ct in catalog:
        score, included = ct.evaluate(ctx)
        results.append({
            "id": ct.id,
            "slug": ct.slug,
            "title": ct.title,
            "score": round(score, 3),
            "included": included,
            "threshold": ct.threshold,
            "template": ct.template,
            "reason": _reason(ct, ctx, score),
        })
    return results


def _reason(ct: ContentType, ctx: ReportContext, score: float) -> str:
    """Produit une courte chaine d'audit pour expliquer le score."""
    if ct.id == 1:
        return f"confirmed_x13={ctx.confirmed_x13}"
    if ct.id == 2:
        return f"request_type={ctx.request_type}"
    if ct.id == 3:
        return f"callers={ctx.callers}, confirmed={ctx.confirmed_x13}, new={ctx.new_findings}"
    if ct.id == 4:
        return f"confirmed_x13={ctx.confirmed_x13} (>=1 requis)"
    if ct.id == 5:
        total = ctx.confirmed_x13 + ctx.new_findings
        if total == 0:
            return "aucune matiere (confirmed=0, new=0)"
        ratio = ctx.confirmed_x13 / total
        return f"signal_ratio={ratio:.2f} (confirmed={ctx.confirmed_x13}, new={ctx.new_findings})"
    if ct.id == 6:
        return f"overwrites_detected={ctx.overwrites_detected}"
    if ct.id == 7:
        return f"literals_detected={list(ctx.literals_detected)}"
    if ct.id == 8:
        all_kw = set(ctx.keywords_metier) | set(ctx.keywords_techniques)
        exact_hits = sorted(all_kw & _DOSSIER_EXACT_TRIGGERS)
        substr_hits = sorted({trig for trig in _DOSSIER_SUBSTRING_TRIGGERS
                               if any(trig in kw for kw in all_kw)})
        return f"dossier_triggers_hit={exact_hits + substr_hits}"
    if ct.id == 10:
        return f"confirmed_x13={ctx.confirmed_x13} (synergique type 4)"
    return f"score={score:.2f}"


# --- Detection auxiliaire depuis evidence.confirmed ---------------------


# Patterns metier recurrents : codes etat, codes tiers, codes piece, arret, etc.
_LITERAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "Ce4": re.compile(r"\bCe4\s*[=<>!]+\s*['\"][\w\d]{1,3}['\"]", re.IGNORECASE),
    "TiCod": re.compile(r"\bTiCod\s*[=<>!]+\s*['\"][\w\d]{1,3}['\"]", re.IGNORECASE),
    "PiCod": re.compile(r"\bPiCod\s*[=<>!]+\s*['\"]?\d{1,3}['\"]?", re.IGNORECASE),
    "AsCod": re.compile(r"\bAsCod\s*[=<>!]+\s*['\"]?\d{1,3}['\"]?", re.IGNORECASE),
}

_OVERWRITE_PATTERN = re.compile(r"\b(Xmt_Call|OverWrittenBy)\b", re.IGNORECASE)


def _extract_detections(evidence: dict) -> tuple[tuple[str, ...], int]:
    """Scanne les snippets (confirmed + new_findings) pour detecter litteraux metier et surcharges.

    Retourne (literals_detected, overwrites_count). Les new_findings sont inclus car un
    litteral metier recurrent peut etre decouvert via grep sans etre sur un symbole cible
    (ex: la table Ce4 dans dav_sd.dhsq pour le ticket contremarque).
    """
    literals_found: set[str] = set()
    overwrite_count = 0
    sources = list(evidence.get("confirmed", [])) + list(evidence.get("new_findings", []))
    for item in sources:
        snippet = item.get("context_sample", {}).get("snippet", "")
        if not snippet:
            continue
        for name, pat in _LITERAL_PATTERNS.items():
            if pat.search(snippet):
                literals_found.add(name)
        overwrite_count += len(_OVERWRITE_PATTERN.findall(snippet))
    return tuple(sorted(literals_found)), overwrite_count


def ctx_from_json(
    request: dict,
    candidates: dict,
    evidence: dict,
) -> ReportContext:
    """Construit un ReportContext depuis les 3 JSON intermediaires de l'analyse pre-action."""
    literals, overwrites = _extract_detections(evidence)
    keywords_metier = tuple(
        kw.lower() for kw in request.get("keywords_metier", []) if isinstance(kw, str)
    )
    keywords_techniques = tuple(
        kw.lower() for kw in request.get("keywords_techniques", []) if isinstance(kw, str)
    )
    return ReportContext(
        request_type=request.get("type", "unknown"),
        confirmed_x13=len(evidence.get("confirmed", [])),
        new_findings=len(evidence.get("new_findings", [])),
        disappeared_x13=len(evidence.get("disappeared", [])),
        callers=len(evidence.get("impact", {}).get("callers", [])),
        literals_detected=literals,
        overwrites_detected=overwrites,
        keywords_metier=keywords_metier,
        keywords_techniques=keywords_techniques,
    )
