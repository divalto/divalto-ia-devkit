# workflow.md -- Enchainement detaille des 4 phases

## Contenu

- Phase 1 -- PARSE
- Phase 2 -- QUERY NEO4J
- Phase 3 -- VERIFY X.13
- Phase 4 -- BUILD REPORT + ENRICHISSEMENT LLM
- Recapitulatif des fichiers intermediaires

---


Complement au `SKILL.md` avec les commandes copier-coller et les patterns specifiques.

## Phase 1 -- PARSE

### Commande

```bash
# Depuis stdin (developpeur colle dans la conversation, Claude redirige via heredoc)
py .claude/skills/parsing-diva-request/scripts/parse_request.py > output/request.json
```

### Lecture du resultat

```python
import json
request = json.load(open("output/request.json", encoding="utf-8"))
# Champs a verifier : type, titre, acteurs, domaine_pressenti, ca_detectes,
#                     message_erreur, needs_clarification
```

### Decisions au CP1

| Situation | Action |
|-----------|--------|
| `needs_clarification=true` | Demander au developpeur de completer avant phase 2 |
| `type=unknown` | Demander clarification sur la nature de la demande |
| `type=feature` mais `ca_detectes=[]` | Demander les criteres d'acceptation |
| `type=ticket` mais `message_erreur=null` | Demander le message d'erreur precis |
| Domaine pressenti incorrect | Editer `request.json` pour corriger |
| Version ERP cible != defaut | Etablir la version contre laquelle le projet compile (`.dhpt` : `versioncible` / segment `repobjet`, cf. R-17 understanding-integrator-workspace) et la passer en `--erp-root` -- le defaut X.13 n'est pas forcement la cible (#191) |

### Sources de la demande -- fallbacks d'environnement

La demande vient souvent d'un work item **ADO** ou d'un **PDF de spec**. Deux ecueils recurrents a gerer AVANT de conclure :

- **PAT ADO expire (#189)** : un GET work item (`workItems/{id}?$expand=all`) renvoyant `Access Denied: ... Personal Access Token ... expired` (ou 401) n'est PAS un probleme d'analyse. Afficher d'emblee la procedure -- **renouveler le PAT dans Azure DevOps, mettre a jour la variable d'env `ADO_PAT` (User scope Windows), relancer la session** -- plutot que de laisser remonter l'erreur HTML brute. Les *discussions* de l'US portent souvent des precisions metier absentes du PDF : ne pas les zapper.
- **PDF de spec illisible (#190)** : si `Read` sur le PDF echoue (`pdftoppm not found` / `No module named pypdf`), fallback : `py -m pip install pypdf`, extraire vers `.claude/<nom>.txt` en **UTF-8**, puis relire le `.txt`. **Ne pas** faire de `print` direct du texte extrait (console Windows cp1252 : plante sur `U+F0B7` et autres non-ASCII).

### Piege inter-versions (#191)

La structure des points d'extension (hooks) DIFFERE entre majeures du standard : un symbole candidat (hook vide, fonction) peut exister en X.13 mais PAS dans la version cible du projet -- ou etre construit « en dur » ailleurs. Toujours re-verifier l'existence d'un symbole dans **la version cible** (`--erp-root` fixe au CP1), jamais dans « la derniere » par defaut -- sinon on propose au client un point de surcharge qui n'existe pas chez lui.

---

## Phase 2 -- QUERY NEO4J

### Etape 2a -- Generer les requetes Cypher

```bash
py .claude/skills/querying-diva-graph/scripts/query_neo4j.py \
    --mode generate --request output/request.json \
    > output/queries.json
```

`queries.json` contient une liste d'objets `{template, parameter, cypher}`.

### Etape 2b -- Executer via le MCP

Pour chaque requete dans `queries.json` :

```python
# Pseudo-code Claude :
for q in queries["queries"]:
    result = mcp__plugin_divalto-devkit_diva-mcp__query_cypher(query=q["cypher"])
    raw_results[f"{q['template']}:{q['parameter']}"] = result
```

**Gestion d'erreur** :
- Timeout d'une requete : continuer, marquer la cle avec `[]`
- Erreur reseau globale : basculer en mode direct (voir SKILL.md)

### Etape 2c -- Ecrire les resultats bruts

```python
json.dump(raw_results, open("output/raw_results.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
```

### Etape 2d -- Consolider

```bash
py .claude/skills/querying-diva-graph/scripts/query_neo4j.py \
    --mode consolidate --request output/request.json \
    --results output/raw_results.json \
    > output/candidates_x12.json
```

### Decisions au CP3

| Situation | Action |
|-----------|--------|
| `> 50` candidats dans `programs` | Declencher CP2 supplementaire pour restreindre |
| 0 candidats | **Declencher CP2 "0 candidat"** (voir SKILL.md) : verifier keywords (le parser expanse deja les abreviations du catalogue `parsing-diva-request/reference/abreviations-divalto.md`), proposer 2-3 reformulations, verifier `domaine_pressenti`, basculer mode direct si Neo4j up mais 0 match |
| Developpeur ecarte certains candidats | Editer `candidates_x12.json` manuellement avant phase 3 |

---

## Phase 3 -- VERIFY X.13

### Commande

```bash
py .claude/skills/searching-erp-sources/scripts/verify_x13.py \
    --candidates output/candidates_x12.json \
    --request output/request.json \
    --erp-root "{CHEMIN_ERP_STANDARD}" \
    --domain-scope auto \
    --max-matches 50 --max-files 20 --timeout 60 \
    > output/evidence_x13.json
```

`{CHEMIN_ERP_STANDARD}` est le placeholder de la racine des sources standard livrees. Sa
valeur depend du poste : la demander au collaborateur, ne jamais la deviner.

### Interpretation des statuts

| Statut | Signification |
|--------|--------------|
| `CONFIRME` | Le candidat du graphe existe dans les sources verifiees, snippet extrait |
| `DISPARU` | Le candidat du graphe est introuvable dans les sources verifiees (refactor ou supprime) |
| `NOUVEAU` | Match textuel dans les sources, non couvert par les candidats du graphe |

> **Les statuts ne portent pas de numero de version.** Le script lit la racine qu'on lui
> donne et n'a aucun moyen de savoir quelle version elle contient -- or **la cible n'est
> pas forcement X.13** (cf. CP1 : un projet peut compiler contre X.12). La version
> **declaree** par `--version` est rapportee dans `scope.version_verifiee` ; si l'option
> est omise, le champ vaut `null` et **rien n'est affirme**.
>
> Ne pas remettre la version dans le statut : le consommateur aval teste `X.12` **avant**
> `CONFIRME`, donc un statut `CONFIRME X.12` serait retrograde en simple piste advisory
> et la confirmation sur disque serait perdue.

### Approfondissement

Si le developpeur veut approfondir un fichier :

```bash
py .claude/skills/searching-erp-sources/scripts/extract_context.py \
    --file "<chemin>" --line 42 --window 50
```

Retourne : snippet 50 lignes + fonction englobante.

### Decisions au CP4

| Situation | Action |
|-----------|--------|
| Moins de 3 `CONFIRME` | Proposer `--domain-scope all` pour elargir |
| `matches_truncated=true` | Bornes atteintes, informer le developpeur |
| Beaucoup de `DISPARU` | Snapshot du graphe tres decale par rapport aux sources -- noter dans le rapport |
| **`scope.couverture_keywords_complete=false`** | Des mots-cles n'ont **pas** ete cherches (`keywords_ecartes` au-dela du budget de 5, `keywords_non_atteints` faute de temps). La recherche N'EST PAS exhaustive : le dire au developpeur |
| **`scope.cadrage.repli_sur_erp_root=true`** | Le cadrage par domaine a **echoue** (sous-repertoires absents -- typique d'un specifique a arborescence plate) et la recherche a porte sur **tout** `erp_root`. Avec un budget bas, elle peut n'avoir rien trouve tout en paraissant cadree : relancer avec un `--max-files` adapte |
| **`scope.version_verifiee=null`** | Aucune version declaree : ne pas ecrire "X.13" dans le rapport, on ne sait pas |

---

## Phase 4 -- BUILD REPORT + ENRICHISSEMENT LLM

### Etape 4a -- Rendu markdown de base

```bash
py .claude/skills/building-preaction-report/scripts/build_report.py \
    --request output/request.json \
    --candidates output/candidates_x12.json \
    --evidence output/evidence_x13.json \
    --output-dir output
```

### Etape 4b -- Enrichissement LLM (obligatoire)

Le template produit un squelette. Le LLM complete via `Edit` sur le fichier markdown :

1. **Section 3** : categoriser les fonctions par famille + ajouter 3-5 canoniques
2. **Section 4.2** : rediger la propagation des changements
3. **Section 4.3** : chercher `OverWrittenBy` dans les snippets section 2
4. **Section 5** : 1-3 propositions d'action concretes avec UC generation suggere
5. **Section 6** : 3-5 pistes complementaires contextuelles
6. **Section 7** : conventions domaine + effets de bord

### Regles d'enrichissement

- **Pas d'hallucination `fichier:ligne`** : toute reference doit provenir des JSON intermediaires ou de scripts
- **Chaque proposition section 5** : lier a un exemple concret de la section 2 via `section 2.N`
- **Max 3 propositions** : si plus sont pertinentes, basculer les extras en section 6 (pistes)
- **Langue** : francais systematique, pas d'anglicismes sauf termes techniques DIVA

### Decisions au CP5b

| Situation | Action |
|-----------|--------|
| Developpeur demande un ajout | Editer le markdown et re-presenter |
| Confiance = faible | Verifier que l'encadre ATTENTION est present en en-tete |
| Couverture Neo4j = absente | Verifier la mention dans l'en-tete et section 7 |

---

## Recapitulatif des fichiers intermediaires

```
output/
  request.json                  # Phase 1
  queries.json                  # Phase 2a
  raw_results.json              # Phase 2b (Neo4j brut)
  candidates_x12.json           # Phase 2d
  evidence_x13.json             # Phase 3
  preaction-<slug>-<YYYYMMDD>.md    # Phase 4 (livrable humain)
  preaction-<slug>-<YYYYMMDD>.json  # Phase 4 (metriques)
```

Ces fichiers peuvent etre conserves ou supprimes apres le CP5b. Le livrable pertinent est le `.md` + `.json`.
