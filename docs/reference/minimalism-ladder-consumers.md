# minimalism-ladder: UMAS consumer notes

> **Status:** Decided (owner, 2026-11-09, option A for §9 and option B for §12 of the round-2 choice). **Owner of this file:** this repo. The skill itself lives in [agent-garage](https://github.com/plaktoz/agent-garage) (`skills/minimalism-ladder`) and does not name UMAS.

This file was section 9 (Known Consumers) of the source spec. The pack folder was removed on 2026-11-09. The source spec is in git history at commit `44c1ef6`.

The skill does not depend on any of these consumers.

| UMAS concept | Mapping |
|--------------|---------|
| "Minimalism ladder enforced before any code is written" | The skill is prepended to the Developer and Worker prompts |
| `project.minimalism.level`, `enforce` | `level`, `enforce` in the skill's `config.yaml` |
| `MinimalismEnforcer` rungs 1 and 2, 6 | Implemented by the prompt; rungs 3 to 5 were stubs in code and need no code now |
| Shortcut comments tracked in a debt ledger | Format in the skill; scanner in decision-artifacts |
| `metrics minimalism` | Computed from stored ladder records |
| Router tiers | Ladder applies at every tier, including simple direct workers |

## Not carried over

- **Section 12 (reference code and YAML).** Not copied here. It was non-normative example code from `TECHNICAL-DESIGN-SPEC-PART3.md`, which is not in the tree. Its YAML keys (`enforcement_level`, `ladder.enabled`, `metrics.track_*`, `minimalism_config`) do not match the skill's §6 keys (`level`, `enforce`, `record`). Recover it from commit `44c1ef6` if the enforcer is built. Reconcile the keys first.
