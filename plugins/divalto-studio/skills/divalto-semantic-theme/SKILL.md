---
name: divalto-semantic-theme
description: "Choisit les couleurs d'un Label, Button ou Card par la palette sémantique du thème (attribut `semantic`) plutôt que `textColor`/`backgroundColor`/`borderColor`, que le player ignore alors. Couvre aussi la typographie (`textRole`, `bold`) et les tokens de thème (`color-primary.primary`) pour une propriété seule : colonne de grille, série de graphe, séparateur, POI."
argument-hint: "Décrivez le contrôle et l'effet voulu (ex : un bouton de suppression en rouge d'alerte, un libellé d'avertissement discret, un titre de bloc plus affirmé...)"
capabilities: [mobile, mobile-v7]
---

# Palette sémantique

Sur un projet en thème sémantique, **Label**, **Button**, **Card** et les six contrôles de saisie —
**TextBox**, **TextBoxMultiline**, **CheckBox**, **ComboBox**, **DateTimePicker**,
**NumericUpDown** — ne peignent plus les couleurs de leur configuration. Le player résout leurs
couleurs depuis les tokens du thème.

La famille de couleurs s'écrit sur trois d'entre eux — **Label**, **Button**, **Card** — par
l'attribut `semantic` du bloc `common` du fichier de contrôle. Les six saisies sont peintes par la
palette dans son rendu neutre : il n'y a rien à écrire pour les colorer.

Écrire `textColor`, `backgroundColor` ou `borderColor` sur ces contrôles n'a aucun effet — aucun
réglage ne les rattrape : s'en tenir à la palette, ne jamais écrire les deux « au cas où ». Le
**Card** est un cas à part : il n'a plus aucun attribut couleur, son ancien `background` a été
retiré.

## `semantic` — la famille de couleurs

| Valeur | Usage |
|---|---|
| `default` | pas de famille : rendu neutre du contrôle. Équivaut exactement à ne pas écrire l'attribut |
| `base` | famille neutre : une surface opaque de la couleur de la page, texte adouci |
| `primary` | action principale, mise en avant |
| `secondary` | action secondaire |
| `tertiary` | accent discret |
| `error` | erreur, suppression, danger |
| `warning` | avertissement |
| `success` | confirmation, état valide |
| `info` | information neutre |

Valeurs en minuscules, **par nom uniquement** : `semantic="3"` est rejeté par le player.

`default` rend le contrôle neutre : fond transparent, texte `color.on-app-surface`, bordure fine —
et pour un **Card** sans famille, le fond `color.surface-alt`. C'est le bon choix quand le contrôle
ne doit pas se distinguer.

`default` et `base` ne diffèrent que là où le contrôle ne repose pas directement sur la page : dans
un Card ou sur le socle gris, `default` laisse la surface transparaître, `base` peint par-dessus.
**Sur un Button les deux sont identiques**, un bouton sans famille rendant déjà `base`.

Seules les sept familles `primary` … `info` sont re-seedables par le thème du projet — c'est par
elles que la couleur de marque d'un client arrive. `base` suit la surface et n'est pas re-seedable.

`light`, `dark` et `inverse` existent comme tokens mais **ne sont pas des familles** : ce sont des
pôles de contraste qui s'inversent avec l'apparence (`dark` rend noir en clair et blanc en sombre).
Le player n'a pas de valeur pour eux et retombe sur `default`. Ne pas les écrire.

## Ce que la famille peint sur chaque contrôle

Le thème décide *comment* la famille est appliquée ; ce n'est pas un choix de configuration.

- **Button** : fond plein de la famille, texte contrasté
- **Label** : texte de la famille, ni fond ni bordure — `semantic="error"` veut dire un texte rouge,
  pas un bloc rouge
- **Card** : fond atténué de la famille sous des enfants qui portent leurs propres couleurs ; sa
  bordure vient toujours du rôle outline de la famille

## `textRole` et `bold` — la typographie d'un Label

`textRole` nomme un niveau de la typographie du thème, du plus discret au plus affirmé : `caption`,
`body`, `subtitle`, `title`, `display`. Absent vaut `body`. Il remplace `fontName` / `fontSize` sur
le Label.

`bold` (booléen) met le texte en gras, dans la graisse que le rôle définit.

Les deux ne s'écrivent que sur un **Label**.

## Où l'écrire

Dans l'objet `proposal.common` du fichier de contrôle, à côté de `text` :

```json
{
  "label": "Supprimer",
  "component": "Button",
  "position": { "left": 16, "top": 220, "width": 120, "height": 40 },
  "proposal": {
    "controlType": "Button",
    "common": {
      "text": "Supprimer",
      "semantic": "error"
    }
  }
}
```

Un bouton secondaire discret :

```json
"common": { "text": "Annuler", "semantic": "base" }
```

Un libellé d'alerte, en titre de bloc :

```json
"common": { "text": "Stock insuffisant", "semantic": "warning", "textRole": "title" }
```

Un Card qui met en avant un bloc — c'est là son seul réglage de couleur :

```json
"common": { "semantic": "info" }
```

## Nommer un token dans une couleur de config

C'est l'autre moitié du thème sémantique : là où `semantic` habille un contrôle entier, une
**couleur de config** peut nommer un token pour une propriété seule. C'est ainsi qu'une
série de graphe, un séparateur, le stylo d'un ImageEditor ou un onglet de Calendar prend une couleur
du thème au lieu d'un hex figé, qui ne suivra ni la couleur de marque du client ni le passage en
sombre.

**MUST NOT** — trois endroits où un nom de token ne peint rien :

- ❌ dans une couleur du bloc `common`, sur **n'importe quel** contrôle : le thème les possède
  toutes en thème sémantique, nom de token compris. Sur un Label, un Button ou un Card, c'est
  `semantic` et rien d'autre ; les autres contrôles rendent le
  neutre du thème et n'ont aucune couleur à écrire.
- ❌ dans l'aiguille ou les libellés d'axe d'un Gauge (`indicatorColor`, `textIndicatorColor`) :
  le player ne les lit plus, ils prennent `color.on-app-surface` — noir en clair, blanc en sombre.
- ❌ dans un état : le serveur de rapports résout ses couleurs depuis la palette Divalto, un nom
  de token ne lui parvient pas.

Partout ailleurs, n'importe quelle chaîne de couleur accepte une clé de token à la place d'un hex :

```json
"proposal": {
  "controlType": "Separator",
  "config": { "orientation": "Horizontal", "color": "color-base.subtle" }
}
```

```json
"proposal": {
  "controlType": "Chart",
  "series": [{ "serieColor": "color-series-a.series-a", "textColor": "color.on-app-surface" }]
}
```

**La règle de reconnaissance est le point.** Toute clé de token en porte un, aucun nom de couleur
Divalto n'en a : `color-primary.primary` est un token, `color-green` reste la palette Divalto. Les
deux cohabitent donc dans le même attribut sans ambiguïté.

✅ `"backgroundColor": "color-primary.subtle"` — un token
✅ `"backgroundColor": "FF9C00"` — un hex, toujours valide
✅ `"backgroundColor": "color-green"` — un nom de la palette Divalto, toujours valide
❌ `"backgroundColor": "primary"` — sans point, ce n'est pas un token ; le player cherche un nom de
palette, n'en trouve pas, et laisse la couleur à son défaut **sans rien signaler**

Une clé mal orthographiée échoue de la même façon, en silence. Prendre les clés dans
[references/theme-tokens.md](references/theme-tokens.md) — les 224 clés, par famille — et n'en
inventer aucune par analogie.

## À ne pas faire

- Ne pas écrire `textColor`, `backgroundColor` ni `borderColor` pour styliser un de ces
  contrôles : en thème sémantique, le player les ignore — passer par `semantic` là où il
  s'écrit. Ils restent valides sur tous les autres contrôles. Sur un **Card**, ils n'existent tout
  simplement plus : ni couleur, ni `background`.
- Ne pas poser `semantic` ailleurs que sur Label, Button et Card, ni
  `textRole` / `bold` ailleurs que sur un Label : ils n'y peignent rien.
- Ne pas écrire `fillMode` : le remplissage appartient au thème. Une valeur déjà présente dans un
  fichier survit à un enregistrement, mais elle ne se saisit plus.
- Ne pas écrire `light`, `dark` ni `inverse` : ce ne sont pas des familles, le player retombe sur
  `default`.
- Ne pas écrire la forme ordinale (`semantic="3"`), ni une valeur hors de la liste ci-dessus : le
  player l'ignore et retombe sur `default`.
- Ne pas nommer un token dans la couleur de config d'un de ces neuf contrôles, ni dans un état :
  voir la section ci-dessus.

## À l'exécution

`CONTROL_SEMANTIC(controlName, semantic)` applique une famille depuis un script. Retourne `true` si
le contrôle a été trouvé, `false` sinon. Sa documentation couvre les neuf contrôles de la palette :
ce sont les couleurs de la *configuration* qui se sont réduites à cinq, pas le langage.

```
CONTROL_SEMANTIC("btValider", "success")
CONTROL_SEMANTIC("txMontant", "error")
```

`CONTROL_FORECOLOR` et `CONTROL_BACKCOLOR` ne peignent plus ces contrôles en thème sémantique
(jamais sur un Card) : l'appel réussit et le player loge un avertissement nommant le contrôle, sans
rien changer à l'écran. Ils restent la bonne réponse partout ailleurs.
