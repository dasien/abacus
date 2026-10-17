# Abacus

**Orchestrated multi-agent development**

Abacus is a reference implementation of an orchestrated development pattern. 
It's built on Claude Code's Dynamic Workflows, Agent View and cross-session messaging, with Beads as
the system of record.

Abacus has four parts:

1. **Reliable workers.** One Claude Code session per repository takes a well-scoped bead through a bounded
   Dynamic Workflow (`one-shot`, `lite` or `full`). Guards, git gates, a fresh adversarial reviewer and a single
   close-out door (`abacus-finalize`) mean a bead closes only on evidence.
2. **Agents that coordinate and never write code.**
   - The **concierge** is your one front door: you talk to it in plain language.
   - The **planner** turns a source (an issue, a document, pasted text) into draft beads on every repository
     involved, for your approval.
   - The **orchestrator** dispatches approved work, verifies every report against boards and remotes, and asks you
     only for real decisions.
3. **Shared state and conventions.** A logbook of operating state, a coordination protocol, conventions with a
   `doctor` that checks them, and a learning loop: structured retros, judgment records and a shared memory
   (`consult_memory`) built from every repository's records.
4. **Demos you can run.** A two-repository demo, in which a bead in one repository unblocks a bead in another, and
   a decision demo, in which a worker stops to ask you a product question.

## Repositories

| Repo | Role | Contents |
|---|---|---|
| **abacus** (this) | entry point | installer, the `abacus` command, demos (`demos/`), docs |
| [abacus-standards](https://github.com/dasien/abacus-standards) | rules inside each repository | guards, git hooks, the three Dynamic Workflows, worker skills, `abacus-doctor`, `abacus-adopt`, `abacus-finalize`, `abacus-board`, record validator, judgment checker |
| [abacus-infra](https://github.com/dasien/abacus-infra) | shared state and services | `abacus-logbook` (SQLite state), `abacus-memory` (harvest → ingest → `consult_memory` MCP), `abacus-verify`, `abacus-session` launcher, `abacus-status`, `abacus-lock` |
| [abacus-agents](https://github.com/dasien/abacus-agents) | the agents that coordinate | the concierge, planner and orchestrator roles (deployed to `~/.abacus/agents`), the coordination protocol, `abacus-deploy` |

## Quick start

**New here? Follow [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)** (about 15 minutes, step by step).

```sh
./install.sh --workspace <repo root>      # guided; ends by running `abacus doctor` and shows what's left
abacus add <repo root>/myCodeRepo         # bring a repository in: board, conventions, worker, trust
abacus chat                               # then: "plan <issue link or file>", review it, "build <it>"
```
To see a full run first, try a demo: `abacus demo setup && abacus trust && abacus chat`.

Sessions run in Claude Code's `auto` permission mode. Background workers isolate each bead in its own git worktree
(Claude Code enforces this), and Abacus's guards treat that worktree as the session's only writable space.

The full walkthrough is in [docs/DEMO.md](docs/DEMO.md).

## Talking to Abacus
```sh
abacus chat                 # open the concierge (starts it if needed); also reachable from `claude agents`
abacus status               # what needs you, what's running, what finished
abacus statusline enable    # show that in every Claude Code session's status line (--wrap keeps yours)
abacus update               # get the latest Abacus (--check shows what's new first)
```
Tell the concierge what you want, in plain language. Behind the scenes it maps your request onto a few defined acts,
and asks you when it can't tell which you mean:
- **plan** a source (a GitHub issue, a local file, or text you paste): the planner drafts beads on every repo
  involved, in order, with proposed pipeline labels. You review and approve them in the concierge.
- **build** it ("ship", "finish" and "deliver" mean the same): finish it, including anything it depends on.
- **work on** it: make progress and report where it stands.
- or just ask: "how are we doing?", "what needs me?"

The concierge records your words, starts the planner or orchestrator on demand, and hands the work over. Unrelated
work runs in separate **lanes**, each with its own orchestrator ("how are we doing with the android work?" answers
for that lane only). Decisions that need you show up in the concierge and in the status line. Jira and Confluence
sources are TBD.

## Docs
- [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md): the first 15 minutes, step by step
- [docs/END-TO-END.md](docs/END-TO-END.md): the whole path from install to results, with diagrams
- [docs/INSTALL.md](docs/INSTALL.md): installing, upgrading, uninstalling
- [docs/DEMO.md](docs/DEMO.md): the demos step by step, and what a good run looks like
- [docs/CONCEPTS.md](docs/CONCEPTS.md): architecture, state model, authority boundary, and what enforces what
- [docs/DRAFT-PR-LANDING.md](docs/DRAFT-PR-LANDING.md): ending each bead at a draft PR on repositories that take
  changes through review
- [docs/ROADMAP.md](docs/ROADMAP.md): what's next, what's deliberately not built yet, and known limits
- [CHANGELOG.md](CHANGELOG.md): what each version changed, and how the version number moves
