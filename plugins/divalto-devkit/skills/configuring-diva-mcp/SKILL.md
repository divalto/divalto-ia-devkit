---
name: configuring-diva-mcp
description: >
  Configure les credentials du serveur MCP diva-mcp pour le partenaire integrateur. Le
  plugin marketplace livre un `.mcp.json` template (URL declaree, pas de headers
  d'authentification). Ce skill demande interactivement les 3 elements de la cle API
  (site, env, ApiKey) au partenaire, construit le header `X-Api-Key` au format
  `<site>-<env>@<apikey>`, et patche le `.mcp.json` du plugin pour persister la config
  pour toutes les sessions Claude Code futures. A invoquer la premiere fois apres
  l'installation du plugin, ou en cas de cle expiree / 401 sur les outils
  `mcp__diva-mcp__*`, ou apres une mise a jour du plugin qui aurait restaure le
  template d'origine (perte des credentials). Triggers : "configure diva-mcp",
  "ma cle API diva", "diva-mcp 401 / unauthorized", "diva-mcp ne marche pas",
  "premier demarrage diva-mcp", "renouveler ma cle diva-mcp".
---

# configuring-diva-mcp

## Contenu

- [Quand utiliser ce skill](#quand-utiliser-ce-skill)
- [Workflow interactif](#workflow-interactif)
- [Scripts disponibles](#scripts-disponibles)
- [Apres ecriture : redemarrage obligatoire](#apres-ecriture-redemarrage-obligatoire)
- [References](#references)

---

## Quand utiliser ce skill

| Situation | Action attendue |
|-----------|-----------------|
| Premiere installation du plugin par un partenaire | Le `.mcp.json` est livre sans headers. Lancer ce skill pour les saisir. |
| `mcp__diva-mcp__*` retourne 401 / Unauthorized | La cle est probablement expiree ou rotated. Lancer ce skill pour saisir la nouvelle. |
| Mise a jour du plugin via marketplace | Le `.mcp.json` est restaure a son template. Relancer ce skill. |
| Le partenaire change de site / d'environnement | Lancer ce skill pour mettre a jour les valeurs. |

---

## Workflow interactif

Etape 1 -- Localiser le `.mcp.json` du plugin
```
py scripts/locate_mcp_json.py
```
Renvoie sur stdout le chemin absolu du `.mcp.json` chez le partenaire. Utilise dans
l'ordre :
1. `${CLAUDE_PLUGIN_ROOT}/.mcp.json` si la variable d'env est definie (cas du runtime
   plugin)
2. Recherche en remontant depuis le repertoire courant
3. Chemins par defaut Claude Code (`~/.claude/plugins/.../divalto-devkit/.mcp.json`)

> **CHECKPOINT 1** -- Verifier que le chemin renvoye est bien celui attendu (au sein
> du repertoire d'install du plugin). Si la detection echoue, demander au partenaire
> de fournir le chemin manuellement.

Etape 2 -- Demander les 3 valeurs au partenaire via conversation

Claude doit poser les 3 questions en langage naturel (pas via AskUserQuestion : les
valeurs sont libres) :

1. **Site** : "Quel est le code site de votre installation Divalto ? (exemple :
   `699170`, `607123`, `599654`)"
2. **Environnement** : "Quel environnement ciblez-vous ? (`PROD`, `TEST`, `DEV`)"
3. **API Key** : "Collez votre cle API diva-mcp (fournie par Divalto, format :
   chaine alphanumerique). Note : la cle sera ecrite en clair dans le `.mcp.json`
   chez vous. Si cela vous derange, prevenez l'architecte avant de la coller."

> **CHECKPOINT 2** -- Verifier que les 3 valeurs sont non vides et plausibles
> (site / env en majuscules sans espaces, apikey > 8 caracteres). Si une valeur
> semble incorrecte, redemander.

Etape 3 -- Ecrire les credentials dans le `.mcp.json`

```
py scripts/write_credentials.py \
    --mcp-path "<chemin retourne par locate_mcp_json.py>" \
    --site "<site>" \
    --env "<env>" \
    --apikey "<apikey>"
```

Le script :
- Cree une copie `.bak` du `.mcp.json` original (au cas ou)
- Lit le JSON existant
- Ajoute (ou remplace) le bloc `headers` dans la config de `diva-mcp` :
  ```json
  "headers": {
    "X-Api-Key": "<site>-<env>@<apikey>"
  }
  ```
- Ecrit atomiquement (write to `.tmp` puis rename)
- Sortie JSON sur stdout : `{"status": "ok", "mcp_path": "...", "backup": "..."}`

> **CHECKPOINT 3** -- Confirmer au partenaire que l'ecriture a eu lieu, mentionner le
> chemin du `.bak` au cas ou il voudrait rollback, et lui dire qu'il doit
> **redemarrer Claude Code** pour que le `.mcp.json` modifie soit pris en compte.

---

## Scripts disponibles

| Script | Role |
|--------|------|
| `locate_mcp_json.py` | Trouve le `.mcp.json` du plugin chez le partenaire. Sortie : chemin absolu sur stdout, ou exit 1 si non trouve. |
| `write_credentials.py` | Patche le `.mcp.json` avec le bloc `headers`. Atomic write + backup `.bak`. |

Tous les scripts : `argparse` + sortie JSON sur stdout + exit codes (`0` succes, `1`
erreur applicative, `2` erreur d'usage).

---

## Apres ecriture : redemarrage obligatoire

Le `.mcp.json` est lu **uniquement au demarrage de Claude Code**. Aucun rechargement
runtime. Apres ecriture par ce skill :

1. Le partenaire ferme Claude Code (tous les terminaux / sessions ouvertes)
2. Relance Claude Code
3. Au demarrage, `.mcp.json` est parse, le bloc `headers` est present, diva-mcp se
   connecte avec authentification
4. Test : appeler un outil simple `mcp__diva-mcp__get_schema` -- doit repondre sans
   401

Si le 401 persiste apres redemarrage :
- Le format `<site>-<env>@<apikey>` est-il accepte par le serveur ? Verifier avec
  Divalto (cf. `reference/credentials-format.md`)
- La cle est-elle active ? (peut etre revoque cote serveur)
- L'URL `https://mcp-diva-partner.red.divalto.com` est-elle joignable depuis le poste ?

---

## References

- [reference/credentials-format.md](reference/credentials-format.md) -- Format du
  header `X-Api-Key`, comment obtenir une cle, qui contacter chez Divalto en cas de
  probleme.
