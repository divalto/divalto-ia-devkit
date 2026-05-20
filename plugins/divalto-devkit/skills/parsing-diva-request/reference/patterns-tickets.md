# patterns-tickets.md

Reference des patterns detectes par `parse_request.py` pour classifier une demande comme `ticket` (anomalie, issue myService / JIRA Divalto).

## Patterns declencheurs (heuristique OR)

| Pattern (regex) | Signification | Exemple |
|-----------------|---------------|---------|
| `\banomalie\b` | Mot explicite | "Anomalie detectee sur le zoom" |
| `\bbug\b` | Anglicisme | "Bug sur la saisie de famille" |
| `\berreur\b` | Signal d'erreur | "Erreur a la sauvegarde" |
| `\bplante\b` | Crash | "Le zoom plante au clic" |
| `\bcass[eé]\b` | Fonctionnalite cassee | "La fonction d'import est cassee" |
| `\bne fonctionne pas\b` | Dysfonctionnement | "La touche F5 ne fonctionne pas" |
| `\bticket\s+myService\b` | Mention outil | "Ticket myService #12345" |
| `\bJIRA\b` | Mention outil | "Issue JIRA RT-4567" |
| `^\s*at\s+\w+\.\w+` | Stack trace Java-like | "at com.divalto.ServletX" |

Un signal ticket l'emporte sur feature si les deux sont detectes mais que ticket_score > feature_score.

## Extraction du message d'erreur

Trois strategies en cascade :

### Pattern 1 : texte entre quotes (>= 10 caracteres)

```
Le zoom affiche "Fichier LIVRE non trouve" lors de la creation.
```

Regex : `"([^"]{10,})"` puis `'([^']{10,})'` en fallback.

Le seuil 10 caracteres evite de capturer les identifiants courts (noms de champs, constantes).

### Pattern 2 : ligne `erreur: XXX`

```
erreur : HFileVersion invalide sur RTFTAB
```

Regex : `\b(?:erreur|error)\s*:?\s*([^\n]{5,})`.

Le `.rstrip(".")` evite les points de fin de phrase polluants.

### Pattern 3 : non extrait

Si aucun pattern ne matche, `message_erreur: null` et `needs_clarification: true` (ticket sans message extrait).

## Elements non extraits

| Element | Raison |
|---------|--------|
| Stack trace multi-ligne complete | Hors scope du parser MVP. Le LLM peut lire la stack au CP1 |
| Numero de ticket myService | Non reporte en JSON canonique. Peut etre ajoute a `keywords_techniques` manuellement |
| Version ERP (X.13, X.12) | Non extrait -- la version courante est toujours X.13 par defaut |
| URL d'un ticket | Non extrait |

## Cas limites

| Situation | Comportement |
|-----------|--------------|
| Ticket d'anomalie reformule en user story ("En tant que... quand ca plante...") | Scoring : `feature_score=2, ticket_score=1` -> `feature`. Le LLM peut corriger au CP1 |
| Copie-colle d'un mail avec multiple erreurs | Premiere erreur entre quotes capturee. Les autres a reconstituer via le LLM |
| Stack trace sans message explicite | `message_erreur: null`, `needs_clarification: true`. Le LLM extrait lui-meme au CP1 |
| Ticket sans aucun indice (juste "ca marche pas") | `type: ticket` (score >= 1), message null, `needs_clarification: true` |

## Liens avec la phase 3 (verification X.13)

Le message extrait est utilise comme **keyword techniques** prioritaire dans la phase 3 : `searching-erp-sources` le cherchera textuellement dans les `.dhsp` pour localiser ou le message est emis. Voir `docs/RECHERCHE-ERP.md` section "Patterns d'impact X.13".

Les messages d'erreur DIVA courants (framework, moulinettes) sont a terme documentes dans `coding-diva-advanced` ou un futur skill dedie. Ce parser ne les reconnait pas specifiquement -- tout message entre quotes est capture.
