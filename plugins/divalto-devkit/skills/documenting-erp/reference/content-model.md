# Modele de contenu -- documenting-erp

Ce document detaille les 6 types documentaires du skill et leurs schemas.

## Contenu

- Vue d'ensemble des 6 types
- Schema module
- Schema entity (le plus riche, porte les 3 couches)
- Schema relation
- Schema process
- Schema program
- Schema glossary
- Regles transverses

## Vue d'ensemble

| Type     | Granularite           | Cardinalite cible | Qui le cree ?                  |
|----------|-----------------------|-------------------|--------------------------------|
| module   | 1 par module ERP      | 15 au total       | Une fois, maintenu annuellement|
| entity   | 1 par entite metier   | ~30-50 par module | Extraction auto + narratif     |
| relation | 1 par lien non trivial| ~2-5 par entite   | Extraction auto + review       |
| process  | 1 par processus cle   | ~5-10 par module  | Redige manuellement            |
| program  | 1 par ecran/zoom cle  | ~10-30 par module | Extraction auto + label        |
| glossary | 1 par terme metier    | ~50 par module    | Redige + verifie               |

## Schema module (schemas/module.yaml)

Identite + regroupement. Un module declare ses bases (ex: `GTFDOS`, `CCFJCA`) et les entites qu'il porte. Les dependances `depends_on:` et `integrates_with:` tracent la carte inter-modules.

Champs requis : `code`, `label`, `prefix` (GTF/CCF/...), `status`.
Champs importants : `bases`, `entities`, `depends_on`, `business_context`.

## Schema entity (schemas/entity.yaml)

Unite documentaire principale : **1 entite = 1 page**. Structure a 3 sections correspondant aux 3 couches de lecture :

```yaml
kind: entity
code: CLI
label: Client
module: DAV
base: GTFPCF
status: stable

business:      # couche Metier
  role: ...
  criticality: core | standard | peripheral
  variants: [...]
  processes: [...]
  typical_users: [...]
  business_rules: [...]
  examples: [...]

schema:        # couche Schema
  primary_table: CLI
  primary_key: [DOS, TIERS]
  satellite_tables: [ETBCLI, TIERSGRP]
  relations: [...]
  integration_points: [...]
  diagram_mermaid: |
    graph LR ...

technical:     # couche Technique
  dictionary_source: GTFDD.dhsd
  record_name: Client
  field_count: 241
  fields: [...]
  indexes: [...]
  audit_fields: [...]
  zoom_code: "09021"
  main_screens: [...]
  main_programs: [...]
  moulinettes: [...]
  performance_notes: ...

meta:
  last_reviewed: 2026-04-21
  reviewed_by: scastelain
  a_verifier: [...]
```

### Sous-schema `field` (entry dans technical.fields)

```yaml
- name: TIERS
  nature: C20          # Nature DIVA (reference aux regles D-xx du dictionnaire)
  sql_type: char(20)
  label: "Code client"
  nullable: false
  zoom: SOC            # optionnel : entite/table cible du zoom f8
  business_note: ...   # optionnel : explication metier
  layer: all           # ou schema+technical ou technical-only
```

Le `layer` controle la visibilite : un champ en `technical-only` n'apparait pas dans le rendu `schema`.

### Sous-schema `index` (entry dans technical.indexes)

```yaml
- name: IDX_CLI_PK
  fields: [DOS, TIERS]
  unique: true
  purpose: "Cle primaire metier"
```

## Schema relation (schemas/relation.yaml)

Lien entre 2 entites. Peut etre en-ligne (dans `entity.schema.relations`) ou fichier separe si la relation est riche (M:N avec attributs).

Champs cles : `source_entity`, `target_entity`, `type` (fk | zoom | composition | inheritance | association), `cardinality` (1-1 | 1-N | N-1 | N-N).

## Schema process (schemas/process.yaml)

Processus metier transverse. Permet de restituer la couche "metier" inter-entites (ex: cycle commande-livraison-facturation qui traverse CLI, BDOCL, LDOCL, MOUV, C8).

Champs cles : `code`, `label`, `trigger`, `outcome`, `entities` (ordre d'apparition), `steps` (label + actor + entity).

## Schema program (schemas/program.yaml)

Documente un programme executable : ecran CRUD .dhsf, zoom .dhsp, etat, moulinette, batch.

Champs cles : `code`, `kind` (screen-crud | zoom | report | state | moulinette | batch), `entities_read`, `entities_write`.

## Schema glossary (schemas/glossary.yaml)

Table de correspondance terme metier <-> code technique. Permet aux couches "metier" de pointer vers un code sans l'introduire a chaque mention.

Champs cles : `term`, `technical_code`, `definition`, `synonyms`.

## Regles transverses

### Statut

Chaque instance a un `status:` parmi `draft | stable | deprecated`. Les renderers peuvent filtrer ou marquer visuellement.

### Items [A VERIFIER]

Tout contenu non source ou a verifier est liste dans `meta.a_verifier:` (entity, module, ...) ou `a_verifier:` (autres types). Convention identique a la doc historique du workspace.

### Renvoi inter-types

Les references entre types utilisent le `code` :
- Une entity pointe vers des processes par `business.processes: [ORDER-TO-CASH, ...]`
- Un process pointe vers des entities par `entities: [CLI, BDOCL, ...]`
- Une relation pointe vers des entities par `source_entity` / `target_entity`

### Rendering layers

Chaque schema declare `rendering_layers:` qui route les champs top-level vers les 3 couches. Les renderers consomment cette table pour decider quoi afficher. Regles de routage dans [layering.md](layering.md).
