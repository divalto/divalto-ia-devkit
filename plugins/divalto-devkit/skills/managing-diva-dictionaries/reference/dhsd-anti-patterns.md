# Anti-patterns Dictionnaire -- Regles D01-D13

## Contenu

- Regles verifiees par validate_dhsd.py
- Detail des regles
- Validation croisee
- Garde-fous integres dans generate_dhsd_block.py (D12, D13)

---


Source : `docs/ANTI-PATTERNS.md` (section dictionnaire).

---

## Regles verifiees par validate_dhsd.py

| Regle | Severite | Description | Detection |
|-------|----------|-------------|-----------|
| D01 | **error** | Champs qui se chevauchent dans la table | Position suivante != Position courante + Taille courante |
| D02 | **error** | Trous entre les champs (positions decalees) | Position suivante != Position courante + Taille courante |
| D03 | **error** | Champ `U{TABLE}` (reserve distributeur) absent | Recherche du dernier champ dans [CHAMPS] |
| D04 | **error** | Champ utilise dans [CHAMPS] sans declaration [CHAMP] | Cross-reference [CHAMPS] vs [CHAMP] existants |
| D05 | **error** | Encodage du fichier .dhsd modifie (pas ISO-8859-1) | Analyse binaire |
| D06 | **error** | Fins de ligne LF au lieu de CRLF | Analyse binaire |
| D07 | **error** | Section [/CHAMPS] manquante pour fermer la table | Analyse structurelle |
| D08 | **error** | Section [/TABLES] manquante pour fermer la base | Analyse structurelle |
| D09 | **error** | Section [/INDEX] manquante pour fermer un index | Analyse structurelle |
| D10 | **error** | Valeur CE dans CLE de l'index incoherente avec la table | Cross-reference CLE vs CE= |
| D11 | warning | Base nommee sans le prefixe du dictionnaire | Verification prefixe |
| D12 | **error** | `ce_value` invalide avec discriminator `Ce1` (Nature=1 char) | Garde-fou pre-generation |
| D13 | **error** | Lettre cle d'index non alphanumerique 1 char | Garde-fou pre-generation |

---

## Detail des regles

### D01 / D02 -- Positions des champs (ERREUR CRITIQUE)

**Anti-pattern :** Les positions des champs ne sont pas contigues.

**Risque :** Le compilateur signale "il y a un trou devant le champ X" ou les donnees sont corrompues en base.

**Regle :** `Position(N+1) = Position(N) + Taille(Nature(N))`

```ini
# INCORRECT : trou entre Dos et Ref
Nom=Ce1,1,2,N,0,0,N,3      # pos=1, Nature=1 -> suivant=2
Nom=Dos,2,2,N,0,0,N,3       # pos=2, Nature=8 -> suivant=10
Nom=Ref,15,2,N,0,0,N,3      # ERREUR : devrait etre 10, pas 15

# CORRECT
Nom=Ce1,1,2,N,0,0,N,3       # pos=1, Nature=1 -> suivant=2
Nom=Dos,2,2,N,0,0,N,3       # pos=2, Nature=8 -> suivant=10
Nom=Ref,10,2,N,0,0,N,3      # OK : 10 = 2 + 8
```

### D03 -- U-field absent (ERREUR)

**Anti-pattern :** La table n'a pas de champ `U{NomTable}` en derniere position.

**Risque :** Pas de reserve pour les personnalisations distributeur.

**Bonne pratique :** Toujours ajouter `U{NomTable}` comme dernier champ, avec une Nature de reserve suffisante (typiquement 40 a 1500 octets selon la table).

### D04 -- Champ non declare (ERREUR)

**Anti-pattern :** Un champ est reference dans `[CHAMPS]` d'une table sans avoir de `[CHAMP]` correspondant.

**Exception :** `Filler` est un mot-cle special qui ne necessite pas de declaration.

### D05 / D06 -- Encodage et fins de ligne (ERREUR)

**Anti-pattern :** Le fichier .dhsd a ete converti en UTF-8 ou les fins de ligne ont ete changees en LF.

**Bonne pratique :** Toujours utiliser le skill `writing-diva-files` pour ecrire dans un .dhsd.

### D07 / D08 / D09 -- Sections non fermees (ERREUR)

**Anti-pattern :** Oublier les balises fermantes `[/CHAMPS]`, `[/TABLES]`, `[/INDEX]`.

**Risque :** Structure INI malformee, erreur de parsing a la compilation.

### D10 -- Valeur CE incoherente (ERREUR)

**Anti-pattern :** La valeur CE dans la ligne CLE de l'index ne correspond pas a la valeur CE declaree dans la table.

**Exemple :**
```ini
# Dans [TABLE]
CE=Ce1,A

# Dans [INDEX] -> CLE
CLE=GtfBase,A,Ce1,2,A,n,1,n    # OK : ValeurCE=A correspond
CLE=GtfBase,A,Ce1,2,B,n,1,n    # ERREUR : ValeurCE=B != A
```

### D11 -- Prefixe base (WARNING)

**Anti-pattern :** Le nom de la base ne suit pas la convention de prefixe du dictionnaire.

**Convention :**
| Dictionnaire | Prefixe base |
|-------------|-------------|
| gtfdd.dhsd | Gtf |
| ccfdd.dhsd | Ccf |
| rtlfdd.dhsd | Rtl |
| ggfdd.dhsd | Ggf |
| wmsfdd.dhsd | Wms |

---

### D12 -- ce_value Ce1 (ERREUR pre-generation)

**Anti-pattern :** passer `ce_value` multi-caracteres (ex `"200"`) alors que
le discriminator par defaut `Ce1` est `Nature=1` (un seul caractere).

**Symptome compilation :** `La lettre cle doit etre un seul caractere`.

**Regle :** avec `discriminator=Ce1`, `ce_value` doit matcher `^[A-Z0-9]$`.
Pour un discriminator numerique multi-chiffres, utiliser `CeBin` (non
implemente cote generation pour l'instant).

Le garde-fou est dans `generate_dhsd_block.py` (fonction `validate_ce_value`)
et coupe immediatement avec exit 1.

### D13 -- Lettre cle d'index (ERREUR pre-generation)

**Anti-pattern :** un index nomme `Index_Pay` (suffixe multi-char) donnait
une lettre cle `Pay` (ou pire `0` apres derivation buggee) dans `CLE=`,
incompatible avec la Nature du discriminator (1 char).

**Regle :** la lettre cle doit matcher `^[A-Z0-9]$`. La derivation suit :
1. Si `Index_<X>` avec `X` 1 char alphanumerique : reutiliser `X`
2. Sinon, prendre la 1re lettre du suffixe (`Index_Pay` -> `P`)
3. Si conflit avec un autre index : allouer la 1re lettre libre A-Z

Le garde-fou est dans `generate_dhsd_block.py` (fonction
`derive_index_letter`).

---

## Validation croisee

Le script `validate_dhsd.py` effectue des verifications croisees entre les zones :
- [CHAMPS] de [TABLE] vs [CHAMP] existants (D04)
- CLE de [INDEX] vs CE= de [TABLE] (D10)
- [TABLES] de [BASE] vs [TABLE] existantes
- [INDEXL] vs [INDEX] et [BASE] existants
