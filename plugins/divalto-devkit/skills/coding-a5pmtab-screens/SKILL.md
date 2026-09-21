---
name: coding-a5pmtab-screens
description: >
  Ecrans specifiques a tableaux A5PMTAB : callbacks DefProcInterro_* / DefProcSaisie_*,
  invocation par Creer_Parametre + AP_Interroger_Tableaux / AP_Saisir_Tableaux, options HMP,
  ecrans multi-tableaux et tableaux imbriques.
  A consulter des qu'un developpement met en jeu un tableau A5PMTAB -- et IMPERATIVEMENT
  avant d'ecrire ou de modifier la signature d'une callback : les ecarts de declaration
  COMPILENT et cassent a l'execution sans aucun message (tableau fige, selection de ligne
  perdue, boucle infinie).
---

# coding-a5pmtab-screens

Les ecrans a tableaux **A5PMTAB** sont massivement utilises dans le standard -- **7 663
callbacks declarees dans 661 programmes**. Ils n'avaient aucune reference dans ce devkit,
alors que les Zoom SQL en ont une complete. Un partenaire a paye ce manque d'une vingtaine
d'iterations de compilation et de plusieurs heures de recherche a la main.

## Contenu

| # | Sujet | Reference |
|---|---|---|
| 1 | Les callbacks, la **regle du suffixe**, le catalogue complet | [callbacks-catalogue.md](reference/callbacks-catalogue.md) |
| 2 | Declarer les modules, `Creer_Parametre`, `AP_*_Tableaux`, les options HMP | [invocation.md](reference/invocation.md) |
| 3 | **Les pieges qui compilent** et cassent au runtime | [pieges-execution.md](reference/pieges-execution.md) |
| -- | Le releve date des verifications, ses sources et ses limites | [keywords-verifies.json](reference/keywords-verifies.json) |

---

## Ce qu'il faut savoir avant d'ecrire une ligne

### A5PMTAB est un moteur : il appelle votre code

Apres `AP_Interroger_Tableaux(...)` (ou `AP_Saisir_Tableaux(...)`), **vous n'ecrivez plus le
flux** -- le standard commente cette ligne « *Passage de relai au tableau* ». A5PMTAB prend
le controle et appelle vos callbacks aux moments prevus.

**Elles sont optionnelles** : un ecran du standard confie un tableau en saisie sans en
declarer **aucune**, et le moteur tourne sur ses defauts. Et **le retour de `AP_*_Tableaux`
dit quelle callback a mis fin au tableau** -- 1 abandon, 2 validation, 3 apres, 4 arret
specifique.

### La valeur de retour d'une callback : `0` = « je gere », `1` = « laisse faire »

**C'est le fait le plus couteux a ignorer de tout A5PMTAB**, et il ne provoque aucune erreur.

| Retour | Pour A5PMTAB |
|---|---|
| **`0`** | « je gere cet evenement moi-meme -- **ne fais rien de plus** », navigation et sortie standard **comprises** |
| **`1`** | « je ne gere pas -- **laisse A5PMTAB faire son traitement normal** » |

**`1` est le repli de fin de fonction.** On ne met `0` que dans les branches ou l'on se
substitue vraiment au moteur. Le squelette livre retourne `0` parce que c'est un **stub**,
pas un defaut fonctionnel : corps vide plus « je gere moi-meme » = tableau fige.

### `Fperso` decide de la forme des callbacks appelees

| Ouverture du tableau | Forme appelee | 1er parametre |
|---|---|---|
| `Creer_Parametre(..., Fperso = <vrai>, Nom = '<X>')` | `DefProcInterro_<X>_Apres` | **aucun `Id`** |
| `Creer_Parametre(...)` sans `Fperso` | `DefProcInterro_Apres` | **`&Id`** |

**Le suffixe ne s'invente pas : c'est la valeur passee dans `Nom=`.** Ce n'est pas le nombre
de tableaux qui commande -- c'est `Fperso`, tableau par tableau. C'est la cause du message
*« la fonction attend 0 parametre(s) et l'appelant a place 1 parametre(s) sur la pile »*.

Un ecran du standard porte **les deux formes cote a cote** : tableau principal sans `Perso`,
tableau imbrique avec `Fperso` et `Nom='Detail'`.

### Le fichier de prototypes se trompe sur `Id`

`objet/proto_a5pmtab.dhsp` ecrit `DefProcInterro_Apres(Id)`, **sans esperluette**, sur ses
**90** callbacks non suffixees. **`Id` est passe par adresse** : la forme correcte est
`(&Id)`, celle des extraits de code et des ecrans du standard.

Utiliser le prototype pour la **liste** des callbacks et leur **nombre** de parametres --
**pas** pour leur mode de passage.

### Les faux amis de declaration : `1A` n'est pas un pointeur

`1A` est le **niveau 1 avec forçage d'alignement** sur adresse paire, pas un type adresse.
Sur un parametre de callback, **reproduire exactement le niveau du prototype**. Ajouter `A`
« comme la ligne du dessus » corrompt la memoire a l'execution, sans une erreur.

---

## Les cinq pieges, et ce qu'ils donnent a voir

Aucun ne produit d'erreur de compilation. Aucun ne produit de message a l'execution.

| Piege | Ce que vous observez |
|---|---|
| Suffixe / nombre de parametres | erreur d'appel, ou tableau inerte |
| `Id` sans `&` | comportement casse, sans message |
| `1A` sur un parametre | **selection de ligne perdue** |
| retour `0` en repli au lieu de `1` | **tableau entierement fige** |
| drapeau de reprise non reinitialise a chaque sortie | **boucle infinie** au 2e aller-retour |

**Reflexe de diagnostic** : un tableau qui se comporte mal **sans message** -> soupconner
d'abord la **declaration d'une callback**. Jamais les options d'affichage : un partenaire a
bascule `<Selection>` dans les deux sens parmi une douzaine de tentatives infructueuses,
la cause etant une callback mal declaree.

Detail des cinq : [pieges-execution.md](reference/pieges-execution.md).

---

## Ce que ce skill ne pretend pas

### Deux points encore ouverts

Ecrits comme tels dans le releve plutot que tranches en silence :

1. **Le mecanisme de la corruption par `1A`.** Que la casse vienne precisement du decalage
   d'implantation induit par l'alignement est une **deduction**, pas une demonstration. Ce
   qui est etabli : `A` est un modificateur d'alignement, et le mettre la ou le prototype ne
   le met pas casse a l'execution.
2. **Comment A5PMTAB resout ses callbacks.** Rien ne les enregistre -- contraste avec les
   fonctions `Collate` des RecordSql, qui recoivent les noms de procedures en chaine.

### Ce que ce skill ne couvre pas ENCORE

Demandes des RETEX volontairement differees, listees dans le releve sous `differe_declare`
pour qu'on ne croie pas ce skill complet :

- le **squelette complet** d'un ecran mono-tableau, `Main` compris ;
- le **critere `Interro` vs `Saisie`** -- privilege Consultation d'un cote, Modification /
  Suppression de l'autre, une meme table pouvant avoir les deux selon le contexte d'appel ;
- le motif **« selection + tableau simultanes »** par empilement de pages, et le partage avec
  `grille_wpf` / `panel_wpf` pour les tableaux cote a cote ;
- le **mecanisme de retour vers la selection** ;
- la **regle de lint** demandee pour le piege `1A` : sa faisabilite n'a pas ete mesuree. Le
  RETEX offre lui-meme le repli -- documenter -- et c'est ce que ce lot a pris.

---

## Sources

- **`objet/proto_a5pmtab.dhsp`** -- le fichier de prototypes livre : **188 declarations**
  pour **180 noms distincts**, 90 suffixees / 90 non suffixees. Autoritaire pour la liste et le nombre de parametres.
- **`A5/source/ExtraitsErp/divalto_a5pmtab_*.dhsp`** -- 34 extraits de code, 45 routines,
  aucune protegee. Autoritaires pour les **corps** et le **mode de passage**.
- **Un ecran du standard livre**, lu en entier, pour l'invocation et les options.
- Mesures sur le corpus du standard X.13, consignees dans
  [keywords-verifies.json](reference/keywords-verifies.json).
