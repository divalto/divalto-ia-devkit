# Ajouter un champ a une table existante

> Le reste du skill couvre la **creation d'une table complete** (5 zones) et l'ajout d'un
> champ a une table **standard par surcharge**. Cette page couvre le cas intermediaire, le
> plus courant au quotidien : **ajouter un champ a une table qui existe deja dans votre
> propre dictionnaire**.

## Contenu

- Les 5 lignes obligatoires d'un bloc `[CHAMP]`
- Ou inserer le champ : en fin de table ou au milieu
- **Decider si une synchronisation SQL est necessaire**
- Cas de la table sans `[BASE]` (structure de travail)

---

## Les 5 lignes obligatoires d'un bloc `[CHAMP]`

Mesure sur un dictionnaire specifique reel de **359 blocs `[CHAMP]`** :

| Ligne | Presence mesuree | Statut |
|-------|------------------|--------|
| `Version=` | **359 / 359** | obligatoire |
| `Nom=` | **359 / 359** | obligatoire |
| `Gel=` | **359 / 359** | obligatoire |
| `Nature=` | **359 / 359** | obligatoire |
| `Flags=` | **359 / 359** | obligatoire |
| `DateM=` | 124 / 359 | **facultatif** |
| `NomOdbc=` | 47 / 359 | **facultatif** (utile si le nom SQL differe du nom DIVA) |

```ini
[CHAMP]
Version=1,{timestamp},{login_diva},{timestamp},{login_diva}
Nom={NomChamp},{Description},1
Gel=3
Nature={code}
Flags=o,1,n,n,n,n,n,n,n
```

**`DateM` n'est pas requis pour un nouveau champ** : deux tiers des champs mesures n'en ont
pas. Ne pas en inventer un -- un `DateM` arbitraire est un anti-pattern dans les blocs ou il
compte (cf. [dhsd-anti-patterns.md](dhsd-anti-patterns.md), DICT14).

Le `{login_diva}` est celui du developpeur, sur 20 caracteres. `generate_dhsd_block.py`
l'exige (`--user`) et ne l'invente pas.

---

## Ou inserer le champ : en fin de table ou au milieu

Un champ occupe deux endroits : sa **declaration** globale `[CHAMP]` et sa **ligne de
placement** dans le `[CHAMPS]` de la table. C'est le placement qui decide de l'ampleur du
travail.

| Cas | Consequence | Ce qu'il faut faire |
|-----|-------------|---------------------|
| **En fin de table**, avant `Filler` / container `U` s'ils existent | rien ne se decale en amont | ajouter la ligne, augmenter `Taille=` du nombre d'octets du champ |
| **En fin de table, en consommant le `Filler`** | rien ne se decale, `Taille=` **inchangee** | reduire le `Filler` d'autant (cf. `modify_field_nature.py --filler-policy cannibalize`) |
| **Au milieu** | **tous** les champs en aval se decalent, dans la table **et** dans chaque `[INDEX]` qui les utilise | ne pas le faire a la main -- voir ci-dessous |

> **Une insertion au milieu n'est jamais un ajout local.** Les positions sont cumulatives et
> sans trou : decaler un champ decale toute la suite, y compris les offsets cumules des
> index. `modify_field_nature.py` automatise ce recalcul pour un **changement de Nature** ;
> pour une insertion, la voie sure est de placer le champ **en fin**.

Apres modification, valider : `DICT01` (chevauchement) et `DICT02` (trou) sont les deux regles qui
attrapent un recalcul casse.

```
py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
    --path "chemin/dictionnaire.dhsd" --table MaTable
```

> **Ne jamais editer un `.dhsd` avec un script maison.** Python en mode texte convertit les
> CRLF en LF **a la lecture**, et la reecriture produit un fichier LF pur -- corruption
> silencieuse que `DICT06` detecte apres coup. Passer par les scripts de ce skill ou par le
> skill [`writing-diva-files`](../../writing-diva-files/SKILL.md). Detail des pieges :
> `writing-diva-files/reference/safe-methods.md`.

---

## Decider si une synchronisation SQL est necessaire

C'est l'etape la plus facile a oublier, et son omission ne se voit **pas** au dictionnaire :
la colonne existe au dico, mais **pas physiquement en base** -- l'erreur arrive a la
premiere ecriture, en runtime.

**Le critere est : la table est-elle rattachee a une base ?** Autrement dit, son nom
figure-t-il dans le `[TABLES]` d'un bloc `[BASE]` du dictionnaire ?

| La table... | Persistee ? | Apres l'ajout de champ |
|-------------|-------------|------------------------|
| figure dans le `[TABLES]` d'une `[BASE]` | **oui** | dictionnaire -> **compilation** -> **synchronisation SQL** obligatoire |
| ne figure dans aucun `[TABLES]` | **non** (structure de travail / affichage, en memoire) | dictionnaire -> compilation. **Aucune synchro.** |

Ce n'est pas un cas marginal : sur un dictionnaire specifique reel de 103 tables,
**26 (25 %) ne sont rattachees a aucune base**.

> **`NomOdbc` n'est PAS le critere.** Il ne dit que le nom SQL a utiliser si le nom DIVA ne
> convient pas, il est facultatif (47 champs sur 359 mesures) et son absence ne signifie pas
> qu'une table n'est pas persistee. Seul le rattachement a une `[BASE]` tranche.

Pour la synchronisation elle-meme, suivre le skill
[`syncing-diva-sql`](../../syncing-diva-sql/SKILL.md) -- il exige une compilation buildall a
**0 erreur** au prealable, sans quoi la synchro travaille sur des objets incoherents.

---

## Cas de la table sans `[BASE]` (structure de travail)

Une table de travail, d'arbre ou d'affichage n'a ni `[BASE]` ni `[INDEX]` ni ligne
`[INDEXL]` : elle n'existe qu'en memoire a l'execution. Y ajouter un champ se limite donc a
deux gestes -- le bloc `[CHAMP]` global et la ligne de placement -- suivis d'une
recompilation. Pas de base, pas d'index a recalculer, pas de synchro SQL.

**Attention toutefois** : ces tables sont souvent celles qui **embarquent l'enregistrement
d'une autre table** via `TableInsere=`. Dans ce cas la fenetre reservee est figee, et vos
champs propres commencent **apres** elle -- voir
[dhsd-5-zones.md](dhsd-5-zones.md), section « `TableInsere=` -- embarquer une table dans une
autre ».
