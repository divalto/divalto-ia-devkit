# Erreurs de compilation courantes

## Format du rapport

**Deux formats reels**, selon l'action :

- **`build` incrementale** : le rapport n'a **PAS** de ligne francaise `Erreur(s)=`. Le compte
  d'erreurs est porte par l'en-tete **`[TOTAL_ERRORS]N`**, accompagne de lignes
  `[INFO]` / `[WARNING]` / `[ERROR]`. C'est le format le plus courant.
- **`buildall` complet** : idem, **plus** la ligne de resume francaise ci-dessous.

`[TOTAL_ERRORS]` est donc un resume de **1re classe** : ne jamais conclure "rapport illisible"
au motif qu'il manque `Erreur(s)=`.

Ligne de resume du `buildall` :

```
Erreur(s)=0   Warning(s)=0   Diva=42   Masques=5   Dictionnaires=3   Sql=8   Objets proteges=0
Duree=0:01:23
```

| Champ | Signification |
|-------|---------------|
| `Erreur(s)=` | Nombre d'erreurs (0 = succes) |
| `Warning(s)=` | Nombre de warnings |
| `Diva=` | Fichiers source DIVA compiles |
| `Masques=` | Masques ecran compiles |
| `Dictionnaires=` | Dictionnaires compiles |
| `Sql=` | RecordSql compiles |
| `Objets proteges=` | Objets proteges compiles |
| `Duree=` | Temps total (format H:M:S) |

---

## Extraction des erreurs

**Passer par `scripts/parse_compilation.py`** : il applique la regle de verdict complete et
extrait les erreurs avec leur fichier source. Les recettes manuelles ci-dessous sont donnees
pour comprendre le format, pas pour remplacer le script.

Deux pieges du format reel, que le script traite deja :

1. **Les lignes `[WARNING]` / `[INFO]` / `[TOTAL_ERRORS]` ne sont pas des erreurs**, meme
   quand leur texte contient le mot "erreur" (ex. un warning "risque d'erreur"). Un pattern
   qui ne les exclut pas produit de faux positifs et fausse le verdict.
2. **Le fichier source n'est PAS systematiquement sur la ligne precedente.** Il apparait
   selon les cas sur la ligne d'erreur elle-meme (`[ERROR]/chemin/monfichier.dhsp (7) ...`),
   sur la ligne **suivante** (continuation `Fichier:... Ligne:N`), ou seulement dans le
   contexte precedent. Une extraction `-Context 1,0` attribue donc l'erreur au mauvais
   fichier des qu'il y a deux erreurs consecutives.

La ligne de continuation `Fichier:... Erreur numero N` **decrit** l'erreur precedente : elle
ne compte pas comme une erreur supplementaire.

---

## Erreurs courantes et solutions

### Profil absent du projet

**Symptome** : xwin7 ne trouve pas le profil dans le .dhpt
**Cause** : encodage du nom de profil (`développement`) en UTF-8 au lieu d'ISO-8859-1
**Solution** : encoder le script .ps1 en ISO-8859-1 (voir reference/xwin7-syntax.md)

### Fichier source introuvable

**Symptome** : `Erreur : fichier "xxx.dhsp" introuvable`
**Cause** : fichier reference dans [fichiers] du .dhps mais absent du repertoire source
**Solution** : verifier que le fichier existe, ou le retirer du .dhps

### Erreur de syntaxe DIVA

**Symptome** : `Erreur de syntaxe` avec numero de ligne
**Cause** : code DIVA invalide (variable non declaree, procedure manquante, etc.)
**Solution** : corriger le code source a la ligne indiquee

### `Erreur 99 : Mot inconnu : <NOM>` -- trois causes distinctes

**Symptome** : `[ERROR]/chemin/monfichier.dhsp (7) Erreur 99 : Mot inconnu : <NOM>`

Le compilateur dit qu'un identifiant ne resout pas. Il ne dit pas **pourquoi**. Trois causes,
dans l'ordre ou il faut les eliminer :

| # | Cause | Indice | Correctif |
|---|---|---|---|
| 1 | **Environnement / implicite actif** ne correspondant pas au projet | erreurs « Module absent » **en cascade**, sur des fichiers qui **existent** | valider l'implicite AVANT de compiler (cf. `understanding-integrator-workspace`) -- ne rien toucher au source |
| 2 | **Declaration `Module` manquante** pour une fonction publique | `<NOM>` est une `Public Function` / `Public Procedure` portee par un autre module | ajouter `Module "<le module qui la DEFINIT>.dhop"` dans **votre** source |
| 3 | **Enregistrement non declare localement** | `<NOM>` est un enregistrement (`G3XZ`, `Zoom`, `RowInfo`...) | le declarer chez vous : `Public Record '<dico>.dhsd' <TYPE> <NOM>` |

**Ne jamais confondre 2 et 3.** Declarer le module ne fera **jamais** apparaitre un
enregistrement : `Module` n'apporte que des fonctions et des procedures, et il n'est **pas
transitif** -- declarer un module A qui depend de B ne donne aucun acces aux publiques de B.
Le detail des deux mecanismes est dans le skill `coding-diva-advanced`
(`reference/overwrite-pattern.md`).

**Piege de la cause 2** : le module manquant n'est pas toujours greppable. Certaines familles
de helpers generes vivent dans un module **compile** dont la source n'est pas livree -- la
recherche textuelle dans les sources ne trouve rien, alors que c'est bien une declaration
`Module` qui manque, pas un nom mal orthographie.

### Erreur de compilation masque (.dhsf)

**Symptome** : erreur dans un fichier .dhsf
**Cause** : element graphique mal configure, reference de champ inexistant
**Solution** : verifier la structure du masque (cf. le skill manipulating-dhsf-screens)

### Erreur de compilation dictionnaire (.dhsd)

**Symptome** : erreur dans un fichier .dhsd
**Cause** : trou de position, champ non declare, section mal fermee (D01-D11)
**Solution** : valider avec managing-diva-dictionaries

### Erreur de compilation RecordSql (.dhsq)

**Symptome** : erreur dans un fichier .dhsq
**Cause** : colonne inexistante, table inexistante, syntaxe SQL invalide
**Solution** : verifier le RecordSql (voir generating-recordsql)

---

## Prerequis avant compilation

1. `C:\divalto\sys\xwin7.exe` accessible
2. Fichier .dhpt valide (voir managing-diva-projects)
3. Tous les .dhps references existent
4. Tous les fichiers source references existent
5. Nom de profil avec accent correct en ISO-8859-1
6. Repertoire de sortie du rapport existe
7. Tous les fichiers source en ISO-8859-1 + CRLF (PROJ01, PROJ02)

## Post-compilation

1. **Etablir le verdict avec `parse_compilation.py`** (source unique). Le succes exige que
   TOUT soit vrai : un resume dit 0 erreur (`[TOTAL_ERRORS]0` **ou** `Erreur(s)=0`), **ET**
   aucune ligne `[ERROR]`, **ET** aucune erreur **hors compilation** (`N ERREUR(S) autre(s)`,
   `absent ou inaccessible. Code=` -- souvent un mauvais implicite actif), **ET** aucune
   interruption ni abandon (`Compilation interrompue`, `Construction du projet arretee`,
   `Fin anormale`). Un build **interrompu** affiche `Erreur(s) 0` alors que les objets ne
   sont **pas** a jour : ce n'est jamais un succes.
2. Si erreurs : le script les rend avec leur fichier source et leur ligne.
3. Si succes : possibilite de lancer la synchronisation SQL (voir `syncing-diva-sql`).
