# Layering pre-action : routage claim -> couche

Document de reference pour l'affectation de chaque claim a une couche du livrable.

## 3 couches, 3 audiences

| Couche | Audience | Duree | Objectif de lecture |
|--------|----------|-------|---------------------|
| **strategique** | Chef projet, decideur | 2 minutes | Savoir **quoi** (type de demande, domaine, verdict, action critique) |
| **tactique** | Developpeur implementeur | 15 minutes | Savoir **comment** (chaine d'appels, plan d'action, exemples, commandes) |
| **technique** | Auditeur, specialiste | 30 minutes | Savoir **pourquoi** et **quoi verifier** (constantes, parametrage, surcharges) |

Chaque couche est **autonome** : un lecteur qui s'arrete apres la couche strategique
a deja une comprehension coherente. Il peut ensuite choisir d'approfondir en lisant
tactique puis technique.

## Routage par `claim.kind` et `content_type_id`

Le script `build_facts.py` (skill amont) affecte deja `claim.layer` selon la table :

| `content_type_id` | `slug` | `layer` | `kind` typiques |
|---|---|---|---|
| 1 | exemples | tactical | example |
| 2 | fonctions_langage | technical | function |
| 3 | etude_impact | tactical | call_chain, impact_caller |
| 4 | endroit_agir | tactical | action_site |
| 5 | pistes_recherche | tactical | hint |
| 6 | attention | technical | overwrite_warning |
| 7 | constantes_metier | technical | literal_table |
| 8 | parametrage_dossier | technical | dossier_param |
| 10 | verification_prealable | tactical | verification |

Aucun claim n'est affecte a la couche `strategic` : cette couche est synthetisee
depuis `facts.verdict`, `facts.request`, `facts.coverage` et `facts.selection`
par le renderer. Elle ne contient pas de claim atomique -- c'est une vue de tete.

## Ordre de rendu dans une couche

Dans la couche **tactique** :

1. Chaine d'appels (un seul claim `call_chain`, rend en Mermaid)
2. Plan d'action (claims `action_site`, propositions 1/2/...)
3. Exemples a etudier (claims `example`, sans path:line)
4. Commandes de verification (claims `verification`, prose + code bash)
5. Etude d'impact (claims `impact_caller`, liste)
6. Pistes complementaires (claims `hint`, liste ; inclus si signal faible)

Dans la couche **technique** :

1. Constantes et codes metier (claims `literal_table`, tableau markdown)
2. Parametrage dossier (claims `dossier_param`, prose + commandes)
3. Fonctions du langage utiles (claims `function`, liste courte)
4. Points d'attention (claims `overwrite_warning`, liste)

Dans la couche **strategique** :

1. Verdict (verdict.one_line)
2. Identite de la demande (request.type, request.domaine, confiance)
3. Action prioritaire (premier claim action_site, resume en 1 ligne)
4. Panorama de la selection (types inclus / omis avec raisons courtes)

## Regles d'omission

- Une couche complete sans claim est **omise** (pas de section vide).
- Un type omis par la selection voit ses claims omis du rendu.
- Si `facts.selection[i].included = false`, les claims avec `content_type_id=i`
  sont ignores silencieusement. Seul le panorama de la couche strategique
  mentionne brievement les types omis pour tracabilite.
