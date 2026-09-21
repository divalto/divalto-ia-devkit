# Regles Syntaxe (S01-S12) et Langage inexistant (L01-L04)

## Syntaxe

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| S01 | error | Concatenation avec `+` au lieu de `&` | Regex: `+` entre expressions string |
| S02 | warning | `VRAI`/`FAUX` au lieu de `True`/`False` | Keyword match |
| S03 | error | Variable declaree apres `BeginP`/`BeginF` | Detection de bloc : var entre Begin et End |
| S04 | error | `Function` sans `FReturn` | Parse blocs Function, verifier FReturn |
| S06 | error | Code DIVA dans un `.dhsf` (hors blocs `[diva]` / `[diva_base]`) | Type de fichier + pattern code |
| S07 | error | Code DIVA dans un `.dhsq` | Type de fichier + pattern code |
| S08 | *V2* | `Zoom.Valretour` utilise sans initialisation | Analyse de flux semantique |
| S09 | *V2* | `public` sur une procedure surchargee (Erreur 210) | Necessite de savoir si la proc surcharge le standard. Un critere intra-fichier **sur** existe (une procedure `X` dont le corps appelle `Standard.X()` **est** une surcharge, sinon l'appel ne resoudrait pas) mais il ne trouve **rien** : 0 constat sur 5241 `.dhsp` reels. La regle serait juste et sans prise -- voir la fiche ci-dessous |
| S10 | error | `OverWrittenBy` pointant un `.dhsp` (source) au lieu d'un `.dhop` (compile) | Regex sur la ligne `OverWrittenBy` ; signale si la cible finit par `.dhsp` |
| S11 | error | Procedure/Function **locale** appelee avant sa definition, **sans `Proto`** | Releve les definitions et les `Proto` du fichier, puis tout appel a un nom defini plus bas sans prototype prealable |
| S12 | error | Ligne **physique** de plus de **251 caracteres** | Longueur de chaque ligne. Portee : **`.dhsp` et `.dhsf`** seulement -- les `.dhpt`/`.dhps` en sont exclus sur preuve contraire |

## Langage inexistant

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| L01 | error | `ForEach` (n'existe pas en DIVA) | Keyword: `\bForEach\b` |
| L02 | error | `Try`/`Catch`/`Finally` (pas d'exceptions en DIVA) | Keyword: `\bTry\b`, `\bCatch\b` |
| L03 | error | `Class` (pas d'OOP en DIVA) | Keyword: `\bClass\b` suivi d'un nom |
| L04 | error | Threads (n'existent pas en DIVA) | Keyword: `\bThread\b`, `\bCreateThread\b` |

## Contexte DIVA

- **Concatenation string** : operateur `&` (pas `+` qui est addition numerique). S01 ignore desormais un `+` a l'interieur d'un litteral (ex `Modify('+','%2B',...)`).
- **Booleens** : `True`/`False` (pas `VRAI`/`FAUX` qui n'existent pas)
- **Boucles** : `Loop`/`EndLoop`, `For`/`Next`, `Repeat`/`Until`, `Do`/`While`/`Wend`
- **Separateurs** : `|` separe deux instructions sur une meme ligne logique -- ce n'est NI un commentaire NI un OU ; le commentaire est `;`
- **Pas de** : ForEach, Try/Catch, Class, Thread
- **Surcharge / `OverWrittenBy`** (S10) : la directive doit referencer l'objet **compile** qui surcharge, dont l'extension depend du type de fichier source : `.dhsp` -> `.dhop`, `.dhsq` -> `.dhoq`, `.dhsd` -> `.dhod`. Les jointures `.dhsj` font exception (elles restent en `.dhsj`). S10 est donc **scopee aux `.dhsp`** : detecter un `.dhsp` la ou l'on attend un `.dhop`. Une regle generique « doit finir en `.dhop` » produirait des faux positifs sur tous les `.dhsq` (qui utilisent legitimement `.dhoq`).

## S11 -- appel avant definition, sans prototype

Une procedure ou fonction **locale** doit etre **declaree avant son premier appel** :
le compilateur DIVA resout les appels au fil du module. Le mot-cle `Proto` existe
exactement pour lever cette contrainte -- *« le prototype d'une fonction permet
d'appeler la fonction avant qu'elle soit reellement definie. Cela permet de resoudre
les problemes d'ordre des fonctions dans les sources »* (Manuel de reference DIVA,
« Les prototypes ») :

```diva
Proto Procedure Piece_Calculer_Marge(bMajPaTotMt, RemPiedFl)
  ; declaration des parametres formels
EndProto

; ... l'appel peut desormais preceder la definition
Piece_Calculer_Marge(True, 0)
```

**Mesure sur le standard X.13** (4245 `.dhsp` portant au moins une procedure locale) :
**37** appels anticipes, **tous** couverts par un `Proto` prealable, et **aucun sans**.
1215 fichiers declarent au moins un prototype. La regle est donc muette sur le standard
et ne signale que le vrai defaut (#274).

> **Piege d'implementation** : les commentaires de **milieu de ligne** doivent etre
> retires avant de chercher les appels. Sans ca, `;a totaliser (sous total, total)`
> ressemble a un appel de la procedure `Totaliser` -- faux positif reellement constate
> dans `cctmdeverse.dhsp` du standard en mettant cette regle au point.

---

## S12 -- ligne physique de plus de 251 caracteres

Une telle ligne **compile sans erreur**, mais l'editeur XWin **refuse d'ouvrir le
fichier** : « Edition du fichier impossible : une ligne depasse 251 caracteres »
(#198). Le source devient donc non modifiable dans l'IDE, ce qui est plus penalisant
qu'une erreur de compilation -- d'ou la severite `error`.

La limite porte sur la ligne **physique**. Le caractere de continuation DIVA reste
legitime : il coupe une ligne **logique** en plusieurs lignes physiques, chacune devant
rester sous la limite.

**Portee : `.dhsp` et `.dhsf` uniquement**, les deux types que le RETEX atteste.

- Les **`.dhpt` / `.dhps` sont exclus sur preuve contraire** : le standard livre contient
  une ligne `filtres="??pp*;??pc*;..."` de **282 caracteres** dans
  `divalto modules communs.dhpt`, fichier qui fonctionne. La limite ne s'applique donc
  pas aux fichiers projet -- c'est mesure, pas suppose.
- Les autres types (`.dhsq`, `.dhsd`, `.dhsi`, `.dhse`) sont **non testes** : aucune
  source reelle mesuree n'y depasse la limite, donc ni preuve ni contre-preuve. Ils
  restent hors portee tant qu'un cas concret ne tranche pas.

> Meme regle et meme raison dans `writing-diva-files` (`verify_encoding.py`), qui la
> fait respecter sur le **chemin d'ecriture**. Ici elle est verifiee a la **lecture**,
> sur un source deja ecrit -- les deux sont complementaires, pas redondantes.

---

## S09 -- pourquoi elle reste reportee

`public` sur une procedure surchargee provoque l'erreur 210 (« La fonction/procedure
est une surcharge. Elle ne peut etre PUBLIC »). Un critere **sur** existe sans quitter
le fichier : dans un `.dhsp` portant une directive `OverWrite`, une procedure `X` dont
le corps appelle `Standard.X()` **est** prouvablement une surcharge -- sinon l'appel ne
resoudrait pas.

Mais la mesure ne justifie pas la regle : sur **5241 `.dhsp` reels** (standard X.13 +
un specifique partenaire), ce critere donne **0 constat**. Les 62 fichiers `OverWrite`
du specifique contiennent 141 surcharges prouvees, **aucune** en `public`. La regle
serait juste et sans prise ; le besoin est couvert par la documentation du pattern de
surcharge dans `coding-diva-advanced`.

> **Ne pas generaliser aux masques.** Dans un `.dhsf` de surcharge, le code standard
> vit en `[diva_base]`, ou les `public procedure` ne sont **pas** traitees comme des
> surcharges -- donc pas d'erreur 210, sans aucune transformation. C'est un biais deja
> invalide empiriquement : voir `manipulating-dhsf-screens`,
> `reference/dhsf-overwrite-pattern.md`, section « Biais 1 ».

---

> **S05 retiree (2026-06-16)** : un commentaire de fermeture `EndP`/`EndF` n'est pas une convention DIVA -- regle supprimee (faux positifs sur le code legacy non commente, sans signal utile).
