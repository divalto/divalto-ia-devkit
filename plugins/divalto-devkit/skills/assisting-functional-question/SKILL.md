---
name: assisting-functional-question
description: Assiste un collaborateur qui pose une question fonctionnelle conversationnelle sur le standard ERP Divalto (formulations du type "ne comprends pas pourquoi X ne marche pas", "il manque une info pour que Y fonctionne", "quand l'option Z est activee, W n'apparait plus"). Produit une reponse **chat-ready** courte (< 40 lignes) identifiant 3 a 5 causes probables classees par probabilite, chacune avec une reference fichier:ligne dans X.13 et une action de verification concrete. Cycle court (< 5 min). Ne genere aucun fichier disque. A utiliser quand un collegue colle un message de chat, une capture d'ecran Teams/Slack, ou reformule a l'oral une question sur un parametrage ou un comportement du standard -- pas quand le collaborateur s'apprete a coder (UC-100).
---

# Assisting Functional Question

Cas d'usage UC-110. Reponse a une question conversationnelle sur le fonctionnement
du standard ERP Divalto. Contrairement a `analyzing-diva-request` (UC-100) qui prepare
un developpeur a **coder**, ce skill aide un collaborateur a **comprendre** un
comportement standard ou debloquer un parametrage.

---

## Quand utiliser

Signaux declencheurs (au moins un doit matcher) :

| Forme d'entree | Exemple |
|----------------|---------|
| Chat paste (Teams / Slack / mail) | "je suis bloque sur X, j'ai active Y et maintenant Z ne fonctionne plus" |
| Capture d'ecran de chat | Image d'une conversation Teams avec une question |
| Question orale transcrite | "quelqu'un sait pourquoi le zoom client ne montre rien quand on active les etablissements ?" |
| Question directe de Stephane | "Nicolas m'a demande X, tu peux l'aider ?" |

Signaux anti-declencheurs (**ne PAS utiliser** ce skill) :

- User story formelle avec "En tant que / je veux / afin de" -> utiliser `analyzing-diva-request` (UC-100)
- Ticket myService avec numero -> UC-100
- Demande de generation de code ("cree une entite X") -> `creating-diva-entity` (UC-001)
- Demande de documentation -> `documenting-erp` (UC-200)

---

## Principes directeurs

1. **Cycle court** : objectif < 5 min, 6-10 invocations d'outils (grep + read).
2. **Sortie chat-ready** : < 40 lignes, aucun fichier disque. Voir `reference/chat-ready-format.md`.
3. **Verifiabilite** : chaque cause citee pointe au moins un `fichier:ligne` du code X.13.
4. **Classement par probabilite** : 1ere cause = la plus probable, derniere = cas rare.
5. **Une seule precision a la fois** : si la question est ambigue, demander UNE precision ciblee et continuer.
6. **Signaler les prerequis implicites** : une option DIVA en requiert souvent une autre.

---

## Workflow (4 etapes, 2 checkpoints)

### Etape 1 -- Comprehension (CP1 si besoin)

Lire la question telle qu'elle a ete transmise (chat, capture, texte libre).
Identifier :
- **Action du demandeur** : qu'a-t-il fait ? (active option, cree un enreg, lance un traitement)
- **Comportement attendu** : qu'attendait-il de voir ?
- **Comportement observe** : que voit-il reellement ?
- **Module ou zone** : dossier, zoom, saisie, batch, menu...

> **CHECKPOINT CP1 -- Besoin d'une precision ?** *(conditionnel)*
>
> Ne declencher que si la question est trop ambigue pour avancer. Exemples :
> - module non identifiable (DAV / compta / regl / tiers ?)
> - symptome evasif ("ca ne marche pas" sans preciser quoi)
> - date relative ambigue ("comme hier")
>
> Demander **une seule** question ciblee (pas une batterie). Exemple :
> "Juste pour cadrer : c'est sur un zoom, un ecran de saisie, ou un traitement batch ?"
>
> Si la question est suffisamment claire (cas le plus frequent avec les collegues
> experimentes) : **ne pas declencher CP1**, passer direct etape 2.

### Etape 2 -- Traduction metier -> technique

Utiliser le lexique `reference/lexique-metier-technique.md` pour traduire chaque
terme conversationnel en **symbole DIVA grep-able** :

- "option dans le dossier" -> `SOC.EntCodN(N)`
- "zoom client" -> `a5rsrub.dhsq`, `grtz002_sql.dhsp`
- "gestion des X par Y" -> `Soc_Gerer_X_Y`
- etc.

Produire une liste mentale de **5-8 symboles candidats** a investiguer.

Si un concept n'est pas dans le lexique : faire une inference raisonnable a partir
des conventions DIVA (prefixe domaine + type de fichier) et noter le nouveau concept
pour enrichissement ulterieur du lexique.

### Etape 3 -- Investigation ciblee

**Budget** : 4-6 appels d'outils en PARALLELE, pas plus. Chaque appel doit etre une
recherche / lecture precise, pas une exploration large.

Types d'appels :
- **Grep** sur les symboles techniques dans `{CHEMIN_ERP_STANDARD}`
- **Read** cible sur une ligne precise d'un fichier identifie
- **Neo4j Cypher** (MCP `diva-mcp`) pour explorer les definitions de fonctions, si disponible

Contraintes :
- Lancer **tous** les grep en parallele dans un seul message
- Limiter chaque Grep a `head_limit: 20-30` pour eviter la sur-information
- Cibler en priorite les fichiers `*.dhsq` (filtres SQL), `*.dhsp` (logique), `*.dhsf` (masques)

Pour chaque symbole matche, noter :
- `fichier:ligne` precis
- procedure englobante (si applicable)
- snippet de 5-10 lignes pour comprendre la condition

### Etape 4 -- Classement + formatage chat-ready

**4a.** Parcourir `reference/patterns-causes.md` et selectionner les patterns
compatibles avec les symptomes.

**4b.** Pour chaque pattern selectionne, formuler :
- Une formulation courte (1 phrase) de la cause
- La reference `fichier:ligne` issue de l'etape 3
- L'action de verification concrete (requete SQL, lecture de parametre ERP, lecture de fichier)

**4c.** Classer par probabilite decroissante. Regles de priorisation :
- Prerequis standard d'abord (pattern P1) : "sans ca tout tombe"
- Puis symptomes lies aux donnees historiques (P3)
- Puis contexte utilisateur (P2, P8)
- Puis parametrage fin (P4, P5)
- Puis cas rares (P6, P7, P9, P10)

**4d.** Rediger la reponse dans le format `reference/chat-ready-format.md` :
- Paragraphe d'intro (< 3 lignes) nommant le symbole principal
- Causes numerotees avec gras
- Check-list finale ordonnee
- Ligne de conclusion

> **CHECKPOINT CP2 -- Red team sur le chat-ready**
>
> Avant d'afficher la reponse, Claude verifie mentalement :
>
> 1. **CA1 -- < 40 lignes ?** Compter. Si > 40, condenser.
> 2. **CA2 -- 1 a 5 causes classees ?** La premiere est-elle la plus probable ?
> 3. **CA3 -- Chaque cause a `fichier:ligne` ?** Sinon, soit trouver la ref, soit retirer la cause.
> 4. **CA4 -- Check-list ordonnee ?** Commence par le controle le plus critique.
> 5. **CA7 -- Prerequis implicites signales ?** Ex: si `EntCodN(24)`, mentionner `EntCodN(22)`.
> 6. **Format** : pas de `#`/`##`/`###`, pas de tableaux, pas de blocs code multi-lignes, pas de jargon pipeline.
> 7. **Destinataire** peut-il copier-coller sans reformuler ?
>
> Si un point manque, corriger avant d'afficher. Pas de CP5-style "validation par humain"
> explicite -- la reponse est directement affichee au collaborateur qui jugera lui-meme.

---

## Exemple de reference

Voir `reference/golden-example-nicolas.md` pour un cas complet (chat de Nicolas SINGER
2026-04-23 sur "tiers par etablissement"), avec le scoring des 7 CA.

---

## Scripts

Ce skill est majoritairement **LLM-driven**. Il fournit un seul helper optionnel :

- `scripts/translate_keywords.py` -- prend un texte en francais et liste les symboles
  candidats du lexique, accelerant l'etape 2.

Pas de script d'orchestration : le SKILL.md guide directement Claude.

---

## References

- `reference/chat-ready-format.md` -- spec du format de sortie
- `reference/lexique-metier-technique.md` -- traduction concept conversationnel -> symboles DIVA
- `reference/patterns-causes.md` -- catalogue des 10 patterns de causes recurrentes
- `reference/golden-example-nicolas.md` -- exemple de reference, cas Nicolas 2026-04-23
- Use case associe : `usecases/UC-110-ASSISTER-QUESTION-FONCTIONNELLE.md`

---

## Enrichissement continu

Apres chaque invocation reelle du skill, proposer au collaborateur :
- Enrichir `lexique-metier-technique.md` si un nouveau concept a ete appris
- Ajouter le cas a `patterns-causes.md` si un nouveau pattern de cause a ete identifie
- Ajouter un nouvel exemple de reference `reference/golden-example-<cas>.md` si le cas
  est representatif d'une famille recurrente

L'efficacite du skill augmente avec la taille du lexique et du catalogue.
