"""
Parse un fichier RETEX-skills.md et extrait la liste des entrees R-NNN.

Format d'entree attendu (markdown) :

    ## R-NNN -- YYYY-MM-DD -- Titre court

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
        # Tolerance accents : Categorie/Catégorie, Severite/Sévérité
        pattern = re.compile(
            r"^-\s*\*\*\s*"
            + re.escape(fname).replace("Categorie", r"Cat[eé]gorie").replace("Severite", r"S[eé]v[eé]rit[eé]")
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


def parse_file(path: Path) -> list:
    text = path.read_text(encoding="utf-8")
    headers = list(HEADER_RE.finditer(text))
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
    return entries


def main() -> int:
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
        entries = parse_file(path)
    except Exception as e:
        print(f"ERROR: parsing : {e}", file=sys.stderr)
        return 1

    if args.id:
        entries = [e for e in entries if e["id"] == args.id]

    print(json.dumps({"entries": entries}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
