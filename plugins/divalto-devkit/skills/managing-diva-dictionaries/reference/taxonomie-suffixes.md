# Taxonomie de suffixes typés sur les noms de champ DIVA

## Contenu

- Principe
- Matrice canonique
- Prefixes particuliers
- Noms canoniques (override direct)
- Integration avec les skills
- Sources

---


> Reference pour le script `scripts/suggest_nature.py` et pour l'orchestrateur
> `creating-diva-entity`. Sources : corpus X.13 (24 196 champs, 21 dicos), mesure
> 2026-04-17 (batch 16).

---

## Principe

**Le suffixe PascalCase du nom de champ annonce la Nature DIVA.** Un champ
`CdeDt` est presume etre une date D8 avec confiance 93 %. Un `AnnulFl` est un
flag booleen `1,0` a 95 %.

Cette regle est **empirique** (mesuree) et non absolue (pas 100 %). L'orchestrateur
doit donc :
1. **Proposer** la Nature deduite avec son taux de confiance.
2. **Demander confirmation** au collaborateur quand la confiance < 85 % ou
   quand le suffixe n'est pas discriminant (`Cod`, `No`, `Lib`, `Ref`, `Msk`).
3. **Toujours accepter** une Nature libre si le collaborateur la fournit.

## Matrice canonique

### Correlation forte (>= 85 %) -- proposer sans demander

| Suffixe | Nature | Taux | Exemple | Type |
|---|---|---:|---|---|
| `Dh` | `DH` | 98 % | `UserCrDh`, `CdeDh` | Timestamp 14 oct |
| `Flg` | `1,0` | 99 % | `ChangeTrackingFlg` | Flag booleen |
| `Fl` | `1,0` | 95 % | `AnnulFl`, `ActFl` | Flag booleen |
| `Dt` | `D8` | 93 % | `CdeDt`, `FinDt` | Date AAAAMMJJ |
| `He` | `H6` | 97 % | `CdeHe`, `LivHe` | Heure HHMMSS |
| `Typ` | `1,0` ou `2,0` | 85 % | `PieceTyp` | Type court |

### Correlation moderee (50-85 %) -- proposer + demander confirmation

| Suffixe | Nature | Taux | Exemple |
|---|---|---:|---|
| `Qte` | `12,D2` | 72 % | `QteCde`, `LotQte` |
| `Mt` | `16,D0` (signe) | 65 % | `MtHT`, `AmoMt` |
| `Nb` | `NUM_INT(2-8)` | 50 % | `NbLig`, `NbArt` |

### Correlation faible (< 50 %) -- DEMANDER la taille

| Suffixe | Natures courantes | Exemple |
|---|---|---|
| `Cod` | BYTES(1 / 4 / 5 / 8 / 20) | `TiCod`, `DepoCod` |
| `No` | NUM_INT(2-14) ou BYTES(10-20) | `PiNo`, `EnrNo` |
| `Ref` | BYTES(25 / 33 / 49) | `ArtRef`, `FullRef` |
| `Lib` | BYTES(20 / 40 / 80 / 155) | `Lib`, `Lib80` |
| `Msk` | BYTES(8 / 20 / 25) | `TiersMsk` |
| `Cpt` | BYTES(20) | `CptFou` |
| `Dev` | BYTES(4) ou NUM_INT(16) | `ColDev`, `MtDev` |

### Tableau repete (piege)

| Suffixe | Nature | Explication |
|---|---|---|
| `Tb` | `X*N` ou `X,Y*N` | **PAS** cle vers table externe. Tableau repete : `AdresseTb=16*10` = 10 adresses de 16 car. Pour referencer une table, utiliser `Cod`. |

## Prefixes particuliers

| Prefixe | Nature | Exemple | Regle |
|---|---|---|---|
| `U<Table>` (seul) | BYTES(100-500) | `UGtfArt` | Reserve distributeur. Un seul par table metier. |
| `User` | BYTES(20) ou DH ou D8 | `UserCr`, `UserCrDh`, `UserCrDt` | Audit 4 formes : `UserCr`/`UserMo` = BYTES(20), `*Dh` = DH, `*Dt` = D8, `*Ori` = NUM_INT(2). |
| `Ce` | BYTES(1) | `Ce1`..`CeA` | Composante code enregistrement. |
| `Full` | BYTES(20 ou 33) | `FullRef`, `FullPino` | Version complete d'un code court. |
| `Pref` | BYTES(10) | `PrefPiNo` | Prefixe metier 10 octets. |
| `Sref` | BYTES(8 ou 16) | `Sref1`, `Sref2` | Sous-reference. |

## Noms canoniques (override direct)

Ces noms ont une Nature deterministe et ne doivent JAMAIS etre redeclares
(ils existent deja comme [CHAMP] global dans les dictionnaires standard) :

| Nom | Nature | Role |
|---|---|---|
| `Dos` | BYTES(8) | Dossier multi-tenant |
| `Ce1`..`Ce9`, `CeA`, `Ce` | BYTES(1) / BYTES(10) | Code enregistrement |
| `UserCr`, `UserMo` | BYTES(20) | Audit utilisateur |
| `UserCrDh`, `UserMoDh` | DH | Timestamps audit |
| `Filler` | (special) | Mot-cle special, pas de declaration |

## Integration avec les skills

- **`managing-diva-dictionaries`** -> `scripts/suggest_nature.py` consomme
  cette table.
- **`creating-diva-entity`** -> etape "definition des champs metier" demande
  a l'orchestrateur LLM d'utiliser `suggest_nature.py` pour chaque champ
  propose par le collaborateur, avec ce workflow :
  1. Collaborateur fournit un nom + une description semantique ("date de
     livraison prevue").
  2. LLM propose un nom PascalCase respectant la taxonomie
     (`PrevLivDt`).
  3. LLM appelle `suggest_nature.py --name PrevLivDt` -> `D8` avec confiance 93 %.
  4. Si confiance >= 85 % -> propose directement la Nature.
  5. Si confiance < 85 % OU suffixe non reconnu -> demande confirmation
     avec les Natures alternatives.

## Taxonomie FK (complement 2026-04-20, batch 18 bis)

Au-dela de la Nature, le suffixe peut aussi annoncer la **cible de foreign key**
(le champ est une cle etrangere vers une entite cible via un zoom standard).
Cette couche est complementaire a la Nature : un champ `RacPays` a une Nature
(heritage de la table T013 Pays, typiquement BYTES(3)) ET une cible FK (T013).

Exemples de suffixes FK fiables (fiabilite >= 90 % sur 2408 Check_*_Field_*) :

| Suffixe | Cible FK | Zoom | Module | Fiabilite |
|---------|----------|-----:|--------|----------:|
| `Pay`/`Pays` | T013 | 9053 | `Gttmchkt013.dhop` | 100 % |
| `Dev`/`Devise` | T007 | 9047 | `Gttmchkt007.dhop` | 93 % |
| `Depo` | T017 | 9057 | `Gttmchkt017.dhop` | 97 % |
| `Cpt` | C3 | 9055 | framework CC | 97 % |
| `Axe` | C5 | 9056 | framework CC | 100 % |

Table complete : catalogue des zooms standards (source : `a5tczoom.dhsp` constantes + empirique sur le standard ERP). Consulter le skill [`allocating-zoom-numbers`](../../allocating-zoom-numbers/SKILL.md) pour la correspondance suffixe -> zoom standard.

Le script `suggest_nature.py` retourne **les deux** couches simultanement :
champs `nature` + `confidence` + `rule` (Nature) et `fk_target` + `fk_note` (FK).

## Sources

- Conventions DIVA locales (sections "Suffixes typés sur les noms de champ" et "Suffixes foreign key")
- Pattern FK complet : reference/fk-pattern.md (si disponible)
- Tables A/B/C des zooms standards : reference/zooms-standards.md (si disponible)
- Dataset empirique dhsd_suffix_nature (mesure d'occurrence par nature suffixe) maintenu hors skill
- Script : `scripts/suggest_nature.py`
