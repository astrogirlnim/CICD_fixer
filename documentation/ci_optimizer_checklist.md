
# CI Optimizer Agent – MVP Development Checklist

## Phase 1: Foundation ✅
Criteria: Essential systems that the application cannot function without. These are the building blocks that enable all other functionality.

[x] CLI Bootstrap
  [x] Initialize CLI with argparse or Typer (independent - no dependencies)
  [x] Implement version flag and help output (independent - no dependencies)

[x] Config Loader
  [x] Parse `.cicd-fixer.yml` file and load values into config object (independent - no dependencies)
  [x] Add support for CLI flags to override config file values (independent - no dependencies)
  [x] Add support for environment variables (e.g. `CICD_FIXER_AUTOFIX`) (independent - no dependencies)

[x] File Loader
  [x] Recursively collect `.yml` files from `.github/workflows/` (independent - no dependencies)

[x] Secrets Redactor
  [x] Detect and redact secrets/tokens in workflow files before external calls (independent - no dependencies)

---

## Phase 2: Data Layer ✅
Criteria: Systems for storing, retrieving, and managing application data. Each feature handles a specific type of data or storage mechanism.

[x] YAML Parser
  [x] Load and validate YAML structure (depends on File Loader)
  [x] Identify schema violations and invalid keys (depends on YAML Parser)

[x] DAG Analyzer
  [x] Parse job dependencies and build internal DAG (depends on YAML Parser)

[x] Caching Strategy Analyzer
  [x] Identify presence or absence of caching keys (depends on YAML Parser)
  [x] Detect suboptimal cache paths or patterns (depends on YAML Parser)

---

## Phase 3: Interface Layer
Criteria: Components and interactions for users. Each feature represents a distinct interface element or user journey.

[ ] Suggestion Output (Default Mode)
  [ ] Print actionable issues with line numbers and explanations to CLI stdout (depends on YAML Parser)
  [ ] Show patch-like diffs to CLI (depends on auto-fix logic)

[ ] Auto-Fix Output (Optional Mode)
  [ ] Apply changes in-place with clear CLI logs (depends on fixers and config)

[ ] Exit Codes
  [ ] Return 0 on success, 1 on issues, >1 on fatal error (depends on YAML Parser and Fixer Outcomes)

---

## Phase 4: Implementation Layer
Criteria: Application functionality that delivers value. Each feature handles a specific capability.

[ ] YAML Fixer
  [ ] Auto-fix indentation errors and invalid keys (depends on YAML Parser)
  [ ] Ensure schema-compliant workflows (depends on YAML Parser)

[ ] Caching Optimizer
  [ ] Suggest restore-keys if missing (depends on Caching Strategy Analyzer)
  [ ] Optimize path usage for caching (depends on Caching Strategy Analyzer)

[ ] Job Parallelizer
  [ ] Identify jobs that can safely run in parallel (depends on DAG Analyzer)
  [ ] Inject `needs:` keys or remove unnecessary dependencies (depends on DAG Analyzer)

[ ] Step Reorderer
  [ ] Move dependency installation steps earlier (depends on YAML Parser)
  [ ] Reorder for cache optimization (depends on Caching Strategy Analyzer)

---

## Acceptance Tests
[ ] Test on real-world repositories (depends on all functional features)
  [ ] Validate false positive rate <5% (acceptance criteria)
  [ ] Validate performance target: <5s local, <60s CI (acceptance criteria)

