# Getting started with Abacus (about 15 minutes)

This is the shortest path from nothing to watching Abacus build a change across two repositories. Each step says
what you should see. If you don't see it, `abacus doctor` tells you what's missing and how to fix it.

## 1. Prerequisites 
You need Python 3.9+, git, and Claude Code (`claude update`). Beads is installed for you in step 2 if it's missing
and you have Homebrew; otherwise `npm install -g @beads/bd`.

Abacus is tested on **macOS**. **Linux** should work but hasn't been tested yet (Abacus is plain Python, git and
Claude Code; the open question is Claude Code's background sessions and Agent View there). On **Windows**, use WSL;
that's untested too. If a prerequisite is missing, the installer and `abacus doctor` say how to install it on your
system.

## 2. Install (3 min)
Clone the four repositories side by side, then run the installer:
```sh
cd ~/Source/repos            # anywhere you keep repositories
for r in abacus abacus-standards abacus-infra abacus-agents; do git clone https://github.com/dasien/$r.git; done
cd abacus && ./install.sh --workspace ~/Source/repos
```
The installer:
- checks prerequisites and offers to install Beads
- publishes the Abacus tools to `~/.abacus`
- deploys the agents: concierge, planner and orchestrator
- offers to add `~/.abacus/bin` to your `PATH`
- offers to turn on the Abacus status line
- links `abacus` into a folder already on your PATH, so it works in the same terminal
- runs `abacus doctor` and ends with a numbered list of anything left to do

Pass `--yes` to accept every offer.

**You should see:** the doctor's results, every line `ok` except possibly `folders trusted` (next step) and the
optional status line, then `Remaining steps:` listing at most "trust these folders". You can keep using the same
terminal. Run `abacus doctor` again any time.

## 3. Bring your own repository in (optional now, ~3 min)
```sh
abacus add ~/Source/repos/myCodeRepo
```
It creates the repository's Beads board and works out the test commands from its committed build files (Makefile
`gate`/`test` targets, `package.json`, `Cargo.toml`, `go.mod`, .NET, Python, or CMake presets and CTest), and asks
you to confirm them; if it finds none, it asks you for them. It runs the quick check once, since every commit will,
and stops before changing anything if it fails. Then it installs Abacus's conventions, shows you the changes and the
repository's doctor, asks before committing, registers the worker, and asks before pushing and opening the trust
prompt. If it stops partway, run it again: it carries on. The worker is named after the folder, in lowercase with
hyphens (`6502 Kernel` becomes `coder:6502-kernel`). Inside the repository, `abacus doctor` checks it too.
The demo below shows what a run looks like before you point Abacus at your own code.

## 4. Create the demo and trust its folders (3 min)
```sh
abacus demo setup
abacus trust
```
`abacus demo setup` creates two small repos with one task each. `abacus trust` opens Claude Code in each Abacus
folder it hasn't trusted yet. For each one: accept the trust prompt, then type `/exit`. Claude Code asks this once
per folder, and Abacus never answers it for you.

**You should see:** `abacus doctor` reports every folder trusted (`folders trusted … N/N`).

## 5. Ask Abacus to do the work (5 min)
```sh
abacus chat            # opens the concierge, starting it if needed
```
Then tell it the line `abacus demo setup` printed, with your two bead ids:
> Build repo-a-xxx, then repo-b-yyy which depends on it. I approve that order.

Naming the beads matters: the concierge passes your exact words on, and a goal without a bead costs the
orchestrator an extra question back to you.

**You should see:**
- The concierge records your words and starts the orchestrator, which starts a worker in each repository.
- About 5–7 minutes later, both tasks are verified and done.

Ask the concierge "what's going on?" any time. Give it unrelated work while this runs and it opens a second, named
**lane** with its own orchestrator; "how are we doing with <that work>?" then answers for that lane only
([DEMO.md](DEMO.md) §7). With the status line on, every Claude Code session shows
`abacus · 1 in flight` → `abacus · complete`.

## Where to look afterwards
| You want to… | Do this |
|---|---|
| talk to Abacus | `abacus chat`, or switch to `agent:concierge` in `claude agents` |
| see how it's going | ask the concierge "how are we doing?", or glance at the status line |
| see what needs you | ask the concierge "what needs me?" |
| plan new work | tell the concierge "plan <issue link or file path>"; you review the drafts there |
| watch a worker | `claude agents` → pick `coder:repo-a` (`/workflows` shows the current stage) |
| stop everything | `abacus demo stop` |
| get the latest Abacus | `abacus update` (`--check` shows what's new first) |

Next: try the decision demo (`abacus demo setup --scenario decision`), where a worker stops to ask you a product
question; see [DEMO.md](DEMO.md#5-the-decision-demo). [DEMO.md](DEMO.md) also explains what happened at each step,
and `abacus add <path>` (step 3) brings a real repository in.
