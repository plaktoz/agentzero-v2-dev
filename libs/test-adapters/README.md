# test-adapters

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS. Needs the test frameworks it adapts to be installed in the target project.

---

## 1. Purpose

Run a project's tests with pytest, jest, or cargo, and return one normalised result, whichever framework produced it. Callers (CI wrappers, merge queues, agents) deal with one result schema and never parse framework output.

## 2. Scope and Non-Goals

**In scope**
- Framework detection, command construction, execution with timeout, report parsing
- A single `TestResult` schema, including failures and optional coverage
- Running a subset of tests, and re-running failures
- A small adapter interface to add frameworks

**Non-goals**
- Deciding **which** tests must exist or enforcing TDD, "risky logic" patterns, or coverage policy. That is policy; the library returns the numbers, and callers apply thresholds.
- Checking out branches or modifying the repo. The caller sets the working directory.
- Test generation

## 3. Concepts and Data Model

### 3.1 TestRequest

```
{ cwd, framework?, command_override?, select[]?, timeout_seconds,
  parallelism?, coverage: bool, env{}, retry_failed: int }
```

`select` is a list of test file paths or node IDs. `framework` omitted = auto-detect.

### 3.2 TestResult

```json
{ "schema_version": 1, "framework": "pytest", "status": "passed|failed|error|timeout",
  "total": 120, "passed": 118, "failed": 1, "skipped": 1, "errors": 0,
  "duration_ms": 8421,
  "failures": [ { "name": "tests/test_x.py::test_y", "message": "assert 1 == 2",
                  "file": "tests/test_x.py", "line": 42, "flaky": false } ],
  "coverage": { "line_percent": 83.1, "files": [ { "path": "...", "line_percent": 70.0 } ] },
  "raw": { "exit_code": 1, "stdout_path": "...", "report_path": "..." },
  "command": "pytest ..." }
```

`status`:
- `passed`: ran, no failures or errors
- `failed`: ran, at least one test failed
- `error`: could not run (tool missing, collection error, no tests found when `require_tests` is true, unparseable report)
- `timeout`: killed at the limit. Partial counts are included when available

Failure `line` is `null` when the framework gives no line.

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `detect(cwd) -> [Framework]` | Ordered candidates based on project files (section 5.1). |
| `run(request) -> TestResult` | Build command, execute, parse. |
| `parse(framework, report_path_or_text) -> TestResult` | Parse an existing report without running anything. |
| `adapter_info(framework) -> { command_template, report_format, requires[] }` | Introspection, and the preflight check in `doctor`. |
| `doctor(cwd) -> Report` | Verify the framework and its reporter are installed. |

Also `test-adapters run --json` (exit code 0 only when `status == passed`).

### 4.1 Adapter interface (for adding frameworks)

```
detect(cwd) -> bool
build_command(request) -> argv[] + env + report_paths
parse(report_files, exit_code, stdout) -> TestResult
```

### 4.2 CLI output (AXI)

Follows [CLI Conventions (AXI)](../README.md#cli-conventions-axi). `--json` is unchanged and is what [merge-queue](../merge-queue/README.md) calls. This section covers only what is specific here.

**Why it fits.** An agent runs tests after every change and reads the result. A full report from a large suite is mostly passing names the agent does not need.

**Default view of `run`** (illustrative; layout is not a contract):

```
status: failed
summary: 118 passed, 1 failed, 1 skipped of 120 (8.4s)
failures[1 of 1]{name,file,line,message}:
  tests/test_x.py::test_y,tests/test_x.py,42,"assert 1 == 2"
flaky: none
help[2]:
  test-adapters run --select tests/test_x.py::test_y   # rerun only this
  test-adapters run --full                              # untruncated messages
```

| Rule | Applied here |
|------|--------------|
| Minimal fields | A failure shows `name`, `file`, `line`, `message`. `--fields` adds `flaky`; `--full` lifts the message cut |
| Pre-computed aggregate | One `summary` line with the counts and duration, so the agent never adds them up |
| Definitive empty state | A passing run prints `failures: none` and `flaky: none`, never a blank |
| Truncation | Messages cut at 200 characters with `… (N chars total)`. Stack traces are never inlined: `raw.stdout_path` is given and `--full` prints the first lines of it |
| Failure limit | `failures[20 of 134]` when more than 20 fail, with a `help` line to see the rest |
| Errors | `status: error` plus `error:` (for example `no_tests`) and a `help:` line. For these the tool could not run, so the exit code is 1 and the result is still a normal `TestResult` in `--json` |
| No-argument view | `detect` plus `doctor` for the current directory: which framework was found and whether its reporter is installed. It does not run the tests (running is slow and has side effects, so it is not a safe session-start action) |
| Next steps | Rerun just the failures; `doctor` when a reporter is missing |

**Exit codes.** `0` only when `status == passed` (unchanged). `1` for `failed`, `error` and `timeout`; the output says which. `2` for a usage error, such as an unknown flag. No other codes.

**How to use it.**
- **Coding agent in a loop:** run `test-adapters run --select <files>`; read the failures; fix; run again. Only fall back to `--full` when a message is cut mid-explanation.
- **Merge queue:** `test-adapters run --json`; exit 0 means green. Do not use the default view.
- **Session start (application's choice):** run `test-adapters` with no arguments so the agent knows which test command applies.

## 5. Behaviour

### 5.1 Detection

| Framework | Signals |
|-----------|---------|
| pytest | `pytest.ini`, `pyproject.toml` with `[tool.pytest...]`, `tox.ini`/`setup.cfg` pytest section, `conftest.py`, or `tests/` with `test_*.py` |
| jest | `jest.config.*`, `package.json` with a `jest` key or `jest` in scripts/devDependencies |
| cargo | `Cargo.toml` |

If several match, `run` fails with `Ambiguous` unless `framework` is set. A monorepo can pass `cwd` per package.

### 5.2 Report sources

Each adapter reads the **most stable machine-readable output the tool provides without non-standard plugins where possible**.

| Framework | Preferred report | Notes |
|-----------|------------------|-------|
| pytest | `--junitxml=<file>` (built in) | `pytest-json-report` is an optional richer source; the source spec uses it, but it needs a plugin |
| jest | `--json --outputFile=<file>` (built in) | |
| cargo | `cargo nextest` JUnit output if available; else libtest JSON (`--format json`, requires nightly or `-Z unstable-options`) | The report mechanism for cargo needs confirming against the project's toolchain (see open questions). `doctor` reports which is available |

If no machine-readable report can be produced, the adapter falls back to a parse of stdout and sets `result.degraded = true`. The totals are then best-effort.

### 5.3 Execution

- Run as a child process in its own process group, with `cwd` and merged `env`.
- Capture stdout/stderr to a file (cap `max_output_bytes`, default 5 MiB; keep the tail).
- On timeout: SIGTERM the group, wait `kill_grace` (default 5s), then SIGKILL. Result `status = timeout`.
- Parallelism: translated per framework (`pytest -n N` if xdist is present, `jest --maxWorkers=N`, `cargo test -- --test-threads=N`). If the request cannot be honoured (plugin missing) the result carries a warning rather than failing.

### 5.4 Subsets and retries

- `select`: pytest file/node IDs as arguments; jest `--runTestsByPath`; cargo test name filters. Unsupported selectors -> `error` with the reason.
- `retry_failed: N` re-runs only the failures up to N times. A test that fails first and passes later is reported **passed** with `flaky: true` in an additional `flaky` list, so callers can distinguish flakiness from regressions. The final `status` reflects only tests that still fail.

### 5.5 Coverage

When `coverage: true`: pytest via `--cov` + `--cov-report=json`, jest `--coverage` + json-summary, cargo via `cargo llvm-cov` if present. The result carries `coverage.line_percent` and optional per-file figures. Missing coverage tooling -> `status` unaffected, `coverage = null`, warning added. Thresholds (fail under X%) are applied by the caller.

## 6. Configuration

```yaml
framework: auto
timeout_seconds: 600
kill_grace_seconds: 5
max_output_bytes: 5242880
parallelism: auto
require_tests: true            # status=error if zero tests were collected
retry_failed: 0
coverage: false
command_overrides:             # per framework: replace the generated command
  pytest: null
```

## 7. Failure Modes

| Error / status | Cause | Behaviour |
|----------------|-------|-----------|
| `error: tool_missing` | Framework binary absent | `status=error`, install hint, no crash |
| `error: collection` | Import or syntax error prevents tests loading | `status=error` with the first error message |
| `error: no_tests` | Zero tests and `require_tests` | `status=error` |
| `error: unparseable_report` | Report malformed or missing | `status=error`, raw stdout path included; stdout fallback attempted |
| `timeout` | Run exceeded the limit | Process group killed; partial results if the report exists |
| `Ambiguous` | Multiple frameworks and none chosen | Fail before running |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below; severity is the consumer's policy.

| Error / status | Suggested recoverability |
|----------------|--------------------------|
| `timeout` | `ambiguous` |
| `tool_missing`, `no_tests`, `Ambiguous` | `permanent` until configuration changes |
| `collection`, `unparseable_report` | `permanent` until the code or tool is fixed |

Failing tests are results, not errors. A test failure is not an error record unless the consumer chooses to make one.

## 8. Acceptance Criteria

1. For each supported framework, a sample project with 3 pass / 1 fail / 1 skip yields identical `TestResult` counts and one failure with file and line.
2. A project with a collection error yields `status=error`, not `failed`.
3. A hanging test is killed at the timeout, including child processes of the test.
4. A test that fails once then passes with `retry_failed: 1` is listed under `flaky` and does not fail the run.
5. The adapter for a new framework can be added without changing existing code (verified by a toy adapter in the test suite).
6. `parse` on recorded report fixtures gives the same output as `run` on the same project.
7. The default view of a passing run prints `failures: none` and exits 0; of a failing run it lists at most 20 failures with `n of total`, and exits 1.
8. A failure message of 5,000 characters is cut in the default view and complete with `--full`; `--json` always carries the complete message.
9. `status: error` runs (tool missing, no tests) exit 1 and carry a typed `error:` and a `help:` line; an unknown flag exits 2 and names the valid flags.
10. Running with no arguments detects and checks the framework without executing any test.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| Test Runner (Rust) | Replaced by this library (any implementation language) |
| `TestResult { passed, total, failures, duration_ms }` | Subset of `TestResult` here |
| Merge queue verify | Command: `test-adapters run --json`, so exit code 0 means green |
| Test coverage policy (`selective` / `strict`, `coverage_target`) | Applied by UMAS using `result.coverage`; "risky logic" detection belongs to the verification agents (Tier 2) |
| Flaky test history (exception flow 4.11) | UMAS logs `result.flaky` to the event log and consults it on later failures |
| Error statuses | Mapped to records by UMAS. Test failures stay in `TestResult`; only `status=error` becomes a record |

## 10. Source Material and Deviations

Extracted from `TECHNICAL-DESIGN-SPEC-PART3.md` §6.3 (Rust `TestRunner`) and `UMAS-TECH-DESIGN-SPEC.md` §3.4, §4.11.

| Deviation | Why |
|-----------|-----|
| No `checkout_branch` inside the runner | The source runner checks out a branch itself, mutating the repo as a side effect and duplicating the queue's worktree handling |
| Policy removed (TDD, risky patterns, coverage targets) | The summary lists "TDD enforcement" under Test Runner, but that is a policy about how agents work; the library reports facts only |
| JUnit/JSON built-ins preferred over plugin reports | The source relies on `pytest --json-report` (a plugin); fewer installation prerequisites |
| `error` status distinct from `failed` | A collection error is not a test failure and should not be blamed on a change in the same way |

## 11. Open Questions

1. Cargo: standardise on `cargo nextest` (needs install) or accept nightly-only libtest JSON? Check against the toolchain in use before the adapter is built.
2. Should additional frameworks be in the first release (go test, vitest, JUnit/Maven)? The adapter interface makes these cheap, but each needs fixtures.
3. Test selection by changed files (impact analysis) is useful for large repos but is out of scope here; confirm.

---

## 12. Reference Implementation (Source Code)

> Non-normative. Example code illustrating one way to implement this spec. May use consumer-specific names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [libs/README.md](./README.md). The code is in Rust, which is not in the stack. It is legacy and will be ported to Python.

### 12.1 TestRunner (Rust, legacy: language not in stack, port to Python)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §6.3.2

```rust
// Rust implementation for performance (legacy: language not in stack, port to Python)
use std::process::Command;
use std::path::PathBuf;

pub struct TestRunner {
    project_root: PathBuf,
    test_framework: TestFramework,
}

#[derive(Debug, Clone)]
pub enum TestFramework {
    Pytest,
    Jest,
    Cargo,
}

#[derive(Debug)]
pub struct TestResult {
    pub passed: bool,
    pub total: usize,
    pub passed_count: usize,
    pub failed_count: usize,
    pub skipped_count: usize,
    pub duration_ms: u64,
    pub failures: Vec<TestFailure>,
}

#[derive(Debug)]
pub struct TestFailure {
    pub test_name: String,
    pub error_message: String,
    pub file: String,
    pub line: usize,
}

impl TestRunner {
    pub async fn run_all_tests(
        &self,
        branch: &str,
    ) -> Result<TestResult, TestError> {
        // Checkout branch
        self.checkout_branch(branch).await?;
        
        // Run tests based on framework
        match self.test_framework {
            TestFramework::Pytest => self.run_pytest().await,
            TestFramework::Jest => self.run_jest().await,
            TestFramework::Cargo => self.run_cargo_test().await,
        }
    }
    
    async fn run_pytest(&self) -> Result<TestResult, TestError> {
        let output = Command::new("pytest")
            .arg("--json-report")
            .arg("--json-report-file=test-results.json")
            .current_dir(&self.project_root)
            .output()?;
        
        // Parse JSON output
        let result = self.parse_pytest_output(&output.stdout)?;
        
        Ok(result)
    }
    
    pub async fn run_specific_tests(
        &self,
        test_files: Vec<PathBuf>,
    ) -> Result<TestResult, TestError> {
        // Run only specified test files
        let mut total_result = TestResult {
            passed: true,
            total: 0,
            passed_count: 0,
            failed_count: 0,
            skipped_count: 0,
            duration_ms: 0,
            failures: vec![],
        };
        
        for test_file in test_files {
            let result = self.run_test_file(&test_file).await?;
            total_result.merge(result);
        }
        
        Ok(total_result)
    }
}
```

### 12.2 Test runner configuration (YAML)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §6.3.3

```yaml
test_runner_config:
  framework: pytest  # pytest, jest, cargo
  
  execution:
    parallel: true
    max_workers: 4
    timeout_per_test: 60
    
  coverage:
    enabled: true
    target: 95
    fail_under: 80
    
  reporting:
    format: json
    output_file: test-results.json
```
