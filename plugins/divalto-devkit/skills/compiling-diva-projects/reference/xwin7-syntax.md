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
| `-user` | Code utilisateur. Chaine de fallback (`compile_project.py`) : (1) `--user XX`, (2) **`util=` du `.dhpt`** (#235), (3) `X_USER` env, (4) omis = `USERNAME` Windows | Recommande | `-user <CODE>` |
| `-project` | Chemin du fichier .dhpt | Oui | `"C:\...\divalto achat-vente.dhpt"` |
| `-sousproject` | Nom du sous-projet (.dhps). Limite le scope aux fichiers du sous-projet, mais pas d'impact sur la duree (le projet complet est charge). **Attention** : ne recompile PAS les fichiers [communs] du .dhpt parent. | Non | `-sousproject "a5_zoom dossier.dhps"` |
| `-profile` | Nom du profil de compilation | Oui | `"développement"` (avec accent) |
| `-output` | Chemin du fichier rapport | Oui | `"C:\...\Log\Compilation.txt"` |
| `-outputall` | Inclure tous les details dans le rapport | Recommande | _(flag sans valeur)_ |
| `-select_environment` | Met a jour des cles registre (`Courant`/`ServeurXlogf`) mais **ne fait PAS** un chargement complet d'environnement -> **non utilise par ce skill** (cf. ci-dessous) | Non utilise | — |

### -select_environment (non utilise par ce skill -- #346)

`-select_environment` **ne realise pas** un chargement complet d'environnement : il se contente de mettre a jour des cles de registre (`HKCU:\Software\Divalto\divalto.ini\Environnement` -> `Courant`, `System` -> `ServeurXlogf`). Verifier ces cles fait donc **croire a tort** que la bascule a reussi (#346), alors que l'implicite/les packs/les serveurs ne sont pas charges.

Un chargement complet d'environnement (ODBC, serveurs, packs, add-on, **implicite actif**) releve de l'**outillage d'environnement du poste**, pas de ce skill. **En pratique, ce skill ne bascule pas d'environnement** : assure-toi que le bon environnement est **deja charge** avant de compiler, et valide la coherence environnement/implicite <-> `.dhpt` avec le skill `understanding-integrator-workspace` (cf. « Discipline d'environnement » du SKILL.md).

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
| `creerprojetsurcharge` | Cree la surcharge version N depuis la surcharge N-1 -- voir ci-dessous |
| `mettreAJourMasquesSurcharge` | Reporte les pages du masque d'origine dans les masques de surcharge -- voir ci-dessous |

> **Montee de version d'une surcharge : la syntaxe vit dans `migrating-erp-downgrade`.**
> Les deux dernieres actions ci-dessus appartiennent au rebase de pack (passage d'un Service
> Pack a l'autre) : parametres, pieges et lecture du journal `FUpgrade.log` sont documentes
> dans `migrating-erp-downgrade/reference/montee-version-surcharge.md`.
>
> Elles sont **listees ici** parce que c'est la page ou l'on cherche une action `xwin7` -- un
> retour terrain les y a cherchees et ne les a pas trouvees. **La reference reste unique** :
> cette table nomme, l'autre page explique.

---

## Encodage du script PowerShell

**Regle critique** : si le script .ps1 contient le nom de profil avec accent (`développement`), le fichier .ps1 doit etre en **ISO-8859-1**.

> **Une SECONDE cause, distincte, impose parfois le meme encodage.** PowerShell 5.1 lit un `.ps1` **sans BOM** en ANSI : un chemin accentue ecrit **en dur dans le script** est corrompu avant meme que `xwin7` soit appele. La regle ci-dessus porte sur l'**argument transmis a xwin7** ; l'autre porte sur le **script relu par PowerShell**. Corriger l'une ne dispense pas de verifier l'autre -- detail dans le skill `writing-diva-files`.

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

**Symptomes terrain** :
- Tentative 1 -- PowerShell + `[char]0x00e9` pour construire la chaine -> ExitCode vide, log absent.
- Tentative 2 -- PowerShell + `Start-Process` + ArgumentList contenant `'developpement'` litteral -> ExitCode=1, log absent.
- Tentative 3 (reussie) -- creer un script `.ps1` en ISO-8859-1 + CRLF contenant le profil litteral, puis l'executer (reco courante #217 : via l'operateur d'appel `& '<ps1>'`, **pas** `-ExecutionPolicy Bypass -File` -- cf. Pattern operationnel ci-dessous). xwin7 parvient enfin a matcher le nom de profil avec celui du `.dhpt`.

### Pattern operationnel -- script .ps1 ISO-8859-1

```powershell
# script.ps1 -- a ecrire en ISO-8859-1 + CRLF !
$ErrorActionPreference = 'Continue'
Set-Location '<dossier de xwin7.exe>'   # derive du chemin de xwin7, pas code en dur (#301)
$proc = Start-Process -FilePath 'C:\divalto\sys\xwin7.exe' `
    -ArgumentList '-action build -project "C:\...\projet.dhpt" -profile "developpement" -output "C:\...\log.txt" -outputall' `
    -Wait -PassThru -NoNewWindow `
    -RedirectStandardOutput 'C:\...\log\stdout.txt' `
    -RedirectStandardError 'C:\...\log\stderr.txt'
Write-Host "ExitCode: $($proc.ExitCode)"
exit $proc.ExitCode
```

L'execution : `powershell -NoProfile -Command "& 'script.ps1'; exit $LASTEXITCODE"` (operateur d'appel). **Ne pas** utiliser `-ExecutionPolicy Bypass -File` : sur un poste integrateur verrouille, `-ExecutionPolicy Bypass` en ligne de commande est soit surcharge par une GPO MachinePolicy (script refuse), soit signale comme IOC par l'EDR (process tue) -- **#217**. Un script LOCAL fraichement genere s'execute sans bypass sous la policy usuelle RemoteSigned. Le contenu du `.ps1` etant stocke en bytes ISO-8859-1, PowerShell lit l'octet `0xe9` natif et le transmet a xwin7 sans re-encodage casseur (identique avec `& '<ps1>'` ou `-File`). **Le `; exit $LASTEXITCODE` est obligatoire** : sans lui, PowerShell ecrase tout code de sortie xwin7 non nul en `1` et le diagnostic du crash `-805306369` est perdu.


### Recette automatisee -- `scripts/compile_project.py`

Pour eviter de regenerer ce pattern a la main a chaque compilation, **utiliser `scripts/compile_project.py`** qui :
1. Genere le `.ps1` en ISO-8859-1 + CRLF (cf. `write_iso()`)
2. Le pose dans le meme repertoire que le log (ou `--ps1-dir` si specifie)
3. L'execute via l'operateur d'appel `powershell -NoProfile -Command "& '<ps1>'"` (pas `-ExecutionPolicy Bypass -File`, bloque/signale sur poste verrouille -- #217)
4. Capture stdout / stderr / exit code
5. Parse la ligne de resume du log pour determiner `success`
6. Retourne un JSON structure

Equivalent fonctionnel de `generate_harness.py` mais pour des projets reels (pas des harnesses standalone). Cf. SKILL.md section "Etape 3 -- Compiler" pour le mode d'emploi.
