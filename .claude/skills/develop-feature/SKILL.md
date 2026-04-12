---
name: develop-feature
description: >
  Orchestrate the full agent team (project manager, developer, tech lead, QA
  analyst) to develop a feature end-to-end: specs → task planning → TDD
  implementation → code review → QA validation.
argument-hint: "<feature description>"
disable-model-invocation: true
allowed-tools: Agent, Read, Write, Glob, Grep, Bash
---

# Develop Feature: $ARGUMENTS

Orchestrate the agent team to take "$ARGUMENTS" from specs to a validated,
reviewed implementation. Follow the phases below in strict order.

---

## Prerequisite: Agent Teams

This workflow uses **Claude Code Agent Teams** — each agent runs as an
independent teammate in its own context window, coordinating via a shared
task list and direct messaging.

Agent Teams requires the experimental flag:
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

If this flag is not set in the current environment, stop and instruct the
user to restart the session with the flag enabled:
```bash
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude
```

If the flag is set, proceed.

---

## Source of Truth

Before any work begins, agents must read and internalize these documents:

| Document | Path | Role |
|----------|------|------|
| Functional spec | `specs/FUNC_SPEC.md` | **What** the system does — requirements, acceptance criteria |
| Technical spec | `specs/TECH_SPEC.md` | **How** to build it — stack, architecture, data models, API contracts |
| Project rules | `CLAUDE.md` | Conventions, build/test commands, commit format |
| UI mockups | `specs/mockups/*.html` | Visual source of truth for frontend work |

Every task, review, and QA check must trace back to a requirement in these
documents. If a gap is found, surface it — don't guess.

---

## Tech Stack Reference

Agents must use the correct tools for this project:

| Concern | Backend | Frontend |
|---------|---------|----------|
| Language | Python 3.11+ | TypeScript 5.5+ |
| Framework | FastAPI 0.115.6 | Vue 3.5 + Vite 6 |
| Tests | `pytest tests/backend/ -v` | `cd frontend && npm run test` |
| Lint | `ruff check backend/ tests/` | `cd frontend && npx eslint src/` |
| Format | `ruff format backend/ tests/` | `cd frontend && npx prettier --check src/` |
| Type check | (ruff covers basics) | `cd frontend && npx vue-tsc --noEmit` |
| DB migrations | `alembic upgrade head` | N/A |
| Dev server | `python run.py` | `cd frontend && npm run dev` |

---

## Phase 1 — Planning

Create an agent team for the feature "$ARGUMENTS". Spawn one teammate using
the `project-manager` agent:

> "I need to plan the development of: $ARGUMENTS
>
> You are the project manager. Read these documents first:
> - `specs/FUNC_SPEC.md` — functional requirements
> - `specs/TECH_SPEC.md` — technical architecture, data models, API contracts
> - `CLAUDE.md` — project conventions
>
> Produce a task board in the `tasks/` directory. Each task must list:
> - The files it will create or modify (file ownership)
> - Its dependencies on other tasks
> - Whether it's backend, frontend, or full-stack
> - Acceptance criteria derived from the specs (cite FR numbers or section refs)
>
> Ensure no two tasks with overlapping file ownership are scheduled
> concurrently — conflicting tasks must be serialized via explicit
> dependencies.
>
> When the task board is ready, post a message with: PLANNING_DONE"

**Wait** until the project-manager teammate posts `PLANNING_DONE`.

Read `tasks/BOARD.md` to load the task plan. Present it to the user and
**wait for explicit approval** before proceeding. If the user requests
changes, relay them to the project-manager teammate and wait for an updated
board.

---

## Phase 2 — Implementation Loop

This phase repeats until all tasks on the board are `done`.

### 2a. Identify the ready wave

From `tasks/BOARD.md`, identify all tasks with status `todo` whose
dependencies are all `done`. These tasks form the **current wave** and may
be worked on concurrently.

If no tasks are `todo` but some are `in_progress` or `blocked`, wait for
those to resolve before continuing.

### 2b. Implement each ready task

For each task in the current wave, spawn a `developer` teammate:

> "Implement task $TASK_ID: $TASK_TITLE
>
> Read the full task specification in `tasks/$TASK_ID.md` before writing
> any code. Also read `specs/TECH_SPEC.md` for architecture and API
> contracts, and `CLAUDE.md` for project conventions.
>
> Follow TDD: write the tests first, confirm they fail, then implement.
>
> Stack specifics:
> - Backend tests: `pytest tests/backend/ -v`
> - Frontend tests: `cd frontend && npm run test`
> - Backend lint: `ruff check backend/ tests/`
> - Frontend lint: `cd frontend && npx eslint src/`
> - If touching database models, create an Alembic migration.
> - For frontend work, reference mockups in `specs/mockups/` for the
>   target look-and-feel.
>
> When all acceptance criteria are met and the full test suite passes, post:
> TASK_DONE $TASK_ID"

Tasks in the same wave have no file overlap, so they can run in parallel.

**Wait** until all teammates in this wave post `TASK_DONE <id>`.

### 2c. Review each completed task

For each task that posted `TASK_DONE`, spawn a `tech-lead` teammate:

> "Review the implementation of task $TASK_ID: $TASK_TITLE
>
> Read `tasks/$TASK_ID.md` for the spec requirements and acceptance
> criteria. Review the changed files thoroughly. Check:
>
> **Correctness**
> - Does the implementation match the spec requirements? (cite FR numbers)
> - Are edge cases from `specs/FUNC_SPEC.md` section 5.e handled?
> - Do API responses match the Pydantic schemas in `specs/TECH_SPEC.md` section 5?
>
> **Architecture**
> - Does code respect the layered architecture? (routers → services → repositories)
> - Are external API calls isolated in `backend/clients/`?
> - Is the concurrency model correct? (asyncio, no blocking I/O on the event loop)
>
> **Security**
> - Auth enforcement on all protected endpoints?
> - Input validation at system boundaries?
> - No secrets in code or logs?
>
> **Test quality**
> - Are tests meaningful (not just smoke tests)?
> - Do tests cover the acceptance criteria from the task spec?
>
> **Frontend** (if applicable)
> - Does the UI match the mockups in `specs/mockups/`?
> - Is the component responsive?
> - TypeScript strict mode compliance?
>
> Run all automated checks:
> ```bash
> ruff check backend/ tests/
> pytest tests/backend/ -v
> cd frontend && npx vue-tsc --noEmit && npx eslint src/ && npm run test
> ```
>
> Write your findings (issues + overall verdict) to `tasks/$TASK_ID-review.md`.
>
> Then post one of:
> - APPROVED $TASK_ID  (no issues, or only low-severity nits already noted)
> - CHANGES_REQUIRED $TASK_ID  (medium or higher issues require fixes)"

**Wait** for the tech-lead's message.

### 2d. Handle the review verdict

**If `APPROVED $TASK_ID`:**

1. Relay to the project-manager teammate:
   > "Mark task $TASK_ID as done."
2. Project manager updates `tasks/BOARD.md` (status → `done`).
3. Project manager identifies newly unblocked tasks and updates their
   status to `todo`.
4. Continue the loop (go back to 2a).

**If `CHANGES_REQUIRED $TASK_ID`:**

1. The tech-lead's issues are in `tasks/$TASK_ID-review.md`. Read them.
2. Relay the issues to the developer teammate that worked on this task:
   > "The tech lead has requested changes on task $TASK_ID.
   > Read `tasks/$TASK_ID-review.md` for the full list of issues.
   > Address every issue. When done and the test suite passes, post:
   > TASK_DONE $TASK_ID"
3. **Wait** for another `TASK_DONE $TASK_ID` message.
4. Go back to step 2c for another review pass.

Repeat 2c → 2d until `APPROVED` is received for this task.

---

## Phase 3 — QA Validation

This phase may repeat. It loops back to Phase 2 whenever QA finds failures.

### 3a. Completeness check

Relay to the project-manager teammate:
> "All tasks are done. Cross-check the task board against the specs:
> - `specs/FUNC_SPEC.md` — every FR-xxx requirement
> - `specs/TECH_SPEC.md` — every API endpoint, data model, edge case
>
> Confirm every requirement has been covered by at least one task.
> Report any gaps.
> Post: COVERAGE_OK if complete, or COVERAGE_GAPS if something is missing."

Wait for the project manager's message. If `COVERAGE_GAPS`, the PM should
file new tasks for the uncovered requirements. Restart Phase 2 for those
tasks, then return here.

### 3b. Automated test suite

When the project manager posts `COVERAGE_OK`, run the full automated
test suite:

```bash
# Backend
ruff check backend/ tests/
ruff format --check backend/ tests/
pytest tests/backend/ -v --tb=short

# Frontend
cd frontend
npx vue-tsc --noEmit
npx eslint src/
npx prettier --check src/
npm run test
```

If any check fails, file the failure as a bug task and restart Phase 2
for that task.

### 3c. Functional QA

Spawn the `qa-analyst` teammate:

> "All development tasks for '$ARGUMENTS' are complete and automated tests
> pass. Perform a functional QA session.
>
> **Setup:**
> 1. Start the backend: `python run.py`
> 2. Start the frontend dev server: `cd frontend && npm run dev`
> 3. Read `specs/FUNC_SPEC.md` for expected behaviors and acceptance criteria.
> 4. Read `specs/mockups/*.html` for the target visual design.
>
> **Backend API validation:**
> For every API endpoint defined in `specs/TECH_SPEC.md` section 4:
> - Send valid requests and verify response shapes match Pydantic schemas.
> - Send invalid requests and verify error responses (400, 401, 404, 422).
> - Test auth enforcement: hit protected endpoints without a token → 401.
> - Test edge cases: empty data, boundary values, concurrent requests.
>
> **Frontend validation:**
> Use the browser MCP (if available) or manual inspection to verify:
> - Each view renders correctly and matches the mockups.
> - Navigation flows work (login → dashboard → wallet detail → settings).
> - Responsive layout at desktop (1280px) and mobile (375px) widths.
> - Charts render with data and handle empty states.
> - WebSocket real-time updates work (add wallet → dashboard refreshes).
> - Error states display correctly (API down, invalid input, etc.).
>
> **Integration flows** (from `specs/TECH_SPEC.md` section 9.2):
> - Full user journey: setup → login → add wallet → refresh → dashboard → edit tag → remove → logout.
> - Background refresh: add wallet, wait for scheduler tick, verify new snapshots.
> - Stale data resilience: mock external API failures, verify cached data shown with warning.
>
> Write a QA report to `qa-report.md` with:
> - Test case, expected result, actual result, pass/fail for each check.
> - Screenshots or curl output for any failures.
>
> Post: QA_DONE"

Wait for `QA_DONE`.

### 3d. QA report → PM

Read `qa-report.md`. Relay the full report to the project-manager teammate:
> "The QA analyst has completed testing. Here is the report:
> <contents of qa-report.md>
>
> For each failure, determine whether it requires a developer fix or a spec
> clarification. For failures requiring a fix:
> - Create a new task in `tasks/` with the failure description, the
>   affected files, and the acceptance criterion (QA test must pass).
> - Add it to `tasks/BOARD.md` with status `todo`.
>
> Post: QA_PASSED if there are no failures requiring fixes.
> Post: QA_FIXES_NEEDED if new fix tasks were created."

Wait for the project manager's message.

### 3e. Act on the PM's verdict

**If `QA_PASSED`:** proceed to Phase 4.

**If `QA_FIXES_NEEDED`:**
1. The PM has added new fix tasks to the board. Restart **Phase 2** for
   those tasks (implement → review → approve loop).
2. Once all fix tasks are `done`, return to **Phase 3b** for another QA
   run.

Repeat Phase 3b → 3c → 3d → 3e until `QA_PASSED`.

---

## Phase 4 — Completion

QA has passed with no outstanding failures.

1. Present the final summary to the user:
   - Features implemented (task list with FR references)
   - Test results: backend (pytest) and frontend (vitest) pass counts
   - QA result summary
   - Any spec gaps discovered during development or QA
   - Any deferred items

2. Prompt the user to review and commit. Follow the project's conventions:
   - Conventional Commits format: `feat:`, `fix:`, `refactor:`, `test:`, etc.
   - One-liner messages, no co-author info.
   - Update `CLAUDE.md` if the change affects project structure, build
     commands, key dependencies, or development workflows.

---

## State & Communication Reference

| File | Written by | Read by | Purpose |
|------|-----------|---------|---------|
| `tasks/BOARD.md` | project-manager | all | Task status, ownership, dependencies |
| `tasks/<id>.md` | project-manager | developer, tech-lead | Full task spec |
| `tasks/<id>-review.md` | tech-lead | developer, PM | Issues and verdict |
| `qa-report.md` | qa-analyst | PM, user | QA test results |

All inter-agent communication beyond file writes happens via the Agent
Teams mailbox using the signal keywords above:

| Signal | Posted by | Meaning |
|--------|-----------|---------|
| `PLANNING_DONE` | project-manager | Task board is ready for review |
| `TASK_DONE <id>` | developer | Task implemented, tests passing |
| `APPROVED <id>` | tech-lead | Task passes review |
| `CHANGES_REQUIRED <id>` | tech-lead | Task has issues, developer must fix |
| `COVERAGE_OK` | project-manager | All spec requirements covered by tasks |
| `COVERAGE_GAPS` | project-manager | Spec gaps found, new tasks filed |
| `QA_DONE` | qa-analyst | QA session complete, report written |
| `QA_PASSED` | project-manager | No QA failures require fixes |
| `QA_FIXES_NEEDED` | project-manager | Fix tasks created, Phase 2 restart needed |
