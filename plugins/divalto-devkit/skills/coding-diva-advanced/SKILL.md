---
name: coding-diva-advanced
description: >
  Reference des patterns avances du langage DIVA : HTTP/REST, JSON/XML, integration .NET,
  surcharge (OverWrite) et portee des declarations Module, module table (mtab),
  RecordSql avance (Reader, Collate, Paging), tunnels inter-modules et appel de programme
  (Ping/Pong, ProgramCall, contexte a transmettre avant le Ping), evenements Harmony.
  Ecriture au journal des anomalies (`*_Log_Ano`, livre de bord).
  Couvre aussi la syntaxe de base la ou elle piege : faux amis (ElseIf, EndFor, Str$, Round),
  matrice des 4 boucles et de leurs Exit/Redo, FReturn/PReturn, Beginf/Beginp, Nature=A.
  A consulter pour generer du code DIVA, pour diagnostiquer un mot-cle qui ne compile pas,
  ou un programme lance qui demarre sans son contexte metier.
---

# coding-diva-advanced

## Contenu

- Quand utiliser ce skill
- **Syntaxe de base : ce que le langage n'a pas**
- Domaines couverts (8)
- Anti-patterns avances
- References

---

## Quand utiliser ce skill

Ce skill est une **reference**, pas un generateur. Le consulter quand :
- L'utilisateur demande un appel HTTP/REST depuis DIVA
- L'utilisateur veut parser du JSON ou XML
- L'utilisateur veut integrer une DLL .NET
- L'utilisateur veut surcharger un module standard (OverWrite)
- L'utilisateur veut creer un module table (mtab) avec controles
- L'utilisateur veut utiliser Reader, Collate, ou Paging sur un RecordSql
- L'utilisateur veut communiquer entre modules (tunnels Ping/Pong)
- L'utilisateur veut gerer des evenements clavier/souris dans un Zoom (Harmony)

Ce skill ne couvre PAS la syntaxe de base (types, procedures, fonctions, boucles, chaines) : elle est implicite dans les autres skills de generation.

---

## Syntaxe de base : ce que le langage n'a pas

DIVA **ressemble** a BASIC. Quand une construction manque, le reflexe -- humain comme
machine -- est de combler avec l'analogie la plus proche. **DIVA diverge precisement a ces
endroits**, et le code produit ne compile pas (ou pire : compile et casse a l'execution).

| Ecrit par reflexe | Origine | Realite DIVA |
|---|---|---|
| `ElseIf` | VB | orthographe : **`Elsif` existe** (un seul « e ») -- ne pas contourner |
| `EndFor` | Pascal | **n'existe pas** -- le terminateur du `For` est `Next` |
| `Str$(x)` | BASIC | la fonction est `Str(x)`, sans suffixe |
| `Round(x)` | style fonction | **piege** : `Round` existe, mais c'est une **instruction de mode** sans parametre |
| `break` / `continue` | C, Python | **existent**, mais dans `Switch` et avec un **autre sens** : `Break` sort du `Switch`, `Continue` enchaine sur le `Case` suivant. Sortir d'une boucle = `Exit*`, la relancer = `Redo*` |
| `Exit` seul | C, VB | **n'existe pas** -- `ExitFor`, `ExitLoop`, `ExitDo`, `ExitRepeat` |

Il n'y a **pas** de sortie de boucle universelle : `ExitFor`, `ExitLoop`, `ExitDo`,
`ExitRepeat` -- et autant d'instructions `Redo*` pour le « continue ».

Les conditions se chainent avec **`Elsif`** (un seul « e »), et `Endif` est
**obligatoire** -- autant de `Endif` que de `If` imbriques.

Un **prototype** (`Proto Function` / `Proto Procedure`) reprend la declaration
**complete** des parametres, et se termine par **`EndProto`** -- obligatoire.

**On ne sort JAMAIS d'un `Switch` par un `ExitFor`/`ExitLoop`/`ExitDo`/`ExitRepeat` ni
par un `Goto`** : le selecteur est empile. Sortir du `Switch` par `Break`, puis quitter
la boucle **apres `Endswitch`**. Le motif fautif -- boucler, tester, sortir des qu'on a
trouve -- est le plus naturel qui soit.

Et pour arrondir, preferer l'indicateur `[ A ]` / `[ T ]` / `[ S ]` porte par
l'affectation : la portee du mode global `Round`/`Truncate` n'est pas documentee.

Deux asymetries qui cassent a l'**execution**, pas a la compilation :

- `FReturn` est **obligatoire** dans une `Function` et prend la valeur de retour ; son absence
  **interrompt le programme**. `PReturn` est **facultatif** et sans parametre.
- `Nature=A` n'a de sens que sur un **parametre formel** (la taille vient de l'appelant).

Detail complet, matrice des boucles et pieges du `For` :
[reference/syntaxe-de-base.md](reference/syntaxe-de-base.md).

> Chaque affirmation d'existence **ou d'inexistence** de cette page est verifiee contre le
> graphe de connaissance et consignee, datee, dans
> [reference/keywords-verifies.json](reference/keywords-verifies.json). C'est la seule
> protection contre l'erreur que ce lot corrige : un RETEX affirmait que « Round n'existe
> pas » -- il existe.

---

## Domaines couverts

| # | Domaine | Cas d'usage | Reference |
|---|---------|-------------|-----------|
| 1 | HTTP/REST | Appel API externe, WebRequest, WebServiceDiva | [http-rest.md](reference/http-rest.md) |
| 2 | JSON/XML | Parsing JSON (JsonOpen), lecture XML (XmlRead), HMP | [json-xml.md](reference/json-xml.md) |
| 3 | Integration .NET | Appel DLL .NET (AssemblyLoad/Invoke) | [dotnet-integration.md](reference/dotnet-integration.md) |
| 4 | Surcharge | OverWrittenBy/OverWrite, convention nommage U/UU, codes retour hooks Zoom* | [overwrite-pattern.md](reference/overwrite-pattern.md), [zoom-hooks-reference.md](reference/zoom-hooks-reference.md) |
| 5 | Module table (mtab) | Controles en cascade Switch TRUE, initialisation defauts | [module-table.md](reference/module-table.md) |
| 6 | RecordSql avance | Reader, Collate, Paging, Where fluent, RecordSqlPtr | [recordsql-advanced.md](reference/recordsql-advanced.md) |
| 7 | Tunnels et appel de programme | Ping/Pong, PingLocal, ProgramCall, **contrat de contexte avant le Ping** | [tunnels.md](reference/tunnels.md) |
| 8 | Harmony | Record Harmony, codes touches, timer, ZoomArret | [harmony-events.md](reference/harmony-events.md) |
| 9 | Journal des anomalies | `*_Log_Ano`, code 9999, livre de bord | [log-anomalies.md](reference/log-anomalies.md) |

---

## Anti-patterns avances

**NE JAMAIS generer :**
- `+` pour concatener → utiliser `&`
- `ForEach` → DIVA n'en a pas, utiliser `ListBegin/ListNext/ListEnd` ou Reader
- `Try/Catch` → DIVA n'a pas d'exceptions, utiliser codes retour + `ErrorFatal`/`ErrorWarning`
- `Class` → DIVA n'a pas d'OOP, utiliser les modules mchk
- Threads → utiliser `ProgramCall` pour l'execution parallele
- Oublier `WebRequestClose(ticket)` apres un appel HTTP (fuite)
- Oublier `JsonClose(ticket)` apres parsing JSON
- `GG_*` pour un module DAV → utiliser `GT_*`
- `GT_*` pour un module Production → utiliser `GG_*`

**Pieges de syntaxe DIVA (a priori mainstream souvent faux) :**
- `;` introduit un **commentaire** (pas une fin d'instruction) ; le separateur de ligne logique est `|` (ni un OU, ni un commentaire)
- constante booleenne standard : **`NON = 1`, `OUI = 2`** -- ne jamais supposer `OUI = 1` ni `NON = 0` ; **`0` (ou l'espace) veut dire « non renseigne »**, pas « non ». Voir la section dediee de `reference/syntaxe-de-base.md`
- date du jour : `today()` -- le champ `MZ.DateJour` n'existe pas
- borne / valeur par defaut : variable locale typee + `init` (ex `init InvNo_Defaut = '9'`) plutot qu'une constante en dur
- `_` de continuation dans un `If` multi-ligne combine a des appels prefixes module -> `Erreur 37` ; ecrire la condition sur une seule ligne

---

## References

- [Syntaxe de base](reference/syntaxe-de-base.md) -- faux amis, matrice des 4 boucles (sortie + continue), FReturn/PReturn, Beginf/Beginp, Nature=A
- [Mots-cles verifies](reference/keywords-verifies.json) -- le releve date des verifications, avec le niveau de preuve de chaque entree
- [HTTP/REST](reference/http-rest.md) -- WebRequest API, WebServiceDiva
- [JSON/XML](reference/json-xml.md) -- JsonOpen/Parse, XmlOpen/Read, HMP
- [Integration .NET](reference/dotnet-integration.md) -- AssemblyLoad, codes erreur
- [Surcharge](reference/overwrite-pattern.md) -- OverWrittenBy/OverWrite, convention U, pattern canonique de procedure surchargee, portee de `Module` (non transitive, et sans effet sur les enregistrements)
- [Hooks Zoom*](reference/zoom-hooks-reference.md) -- grille de codes retour O/N/I/C, couverture validee, pattern d'utilisation
- [Module table](reference/module-table.md) -- mtab, Switch TRUE, controles
- [RecordSql avance](reference/recordsql-advanced.md) -- Reader, Collate, Paging, Direct, Transactions, Performance, Callbacks
- [Tunnels](reference/tunnels.md) -- Ping/Pong, PingLocal, ProgramCall (extension `.dhop` obligatoire, contrat de contexte a remplir avant le `Ping`, piege du `ProgramExit` silencieux)
- [Harmony](reference/harmony-events.md) -- Evenements, codes touches, timer
- [Journal des anomalies](reference/log-anomalies.md) -- `*_Log_Ano` : le 1er parametre est un **numero de message**, jamais `MZ.Dos` ; le code `9999` et ses deux pieges mesures

> **Ecrans a tableaux A5PMTAB** -- callbacks `DefProcInterro_*` / `DefProcSaisie_*`,
> `Creer_Parametre`, `AP_Interroger_Tableaux` / `AP_Saisir_Tableaux` : ce n'est PAS ici.
> Voir le skill [`coding-a5pmtab-screens`](../coding-a5pmtab-screens/SKILL.md). Les ecarts
> de declaration d'une callback A5PMTAB **compilent** et cassent a l'execution sans message.
