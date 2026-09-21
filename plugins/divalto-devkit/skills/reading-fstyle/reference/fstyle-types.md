# Fstyle -- Detail des 7 types semantiques

> Reference locale du skill `reading-fstyle`. Chiffres empiriques issus de l'exploration de `C:\divalto\sys\fstyle.dhfi` + `fstylewpf.dhfi` + `fstyleimp.dhfi` + `fstyleweb.dhfi` (2026-04-24).

## Contenu

- Vue d'ensemble (table 7 types + counts)
- Type 1 -- Police
- Type 2 -- Couleur RGB
- Type 3 -- Reference i18n (cas cle pour les `tbl*`)
- Type 5 -- Style global STD
- Type 6 -- Cadre
- Type 7 -- Style compose
- Type 9 -- Contexte / scope
- Strategie de resolution multi-variantes
- Encodage

---

## Vue d'ensemble

| Type | Role | Count fstyle.dhfi | Dominant dans |
|------|------|-------------------|---------------|
| 1 | Police (font) | 71 | -- |
| 2 | Couleur RGB nommee | 125 | -- |
| 3 | Reference i18n | 189 | fstylewpf (223 `tbl*`) |
| 5 | Style global STD | 1 | 1 par variante |
| 6 | Cadre (border) | 6 | constant 6 cadres canoniques |
| 7 | Style compose | 186 | -- |
| 9 | Contexte / scope | 214 | -- |

Le Type est stocke a l'**offset 0** (1 octet ASCII). Different de multichoix (offset 17). Le nom est a l'**offset 2** sur 32 octets padding espaces (windows-1252).

Un record magic `*$version 6E` (Type = `'*'`) apparait en tete du fichier : le parseur le skippe.

---

## Type 1 -- Police

Format : `1 <NOM> <taille> 0 0 0 <poids> 0 <flags> <FAMILLE>`.

Les champs apres le nom sont des tokens separes par espaces. L'empirisme montre :
- Token 1 : **taille** (entier, 6-36 typique)
- Tokens 2-4 : 0 (reserves)
- Token 5 : **poids** (400000 = normal, 700000 = gras, convention Windows font-weight)
- Token 6 : 0
- Tokens 7-9 : 3 flags (observes : `3`, `2`, `1`)
- Token 10 : prefixe numerique (typiquement `34`) colle sans espace a la famille
- Dernier token contenant des lettres : **famille** (ex: `Tahoma`, `Arial`)

### Exemples

| Nom | Taille | Poids | Famille |
|-----|--------|-------|---------|
| `.POLICE` | 8 | 400000 | Tahoma |
| `ARIAL10` | 10 | 400000 | Arial |
| `ARIAL10G` | 10 | **700000** (gras) | Arial |
| `ARIAL11BLANC` | 11 | 400000 | Arial |

Convention de nommage : `<FAMILLE><TAILLE>[G][BLANC|GRI|...]`.

### La couleur du texte -- champ de largeur fixe, hors des tokens

**Taille, poids et famille ne suffisent pas a distinguer deux polices.** Un retour terrain
l'a montre : les 18 styles de la famille `DATA` decodaient tous en
`{taille: 8, poids: 400000, famille: Tahoma}` alors que leurs enregistrements sont
**tous differents**.

La couleur du texte vit a un **offset fixe**, pas dans les tokens : **4 composantes de
3 caracteres cadrees a droite, a partir de l'octet 109**, meme decoupage que le Type 2.

| Style | Octets 109-120 | Couleur |
|---|---|---|
| `DATA` | `  0  0  0  0` | noir |
| `DATA_10` | `255  0  0  0` | rouge |
| `DATA_11` | `  0255  0  0` | vert |
| `DATA_16` | `255255255  0` | blanc |
| `DATA_8_FONCE` | `128128128  0` | gris -- et son nom dit « FONCE » |

**Mesure du 2026-08-30** (`fstylewpf.dhfi`) : **142 Type 1 sur 142** portent la 4 composantes
numeriques dans 0-255 a cet emplacement.

> **La 4e composante vaut `0` sur les 142.** Sa semantique **n'est pas etablie** -- elle
> n'est donc **pas** nommee « alpha », ce qui serait une supposition. Elle est exposee telle
> quelle sous `couleur_texte_composante_4`.

**Effet du decodage sur les collisions**, mesure avant/apres :

| Variante | Type 1 | Indistinguables AVANT | APRES |
|---|---|---|---|
| `fstylewpf` | 142 | **64 (45 %)** | **21 (15 %)** |
| `fstyle` (legacy) | 71 | 27 (38 %) | **3 (4 %)** |
| `fstyleimp` | 69 | 14 (20 %) | **1 (1 %)** |

### Ce qui reste NON decode, et qui est declare comme tel

Les collisions restantes se distinguent par un **champ de drapeaux** vers l'octet 123
(observe : `0010000000`, `0001011111`, `0.01111011`). Sa semantique n'est pas etablie.

`--detail` expose donc `attributs_non_decodes` : **une sortie qui ne dit pas ce qu'elle
ignore parait complete**, et c'est le defaut d'origine du retour terrain -- *« decodage
incomplet, mais presente comme complet »*.

---

## Type 2 -- Couleur RGB

Format : `2 <NOM> <R><G><B><A>`. Les 4 canaux sont concatenes en ASCII, 3 chars chacun (pad espaces). Le token peut mesurer 9 a 12 chars.

### Exemples

| Nom | Valeur brute | R G B (A) | Sens |
|-----|-------------|-----------|------|
| `AFFATTENT` | `2552551280` | 255, 255, 128 (0) | jaune clair (attente) |
| `AFFERR` | `255  0  00` | 255, 0, 0 (0) | rouge (erreur) |
| `AFFOK` | `1282551280` | 128, 255, 128 (0) | vert clair (ok) |
| `AIDE` | `  02552550` | 0, 255, 255 (0) | cyan (aide) |
| `.COULEUR` | `1921921920` | 192, 192, 192 (0) | gris (defaut) |

Le decodeur `_decode_type2` tente un parsing strict en 3 chars par canal ; fallback `rgb_brut` si le format est atypique.

---

## Type 3 -- Reference i18n

**Le type central pour les libelles `tbl*` des multichoix.** Sans fstyle, les libelles `tblart`, `tblacti`, `tblnote`... apparaissent opaques dans les livrables de documentation ; avec fstyle, on les resout en cles i18n `#tblart`, `#tblacti`, `#tblnote` -- pret a etre injecte dans la pipeline de rendu.

Format : `3 <NOM> #<cle_i18n> [<flags>] [<couleur>]`.

### Exemples

```
3 TBLART                          #tblart                                                                             001
3 TBLACTC                         #tblactc                                                                            000AUTOMATIQUE
3 AFF_COMPTA                      #aff_compta                                                                         001
```

- Cle i18n : toujours prefixee par `#`, resolue au runtime par le framework Divalto (ressource externe non localisee dans l'exploration -- chantier FS-01)
- Flag 3 chars (`001` / `000`) : semantique a documenter (chantier FS-04)
- Couleur optionnelle (`AUTOMATIQUE` observe) : s'applique quand le style est utilise comme drapeau colore

### Cas orphelins

Sur les 120 `tbl*` uniques du module DAV, 8 n'ont aucune entree dans les 4 variantes fstyle : `TBLAFF`, `TBLMAINT`, `TBLMOINS`, `TBLNOTESEQ`, `TBLPLUS`, `TBLSMILEY1`, `TBLSMILEY2`, `TBLSMILEY3`. Ces cas retournent `{resolved: false, orphan: true}` en mode `--resolve` et restent a investiguer (chantier FS-02).

---

## Type 5 -- Style global STD

Un seul record par variante. Regroupe les styles par contexte (saisie / affichage / bloc / tableau...).

```
5 STD  CHAMP_SAISI  CHAMP_AFF  STD  TABLEAU_SAISI  ...
```

Le decodeur `_decode_type5` retourne `styles_contextuels` = liste ordonnee des tokens apres le nom. Chaque token est le nom d'un style compose (Type 7) a appliquer pour un contexte specifique.

---

## Type 6 -- Cadre (border)

6 cadres canoniques, constants sur toutes les variantes. Format : `6 <NOM> <index> <flag>`.

| Nom | Index |
|-----|-------|
| `SANS` | 1 |
| `SIMPLE` | 2 |
| `RELIEF_RELACHE` | 3 |
| `RELIEF_ENFONCE` | 4 |
| `CADRE_RELACHE` | 5 |
| `CADRE_ENFONCE` | 6 |

Le flag 2e token (`1` systematique) est reserve.

---

## Type 7 -- Style compose

Assemblage nomme de 3 references. Format : `7 <NOM> <police_ref> <cadre_ref> <couleur_ref>`.

> **Les trois slots sont POSITIONNELS, et leurs noms ne tiennent pas toujours.** Mesure du
> 2026-08-30 sur les **235 Type 7** de `fstylewpf` :
>
> | Slot | Ce qu'il vise reellement |
> |---|---|
> | `police_ref` | Type 1 (police) -- **235 / 235** |
> | `cadre_ref` | Type 6 **165**, Type 2 **59**, Type 1 **11** |
> | `couleur_ref` | Type 2 **222**, Type 1 **13** |
>
> **Aucune reference n'est pendante** : les 705 pointent sur un nom present dans le fichier.
> Un retour terrain avait releve `ENTETE_COLONNE_T` dont le `couleur_ref` vise
> `ENTETE_COLONNE`, **une police** -- ce n'est pas une reference cassee, c'est le nom du
> slot qui promet une semantique que la donnee ne porte pas dans **~25 %** des cas.

`--detail` expose donc, a cote des trois references, le **type reel** de chaque cible
(`refs_types_reels`) et, quand il differe de l'attendu, `refs_hors_type_attendu` qui le dit
en clair. Se fier au **type reel**, jamais au nom du slot.

### Exemples

```
7 .STYLE       .POLICE  SANS  .COULEUR       (valeurs par defaut)
7 CHAMP_AFF    AFF      SANS  AUTOMATIQUE    (champ en affichage)
7 CHAMP_AFF_1  DATA_1   SANS  AUTOMATIQUE    (champ colonne 1 de tableau)
```

---

## Type 9 -- Contexte / scope

Les 3 premiers records sont les racines de contexte sans ref associee :
- `9 .BOUTON`
- `9 .MENU`
- `9 .TOOLBAR`

Les autres sont des entrees nommees pointant vers une cle i18n `#tbr_xxx` (tbr = toolbar resource) :
- `9 AIDE #tbr_aide`
- `9 ABANDON #tbr_abandon`
- `9 ADRESSE #tbr_adresse`

---

## Strategie de resolution multi-variantes

Les 4 variantes coexistent dans `C:\divalto\sys\` pour couvrir differents contextes de rendu. La meme structure ISAM est utilisee ; seul le contenu change.

Ordre de resolution recommande (mode `--resolve`) :

```
wpf (moderne, majoritaire)  ->  legacy (WinForms)  ->  imp (impression)  ->  echec
```

| Variante | Records | TBL* | Role |
|----------|---------|------|------|
| wpf | 1655 | **223** | Source moderne, a priviligier |
| legacy | 794 | 73 | WinForms historique, complement |
| imp | 588 | 13 | Cas specifiques impression |
| web | 56 | 0 | Ultra-minimal (pas de `tbl*`) |

`fstyleweb` est exclu de l'ordre par defaut car 0 `tbl*`. Le reste couvre 93 % des `tbl*` multichoix du module DAV.

---

## Encodage

| Zone | Encodage |
|------|----------|
| Tous textes (`Nom`, champs, cles i18n, familles) | windows-1252 |
| Valeurs numeriques (taille, poids, RGB, index) | ASCII (representation textuelle) |

Pas de champ binaire connu dans fstyle (contraste avec `datemc` de gtfdmc qui contient 8 octets binaires FILETIME).
