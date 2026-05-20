#!/usr/bin/env python3
"""
translate_keywords.py -- Traduit un texte conversationnel francais en symboles techniques DIVA.

Lit le lexique `reference/lexique-metier-technique.md` du skill et applique un
matching naif (substring, case-insensitive, normalisation accents) pour extraire
les symboles techniques candidats.

Usage :
    echo "quand j'active l'option tiers par etablissement ..." | py translate_keywords.py
    py translate_keywords.py --text "le zoom client ne montre plus rien"

Sortie JSON :
    {
      "concepts_detected": ["option dans le dossier", "tiers par etablissement", "zoom client"],
      "symbols_candidates": [
        {"concept": "...", "symbols": ["SOC.EntCodN(N)", ...], "priority": 1}
      ],
      "files_to_grep_first": ["a5rsrub.dhsq", "grtz002_sql.dhsp"]
    }
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


def normalize(text):
    """Minuscules + retrait des accents + trim."""
    text = text.lower().strip()
    text = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in text if not unicodedata.combining(c))


def load_lexique(lexique_path):
    """Parse le lexique markdown et extrait les entrees (concept, symboles, fichier)."""
    if not lexique_path.exists():
        return []
    content = lexique_path.read_text(encoding='utf-8')
    entries = []
    current_section = None
    for line in content.splitlines():
        section_match = re.match(r'^##\s+(.+?)\s*$', line)
        if section_match:
            current_section = section_match.group(1).strip()
            continue
        row_match = re.match(r'^\|\s*"?([^"|]+?)"?\s*\|\s*(.+?)\s*\|', line)
        if not row_match:
            continue
        concept = row_match.group(1).strip()
        if concept in ('Concept', 'Concept conversationnel', '---', 'Symptome conversationnel'):
            continue
        if concept.startswith('-'):
            continue
        symbols_raw = row_match.group(2).strip()
        symbols = [s.strip().strip('`') for s in re.split(r',|;|\|', symbols_raw) if s.strip()]
        entries.append({
            'concept': concept,
            'symbols': symbols,
            'section': current_section,
        })
    return entries


def match_concepts(text, lexique):
    """Detecte les concepts du lexique presents dans le texte (match sur sous-chaine normalisee)."""
    text_norm = normalize(text)
    matches = []
    for entry in lexique:
        concept_norm = normalize(entry['concept'])
        if len(concept_norm) < 4:
            continue
        tokens = [t for t in concept_norm.split() if len(t) >= 4]
        if not tokens:
            continue
        hits = sum(1 for t in tokens if t in text_norm)
        if hits >= min(2, len(tokens)):
            matches.append({
                'concept': entry['concept'],
                'symbols': entry['symbols'],
                'section': entry['section'],
                'match_score': hits / len(tokens),
            })
    matches.sort(key=lambda m: (-m['match_score'], m['concept']))
    seen = set()
    dedup = []
    for m in matches:
        key = m['concept']
        if key not in seen:
            seen.add(key)
            dedup.append(m)
    return dedup


def pick_priority_files(matches):
    """Heuristique : fichiers a grep en priorite selon les concepts detectes."""
    priority = []
    for m in matches:
        for sym in m['symbols']:
            if sym.endswith('.dhsq') or sym.endswith('.dhsp') or sym.endswith('.dhsf') or sym.endswith('.dhsd'):
                priority.append(sym)
    seen = set()
    out = []
    for f in priority:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out[:5]


def main():
    parser = argparse.ArgumentParser(description="Traduit un texte conversationnel en symboles DIVA candidats")
    parser.add_argument('--text', help="Texte a analyser (sinon stdin)")
    parser.add_argument('--lexique', help="Chemin du lexique (defaut: reference/lexique-metier-technique.md)")
    args = parser.parse_args()

    text = args.text or sys.stdin.read()
    if not text.strip():
        print(json.dumps({'error': 'empty input'}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)

    default_lexique = Path(__file__).resolve().parent.parent / 'reference' / 'lexique-metier-technique.md'
    lexique_path = Path(args.lexique) if args.lexique else default_lexique

    lexique = load_lexique(lexique_path)
    if not lexique:
        print(json.dumps({'error': 'lexique not loaded', 'path': str(lexique_path)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(3)

    matches = match_concepts(text, lexique)
    priority_files = pick_priority_files(matches)

    output = {
        'input_length': len(text),
        'lexique_entries_loaded': len(lexique),
        'concepts_detected': [m['concept'] for m in matches],
        'symbols_candidates': [
            {'concept': m['concept'], 'symbols': m['symbols'], 'section': m['section'], 'match_score': round(m['match_score'], 2)}
            for m in matches
        ],
        'files_to_grep_first': priority_files,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
