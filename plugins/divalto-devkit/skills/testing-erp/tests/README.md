# Tests de `testing-erp`

```
py plugin/skills/testing-erp/tests/test_connexion_verifiee.py
```

## `test_connexion_verifiee.py` -- le flux de connexion (#222, 8 cas)

Le retour terrain a l'origine de ces cas est un **feuilleton de debogage en cinq episodes**,
et **les trois du milieu sont une fausse piste** : le remede a ete cherche du cote de
`utilisateurHtml5.txt` pendant trois sessions, jusqu'a ce que le dernier episode etablisse
que **c'est la page de login qui alimente le lancement du moteur**.

Quatre des cinq issues sont **hors perimetre** (deploiement serveur : application IIS, pool,
compte de service -- gestes a elevation). Seul le dernier episode a produit du livrable.

### Ce que ces cas gardent

| Cas | Ce qu'il empeche |
|---|---|
| 1 | que l'URL de repli quitte le **mode operatoire** pour ne survivre que dans le texte |
| 2 | que la **fausse piste redevienne une prescription** |
| 3 | que l'**incertitude** sur la redirection soit effacee, **ou** que l'URL de depart change alors qu'elle n'est pas levee |
| 4 | qu'une insertion casse la **numerotation** du workflow |
| 5 | que la **frontiere avec le deploiement** disparaisse, et invite a repartir dans un terrier ou Claude ne peut rien |
| 6 | que « utilisateur inconnu » soit relu comme un probleme de deploiement |
| 8 | qu'un mot de passe en clair soit **suggere**, ou qu'un chemin de poste entre dans une page distribuee |

### Validation : 9 mutations, 9 discriminantes -- apres deux corrections de mes propres cas

Le harnais a trouve **deux faiblesses de la livraison**, toutes deux de la meme famille --
**une assertion satisfaite ailleurs que la ou elle croyait regarder** :

1. Le cas 1 cherchait l'URL **dans la page entiere**. La supprimer du mode operatoire ne le
   faisait pas tomber : elle subsistait dans le texte explicatif. Il s'ancre desormais sur
   **l'etape numerotee**.
2. Le cas 2 ne tombait pas quand la mise en garde devenait une prescription, et la cause est
   plus profonde : **le decoupeur de phrases etait mis en defaut par le gras markdown**.
   `...txt`.** Ce fichier` ne coupe pas -- le caractere avant l'espace est `*`, pas `.` --
   donc toute la mise en garde formait **une seule phrase**, et son marqueur de refutation
   couvrait la prescription voisine.

> **Le meme decoupeur naif vit dans 5 suites soeurs** (`coding-diva-advanced` x2,
> `manipulating-dhsf-screens` x3), et le motif qui le met en defaut apparait **133 fois**
> dans les pages qu'elles controlent. **Signale, non corrige ici** : hors du perimetre de ce
> lot, ecrit sous.
