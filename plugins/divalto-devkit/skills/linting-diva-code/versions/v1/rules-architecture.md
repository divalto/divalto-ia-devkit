# Regles Architecture Zoom (Z01-Z12) et Module Check (M01-M05)

## Architecture Zoom

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| Z01 | *V2* | Procedures zoom obligatoires manquantes | Liste des 27 procedures requises |
| Z02 | warning | `Zoom.OK = 'I'/'S'/'C'` sans `preturn` apres | Regex: affectation Zoom.OK puis absence de preturn |
| Z03 | warning | Prefixes de domaine mixtes dans un meme zoom | Regex: detecter GT_*, RT_*, GG_* dans un meme fichier |
| Z04-Z07 | *V2* | Mauvais prefixe domaine selon le module | Necessite metadata module |
| Z08 | warning | `Module 'xxpmficsql.dhop'` manquant | Regex: utilisation de GT_*/RT_*/GG_* sans Module correspondant |
| Z09 | *V2* | Alias manquants dans gtpmficsql.dhop | Analyse cross-file |
| Z10 | *V2* | Mode selection `-` non gere | Analyse semantique |
| Z11 | warning | `Initialize_*_PostFetch` manquant apres `Seek_*` | Regex: Seek_* sans PostFetch dans les 5 lignes suivantes |
| Z12 | warning | `SetPrefixeModule` manquant dans fonction wrapper | Regex: Procedure/Function avec prefixe domaine, sans SetPrefixeModule |

## Module Check (mchk)

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| M01 | warning | `Init_Module` sans `GT_Get_CheckObject_Data` | Regex: Procedure Init_Module sans appel GT_Get_CheckObject_Data |
| M02 | warning | Record non initialise dans `Init_Module` | Regex: Init_Module sans affectation INIT du record principal |
| M03 | warning | `A5_Stack_OutputMode`/`A5_UnStack_OutputMode` non apparies | Regex: compter Stack vs UnStack |
| M04 | warning | `GT_PreUpdate_recordSql` sans `majuser=true` | Regex: appel sans parametre majuser |
| M05 | warning | Validation de champ optionnel sans test `<> ' '` | Regex: Check_*_Field_* sans test non-vide |

## Detection des prefixes domaine

Les fonctions framework sont prefixees par domaine :
- `GT_*` : gestion commerciale (DAV)
- `RT_*` : Retail
- `GG_*` : Production

Un fichier zoom ne doit utiliser qu'un seul prefixe domaine.
