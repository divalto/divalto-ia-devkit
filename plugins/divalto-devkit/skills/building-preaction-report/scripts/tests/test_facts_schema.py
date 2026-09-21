"""Tests du validator facts_schema.validate_facts_structure.

Couvre :
- Fixture nominale ticket-contremarque : doit passer (0 erreur).
- Fixture degrade : 4 erreurs volontaires doivent etre detectees.
- Cas unitaires du validator (schema_version, unicite, enum, source absolue, etc.).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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


class TestSelectionTitle(unittest.TestCase):
    """Le libelle humain des types voyage dans le facts.json.

    Un retour terrain a signale que le livrable affichait les slugs bruts
    (`endroit_agir`) dans une couche destinee a un chef de projet. Le libelle existe
    depuis toujours dans `content_types.py` ; il ne traversait simplement pas le
    facts.json. Il est emis ICI plutot que reconstitue par le renderer -- deux tables
    de libelles finiraient par diverger.
    """

    def test_le_catalogue_donne_un_libelle_a_chaque_type(self):
        from content_types import CATALOG
        for ct in CATALOG:
            self.assertTrue(ct.title.strip(),
                            "le type %s (%s) n'a pas de libelle humain" % (ct.id, ct.slug))
            self.assertNotEqual(ct.title, ct.slug,
                                "le libelle du type %s est le slug lui-meme" % ct.id)

    def test_selection_entry_transporte_et_serialise_le_libelle(self):
        from dataclasses import asdict
        from facts_schema import SelectionEntry
        e = SelectionEntry(id=4, slug="endroit_agir", score=1.0, included=True,
                           layer="tactical", reason="x", title="Endroit ou agir")
        self.assertEqual(asdict(e)["title"], "Endroit ou agir")

    def test_le_libelle_est_optionnel_et_vaut_chaine_vide(self):
        """Retrocompatibilite : un facts.json anterieur n'a pas ce champ.

        La valeur par defaut doit etre une chaine vide -- pas `None`, que le nettoyage
        de `to_dict` retirerait, et pas une absence, qui ferait echouer la construction.
        """
        from dataclasses import asdict
        from facts_schema import SelectionEntry
        e = SelectionEntry(id=1, slug="s", score=0.0, included=False,
                           layer="technical", reason="r")
        self.assertEqual(asdict(e)["title"], "")

    def test_un_facts_sans_libelle_reste_valide(self):
        doc = _load_fixture("ticket-contremarque.facts.json")
        for s in doc["selection"]:
            s.pop("title", None)
        self.assertEqual(validate_facts_structure(doc), [],
                         "retirer un champ optionnel ne doit pas invalider le document")

    def test_un_facts_avec_libelle_reste_valide(self):
        doc = _load_fixture("ticket-contremarque.facts.json")
        for s in doc["selection"]:
            s["title"] = "Un libelle"
        self.assertEqual(validate_facts_structure(doc), [])

    def test_le_producteur_transmet_le_libelle(self):
        """Le maillon du milieu : le catalogue le produit, le schema le porte -- encore
        faut-il que la construction le RECOPIE.

        Controle sur la SOURCE et non par execution : cette recopie vit au milieu d'une
        fonction de pipeline qui demande les trois JSON d'entree.

        AVERTISSEMENT. Ce docstring disait aussi qu'un test fabriquant les trois
        JSON « mesurerait surtout sa propre fixture ». C'est ce raisonnement qui a
        laisse passer un `TypeError` a chaque execution : `build_seeds` etait
        appelee avec quatre arguments pour cinq parametres obligatoires. Trois
        fichiers d'entree construits depuis les exigences de `preflight_check`
        parcourent tout le pipeline -- voir `TestPipelineComplet`. Un harnais de mutation a montre
        que sans ce cas, retirer la recopie ne faisait tomber AUCUNE suite -- les deux
        extremites etaient gardees, le milieu ne l'etait pas.
        """
        source = (SCRIPTS_DIR / "build_facts.py").read_text(encoding="utf-8")
        debut = source.index("selection.append(SelectionEntry(")
        bloc = source[debut:source.index("))", debut)]
        self.assertIn("title=", bloc,
                      "la construction de SelectionEntry ne transmet plus le libelle")
        self.assertIn('s.get("title"', bloc,
                      "le libelle n'est plus repris de l'entree du catalogue")


class TestPipelineComplet(unittest.TestCase):
    """Le pipeline complet, execute -- pas lu.

    `build_facts.py` appelait `build_seeds` avec quatre arguments pour cinq
    parametres obligatoires : `TypeError` a chaque execution, dans un script livre.
    Rien ne l'avait vu, parce que les deux fixtures du skill sont des SORTIES et que
    la seule verification qui touchait ce fichier le lisait en texte.

    Les trois entrees sont construites depuis les exigences que `preflight_check`
    enonce dans son propre docstring : `type`, `resume`, `domaine_pressenti`,
    deux `keywords_techniques`, des `functions` non vides, un `confirmed` avec son
    `targeted_symbol` et son `enclosing_block`. Rien d'invente.
    """

    def _lancer(self, sortie):
        fx = Path(__file__).resolve().parent / "fixtures"
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "build_facts.py"),
             "--request", str(fx / "pipeline-ticket.request.json"),
             "--candidates", str(fx / "pipeline-ticket.candidates.json"),
             "--evidence", str(fx / "pipeline-ticket.evidence.json"),
             "--output-dir", sortie, "--slug", "pipeline", "--date", "20260911",
             "--erp-root", "/erp-de-test"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_le_pipeline_va_au_bout(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._lancer(d)
            self.assertEqual(
                r.returncode, 0,
                "build_facts.py ne va pas au bout : rc=%d%s%s"
                % (r.returncode, os.linesep, (r.stderr or "")[:600]))
            produits = sorted(p.name for p in Path(d).glob("preaction-*"))
            self.assertEqual(
                produits,
                ["preaction-pipeline-20260911.facts.json",
                 "preaction-pipeline-20260911.metrics.json"],
                "les deux fichiers attendus ne sont pas produits : %s" % produits)

    def test_le_facts_produit_est_valide(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._lancer(d)
            self.assertEqual(r.returncode, 0, (r.stderr or "")[:400])
            p = Path(d) / "preaction-pipeline-20260911.facts.json"
            doc = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(validate_facts_structure(doc), [],
                             "le facts.json produit ne valide pas son schema")
            self.assertTrue(doc.get("claims"),
                            "le facts.json produit ne porte aucun claim")


if __name__ == "__main__":
    unittest.main()
