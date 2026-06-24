# Arbitrage des sources d'un downgrade (passage de Service Pack)

> Quand on reprend un projet **downgrade** (couche de surcharge d'un distributeur /
> integrateur) au passage d'un Service Pack, il faut decider, source par source, quoi
> **conserver + rebaser**, quoi **abandonner**. Le piege : croire qu'un simple diff
> textuel contre le standard suffit (R-028).

## Contenu

- Le piege : un SP ne livre qu'un sous-ensemble des sources
- Les 3 signaux a croiser
- Classification de repli (quand la source standard manque)
- Lien dictionnaire (RecordSQL / `[CHAMPL]`)

---

## Le piege : un SP ne livre qu'un SOUS-ENSEMBLE des sources

Un Service Pack ne livre qu'une **partie** des sources standard (`.dhsp` / `.dhsf`).
Le reste n'est fourni qu'en **objet compile** (`.dhop` / `.dhof` / `.dhoq`). Sur un
downgrade reel, une **forte proportion** des sources non-RecordSQL n'avait **aucune
source standard** disponible dans le SP cible.

> **Regle imperative** : ne **jamais** conclure « source supprimable / custom » sur la
> **seule absence de source standard**. L'absence de source ne prouve rien -- le module
> standard existe peut-etre, livre uniquement en objet.

---

## Les 3 signaux a croiser

| Signal | Comment | Ce qu'il tranche |
|--------|---------|------------------|
| **1. Diff textuel** | comparer le fichier downgrade au source standard **si disponible** | identifie un vrai ecart de contenu |
| **2. Existence de l'objet standard** | indexer **aussi** l'arbre `objets/` du pack | objet standard present + source absente = **standard recompile** en contexte downgrade (pas un custom) |
| **3. Couplage** | un fichier est dans le downgrade parce qu'il **depend** d'un dico / RecordSQL downgrade | tranche quand le diff textuel est impossible (raisonner par dependance, pas par texte) |

---

## Classification de repli (quand la source standard manque)

- **objet standard present, source absente** -> module **standard recompile** dans le
  contexte downgrade (couple au dictionnaire downgrade). A conserver/rebaser, ce n'est
  pas un custom.
- **ni source ni objet** -> soit un **include** (`pc` / `tc`, compile dans l'hote), soit
  un **vrai custom**. Reconnaitre un **include** a son **contenu** : en-tete
  `;>include xdiva`, « Declarations communes », `Public Record` **sans corps de
  programme** (pas de procedures).

---

## Lien dictionnaire (RecordSQL / `[CHAMPL]`)

L'arbitrage des **RecordSQL** ne se joue pas sur le `.dhsq` seul : un RecordSQL se
compile contre un **record relationnel `[CHAMPL]`** du dictionnaire. La couche
`[CHAMPL]` est l'angle mort classique (un champ custom y vit sans apparaitre dans
`[CHAMPS]`). Voir
[managing-diva-dictionaries/reference/dhsd-diff-downgrade.md](../../managing-diva-dictionaries/reference/dhsd-diff-downgrade.md)
-- diff **3 couches** (CHAMP / CHAMPS / CHAMPL) + classification **3-voies**
(CUSTOM / ROLLBACK / GEL) : meme principe « ne pas conclure sur un seul signal ».

Et pour l'arbitrage specifique d'un **RecordSQL downgrade** (diff texte trompeur car
`SELECT *` couple a la structure dico, collapse de chaine OverWrite, regle des 3 conditions
avant suppression) :
[generating-recordsql/reference/recordsql-downgrade-arbitration.md](../../generating-recordsql/reference/recordsql-downgrade-arbitration.md).
