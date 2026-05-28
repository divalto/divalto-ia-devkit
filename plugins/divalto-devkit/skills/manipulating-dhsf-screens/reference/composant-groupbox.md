# Composant `groupbox` -- cadre decoratif avec en-tete

## Contenu

- Quand utiliser
- Grammaire
- Les 3 couleurs canoniques
- Imbrication et marges visuelles
- Comportement runtime au focus
- Z-order -- regle critique de l'ordre dans le source
- Anti-patterns

---

## Quand utiliser

`groupbox` est le composant **decoratif d'organisation visuelle** d'un masque -- un cadre avec en-tete centre qui regroupe des composants traitant du meme sujet (ex: "Identifiants", "Creation", "Coordonnees"). C'est le composant graphique le plus utilise (~84% des masques en ont).

Distinct du `cadre` (cf. [composant-cadre.md](composant-cadre.md)) qui est purement decoratif sans titre et sans fonction de groupement logique.

---

## Grammaire

```ini
[groupbox]
[presentation]                ; obligatoire
position=Y,X
taille=H,L                    ; doit englober les enfants
id=N                          ; >= 1000001 en surcharge
wstyle="GROUPE"               ; police titre Tahoma 8 gras (quasi-unique a 99.8%)
[param_groupbox]              ; obligatoire
texte="Création"              ; titre, centre automatiquement dans l'en-tete
couleur_fond="GROUPE_FOND"    ; couleur du corps (zone enfants)
```

8 lignes minimum pour un groupbox complet. **Pas de `[description]`, pas de `[param_saisie]`, pas de hooks DIVA** -- le composant est purement decoratif.

---

## Les 3 couleurs canoniques

| `couleur_fond` | RGB | Convention canonique |
|----------------|-----|----------------------|
| `GROUPE_FOND` | 237,237,237 (gris clair) | **Groupbox de niveau 1** -- groupe principal sur une page standard |
| `SOUS_GROUPE_FOND` | 222,222,222 (gris plus fonce) | **Groupbox imbrique** -- sous-section logique a l'interieur d'un groupbox parent. **Doit etre geometriquement contenu** dans un parent |
| `ZOOM` | 255,255,255 (blanc) | **Page 3 mode liste des zooms** -- contexte specifique, typiquement avec `texte="Selection"` |

Les autres couleurs marginales observees (`BLANC`, `STD`, `GROUPE_FONCE`, `GROUPE_FOND_TITRE`) n'ont **pas de convention claire** et sont a eviter.

> **Convention validee empiriquement** : 81% des `SOUS_GROUPE_FOND` du standard sont effectivement contenus geometriquement dans un groupbox parent. Les 19% restants sont identifies comme **erreurs de design dans le standard** (cas concret : `gtez135_sql.dhsf` "Selection des articles a collecter").

---

## Imbrication et marges visuelles

Pour que l'imbrication soit **visible a l'oeil**, le sous-groupbox doit avoir des **marges laterales et verticales** par rapport au parent. Convention canonique : **~10 orteils de marge** lateralement et en bas, **~50+ orteils de marge en haut** (pour laisser de la place aux composants enfants directs du parent).

Exemple verifie empiriquement sur `gtez047_sqlu.dhsf` page 12 :

| Groupbox | Y..Y+H | X..X+L |
|----------|--------|--------|
| "Complements" (parent, `GROUPE_FOND`) | 103..156 | 5..138 |
| "Indicateurs" (sous-groupe, `SOUS_GROUPE_FOND`) | 160..188 | 15..128 |
| Marges effectives | top=57, bottom=10 | left=10, right=10 |

Combine avec `couleur_fond=SOUS_GROUPE_FOND`, la hierarchie est clairement visible au repos.

> **Anti-pattern** : imbriquer un sous-groupbox avec EXACTEMENT la meme largeur que le parent. Geometriquement valide mais **visuellement invisible** -- les deux cadres paraissent cote-a-cote ou empiles plutot qu'imbriques.

---

## Comportement runtime au focus

Le groupbox a un **comportement runtime natif Ywpf** qui met en evidence le groupe quand son contenu est en saisie active :

| Etat | Effet visuel |
|------|--------------|
| Focus de navigation (tab/click sans edition) | En-tete en teinte bleu-gris **subtile** |
| Saisie active (curseur dans un champ, edition) | **Cadre complet + en-tete** en orange/cuivre **marque** (couleur themee) |

Avec imbrication, le mecanisme surligne **toute la chaine hierarchique** des groupbox englobants simultanement. Les sous-groupes freres non concernes restent neutres.

Couleur de surbrillance depend du theme utilisateur (parametrable, pas hard-code). Gere nativement par Ywpf -- aucune propriete DIVA a configurer.

---

## Z-order -- regle critique de l'ordre dans le source

**L'ordre des blocs dans le source `.dhsf` determine l'ordre de dessin runtime (z-order)** :

- Premier bloc declare = dessine en arriere-plan
- Dernier bloc declare = dessine au premier plan (recouvre les precedents)

**Regle absolue** : un groupbox qui englobe des composants doit etre declare **AVANT** ces composants dans le source.

```ini
; CORRECT
[groupbox]                         ; <-- declare en premier
[presentation]
position=10,5
taille=100,130
[param_groupbox]
texte="Coordonnees"
couleur_fond="GROUPE_FOND"

[obj_texte]                        ; <-- libelles ENSUITE
...
[champ]                            ; <-- champs ENSUITE
...
```

Si le groupbox est declare APRES ses enfants, il est dessine par-dessus et **masque les enfants au runtime** -- rendu casse.

**Pattern canonique du standard X.13** : tous les groupbox apparaissent EN TETE de leur page, avant les `obj_texte`/`champ` qu'ils englobent.

> **Cas particulier** : un groupbox qui englobe des composants declares APRES lui dans le source n'a PAS besoin d'etre deplace -- l'ordre est deja correct. Si on insere un nouveau groupbox autour de composants existants, le placer EN AMONT des composants concernes dans le fichier.

---

## Pilotage dynamique

~16% des groupbox declarent un `noms=` pour pilotage runtime via `XmeSetAttribut` (ex: cacher/afficher tout un bloc selon le profil utilisateur). Voir [xmesetattribut-dynamique.md](xmesetattribut-dynamique.md) -- attribut typique : `AN_VISIBILITE`.

---

## Anti-patterns

1. **Declarer un groupbox APRES les composants qu'il englobe** -- z-order incorrect, enfants masques au runtime.
2. **Utiliser `SOUS_GROUPE_FOND` sans imbrication geometrique** dans un groupbox parent -- 18% du corpus mais identifies comme erreurs de design.
3. **Utiliser `ZOOM` hors page 3 mode liste** -- pattern canonique 98% sur page 3 avec texte "Selection". Hors contexte = erreur ou cas tres specifique.
4. **Inventer une autre `couleur_fond`** que les 3 canoniques -- les variantes marginales n'ont pas de convention claire.
5. **Mettre un wstyle `Type 7` compose avec couleur de fond** sur un groupbox -- le wstyle ne doit definir que la police titre. La couleur du corps passe par `couleur_fond=`.
6. **Ajouter `[description]`, `[param_saisie]`, `[touches]`, `[traitements]` sur un groupbox** -- composant purement decoratif. 0 occurrence corpus. Pour pilotage dynamique, utiliser `XmeSetAttribut` + `noms`.
7. **Imbriquer un sous-groupbox avec EXACTEMENT la meme largeur que le parent** -- imbrication invisible visuellement. Ajouter ~10 orteils de marge lateralement.
8. **`taille=H,L` trop petite pour englober les enfants** -- enfants en debordement, rendu visuellement casse.
