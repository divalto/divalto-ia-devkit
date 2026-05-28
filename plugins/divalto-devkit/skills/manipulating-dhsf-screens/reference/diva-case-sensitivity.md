# DIVA -- regle de sensibilite a la casse

## TL;DR

| Couche | Sensibilite | Implication |
|--------|-------------|-------------|
| **DIVA langage** (sections `[diva]` / `[diva_base]` d'un `.dhsf`, et `.dhsp` autonomes) | **INSENSIBLE** | `Public/public/PUBLIC` interchangeables, `MyVar/myvar/MYVAR` aussi |
| **SQL Divalto** (BDD, identifiants tables/colonnes) | **SENSIBLE** | Identifiants en MAJUSCULES obligatoires (`ART` != `Art`) |
| Noms de fichiers (`"foo.dhoq"`) | INSENSIBLE | NTFS case-insensitive sous Windows |

**Regle d'or** : ne JAMAIS supposer la sensibilite a la casse en lisant du DIVA. Un standard peut utiliser `Competence.STAT(1)` ici et `competence.stat(1)` la -- les deux marchent.

---

## Pourquoi cette page

Quand on edite la section `[diva]` d'un masque (cf. [dhsf-structure.md](dhsf-structure.md)), on rencontre des mots-cles et identifiants dans des casses variees. Confondre la regle DIVA (insensible) avec celle de SQL Divalto (sensible) est une source de confusion frequente -- d'autant que les deux univers coexistent dans une chaine de surcharge (`.dhsd` -> SQL -> `.dhsq` -> `.dhsf`).

---

## Datapoints empiriques

### Mots-cles equivalents

Sur `gtez060_sqlu.dhsf` (session 2026-05-06), le compilateur DIVA a declenche la **meme erreur 210** sur les 4 ecritures :

- `Public Procedure ZoomDuplication`
- `public Procedure ZoomDuplication`
- `Public procedure ZoomDuplication`
- `public procedure ZoomDuplication`

L'erreur 210 ("La fonction/procedure ... est une surcharge. Elle ne peut etre PUBLIC") est levee dans les 4 cas -- le compilateur ne distingue pas la casse. Voir aussi [overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md) section "Declaration des procedures surchargees".

### Identifiants cross-section

Sur `gtez096_sql.dhsf` (zoom DAS), la section `[diva_base]` du standard reference `DAS.STATD` (majuscule) tandis que la section `[diva]` user declare le record en `das` (minuscule). Le code compile et fonctionne au runtime -- DIVA matche les identifiants peu importe la casse.

### Convention AGL

L'editeur de masque graphique (xwin7 GUI) normalise systematiquement en lowercase ce qu'il ecrit dans `[diva]` user. C'est une **convention stylistique**, pas une exigence du compilateur. Un generateur peut ecrire :

```diva
Public Record "DDSYS.dhsd" ROWINFO zoomselection
```

OU :

```diva
Public Record "ddsys.dhsd" rowinfo zoomselection
```

-- les deux compilent. La convention lowercase est preservee dans nos generateurs uniquement pour interoperabilite byte-for-byte avec xwin7 GUI (les diffs `_base.dhsf` vs surcharge utilisateur restent lisibles).

---

## Pieges a eviter

1. **Supposer la sensibilite a la casse en lisant du DIVA** -- ne pas considerer une difference de casse comme un bug a corriger.
2. **Confondre avec SQL Divalto** -- si on genere du SQL ou des identifiants destines a la BDD, MAJUSCULES OBLIGATOIRES. Voir aussi la note dans [generating-recordsql](../../generating-recordsql/SKILL.md) sur les identifiants SQL Server case-sensitive.
3. **Prendre les divergences de casse pour des bugs** -- en DIVA, ce n'est pas un bug, c'est de l'equivalence.
4. **Melange de casse pour un meme identifiant dans un fichier** -- toleree par le compilateur mais peut nuire a la lisibilite. Convention recommandee : casse coherente par identifiant au sein d'un fichier.

---

## Convention recommandee pour la generation de surcharge

Quand on genere une surcharge `.dhsf` (cf. [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md)) :

- **Section `[diva]` et `[diva_base]`** : preserver la casse du standard quand on recopie depuis `_base.dhsf`. Pour le code nouveau, suivre la convention lowercase (alignement AGL).
- **Identifiants SQL dans `donnee=`** : suivre la casse du dictionnaire (la propriete `donnee=record,champ,instance` est case-insensitive cote masque mais le `NomOdbc` du dictionnaire est traduit en SQL).
