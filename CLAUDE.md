# CryptoDash

<!-- One-paragraph description of what this project is and who it's for. Update as scope solidifies. -->

## Project Structure

```
cryptodash/
├── .claude/
│   └── skills/            # Claude Code skills (invoke with /skill-name)
│       ├── generate-func-spec/   # /generate-func-spec — functional spec from a brief
│       └── generate-tech-spec/   # /generate-tech-spec — tech spec from a func spec
├── specs/                 # All design artifacts (specs + mockups)
│   ├── FUNC_SPEC.md       # What the system does
│   ├── TECH_SPEC.md       # How to build it
│   ├── TECH_NOTES.md      # Research notes and decision points
│   └── mockups/           # Interactive HTML mockups (visual source of truth for UI)
└── ...                    # To be defined — update this tree as code is added
```

Read `specs/` for detailed functional and technical specs before implementing features. UI mockups in `specs/mockups/` are the visual source of truth — open them in a browser to see the target look-and-feel.

## Build & Run

<!-- Fill in as the tech stack is chosen -->
- Build: `TODO`
- Run: `TODO`
- Test: `TODO`
- Lint: `TODO`

## Git & Remote

- **Hosted on GitLab** (private): `gitlab.com:lukius/cryptodash`
- Use `glab` (not `gh`) for all remote operations: MRs, issues, CI, etc.
- Example: `glab mr create`, `glab issue list`, `glab ci status`

## Development Rules

### Testing — non-negotiable
- **Always run the full test suite after making changes.** Do not accept code that makes tests fail.
- Add new unit and/or functional tests for every new feature or bug fix.

### Commits
- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- One-liner messages, no co-author info.

### After touching code
- Run tests.
- Update this CLAUDE.md if the change affects project structure, build commands, key dependencies, or development workflows.

### About this file
- **Keep it under 200 lines.** If it's growing past that, something belongs elsewhere or can be removed.
- **Only non-obvious information.** If the code, tests, or commit history already describe it, it should not be here. This file is for context that a reader *cannot* derive by reading the source: the *why* behind decisions, implicit conventions, trust boundaries, known traps, and anything that would otherwise live only in someone's head.

## Key Design Decisions

<!-- Record non-obvious architectural and product decisions here. Each entry should explain WHAT was decided and WHY — the kind of context that isn't obvious from reading the code. Examples:

- Why a particular library was chosen over alternatives
- Security boundaries and trust model
- Intentional limitations or trade-offs
- Data flow decisions that affect multiple components
- Conventions that differ from framework defaults
-->

## Caveats & Gotchas

<!-- Add entries here as they come up during development. Things that tripped you up, non-obvious behavior, workarounds for known issues. -->
