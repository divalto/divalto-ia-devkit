"""Tests de pushing-retex-to-github : unicite des R-NNN, verrou, parsing des commentaires.

Chacun de ces cas TOMBE sur le code d'avant les correctifs -- c'est la condition pour
qu'il mesure quelque chose. Les quatre defauts couverts ont tous ete observes sur le
depot partenaire avant d'etre corriges.

Couvre :
- Commentaires HTML : bloc ferme retire, bloc NON ferme retire, citation inline preservee.
- Hash : composition (8 champs dedans, id/date/titre dehors) et pied de page complet.
- Unicite : deux entrees sous un meme R-NNN sont renumerotees AVANT tout appel GitHub ;
  l'entree deja poussee garde son numero ; le gabarit commente n'est jamais renumerote ;
  pas d'ecriture en --dry-run.
- Verrou : un second push concurrent abandonne ; un verrou perime est repris.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
PARSE = SCRIPTS_DIR / "parse_retex_entries.py"


def _charge(nom: str):
    """Importe un script du skill sans l'executer."""
    spec = importlib.util.spec_from_file_location(nom, SCRIPTS_DIR / f"{nom}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ENTREE = """### {eid} -- {date} -- {titre}

- **Skill(s)** : {skills}
- **Categorie** : BUG-SKILL
- **Severite** : HAUTE
- **Resultat** : {resultat}
- **Description** : {description}
- **Reproduction** : reproduction
- **Contournement** : contournement
- **Suggestion** : suggestion
"""

GABARIT_COMMENTE = """<!-- Exemple d'entree :

### R-001 -- 2026-04-15 -- Titre court du probleme

- **Skill(s)** : nom-du-skill
- **Resultat** : KO (description courte)

-->"""


def entree(eid="R-050", date="2026-09-07", titre="Titre", skills="un-skill",
           resultat="KO", description="Description."):
    return ENTREE.format(eid=eid, date=date, titre=titre, skills=skills,
                         resultat=resultat, description=description)


def fichier(*blocs):
    return "# RETEX\n\n## Journal\n\n" + "\n".join(blocs) + "\n"


def parse(texte, tmpdir):
    chemin = Path(tmpdir) / "RETEX-skills.md"
    chemin.write_text(texte, encoding="utf-8")
    r = subprocess.run([sys.executable, str(PARSE), "--retex-file", str(chemin)],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"parse_retex_entries.py a echoue : {r.stderr}")
    return json.loads(r.stdout)["entries"]


class TestCommentairesHtml(unittest.TestCase):
    """Le bloc d'exemple livre avec le gabarit ne doit jamais devenir une entree, et un
    ouvrant orphelin ne doit jamais contaminer le dernier champ parse."""

    def _sans_fragment(self, entrees):
        for e in entrees:
            for champ in ("resultat", "description", "contournement", "suggestion"):
                self.assertNotIn("<!--", e.get(champ) or "",
                                 f"fragment de commentaire dans le champ {champ}")

    def test_bloc_ferme_avant_les_entrees(self):
        with tempfile.TemporaryDirectory() as d:
            e = parse(fichier(GABARIT_COMMENTE, entree()), d)
            self.assertEqual([x["id"] for x in e], ["R-050"])
            self._sans_fragment(e)

    def test_bloc_ferme_apres_les_entrees(self):
        with tempfile.TemporaryDirectory() as d:
            e = parse(fichier(entree(), GABARIT_COMMENTE), d)
            self.assertEqual([x["id"] for x in e], ["R-050"])
            self._sans_fragment(e)

    def test_ouvrant_non_ferme_apres_les_entrees(self):
        """TOMBE avant correctif : la regex exigeait un `-->`, donc l'ouvrant restait et
        atterrissait dans le champ Suggestion, puis dans le corps de l'issue ou -- jamais
        referme -- il masquait le pied de page au rendu GitHub."""
        with tempfile.TemporaryDirectory() as d:
            e = parse(fichier(entree(), "<!-- Exemple d'entree :"), d)
            self.assertEqual(len(e), 1)
            self._sans_fragment(e)

    def test_deux_blocs_le_second_non_ferme(self):
        """TOMBE avant correctif."""
        with tempfile.TemporaryDirectory() as d:
            e = parse(fichier(GABARIT_COMMENTE, entree(), "<!-- Exemple d'entree :"), d)
            self.assertEqual(len(e), 1)
            self._sans_fragment(e)

    def test_citation_inline_preservee(self):
        """TOMBE avant correctif : le retrait n'etait pas ancre en debut de ligne, donc une
        entree qui CITE `<!-- ... -->` voyait sa citation videe et sa phrase amputee."""
        cite = ("Supprimer le bloc `<!-- Exemple d'entree : ... -->` du fichier "
                "avant tout push.")
        with tempfile.TemporaryDirectory() as d:
            e = parse(fichier(entree(description=cite)), d)
            self.assertEqual(len(e), 1)
            self.assertIn("<!-- Exemple d'entree : ... -->", e[0]["description"])


class TestHash(unittest.TestCase):

    def _hash(self, d, **kw):
        return parse(fichier(entree(**kw)), d)[0]["hash"]

    def test_composition_du_hash(self):
        """8 champs entrent dans le hash ; id, date et titre en sont exclus -- c'est ce qui
        permet de retoucher un titre sans declencher un faux commentaire."""
        with tempfile.TemporaryDirectory() as d:
            ref = self._hash(d)
            self.assertEqual(ref, self._hash(d, eid="R-999"), "l'id ne doit pas entrer dans le hash")
            self.assertEqual(ref, self._hash(d, date="2026-12-31"), "la date ne doit pas entrer")
            self.assertEqual(ref, self._hash(d, titre="Autre titre"), "le titre ne doit pas entrer")
            self.assertNotEqual(ref, self._hash(d, resultat="AUTRE"), "resultat doit entrer")
            self.assertNotEqual(ref, self._hash(d, description="Autre."), "description doit entrer")
            self.assertNotEqual(ref, self._hash(d, skills="autre-skill"), "skills doit entrer")

    def test_pied_de_page_porte_le_hash_complet(self):
        """TOMBE avant correctif : le pied de page etait tronque a 8 caracteres, ce qui
        rendait l'arbitrage d'un conflit de numerotation approximatif."""
        pe = _charge("push_entry")
        with tempfile.TemporaryDirectory() as d:
            e = parse(fichier(entree()), d)[0]
            corps = pe.format_body(e, "source.md", "moi@ex.fr")
            self.assertIn(f"_Hash : {e['hash']}_", corps)
            self.assertEqual(len(e["hash"]), 40)


class _BancDePush:
    """Lance le vrai push_new_entries.py sans appeler gh ni le reseau."""

    def __init__(self, dossier, tracking=None, hash_issue=None):
        self.d = Path(dossier)
        self.d.mkdir(parents=True, exist_ok=True)
        (self.d / ".retex-github.json").write_text(json.dumps({"repo": "org/depot"}), encoding="utf-8")
        (self.d / ".retex-pushed.json").write_text(json.dumps(tracking or {}), encoding="utf-8")
        # Hash que GitHub "connait" pour l'issue, dans l'ordre de confiance : corps
        # d'abord, puis commentaires du plus recent au plus ancien.
        self.hashes_issue = [hash_issue] if hash_issue else []
        self.prochaine_issue = 900
        self.appels = []

    def run(self, texte=None, argv_extra=()):
        if texte is not None:
            (self.d / "RETEX-skills.md").write_text(texte, encoding="utf-8")
        m = _charge("push_new_entries")

        def faux_push_one(entry, config_path, source_file, pushed_by, update_issue):
            if update_issue is not None:
                self.appels.append({"action": "COMMENTAIRE", "id": entry["id"],
                                    "hash": entry["hash"], "issue": update_issue})
                return {"action": "updated", "issue": update_issue, "url": f"u/{update_issue}"}
            n = self.prochaine_issue
            self.prochaine_issue += 1
            self.appels.append({"action": "CREATION", "id": entry["id"],
                                "hash": entry["hash"], "issue": n})
            return {"action": "created", "issue": n, "url": f"u/{n}"}

        m.push_one = faux_push_one
        m.detect_pushed_by = lambda: "test"
        m.hashes_connus_de_l_issue = lambda repo, numero: list(self.hashes_issue)

        argv = sys.argv
        sys.argv = ["push_new_entries", "--retex-file", str(self.d / "RETEX-skills.md"), *argv_extra]
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            code = m.main()
        finally:
            sys.stdout, sys.argv = old, argv
        tracking = json.loads((self.d / ".retex-pushed.json").read_text(encoding="utf-8"))
        return code, json.loads(buf.getvalue()), tracking

    @property
    def texte_fichier(self):
        return (self.d / "RETEX-skills.md").read_text(encoding="utf-8")

    def derniere_ligne_conflit(self, eid):
        """Comment le dernier conflit a ete arbitre. Le CHEMIN compte autant que le
        resultat : un repli silencieux sur le tracking donne souvent la bonne reponse,
        mais par chance -- et le tracking est justement corrompu dans le cas abime."""
        lignes = [l for l in (self.d / ".retex-push.log").read_text(encoding="utf-8").splitlines()
                  if f"conflit {eid}" in l]
        return lignes[-1] if lignes else ""


class TestUniciteDesNumeros(unittest.TestCase):
    """Deux entrees sous un meme R-NNN se partagent une seule case de tracking : chacune
    trouve le hash de l'autre, conclut 'modifiee' et commente l'issue de l'autre, a chaque
    passage. Observe sur le depot : une issue a accumule 111 commentaires alternes."""

    A = dict(eid="R-024", date="2026-08-20", titre="Premier", description="Contenu A.")
    B = dict(eid="R-024", date="2026-08-21", titre="Second", description="Contenu B.")

    def test_deux_entrees_meme_numero_donnent_deux_issues(self):
        """TOMBE avant correctif : la seconde partait en COMMENTAIRE sur l'issue de la
        premiere au lieu d'avoir la sienne."""
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(Path(d) / "ws")
            _, sortie, tracking = banc.run(fichier(entree(**self.A), entree(**self.B)))
            actions = [a["action"] for a in banc.appels]
            self.assertEqual(actions, ["CREATION", "CREATION"])
            self.assertEqual(len(tracking), 2, "chaque contenu doit avoir sa propre fiche")
            self.assertEqual(len(sortie.get("renumerotations", [])), 1)

    def test_etat_stable_au_passage_suivant(self):
        """TOMBE avant correctif : chaque passage reproduisait deux commentaires,
        indefiniment, le tracking ne convergeant jamais."""
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(Path(d) / "ws")
            texte = fichier(entree(**self.A), entree(**self.B))
            banc.run(texte)
            banc.appels.clear()
            banc.run()  # le fichier a ete renumerote, on repasse dessus tel quel
            self.assertEqual(banc.appels, [], "aucun appel au second passage")

    def test_entree_deja_poussee_garde_son_numero(self):
        """L'arbitrage doit designer l'entree que l'issue existante contient : sinon on
        cree un doublon de cette issue ET on commente au mauvais endroit."""
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(Path(d) / "ws")
            banc.run(fichier(entree(**self.B)))          # B poussee seule
            hash_b = banc.appels[0]["hash"]
            banc.hashes_issue = [hash_b]                  # le corps de l'issue contient B
            banc.appels.clear()
            _, sortie, tracking = banc.run(fichier(entree(**self.A), entree(**self.B)))
            self.assertEqual([a["action"] for a in banc.appels], ["CREATION"],
                             "seule A doit partir, en creation")
            self.assertEqual(tracking["R-024"]["hash"], hash_b, "B garde R-024")
            self.assertEqual(sortie["renumerotations"][0]["titre"], "Premier")

    def test_entree_deja_modifiee_est_retrouvee_dans_les_commentaires(self):
        """TOMBE avant le correctif, sur le CHEMIN d'arbitrage -- pas sur le resultat.

        Le corps d'une issue est un instantane fige a la creation : une mise a jour
        n'ajoute qu'un commentaire. Des qu'une entree avait ete modifiee une fois, son
        hash courant n'etait plus dans le corps, et l'arbitrage se rabattait EN SILENCE
        sur le tracking. Mesure en conditions reelles sur une vraie issue : le hash etait
        bien connu de GitHub, dans le commentaire de mise a jour.

        Le repli donnait ici la bonne reponse -- mais par chance, et le tracking est
        precisement ce qui est corrompu dans le cas qu'on cherche a reparer. C'est donc
        le chemin qu'on asserte : l'arbitrage doit ABOUTIR sur l'issue.
        """
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(Path(d) / "ws")
            banc.run(fichier(entree(**self.B)))              # B creee -> corps de l'issue
            hash_corps = banc.appels[0]["hash"]
            B2 = dict(self.B, description="Contenu B, enrichi apres coup.")
            banc.appels.clear()
            banc.run(fichier(entree(**B2)))                   # B modifiee -> commentaire
            hash_courant = banc.appels[0]["hash"]
            self.assertNotEqual(hash_corps, hash_courant, "la modification doit changer le hash")
            # GitHub connait donc : le corps (ancien) PUIS le commentaire (courant).
            banc.hashes_issue = [hash_corps, hash_courant]
            banc.appels.clear()
            _, sortie, tracking = banc.run(fichier(entree(**self.A), entree(**B2)))
            self.assertEqual([a["action"] for a in banc.appels], ["CREATION"],
                             "seule A doit partir : B est deja suivie")
            self.assertEqual(tracking["R-024"]["hash"], hash_courant, "B garde R-024")
            self.assertEqual(sortie["renumerotations"][0]["titre"], "Premier")
            ligne = banc.derniere_ligne_conflit("R-024")
            self.assertIn("arbitre par l'issue", ligne,
                          f"l'arbitrage doit aboutir sur l'issue, pas se replier. Log : {ligne}")
            self.assertNotIn("par le tracking", ligne)

    def test_le_corps_tranche_sur_une_issue_abimee_par_le_ping_pong(self):
        """GARDE-FOU, pas un discriminant : il passe aussi sur le code d'avant.

        Quand les DEUX contenus figurent dans l'historique de l'issue -- ce qui est la
        signature du ping-pong -- c'est le corps qui fait foi : c'est ce que l'issue EST.
        Le cas protege cette priorite contre une reecriture qui classerait les hash par
        recence : on rendrait alors le numero a l'entree ayant commente en dernier, ce
        qui est arbitraire.
        """
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(Path(d) / "ws")
            banc.run(fichier(entree(**self.A)))              # A creee -> corps
            hash_a = banc.appels[0]["hash"]
            banc.appels.clear()
            banc.run(fichier(entree(**self.B)))              # B commente la meme issue
            hash_b = banc.appels[0]["hash"]
            # Historique GitHub : corps = A, commentaire le plus recent = B.
            banc.hashes_issue = [hash_a, hash_b]
            banc.appels.clear()
            _, sortie, tracking = banc.run(fichier(entree(**self.A), entree(**self.B)))
            self.assertEqual(tracking["R-024"]["hash"], hash_a,
                             "A, qui EST le corps de l'issue, doit garder R-024")
            self.assertEqual(sortie["renumerotations"][0]["titre"], "Second")

    def test_le_gabarit_commente_n_est_jamais_renumerote(self):
        """Le gabarit livre contient un `### R-001` : ce n'est pas une entree."""
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(Path(d) / "ws")
            banc.run(fichier(GABARIT_COMMENTE, entree(**self.A), entree(**self.B)))
            texte = banc.texte_fichier
            self.assertIn("### R-001 -- 2026-04-15 -- Titre court du probleme", texte)
            self.assertIn("<!-- Exemple d'entree :", texte)
            self.assertIn("-->", texte)

    def test_dry_run_n_ecrit_pas_le_fichier(self):
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(Path(d) / "ws")
            texte = fichier(entree(**self.A), entree(**self.B))
            banc.run(texte, argv_extra=("--dry-run",))
            self.assertEqual(banc.texte_fichier, texte, "le fichier ne doit pas bouger")


class TestVerrou(unittest.TestCase):
    """Le hook lance un push detache a chaque ecriture du RETEX : deux editions rapprochees
    produisent deux pushes simultanes qui creent chacun leur issue. Mesure sur le depot :
    19 paires de doublons sur 19 avaient ce profil (meme id, meme hash, quelques secondes)."""

    def test_un_second_push_concurrent_abandonne(self):
        """TOMBE avant correctif : le second push creait une seconde issue."""
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(Path(d) / "ws")
            banc.run(fichier(entree()))
            m = _charge("push_new_entries")
            verrou = banc.d / m.VERROU_NOM
            verrou.write_text("autre-process\n", encoding="utf-8")
            banc.appels.clear()
            _, sortie, _ = banc.run()
            self.assertEqual(banc.appels, [], "aucun appel quand le verrou est pris")
            self.assertEqual(sortie["skipped"][0]["reason"], "push-concurrent-ignore")

    def test_verrou_perime_est_repris(self):
        """Sans peremption, un seul process tue bloquerait tous les pushes suivants."""
        with tempfile.TemporaryDirectory() as d:
            m = _charge("push_new_entries")
            chemin = Path(d) / m.VERROU_NOM
            chemin.write_text("mort\n", encoding="utf-8")
            vieux = time.time() - (m.VERROU_PERIME_S + 60)
            import os
            os.utime(chemin, (vieux, vieux))
            self.assertTrue(m.prendre_verrou(chemin, Path(d) / "log.txt"))
            m.relacher_verrou(chemin)
            self.assertFalse(chemin.exists())

    def test_verrou_frais_n_est_pas_repris(self):
        with tempfile.TemporaryDirectory() as d:
            m = _charge("push_new_entries")
            chemin = Path(d) / m.VERROU_NOM
            chemin.write_text("vivant\n", encoding="utf-8")
            self.assertFalse(m.prendre_verrou(chemin, Path(d) / "log.txt"))


class TestFichierDuPartenaire(unittest.TestCase):
    """La renumerotation est le SEUL endroit ou ce skill reecrit le journal du
    collaborateur. Ce qu il y ecrit doit se limiter a ce qui a ete annonce : un
    identifiant. Tout le reste -- fins de ligne comprises -- lui appartient.

    Les deux cas mesurent au niveau OCTET. Les helpers de la suite lisent en newline
    universel, ce qui effacerait justement la difference qu on cherche.
    """

    A = dict(eid="R-024", date="2026-08-20", titre="Premier", description="Contenu A.")
    B = dict(eid="R-024", date="2026-08-21", titre="Second", description="Contenu B.")
    CRLF = chr(13) + chr(10)

    def _ecrire_crlf(self, banc):
        """Ecrit la fixture en CRLF, en OCTETS : write_text traduirait."""
        texte = fichier(entree(**self.A), entree(**self.B))
        octets = texte.replace(self.CRLF, chr(10)).replace(chr(10), self.CRLF)
        octets = octets.encode("utf-8")
        with open(banc.d / "RETEX-skills.md", "wb") as f:
            f.write(octets)
        return octets

    def _relire(self, banc):
        with open(banc.d / "RETEX-skills.md", "rb") as f:
            return f.read()

    def test_les_fins_de_ligne_du_partenaire_sont_preservees(self):
        """TOMBE avant correctif : 24 CRLF avant, 0 apres.

        `read_text()` traduit les CRLF en LF a la LECTURE ; `newline=""` a
        l ecriture n empeche que la traduction de SORTIE et ne restitue rien. Les
        quatre RETEX du workspace et le gabarit livre sont tous en CRLF : le defaut
        se declenchait au premier doublon reel.
        """
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(d)
            avant = self._ecrire_crlf(banc)
            banc.run()
            apres = self._relire(banc)
            self.assertGreater(avant.count(b'\r\n'), 0, "fixture sans CRLF : le cas ne mesure rien")
            self.assertEqual(
                apres.count(b'\r\n'),
                avant.count(b'\r\n'),
                "le journal du partenaire a change de fins de ligne")
            self.assertEqual(
                apres.replace(b'\r\n', b'').count(b'\n'), 0,
                "des fins de ligne LF isolees sont apparues")

    def test_le_fichier_est_intact_octet_a_octet_hors_identifiant(self):
        """TOMBE avant correctif : une ligne vide disparaissait par entree.

        `HEADER_FICHIER_RE` finissait par `\\s*$`, et `\\s` contient le saut de ligne :
        le motif consommait le CRLF suivant le titre, que la reecriture ne
        restituait pas. Le fichier restait reparsable -- donc invisible aux autres
        cas -- mais le journal du collaborateur perdait une ligne a chaque passage.
        """
        with tempfile.TemporaryDirectory() as d:
            banc = _BancDePush(d)
            avant = self._ecrire_crlf(banc)
            code, sortie, _ = banc.run()
            self.assertEqual(code, 0, sortie)
            renum = sortie.get("renumerotations") or []
            self.assertEqual(len(renum), 1, "une seule entree devait etre renumerotee : %s" % renum)
            nouveau = renum[0]["nouveau"]
            attendu = avant.replace(
                ("### R-024 -- 2026-08-21").encode("utf-8"),
                ("### %s -- 2026-08-21" % nouveau).encode("utf-8"))
            self.assertEqual(self._relire(banc), attendu,
                             "le fichier a change au-dela du seul identifiant")


if __name__ == "__main__":
    # Meme garde que les suites soeurs : une console Windows en cp1252 leve
    # UnicodeEncodeError des qu'une sortie porte un caractere hors de sa page de codes.
    # La suite est ecrite en ASCII, mais elle imprime des extraits de fichiers RETEX
    # qui, eux, ne le sont pas.
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    unittest.main(verbosity=2)
