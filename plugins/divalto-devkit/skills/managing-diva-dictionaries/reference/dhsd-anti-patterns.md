# Anti-patterns Dictionnaire -- Regles DICT01-DICT16

## Contenu

- Regles verifiees par validate_dhsd.py
- Detail des regles
- Regles de surcharge (DICT14, DICT15, DICT16) -- verifiees avec `--dhsd-standard`
- Validation croisee
- Garde-fous integres dans generate_dhsd_block.py (DICT12, DICT13)

---


Anti-patterns dictionnaire `.dhsd` : le digest livré avec ce skill.

---

## Regles verifiees par validate_dhsd.py

| Regle | Severite | Description | Detection | Regle linter |
|-------|----------|-------------|-----------|--------------|
| DICT01 | **error** | Champs qui se chevauchent dans la table | Position suivante != Position courante + Taille courante | `D01` |
| DICT02 | **error** | Trous entre les champs (positions decalees) | Position suivante != Position courante + Taille courante | `D02` |
| DICT03 | **error** / **warning** | Champ `U{TABLE}` (reserve distributeur) absent -- warning si l'absence est **assumee** (cf. detail) | Recherche du dernier champ dans [CHAMPS] | `D03` |
| DICT04 | **error** | Champ utilise dans [CHAMPS] sans declaration [CHAMP] | Cross-reference [CHAMPS] vs [CHAMP] existants | `D04` |
| DICT05 | **error** | Encodage du fichier .dhsd modifie (pas ISO-8859-1) | Analyse binaire | `D05` |
| DICT06 | **error** | Fins de ligne LF au lieu de CRLF | Analyse binaire | `D06` |
| DICT07 | **error** | Section [/CHAMPS] manquante pour fermer la table | Analyse structurelle | `D07` |
| DICT08 | **error** | Section [/TABLES] manquante pour fermer la base | Analyse structurelle | `D08` |
| DICT09 | **error** | Section [/INDEX] manquante pour fermer un index | Analyse structurelle | `D09` |
| DICT10 | *non implementee* | Valeur CE dans CLE de l'index incoherente avec la table | -- (regle **annoncee, jamais codee** : le validateur ne la remonte pas) | `D10` |
| DICT11 | *non implementee* | Base nommee sans le prefixe du dictionnaire | -- (le code s'arrete sur un `pass` : rien n'est remonte) | `D11` |
| DICT12 | **error** | `ce_value` invalide avec discriminator `Ce1` (Nature=1 char) | Garde-fou pre-generation | -- |
| DICT13 | **error** | Lettre cle d'index non alphanumerique 1 char | Garde-fou pre-generation | -- |
| DICT14 | warning (error si `--dhsd-standard`) | Metadonnees `[BASEU]`/`[TABLEU]` divergentes du standard | Cross-reference avec le `.dhsd` standard | -- |
| DICT15 | **error** | `[CHAMPR] nom=U<X>` sans container `U<X>` dans la table standard correspondante | Cross-reference avec le `.dhsd` standard | -- |
| DICT16 | **error** | Redeclaration d'un `[CHAMP]` global du standard avec Nature/Gel/Flags differents (option C interdite) | Cross-reference avec le `.dhsd` standard | -- |

> **La colonne « Regle linter ».** Un producteur et `lint_diva.py` verifient parfois
> la meme chose et le disent avec deux codes : c'est le prix d'un prefixe par outil,
> et cette colonne fait le lien. Ici elle est remplie **onze fois sur seize** -- les
> `D01`-`D11` du linter enoncent les memes regles, dans le meme ordre.
>
> **Une cellule vide ne veut pas dire que ce numero n'existe pas ailleurs.**
> Le linter a bien un `D12`, un `D13` et un `D14` -- mais ils designent chez lui des
> regles sans rapport avec les notres : PascalCase des champs, des bases et des
> index. Ne pas les lire comme des equivalents : c'est precisement pour cela que
> chaque outil a desormais son prefixe.
>
> **Et pour `DICT10` / `DICT11`, la cellule repare une promesse.** Ces deux regles sont
> annoncees ici sans etre codees dans ce skill. Le linter, lui, les implemente : la
> verification existe, elle est simplement ailleurs. Lancer `lint_diva.py` sur le
> `.dhsd` les couvre.

---

## Detail des regles

### DICT01 / DICT02 -- Positions des champs (ERREUR CRITIQUE)

**Anti-pattern :** Les positions des champs ne sont pas contigues.

**Risque :** Le compilateur signale "il y a un trou devant le champ X" ou les donnees sont corrompues en base.

**Regle :** `Position(N+1) = Position(N) + Taille(Nature(N))`

```ini
# INCORRECT : trou entre Dos et Ref
Nom=Ce1,1,2,N,0,0,N,3      # pos=1, Nature=1 -> suivant=2
Nom=Dos,2,2,N,0,0,N,3       # pos=2, Nature=8 -> suivant=10
Nom=Ref,15,2,N,0,0,N,3      # ERREUR : devrait etre 10, pas 15

# CORRECT
Nom=Ce1,1,2,N,0,0,N,3       # pos=1, Nature=1 -> suivant=2
Nom=Dos,2,2,N,0,0,N,3       # pos=2, Nature=8 -> suivant=10
Nom=Ref,10,2,N,0,0,N,3      # OK : 10 = 2 + 8
```

### DICT03 -- U-field absent (ERREUR **ou** warning)

**Anti-pattern :** La table n'a pas de champ `U{NomTable}` en derniere position, **alors
qu'on s'attendait a en trouver un**.

**Risque :** Pas de reserve pour les personnalisations d'un tiers.

**Ce n'est pas toujours un defaut.** Pour une table dont l'**integrateur est
proprietaire**, la convention est de **ne pas** reserver de zone `U` -- en ajouter une
n'est pas faux, c'est un choix explicite. Mesures : **0 des 103 tables** d'un
dictionnaire specifique reel en ont une, et **67 %** des tables specifiques / **45 %**
des tables standard en sont depourvues. Une regle en `error` par defaut saturerait donc
le rapport et noierait les vrais signaux (`DICT01` chevauchement, `DICT02` trou).

D'ou trois situations distinctes :

| Situation | Comment le validateur le sait | Severite |
|-----------|-------------------------------|----------|
| Absence **deliberee** a la generation | `summary.u_field = null` dans le JSON de `generate_dhsd_block.py` | **warning** |
| Absence **assumee** sur un fichier | option `--no-u-field` | **warning** |
| Etat **preexistant** subi (table legacy en alignement de version) | option `--migration` | **warning** |
| Absence **non declaree** | aucun des trois signaux | **error** |

**Bonne pratique :** quand la table est destinee a etre etendue par un tiers, ajouter
`U{NomTable}` en dernier champ avec une Nature de reserve suffisante (typiquement 40 a
1500 octets). Sur une table standard que l'on surcharge, ce container est au contraire
le **seul** ancrage legitime -- voir
[dhsd-surcharge-pattern.md](dhsd-surcharge-pattern.md), section « `Filler` vs container `U` ».

### DICT04 -- Champ non declare (ERREUR)

**Anti-pattern :** Un champ est reference dans `[CHAMPS]` d'une table sans avoir de `[CHAMP]` correspondant.

**Exception :** `Filler` est un mot-cle special qui ne necessite pas de declaration.

### DICT05 / DICT06 -- Encodage et fins de ligne (ERREUR)

**Anti-pattern :** Le fichier .dhsd a ete converti en UTF-8 ou les fins de ligne ont ete changees en LF.

**Bonne pratique :** Toujours utiliser le skill `writing-diva-files` pour ecrire dans un .dhsd.

#### Le piege ne vient pas que de l'encodage : une edition STRUCTURELLE suffit

Cas reel : apres une insertion **reussie** par `insert_dhsd_blocks.py` (CRLF preserve), une
petite edition Python **supplementaire** -- ajouter une ligne dans le `[TABLES]` d'une base
existante -- a converti **tout le fichier** en LF.

La cause n'a rien a voir avec l'encodage de caracteres : **Python en mode texte convertit
les CRLF en LF a la lecture**, et la reecriture produit un fichier LF pur. Le script
"marche", le diff parait minuscule, et le fichier est corrompu. `DICT06` l'a detecte
immediatement -- mais apres coup.

**Regle** : toute edition d'un `.dhsd` passe par les scripts de ce skill ou par
[writing-diva-files](../../writing-diva-files/SKILL.md) -- **jamais** par un script maison,
meme d'une seule ligne, meme apres une operation reussie. Les pieges detailles (mode texte,
BOM PowerShell, CRLF final manquant -> **Erreur 135**) sont dans
`writing-diva-files/reference/safe-methods.md`.

> **Cette edition-la n'est plus necessaire.** Rattacher une table a une base existante est
> desormais outille : `insert_dhsd_blocks.py --attach-to-base <NomBase>` insere la ligne
> dans le `[TABLES]` au bon rang, en preservant l'encodage. Voir le SKILL.md, section
> « Base deja existante : rattacher, pas recreer ».

### DICT07 / DICT08 / DICT09 -- Sections non fermees (ERREUR)

**Anti-pattern :** Oublier les balises fermantes `[/CHAMPS]`, `[/TABLES]`, `[/INDEX]`.

**Risque :** Structure INI malformee, erreur de parsing a la compilation.

### DICT10 -- Valeur CE incoherente (**non implementee**)

> **Attention : ce controle n'existe pas dans `validate_dhsd.py`.** La regle etait
> declaree et documentee sans avoir jamais ete codee -- la lire ne doit pas faire croire
> qu'un garde-fou automatique existe. La coherence CLE/CE reste a verifier **a la main**.
> Le controle a ecrire est decrit ci-dessous.

**Anti-pattern :** La valeur CE dans la ligne CLE de l'index ne correspond pas a la valeur CE declaree dans la table.

**Exemple :**
```ini
# Dans [TABLE]
CE=Ce1,A

# Dans [INDEX] -> CLE
CLE=GtfBase,A,Ce1,2,A,n,1,n    # OK : ValeurCE=A correspond
CLE=GtfBase,A,Ce1,2,B,n,1,n    # ERREUR : ValeurCE=B != A
```

### DICT11 -- Prefixe base (**non implementee**)

> **Attention : ce controle ne remonte rien.** `validate_dhsd.py` contient bien une
> boucle pour DICT11, mais elle se termine sur un `pass` commente
> « Verification complexe, on laisse en warning simple » -- aucun constat n'est emis.
> La convention ci-dessous reste donc **a verifier a la main**.

**Anti-pattern :** Le nom de la base ne suit pas la convention de prefixe du dictionnaire.

**Convention :**
| Dictionnaire | Prefixe base |
|-------------|-------------|
| gtfdd.dhsd | Gtf |
| ccfdd.dhsd | Ccf |
| rtlfdd.dhsd | Rtl |
| ggfdd.dhsd | Ggf |
| wmsfdd.dhsd | Wms |

---

### DICT12 -- ce_value Ce1 (ERREUR pre-generation)

**Anti-pattern :** passer `ce_value` multi-caracteres (ex `"200"`) alors que
le discriminator par defaut `Ce1` est `Nature=1` (un seul caractere).

**Symptome compilation :** `La lettre cle doit etre un seul caractere`.

**Regle :** avec `discriminator=Ce1`, `ce_value` doit matcher `^[A-Z0-9]$`.
Pour un discriminator numerique multi-chiffres, utiliser `CeBin` (non
implemente cote generation pour l'instant).

Le garde-fou est dans `generate_dhsd_block.py` (fonction `validate_ce_value`)
et coupe immediatement avec exit 1.

### DICT13 -- Lettre cle d'index (ERREUR pre-generation)

**Anti-pattern :** un index nomme `Index_Pay` (suffixe multi-char) donnait
une lettre cle `Pay` (ou pire `0` apres derivation buggee) dans `CLE=`,
incompatible avec la Nature du discriminator (1 char).

**Regle :** la lettre cle doit matcher `^[A-Z0-9]$`. La derivation suit :
1. Si `Index_<X>` avec `X` 1 char alphanumerique : reutiliser `X`
2. Sinon, prendre la 1re lettre du suffixe (`Index_Pay` -> `P`)
3. Si conflit avec un autre index : allouer la 1re lettre libre A-Z

Le garde-fou est dans `generate_dhsd_block.py` (fonction
`derive_index_letter`).

---

## Regles de surcharge (DICT14, DICT15, DICT16)

Ces regles ne s'appliquent qu'aux fichiers `.dhsd` de surcharge (`<dict>u.dhsd`). Elles necessitent un acces au `.dhsd` standard correspondant pour la verification croisee :

```bash
py validate_dhsd.py --path <surcharge>u.dhsd --dhsd-standard <standard>.dhsd
```

Sans `--dhsd-standard`, ces regles passent en mode warning (impossibilite de verifier) ou sont skippees selon le cas.

### DICT14 -- Metadonnees [BASEU]/[TABLEU] divergentes du standard

**Anti-pattern :** un bloc `[BASEU]` ou `[TABLEU]` dans la surcharge a un `Nom=`, `Version=` ou `DateM=` different du `[BASE]`/`[TABLE]` standard correspondant.

**Risque :** corruption silencieuse du merge surcharge/standard. xwin7 peut interpreter la base comme obsolete (-> merge abandonne) ou en avance (-> incoherences runtime) selon les valeurs. Comportement non garanti et non deterministe.

**Regle :** **toujours recopier** `Version=`, `Nom=` et `DateM=` du bloc standard correspondant. Seuls `DateMIndex=` (BASEU) et le 2e `DateM=` (TABLEU, FILETIME courant) sont propres a la surcharge.

```ini
; MAUVAIS -- libelle invente et DateM arbitraire
[BASEU]
Nom=GtfPcf,Tiers principaux,1                    <-- "Tiers principaux" invente
DateM=0000000000000001                           <-- timestamp arbitraire

; BON -- repris a l'identique du [BASE] standard
[BASEU]
Nom=GtfPcf,Tiers,1                               <-- libelle reel "Tiers"
DateM=FEADA18CBB8CD901                           <-- DateM reel
```

Severite : warning si `--dhsd-standard` absent (cross-ref impossible), error sinon.

### DICT15 -- Table sans U-container

**Anti-pattern :** ajout dans `[CHAMPR] nom=U<X>` d'une surcharge alors que la table `<X>` standard **n'a pas** de container `U<X>` dans son `[CHAMPS]`.

**Risque :** la table n'a pas ete concue pour etre surchargeable. La surcharge peut compiler "sans erreur" mais :
- Au prochain upgrade du standard, l'offset choisi peut entrer en conflit avec un nouveau champ standard -> corruption silencieuse
- Pattern non documente, non supporte par xwin7

**Regle :** verifier que la table cible declare bien `Nom=U<NomTable>,<offset>,...` dans son `[CHAMPS]` du `.dhsd` standard. Sinon refuser la surcharge et proposer les options legitimes :

- Demander a Divalto d'ajouter un U-container dans une prochaine release
- Rediriger vers une autre table surchargeable
- Abandonner la demande

Severite : error -- regle dure.

### DICT16 -- Redeclaration de [CHAMP] standard avec attributs differents (option C)

**Anti-pattern :** un bloc `[CHAMP]` dans la surcharge redeclare un champ qui existe deja dans le `.dhsd` standard, avec `Nature=`, `Gel=` ou `Flags=` differents.

**Risque :** dans le meilleur cas, xwin7 rejette la redeclaration (compile echoue). Dans le pire cas, il accepte et **applique le changement globalement** -- toutes les tables qui utilisent ce champ heritent de la nouvelle Nature, casse silencieusement la chaine d'utilisateurs du champ.

**Regle :** quand un champ existe deja cote standard, 3 options se presentent et **seules A et B sont valides** :

| Option | Action | Valide ? |
|--------|--------|----------|
| A | Reutiliser le champ tel quel (Nature standard inchangee) | OK |
| B | Creer un nouveau champ prefixe (`<prefixe><X>`, ex. `spe<X>`) avec Nature librement choisie | OK |
| C | Redeclarer le `[CHAMP]` standard avec Nature/Gel/Flags differents | **INTERDIT** |

Exemple : standard declare `Nom=Ref,Reference,1 Nature=25`. Pour ajouter un Ref Nature=8 sur une table, refuser l'option C, proposer A (reutiliser Nature=25) ou B (creer `speRef` Nature=8).

Severite : error.

> Voir [dhsd-surcharge-pattern.md](dhsd-surcharge-pattern.md) section "Options A/B/C" pour le contexte complet.

---

## Validation croisee

Le script `validate_dhsd.py` effectue des verifications croisees entre les zones :
- [CHAMPS] de [TABLE] vs [CHAMP] existants (DICT04)
- CLE de [INDEX] vs CE= de [TABLE] -- **annonce, non implemente** (DICT10)
- [TABLES] de [BASE] vs [TABLE] existantes
- [INDEXL] vs [INDEX] et [BASE] existants

Avec `--dhsd-standard <path>`, des verifications supplementaires sont effectuees pour les regles de surcharge (sur un fichier `<dict>u.dhsd`) :
- [BASEU]/[TABLEU] vs [BASE]/[TABLE] standards (DICT14)
- [CHAMPR] nom=U<X> vs container U<X> dans la table standard (DICT15)
- [CHAMP] surcharge vs [CHAMP] standard de meme nom (DICT16)
