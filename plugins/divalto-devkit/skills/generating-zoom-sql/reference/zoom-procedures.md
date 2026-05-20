# Procedures obligatoires du Zoom SQL

Source : `rttzfamrglt_sql.dhsp` (303 lignes, ERP X.13).

---

## Les 27 procedures

| # | Procedure | Role | Contenu typique |
|---|-----------|------|-----------------|
| 1 | `Construire_Condition_Selection` | Construit les clauses WHERE de filtrage | Like_{ChampCle}, Like_Libelle, AddCondition |
| 2 | `ZoomDebut` | Initialisation du zoom | Init_Zoom, Load_Gtfdos, TitreFixe, gestion Scevaleur |
| 3 | `ZoomAbandon` | Sortie sans validation | Vide (stub) |
| 4 | `ZoomValidation` | Validation retour | `Zoom.Valretour = {NomVue}.{ChampCle}` |
| 5 | `ZoomFin` | Nettoyage a la sortie | Vide (stub) |
| 6 | `ZoomCreation` | Avant creation | Authorize_Insert + Init + Initialize_New |
| 7 | `ZoomDuplication` | Avant duplication | Authorize_Insert + Initialize_Duplication |
| 8 | `ZoomApresCleCreation` | Apres saisie cle | Check_Key + Where.Exists + Reservation |
| 9 | `ZoomCreationRes` | Apres reservation creation | Vide (stub) |
| 10 | `ZoomAvantWrite` | Avant ecriture | Check + PreInsert |
| 11 | `ZoomApresCreation` | Apres creation | PostInsert + TitreVariable |
| 12 | `ZoomModification` | Avant modification | Authorize_Update + Reservation |
| 13 | `ZoomModificationRes` | Apres reservation modif | Vide (stub) |
| 14 | `ZoomAvantRewrite` | Avant reecriture | Check + PreUpdate(majuser=true) |
| 15 | `ZoomApresModification` | Apres modification | PostUpdate + TitreVariable |
| 16 | `ZoomSuppression` | Avant suppression | Authorize_Delete + Reservation |
| 17 | `ZoomSuppressionRes` | Apres reservation suppr | Vide (stub) |
| 18 | `ZoomAvantDelete` | Avant suppression | PreDelete |
| 19 | `ZoomApresSuppression` | Apres suppression | PostDelete |
| 20 | `ZoomAvantConsult` | Avant consultation | Vide (stub) |
| 21 | `ZoomConsult` | Actions en consultation | F7 = Zoom_Call() |
| 22 | `ZoomAvantInput` | Avant saisie | Vide (stub) |
| 23 | `ZoomArret` | Points d'arret | F8, clic droit, double-clic |
| 24 | `ZoomFiltreAvantValeur` | Avant valeur filtre | Vide (stub) |
| 25 | `ZoomFiltreApresValeur` | Apres valeur filtre | Vide (stub) |
| 26 | `ZoomApresCle` | Apres saisie cle | Construire_Condition_Selection |
| 27 | `ZoomApresRead` | Apres lecture | TitreVariable |

---

## Patterns recurrents

| Code | Signification | Usage |
|------|---------------|-------|
| `Zoom.OK = 'I'` + `preturn` | Interdire l'action | ZoomCreation, ZoomDuplication, ZoomModification, ZoomSuppression |
| `Zoom.Ok = 'S'` + `Preturn` | Stopper avant ecriture (erreur controle) | ZoomAvantWrite, ZoomAvantRewrite |
| `Zoom.Ok = 'O'` | Operation reussie | ZoomApresCreation, ZoomApresModification, ZoomApresSuppression |
| `Zoom.ok = 'C'` | Erreur sur la cle | ZoomApresCleCreation |

**Note** : DIVA est case-insensitive sur les identifiants. `Zoom.OK` = `Zoom.Ok` = `Zoom.ok`.

---

## Structure d'en-tete

```
SetModuleInfo('$Id: {fichier_zoom} 1 {date} user $')
;>xdiva
;*  {Description} ( {TABLE_MAJUSCULE} )

OverWrittenBy '{overwrittenby_zoom}'

Include 'GTTCZ00.dhsp'

Module  '{module_mchk}'
Module  '{module_ficsql}'

HFileVersion  {DICT}.dhsd {TABLE_MAJUSCULE}

Public RecordSql '{fichier_rsql_compile}' {NomVue}
Public RecordSql '{fichier_rsql_compile}' {NomVue}  {NomVue}_Sel

Define ChaineReservation = [ Formater_Res('{PREFIXRES}') {NomVue}.Dos {NomVue}.{ChampCle} ]
Define TitreVariable     = [ {NomVue}.{ChampCle} *1 '-' *1 {NomVue}.Libelle ]
```

---

## Tokens Jinja2 utilises

| Token | Usage |
|-------|-------|
| `fichier_zoom` | SetModuleInfo |
| `date` | SetModuleInfo |
| `Description` | Commentaire + Zoom.TitreFixe |
| `TABLE_MAJUSCULE` | HFileVersion, Check_* |
| `overwrittenby_zoom` | OverWrittenBy |
| `module_mchk` | Module mchk |
| `module_ficsql` | Module ficsql |
| `DICT` | HFileVersion |
| `fichier_rsql_compile` | RecordSql declaration |
| `NomVue` | Instance RecordSql |
| `ChampCle` | Filtres, conditions, Valretour |
| `table_minuscule` | Parametres fonctions mchk |
| `PREFIX_` | Appels framework (RT_, GT_, etc.) |
| `PREFIXRES` | ChaineReservation |
