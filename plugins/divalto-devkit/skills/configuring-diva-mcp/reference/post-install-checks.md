# Verification post-installation et operation de diva-mcp

A lire **apres** avoir ecrit les credentials et redemarre Claude Code, si les outils
`mcp__...diva-mcp__*` ne repondent pas comme attendu.

---

## 1. Diagnostic : diva-mcp est-il charge ?

Apres un redemarrage **complet**, verifier le journal de Claude Code (`main.log`).

- Localisation typique (Windows) : repertoire de logs de l'application Claude Code
  (selon la version installee).
- Chercher les marqueurs, sur la ligne mentionnant `divalto-devkit` / `diva-mcp` :
  - `Shadowing with no-ops to prevent SDK double-load`
  - `remote: 0`

**Si l'un de ces marqueurs est present** : Claude Code a **neutralise** le serveur MCP
HTTP distant declare par le plugin. Les outils `mcp__...diva-mcp__*` ne seront pas
disponibles, **meme avec des credentials corrects**. Passer aux sections suivantes.

**Si aucun marqueur** : le probleme est ailleurs -- cle invalide (-> 401), URL
injoignable, ou `.mcp.json` pas patche (relancer le workflow du skill).

---

## 2. Piege BOM sur `settings.json` (PowerShell)

Une edition de `~/.claude/settings.json` via **PowerShell** ajoute souvent un **BOM
UTF-8** (octets `EF BB BF`) en tete de fichier. Claude Code echoue alors au parsing
(`Unexpected token BOM`) et **desactive silencieusement** `enableAllProjectMcpServers`
/ `enabledMcpjsonServers`.

- Detecter : ouvrir le fichier en binaire ; s'il commence par `EF BB BF`, le BOM est la.
- Corriger : reecrire le fichier **sans BOM** (UTF-8 simple). En PowerShell, utiliser
  `[System.IO.File]::WriteAllText($chemin, $contenu)` (n'ecrit pas de BOM), **pas**
  `Out-File` / `Set-Content` par defaut.

---

## 3. Redemarrage complet (obligatoire)

Fermer la fenetre ne suffit pas : Claude Code peut laisser des processus actifs. Fermer
**tous** les processus Claude (gestionnaire des taches Windows), puis relancer. Le
`.mcp.json` et `settings.json` ne sont relus qu'au demarrage.

---

## 4. Contournement « shadowing » -- DEPENDANT DE LA VERSION DE CLAUDE CODE

> Le « shadowing with no-ops » est un comportement **du systeme de plugins de Claude
> Code** (protection anti double-load des MCP distants), **pas** un defaut du skill.
> La procedure ci-dessous est un **contournement constate par des partenaires**, qui
> **peut cesser de fonctionner** a une mise a jour de Claude Code. **Confirmer la
> procedure officielle d'activation aupres de l'equipe IA Divalto avant de s'y fier.**

Contournement constate (a adapter a la version installee) :

1. Corriger un eventuel BOM dans `~/.claude/settings.json` (section 2).
2. Creer `~/.claude/.mcp.json` avec le **wrapper** `mcpServers` et la config diva-mcp
   + credentials :
   ```json
   {
     "mcpServers": {
       "diva-mcp": {
         "type": "http",
         "url": "https://mcp-diva-partner.red.divalto.com",
         "headers": { "X-Api-Key": "<site>-<env>@<apikey>" }
       }
     }
   }
   ```
3. Ajouter dans `~/.claude/settings.json` (sans BOM) :
   ```json
   "enabledMcpjsonServers": ["diva-mcp"]
   ```
4. Redemarrage **complet** (section 3).

Succes attendu : les outils `mcp__plugin_divalto-devkit_diva-mcp__*` apparaissent et
repondent (ex. `get_schema`, ou la version ERP + le nombre de programmes via
`get_program_overview`).

---

## 5. Garde-fou de version ERP (hook `check_mcp_version.py`)

Tout appel a un outil `mcp__...diva-mcp__*` doit porter une `version` (ou `versions`)
ERP **valide** (X.7 -> X.13) et **validee par l'utilisateur**. Ce n'est pas une
contrainte du serveur : c'est un garde-fou contre une reponse rendue pour la mauvaise
version. En **migration** (ex. X.9 -> X.13), on peut vouloir interroger l'existant *ou*
la cible -- l'intention **n'est pas deductible automatiquement**, d'ou la validation.

Comportement attendu cote Claude :

- Si la version n'a pas encore ete fixee, **proposer les versions plausibles via
  `AskUserQuestion`** (version installee + cible de migration le cas echeant) et laisser
  l'utilisateur **choisir**. Ce choix est l'action de validation.
- Une version **tapee** par l'utilisateur (« ... en X.13 ») vaut aussi validation.
- La confirmation vaut pour **toute la session** : une version validee n'est plus
  redemandee ; seule une version **encore jamais mise en jeu** declenche une nouvelle
  confirmation (1 fois par version, par session).

Le hook **bloque** (et renvoie un message d'aide) tant que la version n'est pas presente,
valide et confirmee. Il n'affiche pas lui-meme de question : c'est Claude qui pose
l'`AskUserQuestion` suite au message de blocage.
