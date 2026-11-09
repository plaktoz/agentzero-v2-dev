# test-adapters

**Moved on 2026-11-09** to its own repository: <https://github.com/plaktoz/test-adapters> (local clone: `~/Developer/test-adapters`).

The requirements (draft v0.4), the roadmap and, later, the source and tests now live there. This folder keeps only this pointer so that links from `umas/`, `libs/` and `packs/` still resolve.

**Status of the dependency.** The repository holds requirements only. There is no code yet, so nothing in UMAS can call it today.

**What UMAS needs from it.** One command that runs a project's tests (pytest, jest) and returns one normalised result, with an exit code that tells a test failure from a tooling fault and from a timeout. UMAS uses the exit codes `0` passed, `1` failed, `2` usage error, `3` error and `4` timeout, and the `--result-file` option. The authority for these is the external requirements, section 5.4. They are not copied here.

**How UMAS uses it.** As an external tool, installed as a package and called by its command line. UMAS code does not import it.

| UMAS caller | Use |
|-------------|-----|
| [merge-queue](../merge-queue/README.md) verify command | `test-adapters run --json --result-file <path>`, wrapped so that exit 3 and 4 halt the queue instead of blaming a candidate. See [verification-spec.md](../../umas/modules/verification/verification-spec.md), O2 |
| [playbook-runner](../../packs/playbook-runner/playbook-runner-spec.md) | Step `verify-run-tests` |
| [test-policy](../../packs/test-policy/test-policy-spec.md) | Supplies `coverage` from the result |
| [metrics-store](../metrics-store/README.md) | `ingest_test_result` reads the JSON result |

Citations written as `[S: test-adapters §N]` in this repository refer to the former in-repo spec (draft v0.1), not to the external requirements, whose section numbers differ. Read it with `git show 2af09bf:libs/test-adapters/README.md`. Where the two disagree, the external requirements win and the citing text is updated.
