# Syntaxe xwin7.exe

## Emplacement

```
C:\divalto\sys\xwin7.exe
```

---

## Commandes de compilation

### Compilation complete (buildall)

```powershell
xwin7 -action buildall -project "chemin\projet.dhpt" -profile "développement" -output "chemin\log.txt" -outputall
```

### Compilation incrementale (build)

```powershell
xwin7 -action build -project "chemin\projet.dhpt" -profile "développement" -output "chemin\log.txt" -outputall
```

Ne recompile que les fichiers modifies depuis la derniere compilation. A privilegier en developpement iteratif.

### Parametres

| Parametre | Description | Obligatoire | Exemple |
|-----------|-------------|-------------|---------|
| `-action buildall` | Compilation complete du projet | Oui (ou `build`) | `buildall` |
| `-action build` | Compilation incrementale (fichiers modifies uniquement) | Oui (ou `buildall`) | `build` |
| `-user` | Code utilisateur. **Recommande**. Chaine de fallback : (1) `-user XX` explicite, (2) `X_USER` env, (3) omis = utilisateur Windows courant [A VERIFIER : fonctionne sur certains postes] | Recommande | `-user SC` |
| `-project` | Chemin du fichier .dhpt | Oui | `"C:\...\divalto achat-vente.dhpt"` |
| `-sousproject` | Nom du sous-projet (.dhps). Limite le scope aux fichiers du sous-projet, mais pas d'impact sur la duree (le projet complet est charge). **Attention** : ne recompile PAS les fichiers [communs] du .dhpt parent. | Non | `-sousproject "a5_zoom dossier.dhps"` |
| `-profile` | Nom du profil de compilation | Oui | `"développement"` (avec accent) |
| `-output` | Chemin du fichier rapport | Oui | `"C:\...\Log\Compilation.txt"` |
| `-outputall` | Inclure tous les details dans le rapport | Recommande | _(flag sans valeur)_ |
| `-select_environment` | Selectionner l'environnement avant compilation | Conditionnel | `"vx13"` |

### -select_environment

- Utiliser **uniquement si** le .dhpt est lie a un environnement configure dans Divalto
- Pour les projets autonomes : **omettre** ce parametre (l'inclure provoque une erreur)
- Si necessaire, l'appel se fait en **deux commandes separees** :

```powershell
xwin7 -select_environment $Environnement -outputall | Out-Null
xwin7 -action buildall -project $Projet -profile $Profil -output $LogFile -outputall | Out-Null
```

---

## Autres actions xwin7

| Action | Role |
|--------|------|
| `buildall` | Compilation complete du projet |
| `build` | Compilation incrementale (fichiers modifies uniquement) |
| `synchroauto` | Synchronisation SQL (voir syncing-diva-sql) |
| `fusionbasesurcharge` | Fusion d'une base et d'une surcharge |
| `fusionprojets` | Fusion de projets (surcharge) |
| `generationprojets` | Generation de projets derives |
| `copierfichiers` | Copie des fichiers sources |
| `copiergroupes` | Copie des groupes objets |

---

## Encodage du script PowerShell

**Regle critique** : si le script .ps1 contient le nom de profil avec accent (`développement`), le fichier .ps1 doit etre en **ISO-8859-1**.

```bash
# Verification
file --mime-encoding script.ps1
# Attendu : iso-8859-1, unknown-8bit, ou us-ascii
# JAMAIS : utf-8

# Conversion si necessaire
iconv -f UTF-8 -t ISO-8859-1 script.ps1 > script_iso.ps1
mv script_iso.ps1 script.ps1
```

Si le .ps1 est en UTF-8, l'accent `é` est encode en 2 octets (`0xC3 0xA9`) au lieu de 1 (`0xE9`). xwin7 compare le nom du profil en ISO-8859-1, donc la correspondance echoue → erreur "Profil absent du projet".

### Pourquoi le passage en argument direct echoue

PowerShell 5.1 (la version par defaut sous Windows 10/11 sans installation supplementaire) stocke les chaines en **UTF-16 LE en memoire**. Quand une session PowerShell normale lance `xwin7.exe` avec un argument litteral type `-profile "developpement"` (e accent aigu), la couche de conversion vers les arguments natifs du processus enfant ne preserve PAS l'octet `0xe9` (ISO-8859-1) attendu par xwin7 -- selon la code page console active, la chaine peut etre re-encodee en UTF-8 (`0xc3 0xa9`) ou en CP1252 selon les cas, et la comparaison echoue silencieusement cote xwin7 (qui lit les octets bruts en ISO-8859-1).

**Symptomes terrain (R-005)** :
- Tentative 1 -- PowerShell + `[char]0x00e9` pour construire la chaine -> ExitCode vide, log absent.
- Tentative 2 -- PowerShell + `Start-Process` + ArgumentList contenant `'developpement'` litteral -> ExitCode=1, log absent.
- Tentative 3 (reussie) -- creer un script `.ps1` en ISO-8859-1 + CRLF contenant `$Profil = "developpement"` litteral, puis l'executer via `powershell -File <script.ps1>`. xwin7 parvient enfin a matcher le nom de profil avec celui du `.dhpt`.

### Pattern operationnel -- script .ps1 ISO-8859-1

```powershell
# script.ps1 -- a ecrire en ISO-8859-1 + CRLF !
$ErrorActionPreference = 'Continue'
Set-Location 'C:\divalto\sys'
$proc = Start-Process -FilePath 'C:\divalto\sys\xwin7.exe' `
    -ArgumentList '-action build -project "C:\...\projet.dhpt" -profile "developpement" -output "C:\...\log.txt" -outputall' `
    -Wait -PassThru -NoNewWindow `
    -RedirectStandardOutput 'C:\...\log\stdout.txt' `
    -RedirectStandardError 'C:\...\log\stderr.txt'
Write-Host "ExitCode: $($proc.ExitCode)"
exit $proc.ExitCode
```

L'execution : `powershell -NoProfile -ExecutionPolicy Bypass -File script.ps1`. Le contenu du `.ps1` etant stocke en bytes ISO-8859-1, PowerShell lit l'octet `0xe9` natif et le transmet a xwin7 sans re-encodage casseur.

### Recette automatisee -- `scripts/compile_project.py`

Pour eviter de regenerer ce pattern a la main a chaque compilation, **utiliser `scripts/compile_project.py`** qui :
1. Genere le `.ps1` en ISO-8859-1 + CRLF (cf. `write_iso()`)
2. Le pose dans le meme repertoire que le log (ou `--ps1-dir` si specifie)
3. L'execute via `powershell -ExecutionPolicy Bypass -File`
4. Capture stdout / stderr / exit code
5. Parse la ligne de resume du log pour determiner `success`
6. Retourne un JSON structure

Equivalent fonctionnel de `generate_harness.py` mais pour des projets reels (pas des harnesses standalone). Cf. SKILL.md section "Etape 3 -- Compiler" pour le mode d'emploi.
