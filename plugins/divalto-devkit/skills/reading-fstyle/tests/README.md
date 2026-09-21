# Tests de `reading-fstyle`

```
py plugin/skills/reading-fstyle/tests/test_decodage_verifie.py
```

## `test_decodage_verifie.py` -- le decodage dit-il ce qu'il sait ? (#326, 10 cas)

Le retour terrain tenait en une phrase : **« decodage incomplet, mais presente comme
complet »**. Les 18 styles de la famille `DATA` sortaient tous en
`{taille: 8, poids: 400000, famille: Tahoma}` alors que leurs enregistrements sont **tous
differents**.

**Les cas ne touchent ni le fichier reel ni la DLL** : ils fabriquent des enregistrements
en memoire. Une suite qui ne tourne que sur un poste equipe de Divalto ne tourne nulle part
ailleurs -- et ce skill est distribue.

### Ce que ces cas gardent

| Cas | Ce qu'il empeche |
|---|---|
| 1-2 | que la couleur cesse d'etre lue **a son offset fixe** -- deux polices identiques sur taille/poids/famille redeviendraient indistinguables |
| 3 | qu'une zone illisible produise **une fausse couleur** au lieu d'un refus declare |
| 4 | que la 4e composante soit nommee **« alpha »** : elle vaut `0` sur les 142 mesures, sa semantique n'est pas etablie |
| 5 | que la sortie **cesse de dire ce qu'elle ignore** -- le defaut d'origine |
| 6-7 | que le **type reel** des references de Type 7 disparaisse, ou qu'un slot hors type attendu passe en silence |
| 8 | que la page perde l'**etat AVANT** du tableau de collisions : sans lui, le gain n'est plus verifiable et l'incompletude restante sort du discours |
| 10 | qu'une trace du poste de l'editeur entre dans un fichier distribue |

### Validation : 10 mutations, 10 discriminantes -- apres trois corrections de mes cas

Le harnais et le premier lancement ont trouve **trois faiblesses de la livraison**, toutes de
la meme famille -- **une regle qui mesure la forme au lieu de la chose** :

1. Le cas 8 s'ancrait sur « une ligne contenant `fstylewpf` et `142` » ; la **phrase de
   mesure** en contient autant que la ligne du tableau. Ancre desormais sur le **debut de
   ligne** du tableau.
2. Le cas 10 interdisait **tout chemin absolu**. Il tombait sur `K:\` cite en exemple dans un
   commentaire -- qui explique justement pourquoi un chemin en dur avait ete retire -- puis
   sur le placeholder `C:\autre\chemin\` d'une ligne d'usage. **Deux mentions, dont une qui
   documente un correctif.**
3. Reecrit pour detecter **la chose** : les marqueurs reels d'un poste. Et la premiere version
   de ce nouveau critere tombait encore -- sur `\\divalto\\`, qui est l'**echappement Python**
   d'un chemin dans une chaine d'aide. *Une regle qui tombe sur l'echappement d'un langage ne
   mesure pas ce qu'elle croit.*

> Deux mutations font tomber **plusieurs cas a la fois** (`1` avec `2`, et `2` avec six
> autres) : c'est attendu, elles retirent la fondation sur laquelle les autres s'appuient.
