# LLM-Orchestrated Multi-Agent Development Framework

> **Version:** 4.0
> **Target stack:** Python (default)
> **Execution model:** Parallel agents dispatched by an orchestrator

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Mandatory Services & Injection Architecture](#mandatory-services--injection-architecture)
3. [Agent Roster & Responsibilities](#agent-roster--responsibilities)
4. [Shared Infrastructure](#shared-infrastructure)
5. [Phase 0 — Research & Feasibility](#phase-0--research--feasibility)
6. [Phase 1 — Scouting & Architecture](#phase-1--scouting--architecture)
7. [Phase 1.5 — Dry Integration Review](#phase-15--dry-integration-review)
8. [Phase 2 — Implementation & Integration](#phase-2--implementation--integration)
9. [Phase 3 — Verification & Delivery](#phase-3--verification--delivery)
10. [Artifact & Documentation Standards](#artifact--documentation-standards)
11. [Dispute Resolution Protocol](#dispute-resolution-protocol)
12. [Version Control Workflow](#version-control-workflow)
13. [Cold-Start Recovery Protocol](#cold-start-recovery-protocol)
14. [Appendix A — Artifact Templates](#appendix-a--artifact-templates)
15. [Appendix B — Glossary](#appendix-b--glossary)

---

## Core Principles

Non-negotiable. Every agent, every phase.

1. **No Hot Fixes.** Cross-module or core infrastructure problems are escalated, never patched in place.
2. **Single Source of Truth.** Every config value, shared constant, env variable, and feature flag lives in exactly one place.
3. **Modules Are Islands.** Self-contained, explicit inputs/outputs, no hidden dependencies. Communication only through Interface Agent contracts.
4. **Services Are Injected, Never Imported.** No module instantiates or directly imports mandatory services. All cross-cutting services arrive through `__init__` injection.
5. **Presentation Is Decoupled.** Business logic never references rendering, UI frameworks, or display concerns.
6. **Data Access Is Abstracted.** Business logic never calls database drivers, ORMs, or storage APIs directly. All persistent state flows through injected repositories.
7. **Async Boundaries Are Explicit.** If a module does async work, the async nature is visible in its public interface. No hidden concurrency, no fire-and-forget.
8. **Documentation Before Code.** No implementation without a corresponding artifact.
9. **Edge Cases Flow Upstream.** Undocumented situations are escalated to the responsible mandatory agent, who updates central guidance. No improvisation.
10. **Context Window Discipline.** No agent gets more work than it can hold in context with high fidelity. Split and add a partner when in doubt.
11. **Human-in-the-Loop at Phase Gates.** No phase transition without explicit human approval.
12. **Recoverable by Design.** All project state is captured such that any agent with zero prior context can resume from the repository alone.

---

## Mandatory Services & Injection Architecture

Every project includes these mandatory injected services, implemented as core infrastructure before any module work begins.

### Injection Pattern: Constructor Injection via `__init__`

All dependencies are passed as explicit parameters to a module's `__init__`. A composition root at the application entry point creates all services and wires them into modules.

```python
# src/core/composition_root.py

config   = ConfigService.load("config/app.toml")
logger   = LogService(config)
errors   = ErrorService(logger, config)
data_ctx = DataContext(config, logger, errors)

module_a = ModuleA(config=config, logger=logger, errors=errors, data_ctx=data_ctx)
module_b = ModuleB(config=config, logger=logger, errors=errors, data_ctx=data_ctx,
                   module_a_api=module_a.public_interface)
```

**Rules:**
- No module ever calls `ConfigService()` or `from core.logger import logger` internally. Dependencies arrive through `__init__`.
- The composition root is the *only* place where services are instantiated and wired.
- Interfaces are defined using `typing.Protocol` for structural typing. No ABC inheritance required.

```python
from typing import Protocol

class UserRepository(Protocol):
    async def find_by_id(self, user_id: str) -> User | None: ...
    async def create(self, data: UserCreate) -> User: ...
    async def update(self, user_id: str, changes: UserUpdate) -> User: ...
    async def delete(self, user_id: str) -> None: ...
```

---

### Mandatory Service: Logging & Debug System

Centralized, structured, injectable observability for every module.

Without this, modules default to ad-hoc `print()` with no consistency, no severity levels, and no cross-module tracing.

**Requirements:**
- Structured output: timestamp, severity, source module, correlation ID, message payload.
- Severity levels: `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`.
- Output targets configurable via config service, not hardcoded.
- Correlation ID propagation across module boundaries.
- Debug mode: config flag enables verbose output per module without code changes.

```python
# Logger is pre-scoped to the module's name
logger.trace("Detailed step-by-step for deep debugging")
logger.debug("Developer-relevant diagnostics")
logger.info("Normal operational events")
logger.warn("Unexpected but recoverable")
logger.error("Operation failed", error_detail=detail)
logger.fatal("Unrecoverable failure", error_detail=detail)
```

**Ownership:** Best Practices Agent defines severity usage. Configuration Agent owns output targets and debug flags. Interface Agent defines correlation ID propagation.

---

### Mandatory Service: Configuration Injector

Typed, validated, centralized configuration delivery.

Without this, Module A reads an env variable directly, Module B reads a JSON file, Module C has a hardcoded default.

**Requirements:**
- Single source of truth: one schema, one loader, one validation step at startup.
- Typed and validated. Fails fast with clear errors on invalid config.
- Module-scoped access. Modules receive only their config namespace.
- Environment-aware (dev, test, staging, production).
- No direct environment access. No `os.environ` anywhere except the config loader.
- Immutable at runtime.

```python
config.get("database.connection_string")  # Returns typed value
config.get("database.max_retries")        # Returns typed value
config.require("api.secret_key")          # Raises if missing
```

**Ownership:** Configuration Agent owns schema, loader, validation, environment strategy. Best Practices Agent enforces "no direct env access."

---

### Mandatory Service: Error Handling System

Standardized error creation, classification, propagation, and reporting.

Without this, Module A throws strings, Module B throws custom objects, Module C returns None on failure.

**Requirements:**
- Standardized error types via base class and taxonomy (validation, not_found, unauthorized, service_unavailable, internal, etc.).
- Error codes: unique, human-readable (e.g., `USER_VALIDATION_001`).
- Structured payloads: code, category, source module, message, optional context.
- Propagation rules: errors crossing module boundaries are wrapped or enriched, never swallowed.
- Auto-integration with logging at appropriate severity.
- No bare raises. No `raise Exception("something")`. All errors created through the error service.

```python
errors.validation("Invalid input: email format", field="email", value=input_val)
errors.not_found("User not found", user_id=uid)
errors.internal("Database connection failed", original_error=err)
errors.wrap(upstream_error, "Failed during user creation")
```

**Ownership:** Interface Agent defines taxonomy and propagation. Best Practices Agent enforces "no bare raises." Testing Agent includes error path coverage.

---

### Mandatory Boundary: Presentation Layer Decoupling

Hard separation between business logic and any rendering/display.

**Requirements:**
- Business logic exposes a data API, never references UI concerns (DOM, terminal formatting, HTTP responses).
- Presentation layer is a consumer. Never the other way around.
- Swappable: system runs headless for testing. CLI harness proves this.
- Adapter pattern at the boundary: adapters live in `src/presentation/`, not in business logic.

**Ownership:** Interface Agent owns the boundary contract. Best Practices Agent enforces "no UI in business logic."

---

### Mandatory Deliverable: Interactive CLI Harness

A CLI that exercises every module's public API. This is the acid test that the presentation boundary is real.

**Requirements:**
- Built alongside modules during Phase 2, not after.
- Exercises every public interface.
- Uses the same composition root and mandatory services as the main application.
- Interactive with help/discovery.

```
src/cli/
├── cli_entry.py          # CLI-specific composition root
├── commands/
│   ├── module_a_commands.py
│   ├── module_b_commands.py
│   └── ...
└── cli_help.py
```

**Ownership:** Orchestrator includes CLI scope in assignments. Coders build CLI commands for their modules. Testing Agent uses CLI for manual verification. Agent Karen verifies CLI exercises the same code paths as the primary UI.

---

### Mandatory Services in the Module Lifecycle

| Phase | Service Integration |
|-------|-------------------|
| 0 | Feasibility report identifies mandatory services and project-specific extensions. Identifies persistence strategy and async requirements. |
| 1.0 | Config Agent: composition root + config schema. Best Practices Agent: injection pattern + async contract. Interface Agent: logging contract + error taxonomy + presentation boundary. Data Agent: repository patterns + data ownership. |
| 1.x | Every module artifact documents mandatory service usage, data access patterns, async behavior. |
| 1.5 | Dry review verifies consistency across all artifacts against service contracts and config schema. |
| 2.0 | Core services and data layer implemented and tested before any module work. |
| 2.x | Coders implement via injection. Karen verifies no bypasses. Testing Agent uses mocks through same injection chain. |
| 3 | CLI harness delivered. README documents service architecture and CLI usage. |

---

## Agent Roster & Responsibilities

### Execution Model

Agents run as subagents dispatched by the Orchestrator. Each subagent:
- Reads its role instructions on start.
- Has its own context window. No shared memory between agents.
- Communicates through the filesystem: committed artifacts, guidance docs, and code.
- Writes only to its scoped directory.

The Orchestrator is the parent process. It dispatches subagents, tracks progress in STATE.md, and owns all writes to shared files (STATE.md, guidance docs).

---

### Orchestrator

**Role:** Pure coordination. Never implements code.

**Responsibilities:**
- Owns the Implementation Plan and Integration Plan.
- Scopes and assigns all scout/coder work from the feasibility report.
- Enforces context window discipline (complexity budget).
- Dispatches subagents in dependency-ordered waves.
- Resolves disputes via Dispute Resolution Protocol.
- Produces all human-facing progress reports and final README.
- Sole agent that communicates phase-gate status to the human.
- Maintains STATE.md — the single source of truth for project status.
- Sole writer of guidance doc updates (queues edge case escalations from subagents).
- Dispatches parallel Karen instances for verification.

**Complexity Budget:**
- No scout owns more than 3 modules or 5 interface boundaries simultaneously.
- If a domain requires >60% of estimated context capacity, split across two scouts with a designated lead.
- Assignments include explicit dependency annotations.

---

### Mandatory Agents

Operate across all phases. Produce and maintain living guidance documents in `/docs/guidance/`. Their authority within their domain is binding.

**Edge Case Protocol:**
1. Agent encounters undocumented situation.
2. Agent halts and escalates to the Orchestrator with the edge case description.
3. Orchestrator routes to the responsible mandatory agent (or handles it directly if wearing that hat).
4. Guidance document is updated. The update is committed by the Orchestrator.
5. Edge case and resolution logged in the guidance document's changelog.

Note: Because the Orchestrator is the sole writer of guidance docs, edge case escalations are queued and applied serially, avoiding merge conflicts when multiple subagents escalate simultaneously.

---

#### Best Practices Agent

**Domain:** Code quality, architecture patterns, conventions, injection enforcement, concurrency standards.

**Guidance document covers:**
- `__init__` injection pattern for Python with `Protocol` interfaces.
- Concurrency & async patterns (see below).
- Decoupling strategies and DI rules.
- No magic numbers, no direct env access, no bare raises, no UI in business logic, no raw data access.
- Naming conventions, file length limits, function complexity limits.
- Directory structure and project layout.
- Logging severity usage guidelines.
- Comment and documentation standards.
- Version control standards (commit conventions, branching).

**Concurrency & Async Patterns** (mandatory for any project with I/O, network, or data persistence):
- Async interface rule: if a method does async work, it's declared `async def`. No hidden async.
- Composition root handles async initialization (`async` startup sequence) before wiring modules.
- Async error handling: how exceptions propagate through the error service in async contexts. No silent swallowing.
- Concurrency boundaries: where parallelism is allowed, how shared state is avoided, cancellation/timeout strategy.
- No fire-and-forget. Every async operation is awaited, error-handled, or explicitly documented as detached with logging.

---

#### Interface Agent

**Domain:** Cross-module communication, data contracts, error handling, presentation boundary.

**Guidance document covers:**
- Type registry: all shared types used across module boundaries.
- Interface schema: for every module-to-module path, input/output types, async behavior, error contract.
- Error contract: standardized types, codes, propagation rules.
- Correlation ID contract: creation, propagation (including across async boundaries), logging inclusion.
- Presentation boundary contract: business logic API surface and consumption rules.
- DTO standards: how data is shaped at presentation and data access boundaries. DTOs defined here, not in modules.
- Nomenclature guide: canonical naming for cross-module concepts.
- Serialization standards.
- Interface versioning rules.

---

#### Configuration Agent

**Domain:** Project configuration, environment setup, shared constants, feature flags, composition root.

**Guidance document covers:**
- Composition root design: how services (including data context) are instantiated and wired. Handles async initialization.
- Config schema: all values, types, defaults, valid ranges.
- Data layer config: connection strings, pool sizes, timeouts, retry policies.
- Environment setup procedures (dev, test, staging, production).
- Log output targets and per-module log levels.
- Debug mode flags.
- Shared constants registry.
- Feature flags and lifecycle.
- Secrets management (what goes where, what never goes in code).

**Timing:** Completes initial guidance before scouts begin. Composition root design is a Phase 1.0 deliverable.

---

#### Data Agent

**Domain:** Data persistence strategy, access patterns, state management.

Without this, modules each invent their own data access — one uses raw SQL, another an ORM, a third calls the database from a click handler.

**Guidance document covers:**
- Persistence strategy: what storage technologies and why.
- Repository pattern: all access through injected `Protocol` interfaces. Concrete implementations in `src/data/repositories/`.
- Data ownership: every piece of persistent data has exactly one owning module. Only that module's repository writes. Others read through defined interfaces.
- Transaction boundaries: where they live (service/use-case level, not inside repository methods), how passed through injection.
- Migration strategy: how schema changes are proposed, reviewed, versioned, applied. Files in `src/data/migrations/`.
- Seed/fixture data: loading approach. Files in `src/data/seeds/`.
- Caching strategy (if applicable).
- Query standards: repository methods preferred over query builders for consistency.

**Relationship to other agents:** Config Agent owns data layer config. Interface Agent owns DTOs at data boundaries. Best Practices Agent enforces "no raw data access in business logic." Testing Agent defines repository mocking and integration test data lifecycle.

**Timing:** Initial guidance in Phase 1.0. If no persistent state, document that decision and what happens if state is added later.

---

#### Testing Agent

**Domain:** Test strategy, test artifacts, test execution.

**Guidance document covers:**
- Module-level test schema (unit, boundary, contract).
- Mandatory service mocking: how to create/inject mock logger, config, errors, repositories via `__init__`.
- Error path coverage: every module tests its defined error cases, not just happy paths.
- Async testing: proper awaiting, timeout handling, rejection testing, avoiding flaky timing tests.
- Data layer testing: repository implementations against test storage, test data lifecycle (setup, teardown, isolation).
- Test naming and file organization.
- Coverage expectations.
- CLI harness usage for manual integration verification.

**Operational rules:**
- Reviews scout artifacts as they complete, not after the full swarm finishes.
- Produces test artifacts from scout documentation.
- Executes full test suite after all coders complete (Phase 2).

---

#### Dependency Agent

**Domain:** Build order, dependency tracking, sequencing enforcement.

**Responsibilities:**
- Produces and maintains the dependency graph (DAG of all modules).
- Enforces build order: if C depends on A and B, A and B artifacts must be verified before C's scout depends on them.
- Identifies circular dependencies and escalates immediately.
- Updates graph as scouts complete work.
- Notes that `src/core/` and `src/data/` are universal first dependencies.

---

### Scout Swarm

**Role:** Research, design, artifact production.

**Rules:**
- Scope assigned by Orchestrator based on feasibility report and complexity budget.
- Distribution is domain-logical and context-window aware.
- Dispatched in dependency-ordered waves by the Orchestrator.
- Each scout produces per module: a Module Artifact (Appendix A) and a Module Report.
- Edge cases escalated to Orchestrator for routing to mandatory agents.
- Scouts idle when finished and await reassignment.
- **Scouts do not write implementation code.** Artifacts and documentation only.
- Scouts write only to `docs/artifacts/[their-module]/`.

---

### Agent Karen (Compliance Team Lead)

**Role:** Quality gate between artifact intent and actual implementation. Leads the Compliance Team that reviews all modules against guidance documents and fixes drift.

**Team Structure:**
- **Karen instances (Reviewers):** Inspect modules against artifacts and guidance docs. Produce review reports. Do not write code.
- **Compliance Coders (Fixers):** Dispatched by Karen to fix drift issues identified in reviews. Write scope limited to the module under correction.

**Rules:**
- Activates in Phase 2 after coders begin producing code.
- Multiple Karen instances run in parallel, each verifying a different module.
- Compares artifact against implementation line by line.
- Inspects both coder and testing agent work.
- **Mandatory compliance checks:**
  - No direct service instantiation (no `ConfigService()`, no `from core.logger import logger`).
  - No direct env access (no `os.environ`, no `os.getenv()`).
  - No bare raises (no `raise Exception(...)` outside error service).
  - No UI/rendering in `src/modules/`.
  - No raw data access in `src/modules/` (no direct SQL, no direct ORM calls).
  - No hidden async (async signatures match artifact spec).
  - CLI commands exercise same code paths as primary UI.
- **Guidance document compliance checks:**
  - `best-practices.md`: File length limits (300 soft / 500 hard), max 6 constructor parameters, max 50-line functions, max cyclomatic complexity 10.
  - `interface-contracts.md`: Protocol method signatures match, error codes from taxonomy, DTO standards followed.
  - `configuration.md`: Config keys match schema, no undeclared keys, namespaces registered.
  - `data-layer.md`: Repository pattern followed, data ownership respected, transactions at service layer.
  - `testing-standards.md`: Test organization, mock injection, error path coverage, naming conventions.
  - `dependency-graph.md`: No circular dependencies, build order respected.
- Flags discrepancies and determines root cause via Dispute Resolution Protocol.
- Has authority to reject work and dispatch Compliance Coders for corrections.
- Karen instances **do not write code or tests.** They inspect, compare, and dispatch corrections.
- Compliance Coders fix only what Karen assigns. They do not add features or refactor beyond the correction scope.
- Karen re-verifies after each correction round.
- Karen writes to `docs/reviews/[module-name]/`. Compliance Coders write to the module under correction.

---

## Shared Infrastructure

### Central Guidance Repository

```
docs/guidance/
├── best-practices.md
├── interface-contracts.md
├── configuration.md
├── data-layer.md
├── testing-standards.md
├── dependency-graph.md
└── changelog.md          # All guidance changes logged here
```

Every guidance document includes a version number and changelog. Edge case updates log: date, raising agent, edge case summary, resolution.

### Artifact Repository

```
docs/artifacts/
├── module-a/
│   ├── artifact.md
│   └── report.md
├── module-b/
│   ├── artifact.md
│   └── report.md
└── ...
```

Artifacts remain in `docs/artifacts/` as the authoritative design record throughout the project. They are not moved or deprecated.

### Project Source Structure

```
src/
├── core/                        # Mandatory services (implemented first)
│   ├── logger.py
│   ├── config.py
│   ├── errors.py
│   ├── data_context.py          # Data access layer bootstrap
│   └── composition_root.py
├── modules/                     # Business logic modules
│   ├── module_a/
│   ├── module_b/
│   └── ...
├── data/                        # Data layer
│   ├── repositories/            # Concrete repository implementations
│   ├── migrations/
│   └── seeds/
├── presentation/                # Primary UI layer
│   └── adapters/
└── cli/                         # Interactive CLI harness
    ├── cli_entry.py             # CLI-specific composition root
    ├── commands/
    │   ├── module_a_commands.py
    │   └── ...
    └── cli_help.py
```

---

## Phase 0 — Research & Feasibility

**Gate:** Human proposes a project.
**Exit:** Human approves feasibility report.

### Step 0.1 — Requirements Discovery

1. Human presents project concept.
2. Orchestrator researches best standards, common architectures, feature sets for the application type.
3. Orchestrator uses readback technique: restates understanding in structured form, asks for correction.
4. Clarifying questions resolved.
5. Human approves scope and goals.

### Step 0.2 — Technology Selection

1. Orchestrator discusses language/framework options (Python is default unless overridden).
2. Orchestrator researches open-source libraries for each project component.
3. If an alternative stack has materially higher success likelihood, Orchestrator presents that finding with reasoning.
4. Orchestrator identifies candidate libraries for mandatory services (logging, config, CLI, ORM/query builder, migrations).
5. Orchestrator evaluates async/concurrency model and flags architectural implications.
6. Human approves technology stack.

### Step 0.3 — Feasibility Report

Technical white paper covering:

- **Project summary:** What and why.
- **Architecture overview:** High-level design, major components, relationships.
- **Technology stack:** Languages, frameworks, libraries with rationale.
- **Mandatory services plan:** How logging, config, error handling, data access are implemented. Candidate libraries. Any extensions beyond core (metrics, caching, auth).
- **Data persistence strategy:** What data to persist, storage technologies, preliminary data ownership map.
- **Concurrency assessment:** Async requirements, language concurrency model, architectural implications.
- **Presentation layer strategy:** Primary UI technology, CLI approach, adapter pattern.
- **Preliminary dependency graph:** Component dependencies, likely build order. `src/core/` and `src/data/` are universal first.
- **Risk register:** Technical and process risks with mitigations.
- **Scope breakdown:** First-pass decomposition into domains and modules for scout assignment.
- **Estimated complexity:** Rough size to inform scout distribution and wave planning.

**Human reviews and approves. Phase 0 ends.**

**Version control:** Initialize repository with skeleton and Phase 0 deliverables.

---

## Phase 1 — Scouting & Architecture

**Gate:** Human approved Phase 0.
**Exit:** All scouts completed, all mandatory agents finalized initial guidance, human approves.

### Step 1.0 — Mandatory Agent Initialization

Before scouts are dispatched. The following can run in parallel where noted:

**Wave 1 (no interdependencies — run in parallel):**
- Configuration Agent: config schema, environment setup, composition root design.
- Best Practices Agent: coding standards, `__init__` injection pattern, async contract.
- Data Agent: repository patterns, data ownership rules, transaction boundaries, migration approach.

**Wave 2 (depends on Wave 1 outputs):**
- Interface Agent: type registry, error taxonomy, correlation ID contract, DTO standards, presentation boundary contract. (Depends on: Best Practices injection pattern, Data Agent repository interfaces.)
- Testing Agent: testing standards, mocking patterns, async test patterns. (Depends on: Best Practices injection pattern, Data Agent repository interfaces.)
- Dependency Agent: initial dependency graph from feasibility report.

All guidance documents placed in `docs/guidance/`.

**Version control:** Commit all initial guidance documents.

### Step 1.1 — Scout Dispatch

Orchestrator assigns scouts in dependency-ordered waves:
- **Wave 1:** Foundational modules with no inter-module dependencies.
- **Wave 2+:** Modules depending on Wave 1 outputs, and so on.

Each scout receives:
- Assigned modules/domains.
- All mandatory agent guidance documents.
- Dependency graph.
- Explicit artifact/report requirements.
- Mandatory service contracts (logger, config, errors, repository interfaces).
- Concurrency and presentation boundary contracts.

### Step 1.2 — Scout Execution

Per module:
1. Research and design internal architecture.
2. Define public interface (inputs, outputs, errors, async behavior) per Interface Agent contracts.
3. Document mandatory service usage (config keys, log events, error types).
4. Document data access (repository interfaces needed, data owned vs. read, transaction requirements) per Data Agent.
5. Document async behavior (which public methods, why, how errors propagate).
6. Document presentation boundary (business logic API surface, adapter needs).
7. Produce Module Artifact (Appendix A).
8. Produce Module Report.
9. Escalate edge cases to Orchestrator.
10. Submit artifacts to Testing Agent for testability review.

**Scouts do not write implementation code.**

### Step 1.3 — Continuous Review

As scouts complete artifacts:
- Testing Agent reviews for testability and clarity.
- Interface Agent updates interface schema and verifies presentation boundary.
- Data Agent reviews access patterns and data ownership consistency.
- Dependency Agent updates graph.
- Best Practices Agent reviews for standards adherence.
- Configuration Agent verifies all referenced config keys exist in schema.

### Step 1.4 — Scout Completion & Progress Report

When all scouts finish:
1. Scouts idle and await reassignment.
2. Orchestrator produces Phase 1 Progress Report:
   - Modules designed and artifacts produced.
   - Guidance document status.
   - Final dependency graph.
   - Mandatory service and data layer readiness.
   - Open risks.

**Human reviews and approves. Phase 1 ends.**

**Version control:** Commit all artifacts and updated guidance.

---

## Phase 1.5 — Dry Integration Review

**Gate:** Human approved Phase 1.
**Exit:** All interface mismatches and dependency conflicts resolved. Human approves.

Catches integration problems before code exists. Dramatically cheaper than finding them in Phase 2.

### Step 1.5.1 — Interface Compatibility Audit

Interface Agent reviews all artifacts as a complete system:
- Module-to-module contracts match (A's output schema = B's expected input).
- Error contracts consistent across boundaries.
- Async boundaries consistent (if A calls B's async method, A's interface reflects this).
- No naming collisions in type registry.
- No implicit assumptions contradicting other artifacts.
- All presentation boundary definitions follow the contract.

### Step 1.5.2 — Data Layer Consistency Audit

Data Agent reviews:
- Every piece of persistent data has exactly one owning module.
- No modules assume write access to data they don't own.
- Repository interfaces cover all required operations.
- Transaction boundaries clear and non-overlapping.
- Migration plan feasible.

### Step 1.5.3 — Mandatory Service Consistency Check

Configuration Agent and Interface Agent jointly verify:
- Every config key in any artifact exists in the schema.
- Every error type in any artifact exists in the taxonomy.
- Every module's service usage follows the injection pattern.
- Composition root can wire all modules with declared dependencies, including async init order.

### Step 1.5.4 — Dependency Validation

Dependency Agent validates:
- Graph is acyclic.
- All referenced dependencies accounted for.
- Build order feasible.
- `src/core/` and `src/data/` confirmed as first implementation targets.

### Step 1.5.5 — Gap Analysis

Orchestrator produces Dry Integration Report:
- Mismatches found and resolutions.
- Revised artifacts.
- Data ownership conflicts resolved.
- Mandatory service gaps addressed.
- Confirmed integration readiness.

**Human reviews and approves. Phase 1.5 ends.**

**Version control:** Commit revised artifacts and Dry Integration Report.

---

## Phase 2 — Implementation & Integration

**Gate:** Human approved Dry Integration Report.
**Exit:** All code implemented, all tests pass, Karen approved. Human approves.

### Step 2.0 — Core Services & Data Layer Implementation

Before any module work. Orchestrator dispatches coding agents for:

**Core services in `src/core/`:**
1. Logger service (per Interface Agent logging contract).
2. Config service (per Configuration Agent schema).
3. Error service (per Interface Agent error taxonomy).
4. Data context (storage init, repository provision, async init if needed).
5. Composition root (instantiates and wires everything, handles async startup).
6. CLI entry point (CLI-specific composition root).

**Data layer in `src/data/`:**
7. Repository implementations (concrete implementations of Data Agent interfaces).
8. Migration baseline (if applicable).
9. Seed data (if applicable).

Core services and data layer tested independently before module implementation.

### Step 2.1 — Scout-to-Coder Transition

Scouts reassigned as coding agents. Before they begin:
1. Coders receive their original artifacts plus all guidance documents.
2. Orchestrator publishes the Integration Plan (module build order from dependency graph).
3. Coders reminded of mandatory compliance.

### Step 2.2 — Module Implementation

Coders implement in `src/modules/`:
1. Follow artifact spec exactly.
2. Adhere to all guidance.
3. Self-contained unit with Interface Agent contracts.
4. All dependencies via `__init__` injection.
5. Async behavior matches artifact.
6. Edge cases escalated, not hot-fixed.
7. Produce Module Implementation Document (deviations with justification, decisions, limitations).
8. Build CLI commands in `src/cli/commands/`.

**Version control:** Commit after each completed module.

### Step 2.3 — Agent Karen Compliance Sweep

After all modules are implemented (Step 2.2 complete), the Orchestrator dispatches Karen's Compliance Team for a full sweep across all modules. This runs as a batch operation, not incrementally per module.

**Priority order for checks and corrections:**

`interface-contracts.md` compliance is **Priority Zero**. This document is the universal language that allows all modules to communicate blind. Protocol signatures, error codes, and DTO shapes must match the contracts exactly, because interface drift cascades: fixing a protocol signature forces updates to every caller, mock, and test. Fix interfaces first, then everything else.

1. **P0 — Interface contracts:** Protocol signatures, error codes, DTO shapes, type registry.
2. **P1 — Framework rules:** No direct instantiation, no env access, no bare raises, no raw data access.
3. **P2 — Data layer / config:** Repository patterns, data ownership, config key compliance.
4. **P3 — Best practices:** File length, parameter counts, function length, complexity.

**Fix report format (standard for all stages):**

Each finding is one line:
```
[P0|P1|P2|P3] [file:line] what's wrong → what it should be
```

Example:
```
[P0] src/modules/match/protocols.py:42 return type is MatchState → should be MatchSummary per interface-contracts §4.5
[P1] src/modules/energy/service.py:15 bare raise ValueError → use errors.validation()
[P2] src/modules/vault/service.py:88 config key "vault.max_items" not in configuration.md → register or remove
```

**Stage 1 — Document-Level Sweep (lightweight, fast):**
1. Compare artifact report (`docs/artifacts/[module]/report.md`) against implementation doc (`docs/implementation/[module]/`).
2. Pure text-vs-text — no code reading required. One agent can sweep multiple modules.
3. Flag design-level deviations: method count mismatches, missing error handling, undocumented additions.
4. Flag modules with missing or suspiciously thin implementation docs — these need closer code-level scrutiny.
5. Produce preliminary drift report per module.

**Stage 2 — P0 Code Review (interface-contracts, parallel):**
6. One focused agent per module.
7. Agent reads ONLY: `interface-contracts.md` + the module's `protocols.py`, `types.py`, `dto.py` (if present). Nothing else.
8. Compare every method name, parameter name, parameter type, return type, error code against the contracts.
9. Produce a P0-only fix report using the standard format.
10. Context load: ~2k lines per agent. Laser precision.

**Stage 3 — P1-P3 Code Review (pre-baked checklist, parallel):**
11. One agent per module.
12. Agent reads: module artifact + module source + module tests + **pre-baked checklist extract** (not raw guidance docs — the Orchestrator extracts specific rules into a ~500-line template so all reviewers apply identical checks).
13. Run all P1, P2, P3 checks from the pre-baked checklist.
14. Produce a P1-P3 fix report using the standard format.
15. Context load: ~4-5k lines per agent.

**Stage 4 — Compliance Coders Fix Module Code (parallel):**
16. One coder per module (or per group if findings are light).
17. Each coder receives: combined fix report from Stages 1-3, module artifact, relevant guidance docs.
18. Fix business logic, protocols, types, DTOs, service code. **Do NOT touch test files.**
19. Fix only what the fix report specifies. No feature additions, no unscoped refactoring.
20. Produce a concise change report listing what was modified (file, line, what changed).

**Stage 5 — Testing Agent Sweep (grouped by similarity):**
21. Testing agents receive ALL fix reports + ALL change reports from Stage 4.
22. Group modules by pattern for efficient context use:
    - **Group A (sync-pure):** board, scoring, special_gems, board_gen
    - **Group B (async-with-repos):** player, auth, energy, vault, match, events, ads, payments, bot_earnings
    - **Group C (Redis-only):** matchmaking
    - **Group D (presentation):** api
23. Assign as many agents per group as needed — split Group B if context is too large.
24. Testing agents update mocks, fixtures, assertions, and test structure to match Stage 4 code changes.
25. Run tests after fixes to verify all pass.

**Stage 6 — Module Architecture Reports (parallel):**
26. One agent per module, post-fixes.
27. Each agent reads the module source (in its final corrected state) and produces a Module Architecture Report using the standard template:
    - **Public interface summary:** Method signatures, async/sync, brief purpose.
    - **Dependencies consumed:** What protocols/services are injected via `__init__`.
    - **Data owned:** Tables, Redis keys, repository interfaces.
    - **Config keys used:** Namespace and key names.
    - **Error codes raised:** From error taxonomy.
    - **Cross-module interactions:** Which other modules this one calls or is called by.
28. Write to `docs/architecture/[module-name].md`.

**Stage 7 — Karen Aggregates architecture.md:**
29. Single Karen agent reads all 15 module architecture reports.
30. Produces `docs/architecture/architecture.md` — the complete project skeleton:
    - Module map with responsibilities.
    - Full dependency graph (runtime, not build-order).
    - Data flow across modules.
    - Shared type registry summary.
    - Cross-module interface map.
31. This document becomes the authoritative architectural reference for Phase 3 delivery.

### Step 2.4 — Module-Level Testing

After Karen approves a module:
1. Testing Agent produces tests from testing artifacts.
2. Tests use mock/stub services injected through `__init__`.
3. Error path coverage for every defined error case.
4. Async operations tested properly.
5. Tests executed.
6. Failures escalated, not hot-fixed.
7. Repeat until passing.

### Step 2.5 — Integration Testing

After all modules pass module-level tests:
1. Testing Agent produces integration tests (workflow, service, cross-module).
2. Test documentation produced first, reviewed, then implemented.
3. Full injection chain (real services, real composition root, test database).
4. End-to-end async flow verification.
5. CLI harness smoke tests.
6. Failures triaged by Karen.
7. Corrections via standard escalation.

### Step 2.6 — Phase 2 Completion

Orchestrator produces Phase 2 Completion Report:
- All modules implemented and verified.
- All tests passing.
- Karen's final approval with compliance audit results.
- CLI harness functional.
- Deviations from artifacts with justification.

**Human reviews and approves. Phase 2 ends.**

**Version control:** Tag repository.

---

## Phase 3 — Verification & Delivery

**Gate:** Human approved Phase 2.
**Exit:** Final deliverables handed to human.

### Step 3.1 — Final Documentation

Orchestrator produces README.md:
- Project overview.
- Architecture summary (mandatory services, data layer, injection pattern).
- Setup/installation (including database, migrations).
- Configuration guide (config modification, env overrides, debug mode).
- Data layer guide (database setup, migration commands, seed loading).
- CLI harness guide (commands, example workflows).
- Module index.
- Documentation index (all project documents with paths).

### Step 3.2 — Human Handoff

Orchestrator presents:
- README.md.
- Project journey summary.
- Known limitations, tech debt, future recommendations.
- All source in `src/`.
- All documentation in `docs/`.
- Working CLI harness.

**Version control:** Final tag.

---

## Artifact & Documentation Standards

All artifacts follow Appendix A templates.

- Markdown format.
- Header: title, author agent, date, version, status (draft/final).
- Consistent heading levels (H1 title, H2 major, H3 sub).
- Fenced code blocks with language identifiers.
- Decisions include brief rationale.
- Open questions flagged with `> **OPEN QUESTION:**`.

---

## Dispute Resolution Protocol

### Level 1 — Agent Resolution
Coding agent and relevant mandatory agent discuss. If implementation was intentional and justified, artifact is updated. If in error, coder corrects.

### Level 2 — Orchestrator Escalation
If Level 1 doesn't resolve (e.g., fix has cascading implications): Orchestrator evaluates scope, affected modules, interface/service contract impact. Makes binding decision and assigns corrective work.

### Level 3 — Human Escalation
Fundamental design/requirements issue beyond Orchestrator's scope. Escalated with: problem description, options considered, Orchestrator's recommendation, impact assessment per option.

---

## Version Control Workflow

### Repository Initialization (Phase 0 Exit)

Initialize with: project skeleton, feasibility report, `.gitignore`, framework document.

Initial commit: `0.3 orchestrator: project initialization and feasibility report`

### Branching Strategy

- **`main`** — Stable. Only receives merges at phase gates after human approval.
- **`develop`** — Working branch. All agent work here. Merges to `main` at phase gates.
- **`hotfix/*`** — Emergency branches off `main` for post-delivery fixes. Requires human authorization.

Single working branch avoids merge conflicts that LLM agents handle poorly.

### Commit Conventions

```
[phase].[step] [agent-role]: [concise description]
```

Examples:
```
0.3 orchestrator: feasibility report complete
1.0 config-agent: initial configuration schema and composition root design
1.2 scout: module-auth artifact and report
2.2 coder: module-auth implementation and CLI commands
2.4 testing: module-auth tests passing
```

STATE.md updates included in same commit as the work they describe.

### Phase Gate Checkpoints

1. All work on `develop` committed with summary commit.
2. Orchestrator updates STATE.md.
3. `develop` merged to `main`.
4. `main` tagged: `v0.1` (Phase 0), `v1.0` (Phase 1), `v1.5` (Phase 1.5), `v2.0` (Phase 2), `v3.0` (Phase 3).
5. Human reviews diff on `main`.

### Mid-Phase Commits

Commit after meaningful units:
- Completed guidance document.
- Completed module artifact and report.
- Completed module implementation.
- Completed test suite.
- Edge case resolution that updated guidance.

---

## Cold-Start Recovery Protocol

Enable any agent — including one with zero context — to resume from the repository alone.

### The Project State File

Maintained by the Orchestrator at **`STATE.md` in the project root**. First file read on every session start.

Why project root: first thing visible when opening the repo. Cannot be buried in a subfolder.

See the STATE.md template in the companion `STATE.md` file.

### Update Rules (non-negotiable)

1. **Session start.** Read STATE.md. Add Session Log entry with intended work.
2. **Task completion.** Check off checklist item immediately. No batching.
3. **Phase gate.** Full checklist and session log current before requesting human approval.
4. **Session end.** Update "In progress at session end" and "Next action."
5. **Key decisions.** Add to Key Decisions immediately when made.
6. **Blockers.** Update Active Blockers immediately when identified or resolved.

**Commit rule:** Every commit that changes project state includes a STATE.md update in the same commit.

### Recovery Procedure

1. **Read STATE.md.** Session Log → what was happening. Phase Checklist → what's done. Key Decisions → what's settled.
2. **Identify position.** First unchecked checklist item = where to resume. Most recent Session Log "Next action" = specific task.
3. **Check for crash damage.** If last session has "In progress" populated but no checked item, work was interrupted. Check "Files touched" against repo state.
4. **Read only what's needed.** Based on current phase, read relevant guidance and active artifacts from Document Map.
5. **Announce recovery.** Tell the human. Summarize position and intent. Wait for confirmation.
6. **Resume.** New Session Log entry and continue.

---

## Appendix A — Artifact Templates

### Module Artifact Template

```markdown
# Module Artifact: [Module Name]

## Header
- **Author:** [Scout ID]
- **Date:** [Date]
- **Version:** [Version]
- **Status:** [Draft | Final]
- **Dependencies:** [Modules this depends on]
- **Dependents:** [Modules that depend on this]

## Purpose
[One paragraph: what and why.]

## Public Interface
### Inputs
[Name, type, description, validation rules per input.]

### Outputs
[Name, type, description per output.]

### Error Cases
[Condition, error type (from taxonomy), error code, expected behavior per case.]

### Async Behavior
[Which public methods are async and why. What triggers async (I/O, network, data access). How async errors propagate. If fully synchronous, state that and explain why.]

## Mandatory Service Usage
### Configuration Keys
[Every config key read, with type and purpose. Must match config schema.]

### Logging Events
[Key log events: description, severity, trigger condition.]

### Error Types Used
[Which taxonomy types this module creates or handles, and conditions.]

## Data Access
### Owned Data
[Persistent data this module owns (write access). Entity descriptions, key fields.]

### Repository Interfaces Required
[Which repository Protocol interfaces needed, which operations used.]

### Data Read from Other Modules
[Data read from other modules' ownership, through what interface.]

### Transaction Requirements
[Whether transactional operations needed, transaction boundaries.]

## Presentation Boundary
[Business logic API surface for presentation layer. Data shapes an adapter needs. What does NOT belong in this module.]

## Internal Design
[Internal architecture, data structures, algorithms, patterns. Enough detail for a coder to implement without guessing.]

## CLI Surface
[CLI commands exercising public API. Arguments, example invocations, expected outputs.]

## Edge Cases & Decisions
[Edge cases from scouting, decisions made, rationale.]

## Open Questions
[Unresolved questions for Orchestrator or human.]
```

### Module Report Template

```markdown
# Module Report: [Module Name]

## Header
- **Author:** [Scout ID]
- **Date:** [Date]

## Summary
[What was designed, key outcomes.]

## Alternatives Considered
[Other approaches evaluated, why rejected.]

## Risks
[Known risks specific to this module.]

## Dependencies & Sequencing Notes
[Build order notes, blockers, coordination needed.]
```

---

## Appendix B — Glossary

- **Artifact:** Structured design document from a scout describing a module's purpose, interface, internals, service usage, data access, async behavior, and edge cases in sufficient detail for implementation.
- **CLI Harness:** Mandatory CLI exercising every module's public API, proving presentation decoupling.
- **Coding Agent:** A scout transitioned to implementation in Phase 2.
- **Cold-Start Recovery:** Process by which an agent with zero context resumes from the repository and STATE.md alone.
- **Complexity Budget:** Maximum scope per scout, calibrated to context window capacity.
- **Composition Root:** Single location (`src/core/composition_root.py`) where all services are instantiated and wired via `__init__` injection.
- **Constructor Injection:** Mandatory DI pattern. All dependencies passed as `__init__` parameters.
- **Correlation ID:** Unique identifier following a request across module boundaries for cross-module log tracing.
- **Data Ownership:** Every piece of persistent data has exactly one owning module with write access.
- **Dependency Graph:** DAG of all modules and dependencies, maintained by Dependency Agent.
- **Edge Case Protocol:** Escalation of undocumented situations to responsible mandatory agent for guidance update.
- **Error Taxonomy:** Standardized error types, codes, categories defined by Interface Agent.
- **Feasibility Report:** Phase 0 deliverable establishing scope, architecture, stack, risks, module breakdown.
- **Guidance Document:** Living document by a mandatory agent defining standards within its domain. Binding on all agents.
- **Hot Fix:** Ad-hoc code change without proper escalation. Prohibited.
- **Mandatory Services:** Required injected services: logging, configuration, error handling, data access.
- **Module:** Self-contained functionality unit with defined inputs, outputs, single responsibility.
- **Orchestrator:** Master coordinating agent. Pure coordination, never implements.
- **Phase Gate:** Human-approval checkpoint between phases.
- **Presentation Boundary:** Architectural separation between business logic and rendering.
- **Protocol:** Python `typing.Protocol` class defining structural interface contracts. Preferred over ABC.
- **Repository Pattern:** Data access abstraction where modules interact with data through injected Protocol interfaces.
- **Scout:** Agent assigned to research, design, and produce artifacts during Phase 1.
- **STATE.md:** Project root file maintained by Orchestrator enabling cold-start recovery.
