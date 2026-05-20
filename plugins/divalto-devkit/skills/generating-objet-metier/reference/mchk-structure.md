# Structure d'un Module Check (.dhsp)

## Contenu

- Sections du fichier (dans l'ordre)
- Fonctions obligatoires par categorie
- Conventions de nommage dans le mchk
- Tokens Jinja2 utilises

---


Source : `rttmchkrtlfamrglt.dhsp` (737 lignes, ERP X.13).

---

## Sections du fichier (dans l'ordre)

### 1. En-tete

```
;>xdiva
SetModuleInfo('$Id: fichier.dhsp 1 date user $')
;*  Module fonctions et procedures de controle objet tables Description
;@!<ZETA
;@!>
```

### 2. OverWrittenBy

```
OverWrittenBy "{moduleprefix_u}mchk{prefix_db}{entity_lower}.dhop"
```

### 3. Includes (4 fichiers)

```
Include   "a5tczoom.dhsp"
include   "{domaine_2l}tcficsql.dhsp"
include   "gttcdav000.dhsp"
include   "a5tcchk000.dhsp"
```

### 4. Modules (5 fichiers)

```
Module  "A5PM000.dhop"
Module  "A5PMCHK000.dhop"
Module  "gttmchk000.dhop"
Module  "{domaine_2l}pmficsql.dhop"
Module  "{domaine_2l}tmchk000.dhop"
```

### 5. Declarations

```
Shared   Record '{DICT}.dhsd'  {table_minuscule} {table_minuscule}_INIT

Record 'a5dd.dhsd'   A5ChkData   ChkData_{TABLE_MAJUSCULE}
Define {TABLE_MAJUSCULE}_FieldNames_Min   = '{CHAMPCLE};LIBELLE'
1  FieldNames_Min  S = {TABLE_MAJUSCULE}_FieldNames_Min

Declaration_{NomVue}  RS_{NomVue}  ;instance globale
```

### 6. Proto + Init_Module

```
Proto function int Initialize_{TABLE_MAJUSCULE}_New(&{TABLE_MAJUSCULE})
Record {DICT}.dhsd {TABLE_MAJUSCULE} {TABLE_MAJUSCULE}
EndProto

Function int Init_Module
beginF
    Init_Module_DAV
    ChkData_{TABLE} = {PREFIX_}Get_CheckObject_Data(RS_{NomVue})
    ChkData_{TABLE}.ImportTableurFl = OUI
    Initialize_{entity}_New({table}_INIT)
    FReturn(0)
endF
1   InitModule 1,0 = Init_Module()
```

---

## Fonctions obligatoires par categorie

| # | Categorie | Fonctions | Nb |
|---|-----------|-----------|:--:|
| 1 | Initialisation | `Init_Module` | 1 |
| 2 | Proprietes | `Get_{TABLE}_ChkData`, `Get_{TABLE}_FieldProperties` | 2 |
| 3 | Cache | `Set_{TABLE}_Cache_Mode`, `Put_{TABLE}_Cache_Data` | 2 |
| 4 | Recherche | `Seek_{NomVue}` | 1 |
| 5 | Exposition | `Get_{table}_Record`, `Get_{TABLE}_Lib`, `GET_{TABLE}_INIT_Record`, `Set_{TABLE}_init_record`, `Get_{table}_Reservation`, `Get_{table}_Key` | 6 |
| 6 | Champs min/all | `Get_{TABLE}_FieldNames_Min`, `Stack_{TABLE}_FieldNames_Min`, `Reset_{TABLE}_FieldNames_Min`, `Get_{TABLE}_FieldNames_All` | 4 |
| 7 | Recherche/Chargement | `SeekAndLoad_{TABLE}`, `Load_{TABLE}_Record`, `Load_{TABLE}`, `Give_{TABLE}` | 4 |
| 8 | Controle existence | `Find_{TABLE}_PK`, `Find_{TABLE}_Lib`, `Find_{TABLE}`, `Exists_{TABLE}`, `Exists_{TABLE}_Record` | 5 |
| 9 | Controle donnees | `Check_{TABLE}_Key`, `Check_{TABLE}`, `Check_{table}_FieldCod` | 3 |
| 10 | Init enregistrements | `Initialize_{table}_CE`, `Initialize_{table}_New`, `Initialize_{table}_PostFetch`, `Initialize_{table}_Duplication` | 4 |
| 11 | Pre/Post actions | `Initialize_{table}_PreInsert`, `PreUpdate`, `PostInsert`, `PostUpdate`, `PreDelete`, `PostDelete` | 6 |
| 12 | Autorisations | `Authorize_{table}_Insert`, `Update`, `Delete` | 3 |
| 13 | Reservation | `Reservation_{table}_Lock/Shift/Share/UnLock` + `Res_{table}_Lock/Shift/Share/UnLock` | 8 |
| 14 | Utilitaires | `Call_{TABLE}_OpenZoom`, `Load_{TABLE}_ID`, `GET_{TABLE}_TRANSLATE_LIBELLE` | 3 |

**Total : ~52 fonctions** pour une entite de reference (Retail FamRglt).

---

## Conventions de nommage dans le mchk

| Element | Convention | Exemple |
|---------|-----------|---------|
| Fonctions de donnees | `{TABLE_MAJUSCULE}` | `Check_RTLFAMRGLT` |
| Fonctions d'init/autorisation | `{entity}` (PascalCase) ou `{table_minuscule}` | `Initialize_rtlfamrglt_New`, `Authorize_rtlfamrglt_Insert` |
| Instance RecordSql | `RS_{NomVue}` | `RS_FamRgltRtl` |
| ChkData | `ChkData_{TABLE_MAJUSCULE}` | `ChkData_RTLFAMRGLT` |
| Record INIT | `{table_minuscule}_INIT` | `rtlfamrglt_INIT` |
| FieldNames_Min | `{TABLE_MAJUSCULE}_FieldNames_Min` | `RTLFAMRGLT_FieldNames_Min` |

---

## Tokens Jinja2 utilises

Le template `mchk.dhsp.j2` utilise les tokens suivants de `compute_names.py` :

| Token | Usage dans le template |
|-------|----------------------|
| `fichier_mchk` | SetModuleInfo, nom du fichier |
| `date` | SetModuleInfo |
| `Description` | Commentaire d'en-tete |
| `overwrittenby_mchk` | OverWrittenBy |
| `domaine_2l` | Includes et Modules |
| `DICT` | Dictionnaire (.dhsd) |
| `table_minuscule` | Records, variables, fonctions init/autorisation |
| `TABLE_MAJUSCULE` | ChkData, FieldNames, fonctions de donnees |
| `CHAMPCLE` | FieldNames_Min, FieldProperties |
| `ChampCle` | Parametres de fonctions |
| `NomVue` | RS_instance, Seek, reservation |
| `PREFIX_` | Appels framework (RT_, GT_, etc.) |
| `prefix_db` | Module ficsql |
| `base` | Fichier .dhoq |
| `PREFIXRES` | Reservation |
| `entity` | Fonctions init/autorisation |

Tokens derives (calcules par `generate_mchk.py`) :

| Token | Derivation |
|-------|-----------|
| `NOMVUE_MAJUSCULE` | `NomVue.upper()` |
| `ChampCle_lower` | `ChampCle` avec 1ere lettre minuscule |
