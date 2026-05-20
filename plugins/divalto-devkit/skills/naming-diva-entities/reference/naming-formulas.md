# Formules de nommage

Formules deterministes pour deriver tous les tokens a partir du triplet (domaine, entite, table SQL).

Source : `docs/CONVENTIONS.md` et `docs/SQUELETTES.md`.

---

## Parametres d'entree

| Parametre | Format | Exemple |
|-----------|--------|---------|
| `domaine` | Nom canonique | `Retail` |
| `entite` | PascalCase | `FamRglt` |
| `table_sql` | PascalCase (prefixe DB inclus) | `RtlFamRglt` |
| `champ_cle` | PascalCase | `RgltFam` |
| `description` | Texte libre | `Famille de reglement` |

---

## Tokens derives — Fichiers

| Token | Formule | Exemple |
|-------|---------|---------|
| `fichier_rsql` | `{prefix_db}rs{base}.dhsq` | `rtlrsfamrglt.dhsq` |
| `fichier_rsql_compile` | `{prefix_db}rs{base}.dhoq` | `rtlrsfamrglt.dhoq` |
| `fichier_rsql_surcharge` | `{prefix_db}rs{base}u.dhoq` | `rtlrsfamrgltu.dhoq` |
| `fichier_zoom` | `{prefix_module}z{entity_lower}_sql.dhsp` | `rttzfamrglt_sql.dhsp` |
| `fichier_zoom_surcharge` | `{prefix_module_u}z{entity_lower}_sql.dhop` | `rtuzfamrglt_sql.dhop` |
| `fichier_mchk` | `{prefix_module}mchk{entity_lower}.dhsp` | `rttmchkfamrglt.dhsp` |
| `fichier_mchk_surcharge` | `{prefix_module_u}mchk{entity_lower}.dhop` | `rtumchkfamrglt.dhop` |
| `fichier_masque` | `{domaine_2l}ez{entity_lower}_sql.dhsf` | `rtezfamrglt_sql.dhsf` |
| `fichier_masque_compile` | `{domaine_2l}ez{entity_lower}_sql.dhof` | `rtezfamrglt_sql.dhof` |

**base** = `table_sql.lower()` apres suppression du `prefix_db`. Ex: `RtlFamRglt` - `rtl` = `famrglt`.

---

## Tokens derives — Instances

| Token | Formule | Exemple |
|-------|---------|---------|
| `NomVue` | `{entite}{prefix_db.capitalize()}` | `FamRgltRtl` |
| `RS_instance` | `RS_{NomVue}` | `RS_FamRgltRtl` |
| `instance_sel` | `{NomVue}_Sel` | `FamRgltRtl_Sel` |
| `record_init` | `{table_minuscule}_INIT` | `rtlfamrglt_INIT` |
| `shared_record` | `{table_minuscule}` | `rtlfamrglt` |
| `ChkData` | `ChkData_{TABLE_MAJUSCULE}` | `ChkData_RTLFAMRGLT` |
| `FieldNames_Min` | `{TABLE_MAJUSCULE}_FieldNames_Min` | `RTLFAMRGLT_FieldNames_Min` |

---

## Tokens derives — Define

| Token | Formule | Exemple |
|-------|---------|---------|
| `ChaineReservation` | `Formater_Res('{PREFIXRES}') {NomVue}.Dos {NomVue}.{ChampCle}` | `Formater_Res('RTTB') FamRgltRtl.Dos FamRgltRtl.RgltFam` |
| `TitreVariable` | `{NomVue}.{ChampCle} *1 '-' *1 {NomVue}.Libelle` (si has_libelle, sinon `{NomVue}.{ChampCle}`) | `FamRgltRtl.RgltFam *1 '-' *1 FamRgltRtl.Libelle` |
| `PREFIXRES` | `({prefix_module} + 'B').upper()[:4]` | `RTTB` |

---

## Tokens derives — Surcharges et modules

| Token | Formule | Exemple |
|-------|---------|---------|
| `overwrittenby_zoom` | `{MODULEPREFIX_U}Z{ENTITY}_SQL.dhop` | `RTUZFAMRGLT_SQL.dhop` |
| `overwrittenby_mchk` | `{prefix_module_u}mchk{entity_lower}.dhop` | `rtumchkfamrglt.dhop` |
| `overwrittenby_rsql` | `{prefix_db}rs{base}u.dhoq` | `rtlrstabu.dhoq` |
| `module_mchk` | `{prefix_module}mchk{entity_lower}.dhop` | `rttmchkfamrglt.dhop` |
| `FichierDico` | `{prefix_db.capitalize()}{entite}` | `RtlFamRglt` |
| `module_ficsql` | Depuis registre domaine | `rtpmficsql.dhop` |

---

## Recapitulatif rapide — Exemple complet Retail FamRglt

```
Entree : domaine=Retail, entite=FamRglt, table=RtlFamRglt, champ_cle=RgltFam

Fichiers :
  rtlrsfamrglt.dhsq        (RecordSql source)
  rttzfamrglt_sql.dhsp     (Zoom)
  rttmchkrtlfamrglt.dhsp   (Module check)

Instances :
  NomVue          = FamRgltRtl
  RS_FamRgltRtl   (instance globale RecordSql)
  FamRgltRtl_Sel  (instance selection)
  rtlfamrglt_INIT (record init)
  rtlfamrglt      (shared record)

Define :
  ChkData_RTLFAMRGLT
  RTLFAMRGLT_FieldNames_Min
  ChaineReservation = Formater_Res('RTTB') FamRgltRtl.Dos FamRgltRtl.RgltFam
  TitreVariable     = FamRgltRtl.RgltFam *1 '-' *1 FamRgltRtl.Libelle
```
