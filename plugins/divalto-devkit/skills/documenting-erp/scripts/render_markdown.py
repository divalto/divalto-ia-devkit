#!/usr/bin/env python3
"""render_markdown.py -- Rend un modele YAML en Markdown.

Filtre selon la couche demandee : business | schema | technical | all.

Structure produite :
  # Module {code} -- {label}
  ## Vue d'ensemble
  ## Entites
    ### {entity.label} ({entity.code})
      (sections par couche)
  ## Processus metier
  ## Glossaire
  ## Items a verifier

Usage :
  py render_markdown.py --input out/doc-erp/DAV/ --layer all \\
     --output out/doc-erp/DAV.md
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERREUR : pyyaml requis. Installer : py -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# Libelles des identifiants externes (multichoix Type 4) pour le rendu lisible.
# Les codes techniques (IdFic, LstPolice, ...) sont resolus au runtime par le
# framework DIVA ; cote doc on affiche la semantique cote utilisateur.
# En audience interne le code technique est affiche entre backticks a cote du libelle.
EXTERN_ID_LABELS = {
    "IdFic": "selection d'un fichier joint",
    "LstPolice": "choix de police de caracteres",
    "LstStyleWpf": "choix de style WPF",
    "LstStyleImp": "choix de style d'impression",
}


# --- Separation fond/forme : audience externe vs interne ------------------

# `externe` (defaut CLI) : livrable autonome destine au public large (clients,
# doc Confluence publique). Aucune ref path:line, aucune mention `fichier.dhsp`,
# aucun chemin absolu. Le validator bloque toute fuite.
#
# `interne` : livrable + refs inline + annexe Sources consultees. Destine a
# l'equipe Divalto pour audit et tracabilite.
AUDIENCES = ("externe", "interne")

# Regex pour detecter les refs X.13 dans les narratifs (pour sanitize externe).
# - `gttmchkart.dhsp:4454` ou `foo.dhsq:12` -> refs fichier:ligne explicites
# - `[gttmchkart.dhsp]` ou `[gtez000_sql.dhsf]` -> citations inline entre crochets
# - `C:/Developpements...` -> chemins absolus
_FILE_LINE_RE = re.compile(r"\b([a-zA-Z0-9_-]+\.dhs[pqdf]):\d+\b")
_BRACKETED_FILE_RE = re.compile(r"\[\s*[a-zA-Z0-9_\-]+\.dhs[pqdf][^\]]*\]")
_ABS_PATH_RE = re.compile(
    r'(?:"[A-Za-z]:[/\\][^"]+"|[A-Za-z]:[/\\][A-Za-z][A-Za-z0-9 _\-./\\]+)'
)


def _sanitize_narrative(text: str, audience: str) -> str:
    """Retire les refs X.13 d'un texte narratif en audience externe.

    En interne : renvoie le texte tel quel (les refs sont legitimes pour audit).
    En externe : supprime les chemins absolus, les `foo.dhsp:123`, les `[foo.dhsp]`.
    Les noms de fichiers sans annotation ([A VERIFIER], [A ENRICHIR]) sont conserves
    car ils signalent aux lecteurs des zones non completees.
    """
    if not text or audience == "interne":
        return text
    text = _ABS_PATH_RE.sub("la source X.13", text)
    text = _FILE_LINE_RE.sub(r"\1", text)
    text = _BRACKETED_FILE_RE.sub("", text)
    # Nettoyer les doubles espaces et les espaces orphelins devant la ponctuation
    # (resultat typique apres retrait de [foo.dhsp] : "article , client ." -> "article, client.")
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _src_inline(src: str, audience: str, prefix: str = "source") -> str:
    """Formate une annotation ` _(source : ...)_ ` en mode interne uniquement."""
    if audience != "interne" or not src:
        return ""
    return f" _({prefix} : `{src}`)_"


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_all(model_dir: Path, subfolder: str) -> list:
    folder = model_dir / subfolder
    if not folder.exists():
        return []
    items = []
    # Fichiers intermediaires a ignorer (produits par extract_narrative/merge_narrative)
    SKIP_SUFFIXES = (".partial.yaml", ".narrative.yaml")
    for path in sorted(folder.glob("*.yaml")):
        if any(path.name.endswith(suf) for suf in SKIP_SUFFIXES):
            continue
        data = load_yaml(path)
        if data:
            items.append(data)
    return items


def fmt_list(items, sep=", "):
    if not items:
        return "_-_"
    return sep.join(str(x) for x in items)


def render_module_header(module: dict, audience: str = "interne") -> str:
    lines = [f"# Module {module.get('code', '?')} -- {module.get('label', '')}", ""]
    header_parts = [f"**Prefixe** : `{module.get('prefix', '?')}`", f"**Domaine** : {module.get('domain', '?')}"]
    if audience == "interne":
        header_parts.insert(1, f"**Statut** : {module.get('status', '?')}")
    lines.append("  |  ".join(header_parts))
    lines.append("")
    if module.get("description"):
        lines.append(_sanitize_narrative(module["description"], audience))
        lines.append("")
    if module.get("business_context"):
        lines.append("## Contexte metier")
        lines.append(_sanitize_narrative(module["business_context"], audience))
        lines.append("")
    if module.get("bases"):
        lines.append(f"**Bases ({len(module['bases'])})** : {fmt_list(module['bases'])}")
    if module.get("entities"):
        lines.append(f"**Entites ({len(module['entities'])})** : {fmt_list(module['entities'])}")
    if module.get("depends_on"):
        lines.append(f"**Depend de** : {fmt_list(module['depends_on'])}")
    if module.get("integrates_with"):
        lines.append(f"**Integre avec** : {fmt_list(module['integrates_with'])}")
    lines.append("")
    return "\n".join(lines)


def _is_placeholder(v) -> bool:
    """Retourne True si v est None, vide, ou un placeholder '[A ENRICHIR]'/'[A VERIFIER]'."""
    if v is None:
        return True
    if isinstance(v, str):
        stripped = v.strip()
        if not stripped:
            return True
        if stripped.startswith("[A ENRICHIR]") or stripped.startswith("[A VERIFIER]"):
            return True
    return False


def render_entity_business(e: dict, audience: str = "interne") -> str:
    b = e.get("business") or {}
    lines = ["#### Metier", ""]
    # Description de l'objet metier (depuis commentaire d'entete du module Check)
    obj_desc = b.get("object_description")
    if isinstance(obj_desc, dict) and obj_desc.get("text"):
        text = _sanitize_narrative(obj_desc["text"], audience)
        src_annot = _src_inline(obj_desc.get("source", ""), audience)
        lines.append(f"> _{text}_{src_annot}")
        lines.append("")
    if b.get("role"):
        lines.append(_sanitize_narrative(b["role"], audience))
        lines.append("")
    if not _is_placeholder(b.get("criticality")):
        crit = b["criticality"]
        if audience == "interne":
            justif = b.get("criticality_justification")
            if justif:
                lines.append(f"**Criticite** : `{crit}` ({justif})")
            else:
                lines.append(f"**Criticite** : `{crit}`")
        else:
            # Reformulation metier : criticite en langage lisible pour un distributeur
            crit_label = {
                "core": "entite centrale -- transverse, referencee par de nombreux autres modules de l'ERP",
                "standard": "entite standard -- referencee par plusieurs modules",
                "peripheral": "entite peripherique -- peu referencee",
            }.get(crit, crit)
            lines.append(f"**Criticite metier** : {crit_label}")
    if b.get("variants"):
        lines.append(f"**Variantes** : {fmt_list(b['variants'])}")
    if b.get("processes"):
        lines.append(f"**Processus** : {fmt_list(b['processes'])}")
    if b.get("typical_users"):
        lines.append(f"**Utilisateurs** : {fmt_list(b['typical_users'])}")
    if b.get("business_rules"):
        lines.append("")
        lines.append("**Regles metier :**")
        for r in b["business_rules"]:
            if not _is_placeholder(r):
                lines.append(f"- {r}")
    # D3 : regles extraites des docstrings des procedures Module Check
    rules_code = b.get("business_rules_from_code") or []
    if rules_code:
        lines.append("")
        lines.append(f"**Regles issues de l'objet metier ({len(rules_code)} procedures documentees) :**")
        lines.append("")
        if audience == "interne":
            lines.append("| Procedure | Description metier | Source |")
            lines.append("|-----------|--------------------|--------|")
            for r in rules_code[:12]:
                desc = (r.get("description") or "").replace("|", "\\|")[:80]
                lines.append(f"| `{r.get('procedure','')}` | {desc} | `{r.get('source','')}` |")
        else:
            lines.append("| Procedure | Description metier |")
            lines.append("|-----------|--------------------|")
            for r in rules_code[:12]:
                desc = (r.get("description") or "").replace("|", "\\|")[:80]
                lines.append(f"| `{r.get('procedure','')}` | {desc} |")
    if b.get("examples"):
        lines.append("")
        lines.append("**Exemples :**")
        for x in b["examples"]:
            if not _is_placeholder(x):
                lines.append(f"- {x}")
    # Champs codifies : valeurs concretes + contexte metier
    codified = b.get("codified_fields") or []
    if codified:
        lines.append("")
        lines.append(f"**Champs codifies ({len(codified)}) -- listes de valeurs utilisees par l'ecran de saisie :**")
        lines.append("")
        for c in codified[:40]:
            raw_title = (c.get("titre") or c.get("info_bulle") or "").strip()
            choix_id = c.get("choix_id", "")
            # Si le titre explicite est absent, ne pas repeter le choix_id (evite "CODE -- CODE")
            title = raw_title if raw_title and raw_title.upper() != choix_id.upper() else ""
            bulle = c.get("info_bulle") or ""
            values = c.get("values") or []
            values_src = c.get("values_source")
            choix_type = (c.get("choix_type") or "").strip()
            lookup = c.get("lookup") or {}
            extern_id = c.get("extern_id") or ""
            lines.append("")
            lines.append(f"**`{choix_id}`** — {title}" if title else f"**`{choix_id}`**")
            if bulle and bulle != title:
                lines.append(f"_{bulle}_")

            if choix_type == "3" and lookup:
                # Multichoix Type 3 : lookup dynamique (valeurs resolues au runtime
                # depuis la table cible). On ne liste pas des `tbl*` illisibles : on
                # explicite la provenance.
                enreg = (lookup.get("enreg") or "").strip()
                donnee = (lookup.get("donnee") or "").strip()
                prefixe = (lookup.get("prefixe") or "").strip()
                ideb = lookup.get("ideb")
                ifin = lookup.get("ifin")
                target = f"`{enreg}.{donnee}`" if enreg and donnee else ""
                range_str = ""
                if prefixe and ideb not in (None, "") and ifin not in (None, ""):
                    range_str = f" (codes `{prefixe}{ideb}` a `{prefixe}{ifin}`)"
                if target:
                    lines.append(f"Liste dynamique : valeurs resolues au runtime depuis {target}{range_str}.")
                else:
                    lines.append("_(liste dynamique resolue au runtime)_")
            elif choix_type == "4" and extern_id:
                # Multichoix Type 4 : identifiant externe. Le framework resout au
                # runtime (fichier joint, police, style WPF...). On affiche la
                # semantique lisible cote doc.
                label_extern = EXTERN_ID_LABELS.get(
                    extern_id, f"identifiant externe `{extern_id}`"
                )
                if audience == "interne" and extern_id not in EXTERN_ID_LABELS:
                    lines.append(f"Liste externe : {label_extern}.")
                elif audience == "interne":
                    lines.append(f"Liste externe : {label_extern} (`{extern_id}`).")
                else:
                    lines.append(f"Liste externe : {label_extern}.")
            elif values:
                # Multichoix Type 1 (liste fixe) : valeurs litterales, avec rendu
                # degrade en externe pour :
                #   - labels `tbl*`  (noms de bitmaps)          -> `_(icone)_`
                #   - labels `#<nom>` (references i18n)         -> `_(libelle traduit)_`
                # En interne, conserver le code brut pour l'audit (ressources nommees
                # identifiables).
                value_strs = []
                for v in values[:12]:
                    vid = v.get("id", "")
                    vlabel_raw = (v.get("label") or "").strip()
                    is_bmp_ref = bool(v.get("label_reference"))
                    is_i18n_ref = bool(v.get("label_translation_ref"))
                    fstyle_name = (v.get("fstyle_name") or "").strip()
                    if audience == "externe" and is_bmp_ref:
                        # FS-03 : si le nom est resolu dans une variante fstyle,
                        # afficher `_(icone TBLART)_` pour donner un indice
                        # semantique au lecteur. Fallback `_(icone)_` pour les
                        # orphelins (8 cas sur 120 pour DAV).
                        if fstyle_name:
                            vlabel = f"_(icone {fstyle_name})_"
                        else:
                            vlabel = "_(icone)_"
                    elif audience == "externe" and is_i18n_ref:
                        vlabel = "_(libelle traduit)_"
                    elif not vlabel_raw:
                        vlabel = "_(vide)_"
                    else:
                        vlabel = vlabel_raw
                    color = v.get("color", "")
                    color_str = f" `[{color}]`" if color else ""
                    value_strs.append(f"`{vid}` = {vlabel}{color_str}")
                lines.append(f"Valeurs : " + " · ".join(value_strs))
                if len(values) > 12:
                    lines.append(f"_(+{len(values)-12} autres valeurs)_")
                if values_src and audience == "interne":
                    lines.append(f"_(source valeurs : `{values_src}`)_")
            else:
                if audience == "interne":
                    lines.append(f"_(valeurs non extraites — consulter `{c.get('dict_file','?')}`)_")
                else:
                    lines.append(f"_(valeurs non extraites)_")
            if audience == "interne":
                lines.append(f"Source ecran : `{c.get('source','')}`")
        if len(codified) > 40:
            lines.append("")
            lines.append(f"_({len(codified) - 40} autres champs codifies)_")
    lines.append("")
    return "\n".join(lines)


def render_mermaid_diagram(e: dict, audience: str = "interne") -> str:
    """D2 : genere un diagramme Mermaid a partir des relations confirmees.

    En externe, on limite plus agressivement le nombre de noeuds (15) pour qu'un
    diagramme tienne sur une seule page PDF ; le tableau FK complet au-dessus
    donne deja la liste exhaustive. En interne on garde 30 pour l'audit.
    Layout vertical (graph TD) : plus compact en A4 portrait que LR.
    """
    s = e.get("schema") or {}
    relations = s.get("relations") or []
    if not relations:
        return ""
    code = e.get("code", "E")
    limit = 15 if audience == "externe" else 30
    out = ["```mermaid", "graph TD"]
    out.append(f"    {code}[({code})]:::entity")
    seen_targets = set()
    truncated = False
    for r in relations:
        target = r.get("target_entity", "?")
        if target in seen_targets:
            continue
        if len(seen_targets) >= limit:
            truncated = True
            break
        seen_targets.add(target)
        field = r.get("source_field", "")
        label = f"|{field}|" if field else ""
        out.append(f"    {code} -->{label} {target}[({target})]")
    out.append("    classDef entity fill:#E8EEF5,stroke:#0F3D68,stroke-width:2px")
    out.append("```")
    if truncated:
        out.append("")
        out.append(f"_Diagramme limite aux {limit} premieres cibles ; liste complete ci-dessus._")
    return "\n".join(out)


def render_entity_schema(e: dict, audience: str = "interne") -> str:
    s = e.get("schema") or {}
    lines = ["#### Schema", ""]
    if s.get("primary_table"):
        lines.append(f"**Table principale** : `{s['primary_table']}`")
    if s.get("primary_key"):
        pk_fields = ", ".join(f"`{p}`" for p in s["primary_key"])
        src_str = _src_inline(s.get("primary_key_source", ""), audience)
        lines.append(f"**Cle primaire metier** : {pk_fields}{src_str}")
    if s.get("primary_key_sql_technical"):
        sql_pk = ", ".join(f"`{p}`" for p in s["primary_key_sql_technical"])
        lines.append(f"**Cle primaire SQL (technique, auto-incrementee)** : {sql_pk}")
    if s.get("required_fields"):
        rf = ", ".join(f"`{f}`" for f in s["required_fields"])
        lines.append(f"**Champs obligatoires metier** : {rf}")
    if s.get("satellite_tables"):
        lines.append(f"**Tables satellites** : {fmt_list([f'`{t}`' for t in s['satellite_tables']])}")
    if s.get("relations"):
        # Separer les FK des partitions pour lisibilite
        fks = [r for r in s["relations"] if r.get("type") == "fk"]
        parts = [r for r in s["relations"] if r.get("type") == "partitioning"]
        if fks:
            lines.append("")
            lines.append(f"**Relations inter-entites ({len(fks)} FK confirmees)** :")
            lines.append("")  # LIGNE VIDE : necessaire pour que markdown cree une VRAIE liste
            for r in fks:
                src = r.get("source_entity", "?")
                tgt = r.get("target_entity", "?")
                tgt_label = r.get("target_entity_label")
                card = r.get("cardinality", "?")
                field = r.get("source_field", "")
                note = r.get("business_note", "")
                tgt_display = f"`{tgt}`"
                if tgt_label:
                    tgt_display = f"`{tgt}` _({tgt_label})_"
                bits = [f"`{src}` → {tgt_display} _({card})_"]
                if field:
                    bits.append(f"via champ `{field}`")
                # Note technique (traitement apres saisie, zoom f8, Check_*_lib) reservee
                # a l'audience interne : bruit pour un partenaire distributeur en externe.
                if note and audience == "interne":
                    bits.append(f"— {note}")
                lines.append(f"- " + " ".join(bits))
        if parts:
            lines.append("")
            lines.append(f"**Champs de partitionnement ({len(parts)})** :")
            lines.append("")
            for r in parts:
                field = r.get("source_field", "?")
                note = r.get("business_note", "")
                lines.append(f"- `{field}` — {note}")
    # D2 : diagramme Mermaid auto-genere depuis les relations confirmees
    mermaid = render_mermaid_diagram(e, audience=audience)
    if mermaid:
        lines.append("")
        lines.append("**Diagramme relationnel** (genere depuis les bindings f8 du masque) :")
        lines.append("")
        lines.append(mermaid)
    elif s.get("diagram_mermaid"):
        lines.append("")
        lines.append("```mermaid")
        lines.append(s["diagram_mermaid"].rstrip())
        lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_entity_technical(e: dict, audience: str = "interne") -> str:
    t = e.get("technical") or {}
    lines = ["#### Technique", ""]
    if not _is_placeholder(t.get("dictionary_source")) and audience == "interne":
        lines.append(f"**Dictionnaire source** : `{t['dictionary_source']}`")
    if t.get("record_name"):
        lines.append(f"**Record DIVA** : `{t['record_name']}`")
    if t.get("field_count") is not None:
        lines.append(f"**Nombre de champs** : {t['field_count']}")
    if t.get("audit_fields"):
        lines.append(f"**Champs audit** : {fmt_list([f'`{x}`' for x in t['audit_fields']])}")
    if t.get("zoom_code"):
        lines.append(f"**Zoom** : `{t['zoom_code']}`")
    if t.get("main_screens"):
        lines.append(f"**Ecrans** : {fmt_list([f'`{x}`' for x in t['main_screens']])}")
    if t.get("main_program"):
        lines.append(f"**Module principal** : `{t['main_program']}`")
    if t.get("module_check"):
        mchk = t["module_check"]
        info = t.get("module_check_info") or {}
        size_kb = info.get("size_chars", 0) // 1024
        lines.append(f"**Module Check (objet metier)** : `{mchk}` ({size_kb} Ko, "
                     f"{info.get('procedures_public_count', '?')} procedures publiques)")
    # Analyse CE : drapeaux multi-etats Ce1..CeA (utilisation + valeurs).
    # Reservee a l'audience interne : le detail technique des drapeaux Ce1..CeA
    # est utile pour le dev Divalto mais bruite le livrable distributeur (cf
    # POC validee 2026-04-23 : absence de cette section en externe), et les
    # `_[A VERIFIER]_` de la colonne `description_metier` leakaient dans le
    # livrable externe (regression signalee par Stephane 2026-04-24).
    ce = t.get("ce_analysis") or {}
    ce_fields = ce.get("fields") or []
    if ce_fields and audience == "interne":
        lines.append("")
        lines.append(f"**Codes d'etat Ce1..CeA (drapeaux multi-etats)** — {ce.get('summary','')}")
        lines.append("")
        lines.append("Chaque CE est un champ char(1). La description metier est redigee a partir "
                     "des signaux X.13 (commentaire dictionnaire, constantes du Module Check, "
                     "regle d'activation) avec citation fichier:ligne. La colonne *Signaux* "
                     "rappelle le role technique deduit de l'usage SQL (indexes, co-colonnes).")
        lines.append("")
        lines.append("| Champ | Statut | Description metier | Signaux | Regle d'activation | Valeurs | Indexes |")
        lines.append("|-------|--------|--------------------|---------|--------------------|---------|---------|")
        for f in ce_fields:
            values = f.get("values_observed_in_mchk") or []
            def _fmt_val(v: str) -> str:
                if v == "":
                    return "`(vide)`"
                if v == " ":
                    return "`' '`"
                return f"`{v}`"
            val_str = ", ".join(_fmt_val(v) for v in values) if values else "_—_"
            idxs = f.get("indexes") or []
            idx_str = ", ".join(f"`{i}`" for i in idxs[:2])
            if len(idxs) > 2:
                idx_str += f" _+{len(idxs)-2}_"
            if not idx_str:
                idx_str = "_—_"
            status_badge = {
                "actif": "✓ actif",
                "reserve": "○ reserve",
                "inutilise": "○ reserve",
            }.get(f.get("status"), f.get("status", "?"))
            # Regle d'activation : expression Condition, sinon valeur fixe, sinon tiret
            rule = f.get("activation_rule")
            fixed = f.get("fixed_value")
            if rule:
                rule_cell = f"actif si `{rule}`"
            elif fixed is not None:
                rule_cell = f"valeur fixe `'{fixed}'`"
            else:
                rule_cell = "_—_"
            # Description metier : narratif (Claude) + citation en italique, ou [A VERIFIER]
            desc_metier = f.get("description_metier")
            desc_src = f.get("description_metier_source")
            if desc_metier:
                if desc_src and "aucun signal" not in desc_src and audience == "interne":
                    desc_cell = f"{desc_metier} _(src: {desc_src})_"
                else:
                    desc_cell = _sanitize_narrative(desc_metier, audience)
            else:
                desc_cell = "_[A VERIFIER]_"
            # Signaux : ancien role_infere, conserve comme diagnostic technique
            signals_cell = f.get("role_infere") or "_—_"
            lines.append("| `{}` | {} | {} | {} | {} | {} | {} |".format(
                f.get("name", ""),
                status_badge,
                desc_cell,
                signals_cell,
                rule_cell,
                val_str,
                idx_str,
            ))

    # API metier (procedures publiques de l'objet) -- reservee a l'audience interne
    # (liste brute de noms de procs = bruit pour un partenaire distributeur)
    api = t.get("object_api") or {}
    if api.get("public_procedures") and audience == "interne":
        procs = api["public_procedures"]
        src_annot = _src_inline(api.get("source", ""), audience)
        lines.append("")
        lines.append(f"**API metier ({len(procs)} procedures publiques)**{src_annot} :")
        for p in procs[:20]:
            lines.append(f"- `{p}`")
    # Constantes metier significatives -- reservees a l'audience interne (utiles
    # uniquement en personnalisation lourde, hors scope partenaire distributeur)
    consts = t.get("business_constants") or []
    if consts and audience == "interne":
        lines.append("")
        lines.append(f"**Constantes metier ({len(consts)} significatives) :**")
        lines.append("")
        if audience == "interne":
            lines.append("| Constante | Valeur | Commentaire | Source |")
            lines.append("|-----------|--------|-------------|--------|")
            for c in consts[:15]:
                comment = (c.get("comment") or "").replace("|", "\\|")[:50]
                lines.append("| `{}` | `{}` | {} | `{}` |".format(
                    c.get("name", ""),
                    c.get("value", "")[:30],
                    comment,
                    c.get("source", ""),
                ))
        else:
            lines.append("| Constante | Valeur | Commentaire |")
            lines.append("|-----------|--------|-------------|")
            for c in consts[:15]:
                comment = (c.get("comment") or "").replace("|", "\\|")[:50]
                lines.append("| `{}` | `{}` | {} |".format(
                    c.get("name", ""),
                    c.get("value", "")[:30],
                    comment,
                ))
    if t.get("fields"):
        lines.append("")
        # En externe : filtrer a la liste courte des champs "pilotes" (PK metier +
        # required_fields + DOS/HSDT). Les 200+ champs complets restent en interne.
        total_fields = len(t["fields"])
        if audience == "externe":
            s_ent = e.get("schema") or {}
            pilots: set[str] = set()
            for k in (s_ent.get("primary_key") or []):
                pilots.add(k.upper())
            for k in (s_ent.get("required_fields") or []):
                pilots.add(k.upper())
            pilots.update({"DOS", "HSDT"})
            fields_to_show = [f for f in t["fields"] if f.get("name", "").upper() in pilots]
            lines.append("**Champs pilotes ({} sur {} au total -- cle primaire metier, champs obligatoires, dossier et date de fin de validite) :**".format(
                len(fields_to_show), total_fields))
        else:
            fields_to_show = t["fields"]
            lines.append("**Champs (extrait, {} au total) :**".format(total_fields))
        lines.append("")
        # Detecter si au moins un champ a un label DIVA pour afficher la colonne
        has_labels = any(
            f.get("label") and f.get("label") != f.get("name")
            for f in fields_to_show
        )
        has_checks = any(f.get("checks") for f in fields_to_show)
        show_source = audience == "interne"
        if has_labels:
            if has_checks:
                if show_source:
                    lines.append("| Nom | Libelle DIVA | Nature | Type SQL | Null | Regles (check procs) | Source |")
                    lines.append("|-----|-------------|--------|----------|------|----------------------|--------|")
                else:
                    lines.append("| Nom | Libelle DIVA | Nature | Type SQL | Null | Regles (check procs) |")
                    lines.append("|-----|-------------|--------|----------|------|----------------------|")
            else:
                if show_source:
                    lines.append("| Nom | Libelle DIVA | Nature | Type SQL | Null | Source |")
                    lines.append("|-----|-------------|--------|----------|------|--------|")
                else:
                    lines.append("| Nom | Libelle DIVA | Nature | Type SQL | Null |")
                    lines.append("|-----|-------------|--------|----------|------|")
        else:
            lines.append("| Nom | Nature | Type SQL | Null | Zoom | Couche |")
            lines.append("|-----|--------|----------|------|------|--------|")
        for f in fields_to_show[:80]:  # limite de securite (filtrage pilote deja applique en externe)
            if has_labels:
                label = f.get("label") or ""
                if label == f.get("name"):
                    label = ""
                source = f.get("source") or ""
                if has_checks:
                    checks = f.get("checks") or []
                    checks_str = ", ".join(f"`{c}`" for c in checks[:2])
                    if len(checks) > 2:
                        checks_str += f" _+{len(checks)-2}_"
                    if show_source:
                        lines.append("| `{}` | {} | `{}` | {} | {} | {} | {} |".format(
                            f.get("name", ""),
                            label,
                            f.get("nature", ""),
                            f.get("sql_type", ""),
                            "N" if f.get("nullable") else "O",
                            checks_str or "-",
                            f"`{source}`" if source else "-",
                        ))
                    else:
                        lines.append("| `{}` | {} | `{}` | {} | {} | {} |".format(
                            f.get("name", ""),
                            label,
                            f.get("nature", ""),
                            f.get("sql_type", ""),
                            "N" if f.get("nullable") else "O",
                            checks_str or "-",
                        ))
                else:
                    if show_source:
                        lines.append("| `{}` | {} | `{}` | {} | {} | {} |".format(
                            f.get("name", ""),
                            label,
                            f.get("nature", ""),
                            f.get("sql_type", ""),
                            "N" if f.get("nullable") else "O",
                            f"`{source}`" if source else "-",
                        ))
                    else:
                        lines.append("| `{}` | {} | `{}` | {} | {} |".format(
                            f.get("name", ""),
                            label,
                            f.get("nature", ""),
                            f.get("sql_type", ""),
                            "N" if f.get("nullable") else "O",
                        ))
            else:
                lines.append("| `{}` | {} | {} | {} | {} | {} |".format(
                    f.get("name", ""),
                    f.get("nature", ""),
                    f.get("sql_type", ""),
                    "N" if f.get("nullable") else "O",
                    f.get("zoom", "") or "-",
                    f.get("layer", ""),
                ))
        if audience == "externe":
            hidden = total_fields - len(fields_to_show)
            if hidden > 0:
                lines.append("")
                lines.append(f"_Liste complete des {total_fields} champs ({hidden} non affiches ici) disponible en audience interne._")
        elif len(fields_to_show) > 80:
            lines.append(f"")
            lines.append(f"_({len(fields_to_show) - 80} champs supplementaires non affiches)_")
    # Indexes SQL : reserves a l'audience interne (utiles pour perf / requetes
    # personnalisees, pas pour un partenaire distributeur).
    if t.get("indexes") and audience == "interne":
        lines.append("")
        lines.append("**Indexes :**")
        for idx in t["indexes"]:
            flags = []
            if idx.get("unique"):
                flags.append("unique")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"- `{idx.get('name', '?')}`{flag_str} sur {fmt_list([f'`{c}`' for c in idx.get('fields', [])])}")
    if t.get("performance_notes"):
        lines.append("")
        lines.append(f"**Notes de performance** : {t['performance_notes']}")
    lines.append("")
    return "\n".join(lines)


def render_entity(e: dict, layer: str, audience: str = "interne") -> str:
    code = e.get("code", "?")
    label = e.get("label", code)
    lines = [f"### {label} ({code})", ""]
    if e.get("module") or e.get("base"):
        meta = []
        if e.get("module"):
            meta.append(f"module `{e['module']}`")
        if e.get("base"):
            meta.append(f"base `{e['base']}`")
        if e.get("status") and audience == "interne":
            meta.append(f"statut {e['status']}")
        lines.append("_" + " | ".join(meta) + "_")
        lines.append("")
    if layer in ("all", "business"):
        lines.append(render_entity_business(e, audience=audience))
    if layer in ("all", "schema"):
        lines.append(render_entity_schema(e, audience=audience))
    if layer in ("all", "technical"):
        lines.append(render_entity_technical(e, audience=audience))
    return "\n".join(lines)


def render_process(p: dict) -> str:
    lines = [f"### {p.get('label', p.get('code', '?'))}", ""]
    if p.get("description"):
        lines.append(p["description"])
        lines.append("")
    if p.get("trigger"):
        lines.append(f"**Declencheur** : {p['trigger']}")
    if p.get("outcome"):
        lines.append(f"**Resultat** : {p['outcome']}")
    if p.get("entities"):
        lines.append(f"**Entites traversees** : {fmt_list([f'`{e}`' for e in p['entities']])}")
    if p.get("steps"):
        lines.append("")
        lines.append("**Etapes :**")
        for i, step in enumerate(p["steps"], 1):
            bits = [step.get("label", "?")]
            if step.get("actor"):
                bits.append(f"_{step['actor']}_")
            if step.get("entity"):
                bits.append(f"(entite `{step['entity']}`)")
            lines.append(f"{i}. " + " ".join(bits))
    lines.append("")
    return "\n".join(lines)


def collect_a_verifier(module: dict, entities: list, relations: list) -> list:
    items = []
    if module:
        for v in module.get("a_verifier", []) or []:
            items.append(("module", module.get("code", ""), v))
    for e in entities:
        for v in (e.get("meta") or {}).get("a_verifier", []) or []:
            items.append(("entity", e.get("code", ""), v))
    for r in relations:
        for v in r.get("a_verifier", []) or []:
            items.append(("relation", r.get("entity", ""), v))
    return items


def render_sources_annexe(module: dict, entities: list) -> str:
    """Annexe audit : recapitulatif des sources X.13 citees dans le modele.

    Produite uniquement en audience=interne. Permet a un auditeur de retrouver
    chaque citation (fichier:ligne) independamment du corps du livrable.
    """
    lines = ["## Sources consultees (audit interne)", ""]
    lines.append(
        "Cette annexe n'apparait qu'en audience `interne`. Elle recapitule les "
        "chemins source X.13 cites dans le modele pour faciliter l'audit."
    )
    lines.append("")
    rows: list[tuple[str, str, str]] = []
    for e in entities:
        code = e.get("code", "?")
        b = e.get("business") or {}
        t = e.get("technical") or {}
        s = e.get("schema") or {}
        obj = b.get("object_description") or {}
        if obj.get("source"):
            rows.append((code, "object_description", obj["source"]))
        for r in b.get("business_rules_from_code") or []:
            if r.get("source"):
                rows.append((code, f"rule `{r.get('procedure','?')}`", r["source"]))
        for c in b.get("codified_fields") or []:
            if c.get("source"):
                rows.append((code, f"codified `{c.get('choix_id','?')}`", c["source"]))
        if s.get("primary_key_source"):
            rows.append((code, "primary_key", s["primary_key_source"]))
        if t.get("dictionary_source"):
            rows.append((code, "dictionary", t["dictionary_source"]))
        api = t.get("object_api") or {}
        if api.get("source"):
            rows.append((code, "API metier", api["source"]))
        for c in t.get("business_constants") or []:
            if c.get("source"):
                rows.append((code, f"constant `{c.get('name','?')}`", c["source"]))
        ce_fields = (t.get("ce_analysis") or {}).get("fields") or []
        for f in ce_fields:
            src = f.get("description_metier_source")
            if src and "aucun signal" not in src:
                rows.append((code, f"CE `{f.get('name','?')}`", src))
    if not rows:
        lines.append("_Aucune source citee dans le modele._")
        return "\n".join(lines)
    lines.append(f"**{len(rows)} citations recensees :**")
    lines.append("")
    lines.append("| Entite | Champ / usage | Source |")
    lines.append("|--------|---------------|--------|")
    for code, usage, src in rows[:200]:
        lines.append(f"| `{code}` | {usage} | `{src}` |")
    if len(rows) > 200:
        lines.append("")
        lines.append(f"_({len(rows) - 200} citations supplementaires non listees)_")
    return "\n".join(lines)


def render_glossary() -> str:
    """Glossaire minimal des conventions Divalto utilisees dans le livrable.

    8 termes techniques recurrents dans les couches SCHEMA et TECHNIQUE d'une
    fiche entite. Presence en audience externe pour un partenaire distributeur
    qui n'est pas dev Divalto ; inoffensif en audience interne (skippable par
    un lecteur aguerri via le TOC PDF).
    """
    lines = [
        "## Glossaire",
        "",
        "Conventions Divalto utilisees dans ce livrable.",
        "",
        "`<PREFIX>` _(prefixe module)_",
        ":   Prefixe canonique d'un module ERP, present en tete des noms de programmes, tables et bases (ex: `GTF*` pour Achat-Vente, `CCF*` pour Comptabilite). Chaque module standard a son prefixe dedie.",
        "",
        "**Base** _(ex: `GTFPCF`, `GTFDOS`)_",
        ":   Unite de packaging logique regroupant plusieurs tables SQL d'un meme domaine fonctionnel dans un module (ex: `GTFPCF` = Pilote Commercial Fichier, regroupe les fiches tiers ART, CLI, FOU, VRP). Ce n'est pas une base SQL au sens serveur -- c'est une organisation Divalto.",
        "",
        "**Record DIVA**",
        ":   Declaration d'une structure de donnees (table) en langage DIVA, portee par un dictionnaire `.dhsd`. Equivalent d'un schema de table pour le runtime : le Record nomme la table (ex: `CLI`), ses champs, leur Nature, et les index associes.",
        "",
        "**Module Check** _(fichier `gttmchk<entite>.dhsp`)_",
        ":   Couche \"objet metier\" d'une entite : regroupe les regles de controle des champs (`Check_<ENT>_Field_*`), les autorisations (`Authorize_<ENT>_Insert/Update/Delete`) et la resolution des cles etrangeres (`Find_<TARGET>`). Toute saisie passe par ce fichier avant ecriture SQL.",
        "",
        "**Nature** _(type de champ DIVA)_",
        ":   Type d'un champ tel que declare dans le dictionnaire. Conventions frequentes : `C<n>` chaine de n caracteres, `N<n>` entier sur n octets, `F<n,d>` numerique float (n chiffres, d decimales), `D8` date, `DH` datetime, `1,0` drapeau booleen (1 = non, 2 = oui). La Nature determine le type SQL genere par la synchro (`char(n)`, `int`, `numeric`, `date`, `datetime2`...).",
        "",
        "**`Ce1..CeA`** _(drapeaux d'etat)_",
        ":   Dix champs `char(1)` reserves en tete de chaque table pour porter des drapeaux d'etat multi-valeurs (`actif/inactif/present/absent/...`). Utilises comme discriminants d'index SQL (tres selectifs) et pour accelerer les filtrages metier recurrents (presence d'une note, appartenance a un groupe, statut en cours, etc.). Chaque CE peut etre actif ou reserve pour extension future.",
        "",
        "**`f8` / zoom** _(binding ecran)_",
        ":   Touche clavier F8 dans l'ERP qui ouvre une fenetre de selection (zoom) pour choisir une valeur dans une table liee. Dans un masque `.dhsf`, `f8=9097` designe le numero du zoom a ouvrir (ici 9097 = zoom des codes postaux). Principal mecanisme UX de navigation dans les FK.",
        "",
        "**`table_associee=oui`** _(attribut de masque)_",
        ":   Attribut d'un champ dans un masque ecran `.dhsf` declarant que le champ pointe vers une table de reference. Combine avec `f8=<num>`, materialise une relation FK a l'interface utilisateur.",
        "",
        "**`HSDT`** _(date de fin de validite)_",
        ":   Champ standard de type date present sur la plupart des entites. Non renseigne = fiche active ; renseigne = fiche cloturee / historisee / hors-activite a partir de cette date. Permet le soft-delete sans perdre l'historique.",
        "",
    ]
    return "\n".join(lines)


def validate_livrable(markdown: str, audience: str = "externe") -> list[str]:
    """Valide le livrable : aucune ref source visible en audience externe.

    En audience interne : renvoie [] (les refs sont legitimes pour audit).
    """
    if audience == "interne":
        return []
    violations: list[str] = []
    patterns = [
        (re.compile(r"[A-Za-z]:[/\\][A-Za-z][A-Za-z0-9 _\-.]*[/\\]"),
         "chemin absolu dans le livrable externe"),
        (re.compile(r"\[X\.1[23]\]|\[(?:CONFIRME|DISPARU|NOUVEAU)\s+X\.1[23]\]"),
         "marqueur de statut X.12/X.13 dans le livrable externe"),
        (re.compile(r"\b[a-zA-Z0-9_-]+\.dhs[pqdf]:\d+\b"),
         "reference fichier:ligne dans le livrable externe"),
    ]
    for pat, label in patterns:
        for m in pat.finditer(markdown):
            line_no = markdown[:m.start()].count("\n") + 1
            excerpt = markdown[max(0, m.start() - 20):m.end() + 30].replace("\n", " ")
            violations.append(f"ligne {line_no} : {label} -- ...{excerpt}...")
    return violations


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="Repertoire modele, ex: out/doc-erp/DAV/")
    ap.add_argument("--layer", choices=["business", "schema", "technical", "all"], default="all")
    ap.add_argument("--output", required=True, help="Chemin markdown de sortie")
    ap.add_argument("--sort", choices=["code", "criticality"], default="code")
    ap.add_argument(
        "--audience",
        choices=list(AUDIENCES),
        default="externe",
        help=(
            "Audience cible. 'externe' (defaut) : autonomie documentaire stricte, "
            "aucune ref source visible. 'interne' : refs inline + annexe Sources "
            "consultees pour audit equipe."
        ),
    )
    args = ap.parse_args()

    in_dir = Path(args.input)
    module = load_yaml(in_dir / "module.yaml")
    entities = load_all(in_dir, "entity")
    relations = load_all(in_dir, "relation")
    processes = load_all(in_dir, "process")

    # tri
    if args.sort == "criticality":
        order = {"core": 0, "standard": 1, "peripheral": 2}
        entities.sort(key=lambda e: (order.get((e.get("business") or {}).get("criticality"), 9), e.get("code", "")))
    else:
        entities.sort(key=lambda e: e.get("code", ""))

    out_lines = []
    if module:
        out_lines.append(render_module_header(module, audience=args.audience))
        # Glossaire : apres le header module, avant la liste des entites.
        # 8 termes techniques recurrents pour aider un lecteur non-dev-Divalto.
        out_lines.append(render_glossary())

    # Rendu par couche : le titre de section indique la couche
    layer_title = {"business": "Vue metier", "schema": "Vue schema",
                   "technical": "Vue technique", "all": ""}[args.layer]

    if entities:
        header = "## Entites" if args.layer == "all" else f"## Entites -- {layer_title}"
        out_lines.append(header)
        out_lines.append("")
        for e in entities:
            out_lines.append(render_entity(e, args.layer, audience=args.audience))

    if processes and args.layer in ("all", "business"):
        out_lines.append("## Processus metier")
        out_lines.append("")
        for p in processes:
            out_lines.append(render_process(p))

    # items a verifier en fin de document (audience interne uniquement -- en externe
    # ces items sont du jargon de generation qui casse la credibilite du livrable)
    a_verifier = collect_a_verifier(module, entities, relations)
    if a_verifier and args.audience == "interne":
        out_lines.append("## Items [A VERIFIER]")
        out_lines.append("")
        for kind, code, item in a_verifier:
            out_lines.append(f"- **{kind} `{code}`** : {item}")
        out_lines.append("")

    # Annexe Sources consultees : uniquement en audience interne
    if args.audience == "interne" and entities:
        out_lines.append(render_sources_annexe(module, entities))
        out_lines.append("")

    # Suffixe .interne.md si audience=interne, sinon chemin --output tel quel
    out = Path(args.output)
    if args.audience == "interne":
        stem = out.stem
        if stem.endswith(".interne"):
            pass
        else:
            out = out.with_name(f"{stem}.interne{out.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(out_lines)

    # Validator : refuse toute ref visible en audience externe
    violations = validate_livrable(content, audience=args.audience)
    if violations:
        print("ERREUR : livrable externe non conforme (refs visibles detectees) :", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print("Corriger le sanitize des narratifs ou le YAML amont.", file=sys.stderr)
        return 4

    with out.open("w", encoding="utf-8") as f:
        f.write(content)

    summary = {
        "input": str(in_dir),
        "output": str(out),
        "layer": args.layer,
        "audience": args.audience,
        "bytes": len(content.encode("utf-8")),
        "entities_rendered": len(entities),
        "processes_rendered": len(processes),
        "a_verifier_count": len(a_verifier),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main()
