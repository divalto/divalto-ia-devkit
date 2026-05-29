# Marketplace Divalto pour Claude Code

Ce dépôt contient la marketplace de plugins, skills, agents et hooks Claude Code utilisés par les équipes d'intégration.

## Prérequis

- Claude Code installé — https://claude.com/claude-code
- Compte GitHub, Le site est public, inutile d'avoir un accès à l'organisation **Divalto**
- GitHub CLI (`gh`) installé et authentifié
- Windows / macOS / Linux

## Installation de GitHub CLI

Cet outil est indispensable pour faire remonter les RETEX via des Issues dans GitHub

### 1. Installer 

**Windows (winget)** — dans PowerShell :

```powershell
winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
```

Si winget échoue, installation directe via MSI (PowerShell **Administrateur**) :

```powershell
$url = "https://github.com/cli/cli/releases/download/v2.92.0/gh_2.92.0_windows_amd64.msi"
$msi = "$env:TEMP\gh_installer.msi"
Invoke-WebRequest -Uri $url -OutFile $msi
Start-Process msiexec.exe -ArgumentList "/i `"$msi`" /quiet /norestart" -Wait
Remove-Item $msi
```

### 2. Recharger le PATH (Windows uniquement)

Sans avoir à rouvrir le terminal :

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

Vérifier l'installation :

```bash
gh --version
```

### 3. S'authentifier sur GitHub

```bash
gh auth login
```

Répondre aux questions :

- **What account do you want to log into?** → `GitHub.com`
- **What is your preferred protocol for Git operations?** → `HTTPS`
- **Authenticate Git with your GitHub credentials?** → `Yes`
- **How would you like to authenticate?** → `Login with a web browser`

Copier le code à usage unique affiché et le coller dans la page web qui s'ouvre.

### 4. Vérifier l'accès au dépôt

```bash
gh repo view Divalto/divalto-ia-devkit
```

- Si le README s'affiche → vous avez accès, passez à l'étape suivante.
- Si `not found` → demandez à un administrateur Divalto de vous inviter au dépôt.

### 5. Ajouter la marketplace dans Claude Code

#### Méthode A — Interface graphique

1. Ouvrir Claude Code
2. `Plugins` → `Ajouter une marketplace`
3. Saisir dans le champ URL :

   ```
   https://github.com/divalto/divalto-ia-devkit
   ```

4. Cliquer sur `Synchro`

#### Méthode B — Ligne de commande

Dans Claude Code :

```
/plugin marketplace add https://github.com/divalto/divalto-ia-devkit
```

### 6. Installer les plugins

Une fois la marketplace ajoutée :

```
/plugin
```

Sélectionner les plugins à installer dans la liste.

## Mises à jour automatiques (optionnel)


## Plugins disponibles

| Plugin | Description |
|---|---|
| `divalto-devkit` | technical foundation for Divalto Harmony. Diva coding for our partners|

## Dépannage

### Claude Code ne trouve pas `gh`

Sur Windows : fermer et rouvrir le terminal après l'installation, ou recharger le PATH (voir étape 2).

## Support

Pour toute question, contacter Le support Divalto.

## Mettre à jour

`/reload-plugins` pour appliquer.

## Désinstaller

```
/plugin uninstall <plugin-name>
```

