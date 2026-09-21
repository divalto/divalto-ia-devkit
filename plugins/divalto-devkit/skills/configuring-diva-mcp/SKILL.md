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
  `mcp__plugin_divalto-devkit_diva-mcp__*`, ou apres une mise a jour du plugin qui aurait restaure le
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
- [Verification post-installation](#verification-post-installation)
- [References](#references)

---

## Quand utiliser ce skill

| Situation | Action attendue |
|-----------|-----------------|
| Premiere installation du plugin par un partenaire | Le `.mcp.json` est livre sans headers. Lancer ce skill pour les saisir. |
| `mcp__plugin_divalto-devkit_diva-mcp__*` retourne 401 / Unauthorized | La cle est probablement expiree ou rotated. Lancer ce skill pour saisir la nouvelle. |
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
2. **Install marketplace** : `~/.claude/plugins/cache/<owner>/divalto-devkit/<version>/.mcp.json`
   (emplacement reellement charge par Claude Code) et
   `~/.claude/plugins/marketplaces/.../divalto-devkit/.mcp.json` -- version la plus recente d'abord
3. Recherche en remontant depuis le repertoire courant
4. Chemins par defaut Claude Code (`~/.claude/plugins/.../divalto-devkit/.mcp.json`)

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

> **PIEGE CLE `$$` (frequent, plusieurs partenaires)** : sous bash, une cle contenant
> `$`, `$$` ou `!` passee en argument (`--apikey "..."`) est **interpretee par le shell
> AVANT Python** (`$$` -> PID du shell) et la cle est ecrite **tronquee/corrompue**.
> Toujours passer la cle **hors argv** : par stdin (recommande) ou par fichier.

Methode recommandee -- stdin (aucune interpretation shell) :
```
printf '%s' '<apikey>' | py scripts/write_credentials.py \
    --mcp-path "<chemin>" --site "<site>" --env "<env>" --apikey-stdin
```

Ou par fichier temporaire (puis supprimer le fichier) :
```
py scripts/write_credentials.py --mcp-path "<chemin>" \
    --site "<site>" --env "<env>" --apikey-file "<fichier>"
```

(`--apikey "<apikey>"` reste accepte mais **deconseille** sous bash ; si vraiment
utilise, entourer la cle de **guillemets simples**.)

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
- Sortie JSON sur stdout : `{"status": "ok", "mcp_path": "...", "backup": "...", "header": "X-Api-Key: <site>-<env>@<cle masquee : 10 premiers...4 derniers>"}`

> **CHECKPOINT 3** -- Confirmer au partenaire que l'ecriture a eu lieu :
> - **Verifier la terminaison de la cle** : comparer les **4 derniers caracteres**
>   affiches dans le champ `header` de la sortie a la fin de la cle fournie par le
>   partenaire. S'ils **different**, la cle a probablement ete corrompue au transport
>   (expansion shell de `$` / `$$` / `!` via `--apikey`) -> relancer via `--apikey-stdin`.
>   C'est la **seule** verification fiable : aucune detection automatique n'est possible
>   une fois la cle recue par le script (un `$` peut aussi etre du **contenu legitime**
>   de la cle -- on ne peut donc ni la refuser ni deviner qu'elle a ete alteree).
> - Mentionner le chemin du `.bak` (rollback possible).
> - Rappeler qu'il faut **redemarrer Claude Code** pour que le `.mcp.json` soit pris en compte.

---

## Scripts disponibles

| Script | Role |
|--------|------|
| `locate_mcp_json.py` | Trouve le `.mcp.json` du plugin, **install marketplace comprise** (`cache/.../<version>/` et `marketplaces/...`). Sortie : chemin absolu sur stdout, exit 1 sinon. `--dry-run-show-candidates` liste les chemins testes. |
| `write_credentials.py` | Patche le `.mcp.json` avec le bloc `headers`. Cle via `--apikey-stdin` / `--apikey-file` (recommande : evite l'expansion shell de `$$`) ou `--apikey`. Atomic write + backup `.bak`. |

Tous les scripts : `argparse` + sortie JSON sur stdout + exit codes (`0` succes, `1`
erreur applicative, `2` erreur d'usage).

---

## Apres ecriture : redemarrage obligatoire

Le `.mcp.json` est lu **uniquement au demarrage de Claude Code**. Aucun rechargement
runtime. Apres ecriture par ce skill :

1. Le partenaire ferme **tous** les processus Claude (via le gestionnaire des taches si
   besoin, pas seulement la fenetre -- cf. piege « shadowing » ci-dessous)
2. Relance Claude Code
3. Au demarrage, `.mcp.json` est parse, le bloc `headers` est present, diva-mcp se
   connecte avec authentification
4. Test : appeler un outil simple `mcp__plugin_divalto-devkit_diva-mcp__get_schema` -- doit repondre sans
   401

Si le 401 persiste apres redemarrage :
- Le format `<site>-<env>@<apikey>` est-il accepte par le serveur ? Verifier avec
  Divalto (cf. `reference/credentials-format.md`)
- La cle est-elle active ? (peut etre revoque cote serveur)
- L'URL `https://mcp-diva.divaltocloud.com` est-elle joignable depuis le poste ?

---

## Verification post-installation

Si, apres redemarrage, les outils `mcp__...diva-mcp__*` **n'apparaissent pas** (ou
restent indisponibles) alors que les credentials sont corrects, le serveur a peut-etre
ete **neutralise au chargement** (« shadowing with no-ops ») ou `settings.json` est
corrompu (BOM UTF-8).

> **CHECKPOINT 4** -- Diagnostic rapide : chercher `shadowing` ou `remote: 0` dans le
> `main.log` de Claude Code. Si present, diva-mcp n'est pas charge -> appliquer
> [reference/post-install-checks.md](reference/post-install-checks.md) (diagnostic
> main.log, piege BOM `settings.json`, redemarrage complet, contournement connu).
> **Le shadowing depend de la version de Claude Code** : le contournement est documente
> comme tel ; la procedure officielle est a confirmer avec l'equipe IA Divalto.

---

## References

- [reference/credentials-format.md](reference/credentials-format.md) -- Format du
  header `X-Api-Key`, comment obtenir une cle, qui contacter chez Divalto en cas de
  probleme.
- [reference/post-install-checks.md](reference/post-install-checks.md) -- Diagnostic
  shadowing / BOM, redemarrage complet, contournement version-dependant, et garde-fou
  de version ERP (AskUserQuestion).
