# patterns-features.md

Reference des patterns detectes par `parse_request.py` pour classifier une demande comme `feature`.

## Patterns declencheurs (heuristique OR)

| Pattern (regex) | Signification | Exemple |
|-----------------|---------------|---------|
| `\bEn tant que\b` | User story format gerondif | "En tant que gestionnaire, je veux..." |
| `\bJe veux\b` | Intention utilisateur | "Je veux saisir la famille de reglement" |
| `\bAfin de\b` | Benefice | "Afin de suivre les reglements" |
| `\bEtant donn[eé]\b` | BDD given | "Etant donne une fiche client..." |
| `\bQuand\b.+\bAlors\b` | BDD when-then | "Quand je valide, alors le zoom ferme" |
| `\bCrit[eè]res? d\'acceptation\b` | Section CA dediee | "## Criteres d'acceptation" |
| `\bUser story\b` | Mention explicite | "User story : ..." |

Un signal feature l'emporte sur ticket si les deux sont detectes mais que feature_score > ticket_score.

## Extraction des criteres d'acceptation (CA)

Trois strategies en cascade :

### Pattern 1 : section dediee + bullets

```
Criteres d'acceptation :
- Le zoom est accessible depuis le menu Retail
- La saisie de la famille est obligatoire
- La suppression est bloquee si des reglements existent
```

Regex :
```
(?:Crit[eè]res? d\'acceptation|Acceptance criteria|\bCA\s*:)\s*:?\s*\n
((?:\s*(?:[-*•]|\d+\.)\s+[^\n]+\n?)+)
```

Types de bullets reconnus : `-`, `*`, `•`, `1.`, `2.`, ...

### Pattern 2 : CAn: numerote inline

```
Le zoom doit etre accessible. CA1 : ouverture menu, CA2 : champ obligatoire.
```

Regex : `\bCA\s*\d+\s*:\s*([^\n]+)`

### Pattern 3 : BDD scenarios

Non extrait automatiquement en CA -- les scenarios BDD sont tournes comme un test, pas comme un CA atomique. Le LLM orchestrateur peut les reformuler en CA au CP1 si besoin.

## Extraction des acteurs

Pattern unique : `En tant que\s+([^,.\n]+)`.

Exemple : `En tant que gestionnaire reglement, je veux...` -> acteur `gestionnaire reglement`.

Si aucun `En tant que` n'est trouve mais que des CA sont detectes, la demande est toujours classee `feature` (ex : brouillon sans user story formelle).

## Cas limites

| Situation | Comportement |
|-----------|--------------|
| Texte 100% BDD (Etant donne + Quand + Alors) sans "En tant que" | `type: feature`, `acteurs: []`, `needs_clarification: true` si pas de CA non plus |
| User story "Je veux X afin de Y" sans CA | `type: feature`, `ca_detectes: []`, `needs_clarification: true` |
| Texte avec "user story" en titre mais corps anomalie | `type: feature` l'emporte (score supra-anomalie si > 0). Le LLM doit detecter la contradiction au CP1 |
| Demande mixte (feature + rappel anomalie precedente) | Le score plus eleve l'emporte. Le LLM peut splitter au CP1 si necessaire |

## Ne pas etendre sans tests

Ce fichier documente le comportement actuel. Toute extension (ex : support de `As a developer` en anglais) doit etre accompagnee :
- D'un ajout dans `FEATURE_PATTERNS` de `parse_request.py`
- D'un scenario dans `evals.json`
- D'une mise a jour de ce fichier

Voir `docs/RECHERCHE-ERP.md` section "Regles pour le LLM" pour le cadrage general.
