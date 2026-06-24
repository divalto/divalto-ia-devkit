# Observations empiriques — migration standard Divalto X.2 → X.4 → X.13

Base de preuves du skill. Obtenue par analyse différentielle des **sources standard** livrées
(`Std\Version X.2` vs `Std\Version X.4`) : 2 574 fichiers `.dhsp` présents dans les deux versions
ont été comparés ligne à ligne pour observer ce que sont **réellement devenus** les `seek_xxx` et
les `Lectab(...)` après la montée de version. Triangulé ensuite avec `Std\Version X.13` (6 877
sources), qui est la **cible réelle** des migrations actuelles (pack `v2026_erpX13`). Les règles du
skill (`reference/regles.md`, `scripts/convert_lectures.py`) sont alignées sur ces constats — pas sur
la seule `autoConvertSrc.json`. Voir la **§9 Triangulation X.13** pour les corrections de cap.

## Chiffres clés (périmètre = fichiers communs aux 2 versions)

| Mesure | X.2 | X.4 (restant) | Lecture |
|---|---|---|---|
| Appels `seek_xxx` | 9 942 | 9 002 | la majorité **subsiste** : ce sont surtout des fonctions locales |
| Appels `Lectab(...)` | 915 | 185 | ~80 % **convertis** : c'est là qu'est le vrai signal de migration |
| `Load_gtfdos` | 0 | 0 | absent X.2→X.4, mais **2 147 en X.13** : adopté plus tard (voir §5 + §9) |
| `Give_xxx` | — | 2 370 | API cible dominante |
| `Find_T0nn` | — | 214 | API cible minoritaire (cas « enreg complet ») |

## 1. `seek_xxx` : surtout des fonctions locales, peu de vraies lectures

Les `seek_` à gros volume sont des **fonctions projet définies** (`function ... seek_xxx(`), pas des
lectures ISAM. Ils ne doivent **jamais** être convertis (garde-fou « helper local » du skill).

| `seek_` | X.2 | X.4 | Nature |
|---|---|---|---|
| `seek_soc` | 692 | 688 | fonction locale (cf §5) |
| `seek_ets` | 338 | 342 | fonction locale (volume en **hausse**) |
| `seek_dossier` | 227 | 248 | fonction locale (volume en **hausse**) |
| `seek_ent` | 208 | — | fonction locale |

Les `seek_` réellement **convertis en `Give_`** (signature lue dans l'objet métier, casse réelle) :

| `seek_` source | Cible dominante observée |
|---|---|
| `seek_cli` | `Give_Cli` (×131) |
| `seek_vrp` | `Give_VRP` (×116) |
| `seek_fou` | `Give_FOU` / `Give_Fou` (×129) |
| `seek_tia` | `Give_TIA` (×50) |
| `seek_c4` | `Give_C4` (×52) |
| `seek_pro` | `Give_Pro` (×26) |
| `seek_t2` | `Give_T2` (×13) / `seek_t1` → `Give_T1` (×7) |
| `seek_c3` | `Give_C3` |
| `seek_bpent` | `Give_BPENT_With_Feu` (variante suffixée, voir §6) |

## 2. `seek_tiers` : pas de cible unique — choix manuel parmi 5

`seek_tiers` se convertit en **l'une de cinq fonctions** selon la nature du tiers ; il n'existe
**aucun** `Give_Tiers`.

```
seek_tiers -> Give_CLI | Give_FOU | Give_PRO | Give_VRP | Give_TIA
```

Conséquence : le moteur ne trouve pas `Give_tiers` dans l'objet métier → laisse **intact + TODO**.
C'est le comportement correct : la sélection de la bonne fonction relève d'une décision métier.
Même schéma pour `seek_pcfidx`.

## 3. `Lectab(nn, ...)` → `Give_T0nn(T0nn, ...)` (cas dominant)

- Le numéro de table peut être sur **1 ou 2 chiffres** : `Lectab(6, ...)`, `Lectab(1, ...)` existent
  autant que `Lectab(17, ...)`. → normalisation sur 2 chiffres (`6` → `T006`).
- Forme bracket `[a b]` et concaténation `&` → **arguments séparés** (voir §7).
- Exemples nets :
  - `Lectab(44, G6.OFFAM)` → `Give_T044(T044, G6.OFFAM)`
  - `Lectab(6, ART.ProdNat)` → `Give_T006(T006, ART.ProdNat)`
  - `Lectab(41, GMSTiers.TEXCOD)` → `Give_T041(T041, GMSTiers.TEXCOD)`

## 4. Give_ vs Find_ : le 3ᵉ argument (numéro d'erreur) tranche

Constat structurel : dans les objets métier (X.4 comme X.13), **toutes** les tables `T000`..`T099`
exposent **à la fois** `Give_T0nn` et `Find_T0nn` (94 / 94). `T041` n'est pas un cas spécial.

Le **3ᵉ argument** d'un `Lectab(nn, clé, errno)` est le **numéro d'erreur** affiché si non trouvé
(convention `11nn` = `1100 + numéro de table` ; `1139` pour T039). Sa présence **détermine la cible**,
parce que les deux fonctions ne gèrent pas l'erreur de la même façon — preuve dans le code de l'objet
métier (`gttmchkt039.dhsp`, X.13) :

```divalto
public function int Give_T039(&T039, ActCod)                ; ;LoadAndGet : remplit T039, AUCUNE erreur
Public function int Find_T039(&ActCod, allcolumns, context) ; clé seule
  ... default | ret = Find_T039_PK(...)                     ; -> GT_GererErreurCheck(1139, ActCod, ...)  (erreur AUTO)
```

- **Sans numéro d'erreur → `Give_T0nn(T0nn, clé)`** (remplit l'instance, pas d'affichage). Cas dominant.
- **Avec numéro d'erreur `11nn` → `Find_T0nn(clé)`** : `Find_` appelle `GT_GererErreurCheck(11nn, …)`
  sur échec → **affichage automatique de l'erreur**, comme l'ancien `Lectab`. `Find_` prend la **clé**
  en 1ᵉʳ argument (pas d'instance).

Conversion du moteur (validée contre le pack X.13) :

```
Lectab(39, ActCod)          ->  Give_T039(T039, ActCod)     ; pas d'erreur -> Give
Lectab(39, ActCod, 1139)    ->  Find_T039(ActCod)           ; erreur 1139 -> Find (affichage auto)
Lectab(40, ChampVal, 1140)  ->  Find_T040(ChampVal)
Lectab(41, x)               ->  Give_T041(T041, x)          ; pas d'erreur -> Give
```

> **Enrichissement automatique** : si un accès `T0nn.Champ` existe ailleurs dans le fichier, le moteur
> génère `Find_T0nn(clé, allcolumns = true)` (charge l'enreg complet) + un `;TODO Get_Record` rappelant
> d'ajouter `T0nn = Get_T0nn_Record()` après succès (2ᵉ instruction, non insérable de façon sûre dans
> une condition `If`). Sinon il garde la forme courte `Find_T0nn(clé)` (validation/existence).

```
Lectab(39, ActCod, 1139)   + "T039.Lib" lu en aval  ->  Find_T039(ActCod, allcolumns = true) ;TODO Get_Record: ... T039 = Get_T039_Record()
Lectab(40, ChampVal, 1140) + record non consomme    ->  Find_T040(ChampVal)
```

## 5. `seek_soc` → `Load_gtfdos` : absent X.2/X.4, **adopté en X.13**

`Load_gtfdos` n'apparaît **jamais** (0 occurrence) en X.2 ni X.4… mais **2 147 fois en X.13**. La
règle `seek_soc → Load_gtfdos` (issue de `autoConvertSrc.json`) est donc **bien réelle**, simplement
adoptée tardivement, entre X.4 et X.13. Comme la cible des migrations actuelles est X.13, la règle est
**valide et utile** : on la conserve comme exception directe du skill. Réserve : dans le standard,
beaucoup de `seek_soc` sont des **fonctions locales** (préservées par le garde-fou helper) ; n'attendez
donc pas une conversion systématique de tous les `seek_soc`.

## 6. Fonctions à variantes suffixées

L'objet métier expose souvent plusieurs accesseurs pour une même entité ; la migration en choisit un
selon l'usage. Le moteur cherche `Give_<ent>` **exact** : si seule une variante existe → TODO.

- `_Conf` : `Give_Cli_Conf`, `Give_Fou_Conf`, `Give_Art_Conf`, `Give_TIA_Conf`, `Give_PRJAP_Conf`
- `_Grref` : `Give_T033_Grref`, `Find_T023_Grref`, `Find_T005_Grref`
- `_With_Feu` : `Give_BPENT_With_Feu`
- `_NoOutput` : `Find_T085_NoOutput`, `Find_T021_NoOutput`

## 7. Éclatement des clés composites (`&` et `[ ]`)

Une clé `Lectab` composée est éclatée en arguments distincts dans l'appel objet métier :

```
Lectab(35, [ 'C' TRE.RemCod ])              -> Give_T035(T035, 'C', TRE.RemCod)        (bracket)
Lectab(62, T061.CBNGESCOD & T017.DEPO)      -> Give_T062(T062, T061.CBNGESCOD, T017.DEPO)   (&)
Lectab(55, [ G7.SalGrp MUSER.User ])        -> Give_T055(T055, G7.SalGrp, MUSER.User, G7.TypeRelation)
```

- La forme **bracket `[a b]`** est éclatée automatiquement par le moteur (sûr).
- La forme **`A & B`** (54 cas en X.2, 11 restants) est éclatée par l'éditeur, mais **risquée** à
  automatiser (le `&` peut être un opérateur dans une expression / une chaîne) → laissée telle quelle
  par le moteur ; à éclater manuellement. Le dernier exemple ajoute même un argument
  (`G7.TypeRelation`) issu de la signature réelle → toujours vérifier la signature cible.

## 8. `Lectab(<constante>, ...)` : 1ᵉʳ argument symbolique

Le 1ᵉʳ argument peut être une **constante de table** plutôt qu'un numéro :
`C_TABLE_SREF`, `C_TABLE_PAYS`, `C_TABLE_DEPOT`, `C_TABLE_NATURE_STOCK`, `CeBin`, `CeCout`, `CeCP`,
`Valnum`… Le moteur ne touche que les numéros (1–2 chiffres) → ces formes restent intactes
(certaines, comme `cebin`/`CeCout`, subsistent telles quelles en X.4 ; d'autres ont été résolues
manuellement vers le `Give_T0nn` correspondant à la valeur de la constante).

## 9. Triangulation X.13 (cible réelle des migrations)

Inventaire global par version (tous fichiers, pas seulement les communs) :

| Mesure | X.2 | X.4 | X.13 |
|---|---|---|---|
| Sources `.dhsp` | 3 957 | 3 786 | 6 877 |
| Appels `Lectab(...)` | 1 249 | 201 | 276 |
| `Give_xxx` | 0 | 3 138 | 7 085 |
| `Find_xxx` | 59 | 3 807 | 8 962 |
| `Load_gtfdos` | 0 | 0 | **2 147** |
| `allcolumns = true` | — | 1 570 | **5 642** |
| `Get_*_Record()` | — | 497 | **1 423** |

Ce que la cible X.13 **confirme** et **corrige** :

1. **`Load_gtfdos` est bien la cible de `seek_soc`** — absent X.2/X.4, massif en X.13 (cf. §5). La
   règle du skill est validée pour la cible réelle.
2. **`Give_T0nn` + `Find_T0nn` pour les 94 tables : surface identique X.4 et X.13.** Les règles
   T0nn se transposent directement vers X.13 sans adaptation.
3. **`Lectab` avec numéro d'erreur → `Find_T0nn`**, confirmé sur la cible, même fichier d'une version
   à l'autre. Ici `allcolumns = true` a été ajouté car le code consommait aussi l'enregistrement :
   - `divaltouserdrt_sql.dhsp` : `Lectab(17, Utilisateur.Depo, 1117)` (X.2) → `Find_T017(Utilisateur.Depo, allcolumns = true)` (X.13).
   - `grpz003.dhsp` : `Lectab(41, GRTEVT.TEXCOD, 1141)` (X.2) → `Find_T041(GRTEVT.TEXCOD, allcolumns = true)` (X.13).
   La forme `allcolumns = true` + `Get_*_Record()` progresse en X.13 (`allcolumns=true` ×5 642,
   `Get_*_Record()` ×1 423) : c'est l'enrichissement « record complet », ajouté manuellement.
4. **Sans numéro d'erreur, le défaut reste `Give_T0nn`** ; le moteur génère `Find_T0nn(clé)` (forme
   courte) dès qu'un numéro d'erreur `11nn` est présent, et laisse l'éventuel `allcolumns=true` +
   `Get_*_Record()` en enrichissement manuel.
5. **Variante `Load_T0nn(clé, allcolumns = true)`** : 3ᵉ forme d'accès (≈ une dizaine d'occurrences,
   ex. `Load_T073`) — minoritaire, à traiter manuellement.

## 10. `seek_xxx` en X.13 : wrappers de compatibilité préservés

Constat majeur, spécifique aux **entités** (≠ tables T0nn) : en X.13, la famille `Seek_<entité>`
**survit** comme **fonctions publiques** du module framework `gtpmfic.dhsp` — des dizaines :
`Seek_ART`, `Seek_SART`, `Seek_Ent`, `Seek_Mouv`, `Seek_MVTL`, `Seek_TVA`, `Seek_PRJAP`, `Seek_BNPAR`…
(+ leurs variantes `Seek_<entité>_Key`).

```divalto
public function int Seek_ART (ref, artind)        ; gtpmfic.dhsp (X.13)
  ...
  Xmt_Call("ART_Seek_Av")                          ; hook AVANT
  if G3_File_Seek(GTFAT, ART) <> 0 | freturn(2) | endif   ; acces ISAM legacy
  Xmt_Call("ART_Seek_Ap")                          ; hook APRES
  freturn(0)
```

Conséquences :

1. **La conversion `seek_<entité>` n'est PAS systématique → décision 3-voies** : un `seek_xxx` dont le
   wrapper **survit** dans la cible compile et tourne tel quel ; il faut donc le **garder**, pas le
   convertir. Mais un wrapper peut aussi **disparaître** d'une version à l'autre (ex. `seek_c4` : 0
   `Seek_C4` vif / 39 `Give_C4` en réf. X.12) → là il **faut** convertir. Le moteur tranche par appel
   sur l'**index des `seek_*` lus dans l'arbre Objets `.dhop`** de la cible (`--objets`, obligatoire) :
   garder si présent (ou helper local), convertir vers `Give_<ent>` si absent mais `Give_<ent>` au pack,
   `;TODO migration` sinon. Pour `Lectab`, au contraire, il n'y a jamais de wrapper → conversion nécessaire.
2. **L'appel `seek_<entité>` ne porte pas de numéro d'erreur** (ex. `Seek_ART(ref)`, `Seek_ART(ref) = 2`)
   → pas de routage `Find_` ; la cible de modernisation est `Give_<entité>`.
3. **Perte de hooks à la modernisation** : `Give_<entité>` (= `Load_<entité>` + `Get_<entité>_Record`)
   **n'appelle pas** `<Ent>_Seek_Av` / `<Ent>_Seek_Ap`. Quand le moteur **convertit** (cas 2 ci-dessus),
   il ajoute un `;TODO hooks: …` sur chaque conversion `seek_` pour vérifier qu'aucune surcharge / aucun
   standard ne s'y branche.
4. **Beaucoup de `seek_xxx` du standard sont aussi des helpers locaux** (cf. §1) — laissés intacts par
   le garde-fou. Entre wrappers framework et helpers locaux, la part réellement convertie reste faible.

## Reproduire l'analyse

Scripts d'analyse (jetables, non livrés avec le skill) : différentiel ligne-à-ligne via `difflib`
entre les arbres `.dhsp` communs aux deux versions, plus comptage des flags `11nn` et inventaire
`Give_/Find_` dans les objets métier `*tmchk*.dhsp` de la version cible. La triangulation X.13 ajoute
l'inventaire global par version et le comptage des formes `allcolumns = true` / `Get_*_Record()`.
