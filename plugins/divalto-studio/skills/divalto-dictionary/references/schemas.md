# Énumérations et schémas — dictionnaire Divalto

Schémas autoritaires : `resources/dictionary/schemas/*.schema.json`. Tout schéma a `additionalProperties: false` — une clé inconnue échoue à la validation.

## `ColumnType` (entity columns + view columns)

```
Unknown | Bool | Int | Double | Varchar | Text | Timestamp | Blob | BigInt
ForeignKey | PrimaryKey | MediumText | MediumBlob | DateTime | Char | NVarchar | SmallInt
```

- `ForeignKey` → la colonne **doit** avoir `foreignEntity: "<code>"` (code de l'entité cible, pas son `schemaTable`).
- `PrimaryKey` → habituellement implicite et géré par le serveur ; ne pas l'ajouter manuellement sauf cas connu (tables sans Id auto).
- `Varchar` / `Char` / `NVarchar` → fournir `length` (entier ≥ 1) ou laisser absent (= défaut serveur).

## `IndexTarget`

```
Disabled | Server | Mobile | Both
```

- `Server` — index posé seulement sur la base serveur.
- `Mobile` — index posé sur la réplication mobile (Mongo). Requiert que les colonnes ciblées soient `mobile.available: true`.
- `Both` — server + mobile (cas le plus courant pour les colonnes utilisées en filtre).
- `Disabled` — déclaration conservée mais index physique non créé (utile pour désactiver temporairement sans perdre la définition).

## `SqlModeCode` (au niveau entité)

```
CaseInsensitive | CaseSensitive
```

Hérité du collation du serveur si absent. Ne pas changer sur une entité existante sans vérifier l'impact sur les comparaisons WHERE de toutes les pages qui la consomment.

## Champs « plateforme » d'une colonne

```json
"server": { "edit": bool, "visible": bool, "mask": "string | null" }
"mobile": { "available": bool, "edit": bool, "visible": bool, "mandatory": bool,
            "length": "integer | null", "mask": "string | null" }
```

- `mobile.length` permet de **réduire** la longueur côté mobile (ex. `Varchar(255)` serveur, `Varchar(64)` mobile). Si absent, mobile suit `length` racine.
- `mobile.mandatory` n'a de sens que si `mobile.available: true` et `mobile.edit: true`.
- `mask` `null` (et non absent) = « purger un masque hérité du std » sur un override spé.

## Permissions API

Entité — `api: { read, insert, update, delete }`. Tous bool, défauts serveur (typiquement `read: true`, écritures fermées) si absent.

Vue — `api: { read }`. Une vue n'a pas d'écriture exposée par la `DatabaseAPI`.

## Traductions

```json
"translations": { "fr": "Contact", "en": "Contact", "de": "..." }
```

Clés = codes langue ISO en **minuscules**. Pas de fallback automatique côté serveur : si une langue manque, le label brut (`label` ou `schemaColumn`) est utilisé.

Surcharge spé partielle : ne mettre QUE les langues qu'on veut surcharger. Les autres restent héritées du std.

## Ce qui n'est PAS dans les fichiers

| Donnée                | Où elle vit                                            |
| --------------------- | ------------------------------------------------------ |
| `code` / `name` logique | Nom du fichier ou du dossier                          |
| IDs BDD (`metaTable_ID`, `metaColumn_ID`, …) | `Dictionary/<layer>/_registry.json` (auto) |
| `overloadId`          | Implicite : le dossier de couche du fichier (`Dictionary/<layer>/`) |
| Sentinelles serveur (`"Ø"`, `int.MinValue`, etc.) | Jamais ; héritage = clé absente |
