---
name: divalto-report-creation
description: "Crée ou modifie un report mobile Divalto Weavy (état imprimable en sections), au format `reports/{code}.report.xml` + `{code}.json`. Utiliser pour : créer un report, ajouter une section, placer des éléments (Texte, Image, Forme, Ligne, BarCode, Chart), lier des champs SQL, régler marges et format de page."
argument-hint: "Décrivez le report (ex: bon de commande client avec en-tête société, lignes de commande, totaux et pied de page)..."
capabilities: [mobile]
---

# Création d'un report mobile (état imprimable en sections)

## Quand utiliser ce skill

- Créer un nouveau report (document imprimable/exportable structuré en sections)
- Ajouter ou supprimer une section (`ReportHeader`, `PageHeader`, `Detail`, `GroupHeader`/`GroupFooter`, `TotalHeader`/`TotalFooter`, `PageFooter`, `ReportFooter`)
- Placer ou modifier des éléments dans une section : `Texte`, `Image`, `Forme`, `Ligne`, `Check`, `BarCode`, `Chart`
- Lier un élément à une colonne SQL, ou écrire/modifier la requête (`requete`) d'une section
- Régler les marges, le format de page, la police globale, ou les propriétés base de données du report (`{code}.json`)

---

## Emplacement et nommage du fichier

Les reports vivent dans :

```
Mobile/
  reports/
    order.report.xml     ← mise en page (sections, éléments, XML <Etat>)
    order.json            ← propriétés base (label, type, defaut, archivage...)
```

**Convention de nommage :** le nom de fichier (sans extension) **est** le code du report, en minuscules. Il n'y a **pas** de champ `code` ni `_id` dans l'un ou l'autre fichier — le code est inféré du nom de fichier.

> **Surcharge active :** si une surcharge non-racine est active (`_project.json`), le code doit porter son préfixe (ex. `final_order`, pas `finalorder`). Règle complète : [divalto-mobile-screen-creation](../divalto-mobile-screen-creation/SKILL.md), section « Surcharges (overloads) ».

---

## Deux fichiers

- **`{code}.report.xml`** — la mise en page : racine `<Etat>`, marges, format de page, sections (`<Section>`) et leurs éléments (`<Element>`). C'est le fichier que `validate_report_xml` vérifie.
- **`{code}.json`** — les propriétés base de données du report (`label`, `reportType`, `isDefault`, `exportValue`, `externalDocCode`, `stub`, `archiveMode`, `archiveVersionsNumber`, `translationKey`). Forme exacte : catégorie `dbProps` de `get_report_element_reference`, ou [references/elements.md](references/elements.md) § `{code}.json`.

Les deux fichiers sont indépendants : le XML peut être édité sans toucher au JSON et inversement, mais un report neuf a besoin des deux.

---

## Workflow obligatoire

1. **`get_report_element_reference`** — charger le schéma complet (types d'éléments, types de sections, tokens, formats, attrs `<Etat>`, forme du `{code}.json`) avant de composer quoi que ce soit.
2. **`get_entities`** / **`get_entity_properties`** — identifier la ou les tables et colonnes utilisées par chaque section, pour écrire la requête SQL de sa `requete`.
3. **Écrire le SELECT de chaque section** — la base mobile est **MariaDB** : syntaxe MariaDB/MySQL obligatoire (`CONCAT`, `IFNULL`, pas de `||`...). Détails complets : [divalto-mobile-screen-creation](../divalto-mobile-screen-creation/SKILL.md), section « Base de données : MariaDB ». La clause `WHERE ... = '%row_ID%'` lie la section à l'enregistrement imprimé.
4. **Composer le XML** — `<Etat>` racine, une `<Section>` par section, des `<Element>` à l'intérieur, en respectant les pièges ci-dessous.
5. **`validate_report_xml`** — valider le XML, corriger, **répéter jusqu'à `valid: true`** (aucune erreur de sévérité `error`). Les avertissements (`warning`, ex. `<Champ>` absent des alias du SELECT) doivent être examinés mais n'empêchent pas d'écrire le fichier.
6. **Écrire les deux fichiers** (`{code}.report.xml` et `{code}.json`) sur le disque.
7. L'utilisateur review les changements dans le panel Source Control (SCM).
8. L'utilisateur clique « Sync to Server » quand il est satisfait — les modifications ne sont **jamais** envoyées automatiquement.

---

## Squelette minimal

`Mobile/reports/{code}.report.xml` :

```xml
<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<Etat table="sw_data_orderheader" margeLeft="20.00" margeTop="20.00" margeRight="20.00" margeBottom="20.00" format="A4">
  <Grille grilleLargeur="5" grilleHauteur="5" />
  <GlobalFont fontFamily="Tahoma" size="8.25" />
  <Section name="Section0" type="Detail" height="60.00" visible="true" requete="SELECT oh.orderDate AS 'oh.orderDate' FROM sw_data_orderheader AS oh WHERE oh.orderheader_ID = '%row_ID%'">
    <Element name="Texte1" left="0.00" top="0.00" width="200.00" height="12.01" type="Texte">
      <Champ>oh.orderDate</Champ>
      <ContentAlignment>MiddleLeft</ContentAlignment>
      <FormatDate>d</FormatDate>
    </Element>
  </Section>
</Etat>
```

`Mobile/reports/{code}.json` (miroir de la catégorie `dbProps` de `get_report_element_reference`) :

```json
{
  "label": "Mon report",
  "reportType": null,
  "isDefault": false,
  "exportValue": null,
  "externalDocCode": null,
  "stub": null,
  "archiveMode": null,
  "archiveVersionsNumber": null,
  "translationKey": null
}
```

> Pour renseigner `translationKey` — créer ou réutiliser une **clé de traduction** au lieu de laisser `null` ou un libellé en dur — déléguer au skill [divalto-translations](../divalto-translations/SKILL.md).

---

## Pièges fréquents

- **Unités en points, pas en pixels.** `left`/`top`/`width`/`height` sur `<Etat>` (marges) et `<Element>` (géométrie) sont exprimés en points.
- **Couleurs ARGB en entier signé.** `FillingColor`, `PenColor`, `ForeColor`, `BackColor`, etc. sont des entiers 32 bits **signés** (ex. `<FillingColor>-4144960</FillingColor>`), jamais une chaîne hexadécimale ni un entier non signé.
- **Les propriétés vivent en enfants texte, pas en attributs.** `<Champ>`, `<Texte>`, `<ContentAlignment>`, `<FormatDate>`... sont des éléments enfants avec du texte, pas des attributs de `<Element>`. Seuls `left/top/width/height/name/type` sur `<Element>`, et `fontFamily/size` sur `<Font>`, sont des attributs.
- **`%row_ID%` lie la section à l'enregistrement courant.** Présent dans la clause `WHERE` de la `requete` d'une section, il est substitué à l'exécution par l'identifiant de l'enregistrement imprimé.
- **Tokens vs colonnes réelles.** `<lng>KEY</lng>` (traduction) et `<msk>EXPR</msk>` (masque/expression), utilisés à l'intérieur d'un `<Texte>` statique, ne sont **pas** des colonnes SQL. Un alias `'lng:groupe:colonne'` dans le SELECT lie lui une traduction à une colonne de données — le `<Champ>` référence alors cet alias complet.
- **Normaliser les retours à la ligne en entités hexadécimales.** Dans un attribut XML (ex. `requete`), un CRLF doit être encodé `&#xD;&#xA;` (forme **hexadécimale**) — la forme décimale (`&#13;&#10;`) n'est **pas** reconnue par le parseur du designer et casse la correspondance `<Champ>` ↔ alias SELECT.
- **Jamais de champ `code` ou `_id`.** Ni dans le XML ni dans le `{code}.json` — le code est toujours inféré du nom de fichier.

---

## Renvois

- [references/elements.md](references/elements.md) — prose détaillée sur chaque type d'élément, chaque type de section, les tokens et les formats.
- [references/example-order.md](references/example-order.md) — exemple complet et validé (bon de commande), dérivé d'un report réel.
- Pour le schéma exhaustif et toujours à jour, appeler l'outil MCP `get_report_element_reference`.
