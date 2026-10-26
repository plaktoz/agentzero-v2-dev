"""Checks that schema/assessment.json is a valid JSON Schema and enforces the pack rules.

Needs the third-party package jsonschema; the test is skipped when it is missing.
Run: python3 -I scripts/test_schema.py
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent

try:
    import jsonschema  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    jsonschema = None


def unit(**over):
    base = {"location": "pricing.py:1-12", "kind": "money", "risky": True, "tests_required": True,
            "cases": ["zero quantity"], "present": False}
    base.update(over)
    return base


def record(**over):
    base = {"mode": "selective", "change_class": "normal", "units": [unit()], "gate": "missing_tests",
            "reasons": ["pricing.py:1-12 is money logic with no test"]}
    base.update(over)
    return base


@unittest.skipIf(jsonschema is None, "jsonschema is not installed")
class AssessmentSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads((PACK / "schema" / "assessment.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(cls.schema)
        cls.validator = jsonschema.Draft202012Validator(cls.schema)

    def ok(self, doc) -> None:
        self.assertEqual([e.message for e in self.validator.iter_errors(doc)], [])

    def bad(self, doc) -> None:
        self.assertTrue(list(self.validator.iter_errors(doc)))

    def test_input_schema_is_valid(self) -> None:
        schema = json.loads((PACK / "schema" / "input.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)

    def test_valid_records(self) -> None:
        self.ok(record())
        self.ok(record(pack_version="0.1.0"))
        self.ok(record(units=[unit(present=True)], gate="ok", reasons=[]))
        self.ok({"mode": "selective", "change_class": "trivial", "units": [], "gate": "ok", "reasons": []})
        self.ok({"mode": "selective", "change_class": "trivial", "units": [], "gate": "ok", "reasons": []})
        self.ok(record(units=[unit(kind="none", risky=False, tests_required=False, cases=[], present=False)],
                       gate="ok", reasons=[]))

    def test_tests_required_needs_a_case(self) -> None:
        self.bad(record(units=[unit(cases=[])]))

    def test_gate_must_follow_units(self) -> None:
        self.bad(record(gate="ok", reasons=[]))  # required and absent, yet ok
        self.bad(record(units=[unit(present=True)]))  # nothing missing, yet missing_tests

    def test_reasons_must_match_gate(self) -> None:
        self.bad(record(reasons=[]))
        self.bad(record(units=[unit(present=True)], gate="ok", reasons=["x"]))

    def test_trivial_has_no_units(self) -> None:
        self.bad(record(change_class="trivial"))

    def test_risky_rules(self) -> None:
        self.bad(record(units=[unit(risky=True, tests_required=False, cases=[])], gate="ok", reasons=[]))
        self.bad(record(units=[unit(kind="none")]))
        self.bad(record(units=[unit(kind="none", risky=True)]))

    def test_unknown_values_rejected(self) -> None:
        self.bad(record(mode="loose"))
        self.bad(record(units=[unit(kind="style")]))
        self.bad(record(extra=1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
