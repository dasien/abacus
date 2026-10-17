# Abacus end to end

You install once and add each repository, then do everything else by talking to the concierge. The diagrams show the path from your side, and each step has its own section below.

## Overview

The whole path, from install to results and back to the concierge for the next request.

```mermaid
flowchart TD
    I["<b>Install</b><br/>./install.sh --workspace &lt;root&gt;"] --> A["<b>Add a repo</b><br/>abacus add &lt;repo&gt;"]
    A --> T["<b>Trust</b><br/>abacus trust"]
    T --> C["<b>Chat</b><br/>abacus chat"]
    C -->|"plan &lt;issue, file or text&gt;"| P["<b>Plan</b><br/>the planner drafts beads"]
    P --> V["<b>Review the plan</b><br/>drafts, order, proposed sizes"]
    V -->|"change it"| P
    V -->|"approve"| B["<b>Build</b><br/>build &lt;source or bead&gt;"]
    C -->|"build &lt;bead&gt;"| B
    B --> W["<b>Watch</b><br/>status line, abacus status,<br/>'how are we doing?'"]
    W -->|"NEEDS YOU card"| D["<b>Decide</b><br/>answer in the concierge"]
    D --> W
    W -->|"program complete"| R["<b>Result</b><br/>push: verified commits on the default branch<br/>draft-pr: draft PRs you review and merge"]
    R --> L["<b>Learn</b><br/>harvested retros feed<br/>shared memory"]
    L -.-> C
```


## A typical "plan, then build" request

What passes between you, the concierge, the rest of Abacus and the repository, including where you are asked to decide.

```mermaid
sequenceDiagram
    participant U as User
    participant C as Concierge
    participant A as Abacus (planner, orchestrator, workers)
    participant G as GitHub / repo
    Note over U,G: Plan
    U->>C: "plan dasien/bwcli-rs#35;1"
    C->>A: hand off to the planner
    A->>A: draft beads on every repo involved
    A->>C: plan review: drafts, order, proposed sizes
    Note over U,G: Review the plan
    C->>U: shows the plan
    U->>C: "approve" (or "make the SDK one full, then approve")
    C->>A: approval, recorded in your words
    A->>C: plan applied
    Note over U,G: Build
    U->>C: "build dasien/bwcli-rs#35;1"
    C->>U: "Recorded. I'll ask the orchestrator to build it."
    C->>A: hand off to the orchestrator (started on demand)
    Note over U,G: Watch
    loop each bead, in dependency order
        A->>A: dispatch to the repo's worker, which builds, tests and reviews
        alt worker hits a question only you can answer
            Note over U,A: Decide
            A-->>C: NEEDS YOU card (status line shows "1 needs you")
            C->>U: question, options, recommendation
            U->>C: "CSV"
            C->>A: your words, relayed verbatim, and the worker resumes
        else worker cannot finish cleanly
            A->>A: nothing committed, patch saved, orchestrator re-sequences or files a follow-up
            A-->>C: or a NEEDS YOU card when it is outside its authority
        end
        A->>G: push the commit (push) or open a draft PR (draft-pr)
        A->>G: verify the commit landed before starting beads that wait on it
    end
    Note over U,G: Result
    A-->>C: program complete
    C->>U: done, every bead closed and verified
    U->>G: review and merge the draft PRs (draft-pr only)
```


## Steps

### Install

Run `./install.sh --workspace <root>` once, with the four repositories cloned side by side. See [Getting started, step 2](GETTING-STARTED.md#2-install-3-min).

### Add a repo

Run `abacus add <repo>` and confirm what it proposes. See [Getting started, step 3](GETTING-STARTED.md#3-bring-your-own-repository-in-optional-now-3-min), and [Draft-PR landing](DRAFT-PR-LANDING.md) for the `landing` setting.

### Trust

Run `abacus trust` and accept Claude Code's trust prompt in each folder it opens. See [Getting started, step 4](GETTING-STARTED.md#4-create-the-demo-and-trust-its-folders-3-min).

### Chat

Run `abacus chat` and say what you want in plain language. See [Getting started, step 5](GETTING-STARTED.md#5-ask-abacus-to-do-the-work-5-min).

### Plan

Say "plan" with a GitHub issue, a local file or pasted text. See [How you talk to it](CONCEPTS.md#how-you-talk-to-it).

### Review the plan

Approve the drafts, their order and proposed sizes, or say what to change. See [Authority boundary](CONCEPTS.md#authority-boundary-starting-position).

### Build

Say "build" with the source or a bead, and Abacus runs it and everything it depends on, in order. See [How you talk to it](CONCEPTS.md#how-you-talk-to-it).

### Watch

Use the status line, `abacus status`, or ask the concierge "how are we doing?". See [Where to look afterwards](GETTING-STARTED.md#where-to-look-afterwards).

### Decide

Answer a NEEDS YOU card in the concierge, and your words reach the worker verbatim. See [How you talk to it](CONCEPTS.md#how-you-talk-to-it).

### Result

With `push`, each bead's commit is on the default branch; with `draft-pr`, each bead ends at a draft PR you review and merge. See [Draft-PR landing](DRAFT-PR-LANDING.md).

### Learn

Run `abacus-memory harvest-me` in a repo to add its retros and closed beads to shared memory. See [The pieces](CONCEPTS.md#the-pieces).
