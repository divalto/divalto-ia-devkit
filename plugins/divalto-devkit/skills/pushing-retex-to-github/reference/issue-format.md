# Format des issues GitHub generees

## Titre

```
[R-NNN] <titre court de l'entree RETEX>
```

Exemples :
- `[R-001] Naming RaceChien OK + parametre --nomrecordsql`
- `[R-019] Pattern FK callback dhsf_add_fk.py corrige (R-005 + R-011)`

## Labels

Trois sources de labels :

1. **labels_default** : toujours appliques (defaut `["retex"]`)
2. **labels_categorie** : derive de la valeur du champ `Categorie` de l'entree
3. **labels_severite** : derive de la valeur du champ `Severite`

Si plusieurs valeurs de categorie sont mentionnees (`SUGGESTION + BUG-SKILL`), tous les
labels correspondants sont ajoutes.

Les labels doivent **preexister** dans le repo cible. Sinon `gh issue create` echoue
silencieusement sur le label inconnu et l'issue est creee sans ce label.

A creer une fois pour toutes dans le repo cible :

```bash
gh label create retex --color "0075ca" --description "Retour d'experience partenaire"
gh label create bug-skill --color "d73a4a" --description "Bug dans un skill"
gh label create bug-doc --color "e99695" --description "Bug dans la documentation d'un skill"
gh label create suggestion --color "a2eeef" --description "Suggestion d'amelioration"
gh label create env --color "fef2c0" --description "Probleme d'environnement"
gh label create claude-tool --color "c5def5" --description "Outil Claude Code lui-meme"
gh label create severite:critique --color "b60205"
gh label create severite:haute --color "d93f0b"
gh label create severite:moyenne --color "fbca04"
gh label create severite:basse --color "0e8a16"
gh label create severite:info --color "c5def5"
```

## Body

Template (markdown) :

```markdown
> RETEX pousse automatiquement depuis le poste de <email> via le skill
> `pushing-retex-to-github`. Source : `<chemin du RETEX-skills.md>`.

## Resultat

<contenu du champ Resultat>

## Skill(s) concerne(s)

<contenu du champ Skill(s)>

## Description

<contenu du champ Description>

## Reproduction

<contenu du champ Reproduction>

## Contournement

<contenu du champ Contournement>

## Suggestion

<contenu du champ Suggestion>

---

_Date d'origine : YYYY-MM-DD_
_ID local : R-NNN_
_Hash : <8 premiers chars du sha1>_
```

## Mise a jour d'une entree existante

Quand le contenu d'une entree change (hash different), au lieu de creer une nouvelle
issue, le skill **commente** l'issue existante avec :

```markdown
**Mise a jour de l'entree RETEX**

Le contenu de R-NNN a ete modifie cote partenaire le YYYY-MM-DD HH:MM. Nouveau contenu :

---

<corps complet de l'entree mise a jour, meme template que ci-dessus>

---

_Nouveau hash : <8 chars>_
```

## Cas limites

| Cas | Comportement |
|-----|--------------|
| Champ `Categorie` absent | Aucun label categorie ajoute |
| Champ `Severite` absent | Aucun label severite ajoute |
| Categorie inconnue (ex `META`) | Label brut `categorie:meta` ajoute |
| Severite inconnue | Label brut `severite:<valeur>` ajoute |
| Caracteres speciaux dans titre | Echappes pour `gh issue create --title` |
| Body > 65k chars (limite GitHub) | Tronque + lien vers RETEX-skills.md commit hash si dispo |
