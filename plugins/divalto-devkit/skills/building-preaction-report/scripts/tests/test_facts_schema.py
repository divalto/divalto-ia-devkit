"""Tests du validator facts_schema.validate_facts_structure.

Couvre :
- Fixture nominale ticket-contremarque : doit passer (0 erreur).
- Fixture degrade : 4 erreurs volontaires doivent etre detectees.
- Cas unitaires du validator (schema_version, unicite, enum, source absolue, etc.).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# Permet d'importer facts_schema depuis scripts/
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from facts_schema import (  # noqa: E402
    SCHEMA_VERSION,
    validate_facts_structure,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        return json.load(f)


class TestFixtureNominal(unittest.TestCase):
    """Le fixture ticket-contremarque.facts.json doit etre valide."""

    def test_nominal_is_valid(self):
        doc = _load_fixture("ticket-contremarque.facts.json")
        errors = validate_facts_structure(doc)
        self.assertEqual(
            errors,
            [],
            msg=f"Fixture nominale doit passer, erreurs inattendues:\n" + "\n".join(errors),
        )

    def test_nominal_has_schema_version(self):
        doc = _load_fixture("ticket-contremarque.facts.json")
        self.assertEqual(doc["schema_version"], SCHEMA_VERSION)

    def test_nominal_has_at_least_15_claims(self):
        """CA : le fixture doit etre riche (couvre les 9 types par layer)."""
        doc = _load_fixture("ticket-contremarque.facts.json")
        self.assertGreaterEqual(len(doc["claims"]), 15)

    def test_nominal_covers_included_types(self):
        """Chaque type inclus dans selection a au moins 1 claim correspondant."""
        doc = _load_fixture("ticket-contremarque.facts.json")
        included = {s["id"] for s in doc["selection"] if s["included"]}
        claim_ctids = {c["content_type_id"] for c in doc["claims"]}
        missing = included - claim_ctids
        self.assertEqual(missing, set(), f"types inclus sans claim : {missing}")


class TestFixtureDegrade(unittest.TestCase):
    """Le fixture degrade doit remonter les 4 erreurs volontaires."""

    def setUp(self):
        self.doc = _load_fixture("ticket-degrade.facts.json")
        self.errors = validate_facts_structure(self.doc)

    def test_degrade_has_errors(self):
        self.assertGreater(len(self.errors), 0, "Fixture degrade doit remonter des erreurs.")

    def test_detects_claim_without_source(self):
        """Erreur 1 : C1 n'a pas de source (kind=example exige >= 1 source)."""
        matches = [e for e in self.errors if "C1" in e and "source" in e.lower()]
        self.assertTrue(
            matches,
            f"Doit detecter C1 sans source. Erreurs vues : {self.errors}",
        )

    def test_detects_invalid_layer(self):
        """Erreur 2 : C2 a layer='wrong_layer'."""
        matches = [e for e in self.errors if "C2" in e and "wrong_layer" in e]
        self.assertTrue(
            matches,
            f"Doit detecter layer invalide sur C2. Erreurs vues : {self.errors}",
        )

    def test_detects_edge_to_unknown_node(self):
        """Erreur 3 : C3 a un edge vers N_inexistant."""
        matches = [
            e for e in self.errors if "C3" in e and "N_inexistant" in e
        ]
        self.assertTrue(
            matches,
            f"Doit detecter edge vers node inconnu. Erreurs vues : {self.errors}",
        )

    def test_detects_source_ref_to_unknown_claim(self):
        """Erreur 3bis : C3 node N1 pointe vers C99_inexistant."""
        matches = [
            e for e in self.errors if "C99_inexistant" in e
        ]
        self.assertTrue(
            matches,
            f"Doit detecter source_ref vers claim inconnu. Erreurs vues : {self.errors}",
        )

    def test_detects_selection_without_matching_claim(self):
        """Erreur 4 : selection id=7 inclus mais aucun claim avec content_type_id=7."""
        matches = [
            e for e in self.errors if "content_type_id=7" in e and "included" in e
        ]
        self.assertTrue(
            matches,
            f"Doit detecter selection incoherente. Erreurs vues : {self.errors}",
        )


class TestValidatorUnitaires(unittest.TestCase):
    """Cas unitaires du validator : chaque regle testee isolement."""

    def _minimal_valid_doc(self) -> dict:
        """Document minimal valide. Sert de base pour tester les regressions."""
        return {
            "schema_version": SCHEMA_VERSION,
            "slug": "test",
            "date": "2026-04-23",
            "request": {
                "type": "ticket",
                "domaine": "GT_",
                "titre": "Test",
                "resume": "Test.",
            },
            "verdict": {"kind": "investigate", "one_line": "Test."},
            "coverage": {
                "neo4j_status": "available",
                "signal_ratio": 0.5,
                "confiance": "moyenne",
            },
            "claims": [
                {
                    "id": "C1",
                    "content_type_id": 1,
                    "layer": "tactical",
                    "kind": "example",
                    "claim": "Test claim.",
                    "confidence": "high",
                    "sources": [
                        {
                            "status": "CONFIRME_X13",
                            "path": "C:/abs/path/file.dhsp",
                            "line": 1,
                        }
                    ],
                }
            ],
            "selection": [
                {
                    "id": 1,
                    "slug": "exemples",
                    "score": 1.0,
                    "included": True,
                    "layer": "tactical",
                    "reason": "test",
                }
            ],
        }

    def test_minimal_valid_passes(self):
        errors = validate_facts_structure(self._minimal_valid_doc())
        self.assertEqual(errors, [])

    def test_wrong_schema_version(self):
        doc = self._minimal_valid_doc()
        doc["schema_version"] = "0.9"
        errors = validate_facts_structure(doc)
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_missing_top_level_key(self):
        doc = self._minimal_valid_doc()
        del doc["coverage"]
        errors = validate_facts_structure(doc)
        self.assertTrue(any("coverage" in e for e in errors))

    def test_duplicate_claim_id(self):
        doc = self._minimal_valid_doc()
        doc["claims"].append(dict(doc["claims"][0]))
        errors = validate_facts_structure(doc)
        self.assertTrue(any("duplicate" in e.lower() for e in errors))

    def test_invalid_source_status(self):
        doc = self._minimal_valid_doc()
        doc["claims"][0]["sources"][0]["status"] = "BOGUS"
        errors = validate_facts_structure(doc)
        self.assertTrue(any("BOGUS" in e for e in errors))

    def test_relative_path_rejected(self):
        doc = self._minimal_valid_doc()
        doc["claims"][0]["sources"][0]["path"] = "relative/path.dhsp"
        errors = validate_facts_structure(doc)
        self.assertTrue(any("absolute" in e for e in errors))

    def test_invalid_kind(self):
        doc = self._minimal_valid_doc()
        doc["claims"][0]["kind"] = "bogus_kind"
        errors = validate_facts_structure(doc)
        self.assertTrue(any("bogus_kind" in e for e in errors))

    def test_call_chain_without_sources_is_ok(self):
        """call_chain ne requiert pas de source (refs dans nodes)."""
        doc = self._minimal_valid_doc()
        doc["claims"].append({
            "id": "C2",
            "content_type_id": 3,
            "layer": "tactical",
            "kind": "call_chain",
            "claim": "Chain de test.",
            "sources": [],
            "nodes": [
                {"id": "N0", "kind": "ui", "label": "Start"},
                {"id": "N1", "kind": "fn", "name": "Fn1", "source_ref": "C1"},
            ],
            "edges": [["N0", "N1"]],
        })
        doc["selection"].append({
            "id": 3,
            "slug": "etude_impact",
            "score": 1.0,
            "included": True,
            "layer": "tactical",
            "reason": "chain present",
        })
        errors = validate_facts_structure(doc)
        self.assertEqual(errors, [])

    def test_call_chain_without_nodes_fails(self):
        doc = self._minimal_valid_doc()
        doc["claims"].append({
            "id": "C2",
            "content_type_id": 3,
            "layer": "tactical",
            "kind": "call_chain",
            "claim": "Chain invalide.",
            "sources": [],
        })
        errors = validate_facts_structure(doc)
        self.assertTrue(any("call_chain must have 'nodes'" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
