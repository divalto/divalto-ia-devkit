# Tests du skill linting-diva-code

Suites executables, **sans poste Divalto** : chaque cas fabrique un fichier DIVA minimal
en ISO-8859-1 + CRLF dans un repertoire temporaire, lance `scripts/lint_diva.py` dessus et
compare les codes de regles remontes.

```
py .claude/skills/linting-diva-code/tests/run_all.py
```

A lancer apres **toute** modification de `scripts/lint_diva.py`.

---

## Pourquoi ces tests

Un faux positif systematique ne degrade pas un peu le rapport : il le rend **inutile**.
Un agent (ou un developpeur) qui voit le meme avertissement sur tous les fichiers d'une
famille arrete de lire le rapport, et rate les vrais defauts au passage. Les cas ci-dessous
rejouent chacun un faux positif **reellement remonte par un partenaire**, et gardent en
meme temps la detection legitime que la correction ne doit pas casser.

---

## test_faux_positifs.py

| Groupe | Ce qui est rejoue |
|--------|-------------------|
| **En-tetes de surcharge** (#293, #307) | Un `.dhpt` de surcharge s'annonce `xwin-s-projet` et un sous-projet de surcharge `xwin-s-sprojet`. L'ancien controle testait la **sous-chaine** `xwin-projet`, que `xwin-s-projet` ne contient pas -> constat sur tous les fichiers de surcharge. Le controle est desormais un motif **ancre** en debut de ligne acceptant les 4 formes. Mesure sur projet reel : **211 constats -> 0** sur 211 fichiers projet de surcharge. |
| **Matrice complete** | Les 8 croisements (2 extensions x 4 en-tetes) : un en-tete valide pour un type ne doit jamais etre accepte pour l'autre. La matrice verifie le **code exact** remonte, pas seulement sa presence -- **UN code par extension** : `P04` pour le `.dhps`, `P05` pour le `.dhpt`. Auparavant un `.dhpt` mal en-tete remontait **les deux** pour un seul defaut, et `xwin-s-sprojet` echappait a P05 (la sous-chaine `xwin-sprojet` n'y figure pas -- meme faiblesse que celle corrigee sur P04, laissee deux lignes plus loin). Plus les tolerances du motif : espaces de tete, insensibilite a la casse. |
| **Gardes** | Un `.dhpt` portant un en-tete de sous-projet reste signale (P05, vrai melange) ; un en-tete absent ou invalide reste signale (P04 sur `.dhps`, P05 sur `.dhpt`). |
| **CI01 -- audit de convention** (#243) | `SetModuleInfo` **n'est pas obligatoire** : son absence ne provoque aucune erreur de compilation -- mais l'information est lue a l'execution par `ModuleInfo`, dont Divalto se sert pour afficher la version du module. Le standard la pose systematiquement, le specifique est **libre**. CI01 est donc un audit de convention : **muette par defaut**, activable par `--rules CI01`. |
| **CI01 -- fenetre de recherche** (#243) | La cause reelle du bruit n'etait pas le type de fichier mais la fenetre des **100 premieres lignes** : un masque decrit d'abord `[masque]`/`[enregistrements]`/`[bloc]`, son bloc `[diva]` (et donc `SetModuleInfo`) arrive bien au-dela. Les cas verifient qu'un masque dont le marqueur est **apres la ligne 100** est desormais muet, et qu'un masque qui en est reellement depourvu reste signale. |
| **Garde-fou du mecanisme** | Le retrait de CI01 du jeu par defaut passe par un ensemble `REGLES_HORS_DEFAUT` cable dans les 9 points de dispatch. Deux cas verifient qu'une regle normale (S01, L01) reste bien active par defaut -- sinon le mecanisme aurait desactive tout le linter en silence. |

**Verification de discrimination** : jouee contre la version anterieure de `lint_diva.py`,
la suite tombe sur **13 cas** (6 P04, 5 CI01, 1 fenetre x2, 1 severite) et les 16 autres
passent -- ce sont les gardes de non-regression.

---

## test_coherence_catalogue.py

Invariants du **catalogue de regles** lui-meme. La table `RULES` n'est pas lue par le
moteur : elle ne sert qu'a valider les codes passes a `--rules`. Le comportement reel vit
dans les `rule_map` de chaque dispatcher et dans la severite codee en dur de chaque
`check_*`. Rien n'empeche donc les deux de deriver -- et c'est arrive : **`R07` a ete
declaree au catalogue, documentee dans `rules-recordsql.md`, et n'a jamais eu
d'implementation**. Une regle annoncee qui ne s'execute pas est pire qu'une regle absente :
un agent croit disposer d'un controle qu'il n'a pas.

| Invariant | Ce qu'il empeche |
|-----------|------------------|
| Aucune regle **morte** | Une regle declaree dans `RULES` sans etre dispatchee (le cas `R07`) |
| Aucune regle **fantome** | Une regle dispatchee sans figurer au catalogue |
| `RULES['types']` == extensions reellement cablees | Un catalogue qui annonce une portee differente de la portee reelle |
| Severite declaree == severite emise | Une regle annoncee `warning` qui remonte en `error` |
| Aucune regle **V2 declaree dans `RULES`** | La convention du skill : une regle reportee vit dans la page de reference avec la mention `*V2*`, jamais au catalogue actif. C'est celle que `R07` violait. |
| Aucune **nouvelle** regle non documentee | La dette actuelle (9 regles) est **gelee** dans `DETTE_DOC` : le test bloque la 10e. Ne jamais allonger la liste pour faire passer le test -- documenter la regle a la place. Le test signale aussi une regle devenue documentee restee dans la liste. |

**Verification de discrimination** : jouee contre la version anterieure de `lint_diva.py`,
la suite tombe sur **2 cas**, tous deux nommant `R07`.

---

## Convention

- Les fichiers de test sont ecrits en **ISO-8859-1 + CRLF** (comme de vrais fichiers DIVA),
  jamais en UTF-8 : le linter controle l'encodage, un fichier de test mal encode ferait
  remonter des faux constats (P01/D05/E10).
- Les cas lisent la sortie **JSON** du linter (le script prefixe une ligne
  `Analyse de ...` sur stderr, le helper la saute).
- Aucun chemin absolu : tout se passe dans un `tempfile.mkdtemp()` nettoye en `finally`.
