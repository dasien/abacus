# Roadmap and known limits

## Next
- **More than one worker per repository.** Lanes (0.10.0) run unrelated work side by side, but a repository belongs
  to one lane at a time and has one worker, so two lanes can't work in the same repository at once. Several
  workers per repository, each in its own worktree, is the next step there.
- **Draft PRs by default for shared repositories.** Draft-PR landing exists now (`"landing": "draft-pr"` in a
  repository's `.abacus/config.json`), but it's opt-in and `abacus add` doesn't offer it yet. It should ask, and the
  demos should show it.
- **Fewer trips to the terminal.** Day to day, you should only need the concierge. Bringing a repository in is one
  command now (`abacus add`); next it becomes a conversation ("add ~/Source/repos/server to Abacus") that proposes
  the adoption for you to confirm, using the same steps.
- **More planner sources.** GitHub issues, local files and pasted text work today. Jira and Confluence are TBD.
- **Verify that a consumer pins the producer version the orchestrator verified.** A read-only `--check` covers a pin
  today. A general check should be designed against a real multi-repository case.
- **Calibrate shared memory** once real repositories feed it (`abacus-memory calibrate`).

## Deliberately not built yet
- **Periodic inspection**: a weekly review of what escaped, a monthly audit of decisions and rules, a quarterly
  review of the whole system. Run the weekly review by hand before automating anything; the judgment and retro
  records it needs already exist.
- **Vector memory**: shared memory uses SQLite FTS5 (BM25, Porter stemming). The `consult_memory` interface, its four
  outcomes and the floor calibration (`abacus-memory calibrate`) are engine-agnostic. Postgres + pgvector + a reranker
  can replace the engine without changing callers.
- **Plugin packaging**: conventions are vendored into each repository by `abacus-adopt` so the doctor can check them
  byte-for-byte and code review sees every change. A Claude Code plugin marketplace could distribute skills later.
- **Decisions page UI**: `pages/decisions.md` (and `decisions-<lane>.md` per lane) is plain markdown.

## How proposals are tracked
The orchestrator turns retro actions into beads on the Abacus repositories' own boards (label `retro-action`),
deduplicated, so a repeat shows up as a note on one bead rather than a new one. Boards are local to each clone until
a shared Beads remote is set up (`bd dolt push`).

## Known limits (be honest about these)
- **A build pushes to the default branch unless the repository opts into draft PRs.** Set `"landing": "draft-pr"`
  in its `.abacus/config.json` for any repository whose default branch is protected or shared: each bead then lands
  on its own branch and closes when its draft PR opens, and merging stays with people. Draft-PR landing needs the
  GitHub CLI (`gh`), signed in.
- **Cross-repository dependencies are recorded on the boards, but enforced by the logbook.** Beads 1.3 stores
  `external:<project>:<capability>` edges and `bd ship` marks capabilities delivered. With separate embedded
  databases, `bd ready` doesn't treat unshipped external edges as blocking. Abacus records the edge for visibility,
  and the orchestrator ships after verification; `--requires-verified` is the actual gate.
- **Secrets protection is defence in depth, not a vault.** The `secrets` guard blocks the common exposure paths
  (environment dumps, printing secret variables, reading credential files, credential-retrieval CLIs, `ps` while
  secrets are loaded). `redact.py` scrubs the values of secret-named variables loaded in the session, plus well-known
  token shapes, from every tool's output. It cannot see secrets that exist only in a child process (a value a
  script reads from a vault and prints) or ones with no recognizable shape. Also: `Grep` over a directory honors
  `.gitignore` but not the credential-file list, so keep dotenv files gitignored. **Don't give agent sessions
  credentials they don't need.** For Bitwarden, inject the narrowest Secrets Manager machine-account token, scoped
  per repository, and keep vault access (`bw`) human-only, which the guard enforces.
- **Abacus depends on Claude Code's worktree isolation.** Background sessions must edit inside a worktree under
  `.claude/worktrees/`. Abacus's fence, board and verify logic follow that layout. If Claude Code changes where
  worktrees live, the fence refuses rather than allows, and workers report BLOCKED.
- **Project `.mcp.json` isn't discovered everywhere.** In the orchestrator's (non-repository) directory Claude Code
  never loaded it, and never asked for approval. The launcher passes the memory server explicitly with
  `--mcp-config`. Sessions you start yourself outside a repository may not have `consult_memory`.
- **Lanes share the machine.** Each lane has its own orchestrator and workers, but gates and pushes from every lane
  take turns on the one machine-wide heavy lock, so parallel lanes finish later than either alone would.
- **Dispatch checks are deliberately narrow.** One read-only program per check, executed without a shell, from an
  allowlist (grep, test, cat, read-only git, ...). Anything richer belongs in the bead's acceptance criteria.
- **Coordination cost.** In test runs the orchestrator (Opus) used 34-56k output tokens per two-bead program,
  2-3x both workers combined. Each lane runs its own orchestrator, so two lanes cost about twice that. The planner also runs on Opus. Track it per role, and cut wake-ups before tuning worker prompts.
- **Ruling attestation reads the session transcript.** The `human-only` guard accepts quoted operator words only if
  they appear in a user turn whose `promptSource` is typed or SDK-submitted, excluding tool results, skill text, task
  notifications and relayed agent messages, or if they are already in the logbook. This relies on Claude Code's
  transcript format (verified on 2.1.296). If the format changes, the guard fails closed: rulings get refused, never
  silently accepted. An operator who gives a ruling outside the session must restate it in the session.
- **The message protocol is a convention.** No parser rejects a malformed DISPATCH. Enforcement comes from logbook
  preconditions, tests over the templates, and verification on receipt.
- **The worker contract is advisory.** It binds only repositories that adopted it.
- **Workflow-stage detection** (`stage-writes` guard) relies on the hook payload's `agent_type` starting with
  `workflow` (observed live as `workflow-subagent` on Claude Code 2.1.296), or on `ABACUS_STAGE=1`. Re-check after
  Claude Code upgrades: `agent_type` is recorded in `~/.abacus/state/refusals.jsonl`. `abacus-finalize` is the
  backstop either way.
- **`bd where --json` field names**: `abacus-board` accepts `path`, `beads_dir`, `database` or `db_path`. If your
  Beads version differs, the board stage refuses and names what it got.
- **Guard shell parsing** is a careful heuristic (heredoc stripping, operator splitting, `cd` tracking, wrapper
  skipping), not a full shell. It fails closed on unparseable input, and the negative controls in
  `abacus-standards/tests/test_guards.py` are the contract. Add a test before changing a guard.
- **Single machine.** The heavy lock, logbook and memory live under `~/.abacus` on one machine. Cross-machine fleets
  need a shared logbook (Postgres) and a distributed lock.
- **Cost and time.** A `full` run takes tens of minutes and many subagent calls. Model selection by stage
  (haiku/sonnet/opus) is built in, but measure it.
