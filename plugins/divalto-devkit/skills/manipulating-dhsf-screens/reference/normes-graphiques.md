# Normes graphiques DIVA -- Fragment reference manipulating-dhsf-screens

> Source canonique : `docs/NORMES-GRAPHIQUES.md` (workspace). Ce fragment extrait les regles necessaires a la generation / modification d'un masque .dhsf. Les valeurs sont en unites Divalto (le `position=Y,X` et `taille=H,L`).

## Sommaire

1. Placement (mode FICHE)
2. Tailles d'ecran autorisees
3. Styles WPF canoniques
4. Onglet Identifiants -- ordre canonique obligatoire
5. Formules
6. Points d'attention
7. Liens avec les anti-patterns du linter

## 1. Placement (mode FICHE)

| Zone | Valeur | Notes |
|------|--------|-------|
| Bord gauche -> objets | `X=5` | Tous objets (champ, texte, groupe) |
| Bord sup -> 1er objet | `Y=8` sans onglet, `Y=26` avec onglets | Cas special : tableau direct sans champ avant = `Y=18` |
| Marge droite | `X` fin = largeur - 5 | Les groupes se terminent a 5 du bord droit |
| Entre champs dans un groupe | `10` (tasse), `12` (defaut), `14` (espace) | Choix selon densite |
| Cle -> autres objets | `14` (16 si objet = groupe) | Offset de la cle |
| Entre 2 groupes | `8` horizontal ou vertical | Sauf harmonie d'ecran |

## 2. Tailles d'ecran autorisees (page 1 `nb_lig,nb_col`)

Seules ces 8 tailles sont autorisees :

```
33x120  35x120  31x120  25x90  25x60  25x120  33x130  35x130
```

Cas barres bouton texte supplementaires :
- 1 barre texte supp. : 35x120 -> **33x120**
- 2 barres texte supp. : **31x120**

## 3. Styles WPF canoniques

**Textes (`[obj_texte]`)** : `STD`, `STD_AFF`, `STD_GRAS`, `STD_CADRE3D`, `STD_AFF_TITREGROUPE`, `STD_TITREGROUPE`, `TITRE`, `TITRE_GROUPE`.

**Champs (`[champ]`)** : `CHAMP_SAISI`, `CHAMP_NON_SAISI`, `CHAMP_AFF`, `CHAMP_AFF_GRAS`, `CHAMP_NON_SAISI_GRAS`, `CHAMP_AFF_OPEN`, `CHAMP_AFF_TITREGROUPE`, `CHAMP_TITREGROUPE`, `ZOOM_SAISI`, `ZOOM_NON_SAISI`, `ETAT`, `ETAT_OPEN`.

**Tableaux** : `TABLEAU_AFF`, `TABLEAU_SAISI`, `TABLEAU_AFF_ETAT` (icone non-deplaçable), `TABLEAU_AFF_POINTE`, `ENTETE_COLONNE`.

**Groupes (`[groupbox]`)** :

| Cas | `wstyle` | `couleur_fond` |
|-----|----------|----------------|
| Groupe standard | `GROUPE` | `GROUPE_FOND` |
| Sous-groupe | `GROUPE` | `SOUS_GROUPE_FOND` |
| Cadre a fond blanc + titre `TITRE` | `GROUPE` | `BLANC` |

**Styles modules-specific** (a utiliser seulement dans le module concerne) : `TNT_*` (Achat-Vente), `TABLEAU_CPT_*`/`CHAMP_CPT_*` (Comptabilite), `CHAMP_TPV_*`/`TABLEAU_TPV_*` (Point de vente), `CHAMP_ATELIER_*` (Atelier).

## 4. Onglet Identifiants -- ordre canonique obligatoire

Regle : **tout champ audit declare dans le dictionnaire** (`Ce1`, `Note`, `Joint`, `UserCr`, `UserCrDh`, `UserMo`, `UserMoDh`) **doit apparaitre** dans l'onglet Identifiants du masque zoom.

Ordre des groupboxes (par Y croissant) :

1. **Codes enregistrements** (Y min, obligatoire si `Ce1`/`Note`/`Joint` dans le dict)
2. _optionnel_ : Protection
3. _optionnel_ : Derniere operation
4. **Creation** + **Derniere modification** (Y max, obligatoires si socle `UserCr`/`UserCrDh`/`UserMo`/`UserMoDh`)
5. _optionnel_ : extensions domaine (Origine creation, Date dernier envoi CRM, ...)

Exemple X.13 (zoom Article, page 22) :

```
Y=26  X=5    Codes enregistrements
Y=72  X=5    Derniere operation
Y=108 X=5    Creation
Y=108 X=164  Derniere modification
Y=158 X=5    Origine creation         <- extension domaine
```

## 5. Formules

**Libelle accole a un champ** :

```
Pos X(libelle) = 1 + Pos X(champ) + Taille(champ)
```

**Taille d'un `[groupbox]` standard** :

```
taille = NbLignes * espacement (10/12/14) + 18
taille = 30 si 1 ligne (espacement 12 implicite)
```

**Taille d'un `[groupe_radio]`** :

```
taille = NbLignes * 10 + 12              (avec titre)
taille = NbLignes * 10 + 11              (sans titre, 1er bouton a Y=8 au lieu de 9)
```

**Ecart entre un titre et son tableau** :

```
Pos Y(tableau) = Pos Y(texte) + Taille(texte) + 1
```

**Bornes de grille (regles R4/R5 du validateur)** :

```
max_X(obj) <= nb_col * 4                  -- regle R4 (saturation largeur)
max_Y(obj) <= nb_lig * 14 - 30            -- regle R5 (saturation hauteur)
```

La borne theorique de R5 est `nb_lig * 14`, mais xwin7 echoue avec
`"Objet en dehors de la clip grille"` pour des `max_Y` bien sous ce plafond
sur les pages avec onglet : le header + footer reservent ~30 unites non
comptabilisees dans `nb_lig`. Empiriquement, sur une page nb_lig=25
(theorique 350), la saturation reelle commence vers max_Y=320. La constante
`GRID_LIG_MARGE = 30` dans `scripts/dhsf_modify.py` reflete cette marge.

**Dimensions de groupes a largeur egale (mode FICHE zoom traditionnel)** :

| Ecran | 1 groupe | 2 groupes (taille, Y2) | Notes |
|-------|----------|------------------------|-------|
| 33x120 | 470 | 231, X=244 | 3 groupes : 151 + 151 + 152 |
| 25x90 | 350 | 171, X=184 | -- |
| 25x60 | 230 | 111, X=124 | -- |

## 6. Points d'attention

- **Pas d'attachement** (attache_lgx/attache_lgy) sur les `[groupbox]` (norme 2015 a reconfirmer).
- Cases a cocher : texte a **droite** de preference (alignement avec autres objets).
- Tableaux : ligne courante surlignee + fleche en consultation ET modification.
- Tableau avec arbre : afficher systematiquement `+`/`-` via boutons feuille de style.
- Colonnes non-deplaçables : `"colonnes deplaçables"=OUI`, `"nombre affichees"=X`, `"a partir de"=X+1` ; icones en `TABLEAU_AFF_ETAT` + "Trait autour"=NON + largeur 12.

## 7. Liens avec les anti-patterns du linter

| Code | Objet | Severite |
|------|-------|----------|
| E16 | Champ audit declare mais absent de l'onglet Identifiants | error |
| E17 | Ordre des groupboxes de l'onglet Identifiants non canonique | warning |
| E18 | Positions X hors valeurs canoniques {0, 5, 8, 10, 12, 14, 16, 18, 26} en 1re colonne | info |
| E19 | Taille d'ecran hors liste autorisee section 2 | warning |
