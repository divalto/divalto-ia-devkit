# report-sections.md

## Contenu

- Section 1 -- Comprehension de la demande
- Section 2 -- Exemples de code DIVA similaires
- Section 3 -- Fonctions du langage DIVA utiles
- Section 4 -- Etude d'impact
- Section 5 -- Endroit ou agir
- Section 6 -- Pistes de recherche complementaires
- Section 7 -- Points d'attention
- Annexe -- Sources consultees
- JSON de metriques

---


Detail de chaque section du rapport genere par `build_report.py`.

## Section 1 -- Comprehension de la demande

Source : `request.json`.
Contenu genere deterministe. Le LLM, a l'etape de redaction finale, peut ajouter une note "reformulation finale apres clarifications".

## Section 2 -- Exemples de code DIVA similaires

Source : `evidence.confirmed` + `evidence.new_findings`, tries par ordre d'apparition.

Borne dure : **max 5 exemples**. Si plus sont disponibles, les 5 premiers (tri : score Neo4j decroissant puis ordre d'apparition).

Format par exemple :
- Titre = `ex.from_x12` (candidat Neo4j) ou `ex.pattern` (new finding)
- Fichier + lignes + statut obligatoires
- Fonction englobante affichee si `context_sample.enclosing_block` present
- Snippet dans un bloc de code

Section "Non retrouves en X.13" separee en fin de section 2 pour les `disappeared`.

## Section 3 -- Fonctions du langage DIVA utiles

Source : fonctions englobantes extraites des `context_sample` des confirmed.

Le template remplit automatiquement les fonctions detectees. A la redaction finale, le LLM **doit** :
- Categoriser chaque fonction en famille (`Framework`, `RecordSql`, `ISAM`, etc.)
- Ajouter des fonctions du catalogue DIVA (référence langage avancé interne) pertinentes a la demande
- Borner a 12 fonctions maximum

## Section 4 -- Etude d'impact

### 4.1 Appelants potentiels

Source : `evidence.impact.callers` (tronque a 15 max).
Format : `fichier:ligne -- appelle fonction [STATUT]` + citation de la ligne.

### 4.2 Propagation des changements

**Pas deterministe**. A la redaction finale, le LLM redige selon le type de modification envisagee :
- Ajout de champ -> impact sur les masques, dictionnaire, RecordSql
- Modification de signature -> impact sur tous les callers de 4.1
- Suppression -> verifier qu'aucun appelant n'existe

### 4.3 Surcharges existantes

A la redaction finale, le LLM :
- Cherche les patterns `OverWrittenBy` dans les snippets de la section 2
- Liste chaque surcharge detectee avec son domaine
- Explique l'impact : "le projet X surcharge cette fonction, toute modification devra etre portee la-bas"

## Section 5 -- Endroit ou agir

**Totalement redigee par le LLM a l'etape de redaction finale**. Le template fournit un squelette avec une proposition placeholder.

Regles :
- 1 a 3 propositions (pas plus)
- Chacune justifiee par un exemple de la section 2 (lien `section 2.N`)
- Indiquer le skill de generation suggere (`creating-diva-entity` pour creer, `modifying-diva-entity` pour modifier)
- Impact estime `faible/moyen/fort`

## Section 6 -- Pistes de recherche complementaires

Mixte : suggestions deterministes (Grep X.13 elargi, requete Cypher type) + suggestions contextuelles du LLM.

Regles :
- 3 a 5 items
- Types acceptes : Cypher, Grep, fichier, doc, skill
- Chaque item inclut la commande/lien/reference precise

## Section 7 -- Points d'attention

Deterministe depuis les metriques :
- Disclaimer global X.12
- Bornes atteintes oui/non
- Duree + fichiers examines
- Nombre de candidats disparus
- Clarification requise oui/non

A la redaction finale, le LLM peut ajouter des points contextuels (effets de bord, conventions domaine).

## Annexe -- Sources consultees

Statistiques de collecte. Deterministe depuis les JSON.

## JSON de metriques

Schema canonique :

```json
{
  "date": "YYYY-MM-DD",
  "slug": "<slug>",
  "request_type": "feature|ticket|unknown",
  "domaine": "RT_|GT_|...|null",
  "metrics": {
    "exemples_similaires": N,
    "fonctions_utiles": N,
    "appelants_potentiels": N,
    "propositions_action": N,
    "pistes_complementaires": N,
    "disclaimers_x12": N,
    "confirmed_x13": N,
    "disappeared_x13": N,
    "new_x13": N,
    "confiance_globale": "faible|moyenne|forte",
    "couverture_neo4j": "disponible|partielle|absente"
  },
  "confiance_globale": "...",
  "couverture_neo4j": "..."
}
```

Utilisation : comparaison de rapports sur plusieurs scenarios, calibration du skill (voir `scoring/`).
