# Arbitrage d'un RecordSQL en downgrade (migration de Service Pack)

> Lors de la reprise d'un projet **downgrade** au passage d'un Service Pack, decider de
> **conserver, collapser ou supprimer** un RecordSQL overlay (`XXrsYYYu.dhsq`) est piegeux :
> le **texte source ne suffit pas** a trancher (R-025, R-029, R-030). Cette page traite le
> cas specifique des RecordSQL ; pour l'arbitrage des sources en general et l'ordre de build,
> voir le skill `migrating-erp-downgrade`.

## Contenu

- Regle 1 -- le diff texte du `.dhsq` est trompeur (SELECT * couple a la structure dico)
- Regle 2 -- collapse : resolution de la chaine OverWrite
- Regle 3 -- ...mais verifier les consommateurs DANS le perimetre downgrade
- Voir aussi

---

## Regle 1 -- le diff texte est trompeur (R-025)

Comparer le **texte** d'un RecordSQL overlay au standard pour decider de le supprimer est
**FAUX**, pour deux raisons :

1. **`SELECT table.*` est couple a la STRUCTURE du dictionnaire**, pas a son texte. Si le
   dico downgrade porte des champs custom (via overlay `[CHAMPR]/[CHAMPL]`), l'objet compile
   `.dhoq` **differe** -- meme si le `.dhsq` est identique au standard.
2. Un overlay `<DictionarySql OverWrite=... OverWrittenBy=...>` ne contient que le **DELTA**
   (ex. clauses `<Where>` custom nommees). Un `.dhsq` « identique entre SP d'origine et
   downgrade » signifie que **le delta est stable**, PAS qu'il est redondant.

**Methode correcte** : (a) identifier les tables du `SELECT` ; (b) diff la **structure**
(liste des champs) de chaque table entre dico downgrade et dico standard du **nouveau SP** ;
(c) pour les overlays, verifier si le **delta custom** est desormais absorbe par le source
standard du nouveau SP. **Ne supprimer que si structure identique ET delta absorbe.**

> Cas reel : 6 RecordSQL flagges « supprimer » par simple diff texte devaient en realite
> tous etre **conserves**.

---

## Regle 2 -- collapse : resolution de la chaine OverWrite (R-029)

Dans une chaine de surcharge a plusieurs niveaux (standard -> downgrade `u` -> surcharge
`uu` -> ...), un niveau intermediaire (le downgrade) peut etre **entierement redondant** si
**les deux** conditions suivantes sont reunies :

1. un niveau **superieur** (`uu`) **redefinit completement le meme record** par son nom
   (`<RecordSql Name=...>`) -- la redefinition masque celle du niveau inferieur ;
2. le champ custom qui justifiait le downgrade est porte par le **DICTIONNAIRE** (overlay
   `XXddu`), **PAS** par le RecordSQL -- car `SELECT table.*` resout les champs depuis le
   dico du projet ou il compile.

Si les deux sont vraies, le niveau downgrade est **candidat au collapse** (3 niveaux -> 2).
**MAIS** voir la regle 3 avant de conclure.

---

## Regle 3 -- verifier les consommateurs DANS le perimetre downgrade (R-030)

Le collapse de la regle 2 est **FAUX si on oublie que le projet downgrade est une UNITE DE
COMPILATION SEPAREE**. La surcharge `uu` vit dans le **projet principal**, PAS dans le projet
downgrade. Si **un source du projet downgrade consomme** la table physique ou le record
concerne, alors l'overlay downgrade est **OBLIGATOIRE** dans ce perimetre : c'est la seule
surcharge disponible, compilee contre le dico downgrade (avec le champ custom). Le retirer
ferait resoudre le record contre le standard (sans le custom) -> **incoherence de layout**.

**Regle de collapse complete -- les 3 conditions sont NECESSAIRES :**

1. une surcharge superieure redefinit le record ;
2. le custom est porte par le dico present dans le projet cible ;
3. **AUCUN** source du projet downgrade ne consomme la table/record (grep des consommateurs
   -- table physique **et** nom de record -- dans tout le projet downgrade, hors `base_sp*`).

Toujours raisonner **par perimetre de compilation** : un projet downgrade ne voit pas les
surcharges du projet principal.

---

## Voir aussi

- Arbitrage des **sources** (un SP ne livre qu'un sous-ensemble) et **ordre de build** :
  [migrating-erp-downgrade](../../migrating-erp-downgrade/SKILL.md).
- Arbitrage au niveau **dictionnaire** (3 couches `[CHAMP]/[CHAMPS]/[CHAMPL]`, classification
  3-voies) :
  [managing-diva-dictionaries/reference/dhsd-diff-downgrade.md](../../managing-diva-dictionaries/reference/dhsd-diff-downgrade.md).
- Pattern d'ecriture d'une surcharge RecordSQL : [dhsq-overwrite-pattern.md](dhsq-overwrite-pattern.md).
