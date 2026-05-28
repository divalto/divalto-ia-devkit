# Format des credentials diva-mcp

## Le header attendu par le serveur

```
X-Api-Key: <site>-<env>@<apikey>
```

Le serveur `https://mcp-diva.divaltocloud.com` parse ce header au format strict
suivant :

| Element | Description | Exemple |
|---------|-------------|---------|
| `<site>` | Code site du partenaire dans le referentiel Divalto. Majuscules, lettres/chiffres/tirets uniquement. | `GENEVE`, `STRASBOURG-CENTRE` |
| `<env>` | Environnement cible. Generalement `PROD`, `TEST`, ou `DEV`. | `PROD` |
| `<apikey>` | Clef alphanumerique fournie par Divalto au moment de l'onboarding. | `aB3xK9...mZ7q` (32-64 chars typiquement) |

Le separateur entre site et env est un tiret `-`. Le separateur entre `env` et la
cle est un `@`. Aucun espace.

## Comment obtenir une cle API

La cle est emise par l'equipe IA Divalto a la souscription au plugin partenaire. Pour
en obtenir une (ou une nouvelle si compromise) :

1. Ouvrir le site my.divalto.com avec votre compte
2. Aller dans Clé D'API:
   - Le code projet du site Divalto sous la forme <Site-Env>
   - Générer une clé d'API en utilisant le Type "MCP divalto-ia-devkit"
   - Recupérer par copier coller l'ApiKey

> Note : la cle a une duree de vie typique de **12 mois**. Un message d'avertissement
> est emis par l'API a partir de J-30 avant expiration. En cas de cle expiree, le
> serveur retourne 401 sur tous les outils `mcp__diva-mcp__*`.

## Securite

Le fichier `.mcp.json` chez le partenaire **contient la cle en clair**. C'est un choix
explicite (vs. variables d'env) pour simplifier la configuration. Implications :

| Risque | Mitigation |
|--------|------------|
| Backup du `~/.claude/` envoye en clair | Eviter de partager les backups, ou chiffrer. |
| Screenshot / screen share | Verifier qu'aucun terminal ne lit le `.mcp.json` quand on partage l'ecran. |
| Commit accidentel | Le `.mcp.json` n'est jamais commitable (gitignore generique sur `.claude/`). Verifier. |
| Cle volee / divulguee | Demander une revocation immediate par ticket myService. Generer une nouvelle cle. Relancer le skill `configuring-diva-mcp` pour reecrire. |

## Que faire en cas de 401 / Unauthorized

1. **Verifier l'URL** : `curl -sI https://mcp-diva-partner.red.divalto.com` doit
   repondre (sans header, attend 401 -- c'est normal).
2. **Verifier le format** : ouvrir `.mcp.json`, regarder la ligne `X-Api-Key` -- doit
   matcher `<site>-<env>@<apikey>` strictement.
3. **Verifier l'expiration** : Divalto peut confirmer si la cle est encore active.
4. **Relancer le skill** `configuring-diva-mcp` avec les bonnes valeurs.

## Contact

| Probleme | Canal |
|----------|-------|
| Cle introuvable / onboarding | myService categorie `DEMANDE-IA-PARTENAIRE` |
| Cle volee | myService categorie `INCIDENT-SECURITE` (urgence) |
| Format ou validation du header | Architecture IA Divalto, contact via myService |
| Bug du skill `configuring-diva-mcp` | Voir RETEX-skills.md du workspace, push automatique GitHub |
