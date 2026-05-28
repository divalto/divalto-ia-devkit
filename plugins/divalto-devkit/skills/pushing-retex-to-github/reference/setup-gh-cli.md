# Setup GitHub CLI (gh) cote partenaire

## Installation

### Windows (recommande : winget)

```powershell
winget install --id GitHub.cli
```

Puis ouvrir un nouveau terminal pour que `gh` soit dans le `PATH`.

### Alternative : MSI

Telecharger depuis https://cli.github.com/ et installer.

### Verification

```powershell
gh --version
# gh version 2.x.x (...)
```

## Authentification

### Option 1 : navigateur (recommandee)

```powershell
gh auth login
# > Where do you use GitHub? -> GitHub.com
# > Preferred protocol -> HTTPS
# > Authenticate Git with your GitHub credentials -> Yes
# > How would you like to authenticate -> Login with a web browser
```

Le navigateur s'ouvre, copier le code one-time affiche en console, valider l'app sur
github.com. La session est persistee sur le poste.

### Option 2 : Personal Access Token

Si l'organisation impose un PAT :

1. Generer un token sur https://github.com/settings/tokens (scope `repo` minimum)
2. `gh auth login --with-token < token.txt`

### Verification

```powershell
gh auth status
# > Logged in to github.com as <username>
# > Active account: true
# > Token scopes: 'repo', 'workflow', ...
```

## Permissions sur le repo cible

Le compte authentifie doit avoir les permissions :

- **Lecture** : pour eviter les doublons (le script peut chercher si l'issue existe deja)
- **Ecriture** : pour creer/commenter des issues (`Issues: Read and Write` au minimum)

Si le repo cible est dans une organisation, demander a l'admin de l'organisation
d'ajouter le compte comme collaborateur ou de creer une equipe avec le droit `Triage`
(suffisant pour creer des issues).

## Depannage

| Symptome | Cause probable | Solution |
|----------|----------------|----------|
| `gh: command not found` | Pas installe ou pas dans le PATH | Reinstaller, ouvrir nouveau terminal |
| `HTTP 401: Bad credentials` | Token expire / revoke | `gh auth login` a nouveau |
| `HTTP 403: Resource not accessible by integration` | Pas les droits sur le repo | Demander l'acces a l'admin |
| `HTTP 404: Not Found` | Repo n'existe pas ou pas visible | Verifier le nom dans `.retex-github.json` |
| Issue creee mais pas de labels | Labels n'existent pas dans le repo | `gh label create <nom>` ou desactiver dans config |
