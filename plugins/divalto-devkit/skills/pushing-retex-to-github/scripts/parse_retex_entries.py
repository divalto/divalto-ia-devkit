"""
Parse un fichier RETEX-skills.md et extrait la liste des entrees R-NNN.

Format d'entree attendu (markdown) :

    ### R-NNN -- YYYY-MM-DD -- Titre court

    - **Skill(s)** : ...
    - **Categorie** : ...
    - **Severite** : ...
    - **Resultat** : ...
    - **Description** : ...
    - **Reproduction** : ...
    - **Contournement** : ...
    - **Suggestion** : ...

Sortie JSON sur stdout :

    {
      "entries": [
        {
          "id": "R-001",
          "date": "2026-04-27",
          "titre": "...",
          "skills": "...",
          "categorie": "...",
          "severite": "...",
          "resultat": "...",
          "description": "...",
          "reproduction": "...",
          "contournement": "...",
          "suggestion": "...",
          "raw": "...",         # bloc markdown complet de l'entree
          "hash": "<sha1>"       # hash du raw
        }
      ]
    }

Exit codes : 0 succes, 1 erreur applicative, 2 erreur d'usage.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Header d'entree : `## R-NNN -- date -- titre` (1-3 #, on accepte les 2 niveaux usuels)
HEADER_RE = re.compile(
    r"^(#{1,3})\s*(R-\d+)\s*--\s*(\d{4}-\d{2}-\d{2})\s*--\s*(.+?)\s*$",
    re.MULTILINE,
)

# Detection souple d'un en-tete R-NNN, pour reperer ceux MAL FORMES (date manquante,
# separateur incorrect) et les signaler au lieu de les ignorer en silence.
LOOSE_HEADER_RE = re.compile(r"^#{1,3}\s*(R-\d+)\b.*$", re.MULTILINE)

# Bloc de commentaire HTML STRUCTUREL (ex : le bloc "Exemple d'entree" livre avec le
# template) -- ignore au parsing pour ne pas pousser une entree-exemple comme un vrai RETEX.
#
# Un commentaire n'est STRUCTUREL que si son ouvrant demarre une ligne. En milieu de ligne
# c'est du texte d'auteur : une entree qui CITE `<!-- ... -->` doit garder sa citation
# intacte (sans l'ancrage, la citation etait videe et la phrase amputee).
#
# Deux formes, retirees dans cet ordre :
#   1. bloc FERME     : de l'ouvrant en debut de ligne jusqu'au premier `-->`
#   2. bloc NON FERME : de l'ouvrant en debut de ligne jusqu'a la fin du fichier
#
# Sans la seconde, un ouvrant orphelin n'etait pas retire du tout : il atterrissait dans le
# dernier champ parse, puis dans le corps de l'issue, ou -- etant un commentaire HTML jamais
# referme -- il masquait au rendu tout ce qui suit (date, ID local, hash invisibles).
HTML_COMMENT_BLOC_RE = re.compile(r"^[ \t]*<!--.*?-->[ \t]*\n?", re.DOTALL | re.MULTILINE)
HTML_COMMENT_OUVERT_RE = re.compile(r"^[ \t]*<!--.*\Z", re.DOTALL | re.MULTILINE)

# Champ : `- **Nom** : valeur` (multiligne possible jusqu'au prochain `- **` ou header)
FIELD_NAMES = [
    "Skill(s)",
    "Categorie",
    "Severite",
    "Resultat",
    "Description",
    "Reproduction",
    "Contournement",
    "Suggestion",
]

FIELD_KEYS = {
    "Skill(s)":      "skills",
    "Categorie":     "categorie",
    "Severite":      "severite",
    "Resultat":      "resultat",
    "Description":   "description",
    "Reproduction":  "reproduction",
    "Contournement": "contournement",
    "Suggestion":    "suggestion",
}


def normalize_field_name(name: str) -> str:
    return name.strip().lower().replace("e", "e").replace("é", "e")


def parse_entry_body(body: str) -> dict:
    """Parse le corps d'une entree (texte entre l'header et le prochain header)."""
    fields = {}
    # On va chercher chaque champ par regex tolerante (accents optionnels)
    # Le champ se termine au prochain `- **` en debut de ligne, ou EOF.
    for fname in FIELD_NAMES:
        # Tolerance accents sur le NOM du champ : Categorie/Catégorie, Severite/Sévérité,
        # Resultat/Résultat. Sinon un en-tete accentue n'est pas reconnu -> valeur vide ->
        # hash instable -> faux "update" et commentaires indesirables (cf. #338).
        pattern = re.compile(
            r"^-\s*\*\*\s*"
            + (
                re.escape(fname)
                .replace("Categorie", r"Cat[eé]gorie")
                .replace("Severite", r"S[eé]v[eé]rit[eé]")
                .replace("Resultat", r"R[eé]sultat")
            )
            + r"\s*\*\*\s*:\s*(.*?)(?=^\s*-\s*\*\*|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(body)
        if m:
            value = m.group(1).strip()
            # nettoie les retours a la ligne multiples
            value = re.sub(r"\n{3,}", "\n\n", value)
            fields[FIELD_KEYS[fname]] = value
        else:
            fields[FIELD_KEYS[fname]] = ""
    return fields


def parse_file(path: Path):
    """Parse le fichier. Retourne (entries, warnings).

    - Les blocs de commentaire HTML **structurels** (ouvrant en debut de ligne) sont
      retires avant parsing, qu'ils soient fermes ou non : evite de pousser un exemple
      de gabarit comme un vrai RETEX, et evite qu'un ouvrant orphelin ne contamine le
      dernier champ. Une citation `<!-- ... -->` en milieu de ligne est preservee.
    - Les en-tetes `R-NNN` mal formes (date manquante / separateur incorrect) sont
      remontes en warning au lieu d'etre ignores silencieusement.
    """
    raw_text = path.read_text(encoding="utf-8")
    text = HTML_COMMENT_BLOC_RE.sub("", raw_text)
    text = HTML_COMMENT_OUVERT_RE.sub("", text)

    headers = list(HEADER_RE.finditer(text))
    warnings = []
    strict_starts = {m.start() for m in headers}
    for lm in LOOSE_HEADER_RE.finditer(text):
        if lm.start() not in strict_starts:
            warnings.append(
                "En-tete R-NNN ignore (mal forme : date manquante ou separateur "
                f"incorrect) : '{lm.group(0).strip()}'"
            )

    entries = []
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        raw = text[start:end].rstrip()
        body = text[m.end():end]
        entry = {
            "id":    m.group(2),
            "date":  m.group(3),
            "titre": m.group(4),
        }
        entry.update(parse_entry_body(body))
        entry["raw"] = raw
        # hash sur le corps normalise (sans le titre/date qui peuvent bouger)
        normalized_for_hash = "\n".join(
            f"{k}={entry.get(k, '')}" for k in sorted(FIELD_KEYS.values())
        )
        entry["hash"] = hashlib.sha1(normalized_for_hash.encode("utf-8")).hexdigest()
        entries.append(entry)
    return entries, warnings


def main() -> int:
    # stdout UTF-8 force : sinon UnicodeEncodeError sur un caractere hors cp1252
    # (ex U+2248) quand la console Windows est en cp1252.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retex-file", required=True, help="Chemin vers RETEX-skills.md")
    parser.add_argument(
        "--id",
        help="Si fourni, ne renvoie que l'entree de cet ID (ex R-027)",
    )
    args = parser.parse_args()

    path = Path(args.retex_file)
    if not path.exists():
        print(f"ERROR: fichier introuvable : {path}", file=sys.stderr)
        return 1

    try:
        entries, warnings = parse_file(path)
    except Exception as e:
        print(f"ERROR: parsing : {e}", file=sys.stderr)
        return 1

    if args.id:
        entries = [e for e in entries if e["id"] == args.id]

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    print(json.dumps({"entries": entries, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
