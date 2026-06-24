# Règles de conversion — détail et cas limites

Source de vérité comportementale du skill `converting-diva-lectab`. Le moteur
(`scripts/convert_lectures.py`) reproduit les regex de `autoConvertSrc.json` (outil éditeur
`AutoConvertSrc.exe`) puis les **étend** et les **valide** contre l'objet métier du pack Std cible.

> Les règles ci-dessous sont **alignées sur la migration standard réelle X.2 → X.4**, triangulée avec
> **X.13 (la cible des migrations actuelles)**. Preuves chiffrées, exemples nominatifs et inventaire
> par version : voir [`reference/observations-x2-x4.md`](observations-x2-x4.md).

## 1. `seek_soc` → `Load_gtfdos`

- `seek_soc(args)` → `Load_gtfdos(args)`.
- **Exception directe** : pas de vérification d'objet métier (le dossier/société n'a pas de
  `*tmchksoc.dhsp` ; la nouvelle API est `Load_gtfdos`).
- Règle issue de `autoConvertSrc.json`, **confirmée par la cible X.13** : `Load_gtfdos` y apparaît
  2 147 fois (0 en X.2/X.4 — adoptée entre X.4 et X.13). Pleinement valide pour une migration vers
  X.13. Réserve : beaucoup de `seek_soc` du standard sont des **fonctions locales** (préservées par le
  garde-fou) → pas de conversion systématique.
- Tous les autres `seek_<x>` suivent le schéma `Give_<x>`.

## 2. `seek_<x>` génériques → `Give_<x>(<INSTANCE>, …)`

- Entité = ce qui suit `seek_` (ex. `seek_art` → `art`, `seek_sart` → `sart`, `seek_fou` → `fou`).
- Objet métier recherché : `*tmchk<x>.dhsp` dans le pack Std (`--std`), n'importe quel préfixe
  domaine (`gt`, `cc`, `rc`…). Localisation par index des noms de fichiers.
- Fonction cible : `public function <type> Give_<x>(&<INSTANCE>, …)`.
  - Le **nom exact** (`Give_ART`, `Give_AdrIso`) et le **nom d'instance** (`ART`, `AdrIso`) sont
    extraits de la signature réelle — jamais devinés.
- Conversion : `seek_art(ref)` → `Give_ART(ART, ref)`. Confirmés sur X.2→X.4 :
  `seek_cli`→`Give_Cli`, `seek_vrp`→`Give_VRP`, `seek_fou`→`Give_FOU`, `seek_tia`→`Give_TIA`,
  `seek_c4`→`Give_C4`, `seek_t2`→`Give_T2`.
- **Décision 3-voies (≠ `Lectab`)** : `Seek_<ent>` **peut survivre** comme wrapper public dans le
  framework de la cible (`gtpmfic.dhsp` : `Seek_ART`, `Seek_SART`, `Seek_Ent`, `Seek_Mouv`, `Seek_TVA`, …
  + variantes `_Key`), faisant l'accès ISAM legacy (`G3_File_Seek`) **et appelant les hooks d'extension
  `<Ent>_Seek_Av` / `<Ent>_Seek_Ap`**. Le moteur **ne convertit donc pas aveuglément** : il tranche
  **par appel** sur l'index des `seek_*` lus dans l'arbre Objets `.dhop` de la cible (`--objets`,
  **obligatoire**) :
  1. **GARDER** `seek_<ent>` intact si présent dans l'index (le wrapper survit) — ou défini localement ;
  2. **CONVERTIR** en `Give_<ent>` (+`;TODO hooks`) si le wrapper a disparu **mais** `Give_<ent>` existe au pack ;
  3. **`;TODO migration`** si introuvable partout (à investiguer).
  Frontière de mot stricte (`seek_c3` ≠ `seek_c3xq`). Sans `--objets`, le script refuse de tourner.
- **Note hooks (ajoutée automatiquement)** : `Give_<ent>` (= `Load_<ent>` + `Get_<ent>_Record`) **ne
  déclenche pas** les hooks `<Ent>_Seek_Av/_Ap`. Chaque conversion `seek_<ent>` → `Give_<ent>` reçoit
  donc un `;TODO hooks: …` invitant à vérifier qu'aucune surcharge / aucun standard ne se branche sur
  ces hooks (sinon régression).
- **Variante `_Key`** : `Seek_<ent>_Key(...)` accède au **même** objet métier `<ent>` par une clé
  alternative. Si `Give_<ent>_Key` n'existe pas mais `Give_<ent>` oui, le moteur cible `Give_<ent>`
  (clé multi-champs éclatée normalement, cf. §4 bis) — il ne cherche pas un objet `<ent>_Key` inexistant.
- **`seek_tiers` n'a pas de cible unique** : pas de `Give_Tiers`. Il se résout selon la nature en
  `Give_CLI | Give_FOU | Give_PRO | Give_VRP | Give_TIA` → le moteur laisse **intact + TODO** (choix
  métier). Idem `seek_pcfidx`.
- **Variantes suffixées** : l'objet métier expose parfois seulement `Give_<x>_Conf`,
  `Give_<x>_Grref`, `Give_BPENT_With_Feu`… Le moteur cherche `Give_<x>` **exact** ; si seule une
  variante existe → TODO (à brancher manuellement sur la bonne variante).
- **Si `Give_<x>` introuvable** dans le pack → ligne inchangée + `;TODO migration: Give_<x> …` + rapport.

## 3. `Lectab(nn, …)` → `Give_T0nn(T0nn, …)` (cas dominant)

- Numéro de table sur **1 ou 2 chiffres** : `Lectab(6, …)`, `Lectab(1, …)` aussi bien que
  `Lectab(17, …)`. Normalisation sur 2 chiffres → entité `t0nn`, objet métier `*tmchkt0nn.dhsp`,
  fonction `Give_T0nn`, instance `T0nn` (extraite de la signature, ex. `Give_T025(&T025,Nst)`).
- `Lectab(25, wmvtl.nst)` → `Give_T025(T025, wmvtl.nst)` ; `Lectab(6, ART.ProdNat)` → `Give_T006(T006, ART.ProdNat)`.
- **Forme bracket** : `Lectab(nn, [p1 p2])` → `Give_T0nn(T0nn, p1, p2)` (éclatement sur l'espace).
- **Args surnuméraires tronqués à l'arité réelle** (`trim_args`) : `Lectab`/`Seek` recopiaient des flags
  legacy (n° d'erreur déjà extrait, `0` de non-affichage, options) que `Give_`/`Find_` n'acceptent pas.
  Le moteur tronque à l'arité de la signature cible (give = params après l'instance ; find = champs de
  clé ; `Load_gtfdos` = 1). Un arg qui rentre est conservé (`Give_C3(C3, cpt, 0)` si `Give_C3` a 2 params
  après l'instance) ; le surplus est coupé. Si le surplus coupé n'est pas un simple `0`/vide → `;TODO args`.
- **Concaténation `&` (clé composite)** : `Lectab` / `Seek` reçoivent la clé **concaténée**
  (`champ1 & champ2`) alors que `Give_`/`Find_` attendent les champs **séparés**. Le moteur éclate
  la clé sur les `&` de **premier niveau** (en respectant `()` et `[]`, ignore `&&`) en autant
  d'arguments que la cible attend de **champs de clé** — voir §4 bis. Ex. `Lectab(18, mvtl.Depo &
  mvtl.Lieu, 1118)` → `Find_T018(mvtl.Depo, mvtl.Lieu, allcolumns = true)`.
- **Éclatement ambigu** : si le nombre de segments `&` ≠ nombre de champs de clé attendu (ex. la clé
  est une variable déjà concaténée, ou l'appel d'origine fournissait moins de champs que la clé n'en
  compte), la clé est **laissée telle quelle** + `;TODO cle: …` pour séparation manuelle.
- **Si `Give_T0nn` introuvable** → TODO.
- Premier argument **non numérique** (constante `C_TABLE_*`, `CeBin`, `CeCout`, `Valnum`…) → appel
  laissé tel quel, silencieusement.

## 4. Give_ vs Find_ : c'est le 3ᵉ argument (numéro d'erreur) qui tranche

Le 3ᵉ argument d'un `Lectab(nn, clé, errno)` est le **numéro d'erreur** affiché si l'enregistrement
n'est pas trouvé, convention `11nn` = `1100 + numéro de table` (`1139` pour T039, `1140` pour T040…).
Sa présence détermine **mécaniquement** la cible, parce que les deux fonctions de l'objet métier ne
gèrent pas l'erreur de la même manière (vérifié dans le code, cf. signatures réelles ci-dessous) :

- **Sans numéro d'erreur → `Give_T0nn(T0nn, clé)`** : remplit l'instance `T0nn` (`Load` + `Get_Record`),
  **n'affiche aucune erreur**. C'est le cas dominant.
- **Avec numéro d'erreur `11nn` → `Find_T0nn(clé)`** : `Find_T0nn` appelle en interne
  `GT_GererErreurCheck(11nn, clé, …)` sur échec → **affiche l'erreur automatiquement**, exactement
  comme le faisait l'ancien `Lectab` avec son numéro d'erreur.

> Toutes les tables `T000`..`T099` exposent à la fois `Give_T0nn` **et** `Find_T0nn` ; `T041` n'est pas
> un cas spécial. `Lectab(41, x)` *sans* numéro d'erreur → `Give_T041`.

**Signatures réelles (objet métier X.13)** — attention, elles diffèrent :

```divalto
public function int Give_T039(&T039, ActCod)              ; instance + clé, remplit T039, pas d'erreur
Public function int Find_T039(&ActCod, allcolumns, context) ; CLE seule (pas d'instance), erreur auto
```

- `Give_` se convertit `Give_T0nn(T0nn, clé)` (instance en 1ᵉʳ argument).
- `Find_` se convertit `Find_T0nn(clé)` — **la clé directement, sans instance** en 1ᵉʳ argument.
  `allcolumns` (défaut `false`) et `context` (défaut `false`) sont optionnels.

**Si le code aval lit l'enregistrement après un `Find_`** : `Find_T0nn(clé)` (allcolumns défaut `false`)
ne remplit pas l'instance. **Le moteur détecte ce cas automatiquement** : si un accès `T0nn.Champ`
existe ailleurs dans le fichier, il génère `Find_T0nn(clé, allcolumns = true)` et ajoute en fin de
ligne `;TODO Get_Record: … T0nn = Get_T0nn_Record()`. Pourquoi un TODO et pas l'insertion directe : le
`Get_T0nn_Record()` est une **2ᵉ instruction**, à placer après le succès du `Find_` ; quand le `Find_`
est dans une condition (`If Find_T0nn(...) = 0`), insérer une instruction séparée n'est pas fiable
mécaniquement → c'est laissé au développeur, mais signalé et localisé. Variante minoritaire :
`Load_T0nn(clé, allcolumns = true)`.

Détection : `\bT0nn\.` (instance suivie d'un point) dans le fichier. Heuristique « sûre par excès » —
charger l'enregistrement quand il n'est pas consommé est inoffensif ; l'oublier alors qu'il l'est
serait un bug. Un `Lectab` **sans** numéro d'erreur reste un `Give_T0nn` (qui remplit déjà l'instance),
même si `T0nn.Champ` est lu ensuite : pas d'enrichissement nécessaire.

**Distinction clé composite / numéro d'erreur** : `Lectab(62, A & B)` (clé composite) → les segments
`&` deviennent des arguments séparés (cf. §4 bis) ; seul un dernier argument **égal à `1100+nn`** est
traité comme un numéro d'erreur (et déclenche le routage `Find_`).

## 4 bis. Nombre de champs de clé : lu sur la signature `Find_<ent>`

L'ancien `Lectab`/`Seek` prend la clé **concaténée** ; `Give_`/`Find_` prennent les champs **séparés**.
Pour savoir en combien d'arguments éclater, le moteur compte les **paramètres de tête passés par
référence (`&`)** dans la signature `Find_<ent>` (convention objet métier : la clé d'abord, en `&`,
puis les options par valeur — `conf`, `nonvide`, `allcolumns`, `context`, …) :

```divalto
Find_T018(&depo, &lieu, allcolumns, context)              ; 2 champs de clé : depo, lieu
Find_C3(&cpt, nonvide, syntaxe, …)                        ; 1 champ de clé : cpt
Find_ART(&ref, artind, conf, HsDt, allcolumns, …)         ; 1 champ de clé : ref
Find_pcfidx(&tiers, &contact, conf, …)                    ; 2 champs de clé : tiers, contact
```

- Ce compte sert **autant à `Give_` qu'à `Find_`** (même entité, même clé) : `Give_C3(&C3, cpt, conf, f)`
  a 1 champ de clé (`cpt`), pas 3 — `conf`/`f` sont optionnels et **ne sont pas devinés** par le moteur.
- Clé à **1 champ** → jamais éclatée (même si l'expression contient un `&`, c'est alors une valeur).
- Clé à **N>1 champs** → éclatement sur `&` si le nombre de segments correspond, sinon `;TODO cle`.
- `Find_<ent>` introuvable / aucun `&` en tête → compte inconnu → pas d'éclatement (comportement sûr).

## Déclaration du module objet métier

Toute conversion utilisant un objet métier impose la présence de sa directive d'inclusion compilée
en tête de source : `Module "<om>.dhop"` (l'objet métier source `gttmchkart.dhsp` se référence en
`gttmchkart.dhop`).

- Le moteur collecte, par fichier, l'ensemble des objets métier réellement utilisés par les
  conversions appliquées (`Give_ART` → `gttmchkart`, `Give_T036` → `gttmchkt036`,
  `Find_T041` → `gttmchkt041`, …).
- Les directives **manquantes** sont insérées dans le bloc `Module` existant (sinon après le dernier
  `Include`, sinon avant la première ligne de code), au format `Module\t"<nom>.dhop"`.
- **Dédoublonnage** insensible à la casse vs les `Module` déjà déclarés → **idempotent** (re-exécuter
  n'ajoute pas de doublon).
- `seek_soc → Load_gtfdos` ajoute `Module "gtpmfdos.dhop"` (module framework portant `Load_gtfdos`,
  livré compilé dans le pack ; son source `.dhsp` n'est pas dans l'extrait).
- Le rapport liste chaque `Module "X.dhop" ajoute dans <fichier>` + un total.

## Cas limites et garde-fous

- **Casse** : recherche insensible (`Seek_Art`, `seek_art`, `LECTAB` matchent). Sortie = casse réelle
  de l'objet métier.
- **Faux-amis** : `\b` (frontière de mot) évite de matcher `seek_art` à l'intérieur de `xseek_art` ;
  en mode généralisé `seek_sart` est traité comme une entité distincte (`sart`).
- **Fonctions locales** : tout `seek_xxx` défini comme `function … seek_xxx(` **n'importe où dans les
  sources du lot** est considéré comme un helper projet → jamais converti ni flagué (pré-passe globale).
- **Appels imbriqués** : les arguments sont traités récursivement (un read dans les args d'un autre
  read est aussi converti) via extraction par parenthèses équilibrées.
- **Multi-ligne** : traitement ligne par ligne ; un appel non refermé sur la ligne n'est pas converti
  (continuation `\` non reconstituée).
- **Encodage** : lecture/écriture ISO-8859-1 (latin-1) → round-trip exact des octets non modifiés,
  fins de ligne préservées, aucun BOM ajouté.
- **`SetModuleInfo`** : règle de vérification de l'outil d'origine — **ignorée** ici.
- **Périmètre fichiers** : `.dhsp` + masques `.dhsf`/`.dhsi` + `.dhsq` (option `--extensions`, défaut `dhsp,dhsf,dhsi,dhsq`). Les `.dhsd` (dictionnaires) ne sont jamais touchés. Les fichiers `*_base.*` sont exclus (`--exclude-pattern`, défaut `_base`). Mesuré sur un projet V7 réel : ~84 % des `seek_`/`Lectab` vivent dans les masques (`.dhsf`/`.dhsi`), ~16 % dans les `.dhsp` ; les `.dhsq` sont déclaratifs (aucun appel de lecture → no-op).
- **Filtre `[diva]` / `[diva_base]` (masques de surcharge — NON-NÉGOCIABLE)** : un masque de surcharge contient `[diva]…[/diva]` (code SURCHARGE, modifiable) et `[diva_base]…[/diva]` (copie figée du STANDARD, **INTOUCHABLE** — la modifier casse le diff de surcharge). Sur `.dhsf`/`.dhsi`, le moteur ne transforme **que** les lignes du bloc `[diva]` exact (state machine ligne par ligne) et **restreint l'insertion des directives `Module` à ce seul bloc**. Désactivable par `--no-diva-filter` (dangereux).
  - **Fail-safe** : toute structure de balises inattendue (bloc non fermé, imbrication, `[/diva]` orphelin, plus d'un bloc `[diva]`) → fichier **laissé intact** et listé au rapport (« Masques IGNORÉS par sécurité »). Les variantes `[diva_xxx]` (≠ `[diva]` exact) sont traitées comme **non modifiables**.
  - **Garde-fou auto-vérifié** : après conversion d'un masque, le moteur vérifie qu'**aucune ligne hors `[diva]` n'a changé** (sinon abandon du fichier) et le rapport l'atteste par fichier (« bloc [diva] lignes X-Y — aucune modif hors [diva] »).

## Sortie

- Seuls les fichiers **modifiés** sont écrits sous `--out`, en miroir du chemin relatif.
- Rapport `regExResult.txt` : en-tête (paramètres), liste par fichier
  (`<titre> - appliqué dans <fichier> (xN)` et `<fonction> NON converti - objet métier absent …`),
  synthèse chiffrée, **`;TODO` regroupés par type** (hooks / Get_Record / migration / clé) avec
  compteur, audit masques (« 0 dans `[diva_base]` ») et liste des masques ignorés par sécurité.
- Option **`--dry-run`** : génère le rapport **sans écrire** le miroir converti (estimation de périmètre).
