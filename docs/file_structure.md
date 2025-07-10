# CI Optimizer Agent - File Structure

## Directory Structure

```
CICD_fixer/
├── documentation/                    # Project documentation
│   ├── ci_optimizer_agent_design.md # System design and implementation plan
│   ├── ci_optimizer_agent_prd.md    # Product requirements document
│   └── ci_optimizer_checklist.md    # Development checklist
├── docs/                            # Additional documentation
│   └── file_structure.md            # This file - project structure reference
├── ci-agent/                        # Main application directory
│   ├── agent/                       # Core agent logic
│   │   ├── __init__.py
│   │   ├── main.py                  # Main agent orchestrator
│   │   ├── config_loader.py         # Configuration management
│   │   ├── file_loader.py           # Workflow file discovery
│   │   ├── secrets_redactor.py      # Secret redaction logic
│   │   ├── exit_handler.py          # Exit code management
│   │   ├── fixers/                  # Fix implementation modules
│   │   │   ├── __init__.py
│   │   │   ├── yaml_fixer.py        # YAML syntax and schema fixes
│   │   │   ├── caching_fixer.py     # Cache optimization fixes
│   │   │   ├── parallelizer.py     # Job parallelization fixes
│   │   │   └── step_reorderer.py   # Step reordering fixes
│   │   ├── parsers/                 # CI platform parsers
│   │   │   ├── __init__.py
│   │   │   ├── yaml_parser.py       # Generic YAML parser
│   │   │   ├── github_actions.py    # GitHub Actions specific parser
│   │   │   └── gitlab_ci.py         # GitLab CI parser (future)
│   │   ├── analyzers/               # Analysis modules
│   │   │   ├── __init__.py
│   │   │   ├── dag_analyzer.py      # Job dependency DAG analysis
│   │   │   └── caching_analyzer.py  # Cache strategy analysis
│   │   └── output/                  # Output formatting modules
│   │       ├── __init__.py
│   │       ├── suggestion_formatter.py  # Suggestion mode output
│   │       └── autofix_handler.py      # Auto-fix mode handler
│   ├── cli/                         # CLI interface
│   │   ├── __init__.py
│   │   └── cli_entry.py             # CLI entry point
│   ├── githooks/                    # Git hook scripts
│   │   ├── pre-commit               # Pre-commit hook
│   │   └── pre-push                 # Pre-push hook
│   ├── tests/                       # Test suite
│   │   ├── __init__.py
│   │   ├── test_yaml_fixer.py      # YAML fixer tests
│   │   ├── test_parser_github.py    # GitHub Actions parser tests
│   │   └── fixtures/                # Test fixtures
│   │       └── sample_workflows/    # Sample workflow files for testing
│   └── examples/                    # Example configurations
│       └── sample_workflows/        # Sample CI workflows
├── pyproject.toml                   # Project configuration and dependencies
├── requirements.txt                 # Python dependencies
├── .cicd-fixer.yml                  # Default configuration file
├── README.md                        # Project readme
└── .gitignore                       # Git ignore patterns
```

## Key Components

### Phase 1: Foundation
- **CLI Entry**: `cli/cli_entry.py` - Main command-line interface
- **Config Loader**: `agent/config_loader.py` - Handles configuration from file, CLI, and env vars
- **File Loader**: `agent/file_loader.py` - Discovers workflow files
- **Secrets Redactor**: `agent/secrets_redactor.py` - Redacts sensitive data

### Phase 2: Data Layer
- **YAML Parser**: `agent/parsers/yaml_parser.py` - Parses and validates YAML
- **DAG Analyzer**: `agent/analyzers/dag_analyzer.py` - Analyzes job dependencies
- **Caching Analyzer**: `agent/analyzers/caching_analyzer.py` - Analyzes cache usage

### Phase 3: Interface Layer
- **Suggestion Formatter**: `agent/output/suggestion_formatter.py` - Formats suggestions
- **Auto-fix Handler**: `agent/output/autofix_handler.py` - Applies fixes
- **Exit Handler**: `agent/exit_handler.py` - Manages exit codes

### Phase 4: Implementation Layer
- **YAML Fixer**: `agent/fixers/yaml_fixer.py` - Fixes YAML issues
- **Caching Fixer**: `agent/fixers/caching_fixer.py` - Optimizes caching
- **Parallelizer**: `agent/fixers/parallelizer.py` - Optimizes job parallelism
- **Step Reorderer**: `agent/fixers/step_reorderer.py` - Reorders steps for efficiency 