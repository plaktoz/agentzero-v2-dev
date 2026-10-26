"""Tests for scripts/prefilter.py. Standard library only.

Run from any directory:

    python3 -I scripts/test_prefilter.py
    python3 -I -m unittest scripts/test_prefilter.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PACK = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import prefilter  # noqa: E402
import yaml_subset  # noqa: E402

PREFILTER = SCRIPTS / "prefilter.py"
FIXTURES = PACK / "fixtures"
CONFIG = PACK / "config.yaml"


def fixture_diff(name: str) -> str:
    doc = yaml_subset.load_path(FIXTURES / f"{name}.yaml")
    return doc["input"]["diff"]


def run_cli(args: list[str], stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(PREFILTER), *args],
        input=stdin,
        capture_output=True,
        check=False,
    )


SETTINGS = prefilter.load_settings(CONFIG)


class FixtureVerdicts(unittest.TestCase):
    def test_trivial_fixtures(self) -> None:
        for name in ("F1", "F2", "F3"):
            with self.subTest(fixture=name):
                self.assertEqual(prefilter.classify(fixture_diff(name), SETTINGS).verdict, "trivial")

    def test_needs_model_fixtures(self) -> None:
        for name in ("F4", "F5", "F10"):
            with self.subTest(fixture=name):
                self.assertEqual(prefilter.classify(fixture_diff(name), SETTINGS).verdict, "needs_model")

    def test_cli_prints_verdict_only(self) -> None:
        for name, expected in (("F1", "trivial"), ("F2", "trivial"), ("F3", "trivial"),
                               ("F4", "needs_model"), ("F5", "needs_model"), ("F10", "needs_model")):
            with self.subTest(fixture=name):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / f"{name}.diff"
                    path.write_bytes(fixture_diff(name).encode("utf-8"))
                    done = run_cli([str(path)])
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(done.stdout, (expected + "\n").encode("ascii"))


class Determinism(unittest.TestCase):
    def test_same_input_same_output(self) -> None:
        for name in ("F1", "F4", "F5", "F10"):
            with self.subTest(fixture=name):
                diff = fixture_diff(name)
                first = prefilter.classify(diff, SETTINGS)
                second = prefilter.classify(diff, SETTINGS)
                self.assertEqual(first, second)

    def test_cli_repeat_identical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "F4.diff"
            path.write_bytes(fixture_diff("F4").encode("utf-8"))
            runs = [run_cli([str(path), "--candidates"]) for _ in range(2)]
        self.assertEqual((runs[0].stdout, runs[0].stderr), (runs[1].stdout, runs[1].stderr))
        self.assertEqual(runs[0].stdout, b"needs_model\n")


class Trivial(unittest.TestCase):
    def test_docs_only(self) -> None:
        diff = "diff --git a/notes.md b/notes.md\n--- a/notes.md\n+++ b/notes.md\n@@ -1 +1 @@\n-old\n+new\n"
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "trivial")

    def test_lockfile_and_config_only(self) -> None:
        diff = (
            "diff --git a/poetry.lock b/poetry.lock\n--- a/poetry.lock\n+++ b/poetry.lock\n"
            "@@ -1 +1 @@\n-x = 1\n+x = 2\n"
            "diff --git a/app.toml b/app.toml\n--- a/app.toml\n+++ b/app.toml\n"
            "@@ -1 +1 @@\n-port = 1\n+port = 2\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "trivial")

    def test_whitespace_only_change(self) -> None:
        # Spacing next to a comma or bracket is not significant.
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,2 @@\n"
            "-def f(a,b):\n-    return g(a,b)\n"
            "+def f(a, b):\n+    return g(a, b)\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "trivial")

    def test_operator_spacing_is_not_whitespace_only(self) -> None:
        # "a - -b" and "a--b" are different code (two negations versus a decrement).
        diff = "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-x = a - -b\n+x = a--b\n"
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_spacing_around_equals_is_not_whitespace_only(self) -> None:
        diff = "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-x = 1\n+x=1\n"
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_comment_only_change(self) -> None:
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,2 @@\n"
            "-# old note\n-x = 1\n+# new note\n+x = 1\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "trivial")

    def test_empty_diff_is_trivial(self) -> None:
        self.assertEqual(prefilter.classify("", SETTINGS).verdict, "trivial")

    def test_rename_detection_can_be_turned_off(self) -> None:
        settings = prefilter.Settings(
            exempt=SETTINGS.exempt,
            trivial_extensions=SETTINGS.trivial_extensions,
            rename_detection=False,
            reserved=SETTINGS.reserved,
            languages=SETTINGS.languages,
            rename_min_occurrences=SETTINGS.rename_min_occurrences,
        )
        self.assertEqual(prefilter.classify(fixture_diff("F1"), settings).verdict, "needs_model")


class NeedsModel(unittest.TestCase):
    def test_rename_that_changes_behaviour_is_not_trivial(self) -> None:
        # "if" to "while" swaps one keyword for another: never a plain rename.
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,4 +1,4 @@\n"
            "-    if ready:\n-        pass\n"
            "+    while ready:\n+        pass\n"
            "-    if ready:\n-        pass\n"
            "+    while ready:\n+        pass\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_partial_rename_is_not_trivial(self) -> None:
        # "qty" is renamed on one line but still used unchanged on another.
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,3 +1,3 @@\n"
            "-a = qty\n+a = total\n"
            "-b = qty + 1\n+b = qty + 1\n"
            "     print(qty)\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_rename_merging_two_names_is_not_trivial(self) -> None:
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,2 @@\n"
            "-x = apple\n+x = pear\n"
            "-y = banana\n+y = pear\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_new_name_already_in_use_is_not_trivial(self) -> None:
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,3 +1,3 @@\n"
            "-value = 1\n+total = 1\n"
            "     total = 0\n"
            "     print(total)\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_single_swapped_name_is_not_trivial(self) -> None:
        # One use of foo becomes bar. bar may be a different variable, so a model must look.
        diff = "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-x = foo\n+x = bar\n"
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_logic_change_is_not_trivial(self) -> None:
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,2 @@\n"
            "-    if a > 1:\n+    if a > 2:\n"
            "         return a\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_unparseable_input_needs_model(self) -> None:
        self.assertEqual(prefilter.classify("this is not a diff\n", SETTINGS).verdict, "needs_model")
        broken = "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,5 +1,5 @@\n-x\n+y\n"
        self.assertEqual(prefilter.classify(broken, SETTINGS).verdict, "needs_model")

    def test_binary_change_to_code_needs_model(self) -> None:
        diff = "diff --git a/logo.bin b/logo.bin\nBinary files a/logo.bin and b/logo.bin differ\n"
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")


class Candidates(unittest.TestCase):
    def test_hit_is_listed_with_file_line_and_kind(self) -> None:
        result = prefilter.classify(fixture_diff("F4"), SETTINGS)
        self.assertEqual(result.verdict, "needs_model")
        self.assertIn(("pricing.py", 4, "money"), result.candidates)
        self.assertIn(("pricing.py", 6, "branching"), result.candidates)

    def test_no_hit_gives_no_candidates(self) -> None:
        result = prefilter.classify(fixture_diff("F7"), SETTINGS)  # getter and setter
        self.assertEqual(result.verdict, "needs_model")
        self.assertEqual(result.candidates, [])

    def test_no_hit_on_flagged_word_in_comment(self) -> None:
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,3 @@\n"
            " x = 1\n"
            "+# if the price is high, check the discount\n"
            "+y = 2\n"
        )
        result = prefilter.classify(diff, SETTINGS)
        self.assertNotIn("branching", {kind for _, _, kind in result.candidates})
        self.assertNotIn("money", {kind for _, _, kind in result.candidates})

    def test_auth_unit_flagged_as_security(self) -> None:
        result = prefilter.classify(fixture_diff("F10"), SETTINGS)
        self.assertIn("security", {kind for path, _, kind in result.candidates if path == "documents.py"})


class RenameAndNumbers(unittest.TestCase):
    def test_number_change_is_not_rename(self) -> None:
        diff = "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "needs_model")

    def test_identifier_substitution_is_recognised(self) -> None:
        diff = (
            "diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,2 @@\n"
            "-def amount_of(x):\n+def total_of(x):\n"
            "-    return amount_of(x) + 1\n+    return total_of(x) + 1\n"
        )
        self.assertEqual(prefilter.classify(diff, SETTINGS).verdict, "trivial")


class LineEndings(unittest.TestCase):
    def test_crlf_diff_gives_same_verdict(self) -> None:
        for name in ("F1", "F2", "F4"):
            with self.subTest(fixture=name):
                lf = fixture_diff(name)
                crlf = lf.replace("\n", "\r\n")
                self.assertEqual(
                    prefilter.classify(crlf, SETTINGS).verdict,
                    prefilter.classify(lf, SETTINGS).verdict,
                )

    def test_cli_reads_crlf_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f1.diff"
            path.write_bytes(fixture_diff("F1").replace("\n", "\r\n").encode("utf-8"))
            done = run_cli([str(path)])
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout, b"trivial\n")


class CommandLine(unittest.TestCase):
    def test_reads_standard_input(self) -> None:
        diff = fixture_diff("F2").encode("utf-8")
        done = run_cli(["-"], stdin=diff)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, b"trivial\n")

    def test_missing_file_is_usage_error(self) -> None:
        done = run_cli([str(FIXTURES / "does-not-exist.diff")])
        self.assertEqual(done.returncode, 2)
        self.assertEqual(done.stdout, b"")
        self.assertIn(b"prefilter:", done.stderr)

    def test_bad_config_is_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "config.yaml"
            bad.write_text("- not\n- a mapping\n", encoding="utf-8", newline="\n")
            diff_path = Path(tmp) / "f.diff"
            diff_path.write_bytes(fixture_diff("F1").encode("utf-8"))
            done = run_cli(["--config", str(bad), str(diff_path)])
            self.assertEqual(done.returncode, 2)
            self.assertEqual(done.stdout, b"")


class ReaderSubset(unittest.TestCase):
    def test_fixture_files_parse_with_expected_shape(self) -> None:
        for number in range(1, 11):
            with self.subTest(fixture=f"F{number}"):
                doc = yaml_subset.load_path(FIXTURES / f"F{number}.yaml")
                self.assertEqual(doc["id"], f"F{number}")
                self.assertIsInstance(doc["input"]["diff"], str)
                self.assertTrue(doc["expect"])

    def test_scalars_and_flow_lists(self) -> None:
        doc = yaml_subset.load(
            'a: 1\nb: 2.5\nc: true\nd: null\ne: "x\\ty"\nf: \'it\'\'s\'\ng: ["a, b", c]  # note\n'
        )
        self.assertEqual(doc, {"a": 1, "b": 2.5, "c": True, "d": None, "e": "x\ty", "f": "it's",
                               "g": ["a, b", "c"]})

    def test_literal_block_keeps_final_newline(self) -> None:
        doc = yaml_subset.load("diff: |\n  one\n  two\nnext: 3\n")
        self.assertEqual(doc, {"diff": "one\ntwo\n", "next": 3})

    def test_rejects_duplicate_keys(self) -> None:
        with self.assertRaises(ValueError):
            yaml_subset.load("a: 1\na: 2\n")

    def test_matches_pyyaml_when_available(self) -> None:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError:
            self.skipTest("PyYAML is not installed; the subset is checked by the other tests")
        for path in [CONFIG, PACK / "risky-patterns.yaml", *sorted(FIXTURES.glob("*.yaml"))]:
            with self.subTest(file=path.name):
                self.assertEqual(
                    yaml_subset.load_path(path),
                    yaml.safe_load(path.read_text(encoding="utf-8")),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
