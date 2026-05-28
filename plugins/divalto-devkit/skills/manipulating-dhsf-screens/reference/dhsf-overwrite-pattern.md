# Surcharge masque `.dhsf` -- pattern complet

## Contenu

- Quand surcharger un masque
- Convention de nommage du masque user
- Mecanique reelle -- le `.dhsf` user est une **COPIE COMPLETE** du standard
- 3 proprietes a AJOUTER dans `[masque]`
- 2 proprietes a MODIFIER dans `[masque]`
- Sections `[diva]` / `[diva_base]` -- asymetrie surcharge code vs composants
- Modifier un composant standard -- edition en place (pas de "vrai override")
- Masquer un composant standard -- `XmeSetAttribut` (bonne pratique)
- Fichier compagnon `_base.dhsf`
- Sous-projet `.dhps` de surcharge
- Workflow complet
- Questions ouvertes a Stephane Castelain
- Anti-patterns
- Biais invalides (historique d'apprentissage)

---

## Quand surcharger un masque

Surcharger un masque permet d'**ajouter ou modifier des champs** (composants, callbacks, validations) sur un masque du standard livre, **sans modifier le fichier standard**. xwin7 detecte la surcharge via 3 marqueurs dans la section `[masque]` et lie au masque standard via timestamp de version.

Cas typiques :

- Ajouter un champ custom (issu d'une surcharge dictionnaire R-015/SC-002) dans un zoom existant
- Modifier le comportement d'un masque (validation supplementaire, callback specifique)
- Ajouter une page custom dans un masque multi-pages

---

## Convention de nommage du masque user

```
Standard  : <base>_sql.dhsf       (ex: gtez097_sql.dhsf)
Surcharge : <base>_sqlu.dhsf      (ex: gtez097_sqlu.dhsf)
```

Le suffixe `u` est **AJOUTE A LA FIN du nom de base, AVANT l'extension `.dhsf`**.

**Different du pattern `.dhsp`** : pour les sources DIVA, la convention est `gttz<X>_sql.dhsp` → `gtuz<X>_sql.dhsp` (le `t` devient `u` en position 3-4). Mais pour les masques, la regle universelle est "`e` en position 3 invariant" (cf. [dhsf-structure.md](dhsf-structure.md)), donc le suffixe `u` se place differemment, en fin de nom.

Exemples :

- `gtez000_sql.dhsf` (standard zoom Article) -> `gtez000_sqlu.dhsf` (surcharge)
- `cceq701.dhsf` (standard query Compta) -> `cceq701u.dhsf` (surcharge)
- `a5ee014.dhsf` (standard ecran Transverse) -> `a5ee014u.dhsf` (surcharge)

---

## Mecanique reelle -- le `.dhsf` user est une COPIE COMPLETE du standard

**Le `.dhsf` user n'est PAS un fichier differentiel** pour les sections INI graphiques (`[page]`, `[obj_texte]`, `[champ]`, `[groupbox]`, ...). C'est une **copie complete** du standard, editee directement en place. Tous les composants standards y sont presents avec leurs ids d'origine. Le runtime DIVA charge ce fichier seul, sans fusion avec le standard.

Consequences directes :

- **Ajouter** un composant custom -> nouveau bloc avec `id >= 1000001` (cf. `[masque].dernier_id`)
- **Modifier** un composant standard (position, taille, libelle, wstyle, page parente) -> **editer en place** le bloc existant. **L'id standard est preserve** (id=10 reste id=10).
- **Supprimer** un composant (standard ou custom) -> **retirer purement le bloc** du fichier user. Aucun marqueur, aucune historisation. `dernier_id` n'est pas decremente (compteur monotone d'allocation).
- **Masquer** un composant standard (pratique recommandee plutot que supprimer) -> ajouter `noms="<id_logique>"` dans `[presentation]` puis `XmeSetAttribut(<id_logique>, AN_VISIBILITE, AV_CACHE)` dans `[diva]`. Voir [xmesetattribut-dynamique.md](xmesetattribut-dynamique.md).

> **Pourquoi cette mecanique** : asymetrie volontaire entre code DIVA (override formel via `[diva]`/`[diva_base]`, necessaire pour le compilateur) et UI (copie editable, suffisante car positions/libelles sont volontairement specifiques au projet). Voir section "Sections `[diva]` / `[diva_base]`" ci-dessous.

### Role du `_base.dhsf` confirme

Le fichier compagnon `<basename_complet>_base.dhsf` (voir section dediee plus bas pour la convention de nommage) n'est **pas** une "reference passive". C'est la **reference utilisee par l'AGL pour detecter l'evolution du standard et proposer un re-merge** :

1. A la 1ere edition de surcharge, l'AGL cree `_base.dhsf` = copie exacte du standard de l'epoque
2. A chaque ouverture ulterieure, l'AGL compare `_base.dhsf` avec le standard courant
3. Si different, le standard a evolue -> l'AGL propose un re-merge (re-application des modifications custom sur le nouveau standard)
4. Apres re-merge, `_base.dhsf` est mis a jour vers le nouveau standard

Ce mecanisme est **necessaire** car le `.dhsf` user est autonome au runtime. Sans `_base.dhsf`, on perdrait toute trace du standard d'origine et le re-merge serait impossible.

---

## 3 proprietes a AJOUTER dans `[masque]`

| Propriete | Exemple | Role |
|-----------|---------|------|
| `surcharge=oui` | (constant) | **Marqueur explicite** que xwin7 utilise pour detecter la surcharge |
| `date_modif_base="<TIMESTAMP>"` | `"20211115165338"` | **Coherence de version** : timestamp du standard d'origine. Permet de detecter une mise a jour du standard et signaler les divergences potentielles |
| `niveau_surcharge=1` | `1` ou `2` | Niveau d'imbrication. Analogue au pattern `OverWrite` / `u` / `uu` des `.dhsp` -- voir [overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md) section "Hierarchie de surcharge" |

`date_modif_base` se lit dans l'en-tete du masque standard correspondant :

```
;>xwin4obj   7.0   20211115165338    <-- recopier ce timestamp dans date_modif_base
[masque]
...
```

---

## 2 proprietes a MODIFIER dans `[masque]`

| Propriete | Standard | Surcharge | Pourquoi |
|-----------|----------|-----------|----------|
| `dernier_id` | typiquement 50-100 | **>= 1000000** | Demarrer les IDs custom dans une zone disjointe pour eviter les collisions avec les IDs du standard. Analogue a la regle `EnrNo >= 100000` du skill `allocating-menu-enrno`. |
| `dernier_id_page` | typiquement 10-50 | **>= 100000** | Idem pour les IDs de page custom |

**Exemple final** de bloc `[masque]` apres surcharge :

```ini
[masque]
libelle="Article"
surcharge=oui
date_modif_base="20211115165338"
niveau_surcharge=1
style=normal
dernier_id=1000000
dernier_id_page=100000
dictionnaire=gtfdd.dhsd
...
```

---

## Sections `[diva]` / `[diva_base]` -- asymetrie surcharge code vs composants

Contrairement aux sections INI graphiques (copie complete editee en place), le code DIVA fonctionne par **vrai differentiel** :

| Section | Contenu dans une surcharge masque |
|---------|----------------------------------|
| `[diva_base]` | **Copie EXACTE du `[diva]` standard** (records `Public Record`, procedures `public procedure`, modules, includes, SetModuleInfo -- tout est preserve). C'est la ligne de base utilisee par xwin7 / AGL pour detecter une evolution du standard. |
| `[diva]` | **Surcharge propre** : redeclarations en lowercase derivees de `[enregistrements]` (cf. ci-dessous) + procedures de surcharge a ajouter. Prime sur `[diva_base]` au runtime. |

Le compilateur DIVA tolere `public procedure` dans `[diva_base]` (pas considere comme surcharge la-bas, donc pas d'erreur 210). Les vraies surcharges vont dans `[diva]`, ou les procedures doivent suivre les regles de [overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md) (pas de modificateur de visibilite sur une procedure surchargee, pattern canonique `Standard.<proc>()` d'abord, etc.).

### Pattern `[diva]` user -- derivation depuis `[enregistrements]`

Empiriquement (datapoint canonique gtez113 / gtez047, 2026-05-06), le `[diva]` user genere par l'AGL **n'est PAS** une copie de `[diva]` standard. Il est derive de la section INI **`[enregistrements]`** :

```
[enregistrements] standard                  -> [diva] user
"<file.dhsd>",,<rec>,<alias>,...               Public Record "<file>" <rec> <alias>
"<file.dhoq>",,<rec>,<alias>,...               Public RecordSql "<file>" <rec> <alias>
```

Regles de derivation :

- Tout en lowercase (file, rec, alias)
- Distinction Record/RecordSql par extension (`.dhsd` -> Record, `.dhoq` -> RecordSql)
- Ordre preserve
- Colonnes `<size>` et `<flag>` de `[enregistrements]` ignorees

> **Pourquoi cette derivation** : `[enregistrements]` est la source de verite declarative pour les records du masque. Le code DIVA a besoin des memes records pour ses procedures. La derivation systematique garantit la coherence et permet a l'AGL de regenerer `[diva]` user de facon deterministe.

> **Cas observe** : sur zoom Competence (gtez113), le `[diva]` standard ne contient QU'1 ligne (`Public Record DDSYS.dhsd ROWINFO zoomselection`), mais `[enregistrements]` en contient 3 (2 RecordSql + 1 Record). L'AGL recopie les 3 dans `[diva]` user (lowercase) -- pas seulement la ligne du `[diva]` standard.

### Structure attendue du `[diva]` user

```ini
[diva]
Public Record "ddsys.dhsd" rowinfo zoomselection
Public RecordSql "gtrstab.dhoq" competence competence
Public RecordSql "gtrstab.dhoq" competence competence_sel

; <-- Apres les redeclarations, les procedures de surcharge propres
; (sans modificateur de visibilite, cf. overwrite-pattern.md)

[/diva]
[diva_base]
;; Copie EXACTE du [diva] standard, sans modification
SetModuleInfo('$Id: gtez113_sql.dhsf ...$')
Include "GTTCFICSQL.dhsp"
Module "GTTMCHKCOMPETENCE.dhop"

Public Record DDSYS.dhsd ROWINFO ZoomSelection

Public Procedure Champ_Code_<N>_Ap
BeginP
    ...
EndP

[/diva]
```

> **Terminateur** : observation -- les deux sections sont closes par un **unique** `[/diva]` apres `[diva_base]`. (Voir le datapoint AGL pour confirmer cette syntaxe.)

### Application automatique par `surcharge_mask.py`

Depuis la prise en compte du RETEX R-002, le script `scripts/surcharge_mask.py` applique automatiquement la migration `[diva]` -> `[diva_base]` + la derivation `[diva]` user depuis `[enregistrements]` (extensions `.dhsd` -> `Public Record`, `.dhoq`/`.dhsq` -> `Public RecordSql`, lowercase). Le JSON de sortie inclut un objet `diva_migration` avec `migrated`, `derived_records_count`, `derived_records`, et le tableau `rappels` documente l'etat de la migration ou alerte si elle n'a pas pu etre faite. Verifier ce JSON apres invocation du script avant de compiler -- une migration absente est detectable a ce stade sans recompilation echouee.

---

## Modifier un composant standard -- edition en place

Pour modifier un composant standard (changer position, taille, libelle, wstyle, ou page parente), **trouver le bloc dans le `.dhsf` user et l'editer en place**. L'id standard est **preserve**.

```ini
; AVANT (page 11) -- bloc standard hérité
[obj_texte]
[presentation]
id=10
position=106,10
taille=9,69
wstyle="STD"
[description]
texte="Masquage compte"

; APRES (deplacement vers page 12) -- meme bloc, edition en place
[obj_texte]
[presentation]
id=10                       ; <-- id PRESERVE
position=133,89             ; <-- nouvelle position
taille=9,69
wstyle="STD"
[description]
texte="Masquage compte"
```

**Anti-pattern courant** : creer un nouveau bloc avec `id >= 1000001` au lieu d'editer l'original. Resultat : **doublon visuel** au runtime (le composant standard reste affiche en parallele).

---

## Masquer un composant standard -- `XmeSetAttribut`

La **bonne pratique** pour faire disparaitre un composant standard est de le **masquer dynamiquement** plutot que de le supprimer. Cela preserve la coherence si le standard evolue (le composant existe toujours dans `_base.dhsf`).

Procedure :

1. Dans le `.dhsf` user, ajouter `noms="<id_logique>"` dans la `[presentation]` du composant a cacher
2. Dans la section `[diva]`, appeler `XmeSetAttribut("<id_logique>", AN_VISIBILITE, AV_CACHE)` au point de traitement approprie

Detail complet : [xmesetattribut-dynamique.md](xmesetattribut-dynamique.md).

> **Suppression pure** : retirer purement le bloc du fichier user fonctionne aussi (datapoint canonique 2026-05-07). Aucun marqueur, aucune historisation. Mais perd l'option de revenir en arriere et casse la coherence si le standard evolue.

---

## Fichier compagnon `_base.dhsf`

L'editeur de masque graphique cree **automatiquement** un fichier compagnon `<basename_complet>_base.dhsf` dans `sources/` lors de la 1ere edition de surcharge. C'est une **copie exacte du standard a un instant T**, conservee pour :

- Detecter les divergences si le standard evolue (comparaison `date_modif_base` du `.dhsf` user vs timestamp en-tete du standard actuel)
- Permettre un eventuel re-merge automatique si le standard change

### Convention de nommage du compagnon

Le suffixe `_base` est colle au **basename complet du standard** (extension exclue), pas au prefixe. Si le standard s'appelle `gtez097_sql.dhsf`, le basename complet est `gtez097_sql` -- donc le compagnon est `gtez097_sql_base.dhsf` (et **pas** `gtez097_base.dhsf` comme on pourrait le supposer par analogie avec le pattern `<prefixe>u.dhsf` du masque user).

```
sources/
  gtez097_sqlu.dhsf          <-- masque de surcharge edite par l'integrateur
  gtez097_sql_base.dhsf      <-- copie figee du standard (suffixe _base apres le basename complet _sql)
```

Comportement reproduit par le script `scripts/surcharge_mask.py` (fonction `derive_base_mask_name`) : sortie observee `gtez097_sql_base.dhsf` pour standard `gtez097_sql.dhsf`.

**Convention :** ne JAMAIS editer manuellement le `<basename_complet>_base.dhsf` -- il est gere par l'outil (editeur graphique ou script `surcharge_mask.py`).

> **Question ouverte (a Stephane Castelain)** : le compagnon `_base.dhsf` est-il REQUIS par xwin7 ou seulement utile a l'outillage ? Comportement xwin7 si absent ?

---

## Sous-projet `.dhps` de surcharge

Le masque de surcharge doit etre reference depuis un `.dhps` de surcharge (cf. skill `managing-diva-projects`). Structure type :

```ini
xwin-s-sprojet     2.0                   ; en-tete surcharge (cf. SC-003 / R-006)
[general]
date="<timestamp>"
util="<USER>"
progexec="<programme>.dhop"              ; le mchk associe, observe sur ce cas
[communs]
[fichiers]
fic="gtez097_sqlu.dhsf"," "              ; masque user en [fichiers]
[includes]
[autres]
```

Conventions cles (cf. skill `managing-diva-projects/reference/dhps-structure.md`) :

- En-tete `xwin-s-sprojet 2.0` (variante surcharge, **PAS** `xwin-sprojet`)
- Suffixe `u` final dans le nom du `.dhps` (ex: `gt_table code postal t057u.dhps`)
- **NE PAS** ajouter ce `.dhps` dans `[sousprojets]` du `.dhpt` parent -- xwin7 fait l'auto-detection via `cheminbases` (anti-pattern P17 du skill `managing-diva-projects`)

> Voir [managing-diva-projects/reference/dhps-structure.md](../../managing-diva-projects/reference/dhps-structure.md) section "En-tete -- variantes standard vs surcharge" et anti-pattern P17.

---

## Workflow complet

Sequence canonique pour creer une surcharge masque :

1. **Identifier le masque standard** -- localiser le fichier dans le pack standard livre (`{CHEMIN_ERP_STANDARD}/sources/<base>_sql.dhsf` ou equivalent)
2. **Lire le timestamp du standard** -- recuperer `<TIMESTAMP>` depuis `;>xwin4obj 7.0 <TIMESTAMP>` en en-tete
3. **Copier le standard** vers `<projet_surcharge>/sources/<base>_sqlu.dhsf`
4. **Modifier les 5 proprietes** du `[masque]` (3 ajouts + 2 modifications)
5. **Creer le compagnon** `<basename_complet>_base.dhsf` (suffixe `_base` colle au basename complet, ex: `gtez097_sql_base.dhsf`) -- copie exacte du standard
6. **Creer ou enrichir le `.dhps` de surcharge** -- ajouter le masque dans `[fichiers]`, suffixe `u` final, en-tete `xwin-s-sprojet`, NE PAS ajouter dans `[sousprojets]` du `.dhpt` parent
7. **Compiler** (`buildall`) -- xwin7 doit detecter `surcharge=oui` et lier au standard via `date_modif_base`
8. **Verifier** au runtime : ouvrir le zoom/ecran, confirmer que la surcharge est active

Etapes 3, 4, 5 sont automatisables via le script `surcharge_mask.py` (cf. SKILL.md).

### Indicateur de succes

Apres `buildall`, le rapport mentionne le nombre de masques compiles (`Masques=N`). Verifier que `<base>_sqlu.dhof` est present dans le repertoire des binaires compiles.

---

## Questions ouvertes a Stephane Castelain

Plusieurs points de comportement restent a confirmer cote auteur du framework :

- **Origine de la convention `<base>_sqlu.dhsf`** vs `gtuz<X>_sql.dhsp` -- pourquoi suffixe final pour les masques mais infixe pour les sources ? Lien avec la regle "e en pos 3 invariant" (R-024) ?
- **Comportement `niveau_surcharge=2`** -- multi-niveaux fonctionne-t-il comme le `OverWrite uu` des `.dhsp` ? Cas terrain de multi-niveaux observes ?
- **Compagnon `_base.dhsf` REQUIS ou optionnel** -- comportement xwin7 si absent ? L'outillage le cree-t-il systematiquement ?
- **Mecanisme de detection de derive `date_modif_base`** -- xwin7 ou un outil dedie compare-t-il ce timestamp au standard actuel ? Action prevue en cas de divergence ?

Toute reponse sur ces points peut etre integree dans cette doc via RETEX SUGGESTION-DOC.

---

## Anti-patterns

1. **Convention de nommage `<base>u.dhsf` incorrecte** -- mettre `u` ailleurs que juste avant `.dhsf` (ex: `gtuez097_sql.dhsf` au lieu de `gtez097_sqlu.dhsf`). La regle "e en pos 3 invariant" interdit de toucher au prefixe.
2. **Convention de nommage du compagnon `<basename_complet>_base.dhsf` incorrecte** -- nommer le compagnon `<prefixe>_base.dhsf` (ex: `gtez097_base.dhsf`) au lieu de `<basename_complet>_base.dhsf` (ex: `gtez097_sql_base.dhsf`). Le suffixe `_base` se colle au basename complet du standard (extension exclue), pas au prefixe. Cf. section "Fichier compagnon `_base.dhsf`" -> "Convention de nommage du compagnon".
3. **Oublier `surcharge=oui`** dans `[masque]` -- xwin7 ne reconnait pas la surcharge et tente de charger le masque comme un standard autonome -> conflit / comportement non garanti.
3. **`date_modif_base` invente** -- timestamp arbitraire au lieu de recopier l'en-tete du standard. Casse le mecanisme de detection de derive.
4. **`dernier_id` < 1000000** dans la surcharge -- collision potentielle avec un ID du standard si le standard evolue (nouveau widget avec un ID que la surcharge utilisait deja).
5. **Editer manuellement le compagnon `_base.dhsf`** -- gere par l'outillage, modifier manuellement casse le mecanisme de detection de derive.
6. **Lister le masque de surcharge dans `[sousprojets]` du `.dhpt`** -- doit etre en `[fichiers]` du `.dhps` de surcharge, jamais en `[sousprojets]` (cf. P17 de `managing-diva-projects`).
7. **Ajouter un nouveau bloc avec `id >= 1000001` pour "remplacer" un composant standard** -- cree un doublon visuel. Pour modifier un composant standard, editer en place le bloc existant (id < 1000001 preserve).
8. **Mettre les procedures de surcharge dans `[diva_base]`** au lieu de `[diva]` -- `[diva_base]` doit rester la copie EXACTE du standard. Les surcharges propres vont dans `[diva]`.
9. **Recopier `[diva]` standard dans `[diva]` user** -- l'AGL derive `[diva]` user de `[enregistrements]` (records lowercase), pas de `[diva]` standard.
10. **Transformer `public procedure` en `private procedure` dans `[diva_base]`** -- contournement historique invalide. `[diva_base]` doit conserver les declarations originales du standard sans modification (cf. section "Biais invalides" ci-dessous).

---

## Biais invalides (historique d'apprentissage)

Pour traces historiques uniquement -- ces deux hypotheses initiales sont **invalidees** par la mecanique reelle documentee plus haut :

### Biais 1 -- "Transformer `Public Procedure` en `Private Procedure` dans `[diva]`" (R-031 invalidee par R-033)

**Hypothese erronee** : si la section `[diva]` du masque de surcharge contient des `Public Procedure` du standard, le compilateur leve une erreur 210 ("Elle ne peut etre PUBLIC") car la surcharge est detectee par `surcharge=oui`. Solution proposee : transformer toutes les `Public Procedure` en `Private Procedure`.

**Pourquoi c'est faux** : c'etait un contournement accidentel. La place canonique du DIVA original du standard est `[diva_base]`, **pas `[diva]`**. Dans `[diva_base]`, les `public procedure` ne sont **pas** considerees comme surcharges (donc pas d'erreur 210, sans aucune transformation). La regle correcte : `[diva_base]` = standard inchange / `[diva]` = surcharge propre (cf. R-033/R-034).

### Biais 2 -- "Pas de vrai remplacement possible pour un composant graphique" (R-038 invalidee par R-039)

**Hypothese erronee** : les composants graphiques standards d'un masque (`obj_texte`, `champ`, `groupbox`, ...) ne peuvent pas etre vraiment surcharges. Solution proposee : ajouter des composants `id >= 1000001` en complement (mais le composant standard reste visible -> doublons).

**Pourquoi c'est faux** : le `.dhsf` user est une **COPIE COMPLETE** du standard, editee directement en place. Pour modifier un composant standard, il faut **editer le bloc existant** (id < 1000001 preserve), pas creer un nouveau bloc. Pour supprimer, retirer purement le bloc (pattern symetrique). Pour masquer proprement, utiliser `XmeSetAttribut`.

> Lecon meta : ces deux biais sont des couts d'apprentissage normaux face a une mecanique peu documentee. Le `_base.dhsf` est l'arbitre experimental -- la diff entre une surcharge generee par l'AGL et notre tentative manuelle revele les vraies regles.
