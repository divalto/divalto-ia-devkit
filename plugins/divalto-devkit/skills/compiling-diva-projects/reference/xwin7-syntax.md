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
