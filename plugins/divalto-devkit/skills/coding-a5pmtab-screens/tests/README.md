# Tests du skill coding-a5pmtab-screens

```bash
py .claude/skills/coding-a5pmtab-screens/tests/run_all.py
```

Aucun prerequis : pas de DLL, pas d'ERP installe, pas de reseau, pas de MCP.

## Suites

| Suite | Cas | Ce qu'elle protege |
|-------|-----|--------------------|
| `test_a5pmtab_verifiee.py` | 12 | La concordance entre les 3 pages de reference, le `SKILL.md` et le releve `reference/keywords-verifies.json` -- chiffres compris |

## Pourquoi ces tests ne parlent pas au MCP

Le plugin pose que **les scripts n'appellent jamais le MCP** : interroger le graphe est le
travail de l'orchestrateur LLM. Le partage est donc :

- **l'orchestrateur** interroge le graphe, lit les sources livrees, et consigne -- source,
  date, niveau de preuve -- dans `keywords-verifies.json` ;
- **la suite**, deterministe et hors ligne, verifie que les pages et le releve concordent.

## Ce que ces cas gardent en particulier

**La regle du suffixe** (cas 2 et 3). Le suffixe d'une callback ne change pas seulement son
nom : il change sa **signature** -- la forme suffixee ne recoit pas `Id`. C'est l'explication
exacte du message runtime « la fonction attend 0 parametre(s) et l'appelant a place
1 parametre(s) sur la pile », et rien ne la documente ailleurs.

**Le piege `Id` du fichier de prototypes** (cas 4). `objet/proto_a5pmtab.dhsp` ecrit `Id`
sans esperluette sur ses 90 callbacks non suffixees. C'est faux -- `Id` est passe par
adresse. Notre premiere redaction avait **suivi le prototype** ; elle a ete inversee sur
reponse de l'architecte. Le cas 4 exige que la page porte l'**avertissement** et nomme le
fichier fautif, au lieu de prescrire l'inverse.

**Ce que le skill ne pretend pas** (cas 8). Trois points restent non resolus : la valeur de
retour d'`ArretSpecifique` (le RETEX et le prototype se contredisent), le mecanisme exact de
la corruption par `1A`, et la forme correcte d'un aller-retour saisie / tableau. Le cas 8
verifie qu'ils restent declares -- **une page qui prescrirait une valeur de retour serait
pire qu'une page muette.**
