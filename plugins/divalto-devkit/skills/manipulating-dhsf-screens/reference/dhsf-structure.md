# Structure d'un fichier `.dhsf` (masque ecran)

## Contenu

- Convention de nommage
- Encodage
- Les 8 sections d'un masque
- Section `[masque]` -- proprietes globales
- Section `[diva]` -- code DIVA executable
- Sections visuelles (`[onglet]`, `[page]`, ...)
- **Section `[ressources]`** -- portee MASQUE, et le piege de l'adjacence
- **La chaine des pages** -- `suiv=` / `prec=`
- **Ou vont les sous-sections** -- `[param_case]`, `[param_saisie]`, `esp_si_zero`
- **`col_depl`** -- le tableau qui se fige sans un mot
- Anti-patterns courants

---

## Convention de nommage

La regle de nommage des masques `.dhsf` est **universelle dans le standard** :

| Position | Role | Exemples |
|----------|------|----------|
| 1-2 | Code domaine | `gt`=DAV, `cc`=Compta, `a5`=Transverse, `gg`=Production, `co`=Configuration, `rt`=Retail, `wm`=WMS, `pp`=Paie, `cv`=Convivial, `ga`=Affaires, `gr`=Relation tiers, ... |
| **3** | **Toujours `e`** (= "ecran") | invariant -- **regle universelle** |
| 4+ | Type + identifiant | `z<num>` zoom, `m<X>` module/maintenance, `q<num>` query, `e<num>` ecran libre, `mp<num>` module piece, etc. |

**Verification empirique** : 100 % des 100 masques inspectes du pack standard `v2026_erpX13_p223a` ont `e` en position 3.

Exemples valides :

- `gtez000_sql.dhsf` -- DAV / ecran / zoom 000 (Article)
- `gteepce.dhsf` -- DAV / ecran / edition piece commerciale
- `gtempce000.dhsf` -- DAV / ecran / module piece 000
- `cceq701.dhsf` -- Compta / ecran / query 701
- `a5ee014.dhsf` -- Transverse / ecran / ecran libre 014

> **Bias courant** : confondre la convention "DAV avec suffixe `_sql`" (`gtez<num>_sql.dhsf`) avec une regle generale. C'est seulement une declinaison du domaine DAV ; la **regle universelle est "`e` en position 3"**, pas le suffixe `_sql`.

Le script `is_dhsf_filename.py` automatise la verification de cette regle.

---

## Encodage

Encodage du fichier : **ISO-8859-1 + CRLF**, y compris la section `[diva]` (different d'un `.dhsp` standalone qui peut etre en LF en theorie -- nuance importante).

**Ne jamais** editer un `.dhsf` via Edit/Write de Claude Code -- la conversion silencieuse UTF-8 corrompt les accents (cf. anti-pattern PROJ03 du skill `managing-diva-projects` et hook `protect_encoding.py`). Utiliser le skill `writing-diva-files` ou un script Python explicite avec `encoding="iso-8859-1"`.

---

## Les 8 sections d'un masque

Un `.dhsf` est un **format hybride** : INI declaratif (visuel : pages, champs, onglets) + section `[diva]` qui contient du **vrai code DIVA executable**.

Sections observees sur un masque standard complet (ex: `gtez000_sql.dhsf`) :

| Section | Role | Type |
|---------|------|------|
| `[masque]` | Proprietes globales (libelle, style, ID counters, dictionnaire associe) | declaratif |
| `[defaut]` | Aide, touches par defaut (F1, F8, ...) | declaratif |
| `[enregistrements]` | Records DIVA et RecordSql utilises par le masque | declaratif |
| `[onglet]` | Structure des onglets de navigation | declaratif |
| `[page]` | Definition pages + champs + layout (le gros du fichier) | declaratif |
| `[ressources]` | Ressources externes (images, libelles localises, ...) | declaratif |
| `[diva]` | **Code DIVA executable** (controles, callbacks, validations) | code |
| `[diva_base]` | Code DIVA de base (heritage/framework, typiquement vide ou framework) | code |

En-tete obligatoire avant la 1ere section :

```
;>xwin4obj   7.0   <date>
```

Le `<date>` est un timestamp `YYYYMMDDHHMMSS` qui sert de reference de version (utilise notamment par les surcharges via `date_modif_base` -- voir [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md)).

---

## Section `[masque]` -- proprietes globales

```ini
[masque]
libelle="Article"
style=normal
dernier_id=87                ; compteur d'IDs widgets (incremente a chaque ajout)
dernier_id_page=12           ; compteur d'IDs pages
dictionnaire=gtfdd.dhsd
...
```

Proprietes courantes :

| Propriete | Role |
|-----------|------|
| `libelle="..."` | Titre du masque (apparait dans la barre de fenetre) |
| `style=` | Style global (`normal`, `dialogue`, ...) |
| `dernier_id=<N>` | Prochain ID libre pour un widget custom (incremente a chaque ajout) |
| `dernier_id_page=<N>` | Prochain ID libre pour une nouvelle page |
| `dictionnaire=<X>.dhsd` | Dictionnaire associe (records / RecordSql utilises) |
| `aide=<X>` | Fichier d'aide associe |

**Cas surcharge** : 3 proprietes additionnelles + 2 modifiees. Voir [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md).

---

## Section `[diva]` -- code DIVA executable

La section `[diva]` contient du **vrai code DIVA** au format `.dhsp` standard. C'est la principale source d'erreur quand on traite un `.dhsf` comme du pur INI.

```diva
[diva]
SetModuleInfo('$Id: gtez000_sql.dhsf 186748 ... $')
Include  "GTTCFICSQL.dhsp"
Module   "GTTMCHKART.dhop"

Public Record GTFDD.dhsd ART

Procedure ApresSaisie_Ref
BeginP
    if ART.Ref = ' '
        MessageBox("La reference est obligatoire.")
        ErrorWarning(ART.Ref)
    endif
EndP

Procedure Champ_RacPays_<id>_Ap
BeginP
    ; callback FK : recharge le libelle pays
    Check_T013_Field_RacPays_Lib(<args>)
EndP
[/diva]
```

Types de procedures courantes :

- `ApresSaisie_<champ>` -- controles a la sortie d'un champ (validation, mise a jour cascade)
- `AvantSaisie_<champ>` -- preparation avant entree dans un champ
- `Apres_Zoom_<champ>` -- callback apres un zoom F8
- `Champ_<champ>_<id>_Ap` -- callback FK genere par `dhsf_add_fk.py` (pattern 3 couches)

**Implication majeure** : modifier la section `[diva]` ne se limite PAS a editer le visuel. **Toutes les regles DIVA s'appliquent** :

- Pas de `Public/Private/Protected` sur une procedure surchargee (cf. `coding-diva-advanced/reference/overwrite-pattern.md`)
- Redeclarer les records utilises localement
- Pattern canonique `Standard.<proc>()` d'abord, test du flag d'acceptation ensuite

Voir [coding-diva-advanced/reference/overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md) pour les regles DIVA.

---

## Sections visuelles

Les sections `[onglet]`, `[page]`, `[ressources]` sont du pur INI declaratif. Le parser `dhsf_parser.py` les expose comme un arbre JSON.

### `[onglet]`

Definit la structure des onglets de navigation du masque. Une entree par onglet :

```ini
[onglet]
[onglet_page]
numero=1
libelle="Identifiants"
[/onglet_page]
[onglet_page]
numero=2
libelle="Detail"
[/onglet_page]
[/onglet]
```

### `[page]`

La grosse section du fichier. Une `[page]` par ecran logique, avec ses champs (`[obj_texte]`, `[champ]`, `[champ_tableau]`, `[groupbox]`, ...) :

```ini
[page]
numero=11
libelle="Fiche"
nb_lig=20
nb_col=80
offset_lig=0
offset_col=0
[obj_texte]
id=1
x=5
y=8
texte="Reference"
[/obj_texte]
[champ]
id=2
x=20
y=8
taille=20
donnee=ART,Ref,ART
[/champ]
...
[/page]
```

Voir [normes-graphiques.md](normes-graphiques.md) pour les regles d'ergonomie (espacements canoniques, formules de placement).

### `[enregistrements]`

Liste des records utilises par le masque :

```ini
[enregistrements]
[enregistrement]
nom=ART
type=record
dictionnaire=gtfdd.dhsd
[/enregistrement]
[/enregistrements]
```

---

## Section `[ressources]` -- portee MASQUE, et le piege de l'adjacence

Le bloc `[ressources]` porte les **menus** et les **toolbars**. Sa portee est le **masque
entier**, jamais une page.

> **Il se place APRES la derniere `[page]`.** Mesure : sur les **2 340** masques du corpus qui
> en portent un, **2 340** le placent la. **Aucune exception.**

C'est precisement ce qui rend le piege efficace : le bloc **touche** la derniere page, sans lui
appartenir. Une lecture lineaire conclut a l'inverse.

> **Le cas vecu.** En transformant la derniere page d'un masque en pop-up, le `[ressources]` qui
> la suivait a ete pris pour un menu/toolbar propre a cette page et **absorbe dans la zone
> remplacee**. Menu principal, cinq toolbars et un bouton custom : disparus a l'execution.
> **Rien ne l'a signale** -- ni le compilateur, ni l'ouverture. Seul un backup a sauve la mise.

**Regle** : une edition qui remplace la derniere page d'un masque **s'arrete a la fin de cette
page**. Le `[ressources]` qui suit n'en fait pas partie.

### Le garde-fou : compter avant, compter apres

`dhsf_parser.py --summary` rend un bloc `metrics` avec les compteurs structurants. La recette,
avant toute edition qui **supprime ou remplace** du contenu :

```bash
py scripts/dhsf_parser.py --path <masque>.dhsf --summary   # avant  -> garder metrics
# ... edition ...
py scripts/dhsf_parser.py --path <masque>.dhsf --summary   # apres  -> comparer
```

Les compteurs a surveiller :

| Compteur | Ce qu'il attrape |
|---|---|
| `pages_count` | une page perdue |
| `widgets_total` | des champs, tableaux, groupbox perdus |
| `toolbars_count`, `menus_count` | un toolbar ou un menu entier perdu |
| **`ressources_items_count`** | **un bouton perdu DANS un toolbar conserve** |
| `enregistrements_count` | un enregistrement perdu |

> **Le dernier est celui qui manquait.** Perdre un bouton custom dans un toolbar qui existe
> toujours laisse `toolbars_count` inchange : seul le compte des **items** le voit. Il a ete
> ajoute pour cette raison.

**Toute baisse non voulue est un signal d'arret**, pas un detail a expliquer apres coup.

---

## La chaine des pages -- `suiv=` / `prec=`

Les pages se chainent par `suiv=` (page suivante) et `prec=` (page precedente). C'est ce qui
lie les onglets entre eux.

**Une page sans successeur n'a PAS de ligne `suiv=`** : l'omission est la fin de chaine, il n'y
a pas de valeur « aucune ».

> **Le piege : un lien orphelin ne se voit pas a la compilation.** Un `suiv=` ou un `prec=`
> qui designe une page absente du masque compile **a 0 erreur**. L'ecran meurt a
> l'**OUVERTURE**, avec « page N du masque inexistante ». Rien avant.

**Cas typique, et il vient du template de ce skill.** `template_zoom_sql.dhsf` porte une page
12 « Identifiants » (`usercr`, `usercrdh`, `usermo`, `usermodh`) et la paire `suiv=12` /
`prec=11` qui la chaine a la page 11. Ces champs n'existent **que si la table a ete creee avec
le socle audit standard**. Sur une table sans ce socle, il faut supprimer la page 12 -- et
alors **les deux liens doivent partir avec elle**. Page et liens sont indissociables.

`dhsf_modify.py --action validate` croise desormais les `suiv=`/`prec=` avec la liste des pages
reellement presentes et signale les liens orphelins.

---

## Ou vont les sous-sections -- `[param_case]`, `[param_saisie]`, `esp_si_zero`

Les sous-sections d'un composant ne sont pas interchangeables. Deux regles mesurees sur le
corpus des masques du standard, consignees dans [mesures-corpus.json](mesures-corpus.json).

### `[param_case]` : deux composants, et il y est systematique

| | |
|---|---|
| Occurrences | **7 729** dans **1 217** masques |
| Parents observes | `case_a_cocher` (**6 854**), `case_a_cocher_tableau` (**875**) |
| Ailleurs | **0** |

Le compte est **un pour un** avec le nombre de ces blocs : `[param_case]` n'est pas seulement
*autorise* dans ces deux composants, il y est **systematique**.

Dans un `[champ]` ordinaire, `[param_case]` fait echouer la compilation. Un `[champ]` avec
`saisie=non` affiche la valeur numerique brute.

> Pour la **valeur** d'une case a cocher, voir la regle du booleen DIVA : **non coche = `1`,
> coche = `2`, jamais `0`** -- `0` (ou l'espace) veut dire « non renseigne ». Detail et mesure
> dans le skill `coding-diva-advanced`, `reference/syntaxe-de-base.md`.

### `esp_si_zero` : une regle de PLACEMENT, pas de validite

| | |
|---|---|
| Occurrences | **33 576** dans **2 014** masques sur 2 438 |
| Sous-section | **`[param_saisie]`** -- **0 occurrence ailleurs** |
| Composants porteurs | `champ_tableau`, `champ`, `multi_choix_tableau`, `multi_choix`, `case_a_cocher_tableau` |
| Avec `saisie=non` | **22 451, soit 67 %** |

**`esp_si_zero` est parfaitement valide**, et massivement employe. Ce qui ne l'est pas, c'est
de le placer **hors de `[param_saisie]`** -- en particulier dans `[description]`, forme que le
corpus ne montre jamais.

> **Correction d'un retour terrain.** Un partenaire, apres des erreurs de compilation, avait
> conclu que « `esp_si_zero=oui` n'est pas un attribut valide dans cette version : ne pas
> l'inclure ». La mesure dit l'inverse. Appliquer cette conclusion reviendrait a retirer un
> attribut d'affichage legitime de dizaines de milliers d'endroits. Et `saisie=non` n'y est
> pour rien : c'est **le cas dominant**, pas une exception.

---

## `col_depl` -- le tableau qui se fige sans un mot

`col_depl` se declare dans le `[param_tableau]` d'un `[tableau]`, juste apres `fl_trait_lig`.

> **Symptome de son absence** : le tableau charge et affiche ses lignes normalement, mais
> **ni les fleches du clavier ni le clic ne changent la ligne selectionnee**. Aucune erreur de
> compilation, aucun message au runtime. Le tableau semble simplement fige.

| | |
|---|---|
| Occurrences | **1 704** dans **1 309** masques |
| Valeurs observees | de **1 a 17** ; dominantes `3` (569) et `2` (555) |
| `[param_tableau]` **sans** `col_depl` | **1 113 sur 2 817**, soit **40 %** |

**Ce n'est donc pas une propriete obligatoire** -- 40 % des tableaux du standard s'en passent.
C'est pourquoi ce skill **n'emet pas** d'avertissement quand elle manque : la regle produirait
1 113 faux positifs sur du code livre.

> **Ce qui n'est pas etabli** : la semantique du nombre. La distribution de 1 a 17 est
> coherente avec un **indice de colonne**, mais rien ne le demontre -- la documentation n'en
> porte aucune occurrence, et le corpus ne l'explique pas. Ne pas le deviner : le reprendre
> d'un tableau comparable du meme domaine, comme on le fait pour la semantique d'un indice de
> champ tableau.

---

## Anti-patterns courants

1. **Traiter `.dhsf` comme du pur INI** -- la section `[diva]` contient du DIVA executable, soumis aux regles du langage (cf. `coding-diva-advanced`).
2. **Confondre "convention DAV `gtez_sql`" et "convention universelle"** -- la regle est `e` en position 3, pas le suffixe `_sql`.
3. **Editer `.dhsf` via Edit/Write** -- conversion UTF-8 silencieuse, accents corrompus. Toujours via `writing-diva-files`.
4. **Oublier d'incrementer `dernier_id`** apres un ajout de widget -- collision d'IDs au prochain ajout. Le script `dhsf_modify.py` le gere automatiquement.
5. **Lister un masque de surcharge dans `[fichiers]` standard** au lieu de la convention surcharge -- cf. [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md).
6. **Supprimer une page sans retirer les `suiv=`/`prec=` qui la designent** -- compile a 0 erreur, casse a l'ouverture.
7. **Retirer `esp_si_zero` en croyant l'attribut invalide** -- il l'est seulement hors de `[param_saisie]`.
8. **Utiliser un `[champ]` haut pour du texte multiligne** -- c'est `rich_edit` qu'il faut, cf. [composant-rich-edit.md](composant-rich-edit.md).
