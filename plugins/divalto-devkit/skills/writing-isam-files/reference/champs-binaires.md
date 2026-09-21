# Champs binaires (`Type: "B"`) -- ecrire une valeur d'octets

> Un champ binaire porte des **octets bruts**, pas du texte. Le pipeline texte du script
> passe par `windows-1252`, qui **n'est pas bijectif** sur les octets `0x80`-`0x9F` : il
> est donc impossible d'exprimer un octet arbitraire par une chaine. D'ou une voie
> dediee (#290).

## Contenu

- Ecrire un champ binaire : hexadecimal
- Ce que le script refuse, et pourquoi
- Champ binaire non fourni : ce qui se passe
- **Le cas `datemc` -- ce qui est mesure et ce qui ne l'est pas**

---

## Ecrire un champ binaire : hexadecimal

La structure declare le champ avec `"Type": "B"` :

```json
{ "Nom": "datemc", "Offset": 123, "Taille": 8, "Type": "B" }
```

La valeur se fournit en **hexadecimal**, exactement `2 x Taille` caracteres :

```json
{
  "Fichier": "...\\gtfdmc.dhfi",
  "Structure": "structure_gtfdmc_ch60.json",
  "Donnees": { "Ce": "2", "Nc": "MONCHOIX", "datemc": "01D9EF910F1F5C9D" }
}
```

C'est la **symetrie exacte de la lecture** : `read_isam.py` rend un champ `Type: "B"`
sous la forme `raw.hex().upper()`. Ce que la lecture rend, l'ecriture le reprend tel quel
-- un aller-retour lecture -> ecriture est donc sans perte.

## Ce que le script refuse, et pourquoi

| Cas | Comportement |
|-----|--------------|
| Caracteres non hexadecimaux | **refus**, avec le nombre de caracteres attendu |
| Longueur differente de `2 x Taille` | **refus** -- jamais de troncature |

La troncature silencieuse est refusee pour la meme raison qu'ailleurs dans le devkit :
une valeur binaire tronquee reste **plausible** (ce sont des octets, rien ne parait
anormal) alors qu'elle est fausse. Mieux vaut un refus explicite qu'un enregistrement
credible et corrompu.

## Champ binaire non fourni : ce qui se passe

`build_record` initialise l'enregistrement a `0x20` (espaces) puis n'ecrit que les champs
fournis. Un champ binaire absent des `Donnees` reste donc **rempli d'espaces** -- ce qui
n'est jamais une valeur binaire legitime.

Le script **ne devine aucune valeur**, mais il **ne se tait pas** : il emet un warning
nommant le champ et la longueur hexadecimale attendue. A l'appelant de decider.

---

## Le cas `datemc` -- ce qui est mesure et ce qui ne l'est pas

Le champ `datemc` (offset 123, 8 octets) des dictionnaires de multichoix est le cas
d'ecole, et il est **instructif de bout en bout**.

### Ce qui est mesure

**C'est un FILETIME, stocke en big-endian.** Decodage des valeurs reelles d'un `gtfdmc`
standard :

| Octets stockes | Lu en big-endian | Lu en little-endian |
|----------------|------------------|---------------------|
| `01D9EF910F1F5C9D` | `2023-09-25 09:17:08` | hors plage |
| `01D7328FC9A13577` | `2021-04-16 07:11:57` | hors plage |

Big-endian donne des dates plausibles, little-endian non. A noter : un `FILETIME` Windows
natif est little-endian **en memoire** -- Divalto le stocke donc a l'envers de la
convention Windows.

**Et 8 espaces donnent l'an 8936.**

### Ce qui N'EST PAS etabli

Le RETEX #290 conclut qu'un `datemc` rempli d'espaces rend l'enregistrement **invisible**
dans l'outil natif « Dictionnaire des Multi-Choix ». Le symptome vecu est fiable (5
entrees inserees, 1 affichee). **La cause ne l'est pas.** Mesure sur un `gtfdmc` standard
de 2 859 enregistrements :

| Constat | Volume |
|---------|--------|
| `datemc` = 8 espaces (`2020202020202020`) | **463 enregistrements** |
| `datemc` = 8 zeros | 166 |
| Multichoix dont **toutes** les entrees ont `datemc` a espaces | **172 sur 880, soit 20 %** |

Ce ne sont pas des restes isoles : ce sont des multichoix entiers, livres par Divalto. Si
un `datemc` a espaces suffisait a rendre un enregistrement invisible, **un cinquieme des
multichoix du standard le serait**.

### Ce qu'on en fait

Le script **ne remplit pas automatiquement** `datemc` avec l'horodatage courant. Inventer
une valeur dans un champ dont on ne sait pas ce qui le lit reviendrait a coder une
supposition -- et la mesure contredit precisement la supposition en question.

Si vous avez besoin d'y mettre une date, fournissez-la : `datemc` en hexadecimal, 16
caracteres, FILETIME big-endian.

> **Le fichier des multichoix ne se compile pas** : c'est un sequentiel indexe. Une valeur
> ecrite dans `datemc` n'est donc pas reecrite par une recompilation du dictionnaire.

---

## Voir aussi

- [isam-api.md](isam-api.md) -- codes retour et primitives de la DLL
- Lecture d'un champ binaire : skill [`reading-isam-files`](../../reading-isam-files/SKILL.md)
- Structure des multichoix : skill [`reading-multichoix`](../../reading-multichoix/SKILL.md)
