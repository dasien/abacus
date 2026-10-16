# The Abacus demo

Abacus ships two demos. The **two-repo demo** builds up in stages: first **one reliable worker**, then **one
orchestrator moving one dependency across a repository boundary**. The **decision demo** shows a worker stopping
to ask you a product question. After setup, a two-repository run takes about **6 minutes** when everything works.
The value isn't the speed. It's that every handoff is verified and every decision is recorded.

## 0. Before you start (once per machine)

The quickest route is [GETTING-STARTED.md](GETTING-STARTED.md). In short:
1. **Install**: `./install.sh --workspace ~/Source/repos`. It's guided, and offers Beads, the `PATH` line and the
   status line. `~/.abacus/bin` on your `PATH` is required, because your own sessions call `abacus-*` commands.
2. **Create the demo**: `abacus demo setup` (details in step 1).
3. **Trust the folders**: `abacus trust` opens each Abacus folder Claude Code hasn't trusted yet. That's the two
   demo repos plus the agents' folders under `~/.abacus/agents/` (concierge, orchestrator, planner). Accept the prompt, then `/exit`.
   Trust is per path, so `abacus demo setup --force` doesn't ask again. Until a folder is trusted,
   `abacus-session start` refuses with `TRUST`.
4. **Check**: `abacus doctor` should be all `ok`.

Sessions run in Claude Code's **`auto`** permission mode by default. A repository can be promoted to
`bypassPermissions` only after its guards are ADOPTED and you accept Claude Code's disclaimer once
(`claude --dangerously-skip-permissions`). Until then the launcher refuses with `OPERATOR`.

## 1. What setup builds

```sh
abacus demo setup [--force]   # creates abacus-sandboxes/two-repo/ beside your workspace
abacus demo status            # doctor both repos + logbook digest + session liveness
```

Every demo is generated into one sandbox folder, `abacus-sandboxes/` beside your first workspace root (for
example `~/Source/repos/abacus-sandboxes/`). Setup makes it a workspace root, so the repo fence covers the demos.
Nothing in it is source: `--force` or `abacus demo reset` recreates it. The demos' starting files and beads live in
the abacus repository under `demos/<scenario>/` (a folder per repo, plus `scenario.json` for the beads), so you can
read or change a demo without touching the CLI.

```
abacus-sandboxes/two-repo/
  remotes/repo-a.git  remotes/repo-b.git    local bare "origins" (verification checks these)
  repo-a/   textkit: a tiny shared library (slugify)
  repo-b/   wc-report: a CLI that vendors textkit by exact commit (make sync-textkit REV=<sha>)
```

Both repos have a Beads board and have adopted Abacus: guards and redaction, git gates, workflows, skills,
`.abacus/config.json`, the memory server, and the CLAUDE.md block. Two beads are filed:

| Repo | Bead | Pipeline | Depends on |
|---|---|---|---|
| repo-a | Add `word_count(text)` to textkit | `pipeline:lite` | none |
| repo-b | Add `--words` using `textkit.word_count` | `pipeline:lite` | `WAITS-ON repo-a:<id>`: vendor only a commit verified on repo-a's origin |

A seed retro in repo-a ("consumer vendored a library from an unpushed commit") is harvested into shared memory.
That's exactly the mistake repo-b could make, so a good run cites it.

`abacus demo status` should show ADOPTED in both repos for:
- config, guards, workflows, skills, board, labels, gate, close-out-door
- instruction, memory-block, runs-ignored, consult

Two exceptions:
- `emit` is ADOPTED in repo-a, which has the seed retro, and NOT ADOPTED in repo-b until its first retro lands. Zero
  records is never read as green.
- `mutation-guide` is a candidate and stays NOT ADOPTED.

## 2. One reliable worker

An interactive session you drive works in place, so no worktree is needed:
```sh
cd ~/Source/repos/abacus-sandboxes/two-repo/repo-a
bd ready                       # note the bead id
claude
```
```
/abacus-run-bead <repo-a bead id>
```
Watch `/workflows` while `abacus-lite` runs:
1. **Board:** verify the board, sync with origin, claim.
2. **Implement.**
3. **Validate:** the gate runs under the heavy lock, then a fresh adversarial reviewer judges every acceptance
   criterion. There's at most one fix round. An incomplete review is re-asked rather than spending the fix round.
4. **Emit:** a retro, but only if a trigger fires.
5. **Finalize:** `abacus-finalize` commits with trailers, pushes through the pre-push gate, then closes the bead.

Check the result:
```sh
bd show <id>                                    # closed; the close reason gives evidence per criterion
git log -1 --format='%H%n%(trailers)'           # Bead:, Abacus-Pipeline:, Abacus-Session: trailers
abacus-verify --repo . --bead <id> --commit $(git rev-parse HEAD)
```
To see the guards work, ask the session to do something they block:
- `git push --force`
- edit `.claude/settings.json`
- write into `../repo-b`
- `cat .env`
- run `env`

Each is refused with a reason and logged in `~/.abacus/state/refusals.jsonl`. Secrets that reach tool output are
redacted before the model sees them, and `~/.abacus/state/redactions.jsonl` records counts only.

> Put the demo back (`abacus demo reset`) before the orchestrated run so the repo-a bead is open again.

## 3. The orchestrated run

### Option A: talk to the concierge (the normal way)
```sh
abacus chat                        # opens agent:concierge, starting it if needed (or switch to it in `claude agents`)
```
> Build repo-a-xxx, then repo-b-yyy which depends on it. I approve that order.

Use the two bead ids `abacus demo setup` printed (`abacus demo status` shows them again). Name the beads: a goal
without one ("start the orchestrator") makes the orchestrator come back and ask which work you meant.

The concierge records your words verbatim, starts the orchestrator on demand, and sends it a `HANDOFF`. The
orchestrator starts each repository's worker when it dispatches the first bead there, so you don't start any
sessions yourself. (`abacus demo start` starts the workers and the concierge ahead of time, which only saves the
first dispatch a few seconds.) Ask it
"what's going on?" at any time. With `abacus statusline enable`, every Claude Code session shows
`abacus · 1 in flight` / `abacus · 1 needs you` / `abacus · complete`.

### Option B: drive the orchestrator yourself
```sh
abacus-session start agent:orchestrator     # it starts the workers when it dispatches
claude agents                               # pick agent:orchestrator (attaching by name is ambiguous once old sessions are listed)
```
> Goal: build repo-a's word_count bead, then repo-b's --words bead that depends on it. Recover first, check the
> premise, and propose the sequence for my approval. Don't start until I approve.

### Option C: unattended, with the sequence pre-approved
```sh
abacus-session start agent:orchestrator --prompt '/recover first. Then here is the operator goal, to be recorded
verbatim as a ruling: "Build repo-a bead <A> (textkit word_count), then repo-b bead <B> (wc-report --words) which
waits on it. I approve the A-then-B sequence for this unattended demo run; do not wait for me to approve it. Any other
decision goes on the decisions page and you stop there." Then run it: dispatch, verify each report independently, hand
off to B only after A is verified, and finish with the program retrospective in retros/.'
```
The orchestrator can record your words as a ruling only because they appear in a genuine operator turn: the prompt
you launched it with. The human-only guard refuses anything it would put in your mouth.

The launcher refuses by named code if anything is off: `ROLE`, `ATTENDED`, `BUSY`, `UNSAVED`, `AUTHORITY`, `MODEL`,
`TRUST`, `OPERATOR`, `LAUNCH` if `claude --bg` itself fails, or `AGENT_VIEW` if `claude agents --json` fails
(so it can't tell whether the session is already running). Agent View failures are logged in
`~/.abacus/state/agent-view.log`; `ABACUS_DEBUG=1` prints every lookup. The orchestrator runs from `~/.abacus/agents/orchestrator` with no Edit or Write tools, and
starts with `/recover`.

## 4. What a good run looks like

A good run does this:

1. **Recover before acting.** It reads the logbook digest, live sessions and both boards, checks that shared memory
   loads, and challenges the premise. If memory is missing, it raises an OPERATOR STEP card and does not dispatch.
2. **Record and relay your ruling.** Your words go into the logbook verbatim, then onto both beads as a STANDING row.
   It then sends a `RULING` message to each worker. The logbook refuses to dispatch a bead whose worker was never
   sent the ruling (`UNRELAYED`).
3. **Consult memory.** Both dispatches cite the seed retro (`memory: repo-a:docs/retros/...`).
4. **Dispatch A.** The dispatch is recorded *before* the message is sent (`abacus-logbook show in-flight`). It states
   an outcome, checkable preconditions, and any `checks:` the verifier will run. It never says how to implement.
5. **The worker isolates and runs.** coder:repo-a enters a worktree named after the bead (Claude Code enforces this
   for background sessions), runs the lite workflow there, then removes the worktree after a verified close.
6. **Verify independently.** `abacus-verify` checks that:
   - the bead is closed on its own board
   - the commit is on origin and names the bead
   - nothing is unpushed, and the tree and the bead's worktree are clean
   - every dispatch check passes

   Only then is the dispatch `verified`.
7. **Hand off to B.** It dispatches only after A is verified (`--requires-verified`), with A's verified sha in the
   preconditions and a check that `vendor.json` pins it. Dispatching B any earlier is refused with `PREREQUISITE`.
8. **Stay quiet while waiting.** It subscribes to worker idle notifications instead of polling. Check-ins that find
   nothing wrong send nothing.
9. **Close out.** It closes the dispatches, stops the workers it started, writes a blameless program retrospective to
   `retros/`, and marks the decisions page COMPLETE.

Anything that needs you appears on `~/.abacus/agents/orchestrator/pages/decisions.md` as **NEEDS YOU**, with options,
a recommendation, a confidence level and a proposed review clause. Your answer is recorded verbatim before it is
acted on.

### Signs of trouble, and the curriculum they set
- the orchestrator drifts toward implementing
- a report conflicts with the board
- the dependency order lives only in conversation
- too many questions reach you
- a session sits idle for a long time

Each should become a system change: a fence, a verification step, an explicit wait, a clearer delegation, or a
disposable worker. Grow the fleet only once this two-repo run is boring, observable and recoverable.

## 5. The decision demo
This one shows what happens when a worker hits a product question it shouldn't answer itself.
```sh
abacus demo setup --scenario decision      # one repo, ledger, with one bead
abacus trust                               # if it names the new folders
abacus chat
```
> Build ledger-xxx.

Use the bead id setup printed (`abacus demo status --scenario decision` shows it again). The bead asks for an
`export` command whose default format, CSV or JSON, is left to you on purpose.

**You should see:**
1. The worker stops before building anything and reports `NEEDS-RULING`, with both options, a pro and a con for
   each, and a recommendation.
2. A **NEEDS YOU** card appears on the decisions page. The concierge tells you, and the status line shows
   `abacus · 1 needs you`.
3. You answer in the concierge, for example "CSV". Your words are recorded verbatim, relayed to the worker, and
   written on the bead as a JUDGEMENT row.
4. The worker builds it with your default. The orchestrator verifies the commit, then stops itself.

## 6. A real-code pilot: the heartbeat scenario
This scenario isn't one of the shipped demos: it needs your own checkouts of
[bitwarden/sdk-internal](https://github.com/bitwarden/sdk-internal) and
[dasien/bwcli-rs](https://github.com/dasien/bwcli-rs) (a Rust CLI that builds against the SDK). It shows how to run
Abacus on real code you can reset and rerun. It uses sandbox copies of both repositories, with the work from
[dasien/bwcli-rs#1](https://github.com/dasien/bwcli-rs/issues/1). An SDK bead adds `PlatformClient::heartbeat()`,
and a CLI bead adds `bw heartbeat`, which can't start until the SDK change is verified.
```sh
abacus demo setup --scenario heartbeat    # once: builds abacus-sandboxes/heartbeat/
abacus trust
abacus chat                                # tell it the line setup printed: "Build sdk-…, then bwcli-… …"
```
Setup copies the committed `HEAD` of your checkouts and never writes to them. If they aren't at
`<workspace parent>/bitwarden/`, pass `--sdk-repo` and `--cli-repo` once; they're remembered. Pushes go to local
bare remotes in `remotes/`, so nothing reaches GitHub. Both repos share one cargo build folder, `target/`.

**Running it again.** Each run changes the repos and boards, so put them back between runs:

| You want to | Run | Time |
|---|---|---|
| rerun the same work (most common) | `abacus demo reset --scenario heartbeat` | seconds |
| test bead filing from the issue | `abacus demo reset --scenario heartbeat --empty-boards` | seconds |
| pick up new commits from your real checkouts | `abacus demo setup --scenario heartbeat --force` | ~2 min |

A reset:
- stops the scenario's sessions, discarding their unsaved work
- archives the logbook and decisions page as `~/.abacus/state/logbook-heartbeat-N.db` and
  `state/archive/heartbeat-N/`, so you can compare runs
- removes workers' worktrees and puts both repos and their remotes back to the `pilot-baseline` tag
- restores both boards from `baseline/`, with the same bead ids, so the first message stays the same
- keeps the build cache

Shared memory is not reset, so lessons from earlier runs' retros carry into later runs. `abacus demo reset` works
for the other scenarios too, where it archives the run and recreates the demo.

### Planning it instead of filing by hand
The heartbeat's two beads were filed by hand. To have the planner do it:
```sh
abacus demo setup --scenario heartbeat --force     # once after 0.7.0, so the repos get the current filing rules
abacus demo reset --scenario heartbeat --empty-boards
abacus chat
```
> plan https://github.com/dasien/bwcli-rs/issues/1

**You should see:**
1. The concierge records your words and starts the planner (`agent:planner`, visible in `claude agents`).
2. The planner reads the issue and both repos, then drafts an SDK bead and a CLI bead that waits on it.
3. A plan review appears in the concierge: each draft, its criteria, the order, and a proposed label with a reason.
4. You answer, for example "approve", or "make the SDK one full, then approve". The planner applies exactly that.
5. "Build dasien/bwcli-rs#1" then runs both, SDK first.

`abacus-board find "dasien/bwcli-rs#1"` shows the drafts and their state on both boards at any point.

## 7. Two lanes at once
The two-repo demo and the decision demo share no repositories, so they can run side by side as two lanes:
```sh
abacus demo setup && abacus demo setup --scenario decision    # if they aren't set up already
abacus trust
abacus chat
```
Send the two requests as separate messages, so the concierge sees two pieces of work:
> Build repo-a-xxx, then repo-b-yyy which depends on it. I approve that order.

> Build ledger-zzz.

**You should see:** the concierge starts two lanes and names each (for example `textkit` and `ledger`), with two
orchestrators in `claude agents` (`agent:orchestrator-<lane>`). Ask "how are we doing with the ledger work?": the
answer covers only that lane, including its NEEDS YOU card about the export format. "How are we doing?" gives a line
per lane, and the status line reads `abacus · 2 lanes · …`. Each lane closes and its orchestrator stops when its work
is done.

The heartbeat scenario (§6) pairs with the two-repo demo the same way. Its Rust gates take turns with the other
lane's gates on the machine-wide heavy lock, so expect the pair to take longer than either alone; that wait is the
lock protecting the machine, not the lanes interfering.

## 8. Stopping and cleaning up
```sh
abacus demo stop                           # or: abacus-session stop <name>
```
Agent View keeps a record of every session after it stops, and labels one stopped mid-turn as "working", so old
orchestrators can look as if they're still running. `abacus prune` removes those records. It never touches a running
session, keeps the most recent stopped one per role (`--keep N`), and `--dry-run` shows what would go.

`stop` refuses with `UNSAVED` while a session's checkout or any of its worktrees has uncommitted or unpushed work. A
worker keeps its worktree on escalation, so the saved patch survives. `--force-unsaved` ends the session anyway; it
never deletes files.

## Useful commands while it runs
```sh
abacus-logbook digest                      # one-screen state, incl. unrecorded/unrelayed rulings
abacus-logbook show in-flight              # dispatches, status, checks
abacus-logbook show reports                # reports and whether each was verified
abacus-logbook show rulings                # your words, verbatim, and where they were recorded
abacus-logbook show rulings-unrelayed      # rulings a dispatched worker was never sent
abacus-session list                        # Agent View reconciled with the logbook
claude logs coder:repo-a                   # a worker's recent output
tail -f ~/.abacus/state/refusals.jsonl     # guard refusals: review and classify them
```

## Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `REFUSED TRUST` | Claude Code hasn't trusted that folder | run `claude` there once and accept |
| `command not found: abacus-board` (or another `abacus-*`) in your session | `~/.abacus/bin` is not on your `PATH` | step 0.1 |
| Orchestrator raises "restore shared memory" | `consult_memory` didn't load | sessions started with `abacus-session` get the memory server passed explicitly; check `abacus-memory status` |
| `REFUSED UNRELAYED` on dispatch | a ruling covering the bead wasn't sent to that worker | `/relay-ruling`; `abacus-logbook show rulings-unrelayed` |
| `REFUSED UNSAVED` on stop | uncommitted or unpushed work in the checkout or a worktree | let the worker report, or `--force-unsaved` (keeps files) |
| exit 75 on push | heavy-lock contention, not a failing gate | retry |
