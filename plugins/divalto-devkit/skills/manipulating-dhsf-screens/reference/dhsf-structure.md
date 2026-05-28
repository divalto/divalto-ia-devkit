# Structure d'un fichier `.dhsf` (masque ecran)

## Contenu

- Convention de nommage
- Encodage
- Les 8 sections d'un masque
- Section `[masque]` -- proprietes globales
- Section `[diva]` -- code DIVA executable
- Sections visuelles (`[onglet]`, `[page]`, ...)
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

**Ne jamais** editer un `.dhsf` via Edit/Write de Claude Code -- la conversion silencieuse UTF-8 corrompt les accents (cf. anti-pattern P03 du skill `managing-diva-projects` et hook `protect_encoding.py`). Utiliser le skill `writing-diva-files` ou un script Python explicite avec `encoding="iso-8859-1"`.

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

## Anti-patterns courants

1. **Traiter `.dhsf` comme du pur INI** -- la section `[diva]` contient du DIVA executable, soumis aux regles du langage (cf. `coding-diva-advanced`).
2. **Confondre "convention DAV `gtez_sql`" et "convention universelle"** -- la regle est `e` en position 3, pas le suffixe `_sql`.
3. **Editer `.dhsf` via Edit/Write** -- conversion UTF-8 silencieuse, accents corrompus. Toujours via `writing-diva-files`.
4. **Oublier d'incrementer `dernier_id`** apres un ajout de widget -- collision d'IDs au prochain ajout. Le script `dhsf_modify.py` le gere automatiquement.
5. **Lister un masque de surcharge dans `[fichiers]` standard** au lieu de la convention surcharge -- cf. [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md).
