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
