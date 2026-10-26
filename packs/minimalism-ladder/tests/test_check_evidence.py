"""Tests for scripts/check_evidence.py. Stdlib unittest only.

Run from the pack directory:
    python -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent.parent
SCRIPT = PACK_DIR / "scripts" / "check_evidence.py"


def write_text(path, text, newline=None):
    """Write UTF-8 text. newline="\\r\\n" produces CRLF line endings on any OS."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)


def record(rung, evidence, **extra):
    names = {
        1: ("not_needed", "skip"),
        2: ("exists_in_codebase", "reuse"),
        3: ("stdlib_or_platform", "use_builtin"),
        4: ("installed_dependency", "use_dependency"),
        5: ("one_line", "write_one_line"),
        6: ("minimum_code", "write_minimum"),
    }
    rung_name, decision = names[rung]
    body = {
        "pack_version": "0.1.0",
        "rung": rung,
        "rung_name": rung_name,
        "evidence": evidence,
        "decision": decision,
        "loc_estimate": 0,
        "shortcuts": [],
    }
    body.update(extra)
    return body


class CheckEvidenceCliTest(unittest.TestCase):
    """Runs the script as a separate process, the way a CI job would."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        write_text(self.root / "util" / "retry.py", "def retry(fn, attempts=3):\n    return fn()\n")
        write_text(self.root / "auth" / "session.py", "class SessionStore:\n    def load(self):\n        pass\n")
        self.record_path = Path(self._tmp.name) / "record.json"

    def tearDown(self):
        self._tmp.cleanup()

    def run_script(self, body, root=None, raw=None):
        if raw is not None:
            write_text(self.record_path, raw)
        else:
            write_text(self.record_path, json.dumps(body))
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.record_path), str(root or self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_existing_path_exits_zero(self):
        result = self.run_script(record(2, ["util/retry.py"]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok:", result.stdout)

    def test_missing_path_exits_nonzero(self):
        result = self.run_script(record(2, ["util/does_not_exist.py"]))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING", result.stderr)
        self.assertIn("util/does_not_exist.py", result.stderr)

    def test_existing_symbol_exits_zero(self):
        result = self.run_script(record(2, ["util/retry.py:retry"]))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_symbol_exits_nonzero(self):
        result = self.run_script(record(2, ["util/retry.py:backoff"]))
        self.assertEqual(result.returncode, 1)
        self.assertIn("backoff", result.stderr)

    def test_dotted_symbol_checks_each_part(self):
        self.assertEqual(self.run_script(record(3, ["auth/session.py:SessionStore.load"])).returncode, 0)
        self.assertEqual(self.run_script(record(3, ["auth/session.py:SessionStore.save"])).returncode, 1)

    def test_one_bad_entry_among_good_ones_fails(self):
        result = self.run_script(record(2, ["util/retry.py", "util/gone.py"]))
        self.assertEqual(result.returncode, 1)
        self.assertIn("util/gone.py", result.stderr)

    def test_empty_evidence_fails_for_evidence_rung(self):
        result = self.run_script(record(4, []))
        self.assertEqual(result.returncode, 1)

    def test_rung_without_evidence_requirement_passes_when_empty(self):
        result = self.run_script(record(5, []))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_absolute_path_is_rejected(self):
        absolute = str((self.root / "util" / "retry.py").resolve())
        result = self.run_script(record(2, [absolute]))
        self.assertEqual(result.returncode, 1)

    def test_backslash_separators_are_read_as_path_separators(self):
        result = self.run_script(record(2, ["util\\retry.py:retry"]))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_path_escaping_root_is_rejected(self):
        result = self.run_script(record(2, ["../record.json"]))
        self.assertEqual(result.returncode, 1)

    def test_crlf_record_and_crlf_source_are_read(self):
        write_text(self.root / "crlf.py", "def make_thing():\r\n    return 1\r\n", newline="")
        raw = json.dumps(record(2, ["crlf.py:make_thing"]), indent=2).replace("\n", "\r\n")
        result = self.run_script(None, raw=raw)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unreadable_record_is_input_error(self):
        result = self.run_script(None, raw="{not json")
        self.assertEqual(result.returncode, 2)

    def test_bad_rung_is_input_error(self):
        body = record(2, ["util/retry.py"])
        body["rung"] = 9
        result = self.run_script(body)
        self.assertEqual(result.returncode, 2)

    def test_missing_repo_root_is_input_error(self):
        result = self.run_script(record(2, ["util/retry.py"]), root=self.root / "nope")
        self.assertEqual(result.returncode, 2)

    def test_non_ascii_evidence_does_not_crash_a_narrow_console(self):
        # PYTHONIOENCODING=ascii stands in for a console that cannot print the text.
        env = dict(os.environ, PYTHONIOENCODING="ascii")
        write_text(self.record_path, json.dumps(record(2, ["util/café.py"])))
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.record_path), str(self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("MISSING", result.stderr)

    def test_wrong_arg_count_is_input_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.record_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
