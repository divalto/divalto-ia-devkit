# Composant `grille_wpf` (et ses `panel_wpf`) -- afficher des pages cote a cote

## Contenu

- Quand utiliser
- Le mecanisme -- `grille_parent` et `[param_panel] page`
- Dimensionner : l'unite de ligne vaut **8**
- Le piege : ajouter un panel sans revoir les hauteurs
- Ce qui n'est PAS etabli
- Anti-patterns

---

## Quand utiliser

Une **grille** (`grille_wpf`) decoupe une zone en lignes et colonnes ; chaque cellule accueille
un **panel** (`panel_wpf`), et **chaque panel affiche une PAGE du meme masque**. C'est le
mecanisme des ecrans « selection en haut, resultat en bas » : deux pages independantes,
affichees simultanement.

Mesure sur le corpus du standard : **338 grilles exploitables, 810 panels**, et une grille en
porte **2 ou 3 dans 92 % des cas** (2 : 154 grilles, 3 : 156).

---

## Le mecanisme -- `grille_parent` et `[param_panel] page`

```
  [grille_wpf]
   [presentation]
    position=<lig>,<col>
    taille=<hauteur>,<largeur>
    id=<idGrille>
    wstyle="STD"
   [param_grille]
    nblig=<n>
    nbcol=<n>
   [lignes_grille]
    [ligne]
     [param_ligne]
      hauteur=<unites>
     [cellules_ligne]
      [cellule] ...

  [panel_wpf]
   [presentation]
    position=<lig>,<col>
    taille=<hauteur>,<largeur>
    id=<idPanel>
    grille_parent=<idGrille>,<ligne>,<colonne>
    wstyle="STD"
   [param_panel]
    page=<numero de page>
```

Deux cles font tout le travail, et elles sont **systematiques -- 810 blocs sur 810** :

| Cle | Ou | Role |
|---|---|---|
| `grille_parent` | `[panel_wpf]` > `[presentation]` | rattache le panel a **une cellule** : `<idGrille>,<ligne>,<colonne>` |
| `page` | `[panel_wpf]` > `[param_panel]` | numero de la **page affichee** dans ce panel |

Le panel n'a pas de contenu propre : **c'est une fenetre ouverte sur une page**.

---

## Dimensionner : l'unite de ligne vaut **8**

Les hauteurs de grille, de ligne et de panel sont en **unites**, alors qu'une page se declare
en **lignes** (`nb_lig`). Le rapport mesure entre les deux :

| | |
|---|---|
| `hauteur_panel / nb_lig` | mediane **8,00** |
| Arrondi a **8** | **683** panels sur 810 |
| Arrondi a 9 | 104 · a 7 : 19 |
| Avec k = 8 | **67 %** au chiffre exact, **87 %** a une ligne pres |

**Ordre de grandeur a retenir : une ligne vaut environ 8 unites de hauteur.**

Et les panels d'une grille n'en occupent pas toute la hauteur : la somme de leurs hauteurs vaut
la hauteur de la grille **moins environ 12 unites** (ecart dominant sur 112 grilles) -- ce qui
correspond a une marge de 6 en haut et 6 en bas.

---

## Le piege : ajouter un panel sans revoir les hauteurs

> **Ajouter un 3e panel dans une grille existante sans recalculer les hauteurs ecrase les
> panels.** C'est un constat de terrain, et il est juste.
>
> **`attache_lgy=oui` ne dispense PAS de l'ajustement.** L'attachement gere le
> redimensionnement de la **fenetre a l'execution** ; il ne fait rien pour la mise en place
> initiale dans la grille.

La demarche : reprendre la hauteur de la grille, retrancher la marge, repartir le reste entre
les lignes (`hauteur=` de chaque `[ligne]`), puis ajuster le `nb_lig` de chaque page de panel
sur la hauteur qui lui revient -- environ un huitieme.

---

## Ce qui n'est PAS etabli

Un retour de terrain enonce que **le total des `nb_lig` des pages de panels doit correspondre a
la hauteur de la grille**. **La mesure ne le confirme pas.** Testee sous plusieurs formes
(unite 8 ou 8,5, avec ou sans la marge de 12), la regle plafonne a **23 % des 336 grilles** a
quatre unites pres. Les ecarts positifs vont jusqu'a **200 unites** : autrement dit, **des pages
sont bien plus hautes que le panel qui les affiche**.

C'est coherent avec ce qu'est un panel -- une **fenetre**, pas un contenant exact : la page peut
deborder et defiler. La formule n'est donc pas ecrite ici, et **aucun controle automatique n'en
decoule** : il signalerait des masques du standard parfaitement valides.

Le detail des mesures est dans [mesures-corpus.json](mesures-corpus.json).

---

## Anti-patterns

| A ne pas faire | Pourquoi |
|---|---|
| Ajouter un panel sans revoir les hauteurs de lignes | les panels s'ecrasent -- constat de terrain |
| Compter sur `attache_lgy=oui` pour l'ajustement initial | il ne gere que le redimensionnement a l'execution |
| Deduire `nb_lig` d'une formule sur la hauteur de grille | la regle ne se verifie pas : 23 % au mieux |
| Oublier `grille_parent` sur un panel | rien ne le rattache a une cellule |

---

## Voir aussi

- [dhsf-structure.md](dhsf-structure.md) -- les sections d'un masque, la chaine des pages
- [normes-graphiques.md](normes-graphiques.md) -- espacements et formules de placement
- [mesures-corpus.json](mesures-corpus.json) -- le releve date des mesures citees ici
