# Agent guidance setup verification

Date: 29 October 2026 (Europe/Paris). Scope: instructions and skills only.

## Repository state and changes

Before setup, Projet 3 contained only docs/FRAUD_ML_PLAN.md, with no application, dependency manifest, tests, CI or Git repository. No implementation milestone was started.

Created root [AGENTS.md](../AGENTS.md) and six project-scoped skills:

- [fraud-ml-data](../.agents/skills/fraud-ml-data/SKILL.md)
- [fraud-pytorch-training](../.agents/skills/fraud-pytorch-training/SKILL.md)
- [fraud-model-evaluation](../.agents/skills/fraud-model-evaluation/SKILL.md)
- [fraud-api-integration](../.agents/skills/fraud-api-integration/SKILL.md)
- [fraud-tests-ci](../.agents/skills/fraud-tests-ci/SKILL.md)
- [fraud-review](../.agents/skills/fraud-review/SKILL.md)

Each skill has agents/openai.yaml metadata with implicit invocation enabled and an explicit $skill-name example. No generic user-scoped skill was copied or edited. Existing verification, adversarial-review and git-workflow are reused; implement-milestone is Payment-specific and deliberately not applied to Fraud ML.

Updated only the type-checker choice in the [plan](FRAUD_ML_PLAN.md): mypy becomes strict Pyright, with a note recording the user's newer requirement. Generator, model configuration, thresholds and M1–M3 scope are preserved.

## Checks and evidence

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Skill frontmatter and UI YAML | PASS | Ruby YAML.safe_load parsed all six SKILL.md manifests and all six openai.yaml files; names match folders, descriptions nonempty, implicit invocation true and prompts name the skill |
| Routing and references | PASS | All six skills are routed from AGENTS.md; referenced canonical generic skills exist; no placeholder scaffolding |
| Plan alignment | PASS | Diff limited to Pyright in stack/CI and one explanatory paragraph; no experiment changes |
| Fresh Codex discovery | PASS | Real ephemeral Codex invocation from Projet 3 reports all six skills in its available catalog, separately from explicit file reading |
| Effective skill use | PASS | Command-execution events confirm reading all six entrypoints plus AGENTS.md and the plan; response routes all six task types correctly |
| Boundary scenarios | PASS | Probe rejects fitting on train+test, using p(x) as a feature, Payment POST retry on ML timeout and substituting mypy for required Pyright |
| Generic skill preservation | PASS | Original SHA-256 values rechecked; no local copies created |
| Application tests, Ruff, Pyright, scans, training, Docker | SKIPPED | No implementation/tooling exists; these are future milestone gates, not setup outcomes |
| Bundled Python quick_validate.py | SKIPPED (environment) | Invocation fails before validation with ModuleNotFoundError: yaml; used actual Ruby YAML parsing instead, not an asserted official-validator pass |

The initial unprivileged probe could not initialize Codex's app-server/state database in the sandbox. The same read-only ephemeral probe succeeded with host access; execution exited 0. Unrelated optional MCP servers emitted startup warnings; they were not used by the probe. Writing the requested .agents directory also required host access because that directory is sandbox-protected. No automatic approval rejection occurred.

Discovery probe command shape:

```sh
codex exec --ephemeral --skip-git-repo-check --sandbox read-only --json \
  -C '/Users/william/Documents/Projet 3' \
  -o /tmp/fraud-codex-guidance-probe.md '<read-only discovery and boundary scenarios>'
```

Probe requested catalog-versus-disk distinction, six task routes, and the four adverse scenarios in the table. This is a bounded behavior check, not proof that future agents cannot violate instructions. The parent chat's initial skill catalog predates creation; the fresh process is the evidence of current discovery. A new chat/session rooted at Projet 3 can load the current instructions and catalog.

## Captured fresh-process result

Automatically supplied context includes the workspace’s `AGENTS.md` instructions, environment details, and the available-skill catalog with path mappings. I can confirm the six entries below are actually in that catalog—not merely mentioned in `AGENTS.md`. I cannot independently establish how the host injected the workspace instructions or whether other instruction files were loaded.

I then explicitly read the on-disk `AGENTS.md`, `docs/FRAUD_ML_PLAN.md`, and all six `SKILL.md` files. Catalog discovery itself did not read their contents.

| Work | Catalog skill and verified file |
|---|---|
| Synthetic splitting / sklearn preprocessing | [fraud-ml-data](</Users/william/Documents/Projet 3/.agents/skills/fraud-ml-data/SKILL.md>) |
| PyTorch checkpoints | [fraud-pytorch-training](</Users/william/Documents/Projet 3/.agents/skills/fraud-pytorch-training/SKILL.md>) |
| Thresholds / calibration evaluation | [fraud-model-evaluation](</Users/william/Documents/Projet 3/.agents/skills/fraud-model-evaluation/SKILL.md>) |
| FastAPI / read-only payment demo | [fraud-api-integration](</Users/william/Documents/Projet 3/.agents/skills/fraud-api-integration/SKILL.md>) |
| CI verification | [fraud-tests-ci](</Users/william/Documents/Projet 3/.agents/skills/fraud-tests-ci/SKILL.md>), alongside generic `verification` |
| Independent review | [fraud-review](</Users/william/Documents/Projet 3/.agents/skills/fraud-review/SKILL.md>), alongside generic `adversarial-review`; implemented milestones require a separate reviewer |

The loaded guidance requires:

- **Global train+test fit:** reject as leakage. Freeze disjoint split IDs first; fit on train only, select on validation, freeze before final test.
- **Oracle probability feature:** reject. `p(x)` stays in a separate evaluation-only reference; predictors are exclusively `amount_minor` and `currency`.
- **Payment POST retry after ML timeout:** reject. Payment access is authenticated GET-only; retries are disabled. Report score unavailable and exit nonzero, leaving Payment untouched.
- **Replace Pyright with mypy:** reject under current requirements. Strict Pyright covers `src` and tests; both the current instructions and the plan specify it.

**PASS:** catalog discovery and file consultation. **SKIPPED by scope:** application verification. No edits, training, code creation, Git initialization, or Payment contact occurred.

## Preserved user-scoped skill digests

- `verification`: `b991a4b650242402a6f48c519aa7288a1db0c106526b5201505a85b77910a488`
- `adversarial-review`: `dd878adef5546f9eb9421dd8cf725da068925147ced9a2c2e40f91f8cbc3b79b`
- `implement-milestone`: `458f60b9063c20d63cfa2325c59cc4e33da224c026ab0ec8d70f7c4b67a6a4f7`
- `git-workflow`: `88e3f26aedd164533b2fd3b411ac654852a4d1a763effe7f5e99e619e6bcf64f`

## Source and interpretation

[Official skills documentation](https://learn.chatgpt.com/docs/build-skills) documents project .agents/skills discovery and user-scoped reuse. [Official AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md) describes startup instruction loading. The local runtime probe supplements that documentation with observed behavior on this host.

Projet 1 remains outside setup scope. Its pre-existing untracked reviews/architecture-plan-review.md remains present; no tracked diff was observed before or after setup. No financial/API write call was performed. Future M3 acceptance still needs the real authorized local demo.
