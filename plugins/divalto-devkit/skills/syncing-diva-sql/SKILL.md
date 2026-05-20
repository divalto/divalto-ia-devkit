---
name: syncing-diva-sql
description: >
  Synchronise la base SQL Server a partir des dictionnaires compiles via xwin7 synchroauto.
  Parse le rapport de synchronisation et presente les erreurs.
  A utiliser apres une compilation buildall reussie (0 erreur) pour mettre a jour la base SQL.
---

# syncing-diva-sql

## Contenu

- Utilisation rapide
- Workflow complet (3 etapes)
- Parsing du rapport
- Scripts disponibles
- References

---

## Utilisation rapide

### Lancer une synchronisation

```powershell
# IMPORTANT : le working directory doit etre C:\divalto\sys
$SavedDir = Get-Location
Set-Location "C:\divalto\sys"

C:\divalto\sys\xwin7.exe -action synchroauto `
    -project "C:\...\projet\divalto achat-vente.dhpt" `
    -profile "développement" `
    -output "C:\...\Log\Synchro.txt" `
    -outputall | Out-Null

Set-Location $SavedDir
```

**Prerequis critique** : compilation buildall avec **0 erreur** sur le meme projet/profil. Sans cela, les objets compiles sont incoherents → synchro invalide.

### Parser le rapport

```bash
py .claude/skills/syncing-diva-sql/scripts/parse_synchro.py \
    --path "C:/chemin/Log/Synchro.txt"
```

---

## Workflow complet

### Etape 1 -- Verifier les prerequis

Avant synchronisation :
1. **Compilation buildall reussie** : `Erreur(s)=0` dans le rapport buildall (voir compiling-diva-projects)
2. **Working directory** : `C:\divalto\sys` (sinon erreur code 3)
3. **Meme projet et profil** que le buildall precedent
4. Fichier .dhpt valide (voir managing-diva-projects)
5. Script .ps1 en ISO-8859-1 si profil avec accent

### Etape 2 -- Synchroniser

```powershell
$SavedDir = Get-Location
Set-Location "C:\divalto\sys"

xwin7 -action synchroauto `
    -project $Projet -profile $Profil `
    -output $LogSynchro -outputall | Out-Null

Set-Location $SavedDir
```

**Avec environnement** (deux commandes separees) :
```powershell
Set-Location "C:\divalto\sys"
xwin7 -select_environment $Environnement -outputall | Out-Null
xwin7 -action synchroauto -project $Projet -profile $Profil -output $LogSynchro -outputall | Out-Null
```

### Etape 3 -- Analyser le rapport

```bash
py .claude/skills/syncing-diva-sql/scripts/parse_synchro.py \
    --path "chemin/rapport.txt"
```

Si `success: true` → synchronisation SQL reussie, base a jour.
Si `success: false` → corriger les erreurs et relancer.

---

## Parsing du rapport

### Marqueur de resultat

Le rapport de synchronisation utilise le marqueur `[TOTAL_ERRORS]N` :

```
[TOTAL_ERRORS]0
```

| Valeur | Signification |
|--------|---------------|
| `[TOTAL_ERRORS]0` | Synchronisation reussie |
| `[TOTAL_ERRORS]N` (N > 0) | N erreurs de synchronisation |

**Attention** : ce format est different de buildall qui utilise `Erreur(s)=N`.

### Erreurs dans le rapport

Les erreurs de synchronisation apparaissent dans le corps du rapport avant la ligne `[TOTAL_ERRORS]`. Le script `parse_synchro.py` extrait :
- Le nombre total d'erreurs
- Les lignes d'erreur avec contexte

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `parse_synchro.py` | Parse rapport synchroauto | --path fichier.txt | JSON (success, total_errors, errors) |

**Exit codes** : 0 = synchronisation reussie, 1 = erreurs trouvees, 2 = rapport illisible.

---

## References

- [Prerequis synchronisation](reference/synchro-prerequisites.md) -- prerequis detailles, erreur code 3, working directory
- [Format du rapport](reference/synchro-report.md) -- marqueur [TOTAL_ERRORS], erreurs courantes
