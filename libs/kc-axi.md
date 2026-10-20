# kc-axi

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](README.md)
> **Independence:** no dependency on UMAS, on any AI model, or on any other library. Talks to a Keycloak server and, for `up`/`down`, to a Docker or Podman CLI. No database of its own.

---

## 1. Purpose

Two jobs, one binary:

1. **Run** a local Keycloak server in a Docker or Podman container, repeatably, on Linux or Windows.
2. **Administer** it (realms, clients, users) through a command-line interface a coding agent can call without wasting tokens, hanging on a prompt, or leaking a secret.

The output style follows the AXI principles named in the source issue: token-lean output, few fields, truncation with a count, definitive empty states, structured exit codes, and a next-step hint. The AXI repository itself has not been read for this draft, so check the principles against it before treating them as the standard.

## 2. Scope and Non-Goals

**In scope**
- `up`, `down`, `status` for one Keycloak container, with Docker or Podman
- List, get, create and disable for realms, clients and users, through Keycloak's admin REST API
- Creating a realm from a caller-supplied file
- An agent-friendly output format and fixed exit codes
- Refusing writes unless confirmed, and never printing a secret
- An optional audit file of writes
- One static binary for Linux and Windows

**Non-goals**
- Authorisation. Keycloak answers "who is this". What that person may do is the consuming application's business.
- Production deployment of Keycloak (clustering, external database, TLS, backups). `up` starts a development instance only.
- Managing roles, groups, identity brokering, or themes. They can be added later without changing the contract.
- Replacing Keycloak's own admin console.
- Supporting identity servers other than Keycloak. The command set is small enough (list, get, create, disable on three kinds of object) that another OIDC server could be added as a second adapter behind the same commands. None is planned.

## 3. Concepts and Data Model

### 3.1 Connection

```
{ base_url, admin_realm, admin_user, admin_password | admin_password_file,
  runtime: "auto"|"docker"|"podman", container_name, image, port, volume? }
```

Credentials come from the environment or a file, never from an argument (section 5.4).

### 3.2 Resource views

Each list item shows a minimal view by default, and a wider fixed set with `--full`. Neither view contains a secret.

| Kind | Default fields | `--full` adds |
|------|----------------|---------------|
| realm | `id`, `enabled` | `displayName` |
| client | `id`, `clientId`, `enabled` | `protocol`, `publicClient` |
| user | `id`, `username`, `enabled` | `email`, `emailVerified` |

### 3.3 Audit record

One JSON line per write, appended to `audit_path` if set:

```json
{ "schema_version": 1, "ts": "...", "command": "create-user", "realm": "dev", "kind": "user", "id": "...", "result": "ok|refused|error", "code": 0 }
```

No credential, token, or secret value is ever written.

## 4. Interface

| Command | Effect | Needs a container runtime |
|---------|--------|---------------------------|
| `kc-axi up` | Start the container if not running; wait until ready | yes |
| `kc-axi down [--purge]` | Stop and remove the container; with `--purge`, remove its volume | yes |
| `kc-axi status` | Runtime found, container state, server reachable, version | only to report container state |
| `kc-axi realms` | List realms | no |
| `kc-axi clients [--realm R]` | List clients | no |
| `kc-axi users [--realm R]` | List users | no |
| `kc-axi get <kind> <id> [--realm R]` | One object | no |
| `kc-axi create-realm --file F` | Create a realm from a file | no |
| `kc-axi create-user`, `create-client`, `disable-user` | Write operations | no |

List commands take `--full`, `--limit N` (default 3), and `--json` (raw JSON, same field sets). Every write takes `--yes`.

All commands except `up`, `down` and `status` use only the Keycloak REST API, so they also work against a Keycloak that was not started by this tool, such as a remote one.

Embedded use: the same operations exist as a Go package with `on_event(callback)` for the audit records.

### 4.1 Output format

1. Plain key-value lines unless `--json`.
2. A list starts with `status: empty|active` and `total: N`, then the items, then `truncated: true|false`.
3. An empty result prints `status: empty` and `total: 0` and exits 0. It is never blank.
4. Ends with `suggested: <next command>` when one is obvious.
5. Errors go to stderr as `error: <code>: <message>`.
6. UTF-8, no colour or cursor control unless stdout is a terminal.

### 4.2 Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success, including an empty result |
| 2 | Usage error, including an ambiguous container runtime (section 5.2) |
| 3 | Keycloak unreachable or not ready |
| 4 | Authentication to Keycloak failed |
| 5 | Not found |
| 6 | Refused: a write without `--yes` |
| 7 | Container runtime missing, or it returned an error |

## 5. Behaviour

### 5.1 Reading and counting

The tool parses Keycloak's JSON response, counts items, then truncates by item to the limit. It does not parse text with line tools, so a value containing a comma, a space or a nested object cannot break the count.

### 5.2 Choosing a container runtime

`runtime: auto` works as follows:
- Commands that act on an existing container use the runtime that has a container with `container_name`.
- `up` with only one of Docker or Podman installed uses it.
- `up` with both installed, and neither holding the container, exits 2 and asks for `--runtime`. The tool does not guess, because the two keep separate container stores.

Runtimes are invoked as an argument list, never through a shell. This avoids quoting differences between `cmd`, PowerShell and POSIX shells, and avoids path rewriting by Windows POSIX-emulation shells (a known problem with container paths such as `/opt/...`; general knowledge, not tested here).

### 5.3 `up`

1. Check that `image` is set. The tool has **no default image tag**, so a moving tag such as `latest` cannot be used by accident.
2. Create the container in development mode, publishing the port on `127.0.0.1` only.
3. Pass the admin bootstrap credentials as environment variables to the container, read from the caller's environment or file.
4. Poll the server until ready or `ready_timeout` passes. Exit 3 on timeout.

Data persists only if `volume` is set. The default is a **named volume**, not a host directory, because host paths differ between Linux and Windows and a Podman bind mount on an SELinux host needs extra labelling (general knowledge, unverified). A caller who wants a host directory sets it explicitly.

### 5.4 Safety

- **Read by default.** A write without `--yes` prints what it would do, changes nothing, and exits 6.
- **No secrets in output** with or without `--full` or `--json`: no passwords, client secrets, tokens, or credential values.
- **No prompts.** The tool never waits for input.
- **Credentials never on the command line.** They would show in process listings. Sources, in order: the environment (`KC_ADMIN_USER`, `KC_ADMIN_PASSWORD`), then `admin_password_file`.
- **One login per call.** The tool obtains a short-lived admin token, uses it, and discards it. Nothing is written to disk.
- **File permission check.** On Linux, a password file readable by others is refused. Windows has no mode bits, so the tool does not check there and says so in `status`.

### 5.5 Platform matrix

| Concern | Linux | Windows |
|---------|-------|---------|
| Binary | Static, `amd64` and `arm64` | Static `.exe`, `amd64` and `arm64` |
| Container engine | Docker or Podman runs containers directly | Docker Desktop or Podman runs Linux containers inside a virtual machine (WSL2 or equivalent). The image is the same Linux image |
| Port on `127.0.0.1` | Direct | Forwarded by the engine (general knowledge; confirm for each engine) |
| Shell | None required | None required (no `bash`, `jq`, `grep` or `tr`) |
| Paths | `/`-separated | Accepts either separator in arguments; never builds a path inside the container |
| Line endings | LF written | LF written, CRLF accepted on read |

The same source also builds for macOS. It is not a stated requirement, and nobody has committed to testing it.

## 6. Configuration

```yaml
schema_version: 1
base_url: "http://127.0.0.1:8080"
admin_realm: "master"
runtime: auto                  # auto | docker | podman
container_name: "keycloak-dev"
image: ""                      # required for `up`; no default tag
port: 8080
volume: "keycloak-dev-data"    # named volume; empty means no persistence
ready_timeout_seconds: 120
default_limit: 3
audit_path: ""                 # empty means no audit file
```

Environment variables override the file: `KC_AXI_RUNTIME`, `KC_AXI_BASE_URL`, `KC_ADMIN_USER`, `KC_ADMIN_PASSWORD`.

## 7. Failure Modes

| Condition | Behaviour |
|-----------|-----------|
| Keycloak not reachable | Exit 3, error on stderr, no hang (every request has a timeout) |
| Wrong admin credentials | Exit 4 |
| Neither Docker nor Podman installed | Exit 7 for `up`, `down`, and the container line of `status` |
| Both installed, container not found | Exit 2 for `up`, as in section 5.2 |
| Container exists but stopped | `up` starts it; `status` reports `stopped` |
| Port already in use | Exit 7 with the runtime's message |
| Audit file not writable | The write is **refused** and exits 7 rather than proceeding unlogged |
| Unknown `schema_version` in config | Read N and N-1; newer is refused |
| Keycloak returns a field set this tool does not know | Unknown fields are ignored; only the documented ones are shown |

### Error records

The tool keeps its own typed errors. A consumer that wants one error vocabulary can express them as [error-classifier](error-classifier.md) records (a data format, not a dependency). Suggested `recoverability`:

| Exit code | Suggested recoverability |
|-----------|--------------------------|
| 3 | `transient` |
| 4, 5, 6 | `permanent` until the input or credential changes |
| 7 | `permanent` for missing runtime; `transient` for a port or daemon error |

## 8. Acceptance Criteria

1. `kc-axi clients` against a realm with no clients prints `status: empty` and `total: 0` and exits 0, with no `bash` or `jq` installed.
2. `kc-axi users` with five users prints three, `truncated: true` and `total: 5`.
3. A client or user value containing a comma, a space or a quote does not change counts or truncation.
4. With Keycloak stopped, every REST command exits 3 within the request timeout.
5. A wrong admin password exits 4.
6. A write without `--yes` changes nothing and exits 6.
7. No command prints a password, secret or token, with or without `--full` and `--json`.
8. The admin password never appears in the process list of the tool or of the container command.
9. `up` with no `image` configured refuses and exits 2.
10. `up`, `status` and `down` give the same results with Docker and with Podman.
11. The same acceptance cases pass on Linux and on Windows.
12. With the audit file unwritable, a write is refused and nothing changes.

## 9. How UMAS Uses It

| UMAS need | Mapping |
|-----------|---------|
| Identity provider for people (OIDC) | Keycloak, run by `up` in Phase 1 and moved to a production deployment in Phase 2 |
| One realm for the system | `create-realm --file` with a realm file kept in UMAS configuration. The realm name, the dashboard client (public, authorization code with PKCE), the API client (resource server) and the per-service clients are all in that file, not in this library |
| Roles and bindings | Not in Keycloak. They live in UMAS data. The API reads only the token's `sub`, `iss`, `iat`, `exp` and `jti` |
| Who may run it | An Admin and the Admin's own coding agent, for set-up and maintenance. **UMAS runtime agents never use it:** their roles have no access to configuration or secrets, and Keycloak admin rights would bypass that. The command must not be reachable from a Worker's sandbox |
| Audit of identity changes | `audit_path` pointing at a file the consumer ingests into [event-log](event-log.md), or the `on_event` callback |
| Pinned image | UMAS records the Keycloak image tag in one place and passes it as `image` |

See [modularisation-assessment.md](../modularisation-assessment.md) sections 5.6 to 5.9 for the RBAC decisions this serves.

## 10. Source Material and Deviations

Extracted from GitHub issue 18, "keycloak with axi.md", which proposes a Podman container and a Bash wrapper over `kcadm.sh`.

| Deviation | Why |
|-----------|-----|
| Go binary instead of a Bash script | The script needs `bash`, `grep`, `tr`, `head` and `echo`, so it does not run natively on Windows |
| REST API instead of `exec` into the container for `kcadm.sh` | Removes the container-runtime dependency from every admin command, works against a remote Keycloak, and avoids path and quoting problems on Windows |
| Docker and Podman both supported, never guessed | The issue picks Podman in its examples and asks which is wanted. The two keep separate container stores, so guessing would act on the wrong one |
| Admin credentials from the environment or a file | The issue types `admin`/`admin` into the command and the script, which end up in git and in agent transcripts |
| No default image tag | The issue uses `latest`, which changes behaviour between runs |
| JSON parsing instead of `grep` and `tr` | The issue's `set -e` with `grep -c` aborts on an empty result, so its advertised empty state never prints. Field extraction by `grep` breaks on commas, spaces and nested objects, and `head -n 9` cuts by line, not by item |
| All three kinds implemented | The issue documents `users` and `realms` but implements only `clients` |
| Write confirmation, audit, and a no-secrets rule | Not in the issue. An agent-facing tool that can change an identity server needs them |
| Principles named, not numbered | The numbering in the issue's comments does not match the list in its text |

## 11. Open Questions

1. Which container engine is the primary target for development, Docker or Podman? Both are supported by the contract; the answer decides which one the tests run against first.
2. Can the test matrix (two operating systems times two engines) be run? Hosted Windows build machines may not run Linux containers, so the Windows cases may need a developer machine.
3. Is the default list limit of 3, taken from the issue, useful for user lists?
4. Should the realm file be exported from a running instance (`kc-axi export-realm`) so a development setup can be rebuilt from scratch?
5. Which resources will an agent manage most: users, clients, realms or roles? Roles and groups are excluded for now.
6. Keycloak's licence, current version, the admin REST endpoints and the production requirements have not been checked.
7. Is macOS needed as a supported platform? The current development machine is macOS.
