# CI/CD Fixer 🔧

An AI-powered CLI tool that automatically analyzes and optimizes CI/CD pipeline configurations, starting with GitHub Actions. Make your pipelines faster, more reliable, and easier to maintain.

## Features ✨

- **🔍 Auto-detect Issues**: Finds YAML syntax errors, schema violations, and inefficiencies
- **⚡ Performance Optimization**: Parallelizes jobs, optimizes caching, and reorders steps
- **🤖 AI-Powered Suggestions**: Uses LLMs to provide intelligent optimization recommendations
- **🛡️ Privacy-First**: Redacts secrets before any external API calls
- **🎯 Zero Config**: Works out of the box with sensible defaults
- **🔄 Multiple Modes**: Choose between suggestion mode or auto-fix mode

## Installation 📦

```bash
# Install from PyPI (coming soon)
pip install cicd-fixer

# Install from source
git clone https://github.com/yourusername/cicd-fixer.git
cd cicd-fixer
pip install -e .
```

## Quick Start 🚀

```bash
# Analyze your CI workflows (suggestion mode)
cicd-fixer

# Auto-fix issues
cicd-fixer --autofix

# Check specific workflow file
cicd-fixer --file .github/workflows/ci.yml

# Dry run to see what would be changed
cicd-fixer --autofix --dry-run
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

### Local Development

```bash
# Add to git hooks for automatic checking
cicd-fixer install-hooks

# Run before committing
cicd-fixer check
```

### CI Pipeline Integration

```yaml
# .github/workflows/ci.yml
- name: Check CI Configuration
  run: |
    pip install cicd-fixer
    cicd-fixer --exit-on-issues
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

- All secrets are redacted before external API calls
- Use `--no-cloud` flag to disable all external calls
- Sensitive patterns are never sent to LLMs
- Local processing by default

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

- [x] MVP: GitHub Actions support
- [ ] GitLab CI support
- [ ] CircleCI support
- [ ] Jenkins support
- [ ] Web UI dashboard
- [ ] VS Code extension

## Contributing 🤝

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support 💬

- 📧 Email: support@cicd-fixer.dev
- 💬 Discord: [Join our community](https://discord.gg/cicd-fixer)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/cicd-fixer/issues)

---

Made with ❤️ by the CI Optimizer Team 