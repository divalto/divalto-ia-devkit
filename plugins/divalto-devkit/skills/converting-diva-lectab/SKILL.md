---
name: converting-diva-lectab
description: >-
  Convertit en masse les anciennes fonctions de lecture DIVA (seek_xxx, Lectab) vers la nouvelle
  API objet metier (Give_xxx, Find_T041, Load_gtfdos) lors d'une migration Divalto. Pour chaque
  appel seek/Lectab, verifie dans l'objet metier *tmchk<entite>.dhsp du PACK STD DE DESTINATION
  que la fonction cible existe avant de convertir ; sinon laisse le code intact avec un TODO.
  A utiliser quand un integrateur Divalto demande de "migrer/convertir les fonctions de lecture",
  "passer les seek_xxx en Give_xxx", "convertir les Lectab", ou "automatiser la migration des
  acces fichiers" sur un dossier de sources. Traite les .dhsp ET les masques de surcharge
  .dhsf/.dhsi -- pour ces masques, ne transforme que le bloc [diva] (jamais [diva_base], copie
  figee du standard). Pour chaque seek_<entite>, decide s'il faut le GARDER (wrapper survivant
  dans la cible) ou le convertir, d'apres l'arbre des Objets compiles (.dhop) de la version cible.
  Autonome (ni AutoConvertSrc.exe, ni diva-MCP).
---

# Conversion des fonctions de lecture DIVA (migration)

Reproduit et depasse l'outil editeur `AutoConvertSrc.exe` : transformations regex faites maison,
mais **validees contre l'objet metier** du pack Std cible et **etendues** aux appels multi-arguments.

## Quand l'utiliser

Migration de sources DIVA `.dhsp` : remplacer les lectures ISAM historiques par l'API objet metier.

## Inputs a demander a l'integrateur (obligatoire)

1. **Dossier des sources** a convertir (`--src`, recursif). Traite par defaut `.dhsp,.dhsf,.dhsi,.dhsq` (option `--extensions`) et exclut les fichiers `*_base.*` (option `--exclude-pattern`).
2. **Dossier de sortie** (`--out`) — seuls les fichiers modifies y sont ecrits, en miroir.
3. **Chemin du PACK STD DE DESTINATION** (`--std`) de la migration.
   - C'est le pack de la version cible (ex. `C:\Developpements Harmony\Sources\v2026_erpX13_sp223c`).
   - **PAS** le dossier interne editeur `C:\...\Std` : les integrateurs n'y ont pas acces.
   - Si l'integrateur ne l'a pas, lui demander de recuperer le pack Std de la version visee.
4. **Arbre des Objets COMPILES (.dhop)** de la version cible (`--objets`, **obligatoire**).
   - Sert a la **decision 3-voies** des `seek_<entite>` (cf. « seek_ : garder ou convertir »).
   - C'est l'arbre des `.dhop` de la version cible **installee** (runtime/Objets), distinct du pack Std de sources.
   - Sans lui, la decision serait aveugle (sur-conversion) : **le script refuse de tourner** (erreur, exit 2).

## Execution

```
py .claude/skills/converting-diva-lectab/scripts/convert_lectures.py \
  --src "<dossier_sources>" --out "<dossier_sortie>" --std "<pack_std>" \
  --objets "<arbre_objets_dhop>" [--report "<chemin>"] [--dry-run]
```

Le rapport (`<out>/regExResult.txt` par defaut) liste : conversions appliquees, appels non convertis
(objet metier absent du pack), les **`seek_` gardes** (wrapper survit en cible), une synthese chiffree,
et les **`;TODO` regroupes par type** (`hooks` / `Get_Record` / `migration` / `cle` / `args`) avec
compteur. Option **`--dry-run`** : produit le rapport **sans ecrire** le miroir converti (pour estimer
un perimetre avant action).

## Regles appliquees (detail dans `reference/regles.md`)

| Source | Cible | Condition |
|---|---|---|
| `seek_soc(x)` | `Load_gtfdos(x)` | exception directe, sans verif (confirme cible X.13 : 2147 occ.) |
| `seek_<x>(args)` | **garde** OU `Give_<x>(<INSTANCE>, args)` + `;TODO hooks` | decision **3-voies** selon l'arbre Objets (cf. « seek_ : garder ou convertir ») |
| `Lectab(n\|nn, cle)` | `Give_T0nn(T0nn, cle)` | **sans** n° d'erreur : lecture simple ; forme `[a b]` -> `, a, b` |
| `Lectab(nn, cle, 11nn)` | `Find_T0nn(cle)` | **avec** n° d'erreur (3e arg = 1100+table) : `Find_` affiche l'erreur auto |
| ⮡ si `T0nn.Champ` lu en aval | `Find_T0nn(cle, allcolumns = true)` + `;TODO Get_Record` | enrichissement auto : charge l'enreg complet ; `Get_T0nn_Record()` à ajouter à la main |

Le nom exact de la fonction et le nom d'instance sont **lus dans la signature reelle** de l'objet
metier (ex. `public function int Give_ART(&ART,...)` -> `Give_ART(ART, ...)`).

> **Give_ vs Find_ : c'est le 3e argument (n° d'erreur) qui tranche.**
> - Pas de n° d'erreur -> **`Give_T0nn(T0nn, cle)`** : remplit l'instance, **pas** d'affichage d'erreur.
> - N° d'erreur `11nn` (= 1100+table) -> **`Find_T0nn(cle)`** : `Find_` reproduit l'affichage auto de
>   l'erreur (appel interne a `GT_GererErreurCheck(11nn, ...)`), comme l'ancien `Lectab`. `Find_` prend
>   **la cle** en 1er arg (pas d'instance). **Enrichissement auto** : si `T0nn.Champ` est lu ailleurs
>   dans le fichier, le moteur emet `Find_T0nn(cle, allcolumns = true)` + un `;TODO Get_Record` (le
>   `T0nn = Get_T0nn_Record()` reste a ajouter a la main : 2e instruction non inserable dans un `If`).
>
> Toutes les tables `T000..T099` exposent les deux fonctions ; `T041` n'est pas un cas special.
> `seek_tiers` n'a pas de `Give_Tiers` (choix manuel parmi `Give_CLI/FOU/PRO/VRP/TIA`).
> Preuves et signatures reelles : `reference/observations-x2-x4.md`.

> **seek_ : garder ou convertir (decision 3-voies, `--objets`).** `Seek_<entite>` peut survivre comme
> wrapper public dans le framework de la cible (acces ISAM legacy + hooks `<Ent>_Seek_Av/_Ap`). Le moteur
> tranche **par appel** a partir de l'**index des `seek_*` lus en clair dans l'arbre Objets `.dhop`** de la
> cible (`--objets`, obligatoire) :
> 1. **GARDER intact** si `seek_<entite>` est present dans l'index (le wrapper survit) — ou s'il est defini
>    localement (helper projet) ;
> 2. **CONVERTIR** vers `Give_<entite>` (+`;TODO hooks`, car `Give_` ne declenche pas les hooks) si le
>    wrapper a disparu de la cible MAIS `Give_<entite>` existe dans le pack Std ;
> 3. **`;TODO migration`** si l'entite est introuvable partout (a investiguer).
>
> Frontiere de mot stricte (`seek_c3` != `seek_c3xq`). Le rapport recense les `seek_` gardes.
> **Variante `_Key`** : `Seek_<ent>_Key(...)` cible le **meme** objet metier `<ent>` ; si `Give_<ent>_Key`
> n'existe pas mais `Give_<ent>` oui, le moteur cible `Give_<ent>` (cle multi-champs eclatee normalement).

### Declaration du module objet metier

Chaque conversion s'appuyant sur un objet metier **ajoute la directive `Module "<om>.dhop"`** en tete
du source si elle est absente (ex. `Give_ART` -> `Module "gttmchkart.dhop"`, `Find_T041` ->
`Module "gttmchkt041.dhop"`). Inseree dans le bloc `Module` existant (sinon apres le dernier
`Include`, sinon avant la 1re ligne de code). Dedoublonnee et idempotente. `seek_soc -> Load_gtfdos`
ajoute `Module "gtpmfdos.dhop"` (module framework portant Load_gtfdos).

## Garde-fous (comportement verifie)

- **Verification objet metier uniforme** : `seek` ET `Lectab` ne sont convertis que si la fonction
  cible existe dans le pack ; sinon ligne **inchangee** + commentaire `;TODO migration ...` + rapport.
- **Fonctions locales preservees** : un `seek_xxx` defini comme `function ... seek_xxx(` dans les
  sources (meme dans un autre fichier du lot) est un helper projet, **jamais converti ni flague**.
- **Casse insensible** en entree ; sortie = casse reelle de l'objet metier.
- **Ligne par ligne** : un appel etale sur plusieurs lignes (continuation `\`) n'est pas reconstitue.
- **Lignes commentees jamais transformees** : un corps commencant par `;` (commentaire DIVA) reste
  intact (la migration de reference ne touche pas aux commentaires).
- **Args surnumeraires tronques a l'arite reelle** (`trim_args`) : la cible recoit exactement le nombre
  de parametres de sa signature (give = params apres l'instance ; find = champs de cle ; `Load_gtfdos` = 1).
  Un arg qui rentre est conserve (`Give_C3(C3, cpt, 0)` reste) ; tout surplus est coupe. Si le surplus
  coupe n'est pas un simple `0`/vide, un `;TODO args` signale la valeur supprimee.
- **Encodage preserve** : ISO-8859-1 (latin-1), fins de ligne d'origine, sans BOM. Originaux intacts.
- **Ignore** : la regle `SetModuleInfo` et les dictionnaires `.dhsd`. Les masques `.dhsf`/`.dhsi` sont traites via le **filtre `[diva]`** (cf. « Surcharges masque » ci-dessous) ; les `.dhsq` sont scannes mais declaratifs (no-op).

## Surcharges masque (.dhsf / .dhsi)

Un masque de surcharge contient **deux** blocs de code DIVA :
- `[diva] … [/diva]` = code **surcharge** (le specifique du partenaire) — **modifiable** ;
- `[diva_base] … [/diva]` = **copie figee du standard** — **INTOUCHABLE** (la modifier casse le diff de surcharge).

Sur les `.dhsf`/`.dhsi`, le moteur applique un **filtre `[diva]`** (active par defaut, desactivable par `--no-diva-filter`) :
- il ne transforme que les lignes du bloc `[diva]` exact (state machine) et n'insere les directives `Module` que dans ce bloc ;
- **fail-safe** : toute structure de balises inattendue (bloc non ferme, imbrication, `[/diva]` orphelin, plus d'un bloc `[diva]`, variante `[diva_xxx]`) → fichier **laisse intact** et liste au rapport sous « Masques IGNORES par securite » (a traiter a la main) ;
- **garde-fou auto-verifie** : le rapport atteste par fichier que les conversions sont confinees au `[diva]` (« 0 dans `[diva_base]` »).

> N'utilisez **jamais** `--no-diva-filter` sur de vraies surcharges : le moteur convertirait aussi `[diva_base]`, corrompant silencieusement la copie du standard.

## Apres conversion

Relire le rapport avec l'integrateur, traiter manuellement les `;TODO` (lectures sans objet metier
dans le pack), puis compiler/lint les sources converties (voir skill `compiling-diva-projects`).
