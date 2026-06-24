# Format du rapport synchroauto

## Marqueur de resultat

Le rapport de synchronisation SQL utilise le marqueur `[TOTAL_ERRORS]N` pour indiquer le nombre d'erreurs :

```
[TOTAL_ERRORS]0
```

| Valeur | Signification |
|--------|---------------|
| `[TOTAL_ERRORS]0` | Synchronisation reussie, base SQL a jour |
| `[TOTAL_ERRORS]N` (N > 0) | N erreurs de synchronisation |

**Attention** : ce format est **different** de buildall :
- buildall : `Erreur(s)=N`
- synchroauto : `[TOTAL_ERRORS]N`

Ne pas confondre les deux parsers.

---

## Structure du rapport

Le rapport synchroauto contient :
1. Les operations executees (CREATE TABLE, ALTER TABLE, etc.)
2. Les messages d'erreur eventuels
3. La ligne `[TOTAL_ERRORS]N` en fin de rapport

---

## Delta de schema (ce qui change reellement)

La synchro produit un **vrai delta**, pas un DROP+CREATE en bloc (sauf **table
neuve** : `DROP TABLE` conditionnel + `CREATE TABLE`). Sur une table existante :

```sql
ALTER TABLE [dbo].[ART] DROP COLUMN [MIMARQUE],[MIMISESERVICEDT],[MIMODELE]
ALTER TABLE [dbo].[ART] ADD [TESTRAJOUT] numeric(1,0) default 0 NOT NULL
DROP INDEX [MI_ARTMODELE] ON [dbo].[ART]
```

**Sauvegarde avant DROP COLUMN** : la synchro cree d'abord une table
`<TABLE>_oldcolumns` + `INSERT INTO ... SELECT` pour preserver les donnees des
colonnes supprimees. Ce sont des **artefacts de sauvegarde**, pas des changements de
schema -> a ignorer dans un resume de delta.

**En-tetes machine-readable** (script `.sql`) : chaque bloc est precede d'un
commentaire de flags, ex. :

```
/* <ifAlterTable>1<ifTableName>ART<ifAlterTableDropColumn>1<champ>MIMARQUE,3,20,0;... */
```

Indicatifs (`<ifTableName>` ne suit pas toujours la table reelle sur les blocs ADD) :
la **source de verite reste l'instruction DDL** (`ALTER TABLE [dbo].[X] ...`).

**Procedures `ERASE_*`** (truncate par module) : regenerees (DROP+CREATE) a chaque
synchro -> boilerplate, pas un changement de schema.

### Resume automatique : `--changes`

```bash
py parse_synchro.py --path <rapport.txt|DhOdbcConfigSql.log|...Script.sql> --changes
```

Extrait le delta groupe par table (`add_columns` / `drop_columns` / `create_index` /
`drop_index` / `created` / `dropped`) + `procedures` + `functions`, en filtrant le
bruit ci-dessus. Marche sur le rapport `synchroauto` **et** sur le log/script d'audit
`C:\divalto\DivaltoLog\DhOdbcConfigSql.log` / `DhOdbcConfigSqlScript.sql`.

## Apercu avant application (dry-run)

Pas de dry-run **natif** dans `xwin7 synchroauto`. Un apercu est possible **par
programmation** via le mecanisme `ModeAudit` (cf. doc Divalto « Synchronisation du
schema de la base par programmation »). A defaut, le mode `--changes` ci-dessus donne
le delta **a posteriori** (apres execution).

---

## Erreurs courantes

### Erreur de connexion SQL Server

**Symptome** : echec connexion, message contenant "connection" ou "login"
**Cause** : SQL Server inaccessible ou credentials incorrects
**Solution** : verifier la connexion SQL Server dans la configuration Divalto

### Table deja existante avec structure incompatible

**Symptome** : erreur ALTER TABLE
**Cause** : la table SQL existe deja avec une structure differente (colonne supprimee, type modifie)
**Solution** : verifier la coherence entre le dictionnaire .dhsd et la table SQL existante

### Droits insuffisants

**Symptome** : erreur "permission denied" ou equivalent
**Cause** : le compte SQL utilise n'a pas les droits CREATE/ALTER sur la base
**Solution** : verifier les permissions du compte SQL configure dans Divalto

### Colonne utilisee par une vue ou contrainte

**Symptome** : erreur lors d'un ALTER TABLE DROP COLUMN
**Cause** : la colonne a supprimer est referencee par une vue, un index, ou une contrainte
**Solution** : supprimer la dependance manuellement avant de relancer la synchro

---

## Parsing PowerShell

```powershell
$synchroErrors = Get-Content $LogSynchro | Select-String '\[TOTAL_ERRORS\]'
if ($synchroErrors.Line -match '\[TOTAL_ERRORS\]0') {
    Write-Host "Synchronisation SQL OK" -ForegroundColor Green
} else {
    Write-Host "Erreurs de synchronisation detectees" -ForegroundColor Red
    Get-Content $LogSynchro
}
```

---

## Parsing Python

```bash
py .claude/skills/syncing-diva-sql/scripts/parse_synchro.py --path rapport.txt
```

Sortie JSON :
```json
{
    "file": "rapport.txt",
    "success": true,
    "total_errors": 0,
    "errors": []
}
```
