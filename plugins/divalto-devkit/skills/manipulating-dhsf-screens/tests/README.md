# Tests du skill manipulating-dhsf-screens

```
py .claude/skills/manipulating-dhsf-screens/tests/run_all.py
```

Aucun poste Divalto requis : les cas n'appellent que des fonctions de nom de fichier.

---

## test_surcharge_presomption.py

`is_dhsf_filename.py` ne recoit qu'un **nom de fichier** -- il n'ouvre rien. Et un
`.dhsf` ne porte **aucun marqueur interne** de surcharge : verifie sur **2962 fichiers
reels** (2438 du standard X.13 + 524 d'un specifique partenaire), **zero** occurrence
de `overwrite` / `overwrittenby`. Le suffixe `u` du nom est donc le **seul** signal
disponible ici -- contrairement aux `.dhps`, dont l'en-tete `xwin-s-sprojet` est
autoritaire et sur lesquels la deduction par le nom a ete supprimee.

La consequence est inevitable : tout nom finissant par la lettre `u` est presume
surcharge, y compris pour des raisons purement lexicales. Les **5 masques du standard
X.13** concernes n'en sont **aucun** :

| Masque | Pourquoi il finit par `u` |
|--------|---------------------------|
| `a5eepersmenu.dhsf` | me**nu** |
| `rceebordereau.dhsf` | bordere**au** |
| `rcembordereau.dhsf` | bordere**au** |
| `rceztreressimu.dhsf` | ressi**mu** |
| `speewebscru.dhsf` | websc**ru** |

**On ne peut pas corriger la deduction ; ce qui se corrige, c'est de cesser de la
presenter comme un fait.** La sortie porte desormais `is_surcharge_base`
(« suffixe du nom de fichier -- PRESOMPTION ») et, quand la presomption est positive,
`is_surcharge_avertissement` qui nomme la mesure, cite les contre-exemples du standard
et dit **comment confirmer autrement** (emplacement du fichier en zone specifique, ou
en-tete du `.dhps` qui le reference).

| Groupe de cas | Ce qui est verifie |
|---------------|--------------------|
| Masque ordinaire | `is_surcharge` faux, et la base de la deduction est annoncee **meme quand la reponse est faux** |
| Les 5 faux positifs mesures | `is_surcharge` reste `true` (on ne peut pas faire mieux) **mais** l'avertissement accompagne toujours la reponse |
| Contenu de l'avertissement | il nomme la base, l'absence de marqueur interne, les contre-exemples, et la marche a suivre |
| Vrai nom de surcharge | reste presume surcharge : la deduction garde son utilite |
| Non-regression | la regle universelle du masque (`pos 3 = 'e'`) n'est pas touchee |

**Verification de discrimination** : jouee contre la version anterieure du script, la
suite tombe sur **10 cas** (l'aveu etait absent) et 9 gardes passent dans les deux
versions.

## `test_grammaire_verifiee.py` -- grammaire du .dhsf (13 cas)

Deux familles de cas. **doc <-> releve** : les pages citent des chiffres mesures sur le corpus
des masques du standard, `reference/mesures-corpus.json` les porte et les qualifie, un cas
verifie que les deux concordent. **Fonctionnel** : le controle de chaine des pages est execute
sur un masque reellement casse, fabrique depuis le template livre avec le skill.

Ce que ce lot a appris, et que les cas gardent :

- **Deux des trois retours terrain se trompaient.** L'un concluait que `esp_si_zero` n'est pas
  un attribut valide -- il est employe **33 576 fois**, dans 2 014 des 2 438 masques. L'autre
  donnait `RTF_NOTE` pour LE style du `rich_edit` -- c'est le **4e**, derriere
  `CHAMP_NON_SAISI`, `STD` et `CHAMP_SAISI`. Les cas 3 et 4 gardent la mesure **et** la
  refutation : une conclusion fausse citee pour etre refutee ne doit pas pouvoir revenir sous
  forme de prescription. Le cas 4 controle donc la **phrase**, pas le fichier.
- **Une regle de lint demandee a ete mesuree puis ECARTEE.** 40 % des `[param_tableau]` du
  standard n'ont pas de `col_depl` : l'avertissement reclame produirait 1 113 faux positifs sur
  du code livre. Le cas 6 garde le chiffre qui le refute -- sans lui, un lot ulterieur
  reintroduirait la regle.
- **Le skill se contredisait lui-meme.** Trois composants qu'il **documente** -- `cadre`,
  `bitmap_constante`, `bitmap_variable` -- etaient absents de la liste blanche de son propre
  parser : un masque qui en contient etait parse sans les voir. Le cas 8 en fait un
  **invariant** : toute page `composant-*.md` doit avoir son type reconnu. C'est le cas qui
  aurait attrape le defaut avant nous.
- **Deux codes etaient emis et decrits nulle part.** `validate_page_chain()` est arrive
  avec ses deux codes, et la table de `SKILL.md` ne couvrait que le layout des groupbox :
  le partenaire pouvait lire un code en sortie sans rien pour le comprendre. Le cas 12
  confronte la table aux emissions **dans les deux sens** -- un code emis sans ligne est
  indocumente, une ligne sans emission est un code qu'on cherchera en vain dans une
  sortie. Il enumere par `ast`, pas par motif : c'est un motif `R[1-5]` qui avait rate
  ces deux codes-la. Ajoute au passage au prefixe `DHSF`, avec sa preuve : les deux
  mutations (les lignes retirees, une ligne inventee) le font tomber, et lui seul.
- **La post-validation ne voyait qu une des deux familles.** `--action validate`
  cumule le layout des groupbox et la chaine des pages ; la post-validation qui suit
  une MODIFICATION n appelait que le premier. Deux verdicts differents sur le meme
  fichier, selon la commande. Le cas 13 verifie la SORTIE d une action modifiante --
  le JSON que l orchestrateur lit -- et que sa forme `{valid, violations, stats}`
  n a pas bouge.

Validation : **11 mutations, 11 discriminantes**, et le rejeu des versions d'avant le lot fait
tomber **11 des 11 cas**. Le harnais a trouve **un trou de ma livraison** : le cas 5 citait
7 729 occurrences sans jamais les confronter au releve -- changer le chiffre ne le faisait pas
tomber. Corrige.

> **Style.** Cette suite emploie le decorateur `@cas`, comme celles des autres skills du
> plugin. `test_surcharge_presomption.py` utilise une forme anterieure ; l'aligner est trace
> plutot que fait ici, hors perimetre.

## `test_edition_verifiee.py` -- garde-fous d'edition (12 cas)

Memes deux familles que la suite de grammaire, avec **deux cas fonctionnels** -- le cas 4
et le cas 6 : les correctifs de script sont **executes** sur de vrais fichiers, pas
seulement decrits. Le cas 6 enchaine trois invocations (parse, add-column, re-parse) ;
ce sont bien trois appels, mais **un seul cas**.

> **Le cas 12 garde ce compte-la meme.** Il recalcule sur les fichiers les nombres que ce
> README annonce -- cas par suite, et cas fonctionnels -- et **echoue aussi si la phrase
> qu'il verifie a disparu**, pour ne pas passer par absence de sa cible. Il est ne d'une
> erreur : ce paragraphe annoncait TROIS cas fonctionnels la ou il y en a DEUX.

Ce que ce lot a appris :

- **Le defaut de #268 avait une cause plus profonde que son symptome.** `compute_max_id`
  ignorait `dernier_id`, que le parser expose pourtant -- alors que `action_add_page`
  respectait deja `dernier_id_page`. **Trois sites sur quatre, dans le meme fichier** : une
  asymetrie interne, motif. Le correctif retenu est plus general que celui demande :
  un **plancher** `max(id present, dernier_id)`, sans detecter la surcharge ni coder 1000000
  en dur. Le cas 6 rejoue le defaut reel sur un masque a `dernier_id=1000000`.
- **Le compteur qui manquait.** Perdre un bouton dans un toolbar **conserve** laisse
  `toolbars_count` inchange : seul le compte des ITEMS le voit. Les cas 3 et 4 le gardent,
  documente et execute.
- **La regle de #187 ne se verifie pas** : 23 % des 336 grilles au mieux. Le cas 9 garde les
  deux sens -- le refus doit rester ecrit **avec son chiffre**, et la formule ne doit pas
  revenir comme prescription.
- **Un ecart signale, pas corrige** : la regle `DHSF05` du validate utilise `nb_lig * 14` la ou la
  mesure donne **8** en contexte panel. Toucher `DHSF05` sans verifier serait exactement l'erreur
  reprochee aux RETEX -- conclure d'une observation a une cause. Le cas 10 verifie que l'ecart
  reste **consigne** et que `DHSF05` reste **intacte**.

Validation : **11 mutations, 11 discriminantes**, et le rejeu des versions d'avant fait tomber
**11 des 11 cas**. Le harnais a de nouveau trouve **une faiblesse de ma livraison** : le cas 2
s'ancrait sur le mot « touche », trop commun dans une page qui documente aussi la section
`[touches]` -- remplacer la phrase entiere laissait le cas passer. Meme classe que chercher un
chiffre nu : **ancrer sur la phrase, pas sur le mot**.

## `test_masquage_colonne_verifiee.py` -- masquer une colonne (9 cas)

Le retour terrain donnait une **recette complete en cinq etapes**. La mesure sur les **8 022
sources livrees** du pack en confirme quatre, en **corrige une**, et en laisse une **non
etablie**. Ces trois statuts doivent rester distincts dans la page -- c'est ce que les cas
gardent.

- **Les deux contextes sont mesures**, pas devines : `ZoomEnteteTableau` vit dans **718**
  programmes, **tous** de la famille zoom ; `XmeListGetId` dans **119**, dont **89 % sans
  aucun `Zoom.Idtableau`**.
- **La signature du retour terrain est fausse.** Il ecrit `XmeListGetId("NomDuTableau")` : un
  argument, le nom en premier. Le standard en passe **quatre**, le nom en **troisieme**. Le cas
  4 rejoue la forme fautive.
- **Le champ existe, les valeurs non.** `COLUMNINFO.Affichage` est verifie dans le dictionnaire
  systeme (position 903, sur 40 champs) ; les constantes `AFFCOL_*` n'apparaissent nulle part.
  Le cas 7 garde **la distinction** : effacer la reserve ferait croire que tout est etabli,
  l'etendre au champ ferait croire que rien ne l'est.

Validation : **9 mutations, 9 discriminantes**. Le harnais a trouve **trois faiblesses de ma
livraison**, toutes de la meme famille -- une assertion satisfaite par **une autre occurrence**
du meme texte. `119` apparait deux fois dans la page (« 119 » et « 106 sur 119 ») ; « ne pas
confondre » apparait aussi dans le titre de section et le sommaire, sans rapport avec les deux
champs qu'il devait proteger. Les trois cas sont desormais ancres sur **leur ligne de tableau**.

> **C'est la huitieme occurrence de cette classe sur le cycle.** La regle est simple et je
> continue de l'oublier : **ancrer sur la phrase entiere, jamais sur un mot ni sur un nombre
> isole.**
