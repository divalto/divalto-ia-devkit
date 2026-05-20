#!/usr/bin/env python3
"""_sources_parser.py -- Parseurs minimaux des sources ERP X.13.

Utilise comme module helper par les scripts d'extraction. Pas d'execution directe.

Fournit 3 parseurs specialises, tous en lecture seule :

- parse_dhsd_table(dict_path, table_name)
    Extrait la definition d'une table dans un .dhsd : liste ordonnee des champs
    avec leur Nature reelle et leur libelle (depuis [CHAMP].Nom).
    Source de verite pour Natures + libelles (remplace l'heuristique SQL).

- parse_dhsf_header(dhsf_path)
    Extrait l'identite d'un masque ecran .dhsf : libelle, onglets, nb de pages,
    enregistrements (alias -> table), nb de zooms F8, date modif.
    Alimente le narratif structurel d'une entite.

- parse_dhsp_module(dhsp_path)
    Extrait des infos globales d'un module .dhsp/.dhsq : taille, modules
    references (Module "xxx.dhop"), Records declares, OverWrittenBy.
    Utile pour reperer les dependances et regles metier.

Encodage source : ISO-8859-1 (standard Divalto). Les fichiers sont gros
(dhsd > 1 Mo, dhsp > 100 Ko) : les parseurs utilisent re.search/re.findall
sur un seul read, pas de parse ligne par ligne.
"""
from __future__ import annotations

import re
from pathlib import Path


# ------------------------------------------------------------------
# Parseur .dhsd
# ------------------------------------------------------------------

def parse_dhsd_table(dict_path: str | Path, table_name: str) -> dict | None:
    """Extrait la definition d'une table et de ses champs depuis un .dhsd.

    Structure reelle observee dans gtfdd.dhsd :
    - `[CHAMP]` (singulier, top-level) : declaration globale d'un champ
      avec sa Nature et son libelle (Nom=NomChamp,Description,1 + Nature=...)
    - `[TABLE]` (top-level) : metadonnees d'une table (Nom=TableName,Desc,1 + Taille)
    - `[CHAMPS] ... [/CHAMPS]` (sous-section qui suit immediatement [TABLE]) :
      liste des champs de la table avec positions, format `Nom=Champ,pos,type,nat,...`

    Retourne un dict ou None si non trouvee.
    """
    path = Path(dict_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()

    # 1. Indexer tous les [CHAMP] globaux avec leur Nature + libelle.
    # Chaque champ est stocke deux fois : par nom exact et par nom minuscule
    # pour permettre le lookup case-insensitive (les noms dans les tables SQL
    # sont souvent en majuscules alors que les [CHAMP] globaux sont en PascalCase).
    champs_by_name: dict[str, dict] = {}
    for m in re.finditer(r"(?m)^\[CHAMP\]\s*$", text):
        start = m.end()
        # trouver la fin du bloc = prochaine section [...]
        next_sec = re.search(r"(?m)^\[", text[start:])
        end = start + next_sec.start() if next_sec else len(text)
        block = text[start:end]
        nom_m = re.search(r"(?m)^\s*Nom=([^,\r\n]+),([^,\r\n]*),1\s*$", block)
        if not nom_m:
            continue
        name = nom_m.group(1).strip()
        desc = nom_m.group(2).strip()
        nat_m = re.search(r"(?m)^\s*Nature=(\S+)\s*$", block)
        line_num = text.count("\n", 0, m.start()) + 1
        entry = {
            "name": name,
            "description": desc,
            "nature": nat_m.group(1) if nat_m else "?",
            "source_line": line_num,
        }
        champs_by_name[name] = entry
        # Indexation supplementaire case-insensitive pour lookup depuis SQL
        lower_key = name.lower()
        if lower_key not in champs_by_name:
            champs_by_name[lower_key] = entry

    # 2. Trouver la section [TABLE] avec Nom=<table_name> (case-insensitive)
    table_info = None
    table_start = None
    for m in re.finditer(r"(?m)^\[TABLE\]\s*$", text):
        start = m.end()
        # chercher juste le bloc metadata de la TABLE (jusqu'au prochain [)
        next_sec = re.search(r"(?m)^\[", text[start:])
        meta_end = start + next_sec.start() if next_sec else len(text)
        meta_block = text[start:meta_end]
        nom_m = re.search(r"(?m)^\s*Nom=([^,\r\n]+),([^,\r\n]*),1\s*$", meta_block)
        if not nom_m:
            continue
        name = nom_m.group(1).strip()
        if name.lower() == table_name.lower():
            desc = nom_m.group(2).strip()
            taille_m = re.search(r"(?m)^\s*Taille=(\d+)", meta_block)
            line_num = text.count("\n", 0, m.start()) + 1
            table_info = {
                "table": name,
                "description": desc,
                "size": int(taille_m.group(1)) if taille_m else 0,
                "source_path": str(path),
                "source_line": line_num,
            }
            table_start = start
            break
    if not table_info:
        return None

    # 3. Depuis table_start, chercher [CHAMPS]...[/CHAMPS] SUIVANT
    # (dans le bloc qui suit immediatement la section TABLE)
    after = text[table_start:]
    # borne : prochaine [TABLE] pour ne pas avaler la table suivante
    next_table_m = re.search(r"(?m)^\[TABLE\]\s*$", after)
    scope = after[: next_table_m.start()] if next_table_m else after
    champs_m = re.search(
        r"(?m)^\[CHAMPS\]\s*\n(.*?)\n\[/CHAMPS\]",
        scope,
        re.DOTALL,
    )
    fields_list: list[tuple[str, int]] = []
    if champs_m:
        for line in champs_m.group(1).splitlines():
            # Format : Nom=ChampName,position,type,...
            lm = re.match(r"\s*Nom=([^,\r\n]+),(\d+),", line)
            if lm:
                fields_list.append((lm.group(1).strip(), int(lm.group(2))))

    # 4. Resoudre chaque champ : position + Nature/libelle depuis [CHAMP] global
    resolved = []
    for fn, pos in fields_list:
        if fn == "Filler":
            resolved.append({
                "name": "Filler", "nature": "?", "description": "Bourrage",
                "position": pos, "source_line": None,
            })
            continue
        info = champs_by_name.get(fn)
        if info:
            entry = dict(info)
            entry["position"] = pos
            resolved.append(entry)
        else:
            resolved.append({
                "name": fn, "nature": "?",
                "description": "[champ non trouve dans [CHAMP] global]",
                "position": pos, "source_line": None,
            })
    table_info["champs"] = resolved
    # Exposer le lookup complet des [CHAMP] globaux pour C2 : enrichir
    # TOUS les champs SQL avec leur libelle DIVA, meme ceux absents de [CHAMPS]
    # (cas des zones composites non declarees au niveau table).
    table_info["_all_champs_lookup"] = champs_by_name
    return table_info


def lookup_champ_label(champs_lookup: dict, field_name: str) -> dict | None:
    """Cherche un libelle DIVA pour un champ, en case-insensitive.

    Utile pour enrichir les champs SQL (souvent en MAJ) avec les libelles
    globaux [CHAMP] du .dhsd (en PascalCase).
    """
    if not field_name or not champs_lookup:
        return None
    if field_name in champs_lookup:
        return champs_lookup[field_name]
    lower = field_name.lower()
    if lower in champs_lookup:
        return champs_lookup[lower]
    return None


# ------------------------------------------------------------------
# Parseur .dhsf (masque ecran)
# ------------------------------------------------------------------

def parse_dhsf_header(dhsf_path: str | Path) -> dict:
    """Extrait l'identite structurelle d'un masque .dhsf.

    Retourne un dict :
      {
        "libelle": "...",
        "date_modification": "...",
        "onglets": ["FICHE", "LISTE", ...],
        "pages_count": <int>,
        "enregistrements": [{"dict": "...", "table": "...", "alias": "..."}, ...],
        "f8_count": <int>,
        "type_masque": <int>,
        "source_path": "...",
      }
    """
    path = Path(dhsf_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()

    libelle_m = re.search(r'(?m)^\s*libelle="([^"]+)"', text)
    date_m = re.search(r'(?m)^\s*date_modification="([^"]+)"', text)
    type_m = re.search(r'(?m)^\s*type_masque=(\d+)', text)

    # onglets : blocs [onglet] avec nom="..."
    onglets = re.findall(r'nom="([^"]+)"\s*\n\s*multi_lignes', text)

    # pages
    pages = re.findall(r'(?m)^\[page\]\s*\n\s*numero=(\d+)', text)

    # enregistrements : '<dict>.dhXX',,<table>,<alias>,<size>,<flag>
    records_raw = re.findall(
        r'"([^"\n]+\.(?:dhsd|dhoq|dhsq))"\s*,\s*,\s*(\w+)\s*,\s*(\w+)\s*,',
        text,
    )
    records = [{"dict": d, "table": t, "alias": a} for d, t, a in records_raw]

    # zooms F8
    f8_count = len(re.findall(r'(?m)^\s*f8\s*=', text))

    return {
        "libelle": libelle_m.group(1) if libelle_m else None,
        "date_modification": date_m.group(1) if date_m else None,
        "type_masque": int(type_m.group(1)) if type_m else None,
        "onglets": onglets,
        "pages_count": len(pages),
        "enregistrements": records,
        "f8_count": f8_count,
        "source_path": str(path),
    }


# ------------------------------------------------------------------
# Parseur .dhsp / .dhsq (module source)
# ------------------------------------------------------------------

def extract_procedure_docstrings(dhsp_path: str | Path, entity_code: str,
                                   max_procs: int = 20) -> dict:
    """Extrait les commentaires `;*` qui precedent les procedures publiques.

    Convention Divalto : les procedures sont souvent precedees d'un bloc
    de commentaires de type `;* description`. Ce bloc sert de docstring
    fonctionnel de la procedure.

    On cible en priorite les procedures les plus significatives (Authorize*,
    Check_<Entity>, Find_<Entity>_*, Delete/Insert/Update principales).

    Retourne : {
      "procedures_documented": [
        {"name": "...", "role": "authorize|check|lifecycle", "lines": [...]},
        ...
      ]
    }
    """
    path = Path(dhsp_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()
    lines = text.splitlines()

    # Regex : declaration de procedure publique
    proc_re = re.compile(
        r'^(?:\s*Public\s+)?(?:[Ff]unction|[Pp]rocedure)\s+\w+\s+(\w+)\s*\(',
    )
    # Prioriser les procedures interessantes pour doc
    ent = entity_code.upper()
    priority_patterns = [
        re.compile(rf'^Authorize_{ent}(_\w+)?$', re.IGNORECASE),
        re.compile(rf'^Check_{ent}$', re.IGNORECASE),
        re.compile(rf'^Find_{ent}_\w+$', re.IGNORECASE),
        re.compile(rf'^(Post|Pre)(Ins|Upd|Del)_{ent}', re.IGNORECASE),
        re.compile(rf'^Get_{ent}_\w+$', re.IGNORECASE),
    ]

    def is_priority(proc_name: str) -> bool:
        return any(p.match(proc_name) for p in priority_patterns)

    documented = []
    for i, line in enumerate(lines):
        m = proc_re.match(line)
        if not m:
            continue
        proc_name = m.group(1)
        if not is_priority(proc_name):
            continue
        # Remonter pour capter les lignes ';*' qui precedent
        comment_lines = []
        j = i - 1
        while j >= 0:
            prev = lines[j].strip()
            if prev == "" or prev.startswith(";*"):
                if prev.startswith(";*"):
                    clean = prev.lstrip(";*").strip()
                    if clean:
                        comment_lines.insert(0, clean)
                elif comment_lines:
                    # ligne vide apres des commentaires = fin du bloc
                    break
                j -= 1
            else:
                break
        if comment_lines or proc_name.startswith(("Check_", "Authorize_", "Find_", "Post", "Pre")):
            documented.append({
                "name": proc_name,
                "description": " ".join(comment_lines) if comment_lines else "",
                "source_line": i + 1,
            })
            if len(documented) >= max_procs:
                break
    return {"procedures_documented": documented}


def analyze_ce_fields(entity_code: str, fields_sql: list,
                       indexes_sql: list, mchk_path: str | Path | None = None,
                       dhsd_champs_lookup: dict | None = None,
                       dhsd_source_name: str | None = None,
                       business_constants: list | None = None) -> list:
    """Analyse les champs CE1..CEA (codes enregistrement / drapeaux multi-etats).

    Strategie Divalto :
    - Ce1..CeA sont des drapeaux char(1) partageant la premiere zone de la table
    - Tous ne sont pas utilises : certains sont actifs, d'autres reserves pour extensions
    - Utilisation detectee via : presence dans un index, valeurs observees dans code

    Params optionnels pour enrichissement des signaux (ajoutes pour interpretation
    metier par le LLM en etape 3bis du skill) :
    - dhsd_champs_lookup : dict des [CHAMP] globaux du .dhsd
      (sortie de parse_dhsd_table via _all_champs_lookup)
    - dhsd_source_name   : nom court du .dhsd pour citation (ex: "gtfdd.dhsd")
    - business_constants : constantes C_* extraites par parse_dhsp_module
      (utilisees pour filtrer les constantes nommees CeX)

    Retourne : [
      {
        "name": "CE1",
        "status": "actif" | "reserve" | "inutilise",
        "role_infere": "drapeau principal" | "classement stat" | "reserve",
        "indexes": ["INDEX_B_CLI", ...],
        "index_count": <int>,
        "values_observed_in_mchk": ["0", "1", "3"],
        "dhsd_comment": "Code enregistrement" | None,  # commentaire [CHAMP] Ce<n>
        "dhsd_source": "gtfdd.dhsd:4589" | None,
        "mchk_constants": [{name, value, comment, source}, ...],
        "description_metier": "..." | None,           # fixe pour reserves, rempli par LLM pour actifs
        "description_metier_source": "..." | None,
        "description_metier_signature": "ab12cd34",   # 8-hex, empreinte des signaux (idempotence)
      },
      ...
    ]
    """
    import re as _re
    # 1. Collecter les CE dans les champs (uniquement ceux qui existent)
    ce_fields = [f for f in fields_sql
                 if _re.match(r'^CE[1-9A]$', (f.get("name") or "").upper())]
    if not ce_fields:
        return []

    # 2. Indexer les indexes SQL par champ CE + memoriser les co-colonnes
    #    (pour inferer un role discriminant : STAT_* -> stats, TIERSGRP -> groupement...)
    index_by_ce: dict[str, list] = {}
    co_cols_by_ce: dict[str, set] = {}
    PARTITION_OR_PK = {"DOS", "ETB", "TIERS", "CLI_ID", "FOU_ID", "ART_ID", "SOC_ID"}
    for idx in indexes_sql or []:
        cols = idx.get("columns", []) or idx.get("fields", [])
        ce_in_idx = [c.upper() for c in cols if _re.match(r'^CE[1-9A]$', c.upper())]
        other_cols = {
            c.upper() for c in cols
            if c.upper() not in PARTITION_OR_PK
            and not _re.match(r'^CE[1-9A]$', c.upper())
        }
        for ce_col in ce_in_idx:
            index_by_ce.setdefault(ce_col, []).append(idx["name"])
            co_cols_by_ce.setdefault(ce_col, set()).update(other_cols)

    # 3. Valeurs observees dans le Module Check
    #    Correction bug : on extrait tous les LITTERAUX quotes d'une ligne qui
    #    mentionne CLI.CeX, pour capter Condition(..., '1', ' ') et autres
    #    expressions indirectes. Les guillemets sont desormais OBLIGATOIRES,
    #    ce qui elimine les faux positifs (e.g. 'C' de Condition(...) capture
    #    a tort avec un regex qui rendait les guillemets optionnels).
    values_by_ce: dict[str, set] = {}
    assign_count: dict[str, int] = {}
    compare_count: dict[str, int] = {}
    ref_count: dict[str, int] = {}
    # Extraction complementaire pour le SENS metier des drapeaux :
    # - activation_rule : expression de la Condition (...) quand CeX est assigne
    #   a Condition(<expr>, '1', ' ') -- typique des drapeaux derives de donnees
    # - fixed_value    : litteral affecte sans Condition (ex: CLI.Ce1 = '3')
    activation_rule_by_ce: dict[str, str] = {}
    fixed_value_by_ce: dict[str, str] = {}

    def _extract_condition_first_arg(text: str, start: int) -> str | None:
        """A partir de la position apres 'Condition(', recupere le 1er argument
        en respectant les parentheses imbriquees (arret a la virgule au niveau 0)."""
        depth = 1
        i = start
        while i < len(text):
            c = text[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return None
            elif c == ',' and depth == 1:
                expr = text[start:i].strip()
                # Nettoyer parentheses externes redondantes : ((x and y)) -> (x and y)
                if expr.startswith('(') and expr.endswith(')'):
                    # verifier que c'est bien une paire externe et pas deux groupes
                    d = 0
                    outer = True
                    for k, ch in enumerate(expr):
                        if ch == '(':
                            d += 1
                        elif ch == ')':
                            d -= 1
                            if d == 0 and k < len(expr) - 1:
                                outer = False
                                break
                    if outer:
                        expr = expr[1:-1].strip()
                return expr
            i += 1
        return None

    if mchk_path:
        with open(mchk_path, encoding="iso-8859-1") as f:
            mchk_text = f.read()
        for ce in ("Ce1", "Ce2", "Ce3", "Ce4", "Ce5", "Ce6", "Ce7", "Ce8", "Ce9", "CeA"):
            key = ce.upper()
            # Chaque ligne qui mentionne <Record>.CeX (avec mot complet \b)
            line_pat = _re.compile(
                rf'(?mi)^[^\n]*\b(?:{entity_code}|Cli)\.{ce}\b[^\n]*$',
            )
            observed: set[str] = set()
            n_assign = 0
            n_compare = 0
            n_ref = 0
            # Assignation : CLI.CeX = ou CLI.CeX := (mais pas == ni <=)
            assign_line_pat = _re.compile(
                rf'(?i)\b(?:{entity_code}|Cli)\.{ce}\b\s*:?=(?![=<>])'
            )
            # Comparaison : CLI.CeX == ou CLI.CeX <> ou CLI.CeX <= etc.
            compare_line_pat = _re.compile(
                rf'(?i)\b(?:{entity_code}|Cli)\.{ce}\b\s*(?:==|<>|<=|>=|<|>)'
            )
            # Detection assignement Condition(...)
            cond_assign_pat = _re.compile(
                rf'(?i)\b(?:{entity_code}|Cli)\.{ce}\b\s*:?=\s*Condition\s*\(',
            )
            # Detection assignement litteral direct (CeX = '1') sans Condition
            lit_assign_pat = _re.compile(
                rf'''(?i)\b(?:{entity_code}|Cli)\.{ce}\b\s*:?=\s*['"]([^'"]{{0,3}})['"]\s*(?:;|$)''',
            )
            for lm in line_pat.finditer(mchk_text):
                n_ref += 1
                line = lm.group(0)
                # Litteraux simples/doubles de 0-3 chars (' ', '1', '3', 'AB' ...)
                for v in _re.findall(r"""['"]([^'"\n]{0,3})['"]""", line):
                    # Accepter uniquement codes plausibles (chiffres, lettres, espace)
                    if _re.fullmatch(r'[0-9A-Za-z ]{0,3}', v):
                        observed.add(v)
                if assign_line_pat.search(line):
                    n_assign += 1
                    # Sens metier : extraire activation_rule (Condition) OU fixed_value (litteral)
                    if key not in activation_rule_by_ce and key not in fixed_value_by_ce:
                        cm = cond_assign_pat.search(line)
                        if cm:
                            expr = _extract_condition_first_arg(line, cm.end())
                            if expr:
                                # Nettoyer : retirer les prefixes de record redondants
                                # (ART.Ean -> Ean, CLI.TiersGrp -> TiersGrp pour lisibilite)
                                short_expr = _re.sub(
                                    rf'\b(?:{entity_code}|Cli|ART|CLI|SOC|FOU|VRP)\.',
                                    '', expr, flags=_re.IGNORECASE,
                                )
                                # Normaliser les espaces (tabs -> espace, multi-espaces -> un seul)
                                short_expr = _re.sub(r'\s+', ' ', short_expr).strip()
                                activation_rule_by_ce[key] = short_expr
                        else:
                            lm2 = lit_assign_pat.search(line)
                            if lm2:
                                fixed_value_by_ce[key] = lm2.group(1)
                elif compare_line_pat.search(line):
                    n_compare += 1
            if observed or n_ref:
                values_by_ce[key] = observed
                assign_count[key] = n_assign
                compare_count[key] = n_compare
                ref_count[key] = n_ref

    # 4. Pour chaque CE, produire la synthese
    results = []
    for f in ce_fields:
        ce_name = f["name"].upper()
        idxs = index_by_ce.get(ce_name, [])
        co_cols = co_cols_by_ce.get(ce_name, set())
        values = sorted(values_by_ce.get(ce_name, set()))
        n_a = assign_count.get(ce_name, 0)
        n_c = compare_count.get(ce_name, 0)
        n_r = ref_count.get(ce_name, 0)

        # Role infere : privilegier un indice discriminant dans les co-colonnes
        stat_cols = sorted(c for c in co_cols if c.startswith("STAT_"))
        tiersgrp_present = "TIERSGRP" in co_cols
        nat_cols = sorted(c for c in co_cols if c in ("NATURE", "TIERSNAT"))
        activation = activation_rule_by_ce.get(ce_name)
        fixed_val = fixed_value_by_ce.get(ce_name)

        if len(idxs) >= 5 and ce_name == "CE1":
            status = "actif"
            role = f"drapeau principal de statut/filtrage (indexe dans {len(idxs)} indexes)"
        elif stat_cols:
            status = "actif"
            role = f"classement statistique (co-indexe avec {stat_cols[0]})"
        elif tiersgrp_present:
            status = "actif"
            role = "classement groupement tiers (co-indexe avec TIERSGRP)"
        elif nat_cols:
            status = "actif"
            role = f"classement par nature (co-indexe avec {nat_cols[0]})"
        elif len(idxs) >= 2:
            status = "actif"
            role = f"indexe secondaire ({len(idxs)} indexes)"
        elif len(idxs) == 1:
            status = "actif"
            role = f"indexe dans {idxs[0]}"
        elif activation:
            status = "actif"
            role = "drapeau derive (voir regle d'activation)"
        elif fixed_val is not None:
            status = "actif"
            role = "marqueur permanent (voir valeur fixe)"
        elif values or n_r > 0:
            status = "actif"
            role = "utilise dans le code (pas d'index dedie)"
        else:
            status = "reserve"
            role = "extensibilite future (aucun index, aucune reference code)"

        results.append({
            "name": ce_name,
            "status": status,
            "role_infere": role,
            "indexes": idxs,
            "index_count": len(idxs),
            "co_cols": sorted(co_cols),
            "values_observed_in_mchk": values,
            "activation_rule": activation,
            "fixed_value": fixed_val,
            "assign_count": n_a,
            "compare_count": n_c,
            "ref_count": n_r,
        })

    # Enrichissement signaux X.13 pour interpretation metier (etape 3bis du skill).
    # Ne modifie pas l'heuristique role_infere (preservee comme diagnostic) ; ajoute
    # les signaux bruts + description fixe pour les CE "reserve" (idempotence garantie
    # par construction : seuls les CE "actif" laisses a rediger par le LLM dependent
    # de la signature des signaux).
    _enrich_ce_results_with_signals(
        results,
        dhsd_champs_lookup=dhsd_champs_lookup,
        dhsd_source_name=dhsd_source_name,
        business_constants=business_constants,
        mchk_path=mchk_path,
    )

    return results


def _enrich_ce_results_with_signals(results: list,
                                     dhsd_champs_lookup: dict | None,
                                     dhsd_source_name: str | None,
                                     business_constants: list | None,
                                     mchk_path: str | Path | None) -> None:
    """Enrichit in-place la liste produite par analyze_ce_fields avec :
    - dhsd_comment + dhsd_source : commentaire du champ Ce<n> dans le .dhsd
    - mchk_constants : constantes C_* dont le nom mentionne Ce<n>
    - description_metier_signature : empreinte stable des signaux (8 hex)
    - description_metier + description_metier_source : pre-remplis pour les CE reserves

    Les CE "actif" conservent description_metier a None : c'est l'etape 3bis du skill
    (interpretation par Claude) qui les rempliront avec citation obligatoire.
    """
    import hashlib as _hashlib
    import re as _re

    mchk_name = Path(mchk_path).name if mchk_path else None

    for f in results:
        ce_name = f["name"]  # ex: "CE1"
        n = ce_name[2:]       # "1".."9", "A"

        # 1. dhsd_comment : lookup case-insensitive sur "Ce1".."CeA"
        dhsd_comment = None
        dhsd_source = None
        if dhsd_champs_lookup:
            lk = dhsd_champs_lookup.get(f"Ce{n}") or dhsd_champs_lookup.get(f"ce{n}")
            if lk:
                desc = (lk.get("description") or "").strip()
                if desc:
                    dhsd_comment = desc
                if lk.get("source_line") and dhsd_source_name:
                    dhsd_source = f"{dhsd_source_name}:{lk['source_line']}"
        f["dhsd_comment"] = dhsd_comment
        f["dhsd_source"] = dhsd_source

        # 2. mchk_constants : filtrer par \bCe<n>\b dans le name (strict, pas le commentaire
        #    pour eviter de capter "Flash" ou autres termes contextuels)
        mchk_consts = []
        if business_constants:
            ce_pat = _re.compile(rf'(?i)\bCe{n}\b')
            for c in business_constants:
                if ce_pat.search(c.get("name", "")):
                    entry = {
                        "name": c["name"],
                        "value": c.get("value", ""),
                        "comment": (c.get("comment") or "").strip(),
                    }
                    if mchk_name and c.get("line"):
                        entry["source"] = f"{mchk_name}:{c['line']}"
                    mchk_consts.append(entry)
        f["mchk_constants"] = mchk_consts

        # 3. Signature des signaux (idempotence CA13 : si inchange, le LLM conserve sa redaction)
        sig_parts = [
            ce_name,
            f.get("status", ""),
            "|".join(f.get("indexes") or []),
            "|".join(f.get("co_cols") or []),
            "|".join(f.get("values_observed_in_mchk") or []),
            str(f.get("activation_rule") or ""),
            str(f.get("fixed_value") or ""),
            dhsd_comment or "",
            "|".join(c["name"] + "=" + str(c["value"]) for c in mchk_consts),
        ]
        sig = _hashlib.sha1("\x1f".join(sig_parts).encode("utf-8")).hexdigest()[:8]
        f["description_metier_signature"] = sig

        # 4. Description metier pre-remplie uniquement pour les CE reserves (idempotence)
        if f.get("status") == "reserve":
            f["description_metier"] = (
                "Reserve pour extension future. Aucune reference dans le code "
                "du Module Check, aucun index SQL."
            )
            f["description_metier_source"] = "analyse automatique (aucun signal)"
        else:
            # Les CE actifs sont interpretes par le LLM en etape 3bis
            f["description_metier"] = None
            f["description_metier_source"] = None


def extract_check_procedures_by_field(dhsp_path: str | Path, entity_code: str) -> dict:
    """Extrait les procedures `Check_<Entity>_Field_<Field>[_Lib]` du Module Check.

    Ces procedures implementent les regles de validation par champ :
    - Check_CLI_Field_Pay       : validation de la saisie du pays
    - Check_CLI_Field_Pay_Lib   : recuperation du libelle pays (zoom)
    - Check_CLI_Field_Remcod    : validation du code de remise
    - Authorize_CLI_Insert      : regle d'autorisation de creation
    - Authorize_CLI_Delete      : regle d'autorisation de suppression
    - etc.

    Retourne un dict :
      {
        "by_field": {
          "PAY": ["Check_CLI_Field_Pay", "Check_CLI_Field_Pay_Lib"],
          "REMCOD": ["Check_CLI_Field_Remcod"],
          ...
        },
        "global_procedures": {
          "Authorize_CLI_Insert": {"role": "authorize", "op": "Insert"},
          "Check_CLI": {"role": "check", "op": "all_fields"},
          ...
        }
      }
    """
    path = Path(dhsp_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()
    ent = entity_code.upper()
    # Capter toutes les procedures publiques (pattern Module Check Divalto)
    proc_pattern = re.compile(
        r'(?m)^\s*(?:Public\s+)?(?:[Ff]unction|[Pp]rocedure)\s+\w+\s+(\w+)\s*\(',
    )
    procs = [m.group(1) for m in proc_pattern.finditer(text)]

    by_field: dict[str, list] = {}
    global_procs: dict[str, dict] = {}
    # Regex : Check_<Entity>_Field_<Field>[_Lib]
    field_pat = re.compile(
        rf'^(Check|Get|Set|Init)_{ent}_Field_([A-Za-z0-9]+?)(_Lib)?$',
        re.IGNORECASE,
    )
    global_pat = re.compile(
        rf'^(Authorize|Check|Find|Init|Load|Preload|SeekAndLoad|PostIns|PostUpd|PostDel|PreIns|PreUpd|PreDel)_{ent}(?:_(\w+))?$',
        re.IGNORECASE,
    )
    for p in procs:
        fm = field_pat.match(p)
        if fm:
            verb, field, lib = fm.group(1), fm.group(2), fm.group(3)
            key = field.upper()
            by_field.setdefault(key, []).append(p)
            continue
        gm = global_pat.match(p)
        if gm:
            verb, op = gm.group(1), gm.group(2) or ""
            global_procs[p] = {
                "role": verb.lower(),
                "op": op,
            }
    return {
        "by_field": by_field,
        "global_procedures": global_procs,
    }


def parse_dhsp_module(dhsp_path: str | Path) -> dict:
    """Extrait des infos globales d'un module .dhsp ou .dhsq + cles metier + constantes.

    Retourne un dict complet :
      {
        "size_chars": <int>,
        "modules_referenced": [...], "records_declared": [...],
        "procedures_count": <int>, "procedures_public": [...],
        "overwrittenby": [...],
        "header_description": "..." (1ere ligne ;* non vide),
        "field_names_min": "Dos;Tiers;..." si CLI_FieldNames_Min ou similaire,
        "business_constants": [{name, value, comment, line}, ...] (Const C_*),
        "source_path": "...",
      }
    """
    path = Path(dhsp_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()

    modules = sorted(set(re.findall(r'(?m)^\s*Module\s+["\']([^"\'\r\n]+)["\']', text)))
    records = sorted(set(re.findall(r'(?m)^\s*Record(?:Sql)?\s+(\w+)\s+(\w+)', text)))
    # fonctions declarees (pattern : Function type Nom(...) ou Public Function type Nom(...))
    procs_all = re.findall(
        r'(?m)^\s*(?:Public\s+|Shared\s+)?(?:[Ff]unction|[Pp]rocedure)\s+\w+\s+(\w+)\s*\(',
        text,
    )
    procs_public = re.findall(
        r'(?m)^\s*Public\s+(?:[Ff]unction|[Pp]rocedure)\s+\w+\s+(\w+)\s*\(',
        text,
    )
    overwr = sorted(set(re.findall(r'(?m)OverWrittenBy\s+["\']?([\w.]+)["\']?', text)))

    # Description d'en-tete : premiere ligne ;* non vide apres les commentaires techniques
    header_desc = ""
    for line in text.splitlines()[:15]:
        s = line.strip()
        if s.startswith(";*") and len(s) > 3:
            desc = s.lstrip(";*").strip()
            if desc and "xdiva" not in desc.lower() and "$Id" not in desc:
                header_desc = desc
                break

    # Cle metier : patterns <Entity>_FieldNames_Min ou FieldNames_Min
    fieldnames_min = None
    fm_match = re.search(
        r'(?m)^\s*Define\s+\w*FieldNames_Min\s*=\s*["\']([^"\']+)["\']',
        text, re.IGNORECASE,
    )
    if fm_match:
        fieldnames_min = fm_match.group(1)

    # Constantes metier C_* avec leur commentaire
    constants = []
    for m in re.finditer(
        r'(?m)^\s*[Cc]onst\s+(C_\w+)\s*=\s*([^\r\n;]+?)(?:\s*;(.*))?$',
        text,
    ):
        line_num = text[:m.start()].count('\n') + 1
        constants.append({
            "name": m.group(1),
            "value": m.group(2).strip(),
            "comment": (m.group(3) or "").strip(),
            "line": line_num,
        })

    return {
        "size_chars": len(text),
        "modules_referenced": modules,
        "records_declared": [f"{d}:{r}" for d, r in records],
        "procedures_count": len(procs_all),
        "procedures_public": sorted(set(procs_public)),
        "overwrittenby": overwr,
        "header_description": header_desc,
        "field_names_min": fieldnames_min,
        "business_constants": constants,
        "source_path": str(path),
    }


def parse_dhsf_f8_bindings(dhsf_path: str | Path) -> list:
    """Extrait les bindings FK par zoom standard : `table_associee=oui` + `f8=<zoom>`.

    Structure reelle observee dans les .dhsf DAV :
    ```
    [rubrique]
      ...
      [description]
        donnee=<record>,<champ>,<alias>[,<index>]
      [param_saisie]
        table_associee=oui      <-- flag : zoom standard actif
      [touches]
        f8=<zoom_code>          <-- vrai zoom FK (seule touche prise en compte)
    ```

    IMPORTANT : seule la touche **f8** est consideree comme un vrai binding FK.
    Les touches `f1` (aide generique) et `f7` (tri/listes codifiees generiques)
    sont des "pieges touches" standard qui ne designent pas une table cible
    d'une FK. Un champ bindé uniquement via f1/f7 n'est donc pas promu FK
    par le masque — il peut l'etre via Check_<Entity>_Field_<Field>_Lib du
    Module Check, source de verite complementaire.

    `table_associee=oui` est un FLAG BOOLEEN. La table cible se deduit du nom
    du champ (convention Divalto : PAY->pays, TACOD->T008 tarif, TIERSGRP->TiersGrp)
    ou du zoom_code (mapping 9088=tiers, 9047=tarif, ...).

    Retourne : [{"field_name": "<CHAMP>", "zoom_code": "<N>", "target_table_hint": "<CHAMP>",
                 "line": <int>, "record": "<record_alias>", "key_pressed": "f8"}, ...]
    Deduplique par field_name. Les rubriques sans f8 (ou avec f1/f7 seul) sont ignorees.
    """
    path = Path(dhsf_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()
    results = []
    seen = set()
    # Chaque occurrence `table_associee=oui` signale une rubrique bindee.
    for m in re.finditer(r'(?mi)^\s*table_associee\s*=\s*oui\s*$', text):
        pos = m.start()
        line = text[:pos].count('\n') + 1
        # Fenetre ~500 chars avant pour trouver donnee= (le plus proche)
        before = text[max(0, pos - 500): pos]
        donnee_matches = list(re.finditer(
            r'(?mi)^\s*donnee\s*=\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)(?:\s*,\s*(\d+))?',
            before,
        ))
        if not donnee_matches:
            continue
        dm = donnee_matches[-1]  # le plus proche de table_associee
        record, champ, alias = dm.group(1), dm.group(2), dm.group(3)
        # Fenetre 500 chars apres pour capter exclusivement f8
        after = text[pos: pos + 500]
        f8_m = re.search(r'(?mi)^\s*f8\s*=\s*(\w+)', after)
        if not f8_m:
            # Pas de f8 : ce n'est pas un binding FK (f1/f7 = pieges touches generiques)
            continue
        zoom_code = f8_m.group(1)
        # Cle de dedup : le nom de champ (par rubrique on ne veut pas doublons)
        key = champ.upper()
        if key in seen:
            continue
        seen.add(key)
        # Hint sur la table cible : nom du champ en majuscules
        # (convention : PAY->pays, TACOD->T008 tarif, TIERSGRP->TiersGrp, etc.)
        results.append({
            "field_name": champ.upper(),
            "record": record,
            "alias": alias,
            "zoom_code": zoom_code,
            "key_pressed": "f8",
            "target_table_hint": champ.upper(),
            "line": line,
        })
    return results


def extract_check_procedure_targets(dhsp_path: str | Path, entity_code: str) -> dict:
    """Pour chaque procedure `Check_<Entity>_Field_<Field>` du Module Check,
    extrait la VRAIE table cible FK depuis les appels `Find_<Table>(...)` ou
    `Lectab(<num>, ...)` presents dans le body de la procedure.

    Exemple pour CLI :
        Public function int Check_CLI_Field_TaCod(&CLI)
        ...
            freturn (Find_T014(TiCod, CLI.TaCod, context=true))
        endp

    -> target_table = "T014" pour le champ TACOD

    Retourne :
      {
        "TACOD": "T014",
        "PAY":   "T004",
        "TIT":   "T048",
        "DEV":   "DEVISE",
        "LANG":  "LANGUE",
        "CPT":   "C3",
        ...
      }
    """
    path = Path(dhsp_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()
    ent = entity_code.upper()

    # Regex : declarations de proc Check_<Entity>_Field_<Field>[_Lib]
    proc_pat = re.compile(
        rf'(?mi)^\s*(?:Public\s+)?(?:[Ff]unction|[Pp]rocedure)\s+\w+\s+(Check_{ent}_Field_(\w+?))(_Lib)?\s*\(',
    )
    # Find_<TableName>(... : capture le nom de la table cible
    find_pat = re.compile(r'\bFind_([A-Za-z][A-Za-z0-9_]*)\s*\(')
    # Lectab(<num>, [...]) : capture le numero Lectab (convention : Lectab 14 = T014)
    lectab_pat = re.compile(r'\bLectab\s*\(\s*(\d+)')

    matches = list(proc_pat.finditer(text))
    results: dict[str, str] = {}
    for i, m in enumerate(matches):
        proc_name, field_tok = m.group(1), m.group(2)
        field_upper = field_tok.upper()
        if field_upper in results:
            continue  # on garde la premiere occurence (souvent Check_X avant Check_X_Lib)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else min(len(text), start + 3000)
        body = text[start:end]
        # Priorite : Find_<Table> (plus explicite)
        find_names = find_pat.findall(body)
        # Filtrer les self-calls (Check_CLI_Field_X_Lib appelle Check_CLI_Field_X)
        target = None
        for fn in find_names:
            # Ignorer Find_<Entity>* et Find_<Entity>_Field_* (meme objet) et Find_<Entity>_Lib
            if fn.upper() == ent:
                continue
            if fn.upper().startswith(f"{ent}_"):
                continue
            target = fn
            break
        if not target:
            # Fallback : Lectab(<num>,...) -> convention Tnnn
            lectab_nums = lectab_pat.findall(body)
            if lectab_nums:
                target = f"T{int(lectab_nums[0]):03d}"
        if target:
            results[field_upper] = target
    return results


def lookup_table_labels(dict_path: str | Path, table_names: list[str]) -> dict:
    """Cherche les libelles des tables donnees dans un .dhsd (top-level [TABLE]).

    Retourne : {"T014": "Tarif ventes", "T048": "Titre", ...}
    Les noms sont case-insensitive a la recherche, mais les cles de retour
    sont en MAJUSCULES (pour matching direct avec les target_table extraits).
    """
    path = Path(dict_path)
    if not path.exists():
        return {}
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()
    wanted = {n.upper() for n in table_names}
    out: dict[str, str] = {}
    # Iterer sur chaque bloc [TABLE] ... jusqu'au prochain [
    for m in re.finditer(r'(?m)^\[TABLE\]\s*$', text):
        start = m.end()
        next_sec = re.search(r"(?m)^\[", text[start:])
        meta_end = start + next_sec.start() if next_sec else len(text)
        meta_block = text[start:meta_end]
        nom_m = re.search(r"(?m)^\s*Nom=([^,\r\n]+),([^,\r\n]*),1\s*$", meta_block)
        if not nom_m:
            continue
        name = nom_m.group(1).strip().upper()
        if name in wanted:
            label = nom_m.group(2).strip()
            if label:
                out[name] = label
            if len(out) == len(wanted):
                break
    return out


def extract_diva_apres_fk_bindings(dhsf_path: str | Path, entity_code: str) -> list:
    """Extrait les FK confirmees via `diva_apres` du masque + appel `Check_<Entity>_Field_*`.

    Chaine de validation complete Divalto :
    1. Dans la rubrique du masque :
         donnee=<record>,<CHAMP>,<alias>
         [param_saisie]
           diva_apres="<NomProc>"   <-- traitement apres saisie
    2. Dans la section `[diva]` du meme .dhsf (procedures embarquees) :
         Public Procedure <NomProc>
         Beginp
             Check_<Entity>_Field_<Field>[_Lib](<args>)   <-- validation metier FK
         Endp

    L'appel a `Check_<Entity>_Field_<Field>[_Lib]` est la preuve la plus fiable
    d'une FK : le champ est validé par l'objet metier, ce qui garantit qu'il
    pointe vers une table valide. Canal complementaire au f8+table_associee
    et au listing des `Check_<Entity>_Field_*` du Module Check.

    Retourne : [
      {"field_name": "TACOD", "proc_name": "Champ_Tacod_1_Ap",
       "check_calls": ["Check_CLI_Field_TaCod_Lib"], "line": 23734}, ...
    ]
    Deduplique par field_name (garde la premiere occurrence).
    """
    path = Path(dhsf_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()
    ent = entity_code.upper()

    # 1. Collecter pour chaque rubrique : champ + diva_apres associe
    # On recherche chaque occurrence de diva_apres et on cherche le donnee=<...>
    # dans la fenetre precedente (~500 chars).
    field_to_proc: dict[str, str] = {}
    for m in re.finditer(r'(?mi)^\s*diva_apres\s*=\s*"([^"]+)"', text):
        proc_name = m.group(1)
        before = text[max(0, m.start() - 500): m.start()]
        donnee_matches = list(re.finditer(
            r'(?mi)^\s*donnee\s*=\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)',
            before,
        ))
        if not donnee_matches:
            continue
        champ = donnee_matches[-1].group(2).upper()
        # Garder la premiere association (plusieurs rubriques peuvent partager)
        if champ not in field_to_proc:
            field_to_proc[champ] = proc_name

    # 2. Pour chaque procedure du masque, chercher appels Check_<Entity>_Field_<X>
    proc_to_checks: dict[str, list[str]] = {}
    proc_to_line: dict[str, int] = {}
    proc_pat = re.compile(
        r'(?mi)^\s*(?:Public\s+)?Procedure\s+(\w+)\s*(?:;[^\n]*)?$',
    )
    check_call_pat = re.compile(
        rf'(?i)\b(Check_{ent}_Field_\w+?(?:_Lib)?)\s*\(',
    )
    # Parcours sequentiel : delimiter chaque proc par la suivante
    proc_matches = list(proc_pat.finditer(text))
    for i, pm in enumerate(proc_matches):
        proc_name = pm.group(1)
        start = pm.end()
        end = proc_matches[i + 1].start() if i + 1 < len(proc_matches) else len(text)
        body = text[start: end]
        calls = sorted(set(check_call_pat.findall(body)))
        if calls:
            proc_to_checks[proc_name] = calls
            proc_to_line[proc_name] = text[:pm.start()].count('\n') + 1

    # 3. Croiser : pour chaque champ ayant diva_apres, si la proc appelle un Check_Field, on a une FK
    results = []
    for field_name, proc_name in field_to_proc.items():
        calls = proc_to_checks.get(proc_name)
        if not calls:
            continue
        results.append({
            "field_name": field_name,
            "proc_name": proc_name,
            "check_calls": calls,
            "line": proc_to_line.get(proc_name),
        })
    return results


def parse_choix_values_json(json_path: str | Path) -> dict:
    """Lit le JSON multichoix produit par `extract_codified_values.py`.

    Le fichier source canonique est produit par `_read_multichoix.py --all-details`
    puis enrichi par `extract_codified_values.py` (Type 1/3/4, flags tbl/#, Lookup,
    ExternId, Color via merge avec le `.json` partiel).

    Structure attendue (UTF-8) :
      {
        "Columns": {
          "<nc>": {
            "Type": "1"|"3"|"4",
            "AvailableValues": [{"Id": "1", "Label": "...", "Value": "...",
                                 "LabelReference": true?, "LabelTranslationRef": true?,
                                 "Color": "..."?}],
            "Lookup": {"enreg": "...", "donnee": "...", "prefixe": "...",
                       "ideb": 1, "ifin": 4},                     # Type 3
            "ExternId": "IdFic"                                    # Type 4
          }
        }
      }

    Retourne un dict par choix_id. Les Type 3/4 ont `values=[]` mais portent
    `lookup`/`extern_id` que le renderer exploite. ISO-8859-1 toujours
    tolere en lecture (pour les anciens .json partiels).
    """
    import json as _json
    path = Path(json_path)
    if not path.exists():
        return {}
    # Essaie UTF-8 (format produit par extract_codified_values), puis ISO-8859-1
    # en fallback (format historique des .json partiels DIVA).
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="iso-8859-1")
    try:
        data = _json.loads(text)
    except Exception:
        return {}
    columns = data.get("Columns") or {}
    result = {}
    for choix_id, col in columns.items():
        values = []
        for v in (col.get("AvailableValues") or []):
            entry = {
                "id": v.get("Id", ""),
                "label": v.get("Label", ""),
                "value": v.get("Value", ""),
                "color": v.get("Color", ""),
            }
            if v.get("LabelReference"):
                # Nom de bitmap tbl* -- le renderer externe le remplace par
                # "_(icone)_" ou "_(icone NOM)_" si resolu dans fstyle.
                entry["label_reference"] = True
            if v.get("FstyleName"):
                # FS-03 : nom canonique resolu dans une variante fstyle
                # (wpf/legacy/imp). Permet au renderer d'afficher
                # `_(icone TBLART)_` au lieu de `_(icone)_` generique.
                entry["fstyle_name"] = v["FstyleName"]
                if v.get("FstyleVariant"):
                    entry["fstyle_variant"] = v["FstyleVariant"]
            if v.get("LabelTranslationRef"):
                # Reference i18n #<nom> (libelle traduit au runtime par le framework).
                entry["label_translation_ref"] = True
            values.append(entry)
        meta = {
            "type": col.get("Type", ""),
            "values": values,
        }
        if col.get("Lookup"):
            meta["lookup"] = col["Lookup"]
        if col.get("ExternId"):
            meta["extern_id"] = col["ExternId"]
        result[choix_id] = meta
    return result


def parse_dhsf_choix(dhsf_path: str | Path) -> list:
    """Extrait les champs codifies (listes de choix) d'un masque .dhsf.

    Pour chaque `choix="<dict>.dhfi","<choix_id>"`, recupere le contexte :
    titre, info-bulle, numero de ligne. Le dev peut ensuite aller chercher
    les valeurs concretes dans le .dhfi ISAM (fichier binaire).

    Retourne : [{"choix_id": "...", "dict_file": "...", "titre": "...",
                 "info_bulle": "...", "line": <int>}, ...]
    (deduplique par choix_id, ordre d'apparition).
    """
    path = Path(dhsf_path)
    with path.open(encoding="iso-8859-1") as f:
        text = f.read()
    seen = set()
    results = []
    for m in re.finditer(
        r'choix\s*=\s*"([^"]+\.dhfi)"\s*,\s*"([^"]+)"', text, re.IGNORECASE,
    ):
        dict_file, choix_id = m.group(1), m.group(2)
        if choix_id in seen:
            continue
        seen.add(choix_id)
        line = text[:m.start()].count('\n') + 1
        # Chercher titre et info_bulle dans les ~1500 chars qui suivent
        chunk = text[m.start(): m.start() + 2000]
        titre_m = re.search(r'titre\s*=\s*"([^"]+)"', chunk)
        bulle_m = re.search(r'\[info_bulle\]\s*\n\s*texte\s*=\s*"([^"]+)"', chunk)
        results.append({
            "choix_id": choix_id,
            "dict_file": dict_file,
            "titre": titre_m.group(1) if titre_m else "",
            "info_bulle": bulle_m.group(1) if bulle_m else "",
            "line": line,
        })
    return results
