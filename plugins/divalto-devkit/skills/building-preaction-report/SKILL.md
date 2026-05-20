---
name: building-preaction-report
description: >
  Assemble un rapport d'analyse pre-action a partir des 3 JSON intermediaires
  (request, candidates_x12, evidence_x13). Modele catalogue-driven : evalue 9 types
  de contenus par pertinence (via `content_types.py`), amorce deterministement la
  matiere de chaque type retenu (propositions, grep commands, table Ce4, ...), assemble
  les fragments Jinja correspondants. Produit un markdown et un JSON de metriques avec
  tracabilite `types_included`. Applique les regles de marquage X.12/X.13 systematique
  et les criteres de qualite pre-action. A utiliser quand les 3 JSON (request,
  candidates, evidence) sont disponibles et qu'il faut produire le rapport markdown
  final destine au developpeur.
---

# Building Pre-Action Report

## Contenu

- Utilisation rapide
- Parametres d'entree
- Livrables
- Structure du rapport (7 sections)
- Metriques JSON parallele
- Regles de qualite
- Scripts disponibles
- References

---

## Utilisation rapide

```
py .claude/skills/building-preaction-report/scripts/build_report.py \
    --request output/request.json \
    --candidates output/candidates_x12.json \
    --evidence output/evidence_x13.json \
    --output-dir output
```

Le script calcule automatiquement le slug (40 car max, ASCII-lowercase) depuis `request.titre` et la date (`YYYYMMDD` locale). Les 2 livrables sont ecrits dans `--output-dir`.

---

## Parametres d'entree

| Parametre | Format | Obligatoire | Defaut |
|-----------|--------|-------------|--------|
| `--request` | Chemin `request.json` (phase 1) | Oui | -- |
| `--candidates` | Chemin `candidates_x12.json` (phase 2) | Oui | -- |
| `--evidence` | Chemin `evidence_x13.json` (phase 3) | Oui | -- |
| `--output-dir` | Repertoire de sortie | Non | `output/` |
| `--slug` | Slug manuel (override auto) | Non | auto depuis `request.titre` |
| `--date` | Date YYYYMMDD (override) | Non | date du jour |

---

## Livrables

### Rapport markdown

```
output/preaction-<slug>-<YYYYMMDD>.md
```

Encodage : **UTF-8 + LF** (livrable humain, pas source DIVA). Structure detaillee dans [reference/report-sections.md](reference/report-sections.md).

### JSON de metriques

```
output/preaction-<slug>-<YYYYMMDD>.json
```

Metriques pour evaluation : nb_exemples, nb_fonctions, nb_impacts, confiance_globale, couverture_neo4j, duree_seconds_total.

---

## Structure du rapport (7 sections)

Structure canonique : 7 sections + annexe (detail dans [reference/report-sections.md](reference/report-sections.md)). En resume :

1. **Comprehension de la demande** (depuis request.json)
2. **Exemples de code DIVA similaires** (depuis evidence.confirmed + evidence.new_findings)
3. **Fonctions du langage DIVA utiles** (deduites des snippets + catalogue statique)
4. **Etude d'impact** (depuis evidence.impact.callers)
5. **Endroit ou agir** (propositions generees par le LLM au CP5 -- le template reserve la section)
6. **Pistes de recherche complementaires** (suggestions contextuelles)
7. **Points d'attention** (surcharges, conventions, disclaimers)

Plus l'**annexe "Sources consultees"** avec les stats de collecte.

---

## Metriques JSON parallele

Schema : voir `reference/report-sections.md` section "JSON de metriques".

Champs cles :

| Metrique | Calcul |
|----------|--------|
| `exemples_similaires` | len(evidence.confirmed) + len(evidence.new_findings) |
| `fonctions_utiles` | Comptage des fonctions extraites des snippets (heuristique) |
| `appelants_potentiels` | len(evidence.impact.callers) |
| `disclaimers_x12` | Comptage des marqueurs `[X.12]` dans le rapport |
| `confirmed_x13` / `disappeared_x13` / `new_x13` | Comptage des statuts |
| `confiance_globale` | `forte` si >=3 confirmed et >=5 functions, `moyenne` si >=1 confirmed, `faible` sinon |
| `couverture_neo4j` | `disponible` / `partielle` / `absente` (selon `evidence.scope.neo4j_status_upstream`) |

---

## Regles de qualite

Appliquees par le script (validation post-render) :

1. **Borne dure** : max 5 exemples section 2, max 12 fonctions section 3, max 15 appelants section 4.1
2. **Marquage** : toute occurrence de `[X.12]` doit etre accompagnee d'un statut CONFIRME / DISPARU / NOUVEAU si la phase 3 a tourne
3. **Chemin absolu** : toute reference `fichier:ligne` est un chemin absolu (sinon le rapport est rejete)
4. **En-tete complete** : type / domaine / confiance / couverture Neo4j obligatoires
5. **Confiance degradee** : si moins de 3 exemples confirmes, `confiance_globale = faible` et un encadre explique les ecarts

Voir `reference/report-sections.md` pour le detail par section.

---

## Conventions de templating (RETEX 2026-04-18 -- "correct du premier coup")

Le renderer Markdown/Mermaid de Claude Desktop est un sous-ensemble restreint. Les fragments Jinja2 doivent respecter :

### Markdown

- **Jamais** d'italique `_..._` autour d'un paragraphe contenant `<...>` en inline code -- le renderer casse l'italique en voyant `<champ>` comme balise HTML inconnue. Utiliser **blockquote + bold label** : `> **Attendu :** texte avec \`ENT.$champ\`...`.
- **Placeholders textuels** : preferer `$foo`, `{foo}` ou `FOO` aux `<foo>`. Les angle brackets hors code block sont interpretes comme HTML.
- **Italique simple** (sans code ni placeholders) : OK, ex. `_Pas de constantes nommees._`.
- **Features fiables** : `#`, `**bold**`, `` `code` ``, tables, `[lien](url)`, `> quote`, `<details><summary>`, listes ordonnees/non-ordonnees.

### Mermaid

- **Seul `<br/>` est garanti** dans les labels de noeuds. **Ne pas utiliser** `<code>`, `<em>`, `<span>`, `<strong>` -- ils s'affichent en dur.
- **Stadium** : utiliser `N(["label"])`, **pas** `N@{shape: stadium, label: "..."}` (syntaxe nouvelle pas toujours supportee).
- **Quotes dans labels** : les supprimer ou utiliser `#quot;` (pas `&quot;`, pas toujours decode).
- **Labels courts** : idealement < 50 caracteres. Si plus long, deporter l'info dans une liste "Ouvrir les fichiers" apres le diagramme.

### Contenu (anti-stub)

- **Jamais** de phrase commencant par un pronom relatif (`qui`, `que`, `dont`, `ou`) apres un label de bullet. Si l'extraction automatique ne reconstitue pas un enonce complet, **ne pas generer la ligne** -- meilleure omission que stub.
- **Jamais** de placeholder generique inutile (`(cf. ticket d'origine)`, `a completer`, `TODO`). Le validator `validate_report()` les detecte.
- **Anomalie section** : produire 3 elements structures (contexte declencheur / etat observe / etat attendu) ou echouer et laisser le LLM completer au CP5.

### Test battery obligatoire avant merge

Chaque fragment `.md.j2` doit avoir un golden test avec :
1. ReportContext nominal (donnees completes)
2. ReportContext pathologique (`enclosing_block=None`, `targeted_symbol=""`, `file=""`, etc.)
3. Assertion : le rendu passe `validate_report()` sans error.

Emplacement : `scripts/tests/test_fragments.py` + `tests/golden/*.md`.

**Rationale** : les bugs B10 (Mermaid `<code>`), B11 (Mermaid stadium), B12 (italique+angle brackets) ont couté 2h d'iteration le 2026-04-18. Un test golden les aurait attrapes hors-ligne.

---

## Scripts disponibles

```
scripts/build_report.py
scripts/content_types.py
scripts/templates/report.md.j2              # Squelette
scripts/templates/fragments/*.md.j2         # Fragments par type de contenu
scripts/tests/test_fragments.py             # Tests unitaires (golden + validator)
```

Dependance : Jinja2 3.1+ (prerequis commun du workspace, voir `.claude/skills/README.md`).

### Lancer les tests

```
cd .claude/skills/building-preaction-report/scripts
py -m unittest tests.test_fragments -v
```

Couverture actuelle (19 tests) :
- `TestChainOfBlame` (6 tests) : cas nominal, action sans ligne, fn_noline, available=false, liens file://, gestion des guillemets
- `TestValidatorExtended` (13 tests) : detection et non-detection des patterns interdits (fragments de phrase, italique+angle brackets, stubs, HTML Mermaid) + verification du rapport final publie

**Avant toute modification d'un fragment `.md.j2`** : lancer les tests, modifier, relancer. Un fragment qui casse un test ne part pas en production.

---

## References

- `reference/report-sections.md` -- detail des 7 sections, metriques, critere de qualite
