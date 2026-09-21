# Tests du skill coding-diva-advanced

```bash
py .claude/skills/coding-diva-advanced/tests/run_all.py
```

Aucun prerequis : pas de DLL, pas d'ERP installe, pas de reseau. Les suites ne lisent que
les fichiers du skill. Un cas qui ne s'execute pas est un echec, jamais un "non applicable".

## Suites

| Suite | Cas | Ce qu'elle protege |
|-------|-----|--------------------|
| `test_syntaxe_verifiee.py` | 20 | La concordance entre `reference/syntaxe-de-base.md` et le releve `reference/keywords-verifies.json` |
| `test_surcharge_verifiee.py` | 16 | La concordance entre `reference/overwrite-pattern.md`, le releve et **deux autres skills** (`manipulating-dhsf-screens`, `querying-diva-graph`) |
| `test_recordsql_verifiee.py` | 15 | La concordance entre `reference/recordsql-advanced.md`, le releve, et la fiche `CI03` de `linting-diva-code` |
| `test_appels_programmes_verifiee.py` | 14 | La concordance entre `reference/tunnels.md`, `reference/overwrite-pattern.md`, le releve, et la fiche d'erreurs de `compiling-diva-projects` |
| `test_log_anomalies_verifiee.py` | 11 | La concordance entre `reference/log-anomalies.md`, le releve, et le skill `managing-diva-error-messages` |

## Helpers partages

`_communs.py` porte `lire`, `nu` et `plat`. Ils ont d'abord ete **dupliques** dans deux suites, et le meme defaut y a ete corrige deux fois -- a la troisieme suite la divergence devenait certaine. C'est le motif de en miniature.

Le defaut en question valait la peine : `nu()` supprimait les `_` pour gerer les italiques Markdown, et **mutilait tous les identifiants** --
`H_EOF` devenait `HEOF`. Trois cas echouaient sur des chaines pourtant presentes dans la page.

## Ce que la suite d'appels inter-programmes garde (LOT E)

Trois enseignements, chacun venu d'un defaut reel :

- **Un exemple conforme n'est pas une regle.** `tunnels.md` ecrivait deja
  `ProgramCall("MONPROG.dhop")` dans son bloc de code, sans jamais dire que l'extension est
  obligatoire. Le cas 2 exige une phrase, pas la seule presence de l'extension.
- **Ne pas laisser une correlation devenir une cause.** Le standard ecrit l'extension dans
  100 % de ses appels litteraux ; le RETEX en concluait que le nom nu « ne fonctionne pas ».
  La mesure ne dit pas ca. Le cas 4 garde les deux sens : la reserve doit etre presente, et
  l'affirmation d'echec absente. Sa premiere version interdisait la chaine « le nom nu
  echoue » n'importe ou dans la page -- et tombait sur la mise en garde elle-meme. **Un
  controle qui interdit de nommer ce qu'on refute est inutilisable** : il verifie desormais
  la phrase, pas le fichier.
- **Le cas 10 rejoue un defaut reel** : la page inversait le sens de la dependance entre
  `gttmpce` et `gtpmpce`, alors que le bloc de code juste au-dessus etait correct -- ce qui
  la rendait invisible a la relecture. Le cas exige la bonne phrase **et** interdit la
  mauvaise.

Validation : **14 mutations, 14 discriminantes**. Et le rejeu des versions d'avant le lot
fait tomber **12 des 14 cas**. Les deux qui passent avant comme apres sont les gardes
preventives -- anonymisation et resolution des liens : elles ne gardent pas un contenu neuf,
elles empechent une regression future. Le harnais a trouve deux defauts de la livraison : le
cas 12 etait satisfait par le seul titre de section et survivait a la suppression de
l'enumeration qu'il croyait garder (il compte desormais les rangs du tableau), et le cas 13
appliquait son controle d'anonymisation a une page hors perimetre.

## Le defaut #252, et pourquoi il a survecu tout le cycle

La regle du booleen DIVA (`NON = 1`, `OUI = 2`, `0`/espace = non renseigne) ne vivait que
dans le `SKILL.md` et dans une **eval** -- et les deux etaient **faux** (`NON = 0`, « etat
intermediaire = 1 »). **Aucune page de reference ne la portait, donc aucun cas ne la
confrontait a quoi que ce soit.** Une affirmation fausse peut vivre indefiniment dans un
endroit que rien ne relie au reste.

Le cas 18 confronte desormais les **trois** endroits -- sommaire, evals, pages de reference
-- les uns aux autres. Et les cas 17 et 18 partagent un helper, `phrases_prescrivant()` :
interdire la chaine « NON = 0 » dans tout le fichier ferait tomber le controle sur la note de
correction elle-meme. Le controle porte donc sur la **phrase**, et n'accepte l'ancienne
formulation que lorsqu'elle est explicitement refutee. C'est la meme lecon qu'au LOT E, et
elle a resservi le lot suivant.

## #256 : deux regles vraies que rien ne portait

Meme forme que #252, deux fois. La regle de concatenation (`&`, pas `+`) existait -- **dans
le `SKILL.md` seul**, donc hors de portee de tout cas de test ; et elle ne couvrait que la
forme `+`, pas les crochets, qui etait celle du cas vecu. La regle des champs TABLEAU, elle,
n'existait **nulle part cote code** : le dictionnaire etait couvert par un autre skill, mais
pas la facon d'y acceder.

Le cas 20 garde surtout la **raison**, pas le rituel. Le RETEX disait « toujours verifier
dans le dictionnaire » -- juste, mais sans motif. La mesure donne le motif : **148 noms de
champ sur 615 designent un tableau dans un enregistrement et un scalaire dans un autre**.
C'est pour ca qu'un autre programme ne prouve rien. Sans cette phrase, la regle redevient une
incantation qu'on abandonne des qu'elle coute.

## Ce que la suite du journal des anomalies garde (LOT F)

Ce lot a ete traite **sans le graphe** -- `diva-mcp` etait indisponible. Les mesures viennent
de la lecture des fichiers de messages d'un pack standard, avec le skill
`managing-diva-error-messages`. Trois consequences, toutes gardees par des cas :

- **Une provenance inhabituelle se declare.** Le cas 1 exige que le releve dise que ce bloc
  ne vient **pas** du graphe. Une mesure rangee a cote des autres sans mention ferait croire
  a une interrogation qui n'a pas eu lieu.
- **Le mecanisme prime sur la convention.** « 9999 = texte libre » est vrai par usage ; le
  libelle `$1` en est la cause. Le cas 3 refuse une page qui garderait l'usage et perdrait la
  cause -- ce serait une regle juste par correlation de plus.
- **Les exceptions mesurees ne se taisent pas.** Le prefixe de `a5ferr` et les deux fichiers
  sans `9999` rendent la regle moins jolie et utilisable. Les cas 4, 5 et 6 les gardent, ainsi
  que la contre-observation levee sur le code `9000`.

Cote **#96**, les trois cas ajoutes a la suite de syntaxe gardent l'inverse d'une affirmation :
les quatre inexistences de ce lot **n'ont pas ete interrogees au graphe**, et le cas 16 verifie
que leur reserve reste ecrite. La retirer transformerait une position en verification.

## Pourquoi ces tests ne parlent pas au MCP

Le plugin pose que **les scripts n'appellent jamais le MCP** : interroger le graphe est le
travail de l'orchestrateur LLM. Un test qui appellerait `get_native_keyword_doc`
violerait cette regle, et deviendrait de surcroit dependant du reseau et d'une cle API.

Le partage est donc :

- **l'orchestrateur LLM** interroge le graphe et consigne le resultat -- date, source,
  niveau de preuve -- dans `keywords-verifies.json` ;
- **la suite**, deterministe et hors ligne, verifie que la page et le releve concordent.

Ce que la suite garantit reellement : **aucune affirmation de la page n'est ecrite sans
trace**. Ce qu'elle ne garantit pas : que le releve soit a jour. Cela se refait a la main,
en rejouant les appels et en actualisant `date_verification`.

## Ce qu'un cas attrape

Le defaut d'origine de ce lot : un RETEX affirmait que `Round` n'existe pas. `Round`
existe -- comme instruction de mode sans parametre. Le cas 3 refuse desormais qu'une page
affirme une inexistence sans entree au releve, **et** qu'elle en affirme une contre un
releve qui dit le contraire.

Les 13 cas ont ete valides par 17 mutations : pour chacun, une copie du skill portant
exactement le defaut vise a ete fabriquee, et le cas vise tombe dessus. Un test qui passe
ne prouve rien tant qu'on n'a pas montre qu'il sait echouer. Le harnais a d'ailleurs
trouve trois defauts de la livraison : un trou dans le cas 3 (affirmer "X n'existe pas"
quand le releve donne X existant passait) et, dans le harnais lui-meme, une lecture
apres troncature qui donnait au cas 10 un faux "OK". Le troisieme est venu de
l'architecte, pas du harnais : la page affirmait que `ElseIf` n'existe pas, alors que
la construction existe sous le nom `Elsif`, et rangeait `continue`/`break` parmi les
reflexes C -- les deux existent, dans la famille `Switch`, avec un autre sens. La suite
passait 11/11 dessus : la **liste d'exemptions** du cas 8 couvrait `continue` et
`break`, ce qui desarmait le seul controle capable de le voir. D'ou le cas 12, qui
garde la liste qui garde les autres.
