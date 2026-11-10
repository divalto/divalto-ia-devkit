---
name: divalto-fontawesome-icons
description: "Écrit une icône Font Awesome 7 sur un contrôle mobile (Button, PictureBox, BarcodeScanner, onglet de Calendar, item de navigation, UniSearch) : forme du code `fa-…`, champs sœurs `faIconCode` / `faIconColor`, champs qui refusent une icône. Utiliser pour : mettre une icône sur un bouton, remplacer une image par un pictogramme, colorer une icône."
argument-hint: "Décrivez le contrôle et l'icône voulue (ex : une icône utilisateur bleue sur le bouton Profil)."
capabilities: [mobile, mobile-v7]
---

# Icônes Font Awesome

La règle de nommage des `codePicture` de thème (jamais de préfixe `fa-`) est dans
[divalto-mobile-screen-creation](../divalto-mobile-screen-creation/references/procedure.md).

Un champ de code image accepte, en plus d'un `codePicture` de `sw_data_confthemepicture`,
un code Font Awesome 7. Écrire **la forme lisible** : `fa-` + famille optionnelle + nom
d'icône.

- Familles : absente ⇒ Classic, `duotone-`, `brands-`.
- Exemples : `fa-user`, `fa-duotone-user`, `fa-brands-facebook`.

**MUST NOT : ne jamais écrire de graisse.** Le Player la choisit selon la taille affichée
(Regular jusqu'à 16 px, Light au-delà). Une graisse présente dans un code existant
(`fal-user`, `fa-light-user`) est ignorée : ne pas la signaler, ne pas réécrire le code
pour l'enlever.

- ✅ `fa-user`, `fa-duotone-user`
- ❌ `fa-light-user`, `fa-duotone-regular-user`, `fas-user`

**MUST NOT : Sharp, Sharp Duotone et Thin ne sont pas livrés.** Un code qui les nomme
n'est pas reconnu comme Font Awesome et n'affiche pas d'icône.

- ✅ `fa-user`, `fa-duotone-user`
- ❌ `fa-sharp-user`, `fa-sharp-duotone-user`, `fa-thin-user`, `fass-user`, `fat-user`

**Les noms sont ceux de Font Awesome 7, pas de FA5.** Le passage à FA7 a fait disparaître
**701 noms FA5** — `home` est devenu `house`, `cog` est devenu `gear` — et **24** autres ont
gardé leur nom en changeant de codepoint (mesuré en comparant la table FA5 de l'historique
du Player à la table FA7 embarquée aujourd'hui ; ne pas propager d'autres chiffres sans les
avoir recalculés sur ces deux tables).

**Un nom inconnu échoue en silence** : aucune erreur, aucun avertissement, le code retombe
sur la recherche en base et n'affiche simplement rien. Il n'y a donc aucun moyen de
détecter un nom inventé en relisant la configuration ou en la testant — le seul symptôme
est une image absente sur l'appareil.

En conséquence, quand le nom exact n'est pas certain : **demander à l'utilisateur de le
choisir dans l'onglet « Icônes » du sélecteur d'images et de le communiquer**, plutôt que
d'en écrire un au jugé. Le sélecteur ne liste que des noms qui existent réellement dans les
polices embarquées ; il n'est pas atteignable depuis un agent, mais l'utilisateur l'a sous
la main. Un nom deviné qui se révèle faux coûte une image manquante que personne ne
rattachera à sa cause des semaines plus tard. Cet onglet n'apparaît que si les polices Font
Awesome sont installées dans Studio — un code `fa-` écrit à la main rend malgré tout sur
l'appareil, indépendamment de cette limite d'affichage.

**Champs sœurs Font Awesome (designer et UniSearch).** Les champs images du designer et de
l'UniSearch qui ont un sélecteur d'images ont chacun deux propriétés sœurs :
`<slot>FaIconCode` et `<slot>FaIconColor`.

- Une icône Font Awesome se met dans la propriété sœur `<slot>FaIconCode`, jamais dans
  `<slot>ImageCode`. Si les deux sont renseignées, l'icône gagne et l'image est ignorée.
- `<slot>FaIconColor` prend une famille sémantique parmi les neuf : `default`, `base`,
  `primary`, `secondary`, `tertiary`, `error`, `warning`, `success`, `info`. Jamais un hex.
- ✅ `imageCode: "WEAVY19--Pin"` + `faIconCode: "fa-user"` + `faIconColor: "primary"`
- ❌ `imageCode: "fa-user"` (toujours lu par le Player, mais ne peut porter aucune couleur)

Un code `fa-…` écrit dans l'ancien champ image continue de fonctionner (projets de
développement existants), mais ne peut porter aucune couleur : seule la sœur `FaIconColor`
le peut.

**Champs sans sœur.** Le Player consomme ces champs en octets, et un glyphe n'en a pas. Le
code MUST NOT y être un code Font Awesome — rester un `codePicture` de thème :

- Maps `userLocationImageCode`, `routeOriginImageCode`, `routeDestinationImageCode` et
  l'icône de série ;
- l'arbre de navigation `themePicture`, qui est une clé étrangère et non un code.

- ✅ `userLocationImageCode: "WEAVY19--Pin"` (`codePicture` de thème)
- ❌ `userLocationImageCode: "fa-user"` (rend du vide, sans erreur)

**Coloration (champ sans sœur).** Sur un champ qui n'a pas de sœur `FaIconColor` — ou quand
l'icône reste écrite dans l'ancien champ image — la couleur vient du thème
(`color.on-app-surface`) et suit le mode sombre : il n'y a pas de syntaxe pour la fixer.
