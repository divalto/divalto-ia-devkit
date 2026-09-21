# Composant `rich_edit` -- champ de saisie texte multiligne

## Contenu

- Quand utiliser
- Grammaire
- `[param_rich_edit]` -- les 4 cles
- Les `wstyle` reellement employes
- Ce que la mesure dit, et ce qu'elle ne dit pas
- Anti-patterns

---

## Quand utiliser

`rich_edit` est le composant de **saisie de texte multiligne** d'un masque : commentaire libre,
note, description longue.

> **Un `[champ]` ne fait pas de multiligne**, meme avec une grande hauteur. C'est le constat
> qui a motive cette page -- rapporte par un partenaire, **non reverifie ici** : le workspace
> n'a pas de compilateur.

C'est le **7e type de composant** de ce skill, apres `obj_texte`, `champ`, `groupbox`, `cadre`,
`bitmap_constante` et `bitmap_variable`.

---

## Grammaire

Le bloc `[rich_edit]` se declare directement sous une `[page]`, comme les autres composants.

```
  [rich_edit]
   [presentation]
    position=<lig>,<col>
    taille=<hauteur>,<largeur>
    id=<id>
    wstyle="<style>"
   [description]
    donnee=<enregistrement>,<champ>
   [param_rich_edit]
    largeur=<n>
```

Quatre sections seulement sont **systematiques** -- presentes dans les **355** blocs du
standard :

| Section | Cles systematiques | Cles optionnelles observees |
|---|---|---|
| `[presentation]` | `position`, `taille`, `id`, `wstyle` | `noms`, `attache_lgx`, `attache_lgy` |
| `[description]` | `donnee` | `saisie`, `minmaj` |
| `[param_rich_edit]` | **`largeur`** | `entree_saisie_clav`, `format`, `mode_ecriture` |

Les sections communes a tous les composants -- `[touches]`, `[traitements]`, `[aide_page]`,
`[info_bulle]` -- s'utilisent normalement.

---

## `[param_rich_edit]` -- les 4 cles

| Cle | Occurrences | Remarque |
|---|---|---|
| `largeur` | **355 / 355** | **obligatoire en pratique** : aucun `[rich_edit]` du standard ne s'en passe |
| `entree_saisie_clav` | 74 | |
| `format` | 46 | |
| `mode_ecriture` | 24 | |

Aucune autre cle n'apparait dans ce bloc sur l'ensemble du corpus.

---

## Les `wstyle` reellement employes

| `wstyle` | Occurrences |
|---|---|
| `CHAMP_NON_SAISI` | **126** |
| `STD` | **105** |
| `CHAMP_SAISI` | **85** |
| `RTF_NOTE` | 28 |
| `CHAMP_AFF` | 9 |
| `CHAMP_TPV_AFF` | 1 |
| `CHAMP_TPV_NON_SAISI` | 1 |

> **Correction d'une idee recue.** `RTF_NOTE` est souvent presente comme *le* style du
> `rich_edit`. Il est le **quatrieme** en frequence. Les trois dominants sont
> `CHAMP_NON_SAISI`, `STD` et `CHAMP_SAISI` -- c'est-a-dire les memes styles que les autres
> composants de saisie. Choisir le style selon que le champ est saisissable ou non, pas par
> habitude.

---

## Ce que la mesure dit, et ce qu'elle ne dit pas

**Mesure** : **355 blocs `[rich_edit]` dans 166 masques** d'un pack standard X.13. Toutes les
frequences de cette page en viennent, et elles sont consignees dans
[mesures-corpus.json](mesures-corpus.json).

**Ce qui n'est PAS etabli** : la semantique de `largeur` dans `[param_rich_edit]` -- elle
coexiste avec le `taille=<hauteur>,<largeur>` de `[presentation]`, et rien dans le corpus ne
dit ce qui les distingue. Interroger le graphe de connaissance avant d'en faire une regle.

---

## Anti-patterns

| A ne pas faire | Pourquoi |
|---|---|
| Utiliser un `[champ]` avec une grande hauteur pour du multiligne | le composant ne le supporte pas ; c'est `rich_edit` qu'il faut |
| Ecrire `wstyle="RTF_NOTE"` par defaut | c'est le 4e style en frequence, pas la norme |
| Omettre `largeur` dans `[param_rich_edit]` | aucun `[rich_edit]` du standard ne le fait |

---

## Voir aussi

- [dhsf-structure.md](dhsf-structure.md) -- les sections d'un masque et les regles de grammaire
- [composant-champ.md](composant-champ.md) -- le champ ordinaire, mono-ligne
- [mesures-corpus.json](mesures-corpus.json) -- le releve date de toutes les mesures citees ici
