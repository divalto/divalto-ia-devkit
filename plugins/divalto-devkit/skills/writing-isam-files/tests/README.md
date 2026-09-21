# Tests du skill writing-isam-files

Suites executables, **sans DLL et sans fichier ISAM reel**. Les defauts corriges vivent
dans des fonctions pures (`encoder_champ`, `build_tdf_key`, `record_matches_key_fields`)
ou dans une copie de fichier -- tous testables sans `DhxIsam64.dll` et **sans jamais
toucher a un `.dhfi` de production**.

```
py .claude/skills/writing-isam-files/tests/run_all.py
```

A lancer apres **toute** modification de `scripts/write_isam.py`.

---

## test_cadrage_binaire_backup.py

Couvre les trois correctifs de : cadrage de la cle (#334), champs binaires et
sauvegarde (#290).

### Pourquoi ces tests

Les trois defauts ont le meme profil : **ils ne font pas de bruit**. Un enregistrement
ecrit au mauvais endroit, un champ binaire rempli d'espaces ou un fichier modifie sans
copie de secours ne produisent aucune erreur -- on s'en apercoit plus tard, ou jamais.

| Defaut | Ce que faisait le code |
|--------|------------------------|
| **#334** | `build_record` lisait `Justify`, `build_tdf_key` faisait un `ljust` inconditionnel. Un champ numerique cadre a DROITE partait dans la cle cadre a GAUCHE : une cle totalement differente en tri octet par octet |
| **le jumeau** | `record_matches_key_fields` comparait avec un simple `rstrip` : les espaces de **tete** d'un champ cadre a droite subsistaient, la verification echouait meme apres un positionnement correct |
| **#290** binaire | La lecture rend un champ `Type: "B"` en hexadecimal ; l'ecriture n'avait aucun equivalent (`str().encode(cp1252)` ne permet pas d'exprimer un octet arbitraire) |
| **#290** sauvegarde | **Aucune** copie de securite, alors que le voisin d'ecriture texte en fait une par defaut |

### Le defaut jumeau, que l'issue ne nommait pas

L'issue #334 designe `build_tdf_key`. Mais le message d'erreur qu'elle cite --
`Enreg cible introuvable (match approximatif refuse)` -- est emis par **une autre
fonction**, `record_matches_key_fields`, qui portait la meme classe de defaut sous une
autre forme. **Corriger seulement la fonction nommee aurait laisse `update`/`delete`
casses** : la cle aurait bien positionne, et la verification aurait refuse.

Les cas 5 et 6 verrouillent ce second site ; le cas 3 verrouille l'invariant qui manquait
-- la cle et l'enregistrement doivent porter **les memes octets** pour un meme champ.

### Deux temoins

- **cas 2** re-implemente le `ljust` inconditionnel et exige que la cle produite soit
  **differente**, et se trie ailleurs. Sans lui, le cas 1 n'affirmerait rien.
- **cas 6** re-implemente la comparaison par `rstrip` et exige qu'elle **echoue** la ou la
  nouvelle reussit.

Le cas 7 est leur contrepoids : un enregistrement **voisin** doit rester **refuse**.
L'assouplissement porte sur le cadrage, jamais sur l'identite de la cle -- sans quoi on
ouvrirait la porte a l'ecrasement d'un enregistrement tiers.

### Ce que le lot a corrige au-dela de l'issue

Le RETEX #290 demande une copie `.bak` du **`.dhfi`**. Un ISAM Divalto est une **paire** :
`.dhfi` (donnees) + `.dhfd` (index), et un `.dhfi` sans son `.dhfd` ne s'ouvre meme pas.
Une sauvegarde du seul `.dhfi` **ne permet pas de restaurer** -- le skill de lecture le
documentait deja, celui d'ecriture l'ignorait. Le cas 13 verrouille les deux fichiers.

### Table des cas

| # | Ce qui est verifie |
|---|--------------------|
| 1 | un champ `Justify: right` est cadre a droite **dans la cle** |
| 2 | **temoin** : le cadrage fautif produit une cle differente, qui se trie ailleurs |
| 3 | la cle et l'enregistrement portent les **memes octets** pour chaque champ de cle |
| 4 | idempotence : `"131"` et `"     131"` donnent le meme resultat |
| 5 | la verification post-lecture accepte un enreg dont la cle est cadree a droite |
| 6 | **temoin** : l'ancienne comparaison par `rstrip` aurait refuse |
| 7 | **non-regression** : un enreg voisin reste refuse (garde anti-corruption) |
| 8 | un champ `Type: "B"` accepte l'hexadecimal et ecrit les octets exacts |
| 9 | hexadecimal invalide -> refus |
| 10 | mauvaise longueur -> refus, **jamais** de troncature |
| 11 | champ binaire non fourni -> reste a `0x20` mais est **signale** |
| 12 | aller-retour lecture -> ecriture sans perte |
| 13 | la sauvegarde couvre **`.dhfi` ET `.dhfd`** |
| 14 | le `.bak` est fidele a l'original (empreinte) |
| 15 | **un seul** `.bak` par fichier et par execution, meme sur un lot |
| 16 | `.dhfd` absent -> pas de plantage |

### Verification de discrimination

Jouee contre la version anterieure de `write_isam.py` (`git show HEAD:...`, mise en place,
restauration **prouvee par empreinte**), la suite tombe sur **14 cas sur 16**. Les deux qui
passent sont le **temoin** du cas 6 -- qui rejoue l'ancien comportement, donc passe par
construction -- et la garde de non-regression du cas 7, dont c'est precisement le role.

---

## Convention

- Aucun chemin absolu, aucun fichier de production : tout se passe dans un
  `tempfile.mkdtemp()` nettoye en `finally`.
- Les cas de sauvegarde reinitialisent `_DEJA_SAUVEGARDES` pour rester independants les
  uns des autres.
- Les champs de test sont calques sur la structure que le skill livre reellement
  (`structure_xmenuf_m2.json`), pas sur un cas fabrique : c'est elle qui declenche #334.
