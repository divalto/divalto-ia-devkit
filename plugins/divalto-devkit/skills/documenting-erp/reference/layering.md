# Trois couches de lecture -- documenting-erp

Le skill produit du contenu multi-audience via 3 couches. Ce document precise leur contenu, leur audience, et les regles de routage.

## Contenu

- Les 3 couches
- Profil d'audience par couche
- Regles de routage des champs
- Rendu combine vs separe

## Les 3 couches

### business

**Audience** : consultants, chefs de projet, responsables fonctionnels. Quelqu'un qui comprend le metier mais pas la technique Divalto.

**Contenu** : role metier, processus de rattachement, vocabulaire, regles metier, exemples concrets, variantes fonctionnelles.

**Exclut** : codes techniques bruts (CLI.TIERS), Natures (C20), noms de tables SQL.

### schema

**Audience** : developpeurs clients et integrateurs qui consomment l'ERP via API ou zooms, sans connaitre l'implementation interne.

**Contenu** : entites majeures, cles primaires, relations inter-entites, cardinalites, contrats d'integration, diagrammes.

**Exclut** : detail de chaque champ avec Nature, noms de fichiers sources, moulinettes CI.

### technical

**Audience** : developpeurs Divalto internes qui modifient le code.

**Contenu** : liste complete des champs avec Natures, indexes, fichiers sources (.dhsd, .dhsf, .dhsp), zooms, moulinettes, notes de performance, audit.

**Inclut tout** ce qui est utile a la maintenance du code.

## Profil d'audience par couche

| Dimension               | business         | schema            | technical            |
|-------------------------|------------------|-------------------|----------------------|
| Vocabulaire             | Metier           | Mixte             | Technique            |
| Volume attendu          | Court (1 page)   | Moyen (2 pages)   | Long (5-10 pages)    |
| Frequence de mise a jour| Trimestrielle    | Semestrielle      | Continue             |
| Verification humaine    | Obligatoire      | Recommandee       | Validation par tests |
| Presence de code        | Jamais           | Extraits          | Systematique         |

## Regles de routage des champs

Chaque schema declare `rendering_layers:` au bas du fichier, listant quels champs top-level de l'instance apparaissent dans quelle couche.

Exemple pour `entity` :
```yaml
rendering_layers:
  business:  [code, label, module, base, business]
  schema:    [code, label, schema.primary_table, schema.primary_key, schema.satellite_tables, schema.relations, schema.diagram_mermaid]
  technical: [code, label, technical, meta]
```

Lecture : la couche `business` affiche `code`, `label`, `module`, `base`, et tout le sous-objet `business:`. La couche `schema` affiche un sous-ensemble de `schema:`. La couche `technical` affiche toute la section `technical:` plus `meta:`.

### Cas des champs `field` (couche fine)

Un champ individuel dans `technical.fields[]` a un attribut `layer:` :
- `all` : visible en `schema` et `technical` (ex: TIERS, DOS, NOM)
- `schema+technical` : idem `all` (alias plus explicite)
- `technical-only` : visible seulement en `technical` (ex: USERCR, Filler, LATITUDE)

La couche `business` ne liste jamais les champs individuels -- elle decrit le role, pas la structure.

## Rendu combine vs separe

Trois strategies possibles pour le renderer :

### Strategie A -- Trois documents separes

```
DAV-business.md
DAV-schema.md
DAV-technical.md
```

Chacun autonome, audience claire. Cout : triplication partielle du contenu (code, label, module repetes).

### Strategie B -- Un document avec sections

```
DAV.md
  ## Vue metier (business)
  ## Schema d'integration (schema)
  ## Reference technique (technical)
```

Une seule navigation, un seul fichier a versionner. Lecteur choisit sa section. Cout : fichier long.

### Strategie C -- Un document, rendu parametrable

```
render_markdown.py --layer business|schema|technical|all
```

Le renderer filtre au rendu. Le YAML source est unique. Recommande pour le pilote.

Le script `render_markdown.py` implemente la strategie C. `--layer all` = document long, `--layer business` = document court, etc.

## Transitions entre couches

Un lecteur peut vouloir "monter" (de technical vers business) ou "descendre" (de business vers technical). Le rendu doit faciliter :
- Liens ancres vers la meme entite dans une autre couche : `[voir technique](#cli-technical)`
- Glossaire en bas de page pour les termes techniques apparaissant en couche `schema`
- Table des matieres qui liste les entites triees par nom metier (couche business) avec code technique entre parentheses

Exemple : `## Client (CLI)` en couche business, `## CLI` en couche technical.
