# Volets Ywpf -- panneau lateral et page affichee

> Le volet est le **panneau lateral** d'un ecran (typiquement a droite d'une saisie de
> piece), organise en **pages** presentees comme des onglets. Trois mecanismes distincts le
> gouvernent, et les confondre fait perdre du temps : **l'etat du panneau**, **la page
> courante**, et **le reaffichage**.

## Trois mecanismes, trois roles

| Mecanisme | Ce qu'il pilote | Ce qu'il ne pilote PAS |
|---|---|---|
| `Gerer_Volet` | l'**etat du panneau** a l'ouverture -- visible, plie, decalage de languette | **pas** la page affichee |
| `EcrirePageCouranteVolet(<page>)` / `LirePageCouranteVolet()` | la **page courante** memorisee | **pas** l'affichage : ecrire la page courante ne bascule rien |
| `Reafficher_Volet_Spe` | le **reaffichage** de la page courante | **pas** le premier affichage |

C'est de cette repartition que vient le piege : **aucun des trois, seul, ne fait apparaitre
une page donnee a l'ouverture.**

## `Gerer_Volet` rend une chaine d'options HMP

C'est une `Function Char` dont le retour est une chaine balisee -- elle decrit le **panneau**,
pas son contenu :

```diva
public function char Gerer_Volet
beginf
    Freturn('<IsPaneCollapsed><PaneTabOffset>10' & <raccourci>)
endf
```

| Tag | Effet |
|---|---|
| `<IsPaneInvisible>` | volet **desactive** |
| `<IsPaneCollapsed>` | volet ouvert **plie** |
| `<PaneTabOffset>n` | decalage de la languette |

Dans le standard, cette fonction est un `Switch` sur un parametre utilisateur : elle choisit
entre desactiver, ouvrir plie, ou ouvrir « dans le dernier etat connu ». **Y ajouter un
`EcrirePageCouranteVolet` ne peut pas marcher** : on n'est pas dans le bon mecanisme.

## `Reafficher_Volet_Spe` n'est appele qu'au REAFFICHAGE

Le hook standard est livre **vide, avec son exemple en commentaire** -- et cet exemple donne
la sequence exacte :

```diva
public procedure Reafficher_Volet_Spe
; Lors du reaffichage du volet, reaffiche la page courante si specifique
; Il faut positionner la page courante lors de son affichage : <module>.EcrirePageCouranteVolet(Page)
beginp
    ; Exemple
    ;NumPage = LirePageCouranteVolet()
    ;XmeDispv(MZ.MeCle, NumPage, XME_MODE_GOSUB)
    ;XmeRet
endp
```

**Le standard ne route vers ce hook que sur un rafraichissement explicite du volet** --
typiquement un changement de ligne. **Pas au premier affichage.** C'est la raison de fond
pour laquelle les deux approches naturelles echouent.

> `EcrirePageCouranteVolet` vit dans un module **protege** (prefixe `pp`, non livre en
> source). Elle est donc **appelable** -- en la qualifiant du nom de son module, comme le
> fait le commentaire du hook -- mais son corps n'est pas lisible. Voir
> [overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md),
> section `PP` / `TT`.

## Afficher une page donnee PAR DEFAUT a l'ouverture

**Ce qui ne marche pas**, et qui a ete essaye :

1. surcharger `Gerer_Volet` et y appeler `EcrirePageCouranteVolet(<page>)` -- mauvais
   mecanisme, `Gerer_Volet` pilote le panneau ;
2. appeler `EcrirePageCouranteVolet(<page>)` seul dans un hook precoce -- positionner la page
   courante **ne bascule pas** l'affichage, et `Reafficher_Volet_Spe` n'est pas encore
   appele.

**Ce qui marche** : reproduire **la bascule active complete**, c'est-a-dire exactement la
sequence qu'execute un clic sur l'onglet -- dans un hook qui tourne **apres** le premier
affichage du volet, avec un **garde one-shot**.

```diva
Procedure <Hook_appele_apres_le_premier_affichage>
Beginp
    Standard.<Hook_appele_apres_le_premier_affichage>()

    if vBasculeFaite = 0                      ; garde one-shot : SANS elle, on rebascule
        vBasculeFaite = 1                     ; a chaque passage du hook

        <Charger_le_contenu_specifique>       ; alimenter la page avant de l'afficher
        <module>.EcrirePageCouranteVolet(<page>)
        XmeDispv(MZ.MeCle, <page>, XME_MODE_GOSUB)
        XmeRet
    endif
Endp
```

Les quatre points qui comptent :

1. **Un hook post-premier-affichage.** Dans le cas mesure, c'est le hook de fin de
   chargement de la piece -- appele **apres** que le volet a ete affiche une premiere fois.
2. **Le garde one-shot est obligatoire.** Le hook est appele a chaque chargement ; sans
   garde, la bascule se rejoue et reprend la main sur la navigation de l'utilisateur.
3. **Charger avant d'afficher.** La page doit etre alimentee avant le `XmeDispv`, sinon elle
   s'affiche vide.
4. **`EcrirePageCouranteVolet` ET `XmeDispv` -- les deux.** Le premier memorise la page
   courante (ce que `Reafficher_Volet_Spe` relira aux rafraichissements suivants), le second
   **bascule** effectivement l'affichage. L'un sans l'autre ne suffit pas : c'est toute la
   lecon de ce piege.

## Voir aussi

- [dhsf-structure.md](dhsf-structure.md) -- structure d'un masque et de ses pages
- [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md) -- surcharger un masque, `[diva]` / `[diva_base]`
- [overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md) -- `Standard.<proc>()`, modules `PP` proteges
