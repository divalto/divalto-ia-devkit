# Canonical source -- vendored copies in generating-*/scripts/ and creating-diva-entity/scripts/
# When updating this file, propagate changes to all vendored copies.
"""Bibliotheque de calcul des tokens de nommage pour une entite DIVA.

Ce module est la source canonique. Les copies vendorees dans les skills de generation
doivent etre identiques a ce fichier (hors commentaire d'en-tete).
"""

from datetime import date

# -- Registre des domaines ----------------------------------------------------------------
# Cle = nom canonique du domaine (tel qu'utilise dans les sources ERP)
# Valeurs = prefixes derives selon CONVENTIONS.md et MODULES-ERP.md
DOMAIN_REGISTRY = {
    "DAV": {
        "prefix_code": "GT_",
        "prefix_module": "gtt",
        "prefix_module_u": "gtu",
        "prefix_db": "gtf",
        "domaine_2l": "gt",
        "dict": "GTFDD",
        "module_ficsql": "gtpmficsql.dhop",
        "set_prefixe_module": "GT_SetPrefixeModule()",
    },
    "Retail": {
        "prefix_code": "RT_",
        "prefix_module": "rtt",
        "prefix_module_u": "rtu",
        "prefix_db": "rtl",
        "domaine_2l": "rt",
        "dict": "RTLFDD",
        "module_ficsql": "rtpmficsql.dhop",
        "set_prefixe_module": "RT_SetPrefixeModule()",
    },
    "Production": {
        "prefix_code": "GG_",
        "prefix_module": "ggt",
        "prefix_module_u": "ggu",
        "prefix_db": "ggf",
        "domaine_2l": "gg",
        "dict": "GGFDD",
        "module_ficsql": "ggpmficsql.dhop",
        "set_prefixe_module": "GG_SetPrefixeModule()",
    },
    "Atelier": {
        "prefix_code": "GG_",
        "prefix_module": "ggt",
        "prefix_module_u": "ggu",
        "prefix_db": "ggf",
        "domaine_2l": "gg",
        "dict": "GGFDD",
        "module_ficsql": "ggpmficsql.dhop",
        "set_prefixe_module": "GG_SetPrefixeModule()",
    },
    "Comptabilite": {
        "prefix_code": "CC_",
        "prefix_module": "cct",
        "prefix_module_u": "ccu",
        "prefix_db": "ccf",
        "domaine_2l": "cc",
        "dict": "CCFDD",
        "module_ficsql": "ccpmficsql.dhop",
        "set_prefixe_module": "CC_SetPrefixeModule()",
    },
    "Affaires": {
        "prefix_code": "GA_",
        "prefix_module": "gat",
        "prefix_module_u": "gau",
        "prefix_db": "gaf",
        "domaine_2l": "ga",
        "dict": "GAFDD",
        "module_ficsql": "gapmficsql.dhop",
        "set_prefixe_module": "GA_SetPrefixeModule()",
    },
    "Reglements": {
        "prefix_code": "RC_",
        "prefix_module": "rct",
        "prefix_module_u": "rcu",
        "prefix_db": "rcf",
        "domaine_2l": "rc",
        "dict": "RCFDD",
        "module_ficsql": "rcpmficsql.dhop",
        "set_prefixe_module": "RC_SetPrefixeModule()",
    },
    "Relation-Tiers": {
        "prefix_code": "GR_",
        "prefix_module": "grt",
        "prefix_module_u": "gru",
        "prefix_db": "grf",
        "domaine_2l": "gr",
        "dict": "GRFDD",
        "module_ficsql": "grpmficsql.dhop",
        "set_prefixe_module": "GR_SetPrefixeModule()",
    },
    "Paie": {
        "prefix_code": "PP_",
        "prefix_module": "ppt",
        "prefix_module_u": "ppu",
        "prefix_db": "ppf",
        "domaine_2l": "pp",
        "dict": "PPFDD",
        "module_ficsql": "pppmficsql.dhop",
        "set_prefixe_module": "PP_SetPrefixeModule()",
    },
    "Point de vente": {
        "prefix_code": "PV_",
        "prefix_module": "pvt",
        "prefix_module_u": "pvu",
        "prefix_db": "pvf",
        "domaine_2l": "pv",
        "dict": "PVFDD",
        "module_ficsql": "pvpmficsql.dhop",
        "set_prefixe_module": "PV_SetPrefixeModule()",
    },
    "Qualite": {
        "prefix_code": "QU_",
        "prefix_module": "qut",
        "prefix_module_u": "quu",
        "prefix_db": "quf",
        "domaine_2l": "qu",
        "dict": "QUFDD",
        "module_ficsql": "qupmficsql.dhop",
        "set_prefixe_module": "QU_SetPrefixeModule()",
    },
    "Controle": {
        "prefix_code": "CO_",
        "prefix_module": "cot",
        "prefix_module_u": "cou",
        "prefix_db": "cof",
        "domaine_2l": "co",
        "dict": "COFDD",
        "module_ficsql": "copmficsql.dhop",
        "set_prefixe_module": "CO_SetPrefixeModule()",
    },
    "Processus": {
        "prefix_code": "SP_",
        "prefix_module": "spt",
        "prefix_module_u": "spu",
        "prefix_db": "spf",
        "domaine_2l": "sp",
        "dict": "SPFDD",
        "module_ficsql": "sppmficsql.dhop",
        "set_prefixe_module": "SP_SetPrefixeModule()",
    },
    "Mobilite": {
        "prefix_code": "MO_",
        "prefix_module": "mot",
        "prefix_module_u": "mou",
        "prefix_db": "mof",
        "domaine_2l": "mo",
        "dict": "MOFDD",
        "module_ficsql": "mopmficsql.dhop",
        "set_prefixe_module": "MO_SetPrefixeModule()",
    },
    "GRM": {
        "prefix_code": "GM_",
        "prefix_module": "gmt",
        "prefix_module_u": "gmu",
        "prefix_db": "gmf",
        "domaine_2l": "gm",
        "dict": "GMFDD",
        "module_ficsql": "gmpmficsql.dhop",
        "set_prefixe_module": "GM_SetPrefixeModule()",
    },
}


def resolve_domain(domaine_input):
    """Resout un nom de domaine (insensible a la casse) vers le registre."""
    # Correspondance exacte
    if domaine_input in DOMAIN_REGISTRY:
        return domaine_input, DOMAIN_REGISTRY[domaine_input]

    # Correspondance insensible a la casse
    for key, val in DOMAIN_REGISTRY.items():
        if key.lower() == domaine_input.lower():
            return key, val

    return None, None


def derive_base_from_table(table_sql, prefix_db):
    """Derive le nom de base a partir de la table SQL et du prefixe DB.

    Strategie :
    - Si la table commence par le prefixe DB (case-insensitive), retirer ce prefixe
    - Sinon, utiliser la table entiere en minuscules
    Le resultat est toujours en minuscules.
    """
    table_lower = table_sql.lower()
    prefix_lower = prefix_db.lower()

    if table_lower.startswith(prefix_lower):
        base = table_lower[len(prefix_lower):]
    else:
        base = table_lower

    return base


def check_collision(nom_vue, table_sql):
    """Verifie la regle de non-collision RecordSql / Record.

    DIVA est case-insensitive sur les identifiants : si NomVue et TableSQL
    sont identiques (case-insensitive), il y a collision.
    """
    return nom_vue.lower() == table_sql.lower()


def compute_nom_vue(entite, domaine_2l):
    """Calcule le nom du RecordSql (NomVue).

    Formule standard : {Entite}{DomaineSuffixe}
    Ou DomaineSuffixe = prefixe domaine 2 lettres en PascalCase.
    Ex: FamRglt + rt -> FamRgltRtl (note: Rtl, pas Rt)
    """
    return entite + domaine_2l.capitalize()


def compute_prefix_res(prefix_module):
    """Calcule le prefixe de reservation (4 caracteres, MAJUSCULES).

    D'apres les exemples : rtt -> RTTB (ajout de 'B')
    """
    return (prefix_module + "B").upper()[:4]


# -- Validation multi-table (G-021) -----------------------------------------------
# Types de jointures supportes : implicite (FROM+WHERE, dominant X.13) et LEFT JOIN.
# Les keywords Divalto Join/LeftJoin et INNER/RIGHT/CROSS sont hors scope.
VALID_JOIN_TYPES = {"implicit", "left_join"}
VALID_CASE_TYPES = {"equal", "like", "between"}
VALID_CASE_PARAMS = {"char", "int", "date", "num"}


def _validate_joined_tables(joined_tables):
    """Valide la structure de joined_tables. Retourne la liste des erreurs (vide si OK)."""
    errors = []
    for i, jt in enumerate(joined_tables):
        if not isinstance(jt, dict):
            errors.append(f"joined_tables[{i}] : doit etre un dict")
            continue
        for required in ("table_sql", "alias", "join_type", "join_condition"):
            if required not in jt or not jt[required]:
                errors.append(f"joined_tables[{i}] : champ obligatoire manquant '{required}'")
        jt_type = jt.get("join_type")
        if jt_type and jt_type not in VALID_JOIN_TYPES:
            errors.append(
                f"joined_tables[{i}] : join_type='{jt_type}' invalide "
                f"(attendu : {sorted(VALID_JOIN_TYPES)})"
            )
        columns = jt.get("columns_selected", [])
        if not isinstance(columns, list):
            errors.append(f"joined_tables[{i}].columns_selected : doit etre une liste")
    return errors


def _validate_additional_cases(additional_cases):
    """Valide la structure de additional_cases. Retourne la liste des erreurs (vide si OK)."""
    errors = []
    for i, ac in enumerate(additional_cases):
        if not isinstance(ac, dict):
            errors.append(f"additional_cases[{i}] : doit etre un dict")
            continue
        for required in ("name", "field", "type", "param"):
            if required not in ac or not ac[required]:
                errors.append(f"additional_cases[{i}] : champ obligatoire manquant '{required}'")
        ac_type = ac.get("type")
        if ac_type and ac_type not in VALID_CASE_TYPES:
            errors.append(
                f"additional_cases[{i}] : type='{ac_type}' invalide "
                f"(attendu : {sorted(VALID_CASE_TYPES)})"
            )
        ac_param = ac.get("param")
        if ac_param and ac_param not in VALID_CASE_PARAMS:
            errors.append(
                f"additional_cases[{i}] : param='{ac_param}' invalide "
                f"(attendu : {sorted(VALID_CASE_PARAMS)})"
            )
    return errors


def compute_names(domaine, entite, table_sql, champ_cle, description,
                  nom_vue_override=None, has_libelle=True,
                  champ_libelle="Libelle",
                  joined_tables=None, additional_cases=None):
    """Calcule tous les tokens de nommage pour une entite DIVA.

    champ_libelle : nom du champ libelle dans le RecordSQL/dictionnaire.
    Defaut : "Libelle". A preciser (ex: "Lib") si l'entite utilise un champ
    global de nature differente (R-001).

    joined_tables : liste de dicts decrivant les tables jointes (G-021).
    Format : [{"table_sql", "alias", "join_type" (implicit|left_join),
               "join_condition", "columns_selected": [list]}, ...].
    Absent ou [] -> mode mono-table (backcompat).

    additional_cases : liste de dicts decrivant les Cases WHERE supplementaires (G-021).
    Format : [{"name", "field", "type" (equal|like|between), "param" (char|int|date|num)}, ...].
    """

    # Normalisation des parametres multi-table (G-021)
    joined_tables = joined_tables or []
    additional_cases = additional_cases or []

    # Validation des structures multi-table
    if joined_tables:
        errs = _validate_joined_tables(joined_tables)
        if errs:
            return None, "Erreurs dans joined_tables : " + " ; ".join(errs)
    if additional_cases:
        errs = _validate_additional_cases(additional_cases)
        if errs:
            return None, "Erreurs dans additional_cases : " + " ; ".join(errs)

    # Resoudre le domaine
    domaine_canon, dom = resolve_domain(domaine)
    if dom is None:
        return None, f"Domaine inconnu : '{domaine}'. Domaines valides : {', '.join(sorted(DOMAIN_REGISTRY.keys()))}"

    prefix_db = dom["prefix_db"]
    prefix_module = dom["prefix_module"]
    prefix_module_u = dom["prefix_module_u"]
    domaine_2l = dom["domaine_2l"]
    prefix_code = dom["prefix_code"]
    dict_name = dom["dict"]

    # Derive base
    base = derive_base_from_table(table_sql, prefix_db)

    # FichierDico : nom du fichier/base dans le dictionnaire (ex: GtfLivre)
    fichier_dico = prefix_db.capitalize() + entite

    # NomVue : calcul ou override
    if nom_vue_override:
        nom_vue = nom_vue_override
    else:
        nom_vue = compute_nom_vue(entite, prefix_db)

    # Verification collision
    collision = check_collision(nom_vue, table_sql)

    # Tokens derives
    table_majuscule = table_sql.upper()
    table_minuscule = table_sql.lower()
    entity_lower = entite.lower()
    entity_upper = entite.upper()
    champ_cle_upper = champ_cle.upper()
    prefix_res = compute_prefix_res(prefix_module)

    today = date.today().isoformat()

    # Noms de fichiers
    fichier_rsql = f"{prefix_db}rs{base}.dhsq"
    fichier_rsql_compile = f"{prefix_db}rs{base}.dhoq"
    fichier_rsql_surcharge = f"{prefix_db}rs{base}u.dhoq"
    fichier_zoom = f"{prefix_module}z{entity_lower}_sql.dhsp"
    fichier_zoom_surcharge = f"{prefix_module_u}z{entity_lower}_sql.dhop"
    fichier_mchk = f"{prefix_module}mchk{entity_lower}.dhsp"
    fichier_mchk_surcharge = f"{prefix_module_u}mchk{entity_lower}.dhop"
    # Masque ecran : prefixe = domaine_2l + "e" (ex: gte pour DAV)
    prefix_ecran = domaine_2l + "e"
    fichier_masque = f"{prefix_ecran}z{entity_lower}_sql.dhsf"
    fichier_masque_compile = f"{prefix_ecran}z{entity_lower}_sql.dhof"

    # Instances et variables
    rs_instance = f"RS_{nom_vue}"
    instance_sel = f"{nom_vue}_Sel"
    record_init = f"{table_minuscule}_INIT"
    shared_record = table_minuscule
    chkdata = f"ChkData_{table_majuscule}"
    fieldnames_min = f"{table_majuscule}_FieldNames_Min"
    chaine_reservation = f"Formater_Res('{prefix_res}') {nom_vue}.Dos {nom_vue}.{champ_cle}"
    if has_libelle:
        titre_variable = f"{nom_vue}.{champ_cle} *1 '-' *1 {nom_vue}.{champ_libelle}"
    else:
        titre_variable = f"{nom_vue}.{champ_cle}"

    # Modules et includes
    module_mchk = f"{prefix_module}mchk{entity_lower}.dhop"
    module_ficsql = dom["module_ficsql"]
    overwrittenby_zoom = f"{prefix_module_u.upper()}Z{entity_upper}_SQL.dhop"
    overwrittenby_mchk = f"{prefix_module_u}mchk{entity_lower}.dhop"
    overwrittenby_rsql = f"{prefix_db}rs{base}u.dhoq"

    tokens = {
        # Metadonnees
        "domaine": domaine_canon,
        "entite": entite,
        "table_sql": table_sql,
        "champ_cle": champ_cle,
        "description": description,
        "date": today,

        # Prefixes domaine
        "PREFIX_": prefix_code,
        "prefix_module": prefix_module,
        "prefix_module_u": prefix_module_u,
        "MODULEPREFIX_U": prefix_module_u.upper(),
        "prefix_db": prefix_db,
        "domaine_2l": domaine_2l,
        "DICT": dict_name,
        "module_ficsql": module_ficsql,
        "set_prefixe_module": dom["set_prefixe_module"],

        # Nommage entite
        "NomVue": nom_vue,
        "TableSQL": table_sql,
        "TABLE_MAJUSCULE": table_majuscule,
        "TABLE": table_majuscule,
        "table_minuscule": table_minuscule,
        "entity": entite,
        "ENTITY": entity_upper,
        "base": base,
        "FichierDico": fichier_dico,
        "ChampCle": champ_cle,
        "CHAMPCLE": champ_cle_upper,
        "PREFIXRES": prefix_res,
        "Description": description,

        # Noms de fichiers
        "fichier_rsql": fichier_rsql,
        "fichier_rsql_compile": fichier_rsql_compile,
        "fichier_rsql_surcharge": fichier_rsql_surcharge,
        "fichier_zoom": fichier_zoom,
        "fichier_zoom_surcharge": fichier_zoom_surcharge,
        "fichier_mchk": fichier_mchk,
        "fichier_mchk_surcharge": fichier_mchk_surcharge,
        "fichier_masque": fichier_masque,
        "fichier_masque_compile": fichier_masque_compile,

        # Instances et variables
        "RS_instance": rs_instance,
        "instance_sel": instance_sel,
        "record_init": record_init,
        "shared_record": shared_record,
        "ChkData": chkdata,
        "FieldNames_Min": fieldnames_min,
        "ChaineReservation": chaine_reservation,
        "TitreVariable": titre_variable,

        # Modules et includes
        "module_mchk": module_mchk,
        "overwrittenby_zoom": overwrittenby_zoom,
        "overwrittenby_mchk": overwrittenby_mchk,
        "overwrittenby_rsql": overwrittenby_rsql,

        # Options
        "has_libelle": has_libelle,
        "ChampLibelle": champ_libelle,
        "ChampLibelleMaj": champ_libelle.upper(),

        # Multi-table (G-021) : jointures parametriques et Cases WHERE additionnels
        "joined_tables": joined_tables,
        "additional_cases": additional_cases,
        "has_joins": len(joined_tables) > 0,

        # Validation
        "collision_detected": collision,
    }

    return tokens, None
