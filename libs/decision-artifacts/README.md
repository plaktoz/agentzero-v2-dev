# decision-artifacts

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS, any database, or any LLM. Plain files in a git repository.

---

## 1. Purpose

Keep a repository's decisions durable and findable: product narratives (PRFAQ), architecture decisions (ADR), specifications, a project glossary, and a ledger of deliberate shortcuts found in code. The library creates, updates, links, lints, and indexes these files. It never writes their content; the author (human or agent) supplies that.

## 2. Scope and Non-Goals

**In scope**
- Create and update four artifact kinds as Markdown with YAML front matter
- Safe numbering and linking (ADR supersession)
- Glossary upsert with conflict detection
- Scanning source files for structured `SHORTCUT` comments and producing a debt ledger
- A `check` mode usable in CI or a pre-commit hook

**Non-goals**
- Generating or judging content
- A database. The files are the source of truth; any index is rebuilt by scanning.
- Rendering sites or PDFs

## 3. Concepts and Data Model

### 3.1 Artifact kinds and default locations

| Kind | Default path | Notes |
|------|--------------|-------|
| PRFAQ | `docs/product/<slug>.prfaq.md` | Press release plus FAQ |
| ADR | `docs/decisions/ADR-<NNNN>-<slug>.md` | Numbered, immutable once accepted (except status and links) |
| Spec | `docs/specs/<slug>.spec.md` | |
| Glossary | `GLOSSARY.md` (repo root) | One file; one entry per term |
| Debt ledger | `docs/debt.md` (generated) | Output of the shortcut scan |

All paths are configuration. The two source specs disagree about locations (`docs/...` in the design spec; `artifacts_dir/prfaq`, `artifacts_dir/adr` in the code), so the design spec's layout is the default.

### 3.2 Front matter

```yaml
---
schema_version: 1
kind: adr
id: ADR-0007
title: Use bcrypt for password hashing
status: accepted          # adr: proposed|accepted|superseded|deprecated ; others: draft|final|retired
author: alice
created: 2026-10-19
updated: 2026-10-19
supersedes: [ADR-0003]
superseded_by: []
links: [docs/specs/login.spec.md]
---
```

### 3.3 Section templates

Templates are plain Markdown files, overridable per project.

| Kind | Required sections |
|------|-------------------|
| PRFAQ | Press release, FAQ (question / answer pairs) |
| ADR | Context, Decision, Consequences, Alternatives considered |
| Spec | Problem, Requirements, Out of scope, Acceptance criteria |

`check` verifies that required sections are present and non-empty, so no empty headings pass.

### 3.4 Glossary entry

```
## <Term>
<Definition, one or two sentences>
*Context:* <optional>   *Added by:* <author>  *Date:* <date>
```

Entries are kept sorted alphabetically. The key is the lower-cased, trimmed term.

### 3.5 Shortcut comment

A comment, in any language's comment syntax, with this form:

```
SHORTCUT: <what was deferred> — <when to fix>
```

The separator accepts em dash, ` -- `, or ` - `. Both parts are mandatory. Example: `// SHORTCUT: sync call to avoid queue setup — revisit before 100 users`. This is the only comment form the engineering conventions allow that does not explain *why* code exists, so the scan is how those comments are kept honest.

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `create(kind, title, sections{}, author, opts) -> Artifact` | Writes a new file from the template with the provided sections. ADR numbers allocated per 5.1. Fails `Exists` for duplicate slugs. |
| `update(id_or_path, patch) -> Artifact` | Update sections or front matter. ADRs: only `status`, `links`, `superseded_by`, and appended sections are allowed after acceptance. |
| `supersede(old_adr, new_adr)` | Sets `superseded_by` on the old, `supersedes` on the new, and old status to `superseded`. Atomic across both files. |
| `get(id_or_path)` / `list(filter)` | Read and index by scanning front matter. |
| `glossary_upsert(term, definition, context?, author, replace=false) -> Result` | Section 5.2. |
| `glossary_lookup(term)` | |
| `scan_shortcuts(paths?) -> [Shortcut]` | Section 5.3. |
| `write_debt_ledger(shortcuts) -> path` | Regenerate the ledger file. |
| `check(opts) -> Report` | Lint (section 5.4); non-zero exit on errors. |

Also `decision-artifacts <op> --json`.

## 5. Behaviour

### 5.1 ADR numbering

The next number is `max(existing) + 1`, found by scanning `ADR-*.md`. To be safe with concurrent creators the library claims the number by creating the file with `O_EXCL`; on collision it increments and retries. Numbers are never reused, including for deleted or rejected ADRs (the file stays as `deprecated`).

### 5.2 Glossary upsert

| Situation | Result |
|-----------|--------|
| Term new | Added in sorted position; `created` |
| Term exists, same definition | `unchanged` |
| Term exists, different definition, `replace=false` | **`Conflict`**: returns both definitions and changes nothing. A silent overwrite of a shared definition is the failure this prevents |
| Term exists, different definition, `replace=true` | Updated; previous text preserved in git history and noted in the `updated` field |

Lookups ignore case and surrounding whitespace. Aliases may be declared (`Also: ...`) and resolve to the entry.

### 5.3 Shortcut scan

- Walk the repo honouring `.gitignore`; skip binary files.
- Recognise comment leaders by file extension (configurable table: `//`, `#`, `--`, `/* */`, `<!-- -->`, ...).
- A match yields `{ path, line, what, fix_when, language }`. Optionally enrich with `first_seen` and `age_days` from `git blame` (`blame: true`).
- A `SHORTCUT:` that lacks either part is reported as **malformed**, with a precise location.
- The ledger file (`docs/debt.md`) is regenerated, sorted by age then path, and marked generated. Never hand-edited.

### 5.4 `check`

| Rule | Severity |
|------|----------|
| Front matter missing or invalid | error |
| Required section missing or empty | error |
| ADR number gap or duplicate | error |
| `supersedes`/`superseded_by` not reciprocal | error |
| Broken `links` | error |
| Malformed `SHORTCUT` comment | error |
| Debt ledger out of date vs source | error (fix with `write_debt_ledger`) |
| Shortcut older than `warn_after_days` | warning |
| Glossary: term used in another artifact title but undefined | warning (opt-in) |

Intended uses: a CI step or a pre-commit hook. The library does not install hooks itself.

### 5.5 Writes

All writes are atomic (write temp, rename). The library never creates a git commit, since commit policy belongs to the caller (or to [hook-store](../hook-store/README.md)).

## 6. Configuration

```yaml
paths:
  prfaq: "docs/product/{slug}.prfaq.md"
  adr: "docs/decisions/ADR-{number:04d}-{slug}.md"
  spec: "docs/specs/{slug}.spec.md"
  glossary: "GLOSSARY.md"
  debt_ledger: "docs/debt.md"
templates_dir: null
shortcut:
  marker: "SHORTCUT:"
  warn_after_days: 90
  blame: false
  comment_leaders: { ".py": ["#"], ".ts": ["//", "/*"], ".rs": ["//"], ".md": ["<!--"] }
slug: { max_length: 60 }
```

## 7. Failure Modes

| Error | Behaviour |
|-------|-----------|
| `Exists` | Duplicate slug: fail, nothing written |
| `Conflict` | Glossary definition clash: nothing written, both texts returned |
| `Immutable` | Edit to a protected ADR section: rejected |
| `MissingSection` | `create` without required sections: rejected, lists the missing ones |
| `NotARepo` | Scans need a repository root for `.gitignore` handling; fall back to walking from the given path with a warning |
| `Malformed` | Reported by `check`, never auto-fixed |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below; severity is the consumer's policy.

| Error | Suggested recoverability |
|-------|--------------------------|
| `Exists`, `Conflict`, `Immutable`, `MissingSection`, `Malformed` | `permanent` until the input changes |
| `NotARepo` | `permanent` (the library continues with a warning) |

## 8. Acceptance Criteria

1. Ten concurrent `create(adr, ...)` calls yield ten files with ten distinct, consecutive numbers.
2. Superseding ADR-3 with ADR-7 leaves both files consistent even if the process is killed between the two writes (recoverable by `check`, which reports the non-reciprocal link).
3. A glossary upsert with a different definition is refused unless `replace=true`.
4. `scan_shortcuts` finds markers in each configured language, and reports a marker lacking "when to fix" as malformed.
5. Regenerating the ledger twice with no source change produces a byte-identical file.
6. `check` returns a non-zero exit on each rule marked error and zero on a clean repo.

## 9. How UMAS Uses It

| UMAS concept | Mapping |
|--------------|---------|
| `ArtifactService` (Python) create PRFAQ/ADR, `update_glossary` | Replaced by this library |
| Product Manager and Architect agents | Supply content; call `create`. Their prompt packs (Tier 2) decide *what* to write, and the library decides *where* and *how it is numbered* |
| Shortcut comments tracked in a debt ledger | `scan_shortcuts` + `write_debt_ledger`; run in the merge queue's verify step as `decision-artifacts check` |
| Decision artifacts as durable context for agents | Agents `get`/`list` ADRs and the glossary when starting a task |
| Minimalism ladder rung: "tests/comments" policy | Enforced by `check`, which rejects malformed shortcuts |
| Typed errors | Mapped to records by UMAS. All are input errors for the calling agent, so `render(agent)` is the natural view. See [error-classifier](../error-classifier/README.md) section 9 |

## 10. Source Material and Deviations

Extracted from `TECHNICAL-DESIGN-SPEC.md` §3.3 and `TECHNICAL-DESIGN-SPEC-PART2.md` §3.3 (Python `ArtifactService`), `UMAS-TECH-DESIGN-SPEC.md` §3.1 (artifact locations) and §3.3 (shortcut comments).

| Deviation | Why |
|-----------|-----|
| Files only, no `artifacts` / `glossary_terms` tables | The artifacts are already files in the repo; a table duplicates them and drifts |
| Author supplies content, not the library | The source `create_prfaq` takes pre-written text; this makes the boundary explicit |
| Glossary conflict detection | The source `update_glossary` has no stated behaviour for an existing term |
| Locations follow the design spec | The code uses `artifacts_dir/prfaq` and `artifacts_dir/adr`; the design spec uses `docs/product`, `docs/decisions`, `docs/specs` |
| Shortcut scan added | The source says shortcuts "must be tracked" but defines no mechanism |
| ADR number allocation hardened | Source `_get_next_adr_number` is a scan-then-write, which races |

## 11. Open Questions

1. ADR filename format: the design spec says `ADR-<NNN>-<title>.md`, the code writes `<NNNN>-<slug>.md`. This spec uses `ADR-<NNNN>-<slug>.md`. Confirm.
2. Should the library ship ready-made agent-skill wrappers (Claude Code skills) so the artifacts can be created interactively, or is that the content pack's (Tier 2) job?
3. Should shortcut entries be allowed to carry an owner or ticket reference (`SHORTCUT[#123]:`)?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Code moved verbatim from the original UMAS technical design. It illustrates one way to implement this spec and uses UMAS names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [libs/README.md](./README.md).

### 12.1 ArtifactService (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART2.md` §3.3.2

```python
    async def create_prfaq(
        self,
        title: str,
        press_release: str,
        faq: List[tuple[str, str]],
        author: str,
    ) -> Artifact:
        """Create a PRFAQ (Press Release + FAQ) document."""
        content = self._format_prfaq(title, press_release, faq)
        file_path = self.artifacts_dir / "prfaq" / f"{self._slugify(title)}.md"
        
        artifact = Artifact(
            id=str(uuid.uuid4()),
            type=ArtifactType.PRFAQ,
            title=title,
            content=content,
            author=author,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            file_path=file_path,
            metadata={"status": "draft"},
        )
        
        await self._write_artifact(artifact)
        await self._save_to_db(artifact)
        return artifact
    
    async def create_adr(
        self,
        title: str,
        context: str,
        decision: str,
        consequences: str,
        alternatives: List[str],
        author: str,
    ) -> Artifact:
        """Create an Architecture Decision Record."""
        adr_number = await self._get_next_adr_number()
        content = self._format_adr(
            adr_number, title, context, decision, consequences, alternatives
        )
        
        file_path = self.artifacts_dir / "adr" / f"{adr_number:04d}-{self._slugify(title)}.md"
        
        artifact = Artifact(
            id=str(uuid.uuid4()),
            type=ArtifactType.ADR,
            title=title,
            content=content,
            author=author,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            file_path=file_path,
            metadata={"number": adr_number, "status": "accepted"},
        )
        
        await self._write_artifact(artifact)
        await self._save_to_db(artifact)
        return artifact
    
    async def update_glossary(
        self,
        term: str,
        definition: str,
        context: Optional[str],
        author: str,
    ) -> None:
        """Add or update a term in GLOSSARY.md."""
        glossary = await self._read_glossary()
        
        glossary[term] = {
            "definition": definition,
            "context": context,
            "author": author,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        await self._write_glossary(glossary)
    
    async def track_shortcut(
        self,
        file_path: Path,
        line_number: int,
        description: str,
        reason: str,
        author: str,
    ) -> Artifact:
        """Track a shortcut comment for technical debt."""
        content = self._format_shortcut(file_path, line_number, description, reason)
        
        artifact = Artifact(
            id=str(uuid.uuid4()),
            type=ArtifactType.SHORTCUT,
            title=f"Shortcut: {file_path}:{line_number}",
            content=content,
            author=author,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            file_path=self.artifacts_dir / "shortcuts" / f"{uuid.uuid4()}.md",
            metadata={
                "file": str(file_path),
                "line": line_number,
                "status": "open",
                "priority": "medium",
            },
        )
        
        await self._write_artifact(artifact)
        await self._save_to_db(artifact)
        return artifact
    
    def _format_prfaq(
        self,
        title: str,
        press_release: str,
        faq: List[tuple[str, str]],
    ) -> str:
        """Format PRFAQ document."""
        content = f"# {title}\n\n"
        content += f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
        content += "## Press Release\n\n"
        content += f"{press_release}\n\n"
        content += "## Frequently Asked Questions\n\n"
        
        for question, answer in faq:
            content += f"### {question}\n\n"
            content += f"{answer}\n\n"
        
        return content
    
    def _format_adr(
        self,
        number: int,
        title: str,
        context: str,
        decision: str,
        consequences: str,
        alternatives: List[str],
    ) -> str:
        """Format ADR document."""
        content = f"# ADR-{number:04d}: {title}\n\n"
        content += f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
        content += "## Status\n\nAccepted\n\n"
        content += f"## Context\n\n{context}\n\n"
        content += f"## Decision\n\n{decision}\n\n"
        content += f"## Consequences\n\n{consequences}\n\n"
        
        if alternatives:
            content += "## Alternatives Considered\n\n"
            for i, alt in enumerate(alternatives, 1):
                content += f"{i}. {alt}\n"
            content += "\n"
        
        return content
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
```

### 12.2 Database schema (SQL)

Source: `TECHNICAL-DESIGN-SPEC-PART2.md` §3.3.3

> **Note:** `libs/decision-artifacts.md` §2 explicitly removes the database requirement — artifacts are files, not rows. This schema is retained here as a historical reference only. It represents the original design before the file-first redesign.

```sql
-- Artifacts table
CREATE TABLE artifacts (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    file_path TEXT NOT NULL,
    metadata JSONB NOT NULL,
    
    INDEX idx_type (type),
    INDEX idx_author (author),
    INDEX idx_created_at (created_at),
    INDEX idx_metadata_gin (metadata) USING GIN
);

-- Glossary terms table
CREATE TABLE glossary_terms (
    id UUID PRIMARY KEY,
    term VARCHAR(255) NOT NULL UNIQUE,
    definition TEXT NOT NULL,
    context TEXT,
    author VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    INDEX idx_term (term)
);
```
