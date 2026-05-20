---
name: rendering-preaction-livrable
description: >
  Rend le livrable final d'une analyse pre-action UC-100 a partir d'un facts.json.
  Produit un markdown unique structure en 3 couches de lecture : strategique (2 min,
  chef projet), tactique (15 min, dev implementeur), technique (30 min, auditeur).
  Autonomie documentaire stricte : aucun path absolu, aucune balise [X.12] ou
  [CONFIRME X.13], aucun chemin C:/ dans le livrable. Les references vivent
  exclusivement dans le facts.json. Un renderer deterministe (Jinja2) transforme
  chaque claim en fragment markdown selon sa couche et son kind. Le validator
  refuse tout rendu contenant un stub, une balise HTML non supportee en Mermaid,
  un pronom relatif apres un label, ou une ref visible. A utiliser apres
  build_facts.py pour produire le livrable destine au developpeur.
---

# Rendering Pre-Action Livrable

## Contenu

- Quand utiliser
- Utilisation rapide
- Regles de rendu (fond vs forme)
- Structure des 3 couches
- Validator anti-regression
- Scripts disponibles
- References

---

## Quand utiliser

Apres avoir genere le `facts.json` via `building-preaction-report/build_facts.py`,
ce skill produit le livrable markdown destine au developpeur qui consomme l'analyse.

**Separation fond / forme** (principe premier) :

- Le `facts.json` (fond) contient toutes les refs aux sources : path absolu, line,
  status X.12/X.13, snippet, enclosing. Machine-lisible, auditable.
- Le livrable `.md` (forme) **n'affiche aucune de ces refs**. Il se lit seul,
  sans que le lecteur ait besoin de consulter d'autres documents. Un auditeur
  qui souhaite verifier une affirmation ouvre `facts.json` ou lance le skill
  `reviewing-preaction-facts` -- pas le livrable.

---

## Utilisation rapide

```
py .claude/skills/rendering-preaction-livrable/scripts/render_livrable.py \
    --facts output/preaction-<slug>-<date>.facts.json \
    --output-dir output
```

Sortie : `output/preaction-<slug>-<date>.md` (UTF-8 + LF).

Le rendu echoue si le livrable contient un path absolu ou une balise X.12/X.13
(code retour 4). Dans ce cas, corriger le template ou le facts.json et relancer.

---

## Regles de rendu (fond vs forme)

Les templates Jinja2 appliquent **3 regles dures** :

1. **Aucun `{{ source.path }}` nulle part.** Les chemins absolus restent dans facts.json.
2. **Aucun `{{ source.line }}` nulle part.** Les numeros de ligne restent dans facts.json.
3. **Aucune balise `[X.12]` / `[CONFIRME X.13]` / `[DISPARU X.13]` / `[NOUVEAU X.13]`
   dans les fragments textuels.** Le statut est signale differemment selon la couche
   (confiance, verdict, selection), pas sous forme de disclaimer.

Les **noms de symboles** (fonctions, procedures, constantes, tables) sont autorises
partout -- ce sont du contenu metier, pas des references. Les **noms de fichiers
courts** (`gtppctm310.dhsp`) sont autorises en couches tactique/technique s'ils
aident la navigation -- sans chemin, sans ligne.

---

## Structure des 3 couches

Voir [reference/layering-preaction.md](reference/layering-preaction.md) pour le
detail des audiences, duree de lecture et regles de routage `claim -> layer`.

Squelette du livrable :

```markdown
# Analyse pre-action : <titre>

## Strategique (2 min)
- Verdict : <one-liner>
- Domaine / type / confiance / couverture
- Action prioritaire (derivee du premier claim action_site)

## Tactique (15 min)
- Chaine d'appels (Mermaid depuis call_chain claim)
- Plan d'action (action_site claims)
- Exemples a etudier (example claims, symboles nommes)
- Commandes de verification (verification claims)
- Etude d'impact (impact_caller claims)

## Technique (30 min)
- Constantes et codes metier (literal_table claims)
- Parametrage dossier (dossier_param claims)
- Fonctions du langage utiles (function claims)
- Points d'attention (overwrite_warning claims)
- Pistes d'exploration complementaires (hint claims, si inclus)
```

Une couche complete sans claims est omise silencieusement (pas de section vide).

---

## Validator anti-regression

Le script `render_livrable.py` execute `validate_report(livrable)` avant d'ecrire
le fichier. La liste des patterns interdits comprend :

**Patterns communs** (heritage de `build_report.py`) :

- Directive LLM residuelle (`LLM (CP5) :`, `a preciser par le LLM`, etc.)
- Stub `[a definir]`, `[a preciser]`, `TODO`, `FIXME`, `XXX`, `a completer`
- Pronom relatif apres label de bullet (`- **X** : qui/que/dont ...`)
- Italique avec placeholder HTML-like (`_... <champ> ..._`)
- Balise HTML non rendue en Mermaid (`<code>`, `<em>`, `<span>`, `<strong>`)

**Patterns specifiques separation fond/forme** :

- Chemin absolu Windows (`C:/Developpements`, `c:\`) : **interdit dans le livrable**
- Marqueur `[X.12]` / `[CONFIRME X.13]` / `[DISPARU X.13]` / `[NOUVEAU X.13]` :
  **interdit dans le livrable**

Si le validator detecte une violation, le rendu echoue (exit 4) avec la liste
des violations. Corriger le template correspondant et relancer.

---

## Scripts disponibles

```
scripts/render_livrable.py                          # CLI principal
scripts/templates/livrable.md.j2                    # squelette (3 includes)
scripts/templates/couches/strategique.md.j2
scripts/templates/couches/tactique.md.j2
scripts/templates/couches/technique.md.j2
scripts/tests/test_render.py                        # tests golden
scripts/tests/fixtures/*.facts.json                 # fixtures d'entree
```

### Lancer les tests

```
cd .claude/skills/rendering-preaction-livrable/scripts
py -m unittest tests.test_render -v
```

Couverture : rendu nominal (3 couches presentes, structure correcte) + assertions
anti-ref (grep sur livrable rendu).

---

## References

- [reference/layering-preaction.md](reference/layering-preaction.md) -- regles
  de routage claim -> couche, audiences, duree de lecture.
- `.claude/skills/building-preaction-report/SKILL.md` -- skill amont qui produit
  le facts.json.
