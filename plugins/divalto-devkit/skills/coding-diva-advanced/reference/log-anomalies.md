# Journal des anomalies -- `*_Log_Ano`

Ecrire dans le **livre de bord** (table SQL `M8`, entite `LIVREDEBORD`) depuis du code DIVA.

## La regle : le premier parametre est un NUMERO DE MESSAGE

```diva
G3_Log_Ano(<NumErr>, '<texte>' [, applic = '<APPLIC>'])
```

`<NumErr>` est une **cle dans le fichier des messages du domaine** (`XXferr`), pas une donnee
metier.

> **Ce n'est JAMAIS `MZ.Dos`, ni aucune variable de contexte metier.**
>
> ```diva
> ; FAUX -- compile, et pollue le livre de bord
> G3_Log_Ano(MZ.Dos, 'Traitement termine', applic = 'MON_APPLIC')
>
> ; JUSTE -- 9999 = message libre
> G3_Log_Ano(9999, 'Traitement termine', applic = 'MON_APPLIC')
> ```
>
> L'erreur **compile sans un message** : le numero de dossier part comme code d'erreur, et le
> livre de bord se remplit de codes qui n'en sont pas. Le defaut ne se voit qu'en relisant le
> journal, longtemps apres.

## Une fonction par domaine

Le prefixe suit le domaine, comme les enregistrements de contexte :

| Fonction | Domaine | Fichier de messages |
|---|---|---|
| `G3_Log_Ano` | gestion commerciale | `gtferr` |
| `A5_Log_Ano` | socle | `a5ferr` |
| `C3_Log_Ano` | comptabilite | `ccferr` |
| `R3_Log_Ano` | reglements | `rcferr` |

## `9999` : pourquoi c'est la valeur du texte libre

Ce n'est pas une convention arbitraire -- **c'est une entree concue pour ca**. Le libelle
stocke pour le code `9999` est **`$1`** : un pur passe-plat. Le message affiche **est** le
parametre passe a l'appel, sans rien autour.

Un code catalogue ordinaire, lui, porte un vrai libelle avec ses substitutions -- par exemple
`9000` vaut `Fichier $2 absent`. Passer `9000` avec un texte n'ecrit donc **pas** ce texte.

### Deux pieges mesures

**1. Le socle prefixe.** Le `9999` de `a5ferr` ne vaut pas `$1` mais **`Erreur $1`**.

```diva
A5_Log_Ano(9999, 'Traitement termine')   ; ecrit "Erreur Traitement termine"
```

Sur les 11 fichiers de messages qui portent `9999`, **10 valent exactement `$1`** ; `a5ferr`
est le seul a prefixer. Si le libelle compte, verifier avant d'ecrire.

**2. `9999` n'existe pas partout.** Sur les **13** fichiers de messages d'un pack standard
recent, **2 ne portent pas `9999`**. La convention n'est donc pas universelle d'un domaine a
l'autre. Les quatre domaines du tableau ci-dessus, eux, la portent tous.

### Verifier un code avant de l'ecrire

C'est le role du skill **`managing-diva-error-messages`** -- il lit le `XXferr` et rend le
libelle :

```bash
py <skill>/scripts/manage_error_messages.py \
   --file <objets>/gtferr.dhfi \
   --read-isam-script <skills>/reading-isam-files/scripts/read_isam.py \
   --check 9999
```

La reponse donne `found` **et** `message` -- c'est le libelle qui dit ce que l'appel produira
reellement.

## Niveaux de preuve

| Affirmation | Etabli comment |
|---|---|
| `9999` porte le libelle `$1`, `9000` porte `Fichier $2 absent` | **mesure** sur les fichiers de messages d'un pack standard, 2026-08-30 |
| `9999` present dans 11 des 13 fichiers, `a5ferr` prefixe | **mesure**, meme date |
| Le 1er parametre est un numero, le 2e un texte | **corrobore** par un appel de production releve chez un partenaire lors d'un autre retour |
| Le nom `applic` du parametre nomme, et la liste complete des parametres | **NON verifie** -- vient du retour partenaire seul. Interroger le graphe. |

## Voir aussi

- `managing-diva-error-messages` -- lire, verifier et gerer les codes des `XXferr`
- `assisting-functional-question` -- ou atterrit le journal (table `M8`, `LIVREDEBORD`)
- [keywords-verifies.json](keywords-verifies.json) -- le releve date et ses reserves
