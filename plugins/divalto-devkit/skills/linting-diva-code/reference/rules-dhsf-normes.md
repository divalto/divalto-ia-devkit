# Regles normes graphiques masques (.dhsf) -- Fragment reference linting-diva-code

> Source canonique : `docs/NORMES-GRAPHIQUES.md` et `docs/ANTI-PATTERNS.md` section 7 (workspace). Ce fragment documente les 6 regles E16-E21 implementees dans `lint_diva.py`.

## E16 -- Champ audit absent de l'onglet Identifiants

**Severite** : `error`

**Regle** : si un masque est un zoom (`type_masque=2`) avec un onglet `libelle="Identifiants"` (typiquement page 12), les 4 champs du socle audit canonique doivent apparaitre dans les `donnee=` des `[champ]` de cette page :

```
UserCr      UserCrDh     UserMo      UserMoDh
```

**Heuristique** (single-file) : extrait la page Identifiants et cherche chaque nom de champ dans les attributs `donnee=vue,champ,alias`. Un champ absent = 1 error E16.

**Extension cross-file** (non implementee -- reportee) : lire le dictionnaire `.dhsd` lie via `[enregistrements]` -> `.dhoq` -> `HFileVersion` et verifier presence des champs audit ; si present dans le dict mais absent du masque, E16 ; sinon pas d'erreur (entite sans socle audit). Pour l'instant, on flag des que le socle canonique est incomplet dans un zoom (faux positifs possibles sur des zooms "exotiques" sans socle).

## E17 -- Ordre des groupboxes de l'onglet Identifiants non canonique

**Severite** : `warning`

**Regle canonique** (groupboxes tries par Y croissant dans la page Identifiants) :

1. **Codes enregistrements** en 1er (Y min) -- obligatoire si present
2. Optionnels intercales : **Protection**, **Derniere operation**
3. **Creation** + **Derniere modification** (Y max du bloc audit)
4. Extensions domaine acceptees apres le bloc audit (ex: Origine creation, Date dernier envoi CRM).

**Detection** : extrait `[groupbox]` + `position=Y,X` + `texte=` dans la page Identifiants, trie par Y croissant. 2 types de warning :
- "Codes enregistrement*" present mais pas en position 1 (Y non-min)
- Un groupbox non-audit (autre que Codes/Protection/Derniere op/Creation/Derniere modif) s'intercale *avant* la fin du bloc audit (= extension placee au milieu)

Les regex de matching (insensibles a la casse) :
- `r'code\s*enregistr'` -> Codes enregistrement*
- `r'^\s*cr[ée]ation\s*$'` -> Creation (exact)
- `r'derni[eè]re\s+modif'` -> Derniere modification
- `r'protection|derni[eè]re\s+op[eé]ration'` -> groupboxes intercalables

## E18 -- Positions X hors valeurs canoniques

**Severite** : `info`

**Valeurs canoniques** (1re colonne) :

```
{0, 5, 8, 10, 12, 14, 16, 18, 26}
```

**Detection** : scan de toutes les `position=Y,X` avec `X < 30` (zone "1re colonne" la plus contrainte par la norme). Emet **une seule info** avec stat agregee : `N/total positions hors canoniques (pct%)`. Pas de report par-occurrence (trop bruite sur les masques existants).

**Tolerance pratique X.13** : X = 4 ou 6 tolere (~10 % des cas en X.13), mais les generateurs doivent emettre strictement `X=5`.

## E19 -- Taille d'ecran hors normes

**Severite** : `warning`

**Tailles autorisees** (page 1, `nb_lig x nb_col`) :

```
33x120   35x120   31x120   25x90   25x60   25x120   33x130   35x130
```

**Detection** : lit les premieres `nb_lig=N` et `nb_col=M` du fichier (typiquement page 1). Verifie presence dans le set autorise. Si hors liste, warning avec la taille trouvee et la liste complete.

**Note** : `35x130` est une derogation tacite acceptee (73 masques X.13 l'utilisent, validation Stephane 2026-04-21).

## E20 -- Groupbox sous-dimensionne (R-007 2026-04-23)

**Severite** : `error`

**Condition** : pour chaque `[groupbox]` contenant N enfants (`[champ]`, `[obj_texte]`, `[case_a_cocher]`, `[bouton_radio]`, `[groupe_radio]`), verifier `taille_H >= N * 10 + 18` (borne min : espacement 10).

**Pourquoi** : formule canonique `NbLignes * espacement (10/12/14) + 18` (15 titre + 3 marge bas). Un groupbox sous-dimensionne tronque son titre ou le chevauche avec le premier champ -- incident RaceChat 2026-04-23 : titre "Description" reduit a "...cription".

**Heuristique** : scan minimal regex (`_extract_all_groupboxes`). Les groupboxes sans enfants typographiques sont ignores.

## E21 -- Gap entre groupbox insuffisant

**Severite** : `warning`

**Condition** : pour deux groupbox consecutifs sur la meme colonne X (meme page), `gap = Y_suivant - (Y_courant + H_courant) >= 8`.

**Pourquoi** : norme v7 section 2.5 "Espacement vertical entre 2 groupes : 8".

**Tolerance empirique X.13** : production admet gaps 2-5 (chevauchement de bordures par design). Severite warning (non bloquant) : la norme reste `>= 8` mais les gaps inferieurs ne sont pas des bugs visuels.

**Heuristique** : scan groupboxes, regroupement par `(page, X)`, tri par Y, gap entre voisins.

## Tests

Les 4 regles ont ete validees sur l'echantillon X.13 (2026-04-21) :
- 100 zooms aleatoires : 0 faux positif sur E16 et E17 ; 3 anomalies E19 reelles detectees ; E18 info produite sur tous (stat variable).
- Templates du skill `manipulating-dhsf-screens` : 0 warning/erreur (apres correction `template_ecran_crud.dhsf` 30x120 -> 33x120).

## Voir aussi (dans ce skill)

- `reference/rules-project.md` -- regles E01-E15 pre-existantes (.dhsf structure + patterns)
- Toutes les regles sont dispatchees depuis `lint_dhsf()` dans `scripts/lint_diva.py`.
