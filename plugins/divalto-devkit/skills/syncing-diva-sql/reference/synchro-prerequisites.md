# Prerequis synchronisation SQL

## Prerequis obligatoires

### 1. Compilation buildall avec 0 erreur

La synchronisation SQL opere sur les **objets compiles** par buildall. Si la compilation contient des erreurs, les objets sont incoherents et la synchronisation produirait des resultats invalides (tables manquantes, colonnes incorrectes).

**Verification** :
```bash
py .claude/skills/compiling-diva-projects/scripts/parse_compilation.py \
    --path "chemin/rapport_buildall.txt"
```
→ `"success": true` et `"errors": 0` requis.

### 2. Working directory = C:\divalto\sys

xwin7 synchroauto **exige** que le repertoire courant soit `C:\divalto\sys`. Sans cela, erreur code 3.

```powershell
$SavedDir = Get-Location
Set-Location "C:\divalto\sys"
# ... synchroauto ...
Set-Location $SavedDir
```

**Important** : toujours sauvegarder et restaurer le repertoire courant.

### 3. Meme projet et profil que buildall

Les parametres `-project` et `-profile` doivent etre **identiques** a ceux du buildall precedent. Synchroauto opere sur les objets compiles dans le repertoire de sortie lie au profil.

### 4. xwin7.exe accessible

`C:\divalto\sys\xwin7.exe` doit exister et etre executable.

### 5. Script .ps1 en ISO-8859-1

Si le profil contient un accent (`développement`), le script PowerShell doit etre encode en ISO-8859-1 (pas UTF-8). Sinon xwin7 ne reconnait pas le profil.

---

## Erreur code 3 -- Working directory incorrect

**Symptome** : synchroauto retourne une erreur code 3, rapport vide ou incomplet.

**Cause** : le working directory n'est pas `C:\divalto\sys` au moment de l'appel.

**Solution** : `Set-Location "C:\divalto\sys"` avant d'appeler xwin7 synchroauto.

---

## Enchainement buildall → synchroauto

Pattern type :

```powershell
# 1. Compiler
xwin7 -action buildall -project $Projet -profile $Profil -output $LogBuild -outputall | Out-Null

# 2. Verifier 0 erreur
$content = Get-Content $LogBuild
if ($content -match 'Erreur\(s\)=0') {
    # 3. Synchroniser
    $SavedDir = Get-Location
    Set-Location "C:\divalto\sys"
    xwin7 -action synchroauto -project $Projet -profile $Profil -output $LogSynchro -outputall | Out-Null
    Set-Location $SavedDir
} else {
    Write-Host "Compilation en erreur, synchro annulee"
}
```
