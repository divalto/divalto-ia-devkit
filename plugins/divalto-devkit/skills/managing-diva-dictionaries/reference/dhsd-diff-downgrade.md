# Diff de dictionnaire et arbitrage de downgrade -- methodologie

> **Statut** : la **compatibilite binaire** (« quelles tables ont change de taille,
> donc quel specifique recompiler ») est **outillee** par `compare_dhsd_versions.py`.
> L'**arbitrage fonctionnel** 3-voies reste **methodologique, sans outil dedie**
> (chantier separe). Cette page sert de garde-fou : tout diff de `.dhsd`,
> manuel ou outille, DOIT respecter les regles ci-dessous, sous peine de conclusions
> fausses (cas reels).

## Contenu

- Pourquoi un diff de dictionnaire est piegeux
- **Deux questions distinctes** : compatibilite binaire vs arbitrage fonctionnel
- **Compatibilite binaire : c'est `Taille=`, pas le nombre de champs**
- Regle 1 -- couvrir les 3 couches (CHAMP / CHAMPS / CHAMPL)
- Regle 2 -- arbitrage downgrade en 3 voies (CUSTOM / ROLLBACK / GEL)
- Lien avec `modify_field_nature.py`

---

## Pourquoi un diff de dictionnaire est piegeux

Comparer deux `.dhsd` (deux versions, ou un downgrade vs son standard) sert a
decider quoi conserver, rebaser ou supprimer lors d'une migration ou d'un
changement de Service Pack. Deux pieges recurrents rendent une analyse
automatique naive **fausse** :

1. ne regarder qu'une seule couche du dictionnaire ;
2. comparer le downgrade a une seule version de reference.

---

## Deux questions distinctes -- ne pas les confondre

Comparer deux `.dhsd` sert a repondre a **deux questions independantes**, qui n'ont ni le
meme critere ni le meme destinataire :

| Question | Critere | Qui agit |
|----------|---------|----------|
| **Compatibilite binaire** -- « mes objets vont-ils encore tourner ? » | la **`Taille=`** du bloc `[TABLE]` | l'integrateur, en **recompilant son specifique** |
| **Arbitrage fonctionnel** -- « ce downgrade a-t-il encore lieu d'etre ? » | la presence/absence de champs sur les **3 couches** | le distributeur, en decidant de conserver / rebaser / adopter |

Les regles 1 et 2 ci-dessous traitent la **seconde**. Elles comparent notamment des
nombres de champs (« un record de selection a 147 champs en downgrade vs 145 cote
standard ») -- ce qui est le bon signal pour **detecter un custom**, et le **mauvais**
pour la compatibilite binaire. D'ou la section suivante.

---

## Compatibilite binaire : c'est `Taille=`, pas le nombre de champs

Un objet compile **memorise la taille** des tables qu'il utilise. Deux objets qui ne
s'accordent pas sur cette taille declenchent a l'execution :

```
enregistrement deja alloue avec la taille X par le module Y
```

> Message **rapporte par le RETEX #110**, non reproduit par nos tests : il faut deux
> objets compiles contre deux dictionnaires divergents et un runtime pour le declencher.

### Pourquoi compter les champs ne marche pas

Le comptage de champs se trompe **dans les deux sens**. Mesure sur un dictionnaire du
standard entre deux versions majeures (763 tables communes), puis sur un pas de Service
Pack (957 tables communes) :

| | Constat |
|---|---|
| **Faux positifs** | **129 tables** ont gagne des champs a **taille constante** -- l'editeur ajoute des champs en consommant sa reserve `Filler` (une table de depots : 31 -> 37 champs a `Taille=500` ; une table tiers : 45 -> 48 a `1400`). Un controle par comptage les signalerait a tort. |
| **Faux negatifs** | **7 des 16 tables** qui changent de taille sur un pas de Service Pack le font a **nombre de champs identique** (une table reste a 16 champs et passe de 13500 a 13700 octets ; une autre, 9 champs, 3700 -> 3750). Un controle par comptage les **manquerait** -- et ce sont precisement celles qui obligent a recompiler. |

### Ce que l'integrateur DOIT faire

Pour chaque table dont la `Taille=` a change : **recompiler son specifique qui utilise
cette table**. C'est obligatoire, pas optionnel -- son specifique a ete compile contre
l'ancien dictionnaire, alors que les objets du standard lui arrivent deja recompiles.

Sur le pas de Service Pack mesure, cela represente **16 tables sur 957** : c'est un
perimetre de travail identifiable, pas le dictionnaire entier.

### Ce que l'integrateur ne PEUT PAS faire

**Corriger un dictionnaire standard.** Les sources du standard sont protegees : il ne
peut pas les recompiler, et l'objet compile porte deja la taille. Face a une anomalie du
standard, sa seule action est de la **remonter a Divalto**.

### L'outil

```
py .claude/skills/managing-diva-dictionaries/scripts/compare_dhsd_versions.py --from <ancien.dhsd> --to <nouveau.dhsd> --format text
```

Classe chaque table en `Taille=` changee / champs ajoutes a taille stable / inchangee /
ajoutee / supprimee, et sort en **code retour 1** des qu'une table a change de taille
(utilisable en garde-fou de script ; 0 = aucun changement de taille, 2 = erreur).
`--only-incompatible` reduit la sortie au perimetre a recompiler.

Il rapporte a part les changements de container `U<NomTable>` -- voir
[dhsd-surcharge-pattern.md](dhsd-surcharge-pattern.md), section « `Filler` vs container
`U` ».

---

## Regle 1 -- couvrir les 3 couches

Un `.dhsd` porte les customisations sur **trois** couches distinctes. Un diff
qui n'en regarde qu'une est **aveugle** au reste :

| Couche | Bloc | Contenu | Risque si ignoree |
|--------|------|---------|-------------------|
| Globale | `[CHAMP]` | Definition des champs (Nature, flags) | rate les champs ajoutes/modifies globalement |
| Table physique | `[TABLE]` / `[CHAMPS]` | Placement des champs dans les tables physiques | -- (couche habituellement regardee) |
| **Record relationnel** | **`[CHAMPL]`** | Records logiques utilises par les **RecordSQL**, vues, selections | **angle mort** : rate les champs custom references par les WHERE |

**Cas reel** : conclusion automatique « ce downgrade est identique au SP
d'origine, gel pur supprimable » -- **FAUSSE**. Deux champs custom etaient en plus
dans le downgrade, mais **uniquement sur un record relationnel `[CHAMPL]`** (ex. un
record de selection a 147 champs en downgrade vs 145 cote standard) -- couche ignoree
par un parser `[TABLE]`/`[CHAMPS]`. Ces champs sont exactement ceux references par
les clauses WHERE des RecordSQL associes. Le downgrade est donc une **vraie
surcharge, NON supprimable**.

> **C'est la couche `[CHAMPL]` qui est la plus pertinente pour l'arbitrage
> RecordSQL** -- un RecordSQL se compile contre un record relationnel.

**Parsing correct** : ne PAS utiliser une regex englobante `\[CHAMPR\](.*?)\[/CHAMPR\]`
-- un `[CHAMPR]` peut envelopper **plusieurs** records. Parser chaque paire
`nom=<NomRecord>` + `[CHAMPL]...[/CHAMPL]` individuellement. Distinguer aussi les
overlays `u` (`[CHAMPR]`/`[TABLEU]`, purement **additifs**) des dictionnaires
complets (qui peuvent porter des **rollbacks**, cf. regle 2).

---

## Regle 2 -- arbitrage downgrade en 3 voies

Pour decider si un downgrade de dictionnaire a encore lieu d'etre au passage d'un
Service Pack (ex. 217E -> 217F), comparer le downgrade au **seul** standard cible
(217F) est insuffisant : on voit les ecarts, **pas leur nature**. Il faut une
comparaison **3-voies** :

- (a) downgrade **vs** standard d'**ORIGINE** (217E)
- (b) downgrade **vs** standard **CIBLE** (217F)

La position de chaque ecart dans les 3 versions le classe :

| Classe | Condition | Signification | Action |
|--------|-----------|---------------|--------|
| **CUSTOM** | present downgrade, absent 217E **ET** 217F | vraie surcharge distributeur | **conserver + rebaser** sur la cible |
| **ROLLBACK** | present 217E/217F, absent downgrade (retire volontairement) | le downgrade annule une evolution standard | decision : maintenir le rollback ou adopter le standard |
| **GEL DE BASELINE** | downgrade **==** 217E a l'identique, aucun custom | le downgrade ne fait que **bloquer** les evolutions du SP | suppression = adoption du standard cible (**decision fonctionnelle**) |

**Le gel pur est le signal le plus important** : un downgrade dont la suppression
n'est qu'une decision d'adoption du standard -- souvent un reliquat. **Mais** ne
conclure « gel pur » qu'apres avoir verifie les **3 couches** (regle 1) -- c'est
precisement la combinaison des deux regles qui a manque dans le cas CCFDD.

**Cas reels** :
- un downgrade == SP d'origine exactement cote `[CHAMPS]` (apparence de gel pur,
  bloquant des evolutions reglementaires du SP cible) -- mais l'analyse 3 couches a
  revele un custom sur `[CHAMPL]` -> finalement **CUSTOM**, non supprimable ;
- un autre downgrade == SP d'origine + quelques customs (une table custom + plusieurs
  champs custom) -> **conserver + rebaser**.

---

## Lien avec `modify_field_nature.py`

Le script `modify_field_nature.py` (modification de Nature + recalcul des
positions) re-propage les couches **physiques** `[TABLE]/[CHAMPS]` et
`[INDEX]/[CHAMPS]`. Il **ne touche pas** a la couche `[CHAMPL]` : si le champ
modifie figure dans un record relationnel, le script emet un **warning**
(`champ present dans N record(s) [CHAMPL]`) et laisse la re-propagation
relationnelle a la charge de l'integrateur. C'est l'application directe de la
regle 1 : la couche `[CHAMPL]` reste un point de vigilance manuel tant que
l'outillage de diff/arbitrage 3-voies n'existe pas.

---

## Voir aussi

Cette page couvre l'arbitrage au niveau **dictionnaire** (structure `.dhsd`, 3 couches).
Pour le processus de **migration de pack** dans son ensemble -- arbitrage des **sources**
(un SP ne livre qu'un sous-ensemble des sources), **ordre de compilation** (piege overWrite,
deux passes) et **verification post-migration** des surcharges -- voir le skill
[`migrating-erp-downgrade`](../../migrating-erp-downgrade/SKILL.md).
