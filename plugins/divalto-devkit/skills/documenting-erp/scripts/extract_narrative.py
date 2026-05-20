#!/usr/bin/env python3
"""extract_narrative.py -- Extrait le narratif metier d'une entite depuis X.13.

Produit un YAML partiel qui alimente les sections `business.*` et `technical.*`
(libelles champs, Natures reelles, ecran principal, modules references) avec
des citations `fichier:ligne` X.13.

Sources consommees (toutes optionnelles, passees en CLI) :
  --dict           : .dhsd pour libelles + Natures (source de verite champs)
  --main-screen    : .dhsf ecran principal (libelle, onglets, pages, zooms)
  --main-module    : .dhsp/.dhsq module principal (dependances)
  --module-check   : .dhsp Module Check (regles metier)

Regle de citation stricte : chaque affirmation produite porte la reference
`fichier:ligne` de sa source. Les elements non sourcables sont listes dans
`meta.a_verifier` avec une explication.

Usage :
  py extract_narrative.py --entity CLI --module DAV --base GTFPCF \\
     --dict {CHEMIN_FICHIERS}/gtfdd.dhsd \\
     --main-screen {CHEMIN_ERP_STANDARD}/Achat-Vente/source/Dav/gtez021_sql.dhsf \\
     --main-module {CHEMIN_ERP_STANDARD}/Achat-Vente/source/Dav/gttz021_sql.dhsp \\
     --module-check {CHEMIN_ERP_STANDARD}/Achat-Vente/source/Dav/gttmchkcli.dhsp \\
     --output {REPERTOIRE_SORTIE}/doc-erp/DAV/entity/CLI.narrative.yaml
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERREUR : pyyaml requis. Installer : py -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# Vendored module local (skill autonome, pas d'import inter-skill)
sys.path.insert(0, str(Path(__file__).parent))
from _sources_parser import (
    parse_dhsd_table,
    parse_dhsf_header,
    parse_dhsp_module,
    parse_dhsf_choix,
    parse_dhsf_f8_bindings,
    lookup_champ_label,
    extract_check_procedures_by_field,
    extract_check_procedure_targets,
    lookup_table_labels,
    extract_diva_apres_fk_bindings,
    extract_procedure_docstrings,
    parse_choix_values_json,
    analyze_ce_fields,
)


def derive_criticality(screen_info: dict | None,
                        module_info: dict | None,
                        mchk_info: dict | None) -> tuple[str, str]:
    """Derive la criticite metier (core/standard/peripheral) depuis les signaux X.13.

    Retourne (criticality, justification_sourcée).
    Heuristique assumee, basee sur la taille/complexite du code ecosysteme.
    """
    score = 0
    reasons = []
    if screen_info:
        pages = screen_info.get("pages_count") or 0
        f8 = screen_info.get("f8_zooms_count") or 0
        if pages >= 30:
            score += 2
            reasons.append(f"ecran {pages} pages")
        elif pages >= 10:
            score += 1
            reasons.append(f"ecran {pages} pages")
        if f8 >= 100:
            score += 2
            reasons.append(f"{f8} zooms F8")
        elif f8 >= 30:
            score += 1
            reasons.append(f"{f8} zooms F8")
    if mchk_info:
        size = mchk_info.get("size_chars") or 0
        procs = mchk_info.get("procedures_public_count") or 0
        kb = size // 1024
        if kb >= 100:
            score += 2
            reasons.append(f"Module Check {kb} Ko")
        elif kb >= 30:
            score += 1
            reasons.append(f"Module Check {kb} Ko")
        if procs >= 100:
            score += 2
            reasons.append(f"{procs} procedures publiques")
        elif procs >= 30:
            score += 1
            reasons.append(f"{procs} procedures publiques")
    if module_info:
        mods = module_info.get("modules_referenced_count") or 0
        if mods >= 15:
            score += 1
            reasons.append(f"{mods} modules references")

    if score >= 5:
        criticality = "core"
    elif score >= 2:
        criticality = "standard"
    else:
        criticality = "peripheral"
    justification = f"criticite={criticality} (score {score}) : " + ", ".join(reasons)
    return criticality, justification


def short_source(path: str, line: int | None) -> str:
    """Formate une citation `<nom_fichier>:<ligne>` lisible (on garde le basename)."""
    name = Path(path).name
    return f"{name}:{line}" if line else name


def build_narrative(args) -> dict:
    out: dict = {
        "kind": "entity-narrative",
        "entity": args.entity,
        "module": args.module,
        "base": args.base,
        "business": {},
        "schema": {},
        "technical": {},
        "relations_hints": [],
        "meta": {
            "last_reviewed": date.today().isoformat(),
            "reviewed_by": "extract_narrative.py (auto X.13)",
            "a_verifier": [],
            "sources": [],
        },
    }
    a_verifier = out["meta"]["a_verifier"]
    sources_cited = out["meta"]["sources"]

    # ----------------------------------------------------------
    # 1. Dict .dhsd : libelles + Natures reels (remplace heuristique)
    # ----------------------------------------------------------
    fields_real: list[dict] = []
    all_champs_lookup: dict = {}
    if args.dict:
        dict_path = Path(args.dict)
        if dict_path.exists():
            table_def = parse_dhsd_table(dict_path, args.entity)
            if table_def:
                all_champs_lookup = table_def.get("_all_champs_lookup") or {}
                for champ in table_def["champs"]:
                    entry = {
                        "name": champ["name"],
                        "nature": champ["nature"],
                        "label": champ["description"],
                    }
                    if champ.get("source_line"):
                        entry["source"] = short_source(dict_path, champ["source_line"])
                    fields_real.append(entry)
                out["technical"]["dictionary_source"] = dict_path.name
                out["technical"]["fields_enriched"] = fields_real
                out["technical"]["field_count_dict"] = len(fields_real)
                # Pour C2 : exposer le lookup complet au merge pour enrichir les
                # 241 champs SQL (pas seulement les 25 de la section [CHAMPS])
                if all_champs_lookup:
                    out["technical"]["_dhsd_champs_lookup"] = {
                        k: v for k, v in all_champs_lookup.items()
                        if k == k.lower()  # une seule indexation lowercase pour eviter doublons
                    }
                    out["technical"]["_dhsd_source_file"] = str(dict_path)
                sources_cited.append({
                    "type": "dhsd",
                    "path": str(dict_path),
                    "section_line": table_def["source_line"],
                    "extracted": f"Table {args.entity} ({len(fields_real)} champs section [CHAMPS]) + "
                                 f"{len(all_champs_lookup)//2} [CHAMP] globaux indexes",
                })
            else:
                a_verifier.append(
                    f"Table {args.entity} introuvable dans {dict_path.name} "
                    f"(casse ou alias different ?)"
                )
        else:
            a_verifier.append(f"Dictionnaire absent : {dict_path}")

    # ----------------------------------------------------------
    # Resolution VRAIE table cible FK (independante du masque) :
    # parcourt le Module Check, pour chaque Check_<Entity>_Field_<Field>
    # extrait le Find_<Table>(...) et le libelle de la table via le .dhsd.
    # Ce canal fonctionne SANS masque (important pour les entites comme C4/C5
    # qui n'ont pas de zoom .dhsf dedie mais ont un Module Check complet).
    # ----------------------------------------------------------
    target_by_field: dict = {}
    target_labels: dict = {}
    _mchk_p = Path(args.module_check) if args.module_check else None
    if _mchk_p and _mchk_p.exists():
        target_by_field = extract_check_procedure_targets(_mchk_p, args.entity)
    _dict_p = Path(args.dict) if args.dict else None
    if target_by_field and _dict_p and _dict_p.exists():
        target_labels = lookup_table_labels(_dict_p, list(target_by_field.values()))

    def _target_info(field_name: str, fallback_hint: str):
        """Retourne (target_table_real, target_label) en privilegiant Find_<Table>."""
        t = target_by_field.get(field_name.upper())
        if t:
            return t, target_labels.get(t.upper())
        return fallback_hint, None

    # ----------------------------------------------------------
    # 2. Ecran principal .dhsf : narratif structurel + champs codifies
    # ----------------------------------------------------------
    if args.main_screen:
        screen_path = Path(args.main_screen)
        if screen_path.exists():
            info = parse_dhsf_header(screen_path)
            out["business"]["main_screen_name"] = info.get("libelle")
            out["technical"]["main_screens"] = [screen_path.name]
            out["technical"]["main_screen_info"] = {
                "libelle": info["libelle"],
                "onglets": info["onglets"],
                "pages_count": info["pages_count"],
                "f8_zooms_count": info["f8_count"],
                "date_modification": info["date_modification"],
                "source": short_source(screen_path, None),
            }
            # Tables co-utilisees = relations probables
            for rec in info["enregistrements"]:
                if rec["table"].upper() != args.entity.upper():
                    out["relations_hints"].append({
                        "source_entity": args.entity,
                        "target_table": rec["table"].upper(),
                        "relation_type": "co-used-in-screen",
                        "alias_in_screen": rec["alias"],
                        "source": short_source(screen_path, None),
                    })
            # Champs codifies (listes de choix) -- nettoyer les titres "#tbl..."
            # qui sont des cles de traduction, garder l'info-bulle
            choix_list = parse_dhsf_choix(screen_path)
            # Lire les valeurs concretes depuis le .json du dict_file s'il existe
            choix_values_by_id = {}
            if args.choix_json:
                choix_values_by_id = parse_choix_values_json(args.choix_json)
            if choix_list:
                codified = []
                for c in choix_list:
                    entry = {
                        "choix_id": c["choix_id"],
                        "dict_file": c["dict_file"],
                        "titre": c["titre"] if not c["titre"].startswith("#") else "",
                        "info_bulle": c["info_bulle"],
                        "source": short_source(screen_path, c["line"]),
                    }
                    # D1 resolu : injecter les valeurs + type multichoix + lookup/extern_id.
                    choix_meta = choix_values_by_id.get(c["choix_id"])
                    if choix_meta:
                        # Type multichoix (1=liste, 3=lookup, 4=identifiant externe)
                        if choix_meta.get("type"):
                            entry["choix_type"] = choix_meta["type"]
                        if choix_meta.get("values"):
                            entry["values"] = choix_meta["values"]
                        if choix_meta.get("lookup"):
                            entry["lookup"] = choix_meta["lookup"]
                        if choix_meta.get("extern_id"):
                            entry["extern_id"] = choix_meta["extern_id"]
                        entry["values_source"] = Path(args.choix_json).name
                    codified.append(entry)
                out["business"]["codified_fields"] = codified

            # Relations confirmees via table_associee=oui + donnee=... + f8=...
            # (remplace l'heuristique par nom de champ quand les bindings existent)
            f8_bindings = parse_dhsf_f8_bindings(screen_path)
            # Canal plus fiable : diva_apres + appel Check_<Entity>_Field_* dans la proc
            # (chaine complete : masque -> traitement apres saisie -> validation objet metier)
            diva_apres_bindings = extract_diva_apres_fk_bindings(screen_path, args.entity)
            diva_by_field = {b["field_name"]: b for b in diva_apres_bindings}

            # Fusion : enrichir chaque confirmed_relation avec le diva_apres + check_calls
            # + vraie table cible + libelle.
            f8_fields = set()
            confirmed = []
            for b in f8_bindings:
                f8_fields.add(b["field_name"])
                target_real, target_label = _target_info(b["field_name"], b["target_table_hint"])
                rel = {
                    "source_entity": args.entity,
                    "source_field": b["field_name"],
                    "target_table_hint": b["target_table_hint"],
                    "target_table_real": target_real,
                    "target_table_label": target_label,
                    "zoom_code": b["zoom_code"],
                    "key_pressed": b["key_pressed"],
                    "source": short_source(screen_path, b["line"]),
                }
                da = diva_by_field.get(b["field_name"])
                if da:
                    rel["diva_apres_proc"] = da["proc_name"]
                    rel["check_calls_from_screen"] = da["check_calls"]
                confirmed.append(rel)
            # Ajouter les FK confirmees UNIQUEMENT par diva_apres (pas de f8)
            # pour couvrir les champs sans zoom standard mais avec validation objet metier
            for fname, da in diva_by_field.items():
                if fname in f8_fields:
                    continue
                target_real, target_label = _target_info(fname, fname)
                confirmed.append({
                    "source_entity": args.entity,
                    "source_field": fname,
                    "target_table_hint": fname,
                    "target_table_real": target_real,
                    "target_table_label": target_label,
                    "zoom_code": None,
                    "key_pressed": None,
                    "diva_apres_proc": da["proc_name"],
                    "check_calls_from_screen": da["check_calls"],
                    "source": short_source(screen_path, da.get("line")),
                })
            if confirmed:
                out["schema"]["confirmed_relations"] = confirmed
            sources_cited.append({
                "type": "dhsf",
                "path": str(screen_path),
                "extracted": f"Ecran '{info['libelle']}' ({info['pages_count']} pages, "
                             f"{len(info['onglets'])} onglets, "
                             f"{len(choix_list)} champs codifies)",
            })
        else:
            a_verifier.append(f"Ecran principal absent : {screen_path}")

    # ----------------------------------------------------------
    # 2bis. FK confirmees via Module Check UNIQUEMENT (canal 2 autonome).
    # Utile quand aucun masque .dhsf n'expose l'entite (ex: C4, C5 en COMPTA)
    # ou quand le masque ne couvre pas tous les champs FK du code metier.
    # Injecte dans confirmed_relations les champs present dans target_by_field
    # (extrait du Module Check via Find_<Table>) non couverts par f8/diva_apres.
    # ----------------------------------------------------------
    if target_by_field:
        existing = out["schema"].get("confirmed_relations") or []
        covered = {r["source_field"].upper() for r in existing if r.get("source_field")}
        for fname, target in target_by_field.items():
            if fname in covered:
                continue
            existing.append({
                "source_entity": args.entity,
                "source_field": fname,
                "target_table_hint": fname,
                "target_table_real": target,
                "target_table_label": target_labels.get(target.upper()),
                "zoom_code": None,
                "key_pressed": None,
                "source": short_source(_mchk_p, None) if _mchk_p else None,
                "check_proc": f"Check_{args.entity}_Field_{fname.capitalize()}",
            })
        if existing:
            out["schema"]["confirmed_relations"] = existing

    # ----------------------------------------------------------
    # 3. Module principal .dhsp/.dhsq : dependances
    # ----------------------------------------------------------
    if args.main_module:
        mod_path = Path(args.main_module)
        if mod_path.exists():
            info = parse_dhsp_module(mod_path)
            out["technical"]["main_program"] = mod_path.name
            out["technical"]["main_program_info"] = {
                "size_chars": info["size_chars"],
                "modules_referenced_count": len(info["modules_referenced"]),
                "modules_referenced": info["modules_referenced"][:20],
                "source": short_source(mod_path, None),
            }
            sources_cited.append({
                "type": "dhsp",
                "path": str(mod_path),
                "extracted": f"Module principal ({info['size_chars']} chars, "
                             f"{len(info['modules_referenced'])} modules ref.)",
            })
        else:
            a_verifier.append(f"Module principal absent : {mod_path}")

    # ----------------------------------------------------------
    # 4. Module Check .dhsp : objet metier (cle metier, constantes, procedures publiques)
    # ----------------------------------------------------------
    if args.module_check:
        mchk_path = Path(args.module_check)
        if mchk_path.exists():
            info = parse_dhsp_module(mchk_path)
            mchk_modcount = len(info["modules_referenced"])
            out["technical"]["module_check"] = mchk_path.name
            out["technical"]["module_check_info"] = {
                "size_chars": info["size_chars"],
                "modules_referenced_count": mchk_modcount,
                "procedures_public_count": len(info["procedures_public"]),
                "source": short_source(mchk_path, None),
            }

            # Description metier : entete du module
            if info["header_description"]:
                out["business"]["object_description"] = {
                    "text": info["header_description"],
                    "source": short_source(mchk_path, None),
                }

            # Cle primaire metier + champs obligatoires
            if info["field_names_min"]:
                fnmin = info["field_names_min"]
                fields_min = [f.strip() for f in fnmin.split(";") if f.strip()]
                # Cle metier = 2 premiers champs (convention Divalto : Dos + cle_fonctionnelle)
                if len(fields_min) >= 2:
                    out["schema"]["primary_key_business"] = fields_min[:2]
                out["schema"]["required_fields"] = fields_min
                out["schema"]["required_fields_source"] = short_source(
                    mchk_path,
                    None,  # ligne exacte disponible via reparsing, futur
                )

            # Procedures publiques de l'objet (API metier)
            if info["procedures_public"]:
                out["technical"]["object_api"] = {
                    "public_procedures": info["procedures_public"],
                    "source": short_source(mchk_path, None),
                }

            # C3 : extraire les Check_<Entity>_Field_<Field> procs
            # -> regles de validation par champ metier
            field_procs = extract_check_procedures_by_field(mchk_path, args.entity)
            if field_procs["by_field"]:
                out["technical"]["field_check_procedures"] = {
                    "by_field": field_procs["by_field"],
                    "source": short_source(mchk_path, None),
                    "count_fields_with_check": len(field_procs["by_field"]),
                }
            if field_procs["global_procedures"]:
                out["technical"]["object_lifecycle_procedures"] = {
                    "procedures": field_procs["global_procedures"],
                    "source": short_source(mchk_path, None),
                }

            # Strategie CE : analyse des drapeaux multi-etats Ce1..CeA
            # (usage via indexes + valeurs observees dans le code).
            # Passe aussi les signaux X.13 permettant l'interpretation metier
            # ulterieure par le LLM (etape 3bis du skill) : commentaire dhsd
            # du champ + constantes C_*Ce<n>* du Module Check + signature idem.
            if args.sql_columns and args.sql_indexes_json:
                try:
                    import json as _json
                    with open(args.sql_columns, encoding="utf-8") as _f:
                        sql_cols = _json.load(_f).get("columns", [])
                    with open(args.sql_indexes_json, encoding="utf-8") as _f:
                        sql_idx = _json.load(_f).get("indexes", [])
                    _dhsd_name = Path(args.dict).name if args.dict else None
                    ce_analysis = analyze_ce_fields(
                        args.entity, sql_cols, sql_idx, mchk_path,
                        dhsd_champs_lookup=all_champs_lookup or None,
                        dhsd_source_name=_dhsd_name,
                        business_constants=info.get("business_constants"),
                    )
                    if ce_analysis:
                        out["technical"]["ce_analysis"] = {
                            "fields": ce_analysis,
                            "source": f"Indexes SQL + {mchk_path.name}",
                            "summary": (
                                f"{sum(1 for c in ce_analysis if c['status']=='actif')} CE actifs, "
                                f"{sum(1 for c in ce_analysis if c['status']=='reserve')} reserves"
                            ),
                        }
                except Exception as _e:
                    a_verifier.append(f"Analyse CE partielle : {_e}")

            # D3 : docstrings des procedures principales (Authorize, Check, Find...)
            docs = extract_procedure_docstrings(mchk_path, args.entity, max_procs=15)
            if docs["procedures_documented"]:
                # Injecter les docstrings en regles metier de haut niveau
                rules_extracted = []
                for proc in docs["procedures_documented"]:
                    desc = proc.get("description", "")
                    if desc and len(desc) > 5:
                        rules_extracted.append({
                            "procedure": proc["name"],
                            "description": desc,
                            "source": short_source(mchk_path, proc["source_line"]),
                        })
                if rules_extracted:
                    out["business"].setdefault("business_rules_from_code", rules_extracted)

            # Constantes metier significatives (filtrer : exclure les techniques)
            biz_consts = [
                c for c in info["business_constants"]
                if not re.search(r'(Code[UI]nique|_Mes_|_ObjNote$)', c["name"], re.IGNORECASE)
            ]
            if biz_consts:
                out["technical"]["business_constants"] = [
                    {
                        "name": c["name"],
                        "value": c["value"],
                        "comment": c["comment"],
                        "source": short_source(mchk_path, c["line"]),
                    }
                    for c in biz_consts[:15]  # top 15 pour lisibilite
                ]

            sources_cited.append({
                "type": "module_check",
                "path": str(mchk_path),
                "extracted": (
                    f"Module Check ({info['size_chars']//1024} Ko, "
                    f"{len(info['procedures_public'])} procedures publiques, "
                    f"{len(info['business_constants'])} constantes)"
                ),
            })
        else:
            a_verifier.append(f"Module Check absent : {mchk_path}")

    # ----------------------------------------------------------
    # 5. Generation narratif derive
    # ----------------------------------------------------------
    parts = []
    screen_info = out["technical"].get("main_screen_info")
    if screen_info:
        parts.append(
            f"Entite manipulee via l'ecran '{screen_info['libelle']}' "
            f"({screen_info['pages_count']} pages, "
            f"{len(screen_info['onglets'])} onglets : {', '.join(screen_info['onglets'])}) "
            f"[{screen_info['source']}]."
        )
    if screen_info and screen_info.get("f8_zooms_count", 0) > 50:
        parts.append(
            f"Nombreux zooms actifs ({screen_info['f8_zooms_count']} touches F8) "
            f"-- entite relieee a de nombreuses autres tables de l'ERP."
        )
    if out["technical"].get("module_check_info"):
        parts.append(
            f"Regles metier portees par le Module Check "
            f"{out['technical']['module_check']} "
            f"({out['technical']['module_check_info']['size_chars']//1024} Ko) "
            f"[{out['technical']['module_check_info']['source']}]."
        )
    if parts:
        out["business"]["role_sourced"] = " ".join(parts)
    else:
        a_verifier.append(
            "Role metier : aucune source X.13 directement exploitable. "
            "A rediger a partir de la connaissance metier du collaborateur."
        )

    # Derivation automatique de la criticity (au lieu d'un placeholder)
    criticality, justif = derive_criticality(
        out["technical"].get("main_screen_info"),
        out["technical"].get("main_program_info"),
        out["technical"].get("module_check_info"),
    )
    out["business"]["criticality"] = criticality
    out["business"]["criticality_justification"] = justif

    if not fields_real:
        a_verifier.append(
            "Libelles de champs non sourcables (.dhsd absent ou table non trouvee). "
            "Les Natures sont deduites heuristiquement depuis le SQL dans extract_entity.py."
        )

    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--entity", required=True, help="Code entite (ex: CLI)")
    ap.add_argument("--module", required=True, help="Code module (ex: DAV)")
    ap.add_argument("--base", required=True, help="Code base (ex: GTFPCF)")
    ap.add_argument("--dict", help="Chemin du .dhsd (pour libelles + Natures)")
    ap.add_argument("--main-screen", help="Chemin du .dhsf principal")
    ap.add_argument("--main-module", help="Chemin du .dhsp/.dhsq module principal")
    ap.add_argument("--module-check", help="Chemin du .dhsp Module Check")
    ap.add_argument("--choix-json", help="Chemin vers le .json des valeurs de listes codifiees (ex: gtfdmc.json)")
    ap.add_argument("--sql-columns", help="Chemin JSON columns de l'entite (pour analyse CE)")
    ap.add_argument("--sql-indexes-json", help="Chemin JSON indexes de l'entite (pour analyse CE)")
    ap.add_argument("--output", required=True, help="Chemin YAML de sortie")
    args = ap.parse_args()

    narrative = build_narrative(args)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(narrative, f, allow_unicode=True, sort_keys=False, width=120)

    summary = {
        "entity": args.entity,
        "output": str(out_path),
        "sources_cited": len(narrative["meta"]["sources"]),
        "fields_enriched": len(narrative["technical"].get("fields_enriched", [])),
        "relations_hints": len(narrative["relations_hints"]),
        "a_verifier_count": len(narrative["meta"]["a_verifier"]),
        "has_role_sourced": bool(narrative["business"].get("role_sourced")),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
