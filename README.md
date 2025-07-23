# CI/CD Fixer 🔧

A rule-based CLI tool that automatically analyzes and optimizes CI/CD pipeline configurations, starting with GitHub Actions. Make your pipelines faster, more reliable, and easier to maintain.

## Features ✨

- **🔍 Auto-detect Issues**: Finds YAML syntax errors, schema violations, and inefficiencies
- **⚡ Performance Optimization**: Parallelizes jobs, optimizes caching, and reorders steps
- **🧠 Smart Pattern Matching**: Uses comprehensive rules to identify optimization opportunities
- **🛡️ Privacy-First**: Redacts secrets before any external processing
- **🎯 Zero Config**: Works out of the box with sensible defaults
- **🔄 Multiple Modes**: Choose between suggestion mode or auto-fix mode
- **🚀 Ready for AI Enhancement**: Configurable for future LLM integration

## Installation 📦

```bash
# Current: Install from source (PyPI coming soon)
git clone https://github.com/yourusername/cicd-fixer.git
cd cicd-fixer
pip install -r requirements.txt

# Future: Install from PyPI
pip install cicd-fixer  # Coming soon
```

## Quick Start 🚀

```bash
# Navigate to the ci-agent directory
cd ci-agent

# Analyze your CI workflows (suggestion mode)
python -m cli.cli_entry main

# Auto-fix issues (non-interactive)
python -m cli.cli_entry main --autofix --yes

# Check specific workflow file
python -m cli.cli_entry main --file .github/workflows/ci.yml

# Dry run to see what would be changed
python -m cli.cli_entry main --autofix --dry-run

# Future simplified commands (after packaging):
# cicd-fixer, cicd-fixer --autofix, etc.
```

## Configuration ⚙️

Create a `.cicd-fixer.yml` file in your repository root:

```yaml
general:
  mode: suggest  # or 'autofix'
  verbosity: 1   # 0-3

files:
  workflow_paths:
    - .github/workflows/
  exclude:
    - "**/experimental-*.yml"

optimizations:
  yaml:
    fix_indentation: true
  caching:
    suggest_restore_keys: true
  parallelization:
    analyze_dependencies: true
```

## Usage Examples 💡

### Local Development (Current)

```bash
# Run before committing (from ci-agent directory)
python -m cli.cli_entry main --exit-on-issues

# Auto-fix with confirmation
python -m cli.cli_entry main --autofix

# Non-interactive mode for scripts
python -m cli.cli_entry main --autofix --yes
```

### CI Pipeline Integration (Current)

```yaml
# .github/workflows/ci.yml
- name: Check CI Configuration
  run: |
    cd ci-agent
    python -m cli.cli_entry main --exit-on-issues --no-color
```

### Future Enhanced Usage (Planned)

```bash
# Git hooks integration (coming soon)
cicd-fixer install-hooks
cicd-fixer check

# Simplified commands after packaging
cicd-fixer --autofix
```

## Supported Optimizations 🛠️

### Phase 1: Foundation ✅
- CLI with intuitive interface
- Configuration management (file, CLI, env vars)
- Workflow file discovery
- Secret redaction for privacy

### Phase 2: Data Analysis 📊
- YAML parsing and validation
- Job dependency DAG analysis
- Cache strategy analysis

### Phase 3: Smart Fixes 🧠
- **YAML Fixes**: Indentation, invalid keys, schema compliance
- **Cache Optimization**: Missing restore-keys, optimal paths
- **Parallelization**: Convert sequential to parallel jobs
- **Step Reordering**: Optimize for cache reuse

## Privacy & Security 🔒

- All secrets are redacted before any external processing
- Use `--no-cloud` flag to disable future external integrations
- Sensitive patterns are detected and protected
- 100% local processing (no external calls in current version)
- Ready for secure LLM integration when implemented

## Development 👩‍💻

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black ci-agent/
isort ci-agent/

# Type checking
mypy ci-agent/
```

## Architecture 🏗️

```
ci-agent/
├── agent/          # Core logic
├── cli/            # CLI interface
├── fixers/         # Fix implementations
├── parsers/        # Platform parsers
└── analyzers/      # Analysis modules
```

## Roadmap 🗺️

### ✅ Completed (MVP)
- [x] GitHub Actions YAML analysis and optimization
- [x] Rule-based issue detection and fixing
- [x] CLI interface with suggestion and autofix modes
- [x] Configuration management and secret redaction

### 🚧 In Progress (Alpha)
- [ ] PyPI packaging and simplified CLI commands
- [ ] Git hooks integration (`install-hooks`, `check` commands)
- [ ] AI/LLM integration for enhanced suggestions
- [ ] Performance benchmarking and optimization

### 🔮 Future (Beta & Beyond)
- [ ] GitLab CI support
- [ ] CircleCI support
- [ ] Jenkins support
- [ ] Web UI dashboard
- [ ] VS Code extension
- [ ] Real-time optimization recommendations

## Contributing 🤝

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
---

Made with ❤️ by N
