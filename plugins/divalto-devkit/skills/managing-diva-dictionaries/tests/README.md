# Tests du skill managing-diva-dictionaries

Suites executables, **sans poste Divalto** : chaque cas fabrique ses dictionnaires `.dhsd`
en ISO-8859-1 + CRLF dans un repertoire temporaire, puis lance le script du skill dessus.

```
py .claude/skills/managing-diva-dictionaries/tests/run_all.py
```

A lancer apres **toute** modification des scripts couverts.

---

## test_compare_dhsd_versions.py

Couvre `scripts/compare_dhsd_versions.py` -- « quelles tables ont change de taille entre
deux versions, donc quel specifique recompiler » (RETEX #110).

### Pourquoi ces tests

La question a une **fausse reponse evidente** : comparer le nombre de champs. Elle se
trompe dans les deux sens, et c'est mesure :

- **faux positifs** : 129 tables gagnent des champs a taille constante, l'editeur
  consommant sa reserve `Filler` -- un controle par comptage les signalerait a tort ;
- **faux negatifs** : 7 des 16 tables qui changent de taille sur un pas de Service Pack
  le font a nombre de champs **identique** -- un controle par comptage les manquerait,
  et ce sont exactement celles qui obligent a recompiler.

Les cas 1 et 2 verrouillent ces deux sens. Le cas 1 verifie explicitement que son propre
fixture a un nombre de champs constant : sans cela il ne prouverait rien.

### Le cas 5 est un temoin, pas un test de comportement

La capacite d'un container `U<NomTable>` **n'est pas** sur sa ligne de placement
`[CHAMPS]`, ou la 6e position vaut toujours 0 -- contrairement au `Filler`, qui y porte
bien sa taille. Elle vit dans la `Nature=` de sa declaration `[CHAMP]` globale.

La premiere version du script lisait la 6e position : elle comparait donc des zeros et
concluait « aucun container modifie » sur n'importe quelle paire de fichiers. Le cas 5
**re-implemente cette lecture fautive** et verifie qu'elle ne voit rien la ou la lecture
correcte voit une reduction de 1501 a 1000 octets. C'est ce qui garantit que les cas 4, 6,
7 et 8 discriminent reellement.

### Ce que les cas ont fait tomber

| Cas | Defaut attrape |
|-----|----------------|
| **17** | La comparaison portait sur le couple `(nom, capacite)`. Un simple changement de casse du nom (`UArt` -> `UART`) etait donc rapporte comme un changement -- avec le libelle absurde « capacite augmentee 1500 -> 1500 octets ». Corrige : on compare la **presence** et la **capacite**, jamais le nom. |
| **5** | Le temoin lui-meme, ecrit trop large, ramassait la ligne `Nom=UArt,...` du bloc `[CHAMP]` global (3 champs) en plus de la ligne de placement (8 champs). Cadre sur `[CHAMPS]`. |

### Table des cas

| # | Ce qui est verifie |
|---|--------------------|
| 1 | `Taille=` change a nombre de champs constant -> `incompatibles`, exit 1 |
| 2 | champs ajoutes a `Taille=` constante -> `compatibles_champs_ajoutes`, exit 0 |
| 3 | `Filler` consomme sans ajout de champ -> **aucun constat** (transparent pour l'integrateur) |
| 4 | container `U` reduit -> `REDUITE` + « a remonter a Divalto » |
| 5 | temoin de la lecture fautive en 6e position |
| 6 | container `U` agrandi -> signale, **non** qualifie anomalie |
| 7 | container `U` disparu -> anomalie (perte du point d'ancrage) |
| 8 | container `U` apparu -> « sans risque » |
| 9 | tables ajoutees / supprimees |
| 10 | dictionnaires identiques -> exit 0, rien a signaler |
| 11 | fichier introuvable -> exit 2 + message sur stderr |
| 12 | `--only-incompatible` vide les listes annexes, garde `incompatibles` |
| 13 | `--format text` porte le message actionnable et la note `Filler` |
| 14 | lecture ISO-8859-1 : un libelle accentue ne fait pas deriver l'analyse |
| 15 | casse du nom de table : `Art` et `ART` sont la meme table |
| 16 | capacite `U` indeterminable -> le script le **dit** au lieu de comparer des `None` |
| 17 | casse du nom de container a capacite egale -> **aucun** faux constat |


---

## test_options_table_specifique.py

Couvre les options de **table specifique integrateur** dans `generate_dhsd_block.py`,
`validate_dhsd.py` et `insert_dhsd_blocks.py` (RETEX #207 / #245).

### Pourquoi ces tests

Les trois defauts avaient le meme effet : le partenaire ne pouvait **pas passer** par
l'outil et a genere son `blocs.json` a la main.

| Defaut | Ce que faisait le code |
|--------|------------------------|
| **#245** | Toutes les lignes `Version=` portaient `"Claude"` -- alors que le script voisin `generate_surcharge_field.py` exigeait deja `--user`. Tracabilite rompue. |
| **#207** -- champs imposes | `u_field_size=0` ne desactivait rien : le script **refusait de tourner** (`Nature invalide pour le champ 'U...': 0`). Les champs d'audit et le container U etaient inconditionnels. |
| **#207** -- base existante | L'insertion echouait sur `Base 'X' existe deja`, sans dire quoi faire. |

### Le cas 12 est un temoin

`DICT03` (container U absent) est une erreur par defaut ; une absence **declaree** la fait
passer en warning, sinon le generateur produirait des blocs refuses par son propre
validateur. Le cas 11 verifie l'assouplissement ; le cas 12 reprend **le meme JSON prive de
la cle `u_field`** et exige que `DICT03` redevienne une **erreur**. Sans lui, on ne saurait pas
si l'assouplissement est cible ou si la regle a simplement ete desarmee.

### Ce que la suite a fait tomber

| Cas | Defaut attrape |
|-----|----------------|
| **19** | Ecrit d'abord avec des blocs referencant une autre base, il declenchait le controle de coherence au lieu du controle d'existence -- il ne testait donc pas ce qu'il annoncait (doublon du cas 20). Recadre. |
| **21** | La verification d'encodage etait **creuse** (`assert utf8 or True`). Le fixture porte maintenant un libelle accentue, et le cas exige que l'octet ISO-8859-1 survive **et** que le fichier ne decode pas en UTF-8. |

### Ce que les cas verrouillent, par theme

**Identite du developpeur (#245)** -- cas 1 a 5 : refus sans `--user` ; propagation dans
**toutes** les lignes `Version=` (champ, table, base, index) et disparition de `"Claude"` ;
refus de la virgule (elle casserait la ligne) ; refus au-dela de 20 caracteres, **sans
troncature silencieuse** ; priorite du CLI sur la cle `creator` du JSON.

**Champs standard (#207)** -- cas 6 a 10 : pas de container U par defaut, ni declaration
`[CHAMP]` ni ligne de placement ; `--u-field-size 500` en ajoute un ; `--no-audit` retire
les 4 champs d'audit ; **`Ce1` toujours genere** avec sa ligne `CE=`, y compris avec toutes
les options desactivantes -- decision assumee : une table peut exister sans discriminateur,
mais en prevoir un fait partie des bonnes pratiques ; positions contigues et `Taille=`
coherente dans les **4** combinaisons d'options.

**Severite de DICT03** -- cas 11 a 13 : absence deliberee (blocs) et absence assumee
(`--no-u-field` sur fichier) en warning, absence non declaree en erreur.

**Base existante (#207)** -- cas 14 a 23 : l'erreur `existe deja` **nomme desormais
l'option** a utiliser ; `--attach-to-base` rattache la table **sans** creer de bloc
`[BASE]` ; rang alphabetique respecte au milieu comme en fin de liste (convention mesuree
sur 10 bases multi-tables reelles) ; table deja rattachee, base introuvable et incoherence
base/index refusees **avec fichier inchange, prouve par empreinte** ; encodage
ISO-8859-1 + CRLF preserve ; la validation post-insertion ne remonte pas `DICT03` en erreur ;
et une base **nouvelle** continue de fonctionner (non-regression).

### Verification de discrimination

Jouee contre la version anterieure des trois scripts (`git show HEAD:...`, mise en place,
puis restauration prouvee par empreinte), la suite tombe sur **23 cas sur 23**. La suite
`test_compare_dhsd_versions.py` passe **17/17 dans les deux sens** : le lot n'a pas touche
a la comparaison de versions.


---

## test_coherence_doc.py

Invariants entre la **documentation** du skill et son **code**.

### Pourquoi cette suite

Le LOT C est purement documentaire, et **une documentation ne tombe pas en erreur : elle
derive en silence**. Un lecteur ne peut pas savoir qu'une affirmation est devenue fausse.

La lecon vient d'un autre skill, ou une regle de lint avait ete **declaree au catalogue,
documentee dans une page de reference, et n'avait jamais eu d'implementation**. Une regle
annoncee qui ne s'execute pas est pire qu'une regle absente : un agent croit disposer d'un
controle qu'il n'a pas, et ne verifie donc pas a la main.

### Ce que la suite a fait tomber, des sa premiere execution

| Cas | Trouvaille |
|-----|-----------|
| **4** | **Deux regles fantomes.** `DICT10` (« Valeur CE dans CLE incoherente ») n'existe que dans une docstring -- aucun code. `DICT11` (« Prefixe base ») a bien une boucle dans `validate_dhsd.py`, mais elle se termine sur un `pass` commente « Verification complexe, on laisse en warning simple » : **rien n'est remonte**. Les deux etaient documentees comme actives, l'une en `error`. Elles sont desormais marquees **non implementee** dans la page de reference, et gelees dans `DETTE`. |
| **5** | La nouvelle page de reference n'etait pas au catalogue de `discovering-skills`, donc **invisible**. C'est exactement la derive qui avait laisse **trois** pages hors catalogue pendant longtemps. |

### Une erreur de la suite elle-meme, corrigee

Le cas 4 a d'abord accuse `DICT12` et `DICT13` d'etre fantomes. **C'etait faux** : elles sont bien
implementees, mais en **garde-fous pre-generation** dans `generate_dhsd_block.py`
(`validate_ce_value`, controle de la lettre cle) et non dans `validate_dhsd.py` -- que le
test etait seul a scanner. Le test regarde maintenant les **deux** fichiers, et les deux
garde-fous portent un marqueur `Regle DICT12` / `Regle DICT13` lisible par machine.

C'est le meme piege que celui qu'on cherche a eviter : une affirmation plausible, non
verifiee. Ici c'est l'outil de verification qui s'est trompe.

### Table des cas

| # | Invariant | Ce qu'il empeche |
|---|-----------|------------------|
| 1 | Les 5 lignes documentees obligatoires (`Version`, `Nom`, `Gel`, `Nature`, `Flags`) sont celles que le generateur emet, et **pas** de `DateM` | Que la page enumere une liste que le code a cesse de respecter |
| 2 | Toute page `reference/` citee par le SKILL.md existe | Un lien mort vers une page renommee ou supprimee |
| 3 | Aucune page **orpheline** (presente mais jamais citee) | Une page qui ne sera jamais chargee, donc du contenu mort |
| 4 | Toute regle `D-NN` citee par la doc est implementee (validateur **ou** garde-fou pre-generation), hors dette gelee | La regle fantome -- un controle annonce qui n'existe pas |
| 5 | L'inventaire `references` du catalogue == les pages reelles | Une page invisible de `discovering-skills` |
| 6 | Les liens `../../<skill>/SKILL.md` pointent sur des skills existants | Un renvoi inter-skills casse par un renommage |

**`DETTE` ne doit jamais s'allonger** pour faire passer le test : soit on implemente la
regle, soit on retire sa mention de la documentation. Le test est la pour bloquer la
troisieme.

### Verification de discrimination

Jouee contre l'etat d'avant le lot (`git show HEAD:` sur les 4 fichiers touches + retrait de
la nouvelle page + catalogue d'avant, restauration **prouvee par empreinte**), la suite tombe
sur **2 cas sur 6** -- les deux qui portent du contenu neuf (1 et 4), plus le 5 observe en
echec pendant le developpement. Les cas 2, 3 et 6 passent avant comme apres : ce sont des
gardes de non-regression, c'est leur role.

---

## Convention

- Les dictionnaires de test sont ecrits en **ISO-8859-1 + CRLF**, comme de vrais fichiers
  DIVA -- pas en UTF-8.
- Aucun chemin absolu, aucune reference a une arborescence de sources ni a une version
  d'ERP : tout se passe dans un `tempfile.mkdtemp()` nettoye en `finally`.
- Les cas lisent la sortie **JSON** du script et, pour le cas 13, sa sortie **texte**.
- Les codes retour font partie du contrat teste (0 / 1 / 2) : le script est concu pour
  servir de garde-fou dans un script d'integration.
