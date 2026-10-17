# Abacus concepts

## The shape

```
                                   human
                                     │  plain language: "plan …", "build …", "work on …", "how are we doing?"
                              agent:concierge  ── the front door; records your words verbatim
                     plan ┌──────────┴──────────┐ build / work on
                          ▼                     ▼
                   agent:planner          agent:orchestrator  ── neither has Edit/Write tools;
            drafts beads on every      dispatches, verifies,      both are deployed out of their own reach
            repo; you approve          asks you for decisions
                                  reads ▲   │ SendMessage (DISPATCH / RULING)
              logbook (state) ◄─────────┤   ▼
              memory (lessons)          coder:repo-a ── workflow ──► abacus-finalize ──► origin
                                        coder:repo-b ── workflow ──► abacus-finalize ──► origin
                                            │ REPORT (a claim)  ▲ abacus-verify (board + remote)
```

Every box is an ordinary Claude Code session, running in a different role with different context and constraints.
A **worker** (`coder:<repo>`) writes code inside one repository. The **concierge**, **planner** and **orchestrator**
coordinate and never write code.

## How you talk to it
In plain language. The concierge works out what you mean, and when it can't tell, it asks one question before doing
anything. Behind the scenes, every request becomes one of a few kinds of act, defined once in the protocol so every
agent reads them the same way:

| What you ask for | The concierge reads it as | It's done when |
|---|---|---|
| a plan: "plan X", "scope this", "break this issue into beads", "turn this PDR into work" | **plan**: the planner drafts beads across every repository involved, with proposed labels | you approve the plan, in your words |
| finished work: "build X", "ship it", "finish", "deliver", "do X" | **build**: X and every bead it depends on, in order | every one of those beads is closed and its commit verified: on the default branch, or with draft-PR landing at the head of the bead's open draft PR |
| progress: "work on X", "make a start on", "push X along" | **work on**: advance X only | X reaches any report: closed, progress, blocked or needs-ruling |
| a question: "how are we doing?", "what needs me?", "what happened to X?" | an answer from durable state | — |
| an answer to a card: "go with b", "CSV", "approved" | a ruling, recorded verbatim and passed on | — |

Anything else gets clarified rather than guessed: "compile X" could mean "build it" or "just check it compiles",
so the concierge asks which. A remark ("we should probably…", "I wonder if…") is talked through, never turned into
work. Releases, tags, publishing and deploying are never implied by any request; those stay yours. You can name work
by its source ("build dasien/bwcli-rs#1") instead of bead ids: `abacus-board find` searches every board.

## Lanes: unrelated work side by side
Each independent line of work runs in its own **lane**: its own orchestrator (`agent:orchestrator-<lane>`), its own
decisions page, and its own context and cost. Android work and unrelated SDK work run as two lanes in parallel,
without crowding each other.
- **On demand.** The concierge opens a lane when new work arrives, names it after the work (`android`,
  `sdk-heartbeat`), and tells you the name. There's no limit on how many run at once.
- **One lane per repository.** A repository belongs to at most one active lane, enforced by the logbook (`LANE`),
  so lanes never compete for a worker. Work touching a lane's repositories joins that lane; when a lane's program
  completes it closes and releases them.
- **Ask about what you mean.** "How are we doing with the android work?" is answered from that lane alone. A general
  "how are we doing?" gives a line per lane. You can name a lane however you like ("the login fix", the issue, a
  repository); the concierge matches it, and asks if it's ambiguous. "What lanes are running?" lists them.

## The pieces

| Piece | How Abacus does it |
|---|---|
| Beads as system of record | `bd` board in every repo; acceptance criteria in the acceptance field; `FILED AGAINST: <sha>` stamp; `pipeline:<one-shot\|lite\|full\|manual\|operator>` label set by the owner |
| Filing and review skills | `/bead-file` (story · bug · epic · decompose), `/bead-close`, `/judgments`, `/adversarial-review`, `/retro` |
| Dynamic Workflows | `abacus-one-shot`, `abacus-lite`, `abacus-full` (one shared body), stages with structured outputs, a read-only probe after each stage, bounded fix rounds (an incomplete review is re-asked, not "fixed"), verdicts aligned to criteria by index, clean escalation that saves its patch |
| Worker isolation | Claude Code enforces a per-session git worktree for background sessions (`.claude/worktrees/<name>`). Abacus is worktree-native: one worktree per bead; the fence makes it the session's only writable space while protecting its control files; the board resolves to the main checkout; the run fast-forwards to origin first; the worktree is removed after a verified close and kept on escalation |
| Finishing script | `abacus-finalize`: refuses unless every criterion is `met` with evidence (or `moved` to a valid measurement bead); commits with trailers, checks them, pushes, then closes. With `"landing": "draft-pr"` it pushes the bead's own branch and opens a draft PR before closing ([Draft-PR landing](DRAFT-PR-LANDING.md)) |
| Git hooks | `.githooks/pre-commit` (fast check), `.githooks/pre-push` (full gate under the heavy lock) |
| Guards | `guards.py`: repo-fence, foreign-bd, destructive-git, stage-writes, database-url, operator-only, secrets, human-only, role-policy, role-commands; refusal log; negative-control tests |
| Human-only actions | `human-only` guard: operator rulings must be quoted from a genuine operator turn in the session transcript (or a ruling already in the logbook); no browser/desktop control as the signed-in operator; decision records (`docs/adr`, `docs/decisions`) change only with a one-time `abacus-authorize` grant that agents cannot issue |
| Secrets protection | `secrets` guard (no environment dumps, no printing secret variables, no credential-file reads, no `bw`/`bws secret`/keychain/`gh auth token` retrieval, `ps` refused while secrets are loaded) + `redact.py` PostToolUse hook (redacts loaded secret values, their URL/base64 encodings, and known token shapes from all tool output; fails closed) |
| Retrospectives | `/retro` skill; ten-key header; `abacus-validate-records` (POSIX sh); emit triggers as a pure function with a table test |
| Standards repo + doctor | abacus-standards; `abacus-doctor` (five verdicts, three tiers, deviations via `docs/adr` `deviates:<check>`); `abacus-adopt` rollout |
| Logbook | `abacus-logbook` (SQLite): current-state vs insert-only event tables (enforced by triggers), dispatch preconditions that fail closed (`PAUSED`, `ATTENDED`, `UNKNOWN_WORKER`, `WRONG_REPO`, `DUPLICATE`, `PREREQUISITE`, `UNRELAYED`, `BAD_CHECK`), recorded ruling relays, <1 KB digest, `rebuild` from boards |
| Agent View | `abacus-session` launcher (`claude --bg -n <role>:<repo>`, `auto` mode by default, shared memory passed explicitly, `~/.abacus/bin` on `PATH`), refusal codes, liveness reconciliation, `stop` that sees unsaved work in worktrees |
| Coordination protocol | `abacus-agents/protocol/PROTOCOL.md` + the worker contract skill `/abacus-worker`. A `RULING` message is the relay, recorded by a hook. A dispatch can carry `checks:`, read-only commands `abacus-verify` must see pass |
| Lanes | `abacus-logbook lane open/add/close/rename/show/find/owner`: each lane's goal (your words), repositories and items; one active lane per repository (`LANE`); dispatches record their lane. `abacus-status --lane` scopes status; each lane has `pages/decisions-<lane>.md`; the launcher starts `agent:orchestrator-<lane>` (and its `-g<n>` successors) from the one orchestrator entry |
| Orchestrator | `agent:orchestrator` (Opus): capped CLAUDE.md (8 rules), skills (`/recover`, `/handoff`, `/dispatch-bead`, `/verify-report`, `/relay-ruling`, `/file-proposals`, `/check-in`, `/hand-over`, `/decisions-page`), role-policy fence, SendMessage logging hook. Starts on demand and stops itself when a program completes |
| Planner | `agent:planner` (Opus): turns a source (GitHub issue, local file, pasted text; Jira and Confluence TBD) into **draft** beads on every fleet repository involved, in order, with `WAITS-ON` lines, external edges and a proposed pipeline label each. One `PLAN-REVIEW` goes to the operator through the concierge. The `foreign-bd` guard lets it file and shape drafts only, and apply a pipeline label (or lift `draft`) only on beads an operator ruling names; `abacus-board brief` refuses a draft |
| Concierge | `agent:concierge` (Sonnet): the operator's front door, a dedicated session in Agent View (`abacus chat`). It answers from durable state (Agent View first for what's running), records the operator's words verbatim (its one write), finds work on any board, starts the planner or orchestrator on demand, and passes instructions on with a `HANDOFF` (`STATUS: decided \| lean`). A `role-commands` guard enforces its command allowlist. Design: `abacus-agents/docs/CONCIERGE.md` |
| Deploy out of reach | `abacus-deploy`: from a published commit (the installed snapshot's `.published`, or a clean pushed checkout), with a manifest naming that commit; runtime folders are never touched; local edits are overwritten |
| Recovery & handover | `/recover` (board wins); handover state machine `launched → recovered → finished` / `aborted` / `adopted` |
| Judgment loop | JUDGEMENT / STANDING / OUTCOME rows on beads, each naming its logbook ruling (`ruling: #<id>`); `abacus-judgment check / due / status`; operator words stored verbatim first, and a ruling counts as recorded on a bead only when the bead's notes quote it |
| Shared memory | `abacus-memory`: harvest (published records only) → idempotent ingest → `consult_memory` MCP tool with four named outcomes and corpus coverage |

## Three layers of state
1. **System of record**: each repository's Beads board. It is authoritative for the work, its criteria and whether it
   is done. The orchestrator reads boards; it never becomes a second source of truth.
2. **Operating state**: Agent View (which sessions exist) plus the logbook (dispatches, reports, promises, rulings,
   observations). A report is a claim; only `abacus-verify` turns it into a verified dispatch.
3. **Session context**: disposable. Workers stop at a bead boundary when they hit their context ceiling. The
   orchestrator hands over at roughly 30% of its window remaining.

Each layer can be lost and rebuilt from a more durable one.

## Authority boundary (starting position)

| The orchestrator and planner may | The operator retains |
|---|---|
| (planner) file, edit, wire and drop **draft** beads on any board | approving a plan, and every pipeline label |
| start or queue a bead whose pipeline the owner selected | credentials |
| re-sequence work; move an unmet criterion to a follow-up bead | releases and tags |
| decide design questions or NEEDS-RULING reports where a recorded delegation covers them | changes to guards, hooks, gates, workflows |
| record the ruling and notify the operator | production data and go-live |
| | spending beyond a recorded budget |
| | anything irreversible |

Delegation grows from evidence. Rulings that hold, as recorded in OUTCOME rows, become standing rules or delegated
authority. Rulings that fail tighten the boundary.

## Rules, procedures, enforcement
- **CLAUDE.md** holds only the rules that bind every session, and is capped. When a rule becomes enforceable, the
  prose is replaced with a pointer to the enforcement.
- **Skills** hold procedure.
- **Hooks and guards** enforce what cannot depend on the model remembering it.

## What stops a worker, and who enforces it
Two separate mechanisms limit a worker, and they get confused:

| | Abacus's repo fence (`guards.py`) | Claude Code's worktree isolation |
|---|---|---|
| Guards | **writes**: into another repository, the main checkout, `~/.claude`, `~/.abacus`, the repo's own controls | **where git can point**: a background session isolated in a worktree may run git only against that worktree |
| Reads of another repository | allowed by design (`cat`, `grep`, `git -C <abs path> log` all pass) | `git -C ../other …` is refused; it can't verify a path computed at runtime |
| Shows up as | `[abacus:repo-fence] REFUSED: …`, logged in `~/.abacus/state/refusals.jsonl` | "This session is isolated in the worktree …", not in Abacus's log |

So a worker can't reliably check another repository from its worktree, and it isn't meant to. Cross-repository
conditions go on a bead's `WAITS-ON` line, and the orchestrator checks them before dispatch (see `/bead-file` and
`/dispatch-bead`). A refused sibling read is not a gap in the fence: report it as BLOCKED, never route around it.
The fence treats interpreter one-liners (`python3 -c`, `node -e`, …) that name an outside path as writes, because
it can't tell a script's read from a write. Use `cat`, `head`, `grep` or `sed -n` to read.

## Why separate repositories
- **abacus** is the entry point: the installer, the `abacus` command, the demos and the docs.
- **abacus-standards** owns conventions and their checks, and nothing else.
- **abacus-infra** owns durable machinery but defines no policy.
- **abacus-agents** owns the coordinating roles and the protocol, deployed somewhere the running agents cannot edit.

A session cannot widen its own authority because the source of that authority is out of its reach.
