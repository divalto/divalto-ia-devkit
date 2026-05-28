# Composant `champ` -- saisie ou affichage d'une donnee

## Contenu

- Quand utiliser
- Grammaire generale
- Sous-sections detaillees
- wstyle vs saisie -- regle critique
- Distinction `[presentation].cadrage` vs `[description].cadrage`
- Triplet bouton zoom contextuel (F8)
- Cas particulier `saisie=objgraph`
- Codes touches `[touches]`
- Hooks DIVA `[traitements]`
- Anti-patterns
- Templates de generation

---

## Quand utiliser

`champ` est le composant **saisie/affichage d'une donnee** liee a un record DIVA. C'est le composant le plus dense d'un masque (~3683 occurrences sur l'echantillon des 136 masques standard).

Distinct du `obj_texte` (libelle statique sans donnee) : un `champ` est **toujours lie** a une donnee record via `[description].donnee=`.

---

## Grammaire generale

```ini
[champ]
[presentation]                ; obligatoire
position=Y,X
taille=H,L
id=N                          ; >= 1000001 en surcharge
wstyle="CHAMP_SAISI"          ; cf. wstyles ci-dessous
colonnes_saisie=20            ; optionnel, doit <= Nature du champ dans le .dhsd
[description]                 ; obligatoire -- LIAISON DATA
donnee=record,champ,instance  ; reference au .dhsd
[param_saisie]                ; quasi-obligatoire
[touches]                     ; frequent (binding touches F-keys)
[traitements]                 ; majoritaire (hooks DIVA)
[boutons]                     ; optionnel (activation contextuelle des boutons toolbar)
[aide_page]                   ; optionnel (aide F1 contextuelle)
[info_bulle]                  ; rare (tooltip)
```

Sous-sections rares ou obsoletes : `[reaffichage]` est **obsolete** (relique d'une version anterieure, ne pas generer).

---

## Sous-sections detaillees

### `[presentation]`

| Propriete | Valeur |
|-----------|--------|
| `position=Y,X` | Coordonnees en orteils |
| `taille=H,L` | Hauteur et longueur en orteils |
| `id=N` | Identifiant unique du widget. **>= 1000001 en surcharge** |
| `wstyle="<X>"` | Reference vers `fstylewpf.dhfi`. Trois valeurs dominantes : `"CHAMP_SAISI"` (saisissable, 38%), `"CHAMP_NON_SAISI"` (lecture seule avec bordure grisee, 33%), `"CHAMP_AFF"` (affichage sans bordure, 24%) |
| `colonnes_saisie=N` | Largeur de saisie en caracteres. Doit etre **<= Nature** du champ dans le `.dhsd`. Plafonner sinon le champ apparait plus grand que la donnee. |
| `noms="<X>"` | Identifiant logique pour `XmeSetAttribut` (cf. [xmesetattribut-dynamique.md](xmesetattribut-dynamique.md)) |
| `attache_x` / `attache_lgx` | Ancrage droite / largeur variable. Mutuellement exclusifs |
| `cadrage=<X>` | `gauche`/`centre`/`droite` -- aligne la **presentation visuelle de la zone** (purement cosmetique) |

### `[description]`

| Propriete | Valeur |
|-----------|--------|
| `donnee=record,champ,instance` | **Obligatoire**. Reference au dictionnaire DIVA. Ex: `devise,dev,devise` lie le champ au record `Devise`, champ `Dev`, instance `devise`. Pour un champ multi-dimension : `donnee=record,champ,instance,indice1[,indice2]` (chaque dimension en slot positionnel separe). |
| `saisie=<X>` | `non` pour bloquer la saisie au runtime. **Independant de `wstyle`** -- voir section "wstyle vs saisie" ci-dessous. Valeur speciale `objgraph` pour les objets graphiques pilotes par code (cf. ci-dessous). |
| `format="<X>"` | Format d'affichage (alpha, numerique, date, duree, ou dynamique). 4 familles documentees dans `xwin-ecran.chm` (`L`/`M`/`R` cadrage, `0`/`9`/`*` chiffres, `JJ`/`MM`/`AAAA` dates, etc.). Reference complementaire DIVA : fonctions `Format`, `Formatd`, `Fstring`. |
| `sequence=N` | Numero unique de "point de sequence" pour repositionner la saisie via `Harmony.Retour = XMENEXT_POINT_SEQUENCE` + `Harmony.CplRetour = N`. Distinct de l'ordre de saisie (qui suit l'ordre physique des blocs dans le fichier). |
| `cadrage=<X>` | `gauche`/`droite`/`centre` -- aligne le **contenu dans le buffer** de N caracteres (affecte la chaine stockee, distribution des espaces). Equivalent aux codes `L`/`R`/`M` du `format=`. |
| `minmaj=<X>` | `majuscules` / `minuscules` / `minuscules_ss_accents` -- conversion automatique a la saisie. Cas typique : `majuscules` sur les codes SQL (alignement avec la regle MAJUSCULES SQL Server, cf. [diva-case-sensitivity.md](diva-case-sensitivity.md)). |

### `[param_saisie]`

Sous-section optionnelle, presente sur 94.5% des champs.

| Propriete | Valeur |
|-----------|--------|
| `type_date=<X>` | Format date attendu. Valeurs : `jj/mm/aaaa` (94%), `jj/mm/aaaa+hh:mm:ss` (5%), `hh:mm:ss`, `h:m`, `h:m:s`, `dmmm/aaaa` |
| `table_associee=oui` | Active la mecanique zoom F8 (couple avec `[touches].f8=<num>` et `[boutons] "zoom"`) |
| `obligatoire=oui` | Champ requis a la saisie. Halo colore visible au runtime. |
| `cache=oui` | Champ masque (saisie type mot de passe) |
| `esp_si_zero=oui` | Pour les numeriques : afficher des espaces si la valeur est zero. |
| `defaut=<X>` | Valeur par defaut a l'initialisation |

### `[touches]`

Liste de couples `(touche, code_action)`. Le code DIVA standard `A5_Saisie_Page_CaseCommun` route les codes via `Harmony.DataArret` et `Harmony.Key`. Codes courants :

| Code | Action |
|------|--------|
| `129` ou `K_F1` | A propos |
| `135` ou `8000` (`K_F7`) | Zoom generalise |
| `5997`/`5998` (`K_SF1`) | Aide contextuelle |
| `8100..8199` | Aide variant |
| **`1000..1999`** | **Traitement utilisateur** (custom) |
| **`9000+`** | **Zoom contextuel** -- numero specifique de zoom (typiquement `f8=<NumZoom>`) |
| `10000..10099` | Appel de note |

Exemple : `f8=9047` ouvre le zoom Devise (numero 9047).

### `[traitements]`

Hooks DIVA appeles au cours du cycle de vie du champ. Propriete principale : `diva_apres="Champ_<X>_<id>_Ap"`. Le nom est convention `Champ_<NomChamp>_<id_widget>_Ap`. La procedure doit exister dans la section `[diva]` (ou `[diva_base]` du standard, cf. [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md)).

Pour une procedure de surcharge, suivre [overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md) -- pas de `Public/Private/Protected`, redeclaration locale des records, pattern canonique `Standard.<proc>()` d'abord.

### `[boutons]`

Liste de `wnom_sel` (lowercase) matchant les boutons de toolbar definis dans `[ressources] > [toolbar] > [item] > [param_bouton]`. Quand le focus arrive sur le champ, ces boutons s'activent contextuellement.

Distribution corpus : `"zoom"` est dominant (98%). Voir aussi "Triplet bouton zoom contextuel" ci-dessous.

### `[aide_page]`

Aide F1 contextuelle. Propriete `aide=N` (numero d'aide) + `fichier="<X>FAIDE"` (un fichier ISAM d'aide par domaine : `GTFAIDE`, `CCFAIDE`, etc.).

### `[info_bulle]`

Tooltip au survol souris. Propriete `texte="<X>"`. Pas besoin de `noms=`.

---

## wstyle vs saisie -- regle critique

**`wstyle` est purement visuel. `saisie` est ce qui bloque vraiment la saisie au runtime.** Les deux sont **independants** et doivent etre combines correctement :

| Combinaison | Aspect visuel | Comportement runtime | Cas d'usage |
|-------------|---------------|---------------------|-------------|
| `wstyle="CHAMP_SAISI"` (defaut) | Saisissable (bordure visible) | Saisie possible | Champ classique de saisie |
| `wstyle="CHAMP_NON_SAISI"` + `saisie=non` | Bordure grisee visible | Saisie bloquee | Champ lecture seule dans un groupe de saisissables (hierarchie visuelle preservee) |
| `wstyle="CHAMP_AFF"` + `saisie=non` | **Sans** bordure | Saisie bloquee | Champ d'affichage pur (typique : champs audit `UserCr`, `UserMo`) |
| `wstyle="CHAMP_AFF"` **SANS** `saisie=non` | Sans bordure | **Saisie POSSIBLE** -- ANTI-PATTERN | Bug : le champ apparait grise mais reste cliquable et saisissable |

Pour un champ lecture seule, **toujours combiner les deux** : `wstyle` (cosmetique) + `saisie=non` (comportement).

**Distinction `CHAMP_NON_SAISI` vs `CHAMP_AFF`** : tous deux lecture seule, mais avec rendus differents. `CHAMP_NON_SAISI` garde une bordure grisee (utile dans un groupe de champs saisissables pour la coherence visuelle). `CHAMP_AFF` n'a aucune bordure (utile pour les champs audit purs).

---

## Distinction `[presentation].cadrage` vs `[description].cadrage`

Les deux proprietes operent a **niveaux differents** -- ne pas les confondre :

| Propriete | Niveau | Effet |
|-----------|--------|-------|
| `[presentation].cadrage` | **PRESENTATION VISUELLE** (zone graphique) | Aligne le rendu visuel dans la boite -- purement cosmetique, n'affecte pas la donnee stockee. |
| `[description].cadrage` | **DONNEE / BUFFER** | Positionne le contenu dans les N caracteres de la donnee. Affecte la chaine stockee, distribution des espaces de remplissage. |

**Exemple canonique** : champ "Code devise" 4 caracteres avec valeur `"1"` :

- `[description].cadrage=gauche` -> stocke `"1   "` (3 espaces a droite materialises)
- `[description].cadrage=droite` -> stocke `"   1"` (3 espaces a gauche)

`[description].cadrage` fait le meme travail que les codes alpha du `[description].format` (`L`=gauche, `R`=droite, `M`=centre). Coexistence techniquement possible mais convention : utiliser l'un OU l'autre, pas les deux.

---

## Triplet bouton zoom contextuel (F8)

Pour declencher un zoom contextuel sur un champ avec le bouton loupe affichable :

1. `[param_saisie].table_associee=oui` -- active la mecanique zoom
2. `[touches].f8=<NumZoom>` -- numero de zoom a appeler (typiquement >= 9000)
3. `[boutons]` contient `"zoom"` -- affiche le bouton loupe contextuellement (matche le `wnom_sel="zoom"` de la toolbar du masque)

Sans ce triplet, le bouton apparait mais ne fonctionne pas (ou inversement).

---

## Cas particulier `saisie=objgraph`

Variante du champ avec `[description].saisie=objgraph` -- sert a afficher un **objet graphique pilote programmatiquement par le code DIVA** (typique : barre de progression, jauge, indicateur visuel). Cas rare (0.08% du corpus standard).

Caracteristiques distinctives vs champ classique :

| Aspect | Champ classique | Champ `saisie=objgraph` |
|--------|-----------------|--------------------------|
| Saisie utilisateur | Oui | **Non** |
| Hooks DIVA | Frequents | **Aucun** (pas de `diva_avant`/`diva_apres`) |
| `[description].sequence` | Possible | **Aucun** |
| Rendu visuel | Widget WPF natif | **Genere par code DIVA** -- chaine de directives a balises affectee a `G7.Chemin` |

Pilotage par code DIVA : assignation a la variable `G7.Chemin` avec syntaxe a balises. Exemple observe :

```diva
G7.Chemin = "<hog>"
if couleur <> " "  | G7.Chemin &= "<c>" & couleur            | endif
if taille  <> " "  | G7.Chemin &= "<e>" & tostring(taille)    | endif
G7.Chemin &= "<bafv>" & tostring(showProgress)
if maxi    <> " "  | G7.Chemin &= "<max>" & tostring(maxi)    | endif
G7.Chemin &= "<b>" & tostring(valeur) & ";0"
```

Balises identifiees : `<hog>` (init), `<c>` (couleur), `<e>` (taille), `<bafv>` (mode affichage progression), `<max>` (max), `<b>` (valeur courante). Documentation complete : a chercher dans `xwin-ecran.chm` section "Affichage des objets" ou "Affichage des valeurs des barres".

---

## Anti-patterns

1. **Oublier `[description].donnee`** -- champ sans liaison data, non fonctionnel.
2. **`wstyle="STD"`** au lieu d'un `"CHAMP_*"` -- rendu incoherent (style libelle sur un champ).
3. **`format="JJ/MM/AAAA"`** sur un champ non-date -- format inadapte.
4. **`id < 1000001`** sur un nouveau champ en surcharge -- collision avec id standard. Pour modifier un champ standard, editer en place.
5. **Mismatch `diva_apres=` et procedure DIVA** -- la procedure doit exister dans `[diva]` ou `[diva_base]` avec la bonne signature.
6. **`colonnes_saisie` superieur a la Nature du champ** dans le `.dhsd` -- incoherence visuelle. Plafonner a la Nature.
7. **Confondre `[description].cadrage` (buffer) et `[presentation].cadrage` (visuel)** -- meme attribut, niveaux distincts.
8. **Confondre `sequence` et l'ordre de saisie** -- `sequence` est un identifiant pour code DIVA (`XMENEXT_POINT_SEQUENCE`), l'ordre de saisie est gere par l'ordre PHYSIQUE des blocs.
9. **Combiner `attache_x=oui` ET `attache_lgx=oui`** (idem Y) -- exclusivite mutuelle.
10. **Generer `[reaffichage]`** -- OBSOLETE.
11. **`[boutons] "zoom"` sans le triplet complet** (`table_associee=oui` + `f8=<num>`) -- bouton loupe affiche mais non fonctionnel.
12. **`wstyle="CHAMP_AFF"` SANS `saisie=non`** -- le champ apparait grise mais reste saisissable au runtime (cf. section "wstyle vs saisie").
13. **Reference `[boutons] "<X>"`** ou `<X>` n'existe pas dans les toolbars du masque -- bouton orphelin.
14. **`XmeSetAttribut("<X>", ...)`** sans `noms=` correspondant -- appel silencieux ignore.

---

## Templates de generation

### Champ saisissable minimal lie a un U-container

```ini
[champ]
[presentation]
position=120,30
taille=9,80
id=1000003
wstyle="CHAMP_SAISI"
colonnes_saisie=20
[description]
donnee=devise,udev_moncode,devise
```

### Champ avec zoom F8 + bouton zoom contextuel + hook DIVA + aide F1

```ini
[champ]
[presentation]
position=120,30
taille=9,80
id=1000003
wstyle="CHAMP_SAISI"
colonnes_saisie=8
[description]
donnee=devise,udev_pays,devise
[param_saisie]
table_associee=oui                ; <-- 1
obligatoire=oui
[touches]
f1=129
f7=135
f8=9053                           ; <-- 2 (zoom Pays)
[traitements]
diva_apres="Champ_UDev_Pays_1_Ap"
[aide_page]
aide=12345
fichier="gtfaide"
[boutons]
"zoom"                            ; <-- 3 (bouton loupe contextuel)
```

### Champ d'affichage pur (lecture seule, audit)

```ini
[champ]
[presentation]
position=120,30
taille=9,80
id=1000003
wstyle="CHAMP_AFF"                ; aspect "champ d'affichage" (sans bordure)
[description]
donnee=devise,usercr,devise
saisie=non                         ; <-- BLOQUE la saisie au runtime (independant de wstyle)
```

### Champ pilote dynamiquement (visibilite via XmeSetAttribut)

```ini
[champ]
[presentation]
position=120,30
taille=9,80
noms="form_admin"                  ; <-- cle pour XmeSetAttribut
id=1000003
wstyle="CHAMP_SAISI"
[description]
donnee=devise,udev_admincode,devise
```

```diva
; Cote code DIVA dans [diva] :
if user_is_admin = 'O'
    XmeSetAttribut("form_admin", AN_VISIBILITE, AV_VISIBLE)
else
    XmeSetAttribut("form_admin", AN_VISIBILITE, AV_CACHE)
endif
```

Voir [xmesetattribut-dynamique.md](xmesetattribut-dynamique.md) pour le pilotage dynamique complet.
