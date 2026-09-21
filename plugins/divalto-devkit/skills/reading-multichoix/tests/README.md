# Tests du skill reading-multichoix

```
py .claude/skills/reading-multichoix/tests/run_all.py
```

**7 des 9 cas tournent partout**, sans DLL et sans fichier. Les fonctions de décodage du
script sont **pures** — elles travaillent sur des enregistrements de 420 octets, pas sur un
fichier — donc on les alimente avec des enregistrements **fabriqués** aux offsets
documentés, comme les autres suites du plugin fabriquent leurs dictionnaires en temporaire.

**2 cas** exigent un vrai fichier, parce qu'ils mesurent le **processus** et non la logique :
l'encodage de la sortie **redirigée** et les **codes retour**. Pour les activer :

```
set MULTICHOIX_TEST_FILE=<chemin d'une COPIE d'un XXfdmc.dhfi>
```

> **Ne jamais pointer un fichier de production**, même si les scripts ne font que lire.

Ces deux cas se déclarent **non applicables** — jamais « réussis » — quand la DLL ou le
fichier manquent. Un test qui passe faute de pouvoir mesurer donne une assurance qu'il n'a
pas vérifiée. Le statut `N/A` est compté à part du bilan.

> **État initial de cette suite** : 5 cas sur 8 ne s'exécutaient **jamais** par défaut. Elle
> garantissait que la doc *dit* la bonne chose, pas que le code *fait* la bonne chose. La
> refonte a déplacé 4 cas de comportement du conditionnel vers l'inconditionnel, en
> remplaçant le fichier réel par des enregistrements fabriqués.

---

## test_sortie_machine.py

Couvre le contrat de sortie de `read_multichoix.py` (RETEX #170).

### Pourquoi ces tests

L'issue #170 rapportait que `--all-details` rendait une **liste de chaînes** au lieu
d'objets, cassant tout consommateur machine :

```
AttributeError: 'str' object has no attribute 'get'
```

**Ce défaut n'était plus reproductible** au moment du traitement : le mode rend bien un
dictionnaire indexé par Nc. Le refactor qui a introduit `_build_detail()`, partagée par
`--detail` et `--all-details`, l'avait corrigé — sans que personne le sache, et **sans qu'un
test empêche la forme de redériver**. C'est le rôle des cas 4 à 7.

### Ce que la vérification a trouvé à la place

Le mode restait cassé **pour le public que la doc lui assigne** : **la sortie n'était pas en
UTF-8**. Redirigée, elle sortait dans l'encodage local (cp1252 sous Windows FR). Un dump
`--all-details` du dictionnaire standard porte **842 caractères accentués** — le consommateur
plantait avec `UnicodeDecodeError` au lieu de `AttributeError`. Le script frère
`read_isam.py` forçait déjà son encodage ; celui-ci non (**5ᵉ asymétrie entre scripts
frères** du cycle).

### Ce que les enregistrements fabriqués apportent en plus

Ils portent des **accents en dur** — la donnée même qui a cassé le consommateur — et un
**Type 4**, qu'un fichier réel donné ne contient pas forcément. Le jeu fabriqué couvre donc
des cas que la mesure ne couvre pas, et il rend le cas 6 possible : comparer côte à côte les
formes de `--list` et `--all-details`, **la confusion d'origine de l'issue**.

### Une erreur de mesure, transformée en garde-fou

Le cas 9 fige les codes retour parce qu'une **première mesure les avait donnés faux** : `$?`
après un pipe rapporte le code du **dernier élément du pipe**, pas celui du script.
`--resolve` semblait sortir en `0` alors qu'il sort bien en `1` — il n'y avait rien à
corriger. Les cas de mesure lancent désormais le script **en redirection**, jamais en pipe.

### Table des cas

| # | Ce qui est vérifié | Fichier requis ? |
|---|--------------------|------------------|
| 1 | le script force sa sortie en UTF-8, **avant** toute écriture, comme son frère | non |
| 2 | la doc documente la **forme** de `--all-details`, pas seulement son contenu | non |
| 3 | la doc annonce le contrat UTF-8, en tête du format de sortie | non |
| 4 | `multichoix` est un **dict**, `entries` une **liste d'objets** | non |
| 5 | `lookup` présent pour le Type 3, **absent** pour les Types 1 et 4 ; `ideb`/`ifin` en entiers | non |
| 6 | `--list` et `--all-details` n'ont **pas** la même forme — la confusion d'origine | non |
| 7 | `--detail <NC>` == l'entrée correspondante de `--all-details`, et `found: false` sur un Nc absent | non |
| 8 | sortie **redirigée** décodable en UTF-8, **0 octet cp1252** | **oui** |
| 9 | codes retour figés, mesurés **sans pipe** | **oui** |

### Vérification de discrimination

Jouée contre l'état d'avant (restauration prouvée par empreinte) :

| Contexte | Résultat |
|---|---|
| sans fichier de mesure | **3 / 9 tombent** (cas 1 à 3) |
| avec fichier de mesure | **4 / 9 tombent** (+ cas 8, l'encodage) |

Les cas 4 à 7 passent avant comme après : la forme était **déjà correcte**, et rien ne la
protégeait. Ce sont des **gardes de non-régression**, et c'est précisément ce qui manquait —
le défaut d'origine avait été réparé en silence.

---

## Convention

- Aucun chemin absolu dans les cas : le fichier de mesure vient de l'environnement.
- Le script est lancé **en redirection**, jamais en pipe — sinon le code retour mesuré est
  celui du pipe.
- Les enregistrements fabriqués utilisent les **offsets du module** (`M.OFF_*`), pas des
  constantes recopiées : si la structure change, les fixtures suivent.
- Le cas 2 vérifie la **documentation** en même temps que le code : c'est le flou de la doc
  (contenu décrit, forme non dite) qui avait laissé la dérive passer inaperçue.
