# Tests du skill understanding-integrator-workspace

```
py .claude/skills/understanding-integrator-workspace/tests/run_all.py
```

Aucun poste Divalto requis : chaque cas fabrique un workspace minimal (un `.dhpt` en
ISO-8859-1 + CRLF, un fichier implicite vide) dans un repertoire temporaire.

---

## test_convention_nommage.py

`check_workspace_coherence.py` compare le **nom** d'un `.dhpt` a son **en-tete**. Il
avait donc les deux signaux sous la main -- et faisait confiance au mauvais : un nom
finissant par la lettre `u` declenchait une **`error`** conseillant de passer l'en-tete
en `xwin-s-projet 2.0`.

Or le suffixe `u` est une **convention de nommage**, pas un marqueur. Mesure sur un
workspace reel : `addon mercure ieu.dhpt` (ie-**u**) porte l'en-tete `xwin-projet`,
qui est **parfaitement correct**. Suivre le conseil du script transformait un projet
standard en surcharge declaree : un conseil **activement nuisible**, et le seul de
cette classe de defauts a ne pas se contenter de signaler a tort.

Le constat subsiste -- une divergence nom/en-tete vaut d'etre mentionnee -- mais en
`warning`, sans plus rien prescrire, et en disant explicitement que l'en-tete fait foi
et qu'un nom peut finir par `u` sans etre une surcharge.

| Cas | Ce qui est verifie |
|-----|--------------------|
| Nom en `u` + en-tete standard | le constat existe toujours, **en `warning`**, et **ne compte pas** dans `summary.errors` |
| Contenu du message | il dit que l'en-tete fait foi, **ne prescrit plus** de changer l'en-tete, et mentionne qu'un nom peut finir par `u` sans etre une surcharge |
| Nom en `u` + en-tete de surcharge | aucun constat (les deux signaux concordent) |
| Nom ordinaire + en-tete standard | aucun constat |

**Verification de discrimination** : jouee contre la version anterieure du script, la
suite tombe sur **5 cas** -- dont `severite=error` et `summary.errors=1` -- et 3 gardes
passent dans les deux versions.

---

## Convention

- Le workspace de test est jetable : `tempfile.mkdtemp()` nettoye en `finally`.
- Le `.dhpt` est ecrit en **ISO-8859-1 + CRLF** comme un vrai fichier projet.
- Le script exige `--implicit` et `--confirmed-by-user` (garde-fou R-1 : le
  collaborateur doit avoir valide le fichier implicite). Les cas passent un implicite
  **vide**, suffisant pour l'audit de convention de nommage.
