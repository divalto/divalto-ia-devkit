# Mécanique de surcharge — résolution de chemin et formes

## Périmètre d'édition

Un projet Divalto travaille dans un **périmètre d'édition actif** :

- `spe` (défaut, quasi tous les intégrateurs) — on édite la surcharge projet ; le standard est en lecture seule.
- `std` (devs framework, si `CanModifyStandard`) — on édite le standard.

La surcharge s'écrit **dans le périmètre actif**. Un fichier hors du périmètre actif est en lecture seule → ne pas l'écrire. **La surcharge n'est pas intrinsèquement « spé »** : la même mécanique de duplication existe **en standard** — un écran de `Common/` peut être surchargé pour un `DeviceType` donné (la résolution prend en compte le DeviceType). C'est l'autorisation du **chemin cible** qui décide, pas une règle « jamais le standard ».

## Résolution de chemin : surcharger = même chemin relatif

Une surcharge partage le **même chemin relatif** que le fichier surchargé, à un niveau de spécificité supérieur (DeviceType plus précis, ou périmètre spé). La racine est résolue par le périmètre actif : **on ne préfixe pas le chemin par un dossier `Spé`/`Std`**.

```
Surchargé (lecture seule) :  <racine>/DeviceTypes/Default/.../customerContact.id.component.json
Surcharge (écrite, actif) :  <racine-active>/DeviceTypes/Default/.../customerContact.id.component.json
                                       └──────── même chemin relatif + même extension ────────┘
```

Deux axes de surcharge :
- **périmètre** : `spe` surcharge `std` (cas intégrateur) ;
- **DeviceType** : `DeviceTypes/<X>/…` surcharge `Common/…` pour le device `<X>` (cas valable même en standard).

- ❌ Écrire `Spé/DeviceTypes/.../…` (segment `Spé`/`Std` en dur).
- ❌ Écrire un chemin **read-only pour le périmètre actif** (vérifier l'autorisation du chemin cible).
- ❌ Renommer `.component.json` ↔ `.page.json` (cf. CLAUDE.md racine du contexte IA, section *File Naming & Uniqueness* — même namespace, jamais renommer).
- ✅ Écrire au même chemin relatif **et même extension** que le fichier surchargé, dans le périmètre actif.

> Ici : on surcharge le fichier tel qu'il existe, et on valide avec le type correspondant — `validate_divalto_file({ type: "component" })` pour un `.component.json`, `{ type: "page" }` pour un `.page.json`.

## Réécriture intégrale

> **Il n'existe à ce jour aucun mécanisme de patch partiel.** Un fichier de surcharge **remplace** entièrement son homologue standard à l'exécution.

Donc : pour modifier une page surchargée, on **lit son contenu intégral**, on applique la modification (ajout d'un champ, d'une colonne…), et on **écrit le fichier complet** dans le périmètre actif. Ne jamais produire un « fragment » censé fusionner avec le fichier d'origine.

## Scriptlibrary {#scriptlibrary}

Le code-behind d'une page suit le nom de la page (`<page>.scriptlibrary.ts`). Deux cas distincts, **à ne pas confondre** :

> **Nommage de la classe : délégué à [`divalto-scriptlibrary`](../../divalto-scriptlibrary/SKILL.md#conventions-de-nommage-des-fichiers) — ne pas le redéfinir ici.** Ce document ne couvre que le choix entre héritage (Cas A) et code neuf (Cas B).

### Cas A — surcharger un scriptlibrary standard existant : `extends Standard`

> **MUST — surcharger un `.scriptlibrary.ts` standard = sous-classer, PAS dupliquer.** Si le fichier surchargé existe déjà en standard, la surcharge **hérite** de la classe standard via `extends Standard` et ne (re)définit **que** les méthodes ajoutées ou redéfinies. Ne **jamais** recopier le corps du scriptlibrary standard dans la spé — c'est la seule exception à la règle de réécriture intégrale, qui vaut pour tous les autres fichiers de surcharge (JSON de page, JSON de datasource, `.sql` : copie complète puis modification). C'est exactement le stub que l'outil `specialize_file` génère (la commande Spécialiser de l'extension) :

```ts
import Standard from 'Standard/<DeviceType>/<nomFichier>';

export default class <NomClasse> extends Standard {
  // ajouter / redéfinir uniquement les méthodes voulues
  async <NomClasse>_afterChildrenLoad(): Promise<void> {
    await super.<NomClasse>_afterChildrenLoad?.();
    const score = await (this.constructor as typeof <NomClasse>).computeEngagementScore();
    $component.tryGetById('script_engagementScore')?.setValue(score);
  }
}
```

- `import Standard from 'Standard/<DeviceType>/<nomFichier>'` (alias `Standard`, `<nomFichier>` sans l'extension `.scriptlibrary.ts`, `<DeviceType>` du fichier surchargé).
- `export default class <NomClasse> extends Standard` — `<NomClasse>` = nom généré par `specialize_file`, ne pas le renommer.
- Pour étendre un handler existant sans le perdre, appeler `super` puis ajouter le calcul ; pour en ajouter un nouveau, le déclarer simplement.
- Le code standard hérité **reste actif** : rien à recopier.

### Cas B — nouveau code-behind (page fraîchement spécialisée, sans logique standard)

Quand il n'y a **pas** de scriptlibrary standard à hériter (code-behind vide ou page nouvelle), écrire la classe directement :

```ts
export default class <NomClasse> {
  async <NomClasse>_afterChildrenLoad(): Promise<void> {
    const score = await <NomClasse>.computeEngagementScore();
    $component.tryGetById('script_engagementScore')?.setValue(score);
  }

  private static async computeEngagementScore(): Promise<number> {
    // appeler un service découvert via list_typescript_services / get_typescript_methods
    // (ex. $datasource pour agréger les interactions des 90 derniers jours), puis clamp 0-100
    return 0;
  }
}
```

> `<NomClasse>` suit la convention de [`divalto-scriptlibrary`](../../divalto-scriptlibrary/SKILL.md#conventions-de-nommage-des-fichiers).

### Règles communes

- Nommage de la classe : voir [`divalto-scriptlibrary`](../../divalto-scriptlibrary/SKILL.md#conventions-de-nommage-des-fichiers) — propriétaire de la règle.
- Handler **asynchrone** bindé sur un event **au niveau `page`** (`AfterChildrenLoad`) — jamais sur un composant enfant (cf. gate `divalto-page-ui`).
- N'utiliser que des services `$xxx` retournés par `list_typescript_services()` — ne rien inventer.
