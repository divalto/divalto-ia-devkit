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
    result = mcp__2e56c8ef-7b33-4e7d-9991-3a50dc1e7f1b__read_neo4j_cypher(query=q["cypher"])
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
| 0 candidats | **Declencher CP2 "0 candidat"** (voir SKILL.md) : verifier keywords (le parser expanse deja les abreviations du catalogue `abreviations-divalto.md`), proposer 2-3 reformulations, verifier `domaine_pressenti`, basculer mode direct si Neo4j up mais 0 match |
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

`{CHEMIN_ERP_STANDARD}` est le placeholder workspace (par defaut `C:/Developpements harmony/Standard/Version X.13` en local).

### Interpretation des statuts

| Statut | Signification |
|--------|--------------|
| `CONFIRME X.13` | Candidat X.12 existe en X.13, snippet extrait |
| `DISPARU X.13` | Candidat X.12 introuvable en X.13 (refactor ou supprime) |
| `NOUVEAU X.13` | Match textuel dans X.13 non couvert par les candidats Neo4j |

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
| Moins de 3 `CONFIRME X.13` | Proposer `--domain-scope all` pour elargir |
| `matches_truncated=true` | Bornes atteintes, informer le developpeur |
| Beaucoup de `DISPARU X.13` | Snapshot X.12 tres decale -- noter dans le rapport |

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

### Decisions au CP5

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

Ces fichiers peuvent etre conserves ou supprimes apres le CP5. Le livrable pertinent est le `.md` + `.json`.
