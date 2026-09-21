# Ordre de compilation en migration / rebase

> Lors d'une migration de pack (rebase sur un nouveau Service Pack ou une nouvelle
> version X.N), l'**ordre de compilation** n'est pas neutre : un mauvais ordre peut
> effacer silencieusement des surcharges ou casser la reconstruction. Ce fragment
> couvre les deux pieges terrain.

## Contenu

- Regle d'or : bases standard d'abord, surcharges ensuite
- Piege overWrite : recompiler une base apres sa surcharge efface la fusion
- Verifier l'integrite des surcharges (`check_overwrite_order.py`)
- Dependances inter-projets non declarees : le contournement deux passes

---

## Regle d'or

**Compiler les bases standard d'abord, les surcharges `overWrite` ENSUITE.** La
surcharge doit toujours etre l'objet le **plus recent** de sa paire. C'est la regle
qui evite le piege ci-dessous.

---

## Piege overWrite -- recompiler une base apres sa surcharge efface la fusion

Un module `OverWrite <base>.dhop` ne produit **pas** un objet separe : a la
compilation, ses procedures sont **fusionnees DANS l'objet `<base>.dhop`**.

Consequence : si, apres avoir compile la surcharge, on **recompile le standard
`<base>`** (ordre inverse lors d'un rebase), l'objet `<base>.dhop` est regenere
**propre** et **perd toutes les procedures de la surcharge**.

**Symptome runtime** : le comportement **standard** reapparait (les hooks de
surcharge ne sont plus appeles) -- jusqu'a un blocage ou une boucle si la logique
metier dependait d'une procedure de surcharge appelee par le mecanisme standard.
Le piege est silencieux : 0 erreur de compilation, le probleme n'apparait qu'a
l'execution.

**Signature du diagnostic** : une procedure de surcharge (ex. `<ProcSurcharge>`) est
**presente** dans l'objet de l'overlay (`<overlay>.dhop`) mais **absente** de l'objet
de base charge au runtime (`<base>.dhop`) ; et la **date** de `<base>.dhop` est
**posterieure** a celle de l'overlay (signe que le base a ete recompile en dernier).

---

## Verifier l'integrite des surcharges -- `check_overwrite_order.py`

Le script verifie l'etat resultant apres compilation, sur les deux signaux
(date + presence du symbole).

**Paire explicite (fiable)** -- on connait la surcharge et la/les procedure(s) a controler :

```
py .claude/skills/migrating-erp-downgrade/scripts/check_overwrite_order.py \
    --base "objets/<base>.dhop" \
    --overlay "objets/<overlay>.dhop" \
    --symbols "<ProcSurcharge1>,<ProcSurcharge2>"
```

Pour chaque symbole : `in_base` / `in_overlay` / `lost` (present overlay mais absent
base = surcharge effacee). `date_inversion=true` si le base est plus recent que
l'overlay. `anomaly=true` si l'un des deux signaux est leve. Exit 1 si anomalie.

**Scan d'un repertoire (heuristique de nommage)** -- balayage post-migration :

```
py .claude/skills/migrating-erp-downgrade/scripts/check_overwrite_order.py \
    --objets "objets/"
```

Couple les overlays a leur base par le **nommage** : position 3 (index 2) `u` <-> `t`
(ex. `gtuz099` <-> `gttz099`). Sans `--symbols`, le script propose des **candidats**
proc-like presents dans l'overlay et absents du base (a relire -- heuristique, faux
positifs possibles). En cas de doute sur le couplage, confirmer cote source (declaration
`OverWrite`).

> **Portee** : le moteur (presence de symbole via recherche binaire dans le `.dhop`,
> comparaison de dates) est fiable. La detection **end-to-end** suppose de pointer le
> script sur les objets reels du projet (bases standard **et** overlays de surcharge).

---

## Dependances inter-projets non declarees -- contournement deux passes

En reconstruction (`buildall`), certains projets echouent avec
« **Erreur dictionnaire : Erreur lors de la lecture d'un dictionnaire de RecordSql.
Veuillez recompiler les dictionnaires** » sur des `.dhoq` standard. Cause : des
**dependances entre projets** ne sont pas declarees dans les `.dhps` -> mauvais
**ordre de compilation** (un projet compile avant celui dont il depend).

**Contournement eprouve** : enchainer une **2e passe** en mode construction (`build`)
apres le `buildall` -- les objets compiles au 1er passage servent de base, les
dependances sont alors disponibles, les erreurs residuelles se resolvent.

**Correctif durable** : declarer les dependances manquantes dans les `.dhps` concernes
pour que le `buildall` seul suffise. L'identification precise (quel projet doit compiler
avant quel autre) se fait projet par projet -- voir `managing-diva-projects` pour la
structure `[sousprojets]` / `[communs]` et `compiling-diva-projects` pour la passe de
compilation.
