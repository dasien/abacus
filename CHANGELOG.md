# Changelog

One version for all four Abacus repositories (`abacus`, `abacus-standards`, `abacus-infra`, `abacus-agents`).
Bug fixes bump the patch number, features bump the minor number, and the major number changes only when the
operator decides it. See [docs/INSTALL.md](docs/INSTALL.md#versions).

## 0.10.0 (2026-10-16)
- **Lanes: unrelated work side by side.** Each independent line of work runs in its own lane, with its own
  orchestrator (`agent:orchestrator-<lane>`), its own decisions page, and its own context and cost. Android work and
  unrelated SDK work can run in parallel.
  - **On demand:** the concierge opens lanes when work arrives, names them after the work, and tells you the name.
    There's no cap.
  - **One active lane per repository,** enforced by the logbook (`LANE`), so lanes never compete for a worker. Work
    touching a lane's repositories joins it. A lane closes when its program completes, releasing its repositories.
  - **Status answers what you asked:** "how are we doing with the android work?" covers only that lane. A general
    question gets a line per lane. You can refer to a lane by its name, a repository, the issue or your own words.
  - **New commands:** `abacus-logbook lane …` and `abacus status --lane <lane>`. The status line counts lanes. Lanes
    can be renamed between programs.
  - **Under the hood:** the session launcher starts lane orchestrators and their successors from the one orchestrator
    entry. The concierge's allowlist accepts `agent:orchestrator-*` session names. Install and update add new
    settings (like `"lanes"`) to an existing fleet without changing yours.
- Fix: `abacus status` no longer counts a decisions page reading `_None._` as one decision that needs you.
- Fix: `abacus chat` waits up to 90 seconds (was 20) for a newly started concierge to appear in Agent View, says
  it's waiting, and no longer loses its messages when output is piped. Claude Code sometimes takes most of a
  minute to register a background session.
- Fix: a failed `claude agents --json` is no longer read as "nothing running". That reading is how one `abacus chat`
  started a second concierge. The launcher now refuses with `AGENT_VIEW` and the error; `abacus chat` shows it
  instead of starting another. Every failure is logged in `~/.abacus/state/agent-view.log`; `ABACUS_DEBUG=1` prints
  each lookup.
- Not yet: more than one worker per repository.

## 0.9.0 (2026-10-16)
- **Draft-PR landing** (contributed by Patrick Honkonen; implements `abacus-8jc`).
  - **Opting in:** with `"landing": "draft-pr"` in a repository's `.abacus/config.json`, each bead lands on its own
    branch, `abacus/<slug>-<bead id>`, and closes when its draft PR opens. Merging stays with people. The default,
    "push", is unchanged, and an unknown value is refused, so a typo can't fall back to pushing.
  - **Stacking across repos:** a bead whose dependency still has an open PR builds on that PR's branch, and refuses
    if there are two.
  - **Verification:** `abacus-verify` checks the head of the bead's open PR.
  - **The agents:** the orchestrator's instructions and the protocol say what "done" means in this mode.
  - **Requirements:** needs the GitHub CLI (`gh`), signed in.
- **Finalize no longer adds a Co-Authored-By trailer** to bead and record commits (contributed by Patrick
  Honkonen). Each repository decides its own attribution policy.
- **`abacus update`** brings your clones up to date and publishes them, without re-running setup.
  - It fetches each repository from its configured source and fast-forwards.
  - It stops before changing anything if a clone has local commits or is on another branch.
  - It shows the new commits and the changelog entries since your installed version (`--check` stops there).
  - Then it publishes, deploys, restarts the concierge if it's idle, and runs the doctor.
- **Where updates come from is configurable.** `sources.json` in the abacus repository names each repository's URL
  and branch, defaulting to `github.com/dasien/<repo>` on `main`. A fork edits it for its own users, and a user can
  override it in `~/.abacus/config.json`. `abacus --version` shows each repository's source.
- **Uncommitted edits no longer block an install.** They're listed and left out; only committed work is published.

## 0.8.3 (2026-10-15)
- **A crashing guard refuses instead of allowing.** Claude Code treats a hook's exit 1 as non-blocking, so an
  unexpected error in `guards.py` (a payload without `tool_input`, `bd` missing for the planner) used to let the
  call through. Any crash is now an `abacus-guards` refusal with exit 2, logged like any other.
- **A failed `abacus-finalize` push can simply be retried.** When the push or the trailer check refuses, finalize
  undoes the commit it just made, so the changes stay staged and the bead stays open. Running the same command
  again works, where before it refused with "nothing to commit". `--record` does the same.

## 0.8.2 (2026-10-14)
- **Install hints fit your platform.** When a prerequisite is missing, the installer and `abacus doctor` suggest
  `xcode-select` on macOS, your package manager on Linux (apt, dnf, yum, pacman, zypper or apk), and WSL on
  Windows. Beads is suggested via Homebrew only when you have it, and via npm otherwise.
- **Docs are honest about platforms.** Abacus doesn't require macOS. It's tested there, Linux should work but
  hasn't been tested, and on Windows, WSL is the route (also untested).

## 0.8.1 (2026-10-14)
- **Plain language, not required verbs.** The protocol says that build, work on and plan are meanings: the concierge
  maps your own wording onto them when it's clear, and asks one question when it isn't. "Work on" gets synonyms
  too. CONCEPTS and the README describe it that way, with examples of plans, builds, progress, questions and card
  answers, and of what gets clarified rather than guessed.

## 0.8.0 (2026-10-14)
- **`abacus add <path>` brings a repository in with one command.** In order, it:
  - creates the Beads board
  - detects the gate commands from the repo's build files (Makefile, `package.json`, `Cargo.toml`, `go.mod`,
    Python, .NET) and asks you to confirm them
  - runs the adoption, then shows you the changes and the repository doctor's results
  - registers and deploys the worker
  - asks before committing, before pushing, and before opening Claude Code's trust prompt

  It replaces `bd init`, `abacus-adopt`, hand-editing `fleet.json`, `abacus-deploy` and `abacus trust`.
- **`abacus-adopt` catches a `.gitignore` that hides its files** (`abacus-standards-goq`). A rule ignoring all of
  `.claude` is narrowed, so your local settings stay ignored. Any other such rule is refused before anything is
  written. The repository doctor gets a `tracked` check.
- **The installer ends by running `abacus doctor`,** and links `abacus` into a folder already on your PATH. You no
  longer need a new terminal to keep going.
- **One doctor.** `abacus doctor` run inside an adopted repository checks that repository too.

## 0.7.2 (2026-10-14)
- **Docs reviewed** across all four repositories, ahead of publishing. They now describe Abacus as it is:
  - the concierge, planner and orchestrator, and the plan / build / work on verbs
  - one sandbox folder for demos
  - a "Next" section in the roadmap: draft PRs, fewer trips to the terminal, more planner sources
  - known limits, including that builds still push to the default branch

  References to the original design document were removed.
- **The concierge points you to itself, not a terminal**, for progress: "ask me how it's going".

## 0.7.1 (2026-10-14)
Fixes from the first planner run:
- **"Recorded on a bead" has to be true** (`abacus-infra-3zg`, your decision). `abacus-logbook ruling recorded --on
  <bead>` refuses unless the bead's notes on its board quote the ruling's words. The planner no longer marks its
  approval ruling recorded; the orchestrator writes the notes when it builds.
- **Notes on a bead carry the ruling id** (`abacus-agents-5rg`). JUDGEMENT and STANDING rows can end with
  `ruling: #<id>`, and the orchestrator always adds it, so a worker can match each relayed ruling to its note.
- **No stale decisions page** (`abacus-agents-8xk`). Any setup that replaces a scenario's sandbox, in place or
  moved to the new sandbox folder, archives the previous run first. The orchestrator's recovery also checks the
  page against the boards and remotes before acting.
- **Allowlists that fit the work.** The planner may run read-only git without `-C`, and the concierge may use
  `sed -n`. Anything that would write is still refused by their write fences.

## 0.7.0 (2026-10-13)
- **The planner** (`agent:planner`, `abacus-agents-alw`). Tell the concierge "plan <source>", for a GitHub issue, a
  local file or folder, or pasted text (Jira and Confluence are TBD).
  - The planner reads the source and the code it touches in each fleet repo.
  - It drafts beads by the `/bead-file` rules, wires their order across repos with `WAITS-ON` and external
    dependencies, and proposes a pipeline label for each, with a reason.
  - You review and approve everything in one conversation in the concierge. It runs on Opus, never writes code,
    and stops itself when done.
- **Approval is enforced.** The planner files only `draft` beads. It can apply a pipeline label, or lift `draft`,
  only on beads named in a ruling of yours, which the concierge records verbatim and the guard checks in the
  logbook. `abacus-board brief` refuses any bead still labeled `draft`.
- **`abacus-board find`** searches every fleet board by id, title, source link or `#issue`. It pulls in
  prerequisites, and marks what's ready (labeled, open, not a draft, which is what "staged" means). The concierge,
  planner and orchestrator use it, so you can name work by its source instead of bead ids.
- **The concierge** routes plans to the planner, records approvals with the drafts as targets, and checks what's
  running from Agent View before the logbook.
- The installer adds the planner to existing fleets and asks you to trust `~/.abacus/agents/planner`.

## 0.6.0 (2026-10-13)
- **One sandbox folder for every demo.** `abacus demo setup` generates into `abacus-sandboxes/<scenario>/`, beside
  your first workspace root, instead of `abacus-demo/` and `abacus-demo-decision/` scattered in your source folder.
  Setup adds the sandbox folder as a workspace root, so the repo fence still covers it. Existing sandboxes keep
  working where they are, and the next `setup --force` rebuilds a scenario in the new place.
- **Demo content is files, not code.** Each scenario's starting files and beads live in `demos/<scenario>/` in the
  abacus repo: a folder per repo, plus `scenario.json` for the beads and their cross-repo waits. One set of helpers
  generates all three scenarios. `bin/abacus` went from 1,330 to about 1,070 lines. The generated starting commits
  are byte-for-byte what 0.5.0 produced.
- Generated repos finish with a clean working tree: the cross-repo board link is committed with the adoption.

## 0.5.0 (2026-10-13)
- **"Build" and "work on" are the verbs** (your ruling, replacing "ship"). The protocol defines them, and the
  concierge and orchestrator read them:
  - **build X** means X and every bead it needs first, in any repo, each finished and verified.
  - **work on X** means advance X only, and stop at any report.
  - Releases and tags are never part of either, and nobody asks about them unless you do. That closes
    `abacus-agents-5ug`, so the "what does ship mean?" card stops appearing.
  - When the concierge confirms a build, it names the whole chain, and its handoff never excludes a prerequisite.
- **To-do: "done" moves to a draft PR** (`abacus-8jc`). You chose the planner first. Until then, build ends at a
  verified commit on the default branch.
- **The orchestrator's proposals keep their line breaks.** `/file-proposals` passes descriptions with `--body-file`,
  and reads the Abacus repo paths with `cat` instead of a script.
- The demo messages and docs say "Build …" instead of "Ship …".

## 0.4.0 (2026-10-13)
- **`abacus-orchestrator` is now `abacus-agents`.** The repository holds every role that coordinates work without
  writing code: the orchestrator, the concierge, and next the planner (`abacus-agents-alw`). The new name matches
  where those roles are deployed, `~/.abacus/agents/`. Session names (`agent:orchestrator`, `agent:concierge`) are
  unchanged, and the board's bead ids moved to the `abacus-agents-` prefix.
- **Upgrading:** rename your clone (`mv abacus-orchestrator abacus-agents`), then run `./install.sh`. The installer
  removes the old `~/.abacus/lib/abacus-orchestrator` snapshot, and if it finds a clone under the old name it tells
  you to rename it.

## 0.3.4 (2026-10-13)
Fixes from heartbeat run 2:
- **Fix: `git reflog` is a read.** Plain `git reflog` (also with options or a ref) means `reflog show`, but the guard
  treated it as a write and refused the orchestrator's read-only check. `reflog expire` and `delete` are still
  refused.
- **Clearer refusals for interpreter one-liners.** When the fence refuses `python3 -c`, `node -e` and similar, it now
  explains that it can't tell a script's read from a write, and points to `cat`, `head`, `grep` or `sed -n` for
  reads.
- **Status says what time it is.** `abacus-status` and the logbook digest start with the current time in UTC and
  local time. The concierge couldn't tell whether a worker's lease had lapsed.
- **Workers report BLOCKED instead of routing around a refusal.** After a refused sibling read, a worker had tried
  decompressing the other repository's raw git objects, then an absolute path. Its instructions now forbid both.
- **Docs: what stops a worker.** CONCEPTS.md explains the difference between Abacus's fence, which guards writes,
  and Claude Code's worktree isolation, which limits where git can point. The orchestrator has a matching note, so
  it stops logging "fence gaps" that aren't gaps.

## 0.3.3 (2026-10-13)
- **Fix: `abacus chat` attaches to the running concierge.** It attached by name. Agent View keeps a record of every
  stopped session, and orchestrator task text mentions the concierge, so `claude attach agent:concierge` matched
  many sessions and asked for an id instead of opening the conversation. It now finds the running concierge's id
  and attaches to that. DEMO.md no longer suggests attaching by name.

## 0.3.2 (2026-10-13)
- **Cross-repository conditions are the orchestrator's to check** (abacus-standards-i3p, your decision: no guard or
  sandbox change). `/bead-file` keeps acceptance criteria inside the repository and puts the cross-repository
  condition on a `WAITS-ON` line. `/dispatch-bead` has the orchestrator check that condition itself, read-only, and
  record it in the dispatch's preconditions. The heartbeat CLI bead now has four criteria. Its fifth, which read
  `../sdk-internal`, moved to the WAITS-ON line.

## 0.3.1 (2026-10-13)
Fixes from the first heartbeat pilot run:
- **Finalize records what landed** (abacus-standards-6mv). The close reason lists the landed commit's files with its
  sha. Criteria that name a `git diff`, `log` or `show` range get that re-read next to the worker's evidence, which
  was gathered before the commit existed.
- **The orchestrator reads each repository's default branch** instead of assuming `main`
  (abacus-agents-vbp, filed as abacus-orchestrator-vbp). `bwcli-rs` uses `master`. Recovery also gained the never-fetch note.
- **Dispatches record their prerequisites.** The logbook stores each `--requires-verified` gate with the commit it
  was verified at, and `abacus-logbook show dispatches` lists every dispatch with it, so repeated runs can be checked
  for whether the order was enforced.

## 0.3.0 (2026-10-12)
- **The heartbeat pilot** (`abacus demo setup --scenario heartbeat`). Real code: sandbox copies of your
  `sdk-internal` and `bwcli-rs` with local remotes, both adopted, the SDK reachable from the CLI's worker worktrees,
  one shared cargo build folder, and two filed, labeled beads for dasien/bwcli-rs#1.
- **`abacus demo reset`** puts a demo back to its starting point for another run, archiving the logbook and decisions
  page as `<scenario>-N`. For heartbeat it resets the repos, remotes and boards to the baseline in seconds (keeping the
  bead ids and the build cache). `--empty-boards` resets with no beads, for testing filing.
- The heartbeat setup opens up a `.gitignore` that hides `.claude/` for Abacus's own files, so workers' worktrees get
  the guards (abacus-standards-goq tracks doing this in `abacus-adopt` itself).

## 0.2.1 (2026-10-12)
- **Fix:** a ruling that covers no bead (for example "start the orchestrator") no longer counts as unrecorded at
  every recovery and check-in (abacus-infra-0w0). The orchestrator closes it out with
  `abacus-logbook ruling recorded <id> --on none --reason "..."`. The logbook refuses this for a ruling that covers
  beads, and refuses it without a reason. Existing logbooks are migrated in place.

## 0.2.0 (2026-10-12)
- **Several workspace roots** (abacus-dy3). `abacus install --workspace` can be repeated. The repo fence protects
  every root, and every repository registered in the fleet wherever it lives. A reinstall keeps your roots.
- **Works with your own status line** (abacus-huy). `abacus statusline enable --wrap` keeps your status line and
  appends Abacus's state to it, and `disable` restores it exactly. The installer offers this when it finds one.
  Before, `install --yes` stopped with an error for anyone who already had a status line.
- `abacus doctor` shows every workspace root, and whether the status line is wrapping yours.

## 0.1.0 (2026-10-12)
First versioned release: reliable workers, the orchestrator and its shared state, and a minimal learning loop.
- **Workers:** guards and hooks, Dynamic Workflows (one-shot, lite, full), and skills for running and closing a
  bead.
- **Orchestrator:** a logbook, shared memory on SQLite FTS, independent verification, and a session launcher.
- **Concierge:** the operator's front door in Agent View. It starts the orchestrator on demand.
- **CLI:** the installer, `doctor`, `trust`, two demos (two-repo and decision), `chat`, `status`, `statusline`,
  `prune` and `--version`.

Proven live on two-repo runs 4–9 and on the decision demo.
