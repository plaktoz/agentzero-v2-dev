"""Tests for scripts/lint.py. Standard library only.

Run from any directory:
    python -m unittest discover -s <path-to>/packs/anti-slop/scripts -v
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import lint

PACK_DIR = Path(__file__).resolve().parent.parent
FIXTURES = PACK_DIR / "fixtures"
OUTPUTS = FIXTURES / "outputs"


def load_phrase_lists() -> dict[str, list[str]]:
    return lint.load_phrases(PACK_DIR / "phrases.yaml")


class PhraseHitTests(unittest.TestCase):
    def setUp(self) -> None:
        lists = load_phrase_lists()
        self.phrases, self.words = lists["phrases"], lists["words"]

    def test_hit_on_forbidden_phrase(self) -> None:
        hits = lint.phrase_hits("This is a robust framework.", self.phrases, self.words)
        items = {hit["item"] for hit in hits}
        self.assertIn("robust framework", items)

    def test_hit_is_case_insensitive(self) -> None:
        hits = lint.phrase_hits("DELVE INTO the data. Pivotal work.", self.phrases, self.words)
        matched = {hit["matched"].lower() for hit in hits}
        self.assertIn("delve into", matched)
        self.assertIn("pivotal", matched)

    def test_hit_across_line_break(self) -> None:
        hits = lint.phrase_hits("A robust\nframework for teams.", self.phrases, self.words)
        self.assertTrue(any(hit["item"] == "robust framework" for hit in hits))

    def test_curly_apostrophe_matches_straight_in_list(self) -> None:
        hits = lint.phrase_hits("In today’s rapidly evolving field.", self.phrases, self.words)
        self.assertTrue(any(hit["item"] == "in today's rapidly evolving" for hit in hits))

    def test_no_hit_on_plain_text(self) -> None:
        text = "The cache stores 128 entries. Each entry expires after 60 seconds."
        self.assertEqual(lint.phrase_hits(text, self.phrases, self.words), [])

    def test_word_match_is_whole_word(self) -> None:
        # "pivotally" and "delvers" must not match the words "pivotal" and "delve".
        hits = lint.phrase_hits("pivotally placed", self.phrases, self.words)
        self.assertEqual(hits, [])

    def test_lists_are_loaded_from_phrases_yaml(self) -> None:
        self.assertIn("delve into", self.phrases)
        self.assertIn("pivotal", self.words)
        self.assertGreater(len(self.phrases), 5)


class ParagraphAndCommentTests(unittest.TestCase):
    def test_average_paragraph_sentences(self) -> None:
        text = "One. Two. Three.\n\nFour.\n\nFive. Six."
        # paragraphs: 3, 1, 2 sentences -> average 2.0
        self.assertEqual(lint.average_paragraph_sentences(text), 2.0)

    def test_headings_and_fences_are_not_paragraphs(self) -> None:
        text = "# Title\n\nOne sentence.\n\n```\nx = 1. y = 2. z = 3. w = 4. v = 5.\n```\n"
        self.assertEqual(lint.average_paragraph_sentences(text), 1.0)

    def test_comment_ratio_python(self) -> None:
        code = "# note\nx = 1\ny = 2\nz = 3\n"
        self.assertEqual(lint.comment_ratio(code, "python"), round(1 / 3, 3))

    def test_comment_ratio_none_for_other_languages(self) -> None:
        self.assertIsNone(lint.comment_ratio("int x = 1;", "java"))


class CompareTests(unittest.TestCase):
    ORIGINAL = "The pilot ran 20-30 agents and cut cost by 26%. See `pack_version` and Anthropic."

    def test_identical_text_passes(self) -> None:
        report = lint.compare_sets(self.ORIGINAL, self.ORIGINAL)
        self.assertTrue(report["ok"])

    def test_dropped_number_is_caught(self) -> None:
        revised = "The pilot ran 20-30 agents and cut cost. See `pack_version` and Anthropic."
        report = lint.compare_sets(self.ORIGINAL, revised)
        self.assertFalse(report["ok"])
        self.assertIn("26", report["numbers"]["dropped"])

    def test_invented_number_is_caught(self) -> None:
        revised = "The pilot ran 20-30 agents and cut cost by 26% and time by 41%. See `pack_version` and Anthropic."
        report = lint.compare_sets(self.ORIGINAL, revised)
        self.assertFalse(report["ok"])
        self.assertIn("41", report["numbers"]["invented"])

    def test_dropped_identifier_is_caught(self) -> None:
        revised = "The pilot ran 20-30 agents and cut cost by 26%. See Anthropic."
        report = lint.compare_sets(self.ORIGINAL, revised)
        self.assertFalse(report["ok"])
        self.assertIn("pack_version", report["identifiers"]["dropped"])

    def test_dropped_name_is_caught(self) -> None:
        revised = "The pilot ran 20-30 agents and cut cost by 26%. See `pack_version`."
        report = lint.compare_sets(self.ORIGINAL, revised)
        self.assertFalse(report["ok"])
        self.assertIn("Anthropic", report["names"]["dropped"])


class FactFreeRemovalTests(unittest.TestCase):
    """Criterion 2, option C: a name removed only with a fact-free sentence is excused."""

    ORIGINAL = "In today's rapidly evolving AI landscape, teams build agents. Our tool uses Anthropic models."

    def _review(self, *changes: dict) -> dict:
        return {"pack_version": "0.1.0", "revised": "", "changes": list(changes), "kept": [], "flags": []}

    def test_name_removed_with_fact_free_sentence_is_excused(self) -> None:
        review = self._review({"category": "generic_opening",
                               "before": "In today's rapidly evolving AI landscape, teams build agents. ",
                               "after": "", "reason": "generic", "behaviour_change": False})
        revised = "Our tool uses Anthropic models."
        report = lint.compare_sets(self.ORIGINAL, revised, review)
        self.assertTrue(report["ok"], report)
        self.assertIn("AI", report["names"]["excused"])
        self.assertEqual(report["names"]["dropped"], [])

    def test_name_kept_elsewhere_is_still_dropped(self) -> None:
        original = "Generic opening about Anthropic. Our tool uses Anthropic models."
        review = self._review({"category": "generic_opening", "before": "Generic opening about Anthropic. ",
                               "after": "", "reason": "generic", "behaviour_change": False})
        revised = "Our tool uses Anthropic models."
        report = lint.compare_sets(original, revised, review)
        self.assertNotIn("Anthropic", report["names"]["excused"])

    def test_name_removed_with_a_fact_is_still_dropped(self) -> None:
        review = self._review({"category": "vague_claim", "before": "Our tool uses Anthropic models.",
                               "after": "Our tool is good.", "reason": "vague", "behaviour_change": False})
        revised = "Our tool is good."
        report = lint.compare_sets(self.ORIGINAL, revised, review)
        self.assertFalse(report["ok"])
        self.assertIn("Anthropic", report["names"]["dropped"])


class ValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads((PACK_DIR / "schema" / "review-output.json").read_text(encoding="utf-8"))

    def good(self) -> dict:
        return {
            "pack_version": "0.1.0",
            "revised": "The cache stores 128 entries.",
            "changes": [
                {"category": "filler", "before": "serves as", "after": "is", "reason": "Direct verb."}
            ],
            "kept": [],
            "flags": [],
        }

    def test_valid_output_passes(self) -> None:
        self.assertEqual(lint.validate(self.good(), self.schema), [])

    def test_unknown_category_fails(self) -> None:
        bad = self.good()
        bad["changes"][0]["category"] = "vibes"
        self.assertTrue(lint.validate(bad, self.schema))

    def test_missing_reason_fails(self) -> None:
        bad = self.good()
        del bad["changes"][0]["reason"]
        self.assertTrue(lint.validate(bad, self.schema))

    def test_swallowed_error_needs_behaviour_change_true(self) -> None:
        output = self.good()
        output["changes"] = [
            {"category": "swallowed_error", "before": "except: return []", "after": "raise", "reason": "Do not hide errors."}
        ]
        self.assertTrue(lint.validate(output, self.schema))
        output["changes"][0]["behaviour_change"] = True
        self.assertEqual(lint.validate(output, self.schema), [])

    def test_extra_top_level_property_fails(self) -> None:
        bad = self.good()
        bad["score"] = 1
        self.assertTrue(lint.validate(bad, self.schema))

    def test_bad_pack_version_fails(self) -> None:
        bad = self.good()
        bad["pack_version"] = "v1"
        self.assertTrue(lint.validate(bad, self.schema))


class FixtureTests(unittest.TestCase):
    def test_all_ten_fixtures_load(self) -> None:
        paths = sorted(FIXTURES.glob("F*.yaml"), key=lambda p: int(p.stem[1:]))
        self.assertEqual([p.stem for p in paths], [f"F{i}" for i in range(1, 11)])
        for path in paths:
            fixture = lint.load_fixture(path)
            self.assertEqual(fixture["id"], path.stem)
            self.assertTrue(fixture["input"].strip(), path.name)
            self.assertTrue(fixture["expect"], path.name)

    def test_extract_input_writes_utf8_lf(self) -> None:
        fixture = lint.load_fixture(FIXTURES / "F4.yaml")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "F4.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                lint.main(["extract-input", str(FIXTURES / "F4.yaml"), "--out", str(out)])
            data = out.read_bytes()
            self.assertNotIn(b"\r", data)
            self.assertEqual(data.decode("utf-8"), fixture["input"])


class ReadTextTests(unittest.TestCase):
    def test_crlf_is_normalised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "crlf.md"
            path.write_bytes("One.\r\n\r\nTwo.\r\n".encode("utf-8"))
            self.assertEqual(lint.read_text(path), "One.\n\nTwo.\n")

    def test_crlf_file_gives_same_phrase_result(self) -> None:
        lists = load_phrase_lists()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "crlf.md"
            path.write_bytes("A robust\r\nframework.\r\n".encode("utf-8"))
            text = lint.read_text(path)
            hits = lint.phrase_hits(text, lists["phrases"], lists["words"])
            self.assertTrue(any(hit["item"] == "robust framework" for hit in hits))


class ReviewedOutputTests(unittest.TestCase):
    """Runs only on revised outputs that the fixture run wrote to fixtures/outputs/.
    Each file is <ID>.revised.md. Missing output is a failure, not a skip."""

    def test_revised_f1_to_f4_have_zero_phrase_hits(self) -> None:
        lists = load_phrase_lists()
        for fixture_id in ("F1", "F2", "F3", "F4"):
            path = OUTPUTS / f"{fixture_id}.revised.md"
            self.assertTrue(path.exists(), f"missing {path}; run the fixture pass first")
            text = lint.read_text(path)
            hits = lint.phrase_hits(text, lists["phrases"], lists["words"])
            self.assertEqual(hits, [], f"{fixture_id} still has hits: {hits}")



class AcceptanceCriteriaTests(unittest.TestCase):
    """Spec section 8.2. Criterion 2 is checked on revised F1 to F4 and F8 against their
    inputs. Criterion 3 is checked on F10. A failing test here is a real reviewer result,
    not a test defect. See fixtures/RESULTS.md before changing an expected value."""

    def _revised(self, fixture_id: str) -> str:
        path = OUTPUTS / f"{fixture_id}.revised.md"
        self.assertTrue(path.exists(), f"missing {path}; run the fixture pass first")
        return lint.read_text(path)

    def _input(self, fixture_id: str) -> str:
        return lint.read_text(OUTPUTS / f"{fixture_id}.input.txt")

    def test_criterion2_numbers_names_identifiers_match(self) -> None:
        for fixture_id in ("F1", "F2", "F3", "F4", "F8"):
            with self.subTest(fixture=fixture_id):
                review = json.loads(lint.read_text(OUTPUTS / f"{fixture_id}.json"))
                report = lint.compare_sets(self._input(fixture_id), self._revised(fixture_id), review)
                self.assertTrue(report["ok"], f"{fixture_id} compare: {report}")

    def test_criterion3_f10_output_equals_input(self) -> None:
        self.assertEqual(self._revised("F10").rstrip("\n"), self._input("F10").rstrip("\n"))


if __name__ == "__main__":
    unittest.main()
