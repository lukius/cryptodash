# Generate Technical Specification

You are a senior software architect. Your task is to produce a **comprehensive technical specification** from a functional specification. The tech spec must be detailed and unambiguous enough that a developer (or coding agent) can implement every feature correctly without asking follow-up questions.

---

## Input

You will receive:

1. **Functional specification** — the file passed as argument (e.g., `specs/FUNC_SPEC_SERVER.md` or `specs/FUNC_SPEC_CLIENT.md`). This describes **what** the system does, not **how**. This is your primary source of truth.
2. **Project conventions** — read `CLAUDE.md` at the repository root for build commands, project structure, and design decisions.

Read both documents thoroughly before producing any output.

---

## Output

Write a single Markdown file (`specs/TECH_SPEC_SERVER.md` or `specs/TECH_SPEC_CLIENT.md`, matching the input) that covers every section below. Be exhaustive. Prefer concrete decisions over options. When the functional spec is silent on an implementation detail, first consider whether the gap warrants a clarifying question (see "Ask Questions First" above). If it does not — i.e., the choice is low-risk and unlikely to cause rework — make a clear, justified choice and document it in the Ambiguity Resolution Log.

---

## Required Sections

### 1. Technology Stack

- **Language and version**: exact version (e.g., Go 1.22+, Kotlin 2.0+).
- **Minimum platform version**: e.g., Android API level with justification.
- **Frameworks**: name, version constraints, and why each is chosen.
- **Libraries/dependencies**: complete list with group/artifact/version. For each dependency state:
  - What it does in this project.
  - Why it was chosen over alternatives.
- **Build system and toolchain**: build tool (go build, Gradle), plugin versions, build variants.
- **Development tools**: linter, formatter, test framework.

### 2. Architecture Overview

- **Architectural pattern**: e.g., layered, hexagonal, MVI, MVVM — state the pattern and justify it.
- **High-level component diagram**: describe the major components/modules and their relationships in text (ASCII diagram or structured list). Show data flow direction.
- **Component responsibility table**: for each component, one-line description of its single responsibility.
- **Threading/concurrency model**: which components run on which threads/goroutines/coroutine dispatchers, and how they communicate.

### 3. Project Structure

- **Complete directory and file layout**: every package, directory, and source file that will exist. Use a tree diagram. Group by layer/feature.
- **Naming conventions**: files, packages, classes, functions — state the convention and give examples.
- **Module/package boundaries**: what each package exposes, what it keeps internal.

### 4. Component Specifications

For **each** component identified in section 2, provide:

#### 4.a Interface and Contract
- Public API: every exported function, method, struct, class, or interface with full signatures (parameter names, types, return types).
- Preconditions and postconditions for each function.
- Error types and when each is returned.

#### 4.b Internal Design
- Key data structures with field definitions.
- State machine descriptions where applicable (with states and transitions).
- Algorithms or non-trivial logic — describe step by step.

#### 4.c Code Snippets
- Provide concrete, compilable code snippets for:
  - Component initialization and wiring.
  - Core logic (e.g., path resolution, token validation, discovery response construction).
  - Error handling patterns.
  - Concurrency patterns (mutex usage, coroutine scope setup, channel usage).
- Snippets must use the exact libraries and APIs from section 1. No pseudocode.

#### 4.d Edge Cases
- List every edge case the component must handle.
- For each, state the expected behavior and which test should cover it.

### 5. Data Models

- **Every struct, class, data class, and enum** used across the system, with:
  - Field names, types, nullability, default values.
  - JSON serialization/deserialization details (field names, custom adapters if any).
  - Validation rules.
- **API request/response schemas**: full JSON structure for every HTTP endpoint and UDP message, including all possible fields and error shapes.

### 6. Configuration and CLI

- **Every CLI flag/argument**: name, type, default, validation rules, error message on invalid input.
- **Configuration precedence**: CLI flags > environment variables > defaults (or whatever applies).
- **Startup sequence**: ordered list of every step from binary invocation to "ready to serve", including validation, resource allocation, and listening.

### 7. Error Handling Strategy

- **Error taxonomy**: categorize all errors (user input, network, filesystem, internal).
- **Per-layer error handling**: how errors propagate through each layer. Which layer logs, which transforms, which returns to the caller.
- **Error response format**: exact JSON structure for every HTTP error status.
- **Logging**: what gets logged at each level (INFO, WARN, ERROR), with format examples.
- **Retry and recovery**: which operations are retried, how many times, with what backoff.

### 8. Security Considerations

- **Path traversal prevention**: exact algorithm, step by step.
- **Input validation**: every point where external input enters the system and what validation is applied.
- **TLS configuration**: cipher suites, minimum version, certificate handling.
- **Authentication flow**: step-by-step token lifecycle (creation, validation, expiry, cleanup).
- **Secrets handling**: how passwords, tokens, and keys are stored and protected in memory.

### 9. Testing Strategy

- **Unit tests**: list the test files and the functions/behaviors they cover. For each test, describe the scenario in one line.
- **Integration/functional tests**: end-to-end scenarios that must pass.
- **Test fixtures**: what test data and helpers are needed.
- **Edge case tests**: derived from section 4.d — every edge case must have a corresponding test.
- **How to run**: exact commands.

### 10. Ambiguity Resolution Log

Go through the functional spec section by section. For every point where the functional spec is ambiguous, underspecified, or leaves an implementation choice open:

- **Quote** the relevant part of the functional spec.
- **State the ambiguity** clearly.
- **Decide** on the concrete implementation approach.
- **Justify** the decision.

This section is critical — it prevents implementers from making inconsistent ad-hoc choices.

---

## Ask Questions First

Before writing the tech spec, carefully review the functional spec for **blind spots, contradictions, and underspecified areas**. You are strongly encouraged to **stop and ask the user questions** before proceeding when you encounter any of the following:

- **Contradictions**: two parts of the spec that imply incompatible behaviors.
- **Blind spots**: scenarios the spec doesn't address at all (e.g., what happens if X fails mid-Y? what if the input is empty/huge/malformed?).
- **Ambiguous requirements**: wording that could be reasonably interpreted in more than one way, where the wrong choice would lead to rework.
- **Missing constraints**: performance expectations, size limits, timeouts, or capacity bounds that aren't stated but matter for implementation.
- **Unstated dependencies**: interactions between features that the spec describes separately but that affect each other at implementation time.

**Do not silently guess.** If an ambiguity could lead to a meaningful implementation difference, ask. It is far cheaper to clarify now than to rewrite a tech spec or, worse, rework code later.

Present your questions grouped by spec section, with a brief note on why each matters. Once the user answers, incorporate the answers into the tech spec (and into the Ambiguity Resolution Log in section 10).

---

## UI Mockups (Final Step)

After the tech spec is written and reviewed, determine whether the project includes a **user-facing interface** (web UI, mobile app, CLI with rich output, etc.). If it does, create interactive HTML mockups before the implementation phase begins.

### When to create mockups

- The tech spec describes a frontend, dashboard, admin panel, or any visual interface.
- Skip this step for purely backend/library/API-only projects with no UI component.

### Process

1. **Ask the user for visual references.** Prompt: *"Do you have any visual references — websites, screenshots, or design systems — you'd like the UI to resemble? If not, I'll design something from scratch based on the tech spec."* Collect URLs or descriptions if provided.
2. **Research the references.** Fetch the provided URLs and analyze their design language: color palette, typography, layout patterns, card styles, spacing, dark/light mode, animations. Summarize the key design tokens you'll use.
3. **If no references are provided**, design an original look-and-feel based on the project's domain and tech stack. Document the design rationale (why these colors, fonts, layout choices).
4. **Create self-contained HTML mockups** — one file per key screen/view. Each file must:
   - Be a single `.html` file that opens directly in a browser (no build step, no server).
   - Embed all CSS inline (no external stylesheets).
   - Use CDN-loaded libraries where needed (e.g., Chart.js for data visualizations).
   - Include realistic sample data (not "Lorem ipsum" — use domain-appropriate values).
   - Be interactive enough to convey the UX: hover states, modals, toggles, navigation between screens.
   - Be responsive (test at both desktop and mobile widths).
5. **Save mockups to `specs/mockups/`** with numbered filenames for natural ordering (e.g., `01-login.html`, `02-dashboard.html`, `03-detail.html`). This directory sits alongside the functional and technical specs so that all design artifacts are in one place. Implementation code in `frontend/` (or equivalent) should reference these mockups as the visual source of truth.
6. **Open the mockups in the browser** and ask the user for feedback. Iterate until the user is satisfied with the look and feel.
7. **Add a section to the tech spec** (or a note at the top) listing the mockup files and what each one covers, so implementers know where to find the visual references.

### Mockup design guidelines

- **Domain-appropriate aesthetics.** A fintech dashboard should look different from a developer tool. Match the visual tone to the product's audience.
- **Consistent design tokens.** Define CSS custom properties for colors, spacing, radii, and typography at the top of each file. Reuse them across all mockups.
- **Real logos and icons.** Search for actual SVG assets (crypto logos, brand marks, etc.) rather than using placeholder symbols.
- **Fonts from CDN.** Use Google Fonts or similar for the actual typefaces specified in the tech spec.
- **Interactive charts.** If the UI includes data visualizations, use a charting library (Chart.js, etc.) with sample data rather than static images.
- **Show edge cases.** Include empty states, loading states, error banners, and modals — not just the happy path.

---

## Guidelines

- **Be concrete, not abstract.** "Use a mutex" is vague. "Wrap the `tokenStore map[string]tokenEntry` with a `sync.RWMutex`; acquire a read lock in `Validate()` and a write lock in `Store()` and `Cleanup()`" is concrete.
- **No hand-waving.** If a behavior requires 5 steps, list all 5. Don't write "handle errors appropriately" — specify exactly how.
- **Resolve, don't defer.** If the functional spec says "reasonable timeout", pick a number and justify it. Don't write "this should be configurable" unless the functional spec says so.
- **Version-pin everything.** Don't write "use OkHttp" — write "use `com.squareup.okhttp3:okhttp:4.12.0`".
- **Code over prose.** When a paragraph of explanation can be replaced by a 10-line code snippet that shows the exact approach, prefer the snippet.
- **Think adversarially.** For each component, ask: "What inputs could break this? What race conditions exist? What if the filesystem changes mid-operation?" Document the answers.
