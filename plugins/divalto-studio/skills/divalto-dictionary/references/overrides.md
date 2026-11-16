# Surcharger un champ du standard (spé)

Un fichier spé est **sparse** : il ne contient que les clés qui doivent réellement diverger du standard. Le serveur fusionne les couches de la chaîne (`std` → … → couche active) au runtime ; toute clé absente d'une couche est héritée de la couche précédente. Chaque couche vit dans son propre dossier `Dictionary/<layer>/`.

## Cas typiques

### Changer un libellé

```
// Dictionary/std/entities/customer/columns/Name.metacolumn.json
{ "schemaColumn": "name", "type": "Varchar", "length": 255, "translations": { "fr": "Nom" } }

// Dictionary/<layerSpé>/entities/customer/columns/Name.metacolumn.json
{ "translations": { "fr": "Raison sociale" } }
```

Seule la traduction FR est surchargée. EN reste héritée du std si elle existait là-bas.

### Allonger une colonne

```
// std : length 64
// spé :
{ "length": 128 }
```

### Désactiver côté mobile une colonne disponible en std

```
{ "mobile": { "available": false } }
```

Note : un sous-objet (`server`, `mobile`) surchargé en spé **remplace** ce que le std contient pour les clés présentes, mais ne touche pas aux clés absentes. Ici, seul `mobile.available` est forcé à `false`, le reste de `mobile` reste hérité.

### Repasser à `null` une valeur héritée

Pour effacer un masque hérité du std :

```
{ "server": { "mask": null } }
```

`null` (explicite) ≠ clé absente. La clé absente = « hérité » ; `null` = « override à null ».

## Surcharger une entité, pas seulement ses colonnes

Mêmes règles. Le fichier `metatable.json` côté spé peut ne contenir qu'une traduction surchargée :

```
// Dictionary/<layerSpé>/entities/customer/metatable.json
{ "translations": { "fr": "Société" } }
```

Pas de `schemaTable`, pas de `sqlModeCode` — hérités.

## Ajouter une colonne spé qui n'existe pas en std

Le fichier vit uniquement côté spé. C'est une **vraie création** (pas un override) : le fichier doit être **complet** ET son code doit porter le **préfixe d'overload** `<codeOverload>_` (cf. `SKILL.md` § « Préfixe d'overload »).

```
// Dictionary/<layerSpé>/entities/final_devis/columns/final_montant.metacolumn.json
{
  "schemaColumn": "montant",
  "type": "Double",
  "server": { "edit": true, "visible": true }
}
```

Aucun équivalent côté std → vraie création, donc préfixe obligatoire (ici overload `final`). Le fichier décrit toute la colonne.

> ⚠️ On n'ajoute **pas** une colonne dico spé à une entité **standard** (`customer`, `contact`…) : il n'existe pas de mécanisme « colonne custom » sur le standard (cf. le contexte permanent Divalto Studio). Un nouveau champ se crée sur une **table spé** (elle-même préfixée, ex. `final_devis`), ou via un overlay projet (`.fielddefinition.json`).

## Pièges

- **Ré-écrire le std intégralement en spé** : la sparsité disparaît, le push voit toutes les clés comme « surchargées spé » et le pull arrière (sync std → spé) devient indéfini sur ces clés. Toujours diff-er avant d'écrire : ne mettre que les clés qui changent réellement.
- **Surcharge avec une valeur identique au std** : sans effet visible mais marque la clé comme « overridée en spé » dans la BDD. Inutile et bruyant — supprimer la clé du fichier spé.
- **Override d'un sous-objet en ré-écrivant tout le sous-objet** : `"server": { "edit": false, "visible": true, "mask": null }` écrase les 3 clés en spé même si on ne voulait surcharger que `edit`. Mettre uniquement `"server": { "edit": false }`.
- **Code de fichier différent entre std et spé** : interdit. Le code (nom de fichier / dossier) doit être **strictement identique** entre les deux couches pour qu'elles s'associent. `name.metacolumn.json` en std ↔ `name.metacolumn.json` en spé. Pas `Name.metacolumn.json` d'un côté et `name.metacolumn.json` de l'autre.

## Et si la cible « naturelle » est le standard ?

Si l'utilisateur demande quelque chose qui ressemble à une modif du standard alors qu'on est en périmètre spé, **ne pas écrire dans le std**. Deux options :

1. **Proposer la surcharge spé équivalente** (souvent suffisante) et l'appliquer.
2. **Demander de basculer en périmètre std** (`divalto.toggleEditingPerimeter`) si la modif est vraiment cadrée standard (cas des développeurs R&D Divalto, capability `CanModifyStandard` requise).

Ne jamais contourner le verrou logique read-only via Bash ou un Write sur un chemin std en périmètre spé.
