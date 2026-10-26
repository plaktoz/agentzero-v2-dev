"""Deterministic checks for the anti-slop pack. Python standard library only.

Commands:
  check FILE [--kind K] [--language L] [--config PATH]
      Forbidden-phrase hits (case-insensitive), average paragraph length in
      sentences (non-code kinds), comment-to-code ratio (code kind).
  compare ORIGINAL REVISED
      The set of numbers, names and code identifiers in REVISED must equal
      the set in ORIGINAL. Any dropped or invented item is reported.
  validate OUTPUT.json
      Check a review output against schema/review-output.json. Uses a small
      validator for the JSON Schema keywords that file uses (checked by the
      test), so no third-party package is needed.
  extract-input FIXTURE.yaml --out PATH
      Write a fixture's input text to PATH (UTF-8, LF newlines).

Exit codes: 0 ok, 1 findings, 2 usage or input error.
Paths resolve from this file's location, so the script runs from any directory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACK_DIR / "config.yaml"
SCHEMA_PATH = PACK_DIR / "schema" / "review-output.json"

EXT_LANG = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
}
SLASH_COMMENT_LANGS = {"typescript", "javascript", "java", "go"}
HASH_COMMENT_LANGS = {"python"}


class InputError(Exception):
    """Bad arguments or unreadable or malformed input. Exit code 2."""


# ---------------------------------------------------------------- text helpers

def read_text(path: Path) -> str:
    """Read UTF-8 text and normalise CRLF and CR line endings to LF."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InputError(f"{path} is not UTF-8: {exc}") from exc
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def normalise_for_match(text: str) -> str:
    """Curly apostrophes become straight, and any run of whitespace (including
    line breaks) becomes one space, so phrases match across line breaks."""
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text)


# ---------------------------------------------------------------- config and data

def read_config(path: Path) -> dict:
    """Read top-level scalar keys from config.yaml. Nested keys are skipped."""
    values: dict[str, str] = {}
    for raw in read_text(path).split("\n"):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*([^#\n]*?)[ \t]*(?:#.*)?$", raw)
        if match and match.group(2) != "":
            values[match.group(1)] = match.group(2)
    return values


def load_phrases(path: Path) -> dict[str, list[str]]:
    """Read phrases.yaml. Supports two top-level lists, 'phrases' and 'words',
    each a block of '  - item' lines. Comments are full lines starting with '#'."""
    lists: dict[str, list[str]] = {"phrases": [], "words": []}
    section = None
    for number, raw in enumerate(read_text(path).split("\n"), start=1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace() and line.endswith(":"):
            section = line[:-1].strip()
            if section not in lists:
                raise InputError(f"{path}:{number}: unknown section {section!r}")
            continue
        match = re.match(r"^\s+-\s+(.+?)\s*$", line)
        if not match or section is None:
            raise InputError(f"{path}:{number}: expected '  - item' under a section")
        item = match.group(1)
        if len(item) >= 2 and item[0] == item[-1] and item[0] in "\"'":
            item = item[1:-1]
        lists[section].append(item)
    return lists


def load_thresholds(config: dict) -> tuple[float, float]:
    try:
        max_sentences = float(config.get("max_avg_paragraph_sentences", "4"))
        max_ratio = float(config.get("max_comment_ratio", "0.1"))
    except ValueError as exc:
        raise InputError(f"bad threshold in config: {exc}") from exc
    return max_sentences, max_ratio


# ---------------------------------------------------------------- checks

def phrase_hits(text: str, phrases: list[str], words: list[str]) -> list[dict]:
    haystack = normalise_for_match(text)
    hits = []
    for kind, items in (("phrase", phrases), ("word", words)):
        for item in items:
            pattern = r"(?<![A-Za-z0-9])" + re.escape(normalise_for_match(item)) + r"(?![A-Za-z0-9])"
            for match in re.finditer(pattern, haystack, flags=re.IGNORECASE):
                hits.append({"kind": kind, "item": item, "matched": match.group(0)})
    return hits


def _paragraphs(text: str) -> list[str]:
    """Prose paragraphs: blocks of lines separated by blank lines. Headings,
    table rows and fenced code are not paragraphs."""
    paragraphs: list[str] = []
    buffer: list[str] = []
    in_fence = False

    def flush() -> None:
        if buffer:
            paragraphs.append(" ".join(buffer))
            buffer.clear()

    for raw in text.split("\n"):
        stripped = raw.strip()
        if stripped.startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped or stripped.startswith(("#", "|")):
            flush()
            continue
        buffer.append(stripped)
    flush()
    return paragraphs


def average_paragraph_sentences(text: str) -> float | None:
    counts = []
    for paragraph in _paragraphs(text):
        sentences = [part for part in re.split(r"(?<=[.!?])\s+", paragraph) if part.strip()]
        if sentences:
            counts.append(len(sentences))
    return round(sum(counts) / len(counts), 2) if counts else None


def comment_ratio(text: str, language: str) -> float | None:
    """Comment lines over code lines. Python only. A triple-quoted string counts
    as comment (a docstring approximation). Other languages return None."""
    if language not in HASH_COMMENT_LANGS:
        return None
    comment = code = 0
    closer = None
    for raw in text.split("\n"):
        stripped = raw.strip()
        if closer:
            comment += 1
            if closer in stripped:
                closer = None
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            comment += 1
            continue
        for delimiter in ('"""', "'''"):
            if stripped.startswith(delimiter):
                comment += 1
                if delimiter not in stripped[3:]:
                    closer = delimiter
                break
        else:
            code += 1
    return round(comment / code, 3) if code else None


NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*")
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b")


def numbers_of(text: str) -> set[str]:
    return set(NUMBER_RE.findall(text))


def names_of(text: str) -> set[str]:
    """Capitalised words that are not the first word of a sentence or line."""
    names: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        words = WORD_RE.findall(sentence)
        names.update(word for word in words[1:] if word[0].isupper())
    return names


def identifiers_of(text: str) -> set[str]:
    """Backticked spans, plus words with an underscore, a dot, or a lower-to-upper
    camel transition. Heuristic: it does not parse code."""
    found = {" ".join(span.split()) for span in re.findall(r"`([^`\n]+)`", text)}
    for token in IDENT_RE.findall(text):
        if "_" in token or "." in token or re.search(r"[a-z][A-Z]", token):
            found.add(token)
    return found


FACT_FREE_CATEGORIES = {"generic_opening", "filler"}


def excused_names(original: str, review: dict) -> set[str]:
    """Names that are dropped only with a removed fact-free sentence (criterion 2, option C).

    A change counts when the reviewer labelled it `generic_opening` or `filler` and
    its `after` text is empty. The name is excused only if it appears nowhere else in
    the original. A name in any other removed or kept text stays dropped.
    """
    spans = [
        change["before"]
        for change in review.get("changes", [])
        if change.get("category") in FACT_FREE_CATEGORIES and not change.get("after", "").strip()
    ]
    if not spans:
        return set()
    remainder = original
    for span in spans:
        remainder = remainder.replace(span, " ")
    removed_names = set().union(*(names_of(span) for span in spans))
    return removed_names - names_of(remainder)


def compare_sets(original: str, revised: str, review: dict | None = None) -> dict:
    result: dict[str, dict] = {}
    extractors = {
        "numbers": numbers_of,
        "names": names_of,
        "identifiers": identifiers_of,
    }
    for label, extract in extractors.items():
        before, after = extract(original), extract(revised)
        dropped = before - after
        if label == "names" and review is not None:
            excused = dropped & excused_names(original, review)
            dropped -= excused
            result[label] = {
                "dropped": sorted(dropped),
                "excused": sorted(excused),
                "invented": sorted(after - before),
            }
            continue
        result[label] = {
            "dropped": sorted(dropped),
            "invented": sorted(after - before),
        }
    result["ok"] = all(
        not result[label]["dropped"] and not result[label]["invented"]
        for label in extractors
    )
    return result


def language_for(path: Path | None, override: str | None) -> str | None:
    if override:
        return override.lower()
    if path is not None:
        return EXT_LANG.get(path.suffix.lower())
    return None


# ---------------------------------------------------------------- schema subset

SUPPORTED_KEYWORDS = {
    "$schema", "$id", "title", "description", "type", "properties", "required",
    "additionalProperties", "items", "enum", "const", "pattern", "minLength",
    "if", "then",
}


_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


def validate(instance, schema: dict, path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None and not _TYPES[expected_type](instance):
        return [f"{path}: expected {expected_type}"]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {schema['enum']}")
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required '{key}'")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                errors.extend(validate(value, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property '{key}'")
    if isinstance(instance, list) and "items" in schema:
        for index, item in enumerate(instance):
            errors.extend(validate(item, schema["items"], f"{path}[{index}]"))
    if "if" in schema:
        if not validate(instance, schema["if"], path):
            if "then" in schema:
                errors.extend(validate(instance, schema["then"], path))
    return errors


# ---------------------------------------------------------------- fixtures

def load_fixture(path: Path) -> dict:
    """Read the fixture shape used in this pack:
        id: F1
        input: |
          block scalar, indented
        expect:
          - "double-quoted property"
    Only this shape is supported. It is not general YAML."""
    fixture: dict = {"id": None, "input": None, "expect": []}
    state = "top"
    indent: int | None = None
    input_lines: list[str] = []
    for number, raw in enumerate(read_text(path).split("\n"), start=1):
        if state == "input":
            if not raw.strip():
                input_lines.append("")
                continue
            if raw[0] == " ":
                if indent is None:
                    indent = len(raw) - len(raw.lstrip(" "))
                if len(raw) - len(raw.lstrip(" ")) < indent:
                    raise InputError(f"{path}:{number}: bad indentation in input block")
                input_lines.append(raw[indent:])
                continue
            fixture["input"] = "\n".join(input_lines).rstrip("\n") + "\n"
            state = "top"
        if not raw.strip() or raw.startswith("#"):
            continue
        if state == "top":
            if raw.startswith("id:"):
                fixture["id"] = raw[3:].strip()
            elif raw.startswith("input:"):
                if raw[6:].strip() != "|":
                    raise InputError(f"{path}:{number}: input must be a '|' block")
                state = "input"
            elif raw.startswith("expect:"):
                state = "expect"
            else:
                raise InputError(f"{path}:{number}: unexpected line {raw!r}")
        elif state == "expect":
            match = re.match(r'^\s+-\s+"([^"]*)"\s*$', raw)
            if not match:
                raise InputError(f"{path}:{number}: expect items must be double-quoted '- \"...\"'")
            fixture["expect"].append(match.group(1))
    if state == "input":
        fixture["input"] = "\n".join(input_lines).rstrip("\n") + "\n"
    if not fixture["id"] or fixture["input"] is None or not fixture["expect"]:
        raise InputError(f"{path}: fixture needs id, input and at least one expect item")
    return fixture


# ---------------------------------------------------------------- commands

def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.file)
    text = read_text(path)
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG
    config = read_config(config_path)
    max_sentences, max_ratio = load_thresholds(config)
    phrases_file = Path(config.get("phrases_file", "phrases.yaml"))
    if not phrases_file.is_absolute():
        phrases_file = config_path.parent / phrases_file
    lists = load_phrases(phrases_file)

    hits = phrase_hits(text, lists["phrases"], lists["words"])
    ok = not hits
    report: dict = {
        "file": str(path),
        "kind": args.kind,
        "phrase_hits": hits,
        "limits": {"max_avg_paragraph_sentences": max_sentences, "max_comment_ratio": max_ratio},
    }

    if args.kind == "code":
        language = language_for(path, args.language)
        ratio = comment_ratio(text, language or "")
        report["language"] = language
        report["comment_ratio"] = ratio
        if ratio is None:
            report["note"] = "comment ratio is computed for Python only; not checked"
        elif ratio > max_ratio:
            ok = False
    else:
        average = average_paragraph_sentences(text)
        report["avg_paragraph_sentences"] = average
        if average is not None and average > max_sentences:
            ok = False

    report["ok"] = ok
    _emit(report)
    return 0 if ok else 1


def cmd_compare(args: argparse.Namespace) -> int:
    original = read_text(Path(args.original))
    revised = read_text(Path(args.revised))
    review = json.loads(read_text(Path(args.review))) if args.review else None
    report = compare_sets(original, revised, review)
    _emit(report)
    return 0 if report["ok"] else 1


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        instance = json.loads(read_text(Path(args.output)))
    except json.JSONDecodeError as exc:
        _emit({"ok": False, "errors": [f"not valid JSON: {exc}"]})
        return 1
    schema = json.loads(read_text(SCHEMA_PATH))
    errors = validate(instance, schema)
    _emit({"ok": not errors, "errors": errors})
    return 0 if not errors else 1


def cmd_extract_input(args: argparse.Namespace) -> int:
    fixture = load_fixture(Path(args.fixture))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(fixture["input"])
    _emit({"fixture": fixture["id"], "written": str(out)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="anti-slop deterministic checks")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="phrase, paragraph and comment checks")
    check.add_argument("file")
    check.add_argument("--kind", default="prose", choices=["prose", "prd", "docs", "code"])
    check.add_argument("--language", default=None)
    check.add_argument("--config", default=None)
    check.set_defaults(func=cmd_check)

    compare = sub.add_parser("compare", help="numbers, names and identifiers must match")
    compare.add_argument("original")
    compare.add_argument("revised")
    compare.add_argument("--review", default=None, help="review JSON; lets fact-free removals excuse a dropped name")
    compare.set_defaults(func=cmd_compare)

    validate_cmd = sub.add_parser("validate", help="validate a review output")
    validate_cmd.add_argument("output")
    validate_cmd.set_defaults(func=cmd_validate)

    extract = sub.add_parser("extract-input", help="write a fixture's input text to a file")
    extract.add_argument("fixture")
    extract.add_argument("--out", required=True)
    extract.set_defaults(func=cmd_extract_input)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
