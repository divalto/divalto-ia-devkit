---
name: analyzing-diva-request
description: >
  Orchestre l'analyse pre-action d'une demande DIVA (user story + criteres d'acceptation,
  ou ticket myService d'anomalie) en mode collaboratif. Produit un rapport de preparation
  pour le developpeur : exemples de code similaires dans l'ERP X.13, fonctions du langage
  DIVA reutilisables, etude d'impact, points d'action concrets (fichiers/fonctions a toucher),
  pistes complementaires et points d'attention. Strategie hybride : interroge en priorite
  le graphe Neo4j `diva-mcp` (snapshot X.12 advisory) puis verifie systematiquement dans
  le code X.13 standard. 5 checkpoints de validation humaine -- Claude s'arrete apres chaque
  etape significative pour expliquer et attendre le feu vert. A utiliser quand un developpeur
  colle une user story ou un ticket dans la conversation et demande par ou commencer.
---

# Analyzing DIVA Request

## Contenu

- Quand utiliser
- Prerequis
- Carte des 5 checkpoints
- Workflow complet (4 phases)
- Mode direct (MCP indispo)
- Exemple d'invocation
- Scripts disponibles
- References

---

## Quand utiliser

Un developpeur arrive avec :
- une **user story + criteres d'acceptation** (feature), ou
- un **ticket myService / JIRA** (anomalie).

Il colle le texte dans la conversation et ne sait pas par ou commencer. Ce skill produit un **rapport d'analyse pre-action** qui contient, **selectionnes par pertinence** parmi un catalogue de 9 types :
1. Exemples de code DIVA similaires cibles sur symbole nomme
2. Fonctions du langage DIVA utiles (feature surtout)
3. Etude d'impact (callers + propagation)
4. Endroit ou agir (propositions d'action amorcees)
5. Pistes de recherche complementaires
6. Points d'attention (surcharges/effets de bord reels)
7. Constantes et conventions metier (Ce4, TiCod, ...)
8. Parametrage dossier (si detecte dans keywords)
10. Verification prealable (commandes a lancer avant de coder)

**Seuls les types pertinents pour CETTE demande sont inclus** (tracabilite dans `metrics.json` via `types_included`). Pour un ticket anomalie, le type 2 est generalement omis (le dev connait le langage). Pour une feature, les types 7/8 sont moins souvent pertinents.

Le resultat final est un markdown dans `output/preaction-<slug>-<YYYYMMDD>.md` + des metriques JSON avec tracabilite de la selection.

---

## Prerequis

- **Skills consommes** (tous dans `.claude/skills/`) :
  - `parsing-diva-request`
  - `querying-diva-graph`
  - `searching-erp-sources`
  - `building-preaction-report`
- **MCP** : `diva-mcp` (Neo4j X.12 advisory) -- optionnel, degradation gracieuse si indispo
- **Chemin ERP** : `{CHEMIN_ERP_STANDARD}` (par defaut `C:/Developpements harmony/Standard/Version X.13`)
- **Python** : launcher `py`, Jinja2 3.1+

---

## Carte des checkpoints

```
Developpeur colle user story / ticket
         |
         v
  Phase 1 : PARSE
         |
   CP1 -- Comprehension / reformulation
         |
         v
   decision CP2 : perimetre de recherche
         |
         v
  Phase 2 : QUERY NEO4J (advisory X.12)
         |
   CP3 -- Candidats Neo4j priorises
         |
         v
  Phase 3 : VERIFY X.13 (source de verite)
         |
   CP4 -- Confirme / disparu / nouveau
         |
         v
  Phase 4a : BUILD FACTS (fond, refs sources)
         |
   CP5a -- Validation du fond (facts.json)
         |
         v
  Phase 4b : RENDER LIVRABLE (forme, 3 couches)
         |
   CP5b -- Validation de la forme (livrable.md)
         |
         v
     Livrable developpeur (autonomie documentaire)
```

Separation fond / forme : le fond (`facts.json`) porte les refs aux sources ; le
livrable (`.md` 3 couches : strategique / tactique / technique) est autonome et
n'affiche aucune ref. Un auditeur qui veut verifier ouvre le facts.json.

Format des checkpoints : `> **CHECKPOINT CPn -- titre**`. A chaque CP, Claude doit :
1. Presenter ce qui a ete fait, les choix, le resultat
2. Attendre la validation humaine
3. Si refus : corriger et represenrer

Ne jamais sauter un checkpoint, meme trivial.

---

## Workflow complet (4 phases)

### Phase 1 -- Parse de la demande

Le developpeur colle le texte de la demande dans la conversation.

```
echo "<texte colle par le developpeur>" | \
  py .claude/skills/parsing-diva-request/scripts/parse_request.py \
    > output/request.json
```

Sortie : `request.json` avec type, resume, acteurs, donnees, domaine_pressenti, keywords, CA, message_erreur, needs_clarification.

Lire `request.json` et presenter au developpeur ce que Claude a compris.

**RETEX 2026-04-18 Session 3 -- Limites connues du parser** : sur une US longue au format narratif (multi-CA entrelaces, messages d'erreur avec placeholders `JJ/MM/DDDD`), `parse_request.py` produit souvent :
- `domaine_pressenti` errone (ex: matche "reglement" au lieu d'"affaire" comme domaine dominant)
- `keywords_techniques` faibles (1-2 items)
- `donnees` polluees par des placeholders (`DDDD`, `PREFPINO`) detectes comme data
- `ca_detectes` vide

**Claude doit systematiquement red-team le parse au CP1** et proposer des corrections :
1. Verifier le domaine contre la liste canonique des prefixes ERP (GT_, RT_, GG_, CC_, RC_, PP_, GA_, QU_, GR_, A5)
2. Enrichir `keywords_techniques` avec les noms metier DIVA canoniques (Situation, PaiementDirect, SousTraitant, Autoliquidation, etc.)
3. Nettoyer `donnees` des placeholders
4. Extraire les CA depuis le texte narratif et les inscrire dans `ca_detectes` (format "CAn: <description>")

L'edition manuelle du `request.json` au CP1 est acceptee -- c'est meme le role du LLM : le parser fait le gros oeuvre, le LLM affine avec le contexte metier.

> **CHECKPOINT CP1 -- Comprehension de la demande**
> Presenter au developpeur :
> - Type detecte (feature / ticket / unknown)
> - Resume de la reformulation (1-3 phrases)
> - Acteurs metier, donnees manipulees, domaine ERP pressenti
> - Keywords techniques et metier extraits
> - CA detectes (si feature) ou message d'erreur (si ticket)
> - Flag `needs_clarification` si leve
>
> Question : **Ma comprehension est-elle correcte ? Des precisions a ajouter ?**
>
> Si `needs_clarification=true` OU type=unknown : demander explicitement au developpeur de completer avant de continuer.
> Attendre validation avant phase 2.

---

### Phase 2 -- Query Neo4j (advisory X.12)

Generer les requetes Cypher parametrees :

```
py .claude/skills/querying-diva-graph/scripts/query_neo4j.py \
    --mode generate --request output/request.json \
    > output/queries.json
```

Lire `queries.json` pour obtenir la liste des requetes a executer.

**Pour chaque requete**, invoquer l'outil MCP :

```
mcp__2e56c8ef-7b33-4e7d-9991-3a50dc1e7f1b__read_neo4j_cypher(query=<cypher>)
```

(Le prefixe `mcp__2e56c8ef-...` est l'identifiant dynamique du MCP `diva-mcp` dans la session.)

Collecter les resultats bruts dans un dict Python dont les cles sont `<template>:<parameter>` et les valeurs sont les listes de rows retournees. Ecrire dans `output/raw_results.json`.

**Si une requete echoue** (timeout, erreur) : continuer avec les autres. Si toutes echouent : passer en mode direct (voir section "Mode direct").

Consolider :

```
py .claude/skills/querying-diva-graph/scripts/query_neo4j.py \
    --mode consolidate --request output/request.json \
    --results output/raw_results.json \
    > output/candidates_x12.json
```

Cadrage CP2 avant le CP3 : **3 scenarios** declenchent ce checkpoint conditionnel :
- `> 50` candidats : perimetre trop large, restreindre avant phase 3
- `0 candidat` (ou < 2) : requete Cypher muette, **ne pas avancer en phase 3 sur un graphe vide**
- Doute du LLM sur la pertinence des keywords

> **CHECKPOINT CP2 -- Perimetre et mots-cles (si > 50 candidats, 0 candidat, OU doute)**
> Ce CP est conditionnel mais **obligatoire** dans les 3 cas ci-dessus.
>
> **Cas "> 50 candidats"** : presenter top 10, distribution par module, keywords utilises. Proposer de restreindre (ajouter keywords, restreindre domaine).
>
> **Cas "0 candidat" (RETEX 2026-04-18, renforce QW1 2026-04-22)** : c'est un signal fort que le pipeline Neo4j est degradé. Avant d'avancer en phase 3 :
> 1. Verifier les keywords extraits par le parser (sont-ils specifiques et corrects ?). Rappel : `parse_request.py` expanse automatiquement les abreviations du catalogue [`abreviations-divalto.md`](../parsing-diva-request/reference/abreviations-divalto.md) (ctm <-> contremarque, pce <-> piece, cmde <-> commande, ...). Les expansions apparaissent deja dans `request.keywords_metier`.
> 2. Proposer **2-3 reformulations concretes** au developpeur :
>    - synonymes metier (ex: "piece" -> "document", "bon")
>    - abreviations DIVA **non listees** dans le catalogue (si une pertinente manque, l'ajouter au catalogue pour les prochains runs)
>    - desambiguisation du domaine si `domaine_pressenti` semble faible
> 3. Verifier que `domaine_pressenti` est correct (prefixe parmi GT_, RT_, GG_, CC_, RC_, PP_, GA_, QU_, GR_, A5).
> 4. Si Neo4j est disponible mais 0 candidat apres ces ajustements : basculer en mode direct X.13 en informant explicitement le developpeur que la phase 2 n'a rien apporte.
>
> **Ne pas continuer en silence avec `candidates_x12` vide** -- sans signal amont, la phase 3 grep aveugle produit majoritairement du bruit.
>
> Question : **Ces candidats te semblent pertinents ? Faut-il restreindre les keywords / les elargir / changer de domaine ?**

> **CHECKPOINT CP3 -- Candidats Neo4j priorises (advisory X.12)**
> Presenter :
> - Nombre de candidats par categorie (programs, functions, tables, entities)
> - Top 10 candidats avec score
> - **Disclaimer X.12** explicite sur chaque liste : "Snapshot X.12, ne reflete pas X.13"
> - Pistes ecartees et pourquoi (hors-scope)
>
> Question : **Ces candidats sont-ils pertinents ? Je lance la verification X.13 ?**
>
> Si le developpeur retire des candidats : editer `candidates_x12.json` en consequence avant la phase 3.
> Attendre validation avant phase 3.

---

### Phase 3 -- Verify X.13 (source de verite)

**Etape 3a** -- Identifier les symboles metier a cibler dans les snippets. Parcourir `candidates_x12.json.functions` et extraire les noms de procedures/fonctions qui matchent le domaine du ticket (ex: pour contremarque : `Supprimer_LienContremarque`, `ActionERP_Contremarque_*`). Si `candidates_x12.json.functions` est vide (cas frequent quand Neo4j n'a pas remonte de symbole precis), deriver depuis `request.keywords_techniques` et proposer la liste au developpeur.

Lancer la verification avec le flag `--symbols` pour centrer les snippets sur les symboles cibles :

```
py .claude/skills/searching-erp-sources/scripts/verify_x13.py \
    --candidates output/candidates_x12.json \
    --request output/request.json \
    --erp-root "{CHEMIN_ERP_STANDARD}" \
    --domain-scope auto \
    --symbols "<Symbol1>,<Symbol2>,..." \
    --max-matches 50 --max-files 20 --timeout 60 \
    > output/evidence_x13.json
```

Lire `evidence_x13.json` : `confirmed` (chacun avec potentiellement `targeted_symbol`), `disappeared`, `new_findings`, `impact.callers`.

Si peu de confirmes (< 3) et domaine-scope etait limite : proposer au developpeur d'elargir avec `--domain-scope all` (consentement explicite car plus lent).

> **CHECKPOINT CP4 -- Verification X.13 (confirme / disparu / nouveau)**
> Presenter :
> - Nombre de confirmes / disparus / nouveaux
> - Liste des confirmes avec `fichier:ligne` + fonction englobante + `targeted_symbol` (si present)
> - Liste des disparus (candidats X.12 absents de X.13)
> - Liste des nouveaux (decouvertes X.13 hors graphe)
> - Metrique : duree, fichiers examines, bornes atteintes
>
> Question : **Ces pistes confirmees sont-elles les bonnes ? Besoin de cibler d'autres symboles ou d'approfondir un element ?**
>
> Si le developpeur veut cibler d'autres symboles : relancer `verify_x13.py` avec une liste `--symbols` etendue. Si un fichier/ligne merite un approfondissement : relancer `extract_context.py`. Attendre validation avant phase 4.

---

### Phase 4 -- Fond (facts.json) + Forme (livrable 3 couches)

**Phase 4a -- Generer le FOND** via `build_facts.py` :

```
py .claude/skills/building-preaction-report/scripts/build_facts.py \
    --request output/request.json \
    --candidates output/candidates_x12.json \
    --evidence output/evidence_x13.json \
    --output-dir output
```

Le script :
1. Calcule un `ReportContext` depuis les 3 JSON.
2. Evalue chaque type du catalogue (`content_types.py`) -> `selection` avec score, inclus/omis, raison.
3. Amorce le contenu de chaque type (seeds heritage de `build_report.py`).
4. Transforme chaque seed en `Claim` typees (`example`, `call_chain`, `action_site`, `verification`, `literal_table`, `overwrite_warning`, `dossier_param`, `hint`, `impact_caller`, `function`).
5. Nettoie les textes narratifs (supprime les paths absolus, les `foo.dhsp:123`).
6. Assemble un `FactsDocument` valide (schema v1.0).
7. Ecrit `output/preaction-<slug>-<YYYYMMDD>.facts.json` + `output/preaction-<slug>-<YYYYMMDD>.metrics.json`.

> **CHECKPOINT CP5a -- Validation du fond**
>
> Presenter :
> - Chemin du facts.json et du metrics.json
> - Nombre de claims par layer (strategic / tactical / technical)
> - `selection` : types inclus (ids, raisons) et types omis (ids, raisons)
> - Verdict synthese extrait du fond
>
> Questions :
> - **Les claims reflechissent-ils correctement ce qui a ete trouve en phase 3 ?**
> - **La selection est-elle adequate ? Un type important est-il omis ou surrepresente ?**
>
> Si le dev veut corriger (enlever un claim errone, forcer l'inclusion d'un type
> omis) : editer le facts.json directement. Il reste la source de verite pour le
> rendu. Attendre validation avant la phase 4b.

---

**Phase 4b -- Generer la FORME** via `render_livrable.py` :

```
py .claude/skills/rendering-preaction-livrable/scripts/render_livrable.py \
    --facts output/preaction-<slug>-<YYYYMMDD>.facts.json \
    --output-dir output
```

Le renderer :
1. Charge le facts.json.
2. Filtre les claims dont le content_type_id est exclu par `selection`.
3. Assemble les 3 couches (strategique / tactique / technique) via Jinja2.
4. Applique le validator anti-regression (stubs, chemins absolus, marqueurs X.12/X.13,
   refs fichier:ligne, balises HTML non supportees Mermaid, fragments pronom-relatif).
5. Ecrit `output/preaction-<slug>-<YYYYMMDD>.md` (UTF-8 + LF).

Le livrable n'affiche **aucune** reference aux sources : chemins absolus, balises
statut X.12/X.13, `foo.dhsp:123` -- tout cela reste dans le facts.json. Le dev
qui veut auditer une affirmation ouvre le facts.json ou lance le skill
`reviewing-preaction-facts` (optionnel).

**Enrichissement LLM marginal** (contrairement a V1) : le script amorce **deterministiquement** la matiere de chaque type retenu. Le LLM intervient au CP5 uniquement pour :

1. **Preciser l'hypothese** dans les propositions de la section "Endroit ou agir" (type 4) -- 1 ligne par proposition.
2. **Ajouter le "pourquoi"** sur 1 ligne par exemple de la section "Exemples" (type 1) si le symbole cible ne suffit pas.
3. **Categoriser les fonctions par famille** si le type 2 est inclus (feature).
4. **Verifier la coherence de la selection** -- proposer au developpeur de surcharger manuellement si un type pertinent a ete omis ou inversement.

Utiliser l'outil `Edit` pour modifier le markdown. Ne **pas** reecrire le rapport entier -- modifications chirurgicales (principe 3 de `4PRINCIPLES.md`).

**Etape obligatoire avant CP5 -- Auto-reception dev persona + scoring grille** (RETEX 2026-04-18)

Avant de presenter le rapport au developpeur, Claude doit appliquer **3 rituels** (memoire `feedback_uc100_rituals.md`) + un **scoring structure** :

**Rituel R1 -- Red team (3 questions)** lues sur le markdown final :
1. Si j'etais le collaborateur sans contexte, qu'est-ce qui me sauterait aux yeux comme bizarre ?
2. Chaque phrase est-elle un enonce complet (sujet + verbe + complement) ?
3. Chaque balise (MD, Mermaid, HTML) va-t-elle effectivement rendre comme prevu dans Claude Desktop ?

**Rituel R2 -- Non-superlatif** : interdit de dire "TRES satisfaisant / parfait / excellent" sans score mesure.

**Rituel R3 -- Max 2 reruns** : si 2 `build_report.py` ne suffisent pas, basculer en `Edit` chirurgical + signaler bug amont.

**Scoring structure** : noter chaque axe 0-3, calculer la moyenne :

| Axe | Questions a se poser pendant la lecture |
|-----|------------------------------------------|
| 1. Comprehension anomalie | Observe est-il une phrase complete ? Attendu est-il precis ? Declencheur UI identifie ? |
| 2. Chaine d'appels | Labels Mermaid lisibles (pas de HTML non rendu) ? Causalite correcte (lignes attribuees a la bonne fonction) ? Gap marque en orange ? |
| 3. Plan d'action | Commandes concretes et copiables ? Critere de succes explicite ? |
| 4. Tracabilite fichiers | `file://` cliquables ? Chemins absolus et encodes ? |
| 5. Reference metier | Tables de codes (Ce4...) presentes quand pertinent ? |
| 6. Densite / signal | Taille < 200L (cf `metrics.report_size_lines`) ? Signal/bruit eleve ? |

**Seuils** :
- Score moyen **>= 2.8/3** : presenter au CP5 (CA12 "tres satisfaisant").
- Score moyen **2.3-2.8** : corriger chirurgicalement (`Edit`) puis re-scorer. NE PAS presenter tel quel.
- Score moyen **< 2.3** : le probleme est amont (pipeline, inputs). Ne pas bricoler le rapport -- remonter au CP2/CP3/CP4 pour ajuster la source.

**Violations bloquantes** (score 0 sur l'axe concerne si presentes) :
- Un observe commence par un pronom relatif ("qui", "que", "dont")
- Une balise HTML non rendue dans Mermaid (`<code>`, `<em>`)
- Un italique `_..._` contient un placeholder `<X>` (casse le rendu)
- Un stub `(cf. ticket d'origine)`, `a completer`, `TODO`, `FIXME`
- Une attribution causale fausse dans la chaine d'appels

**Verification automatique** : le script `build_report.py` lance `validate_report()` a la fin et echoue (exit 4) si un pattern interdit est detecte. Si `validate_report()` echoue, ne **pas** corriger superficiellement le markdown : corriger le fragment Jinja ou la logique amont et relancer les tests (`py -m unittest tests.test_fragments`).

Livrer au CP5 **uniquement** le rapport qui :
1. Passe `validate_report()` (exit 0)
2. Score >= 2.8/3 sur la grille dev persona
3. Ne contient aucune violation bloquante ci-dessus

> **CHECKPOINT CP5b -- Validation de la forme (livrable)**
>
> Presenter :
> - Chemin du livrable `.md`
> - Taille (lignes), cible < 200 pour un ticket typique
> - Extrait de chaque couche (3 premieres lignes de strategique / tactique / technique)
> - Resultat du validator (0 violation attendue -- sinon le rendu a echoue en amont)
> - Rituels R1/R2/R3 (red team, non-superlatif, max 2 reruns) appliques au livrable
> - Scoring grille 6 axes applique au livrable, moyenne attendue >= 2.8/3
>
> Questions :
> - **Le livrable est-il lisible et actionnable ? La couche tactique donne-t-elle une vraie carte d'implementation ?**
> - **La couche strategique est-elle autonome (chef projet peut-il s'y arreter) ?**
> - **Ajustements visuels avant livraison ? (tailles sections, wording...)**
>
> Si le developpeur veut ajuster :
> - Modification du *contenu* (claim errone, type omis a forcer) -> editer le facts.json et relancer render_livrable.py.
> - Modification de la *forme* (ordre, ton, structure) -> editer les templates Jinja2 du skill `rendering-preaction-livrable` puis re-render.
>
> **Ne pas editer le livrable.md directement** : il est regenerable a partir du fond. La correction chirurgicale doit viser le facts.json ou les templates.

---

## Mode direct (MCP indispo)

Si `diva-mcp` est inaccessible (erreur reseau, token expire, timeout global) :

1. A la phase 2, `mcp__...__read_neo4j_cypher` echoue
2. Invoquer la consolidation en mode unavailable :
   ```
   py .claude/skills/querying-diva-graph/scripts/query_neo4j.py \
       --mode consolidate --request output/request.json \
       --neo4j-status unavailable \
       > output/candidates_x12.json
   ```
3. Presenter un CP3 allege : "Neo4j inaccessible, verification X.13 directe"
4. Phase 3 : `verify_x13.py` utilise `request.keywords_techniques` uniquement. Toutes les trouvailles sont `[NOUVEAU X.13]`.
5. Phase 4 : le rapport indique "Couverture Neo4j : absente" en en-tete.

Le workflow ne plante jamais.

---

## Exemple d'invocation

Developpeur colle :

```
En tant que gestionnaire reglement, je veux saisir la famille de reglement
sur la fiche client, afin de regrouper les reglements par famille.

Criteres d'acceptation :
- Le zoom famille reglement est accessible depuis le menu Retail
- La saisie de la famille est obligatoire sur la fiche client
- La suppression d'une famille est bloquee si des reglements existent
```

Claude enchaine :
1. **Phase 1** : parse_request.py -> CP1 "Ma comprehension..."
2. **Phase 2** : query_neo4j.py generate + MCP -> consolidate -> CP3 "Candidats pertinents..."
3. **Phase 3** : verify_x13.py -> CP4 "Pistes confirmees..."
4. **Phase 4** : build_report.py + enrichissements LLM -> CP5 "Rapport final..."

Livrable : `output/preaction-famille-reglement-fiche-client-YYYYMMDD.md` (prefixe fichier defini par `build_report.py`).

---

## Scripts disponibles

Cet orchestrateur n'a **aucun script propre** -- il chaine les scripts des 4 skills atomiques. Voir :

- `.claude/skills/parsing-diva-request/scripts/parse_request.py`
- `.claude/skills/querying-diva-graph/scripts/query_neo4j.py`
- `.claude/skills/searching-erp-sources/scripts/verify_x13.py`
- `.claude/skills/searching-erp-sources/scripts/extract_context.py`
- `.claude/skills/building-preaction-report/scripts/build_report.py`

Pour les details de chaque script, voir les `SKILL.md` correspondants.

---

## References

- `reference/workflow.md` -- detail etape par etape avec commandes copier-coller
- `reference/report-template.md` -- rappel de la structure du rapport final
