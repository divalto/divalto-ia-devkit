#!/usr/bin/env python3
"""merge_narrative.py -- Fusionne un YAML narrative dans un entity.partial.yaml.

Produit un entity.yaml consolide :
- technical.fields : fusion par nom (fields SQL du partial + libelles/Nature/source du narrative)
- business.role : depuis narrative.business.role_sourced (sinon placeholder)
- business.business_rules : depuis narrative
- technical.main_screens / main_program / module_check : depuis narrative
- meta.a_verifier : union des deux
- meta.sources : depuis narrative

Usage :
  py merge_narrative.py \\
     --entity-partial {OUT}/entity/CLI.partial.yaml \\
     --narrative {OUT}/entity/CLI.narrative.yaml \\
     --output {OUT}/entity/CLI.yaml
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERREUR : pyyaml requis. Installer : py -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def load(p: Path) -> dict:
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _format_fk_note(cr: dict) -> str:
    """Compose une note de validation FK a partir des canaux detectes.

    Canaux possibles (du plus fiable au moins fiable) :
    - Traitement apres (diva_apres) + appel Check_<Entity>_Field_<Field>
    - Masque : f8=<zoom> + table_associee=oui
    - Module Check : procedures Check_<Entity>_Field_<Field>[_Lib]
    """
    parts = []
    da_proc = cr.get("diva_apres_proc")
    calls = cr.get("check_calls_from_screen") or []
    if da_proc and calls:
        # Canal le plus fort : traitement apres saisie appelle le Check
        parts.append(
            f"traitement apres saisie `{da_proc}` appelle "
            f"`{calls[0]}`"
        )
    if cr.get("zoom_code"):
        parts.append(
            f"zoom f8={cr['zoom_code']} + table_associee=oui dans le masque"
        )
    elif cr.get("key_pressed"):
        parts.append(
            f"{cr['key_pressed']} + table_associee=oui dans le masque"
        )
    if not parts and cr.get("check_proc"):
        # Canal 2 seul : procedure Check_<Entity>_Field_<Field> dans le Module Check
        # qui appelle Find_<Table> pour valider la FK. Utilise quand l'entite n'a pas
        # de masque zoom dedie (ex: C4, C5 en COMPTA).
        parts.append(
            f"Module Check appelle `Find_{cr.get('target_table_real','?')}` "
            f"dans `{cr['check_proc']}`"
        )
    if not parts:
        parts.append("confirmee via les sources X.13")
    return "FK confirmee : " + " ; ".join(parts)


def merge_fields(partial_fields: list, narrative_fields: list,
                 dhsd_lookup: dict | None = None,
                 dhsd_source_file: str | None = None,
                 field_checks: dict | None = None) -> list:
    """Enrichit les fields du partial avec libelles/Natures/checks.

    Sources d'enrichissement, par ordre de priorite :
    1. narrative_fields : champs de la section [CHAMPS] de la table (25 pour CLI)
    2. dhsd_lookup      : TOUS les [CHAMP] globaux du .dhsd (C2)
    3. field_checks     : procedures Check_Entity_Field_* par champ (C3)
    """
    narr_by_name = {f["name"].lower(): f for f in narrative_fields}
    out = []
    from pathlib import Path as _Path
    src_basename = _Path(dhsd_source_file).name if dhsd_source_file else None
    for f in partial_fields:
        enriched = dict(f)
        name_lc = f["name"].lower()
        nf = narr_by_name.get(name_lc)
        if nf:
            enriched["label"] = nf.get("label") or enriched.get("label")
            narr_nat = nf.get("nature")
            if narr_nat and narr_nat != "?":
                enriched["nature"] = narr_nat
            if nf.get("source"):
                enriched["source"] = nf["source"]
        # C2 : si pas de libelle trouve mais present dans dhsd_lookup global
        if not enriched.get("label") and dhsd_lookup:
            gf = dhsd_lookup.get(name_lc)
            if gf:
                enriched["label"] = gf.get("description") or enriched.get("label")
                gf_nat = gf.get("nature")
                if gf_nat and gf_nat != "?" and (enriched.get("nature", "").startswith("?")
                                                  or not enriched.get("nature")):
                    enriched["nature"] = gf_nat
                if src_basename and gf.get("source_line"):
                    enriched["source"] = f"{src_basename}:{gf['source_line']}"
        # C3 : si des procedures Check existent pour ce champ, les mentionner
        if field_checks:
            checks = field_checks.get(f["name"].upper())
            if checks:
                enriched["checks"] = checks
        out.append(enriched)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entity-partial", required=True)
    ap.add_argument("--narrative", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    partial = load(Path(args.entity_partial))
    narr = load(Path(args.narrative))

    entity = dict(partial)
    # Retirer les placeholders inline pose par extract_entity.py :
    # le narratif sourcé X.13 les remplace ; les vraies incertitudes
    # partent en meta.a_verifier (non inline dans business.*).
    partial_biz = entity.get("business") or {}
    for k, v in list(partial_biz.items()):
        if isinstance(v, str) and v.strip().startswith("[A ENRICHIR]"):
            partial_biz[k] = None

    # --- business ---
    biz = entity.setdefault("business", {})
    narr_biz = narr.get("business", {})
    if narr_biz.get("role_sourced"):
        biz["role"] = narr_biz["role_sourced"]
    if narr_biz.get("object_description"):
        biz["object_description"] = narr_biz["object_description"]
    if narr_biz.get("main_screen_name"):
        biz.setdefault("main_screen_name", narr_biz["main_screen_name"])
    if narr_biz.get("business_rules"):
        existing = biz.get("business_rules") or []
        if not isinstance(existing, list):
            existing = [existing]
        biz["business_rules"] = existing + list(narr_biz["business_rules"])
    if narr_biz.get("codified_fields"):
        biz["codified_fields"] = narr_biz["codified_fields"]
    if narr_biz.get("business_rules_from_code"):
        biz["business_rules_from_code"] = narr_biz["business_rules_from_code"]
    # criticity : si narrative l'a deduite, l'adopter (remplace [A ENRICHIR])
    if narr_biz.get("criticality"):
        biz["criticality"] = narr_biz["criticality"]
        if narr_biz.get("criticality_justification"):
            biz["criticality_justification"] = narr_biz["criticality_justification"]
    elif isinstance(biz.get("criticality"), str) and biz["criticality"].startswith("[A ENRICHIR]"):
        biz["criticality"] = None

    # --- technical ---
    tech = entity.setdefault("technical", {})
    narr_tech = narr.get("technical", {})
    # Fields : fusion par nom (section [CHAMPS] + [CHAMP] globaux + checks procs)
    if narr_tech.get("fields_enriched") and tech.get("fields"):
        field_checks = (narr_tech.get("field_check_procedures") or {}).get("by_field")
        tech["fields"] = merge_fields(
            tech["fields"],
            narr_tech["fields_enriched"],
            dhsd_lookup=narr_tech.get("_dhsd_champs_lookup"),
            dhsd_source_file=narr_tech.get("_dhsd_source_file"),
            field_checks=field_checks,
        )
    # Copier les metadata X.13 du narrative (exclus les champs techniques internes
    # commençant par "_" qui sont des lookups utilises au merge)
    for key in (
        "dictionary_source", "main_screens", "main_screen_info",
        "main_program", "main_program_info",
        "module_check", "module_check_info",
        "object_api", "business_constants",
        "field_check_procedures", "object_lifecycle_procedures",
        "ce_analysis",
    ):
        if narr_tech.get(key):
            tech[key] = narr_tech[key]
    # Nettoyer les placeholders inline sur dictionary_source (cas [A VERIFIER])
    if isinstance(tech.get("dictionary_source"), str) and tech["dictionary_source"].startswith("[A VERIFIER]"):
        tech["dictionary_source"] = None
    # record_name (nom du Record DIVA) : on conserve si pas ecrase
    if narr_tech.get("fields_enriched"):
        tech["field_count_dict"] = len(narr_tech["fields_enriched"])

    # --- schema ---
    schema = entity.setdefault("schema", {})
    narr_schema = narr.get("schema", {})
    if narr_schema.get("primary_key_business"):
        # Cle primaire metier prime sur CLI_ID (cle SQL technique)
        schema["primary_key"] = narr_schema["primary_key_business"]
        schema["primary_key_source"] = narr_schema.get("required_fields_source")
        # Preserver la PK SQL technique dans un champ separe pour audit
        sql_pk = (partial.get("schema") or {}).get("primary_key")
        if sql_pk and sql_pk != narr_schema["primary_key_business"]:
            schema["primary_key_sql_technical"] = sql_pk
    if narr_schema.get("required_fields"):
        schema["required_fields"] = narr_schema["required_fields"]
    # Relations confirmees (table_associee=oui dans le masque) :
    # ce sont des bindings zoom reels, source de verite par rapport aux heuristiques.
    confirmed = narr_schema.get("confirmed_relations") or []
    # Check procs par champ : deuxieme source de verite pour confirmer une FK
    # (un champ qui a Check_<Entity>_Field_<Champ>_Lib est toujours une FK
    # vers une table codifiee, meme s'il n'apparait pas dans table_associee)
    field_checks = (narr_tech.get("field_check_procedures") or {}).get("by_field") or {}

    # Champs de partitionnement multi-tenant/multi-etablissement (pas des FK classiques)
    PARTITION_FIELDS = {"DOS", "ETB"}

    if confirmed or field_checks:
        existing_heur = schema.get("relations") or []
        confirmed_by_field = {
            r["source_field"].upper(): r for r in confirmed if r.get("source_field")
        }
        resolved = []
        seen_targets = set()
        # 1. Traiter chaque heuristique : promouvoir via confirmed ou via Check_Field, sinon reclasser
        for h in existing_heur:
            sf = (h.get("source_field") or "").upper()
            if sf in PARTITION_FIELDS:
                # Partitionnement : ce n'est PAS une FK classique
                resolved.append({
                    **{k: v for k, v in h.items() if k not in ("business_note", "type")},
                    "type": "partitioning",
                    "business_note": (
                        f"Champ de partitionnement {sf} (multi-tenant). "
                        f"Pas une FK metier : toute table DAV porte ce champ pour l'isolation par dossier/etablissement."
                    ),
                })
                continue
            if sf and sf in confirmed_by_field:
                cr = confirmed_by_field.pop(sf)
                # Privilegier la VRAIE table cible (extraite de Find_<Table> dans
                # Check_Field) plutot que le nom du champ. Fallback : target_table_hint.
                target = (cr.get("target_table_real") or cr["target_table_hint"]).upper()
                target_label = cr.get("target_table_label")
                resolved.append({
                    "source_entity": cr["source_entity"],
                    "target_entity": target,
                    "target_entity_label": target_label,
                    "type": "fk",
                    "cardinality": "N-1",
                    "source_field": cr["source_field"],
                    "zoom_code": cr.get("zoom_code"),
                    "key_pressed": cr.get("key_pressed"),
                    "diva_apres_proc": cr.get("diva_apres_proc"),
                    "check_calls_from_screen": cr.get("check_calls_from_screen"),
                    "source": cr["source"],
                    "business_note": _format_fk_note(cr),
                })
                seen_targets.add((cr["source_field"].upper(), target))
            elif sf and sf in field_checks:
                # Pas confirmee par masque mais confirmee par Module Check (Check_Field procs)
                procs = field_checks[sf]
                resolved.append({
                    **{k: v for k, v in h.items() if k not in ("business_note",)},
                    "business_note": (
                        f"FK confirmee via {len(procs)} procedure(s) Check_<Entity>_Field_* "
                        f"du Module Check : {', '.join(procs[:3])}"
                    ),
                    "checks": procs,
                })
                seen_targets.add((sf, (h.get("target_entity") or "").upper()))
            else:
                # Pas de confirmation : supprimer cette relation (evite les [A VERIFIER]
                # qui fatiguent le lecteur). Tracer la suppression dans meta.a_verifier.
                meta.setdefault("_dropped_heuristic_relations", []).append({
                    "source_field": sf,
                    "target_was": h.get("target_entity"),
                    "reason": "Aucune confirmation dans masque ni Module Check",
                })
        # 2. Ajouter les confirmed qui n'avaient pas d'heuristique
        for cr in confirmed_by_field.values():
            target = (cr.get("target_table_real") or cr["target_table_hint"]).upper()
            target_label = cr.get("target_table_label")
            key = (cr["source_field"].upper(), target)
            if key in seen_targets:
                continue
            seen_targets.add(key)
            resolved.append({
                "source_entity": cr["source_entity"],
                "target_entity": target,
                "target_entity_label": target_label,
                "type": "fk",
                "cardinality": "N-1",
                "source_field": cr["source_field"],
                "zoom_code": cr.get("zoom_code"),
                "key_pressed": cr.get("key_pressed"),
                "diva_apres_proc": cr.get("diva_apres_proc"),
                "check_calls_from_screen": cr.get("check_calls_from_screen"),
                "source": cr["source"],
                "business_note": _format_fk_note(cr),
            })
        schema["relations"] = resolved

    # relations hints (seulement si pas deja renseigne)
    hints = narr.get("relations_hints") or []
    if hints and not schema.get("relations_hints"):
        schema["relations_hints"] = hints

    # --- meta ---
    meta = entity.setdefault("meta", {})
    narr_meta = narr.get("meta", {})
    # Union des a_verifier, exclure TOUS les items deja resolus par le narratif ou l'extraction :
    # regle : ne garder que ce qui necessite vraiment une validation humaine non deductible
    # depuis X.13 (ex: appreciations subjectives, exemples metier a rediger).
    RESOLVED_PATTERNS = (
        "Enrichir section business",
        "Corriger les Natures marquees",
        "Valider primary_key",
        "Libelles de champs non sourcables",
        "Definir layer par champ",  # Heuristique layer deja appliquee : on valide
        "Enrichir description et business_context",
        "Completer la liste des entites",
        "Valider la coherence bases <-> entities",
    )
    combined = list(meta.get("a_verifier") or []) + list(narr_meta.get("a_verifier") or [])
    meta["a_verifier"] = sorted({
        item for item in combined
        if not any(pat in item for pat in RESOLVED_PATTERNS)
    })
    # Sources citees
    if narr_meta.get("sources"):
        meta["sources_x13"] = narr_meta["sources"]
    meta["last_reviewed"] = narr_meta.get("last_reviewed", meta.get("last_reviewed"))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(entity, f, allow_unicode=True, sort_keys=False, width=120)

    summary = {
        "output": str(out_path),
        "fields_count": len(tech.get("fields", [])),
        "fields_with_label": sum(
            1 for f in tech.get("fields", [])
            if f.get("label") and f.get("label") != f["name"]
        ),
        "business_rules_count": len(biz.get("business_rules") or []),
        "a_verifier_count": len(meta["a_verifier"]),
        "sources_x13_count": len(meta.get("sources_x13", [])),
        "has_main_screen": bool(tech.get("main_screen_info")),
        "has_module_check": bool(tech.get("module_check_info")),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
